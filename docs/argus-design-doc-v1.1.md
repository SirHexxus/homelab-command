# Argus Design Doc
**Version:** 1.1
**Last Updated:** February 2026
**Status:** Living Document

---

## 1. Purpose & Philosophy

Argus is an AI-augmented security operations platform for the homelab. Named after the Greek giant Panoptes — the all-seeing, ever-watchful guardian with a hundred eyes — Argus combines traditional SIEM tooling with local AI inference to provide continuous monitoring, automated threat analysis, and conversational incident response.

**Design principles:**
- Every log source feeds a single coherent picture, not isolated silos
- AI analysis is local-first — sensitive security data doesn't leave the network
- Raw logs and AI-derived intelligence are stored separately but queryable together
- Automation reduces MTTR; human judgment handles ambiguous cases
- The system explains its reasoning — no black-box alerts
- Portfolio-quality documentation at every layer

**Dual purpose:** Argus serves as both a functional homelab security platform and the centerpiece portfolio artifact for the CRDC application. Architecture decisions are made to be defensible and demonstrable in an interview context.

---

## 2. System Overview

```
LOG SOURCES
(pfSense, Suricata, Wazuh, Proxmox, Switches)
         |
         v
  COLLECTION LAYER
  (syslog-ng + Vector)
         |
         v
  SIEM LAYER
  (Splunk Free + Wazuh Manager)
         |
    _____|_____________________________
    |                                 |
    v                                 v
POSTGRES:argus_logs            GRAFANA
(TimescaleDB hypertables)      (Dashboards)
         |
         v
  n8n AI ANALYSIS LAYER
  (Every 5 min: query → analyze → enrich)
         |
    _____|_____________________________
    |                                 |
    v                                 v
POSTGRES:second_brain          TELEGRAM
(Incidents as resources)       (Alerts + Argus Agent)
```

---

## 3. Infrastructure

| Service | IP | VLAN | Notes |
|---------|-----|------|-------|
| Splunk Free | 10.0.50.20 | 50 — Lab Services | Log aggregation + search + dashboards |
| Wazuh Manager | 10.0.50.21 | 50 — Lab Services | EDR + host-based IDS |
| Grafana | 10.0.50.22 | 50 — Lab Services | TimescaleDB metric dashboards |
| Suricata | pfSense package | 10 — Management | Network-layer IDS; alerts → Splunk |
| Crowdsec | pfSense package | 10 — Management | Application-layer behavioral IPS; community threat intel; integrates with pfSense + NPM |
| Fail2ban | Per-host | All | Log-based brute force protection on SSH hosts + NPM |
| Uptime Kuma | External VPS | — | Outside-in availability monitoring |
| syslog-ng + Vector | TBD | 50 — Lab Services | Central log receiver + bulk ingestion; host TBD |

All VLAN 50 services are IaC-deployed via Terraform + Ansible.

---

## 4. Log Sources & Collection

### 4.1 Log Sources

| Source | Type | Transport | Data |
|--------|------|-----------|------|
| pfSense | Firewall | Syslog UDP 514 | Firewall allow/deny, DHCP, NAT |
| Suricata (pfSense pkg) | Network IDS | eve.json / syslog | Signature alerts, network flows |
| Wazuh Agents | Host EDR | Wazuh protocol → Manager | File integrity, process events, auth logs |
| Proxmox hosts | System | Syslog | VM/LXC start/stop, resource events |
| Managed switch | Network | Syslog | VLAN changes, port events |
| Crowdsec | IPS | API / syslog | Behavioral detections, bans |
| Fail2ban | Host | Log file / syslog | Ban/unban events per host |

### 4.2 Collection Architecture

**Hybrid approach:** syslog-ng for reception and routing; Vector (Rust-based log router) for high-volume bulk ingestion to TimescaleDB; n8n for AI-enriched event processing.

```
pfSense / Suricata / Proxmox / Switch
    |
    v
syslog-ng (central receiver; host TBD)
    Listens: UDP 514, TCP 514, TLS 6514
    |
    |-- High volume (firewall, flows) --> Vector --> TimescaleDB hypertables
    |-- Critical / anomalous events  --> n8n webhook --> AI pipeline
    |-- All events                   --> Splunk forwarder --> Splunk
    |
Wazuh Agents --> Wazuh Manager --> Wazuh API --> n8n + Splunk
```

**Why Vector for bulk ingestion:** Better performance than n8n for continuous high-volume log streams; built-in parsing and enrichment; direct TimescaleDB output. n8n handles the intelligent exception path, not the firehose.

