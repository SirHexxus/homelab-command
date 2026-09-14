"""Headwind MDM client for the Sophy tablet policy family.

Shared by ``bin/sophy-switch`` (CLI, cron, NFC) and ``bin/sophy-web`` (the parent
control page). Every tablet has its own pair of Headwind configurations, named
after the device number so nothing in this repo says whose tablet it is or which
school app it runs, plus shared configurations that apply to every tablet:

    <number>: School        e.g. "sophy-01: School"   (mode: school)
    <number>: Free Time     e.g. "sophy-01: Free Time" (mode: free)
    Sophy: Locked           nothing usable            (mode: lock)
    Sophy: Admin            everything open           (mode: admin)

"unlock" is an alias for "school": a lock always releases to the fail-closed
state; Free Time is a deliberate parent action, never automatic. Admin clears
every restriction (a parent can reach Settings, the store, and the USB
debugging toggle); School re-applies them, so leaving Admin for School kills
ADB again.

Leaving Locked for School is a kiosk-to-kiosk change, which the launcher does
not act on while it is pinned as its own content app (observed 2026-09-13). So
that transition is bounced through Free Time — a few seconds of the launcher
desktop — before School is applied.

Talks to the Headwind MDM private REST API: log in for a JWT, resolve the
device and the target configuration to their ids, then reassign the device's
configurationId in one PUT — the server pushes the change to the tablet over
MQTT (design doc §7, Gate 1).

Credentials come from the environment only (never arguments, never a file
in this repo):

    THEMIS_URL       https://themis.sirhexx.com
    THEMIS_USER      panel user with the edit_devices permission
    THEMIS_PASSWORD  its password
"""

# ── Standard library imports ──────────────────────────────────────────────────
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable

# ── Constants ─────────────────────────────────────────────────────────────────
# Per-device modes: the configuration is "<number>: <label>".
MODES = {
    'school': 'School',
    'free': 'Free Time',
}

# Shared modes: one configuration for every tablet.
SHARED_MODES = {
    'lock': 'Sophy: Locked',
    'admin': 'Sophy: Admin',
}

MODE_ALIASES = {
    'unlock': 'school',
}

# Order the modes are offered in (CLI help, control page buttons).
MODE_ORDER = ('school', 'free', 'lock', 'admin')

# Device numbers --all expands to. Neutral by design (CLAUDE.md rule 6).
ALL_DEVICES = ('sophy-01', 'sophy-02')

REQUIRED_ENV = ('THEMIS_URL', 'THEMIS_USER', 'THEMIS_PASSWORD')

HTTP_TIMEOUT_SECONDS = 15

# How long to leave a tablet in Free Time when bouncing out of Locked.
BOUNCE_SECONDS = 6


# ── Exceptions ────────────────────────────────────────────────────────────────

class HeadwindError(Exception):
    """A request to the Headwind server failed or returned an error status."""


class ConfigError(Exception):
    """The environment or the server's configuration set is not usable."""


# ── Functions ─────────────────────────────────────────────────────────────────

def env_config() -> dict[str, str]:
    """Read the server URL and credentials from the environment."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise ConfigError(f"missing environment variable(s): {', '.join(missing)}")
    return {name: os.environ[name].strip() for name in REQUIRED_ENV}


def request(base_url: str, method: str, path: str, body: dict | list | None = None,
            token: str | None = None) -> dict:
    """Send one JSON request to the Headwind REST API and return the parsed body."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f'{base_url.rstrip("/")}/rest{path}', data=data,
                                 method=method)
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')

    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise HeadwindError(f'{method} {path} -> HTTP {exc.code} {exc.reason}') from exc
    except urllib.error.URLError as exc:
        raise HeadwindError(f'cannot reach {base_url}: {exc.reason}') from exc
    except json.JSONDecodeError as exc:
        raise HeadwindError(f'{method} {path} returned a non-JSON body') from exc

    if isinstance(payload, dict) and payload.get('status') not in (None, 'OK'):
        message = payload.get('message') or payload.get('status')
        raise HeadwindError(f'{method} {path} -> {message}')
    return payload


def login(config: dict[str, str]) -> str:
    """Exchange credentials for a JWT.

    Headwind expects the MD5 hex of the password, upper-cased — the case is
    baked into the stored hash, and the web panel sends it upper-cased.
    """
    password_md5 = hashlib.md5(config['THEMIS_PASSWORD'].encode()).hexdigest().upper()
    payload = request(config['THEMIS_URL'], 'POST', '/public/jwt/login',
                      {'login': config['THEMIS_USER'], 'password': password_md5})
    token = payload.get('id_token')
    if not token:
        raise HeadwindError('login succeeded but no id_token in the response')
    return token


