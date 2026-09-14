'use strict';

import { get_state, switch_mode } from './services/api.js';

/******************************************************************************
 * Constants
 ******************************************************************************/

const REFRESH_INTERVAL_MS = 30000;

// Confirmation window for Admin: the second tap must land within this time
const ARM_TIMEOUT_MS = 4000;

const MODE_LABELS = {
  school: 'School',
  free: 'Free Time',
  lock: 'Locked',
  admin: 'Admin',
};

// Modes that need a second tap before they are sent
const CONFIRM_MODES = new Set(['admin']);

/******************************************************************************
 * State
 ******************************************************************************/

const appState = {
  devices: [],
  modes: [],
  isBusy: false,
  armedButton: null,
  armedTimer: null,
  refreshTimer: null,
};

/******************************************************************************
 * DOM Helpers
 ******************************************************************************/

const get_element = (selector) => document.querySelector(selector);

const tabletsContainer = get_element('[data-tablets]');
const allModesContainer = get_element('[data-modes-all]');
const statusElement = get_element('[data-status]');
const messageElement = get_element('[data-message]');
const cardTemplate = get_element('[data-template="card"]');

const mode_label = (mode) => MODE_LABELS[mode] || (mode ? mode : 'Unknown');

const create_mode_button = (number, mode) => {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `modes__button modes__button--${mode}`;
  button.dataset.number = number;
  button.dataset.mode = mode;
  button.textContent = mode_label(mode);
  return button;
};

const render_mode_buttons = (container, number, activeMode) => {
  container.replaceChildren();
  const fragment = document.createDocumentFragment();
  appState.modes.forEach((mode) => {
    const button = create_mode_button(number, mode);
    button.classList.toggle('is-active', mode === activeMode);
    fragment.appendChild(button);
  });
  container.appendChild(fragment);
};

const create_card = (device) => {
  const card = cardTemplate.content.firstElementChild.cloneNode(true);
  card.dataset.number = device.number;
  card.classList.add(`card--${device.mode || 'unknown'}`);

  card.querySelector('[data-card-name]').textContent = device.description || device.number;
  card.querySelector('[data-card-number]').textContent = device.number;

  const modeBadge = card.querySelector('[data-card-mode]');
  modeBadge.textContent = mode_label(device.mode);
  modeBadge.classList.add(`card__current-mode--${device.mode || 'unknown'}`);

  render_mode_buttons(card.querySelector('[data-card-modes]'), device.number, device.mode);
  return card;
};

const render_state = () => {
  const fragment = document.createDocumentFragment();
  appState.devices.forEach((device) => fragment.appendChild(create_card(device)));
  tabletsContainer.replaceChildren(fragment);

  // "All tablets" highlights a mode only when every tablet agrees
  const modes = new Set(appState.devices.map((device) => device.mode));
  const sharedMode = modes.size === 1 ? appState.devices[0].mode : null;
  render_mode_buttons(allModesContainer, 'all', sharedMode);
};

const set_status = (text) => {
  statusElement.textContent = text;
};

const show_message = (text) => {
  messageElement.textContent = text;
  messageElement.hidden = false;
};

const clear_message = () => {
  messageElement.hidden = true;
  messageElement.textContent = '';
};

const set_busy = (isBusy) => {
  appState.isBusy = isBusy;
  document.querySelectorAll('[data-mode]').forEach((button) => {
    button.disabled = isBusy;
  });
};

const disarm = () => {
  clearTimeout(appState.armedTimer);
  if (appState.armedButton) {
    appState.armedButton.classList.remove('is-armed');
    appState.armedButton.textContent = mode_label(appState.armedButton.dataset.mode);
  }
  appState.armedButton = null;
  appState.armedTimer = null;
};

const arm = (button) => {
  disarm();
  button.classList.add('is-armed');
  button.textContent = `Tap again for ${mode_label(button.dataset.mode)}`;
  appState.armedButton = button;
  appState.armedTimer = setTimeout(disarm, ARM_TIMEOUT_MS);
};

const time_now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

/******************************************************************************
 * API Functions
 ******************************************************************************/

const apply_state = (state) => {
  appState.devices = state.devices;
  appState.modes = state.modes;
  render_state();
  set_status(`${state.dryRun ? 'Dry run · ' : ''}Updated ${time_now()}`);
};

const refresh_state = async () => {
  try {
    apply_state(await get_state());
    clear_message();
  } catch (error) {
    set_status('Offline');
    show_message(`Could not read tablet state: ${error.message}`);
  }
};

const request_switch = async (number, mode) => {
  set_busy(true);
  set_status(`Switching ${number === 'all' ? 'all tablets' : number} to ${mode_label(mode)}…`);
  try {
    apply_state(await switch_mode(number, mode));
    clear_message();
  } catch (error) {
    show_message(`Switch failed: ${error.message}`);
    await refresh_state();
  } finally {
    set_busy(false);
  }
};

/******************************************************************************
 * Event Handlers
 ******************************************************************************/

const handle_mode_click = (event) => {
  const button = event.target.closest('[data-mode]');
  if (!button || appState.isBusy) return;

  const { number, mode } = button.dataset;

  if (CONFIRM_MODES.has(mode) && appState.armedButton !== button) {
    arm(button);
    return;
  }

  disarm();
  request_switch(number, mode);
};

const handle_visibility_change = () => {
  if (document.visibilityState === 'visible') {
    refresh_state();
  }
};

/******************************************************************************
 * Initialization
 ******************************************************************************/

const initialize = () => {
  document.addEventListener('click', handle_mode_click);
  document.addEventListener('visibilitychange', handle_visibility_change);
  refresh_state();
  appState.refreshTimer = setInterval(refresh_state, REFRESH_INTERVAL_MS);
};

document.addEventListener('DOMContentLoaded', initialize);