---

## 5. Data Storage

### 5.1 Postgres: argus_logs database

Time-series log storage using TimescaleDB hypertables. Lives in the same Postgres instance as `second_brain` (10.0.50.14) for unified backup and cross-database JOIN capability.

**Extensions required:** TimescaleDB, pg_trgm

```sql
-- Firewall logs
CREATE TABLE firewall_logs (
    time            TIMESTAMPTZ NOT NULL,
    action          VARCHAR(10),        -- allow, block, reject
    direction       VARCHAR(10),        -- in, out
    interface       VARCHAR(20),
    src_ip          INET,
    dst_ip          INET,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    bytes           BIGINT,
    vlan_src        INTEGER,
    vlan_dst        INTEGER,
    rule_id         TEXT,
    metadata        JSONB
);
SELECT create_hypertable('firewall_logs', 'time');

-- IDS/IPS alerts
CREATE TABLE ids_alerts (
    time            TIMESTAMPTZ NOT NULL,
    severity        VARCHAR(20),        -- low, medium, high, critical
    src_ip          INET,
    dst_ip          INET,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    signature_id    TEXT,
    signature_name  TEXT,
    category        TEXT,
    source          VARCHAR(20),        -- suricata, crowdsec, fail2ban
    analyzed        BOOLEAN DEFAULT false,
    metadata        JSONB
);
SELECT create_hypertable('ids_alerts', 'time');

-- Host/system logs (Wazuh)
CREATE TABLE system_logs (
    time            TIMESTAMPTZ NOT NULL,
    host            TEXT,
    agent_id        TEXT,
    rule_id         TEXT,
    rule_level      INTEGER,            -- Wazuh severity 0-15
    rule_description TEXT,
    log_source      TEXT,
    full_log        TEXT,
    analyzed        BOOLEAN DEFAULT false,
    metadata        JSONB
);
SELECT create_hypertable('system_logs', 'time');

-- Network flows (aggregated)
CREATE TABLE network_flows (
    time            TIMESTAMPTZ NOT NULL,
    src_ip          INET,
    dst_ip          INET,
    src_port        INTEGER,
    dst_port        INTEGER,
    protocol        VARCHAR(10),
    bytes_in        BIGINT,
    bytes_out       BIGINT,
    packets_in      BIGINT,
    packets_out     BIGINT,
    duration_ms     INTEGER,
    vlan            INTEGER,
    metadata        JSONB
);
SELECT create_hypertable('network_flows', 'time');

-- Security incidents (AI-derived; links to second_brain)
CREATE TABLE security_incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    time            TIMESTAMPTZ NOT NULL,
    severity        VARCHAR(20),
    title           TEXT,
    summary         TEXT,               -- AI-generated
    src_ip          INET,
    target_host     TEXT,
    iocs            JSONB,              -- extracted indicators of compromise
    mitre_tactics   TEXT[],             -- mapped ATT&CK tactics
    mitre_techniques TEXT[],            -- mapped ATT&CK techniques
    second_brain_id UUID,               -- link to second_brain.resources
    status          VARCHAR(20) DEFAULT 'open',  -- open, investigating, resolved, false_positive
    resolved_at     TIMESTAMPTZ,
    metadata        JSONB
);
SELECT create_hypertable('security_incidents', 'time');
```

**Retention and compression policies:**

```sql
-- Retain hot data 90 days; compress after 7 days (~90% storage reduction)
SELECT add_retention_policy('firewall_logs', INTERVAL '90 days');
SELECT add_compression_policy('firewall_logs', INTERVAL '7 days');

SELECT add_retention_policy('ids_alerts', INTERVAL '90 days');
SELECT add_compression_policy('ids_alerts', INTERVAL '7 days');

SELECT add_retention_policy('system_logs', INTERVAL '90 days');
SELECT add_compression_policy('system_logs', INTERVAL '7 days');

SELECT add_retention_policy('network_flows', INTERVAL '90 days');
SELECT add_compression_policy('network_flows', INTERVAL '7 days');

-- Incidents kept indefinitely (AI-derived knowledge; small volume)
-- Archive to MinIO yearly
```

### 5.2 Splunk Free

Parallel log destination for interactive search, correlation rules, and portfolio-quality dashboards. Splunk's SPL query language and native dashboards are industry-standard and directly demonstrable in an interview.