def list_configurations(base_url: str, token: str) -> dict[str, int]:
    """Return {configuration name: id} for every configuration on the server."""
    payload = request(base_url, 'GET', '/private/configurations/list', token=token)
    return {item['name']: item['id'] for item in payload['data']}


def get_device(base_url: str, token: str, number: str) -> dict:
    """Return the device record for a device number (the ID shown in the panel)."""
    payload = request(base_url, 'GET', f'/private/devices/number/{number}', token=token)
    device = payload.get('data')
    if not device:
        raise HeadwindError(f'no device with number {number!r}')
    return device


def assign_configuration(base_url: str, token: str, device_id: int,
                         configuration_id: int) -> None:
    """Reassign one device to a configuration; the server pushes it to the tablet."""
    request(base_url, 'PUT', '/private/devices',
            {'ids': [device_id], 'configurationId': configuration_id}, token=token)


def configuration_name(number: str, mode: str) -> str:
    """Return the configuration name for a device number and mode."""
    mode = MODE_ALIASES.get(mode, mode)
    if mode in SHARED_MODES:
        return SHARED_MODES[mode]
    return f'{number}: {MODES[mode]}'


def mode_of(name: str, number: str) -> str | None:
    """Return the mode a configuration name represents for a device, if any."""
    for mode in MODE_ORDER:
        if configuration_name(number, mode) == name:
            return mode
    return None


def device_states(base_url: str, token: str,
                  numbers: tuple[str, ...] = ALL_DEVICES) -> list[dict]:
    """Return the current configuration and mode of each tablet.

    ``description`` is whatever the panel holds for the device (the family
    keeps the child's name there) — it is server data, never repo data.
    """
    configurations = list_configurations(base_url, token)
    by_id = {cfg_id: name for name, cfg_id in configurations.items()}
    states = []
    for number in numbers:
        device = get_device(base_url, token, number)
        name = by_id.get(device.get('configurationId'), f'#{device.get("configurationId")}')
        states.append({
            'number': number,
            'description': device.get('description') or '',
            'configuration': name,
            'mode': mode_of(name, number),
        })
    return states


def switch(config: dict[str, str], number: str, mode: str, dry_run: bool = False,
           token: str | None = None, log: Callable[[str], None] = print) -> dict:
    """Resolve ids, then move the device (or report what would happen).

    Returns {number, before, after, bounced, changed}; ``log`` receives the
    one-line human summary the CLI prints.
    """
    base_url = config['THEMIS_URL']
    token = token or login(config)

    configurations = list_configurations(base_url, token)
    target_name = configuration_name(number, mode)
    if target_name not in configurations:
        raise ConfigError(f'configuration {target_name!r} does not exist on the server; '
                          f'create it in the panel first')
    target_id = configurations[target_name]

    device = get_device(base_url, token, number)
    current_id = device.get('configurationId')
    current_name = next((name for name, cfg_id in configurations.items()
                         if cfg_id == current_id), f'#{current_id}')
    result = {'number': number, 'before': current_name, 'after': target_name,
              'bounced': False, 'changed': False}

    if current_id == target_id:
        log(f'{number}: already in {target_name!r}')
        return result

    bounce_name = configuration_name(number, 'free')
    needs_bounce = (current_name == SHARED_MODES['lock']
                    and target_name == configuration_name(number, 'school'))
    if needs_bounce and bounce_name not in configurations:
        raise ConfigError(f'configuration {bounce_name!r} does not exist on the server; '
                          f'it is needed to leave {current_name!r}')
    result['bounced'] = needs_bounce

    if dry_run:
        via = f' via {bounce_name!r}' if needs_bounce else ''
        log(f'{number}: would move {current_name!r} -> {target_name!r}{via} '
            f'(device id {device["id"]}, configuration id {target_id})')
        return result

    if needs_bounce:
        assign_configuration(base_url, token, device['id'], configurations[bounce_name])
        time.sleep(BOUNCE_SECONDS)

    assign_configuration(base_url, token, device['id'], target_id)
    after = get_device(base_url, token, number)
    if after.get('configurationId') != target_id:
        raise HeadwindError(f'{number} still reports configuration '
                            f'{after.get("configurationId")}')
    result['changed'] = True
    log(f'{number}: {current_name!r} -> {target_name!r}')
    return result