**Index structure:**
- `firewall` — pfSense logs
- `ids` — Suricata + Crowdsec alerts
- `endpoint` — Wazuh agent events
- `system` — Proxmox + switch logs
- `argus` — AI analysis outputs

**Key dashboards:**
- Network traffic by VLAN (top talkers, bytes in/out)
- Firewall blocks over time (by source, destination, rule)
- Alert trends (IDS/IPS severity over time)
- MITRE ATT&CK coverage heatmap
- Wazuh agent health + event counts

### 5.3 Relationship: TimescaleDB vs. Splunk

These are not redundant — they serve different purposes:

| | TimescaleDB | Splunk |
|-|-------------|--------|
| Primary use | AI pipeline data source; metric aggregation; long-term storage | Interactive investigation; correlation rules; portfolio dashboards |
| Query method | SQL (familiar; scriptable) | SPL (industry standard; demonstrable) |
| AI integration | Direct — n8n queries TimescaleDB | Indirect — Splunk → TimescaleDB or Splunk API |
| Retention | 90 days hot + compression | 90 days (Splunk Free limit) |
| Cost | Free (self-hosted) | Free (500MB/day ingest limit) |

---

## 6. AI Analysis Pipeline

### 6.1 Overview

The AI pipeline runs on a 5-minute polling cycle. It reads unanalyzed high-severity events from TimescaleDB, routes them through the model stack, generates structured incident assessments, and writes results back to both TimescaleDB (`security_incidents`) and `second_brain.resources`.

This is the core differentiator of Argus over a standard SIEM deployment.

### 6.2 Model Routing

Follows the same tiered routing architecture as the Second Brain (see Second Brain Design Doc §6.1):

| Task | Primary | Escalation |
|------|---------|------------|
| Severity triage (is this worth analyzing?) | Mistral 7B | — |
| Incident summarization | Mistral 7B | Gemini Flash |
| IOC extraction | Mistral 7B | Gemini Flash |
| MITRE ATT&CK mapping | Gemini Flash | Claude Sonnet |
| Strategic threat assessment / judgment calls | Claude Sonnet | — |
| Embeddings | nomic-embed-text | — |

### 6.3 5-Minute Analysis Workflow

```
n8n scheduled trigger (every 5 min)
    |
    v
Query TimescaleDB:
    SELECT * FROM ids_alerts
    WHERE analyzed = false
    AND severity IN ('high', 'critical')
    ORDER BY time DESC
    LIMIT 50

    SELECT * FROM system_logs
    WHERE analyzed = false
    AND rule_level >= 10
    ORDER BY time DESC
    LIMIT 50
    |
    v
For each unanalyzed event:
    |
    v
Mistral 7B: severity triage
    "Is this event worth full analysis or routine noise?"
    |
    |-- [Noise / false positive candidate]
    |       --> Mark analyzed = true; skip
    |
    |-- [Worth analyzing]
            |
            v
        AI Analysis (model routing per task):
            - Summarize incident in plain English
            - Extract IOCs (IPs, domains, hashes, user accounts)
            - Map to MITRE ATT&CK tactics and techniques
            - Assess severity and confidence
            - Recommend response action
            |
            v
        Write to TimescaleDB: security_incidents
            |
            v
        Write to Postgres:second_brain resources table:
            Title: "[Severity] Incident: {short description}"
            Bucket: REFERENCE (facts about an event)
            Tags: security, argus, {tactic}, {technique}
            Metadata: {src_ip, target, iocs, mitre_mapping}
            Embedding: vector(768) for semantic search
            |
            v
        Mark source event: analyzed = true
            |
            v
        [severity = critical?]
            --> Immediate Telegram alert (see §7)
```

### 6.4 MITRE ATT&CK Integration

The MITRE ATT&CK Enterprise framework is embedded into the system as a queryable vector store:

```
Download ATT&CK STIX JSON (Enterprise)
    |
    v
Extract: technique ID, name, description, tactic, examples
    |
    v
Generate embeddings (nomic-embed-text) for each technique description
    |
    v
Store in Postgres:second_brain as REFERENCE bucket entries
    Tags: mitre, att&ck, {tactic}
    metadata: {technique_id, tactic, examples}
    |
    v
During incident analysis:
    Generate embedding for incident description
    Vector search → top 5 similar ATT&CK techniques
    AI confirms or rejects each match
    Confirmed techniques written to security_incidents.mitre_techniques[]
```

This enables both automatic mapping during analysis and semantic search — e.g. `/ask "What ATT&CK techniques have I observed in the last month?"`.

---

## 7. Argus Agent — Conversational Interface

Argus has a conversational personality accessible via Telegram. It is not just a notification relay — it is an interactive security assistant that can query data, explain events, and execute authorized response actions.

### 7.1 Personality

Argus is professional, precise, and explains its reasoning. It acknowledges uncertainty rather than guessing. It has a dry wit used very sparingly. Its signature phrases reflect the all-seeing namesake.

**Status closings:** "Standing watch." / "I remain vigilant." / "Monitoring continues."
**Uncertainty:** "Insufficient evidence to determine conclusively. Monitoring required."
**On being asked if it sleeps:** "Like my namesake, I never fully sleep."

### 7.2 Telegram Commands

| Command | Function |
|---------|----------|
| `/status` | Current network health; event counts; top concerns |
| `/alerts` | Recent high/critical alerts |
| `/investigate {ip or host}` | Full profile: recent activity, threat intel, assessment |
| `/search {query}` | Natural language semantic search across security_incidents via pgvector |
| `/ask {question}` | RAG Q&A over security incidents + Second Brain resources |
| `/top` | Top talkers by bandwidth (last hour) |
| `/quarantine {ip}` | Execute quarantine playbook (moves device to VLAN 66) |
| `/unquarantine {ip}` | Release device from VLAN 66 |
| `/incident {id}` | Full details on a specific security_incident |
| `/digest` | Trigger on-demand security digest |

### 7.3 Threat Assessment Response Format

```
[Threat Level: Low / Medium / High / Critical]
[Confidence: Low / Medium / High]

Summary: {1 sentence}

Evidence:
• {key data points}

MITRE ATT&CK:
• {Tactic}: {Technique ID} — {Technique Name}

Assessment: {reasoning}

Recommended Action: {specific action}
[Execute? Yes / No]
```

### 7.4 Daily Security Digest Format

```
Argus Daily Digest — {Date}

Overall Status: {1 sentence}

Statistics:
• Total events: {n}
• Blocked connections: {n}
• Critical alerts: {n}
• High-severity: {n}

Top Concerns:
1. {concern + brief context}
2. {concern + brief context}

Recommended Actions:
• {action}

Notable Events:
• {item}

All systems operational. I remain vigilant.
```

---

## 8. Quarantine Playbook

The quarantine system is an Ansible-powered automated response that moves a device to VLAN 66 (Sandbox) on command — either via Telegram or triggered automatically on confirmed critical threats.

```
Trigger: /quarantine {ip} OR automated critical alert
    |
    v
Validate: confirm IP is on a quarantinable VLAN (not Management/Lab)
    |
    v
Ansible playbook: quarantine.yml
    - Accept: IP address or MAC address
    - Identify current VLAN via pfSense API
    - Move device to VLAN 66 (Sandbox)
    - Apply firewall rule: allow internet, block all internal networks
    - Create monitoring alert for device in TimescaleDB
    - Log action to security_incidents table
    |
    v
Write incident to Postgres:second_brain
    Title: "Device Quarantined: {ip}"
    Bucket: REFERENCE
    Tags: security, quarantine, argus
    |
    v
Telegram confirmation:
    "Quarantine executed.
     Actions taken:
     1. Moved {ip} to VLAN 66 (Sandbox)
     2. Firewall: allow internet, block internal
     3. Incident: {INC-ID}
     Monitoring active. Alert on status change?"
```

**VLAN 66 (Sandbox) firewall policy:**
- Allow: internet-bound traffic (for continued observation)
- Block: all internal VLAN traffic
- Log: all connections to TimescaleDB for analysis

---

## 9. Scheduled Reports

These overlap with Second Brain scheduled reports. Argus contributes the security-specific content.

| Report | Schedule | Delivery | Contents |
|--------|----------|----------|----------|
| Argus Security Digest | Daily, 7:05 AM | Telegram | Yesterday's events; unresolved incidents; SIEM health check |
| Weekly Threat Summary | Sunday, 6:10 PM | Telegram | Week's incidents; top attacker IPs; MITRE tactics observed; trends vs. prior week |
| Monthly Security Report | 1st of month, 8:05 AM | Telegram + Notion page | Incident patterns; MITRE ATT&CK coverage; detection improvements; false positive rate |

---

## 10. Workflow Status

| Workflow / Component | Status | Notes |
|---------------------|--------|-------|
| Suricata (pfSense pkg) | Build fresh | Phase 3 |
| Crowdsec (pfSense pkg) | Build fresh | Phase 3 / 5 |
| Fail2ban (per host) | Build fresh | Phase 3 |
| Splunk Free deployment | Build fresh | Phase 3 |
| Wazuh Manager + agents | Build fresh | Phase 3 |
| Grafana deployment | Build fresh | Phase 3 |
| pfSense logs → Splunk | Build fresh | Phase 3 |
| Wazuh agents → Splunk | Build fresh | Phase 3 |
| Suricata alerts → Splunk | Build fresh | Phase 3 |
| Grafana → TimescaleDB dashboards | Build fresh | Phase 3 |
| Vector bulk log ingestion | Build fresh | Phase 3 |
| 5-min AI analysis workflow (n8n) | Build fresh | Phase 5 |
| MITRE ATT&CK embedding + mapping | Build fresh | Phase 5 |
| Argus Agent Telegram bot | Build fresh | Phase 5 |
| Quarantine Ansible playbook | Build fresh | Phase 5 |
| Uptime Kuma (external VPS) | Build fresh | Phase 5 |
| Scheduled security digests | Build fresh | Phase 5 |
| Splunk dashboards (portfolio) | Build fresh | Phase 6 |
| Attack simulation (from VLAN 66) | Build fresh | Phase 6 |

---

## 11. Portfolio Value

Argus is the primary technical differentiator for the CRDC application. The components map directly to SOC Analyst competencies:

| Argus Component | SOC Competency Demonstrated |
|----------------|---------------------------|
| Splunk + Wazuh deployment | SIEM administration; log management |
| pfSense + Suricata + Crowdsec | Network security monitoring; IDS/IPS |
| MITRE ATT&CK mapping | Threat intelligence; detection engineering |
| AI analysis pipeline | Emerging tech adoption; automation |
| Quarantine playbook | Incident response; automated containment |
| Semantic search over incidents | Advanced query techniques; pattern recognition |
| TimescaleDB schema | Data architecture for security operations |
| Full IaC deployment | Infrastructure as Code; repeatability |

**Resume line:**
> Designed and deployed "Argus," an AI-augmented homelab SIEM processing 10,000+ events/day across an 8-VLAN Zero Trust network. Integrated Splunk, Wazuh, Suricata, and local LLMs (Mistral 7B) for automated threat analysis, MITRE ATT&CK mapping, and conversational incident response via Telegram. Fully codified with Terraform + Ansible.

---

## 12. Deployment Order

Follows Phase 3 (SIEM Stack) and Phase 5 (Argus AI + DMZ) of the Project Roadmap.

**Phase 3 — SIEM Foundation:**
1. Deploy Splunk Free (10.0.50.20) via IaC
2. Deploy Wazuh Manager (10.0.50.21) via IaC
3. Deploy Grafana (10.0.50.22) via IaC
4. Configure Suricata on pfSense
5. Configure pfSense syslog → Splunk + TimescaleDB
6. Deploy Wazuh agents on 5+ endpoints
7. Configure Suricata alerts → Splunk
8. Build Grafana → TimescaleDB dashboards
9. Verify full log flow: source → collection → TimescaleDB + Splunk
10. Build initial Splunk dashboards (traffic by VLAN, top talkers, firewall blocks)

**Phase 5 — AI + Automation:**
11. Embed MITRE ATT&CK framework into second_brain pgvector
12. Build 5-minute AI analysis n8n workflow
13. Build Argus Agent Telegram bot + command handlers
14. Build Quarantine Ansible playbook
15. Configure Crowdsec (pfSense package) after DMZ is live
16. Configure Fail2ban on all SSH hosts + NPM
17. Provision external VPS; deploy Uptime Kuma
18. Build scheduled security digests

**Phase 6 — Portfolio:**
19. Build MITRE ATT&CK coverage Splunk dashboard
20. Run attack simulations from VLAN 66 (Sandbox)
21. Document detection and response for each simulation
22. Screenshot all dashboards; commit to GitHub

---

## 13. Infrastructure as Code

All Argus services are provisioned and configured via IaC. For the full workflow, conventions, secrets management, and recovery procedure, see the **IaC Runbook v1.0**.

### 13.1 Repository Location

```
homelab-command/
└── infrastructure/
    └── argus/
        ├── terraform/
        └── ansible/
```

### 13.2 Terraform — What Gets Provisioned

| Resource | IP | VMID | Notes |
|----------|----|------|-------|
| Splunk Free LXC | 10.0.50.20 | TBD | 4 vCPU, 8GB RAM, 100GB disk |
| Wazuh Manager LXC | 10.0.50.21 | TBD | 4 vCPU, 8GB RAM, 50GB disk |
| Grafana LXC | 10.0.50.22 | TBD | 2 vCPU, 2GB RAM, 20GB disk |

All containers are on VLAN 50 (Lab Services), provisioned using the `lxc-container` module.

```hcl
# infrastructure/argus/terraform/main.tf (abbreviated)

module "splunk" {
  source         = "../../modules/lxc-container"
  hostname       = "splunk"
  cores          = 4
  memory_mb      = 8192
  disk_gb        = 100
  vlan_id        = 50
  ip_address     = "10.0.50.20/24"
  gateway        = "10.0.50.1"
  lxc_template   = var.lxc_template
  proxmox_node   = var.proxmox_node
  ssh_public_key = var.ssh_public_key
}

module "wazuh" {
  source         = "../../modules/lxc-container"
  hostname       = "wazuh"
  cores          = 4
  memory_mb      = 8192
  disk_gb        = 50
  vlan_id        = 50
  ip_address     = "10.0.50.21/24"
  gateway        = "10.0.50.1"
  lxc_template   = var.lxc_template
  proxmox_node   = var.proxmox_node
  ssh_public_key = var.ssh_public_key
}

module "grafana" {
  source         = "../../modules/lxc-container"
  hostname       = "grafana"
  cores          = 2
  memory_mb      = 2048
  disk_gb        = 20
  vlan_id        = 50
  ip_address     = "10.0.50.22/24"
  gateway        = "10.0.50.1"
  lxc_template   = var.lxc_template
  proxmox_node   = var.proxmox_node
  ssh_public_key = var.ssh_public_key
}
```

**Note:** Suricata, Crowdsec, and Fail2ban are not Terraform-managed — Suricata and Crowdsec are pfSense packages; Fail2ban is deployed by Ansible directly on existing hosts as part of their respective roles.

### 13.3 Ansible — What Gets Configured

| Role | Target | Configures |
|------|--------|-----------|
| `splunk` | 10.0.50.20 | Splunk Free install, index definitions, forwarder inputs, admin account |
| `wazuh-manager` | 10.0.50.21 | Wazuh Manager install, agent registration, alert rules |
| `wazuh-agent` | All monitored hosts | Wazuh agent deploy and registration to Manager |
| `grafana` | 10.0.50.22 | Grafana install, TimescaleDB datasource, initial dashboards |
| `suricata` | pfSense (via SSH) | Rule set configuration, eve.json output, syslog forwarding |
| `fail2ban` | All SSH-exposed hosts | Jail configs, ban thresholds, syslog reporting |
| `syslog-ng` | TBD | Central log receiver, routing rules to Vector + Splunk |
| `vector` | TBD (same host as syslog-ng) | Bulk log ingestion pipeline to TimescaleDB |

### 13.4 Secrets (Ansible Vault)

The following secrets are stored in `infrastructure/argus/ansible/group_vars/all/vault.yml`:

```
vault_splunk_admin_password
vault_wazuh_api_password
vault_grafana_admin_password
vault_wazuh_agent_registration_password
```

### 13.5 Playbook Invocations

```bash
# Full initial deployment (Phase 3)
cd infrastructure/argus/terraform/
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with Proxmox credentials
terraform init && terraform apply

# Configure all Argus services
cd ../ansible/
# Update inventory.ini with IPs from Terraform output
ansible-playbook provision.yml --ask-vault-pass

# Deploy Wazuh agents to all monitored endpoints
ansible-playbook deploy-agents.yml --ask-vault-pass

# Ongoing maintenance
ansible-playbook update.yml --ask-vault-pass
```

### 13.6 Recovery

In a full homelab rebuild, Argus deploys in **Phase 4** of the recovery sequence (after Postgres, Redis, MinIO, Ollama, Whisper, and n8n). See IaC Runbook v1.0 §9 for the full ordered procedure.

Argus-specific post-recovery steps:
1. Verify TimescaleDB `argus_logs` schema is intact (restored with Postgres)
2. Re-register Wazuh agents on all endpoints (`deploy-agents.yml`)
3. Confirm Splunk is receiving pfSense logs (check `firewall` index)
4. Verify Grafana datasource connection to TimescaleDB
5. Confirm n8n AI analysis workflow is active (check scheduled trigger)

---

*Part of the Homelab Command Project. Companion documents: Hardware Catalog v1.1 · Network & Services Architecture v1.4 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
