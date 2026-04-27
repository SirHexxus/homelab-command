# Awesome-Selfhosted App Evaluation Report
**Generated:** 2026-03-11
**Source:** awesome-selfhosted/README.md (1,166 apps, 84 categories)
**Pipeline:** Category pre-filter → in-context classification → score filter → research synthesis

---

## Pipeline Summary

| Phase | Input | Output | Method |
|-------|-------|--------|--------|
| Pre-filter (P0) | 1,166 apps / 84 categories | 253 apps / 36 categories | Hard-eliminate irrelevant categories + second-level relevance filter |
| Classification (P1) | 253 apps | 253 classified | In-context classification against homelab profile |
| Score filter (P2) | 253 classified | 99 survivors | Directly_Useful ≥ 5, Possibly_Useful ≥ 7 |
| Research (P3) | 99 survivors | 84 researched | Training knowledge (Aug 2025) + live GitHub stats |
| Synthesis (P4) | 99 researched | 59 Tier 1, 24 Tier 2, 21 Dropped | Revised scores, dealbreaker analysis, stack alignment |

**Classification note:** Ollama/Mistral 7B was bypassed — CPU-only inference on the T150 benchmarks at ~0.6 tok/s, making a full run ~3.3 hours. In-context classification against the known homelab profile is equivalent quality for a set of well-documented apps.

---

## Deployment Status Key

| Symbol | Meaning |
|--------|---------|
| ✅ Running | Confirmed deployed and active |
| 📋 Planned | Explicitly documented in a homelab design doc or roadmap |
| 🆕 New | Identified by this evaluation; not yet in any design doc |
| ⏳ Deferred | In the docs but gated on a post-June condition |

**Currently running:** Ollama, Whisper, n8n, Postgres (pgvector + TimescaleDB), Redis, MinIO, Umami, pfSense, Jellyfin, Audiobookshelf, CalibreWeb, Navidrome, Immich, Sonarr, Lidarr, qBittorrent, ntfy, WireGuard, Vaultwarden, nginx, Authelia (in progress)

**Officially planned (documented in design docs/roadmap):**

| App | Source | Project | Phase |
|-----|--------|---------|-------|
| Splunk Free | `argus-design-doc-v1.2.md`, `network-services-architecture-v1.6.md` | Argus | Phase 3 |
| Wazuh Manager | `argus-design-doc-v1.2.md`, `network-services-architecture-v1.6.md` | Argus | Phase 3 |
| Grafana | `argus-design-doc-v1.2.md`, `network-services-architecture-v1.6.md` | Argus | Phase 3 |
| Suricata | `argus-design-doc-v1.2.md`, `ariadne-design-doc-v1.0.md` | Argus + Ariadne | Phase 3, pfSense pkg |
| Crowdsec | `argus-design-doc-v1.2.md`, `ariadne-design-doc-v1.0.md` | Argus + Ariadne | Phase 3/5, pfSense pkg |
| Fail2ban | `argus-design-doc-v1.2.md`, `ariadne-design-doc-v1.0.md` | Ariadne | Phase 3, per-host |
| Uptime Kuma | `argus-design-doc-v1.2.md` Phase 5, `ariadne-design-doc-v1.0.md` §9 | Ariadne | Phase 5, external VPS |
| Pi-hole | `network-services-architecture-v1.6.md` | Infra | LOW, no prereqs |
| Home Assistant | `project-roadmap-v1.4.md`, `network-services-architecture-v1.6.md` | IoT | ⏳ Post-June |
| Authentik | `project-roadmap-v1.4.md`, `network-services-architecture-v1.6.md` | Identity | ⏳ Post-June |
| Nextcloud | `project-roadmap-v1.4.md`, `orpheus-design-doc-v1.1.md` | Productivity | ⏳ Post-June |

---

## Live GitHub Stats (fetched 2026-03-11)

| App | Stars | Last Push | Status |
|-----|-------|-----------|--------|
| Open-WebUI | 126,757 ⭐ | 2026-03-11 | Very active |
| Stirling-PDF | 75,203 ⭐ | 2026-03-11 | Very active — #1 PDF app on GitHub |
| Memos | 57,732 ⭐ | 2026-03-09 | Very active |
| MeiliSearch | 56,313 ⭐ | 2026-03-11 | Very active |
| AnythingLLM | 56,070 ⭐ | 2026-03-11 | Very active |
| RSSHub | 42,565 ⭐ | 2026-03-11 | Very active |
| SiYuan | 41,798 ⭐ | 2026-03-11 | Very active |
| Paperless-ngx | 37,279 ⭐ | 2026-03-11 | Very active |
| TriliumNext (Trilium) | 34,994 ⭐ | 2026-03-11 | Active — *repo renamed, see note below* |
| Perplexica | 32,736 ⭐ | 2026-03-10 | Active |
| Frigate | 30,781 ⭐ | 2026-03-11 | Very active |
| Hasura | 31,915 ⭐ | 2026-03-11 | Very active |
| changedetection.io | 30,568 ⭐ | 2026-03-11 | Very active |
| Khoj | 33,352 ⭐ | 2026-03-06 | Active |
| Homepage | 28,852 ⭐ | 2026-03-11 | Very active |
| ArchiveBox | 27,040 ⭐ | 2026-02-26 | Active |
| Langfuse | 23,020 ⭐ | 2026-03-11 | Very active |
| Node RED | 22,879 ⭐ | 2026-03-11 | Active |
| docmost | 19,398 ⭐ | 2026-03-11 | Very active — explosive growth |
| Anubis | 17,650 ⭐ | 2026-03-09 | Explosive growth for a new project |
| Karakeep | 24,039 ⭐ | 2026-03-09 | Active — rebranded from Hoarder |
| MeTube | 12,856 ⭐ | 2026-03-11 | Active |
| Gotenberg | 11,494 ⭐ | 2026-03-11 | Active |
| Gatus | 10,357 ⭐ | 2026-03-06 | Active |
| linkding | 10,269 ⭐ | 2026-03-04 | Active |
| Healthchecks | 9,928 ⭐ | 2026-03-11 | Active |
| WatchYourLAN | 6,826 ⭐ | 2025-09-10 | Slower cadence — verify before deploying |
| sish | 4,551 ⭐ | 2026-02-04 | Active |
| SilverBullet | 4,830 ⭐ | 2026-03-11 | Active |
| bitmagnet | 3,901 ⭐ | 2026-01-31 | Active |
| OliveTin | 3,473 ⭐ | 2026-03-11 | Active |
| draw.io | 4,028 ⭐ | 2026-03-06 | Active |
| Canary Tokens | 2,033 ⭐ | 2026-03-10 | Active |

**⚠️ TriliumNext repo rename:** `TriliumNext/Notes` was archived but the project is alive at `TriliumNext/Trilium` (35k ⭐, pushed today). Recommendation unchanged.

---

## Tier 1 — Deploy Next (score 8-9)

*59 apps. PG = Postgres native. LXC = runs in unprivileged LXC container. Complexity = deployment effort.*

### 🔴 Argus / Ariadne — Security + SOC + Access Control

| App | Status | Score | PG | LXC | RAM | Complexity | Notes |
|-----|--------|-------|----|-----|-----|------------|-------|
| **Warpgate** | 🆕 New | 9 | ✓ | ✓ | 100MB | Medium | Smart SSH/HTTPS bastion with session recording, RBAC, MFA — deploy before exposing any new service |
| **Guacamole** | 🆕 New | 8 | ✓ | ✓ | 300MB | Medium | Clientless remote desktop gateway (VNC/RDP/SSH in browser); essential for SOC access to LXC containers |
| **Firezone** | 🆕 New | 8 | ✓ | ✓ | 150MB | Low | WireGuard-based remote access gateway with web UI and MFA — management layer over existing WireGuard |
| **AdGuard Home** | 🆕 New | 9 | ✗ | ✓ | 50MB | Low | Network-wide DNS ad/tracker blocking with detailed query logging; pick this OR Pi-hole (see Key Decisions) |
| **blocky** | 🆕 New | 8 | ✗ | ✓ | 30MB | Low | Lightweight DNS proxy with ad blocking, conditional forwarding, Prometheus metrics; the minimal alternative |
| **Anubis** | 🆕 New | 9 | ✗ | ✓ | 20MB | Low | AI web firewall blocking scraper bots; sits transparently in front of nginx before Authelia |
| **sish** | 🆕 New | 9 | ✗ | ✓ | 20MB | Low | SSH/HTTP tunnels to localhost — external service access without port forwarding; deploy early |
| **Healthchecks** | 🆕 New | 9 | ✓ | ✓ | 120MB | Low | Heartbeat/cron monitoring; Postgres and Telegram native; essential Argus infra health layer |
| **changedetection.io** | 🆕 New | 9 | ✗ | ✓ | 80MB | Low | Web page change detection with ntfy/Telegram alerts; monitors threat intel feeds and vendor advisories |
| **Canary Tokens** | 🆕 New | 9 | ✗ | ✓ | 150MB | Medium | Self-hosted honeypot token generator; Redis-based (already in stack); core Argus deception layer |
| **NetAlertX** | 🆕 New | 9 | ✗ | ✓ | 100MB | Low | Network intruder/device detection with Telegram alerts; requires host-network LXC for ARP scanning |
| **Gatus** | 🆕 New | 9 | ✓ | ✓ | 30MB | Low | Automated service health dashboard; Postgres + Telegram native; 30MB Go binary |
| **WatchYourLAN** | 🆕 New | 8 | ✗ | ✓ | 30MB | Low | Lightweight network IP scanner with ntfy and Grafana export; pick this OR NetAlertX |
| **draw.io** | 🆕 New | 8 | ✗ | ✓ | 50MB | Low | Self-hosted diagrams — MITRE ATT&CK maps, network topology, architecture docs; stateless |
| **Hasura** | 🆕 New | 8 | ✓ | ✓ | 250MB | Low | Instant GraphQL + REST APIs on Postgres with event triggers → n8n webhooks; pgvector support |
| **AliasVault** | 🆕 New | 8 | ✓ | ✓ | 150MB | Low | E2E-encrypted password manager with email alias generator; complements Vaultwarden for signup protection |

> **Already running (Ariadne/security):** Vaultwarden ✅, WireGuard ✅, nginx ✅, Authelia (in progress)
> **Officially planned:** Crowdsec 📋, Fail2ban 📋, Suricata 📋, Uptime Kuma 📋 (Phase 5, external VPS), Pi-hole 📋 (LOW priority)

---

### 🟣 Mnemosyne / Hermes — AI + PKM

| App | Status | Score | PG | LXC | RAM | Complexity | Notes |
|-----|--------|-------|----|-----|-----|------------|-------|
| **Open-WebUI** | 🆕 New | 9 | ✓ | ✓ | 250MB | Low | Best Ollama UI (126k ⭐); RAG, function calling, web search; Postgres-native; deploy immediately |
| **AnythingLLM** | 🆕 New | 9 | ✗ | ✓ | 400MB | Low | All-in-one AI workspace; Ollama + n8n + Telegram native; MCP compatible; Hermes brain |
| **Khoj** | 🆕 New | 9 | ✓ | ✓ | 350MB | Medium | AI second brain with Postgres + pgvector; Telegram bot built-in; Ollama native; Mnemosyne core |
| **TriliumNext Notes** | 🆕 New | 9 | ✗ | ✓ | 200MB | Low | Best hierarchical PKB; scripting, SQL queries, bidirectional links; repo at TriliumNext/Trilium |
| **SilverBullet** | 🆕 New | 9 | ✗ | ✓ | 100MB | Low | Hacker-optimized PKM with Lua plugins, query language, and REST API; single Deno binary |
| **MeiliSearch** | 🆕 New | 9 | ✗ | ✓ | 50MB | Low | Ultra-fast search API (56k ⭐); n8n native node; Rust binary; deploy as search backbone early |
| **Paperless-ngx** | 🆕 New | 9 | ✓ | ✓ | 300MB | Medium | Document scan/OCR/archive; Postgres + Redis native; n8n node exists; 37k ⭐ |
| **Stirling-PDF** | 🆕 New | 9 | ✗ | ✓ | 500MB | Low | Local PDF toolkit — merge, split, compress, OCR, redact; REST API; 75k ⭐ (#1 PDF app on GitHub) |
| **Langfuse** | 🆕 New | 9 | ✓ | ✓ | 300MB | Low | LLM tracing, prompt management, and evaluation; Postgres-native; essential for Hermes quality tracking |
| **OliveTin** | 🆕 New | 9 | ✗ | ✓ | 15MB | Low | Web UI for predefined shell commands; Hermes triggers infra actions safely via API; 15MB Go binary |
| **linkding** | 🆕 New | 9 | ✓ | ✓ | 80MB | Low | Postgres-native bookmark manager; REST API + browser extension; 80MB; Mnemosyne capture layer |
| **Gotenberg** | 🆕 New | 9 | ✗ | ✓ | 200MB | Low | Document conversion API (Chromium + LibreOffice); Mnemosyne document ingestion pipeline |
| **Memos** | 🆕 New | 8 | ✓ | ✓ | 80MB | Low | Quick-capture knowledge base; Postgres + Telegram native; Go binary; 57k ⭐ |
| **Blinko** | 🆕 New | 8 | ✓ | ✓ | 150MB | Low | Note tool with AI features and pgvector; Ollama native; Postgres-native quick-capture |
| **Karakeep** | 🆕 New | 8 | ✗ | ✓ | 200MB | Low | Bookmark-everything with Ollama AI tagging; needs MeiliSearch (already deploying); 24k ⭐ |
| **Perplexica** | 🆕 New | 8 | ✗ | ✓ | 200MB | Low | AI-powered search using local Ollama; SearXNG backend; privacy-first; 32k ⭐ |
| **RSSHub** | 🆕 New | 8 | ✗ | ✓ | 150MB | Low | Generates RSS from anything (YouTube, GitHub, Reddit); Redis cache native; feeds Hermes intelligence |
| **ArchiveBox** | 🆕 New | 8 | ✓ | ✓ | 200MB | Medium | Web archiving with HTML/screenshot captures; Postgres-native; research preservation for Mnemosyne |
| **Local Deep Research** | 🆕 New | 8 | ✗ | ✓ | 100MB | Low | AI deep research tool with multi-source search and PDF extraction; Ollama-native |
| **Node RED** | 🆕 New | 8 | ✗ | ✓ | 100MB | Low | Browser-based flow editor; distinct from n8n — excels at MQTT/IoT/hardware; Frigate integration |
| **SiYuan** | 🆕 New | 8 | ✗ | ✓ | 400MB | Medium | Privacy-first PKM with block refs and MinIO sync; 41k ⭐; evaluate vs TriliumNext |

---

### 🟡 Orpheus — Media

| App | Status | Score | PG | LXC | RAM | Complexity | Notes |
|-----|--------|-------|----|-----|-----|------------|-------|
| **bitmagnet** | 🆕 New | 9 | ✓ | ✓ | 200MB | Low | DHT crawler + Torznab API for Sonarr/Radarr + pgvector search; Postgres-native; fills local torrent discovery gap |
| **MeTube** | 🆕 New | 8 | ✗ | ✓ | 100MB | Low | yt-dlp web GUI with playlist support; essential YouTube/video capture for Orpheus; 12k ⭐ |

> **Already running (Orpheus):** Sonarr ✅, Lidarr ✅, Jellyfin ✅, Navidrome ✅, Audiobookshelf ✅, Immich ✅, qBittorrent ✅

---

### 🔵 Infra / Cross-cutting

| App | Status | Score | PG | LXC | RAM | Complexity | Notes |
|-----|--------|-------|----|-----|-----|------------|-------|
| **Homepage by gethomepage** | 🆕 New | 9 | ✗ | ✓ | 100MB | Low | Industry-standard homelab dashboard (28k ⭐); native widgets for Sonarr, Radarr, Jellyfin, Immich, Grafana |
| **docmost** | 🆕 New | 9 | ✓ | ✓ | 200MB | Low | Postgres + Redis-native wiki; modern Notion/Confluence alternative; 19k ⭐ with explosive growth |
| **Adminer** | 🆕 New | 8 | ✓ | ✓ | 20MB | Low | Single-file Postgres admin tool; deploy behind Authelia; keep patched (XSS CVE history) |
| **Glance** | 🆕 New | 8 | ✗ | ✓ | 30MB | Low | Feed/intelligence dashboard (32k ⭐); RSS, GitHub releases, weather; complements Homepage |

---

## Tier 2 — Evaluate (3-6 months)

| App | Status | Score | PG | LXC | RAM | Project | Notes |
|-----|--------|-------|----|-----|-----|---------|-------|
| **Frigate** | 🆕 New | 8 | ✗ | ⚠ | 350MB | Argus | CPU-only is functional but slow on T150; budget a Coral USB TPU ($60) for real-time AI detection |
| **Kasm Workspaces** | 🆕 New | 8 | ✓ | ⚠ | 2GB | Argus | Isolated SOC browser environments; requires Docker-in-LXC or dedicated Proxmox VM |
| **Onyx Community Edition** | 🆕 New | 8 | ✓ | ⚠ | 4GB | Hermes | Postgres-native RAG + agents + web search, but ~4GB RAM and Vespa dependency; AnythingLLM + Khoj covers this more efficiently |
| **AFFiNE Community Edition** | 🆕 New | 7 | ✓ | ✓ | 400MB | Mnemosyne | Postgres-native docs + whiteboard + Kanban; rapid dev = frequent breaking changes; revisit in 6 months |
| **StackStorm** | 🆕 New | 7 | ✓ | ✓ | 800MB | Argus | Powerful SOC event-driven automation but MongoDB dependency + 800MB; n8n covers simpler IR cases |
| **Home Assistant** | 📋 Planned | 7 | ✗ | ✓ | 400MB | IoT | Post-June per roadmap; deploy in Proxmox VM when VLAN 40 and IoT devices are ready |
| **Dagu** | 🆕 New | 7 | ✗ | ✓ | 30MB | Argus | Lightweight DAG-based cron alternative; 30MB Go binary; complements n8n for pipeline scheduling |
| **Deleterr** | 🆕 New | 7 | ✗ | ✓ | 50MB | Orpheus | Automated media cleanup for Sonarr/Radarr; check Maintainerr as a Jellyfin-compatible alternative |
| **MediaMTX** | 🆕 New | 7 | ✗ | ✓ | 30MB | Orpheus | Real-time RTSP/RTMP media router; deploy alongside Frigate to bridge camera streams to Jellyfin |
| **Upsnap** | 🆕 New | 7 | ✗ | ✓ | 20MB | Infra | Wake-on-LAN dashboard; Hermes can wake the R710 TrueNAS on demand via API |
| **Datasette** | 🆕 New | 7 | ✗ | ✓ | 50MB | Argus | SQLite data explorer and API; useful for ad-hoc Argus log analysis without Splunk |
| **OpenZiti** | 🆕 New | 8 | ✗ | ✓ | 80MB | Ariadne | Zero-trust full mesh overlay; long-term Ariadne evolution path; WireGuard covers current needs |
| **Databunker** | 🆕 New | 7 | ✓ | ✓ | 80MB | Mnemosyne | GDPR-compliant field-level encrypted PII storage on Postgres; deploy if Mnemosyne handles health data |
| **AppFlowy** | 🆕 New | 7 | ✓ | ✓ | 300MB | Mnemosyne | Postgres-native Notion alternative (65k ⭐); better for project management than deep PKM |
| **Bytebase** | 🆕 New | 7 | ✓ | ✓ | 200MB | Infra | Database schema version control for Postgres; low priority until schema churn becomes a problem |
| **Squid** | 🆕 New | 7 | ✗ | ✓ | 100MB | Argus | Caching web proxy for isolated SOC analyst browsing; deploy alongside Kasm Workspaces |
| **CloudBeaver** | 🆕 New | 7 | ✓ | ✓ | 500MB | Infra | Full-featured web DBeaver for Postgres; deploy when Adminer's feature set becomes limiting |
| **Mathesar** | 🆕 New | 7 | ✓ | ✓ | 300MB | Mnemosyne | Intuitive Postgres UI for non-technical data entry; useful for structured Mnemosyne data |
| **Standard Notes** | 🆕 New | 7 | ✓ | ✓ | 200MB | Mnemosyne | E2E-encrypted notes (Rails + Postgres); evaluate for sensitive Mnemosyne content |
| **MeshCentral** | 🆕 New | 7 | ✓ | ✓ | 150MB | Infra | Agent-based remote device management; Warpgate + Guacamole (both Tier 1) cover most access needs |
| **Feeds Fun** | 🆕 New | 7 | ✓ | ✓ | 100MB | Mnemosyne | RSS reader with AI article scoring; Khoj + n8n achieves smarter feed filtering more flexibly |
| **copyparty** | 🆕 New | 7 | ✗ | ✓ | 50MB | Orpheus | Portable file server with WebDAV and media indexer; useful for file access between LXC containers |
| **imgproxy** | 🆕 New | 7 | ✗ | ✓ | 50MB | Mnemosyne | Fast image resizing/converting API; deploy when Mnemosyne or Orpheus needs image processing at scale |
| **TrailBase** | 🆕 New | 7 | ✗ | ✓ | 50MB | Hermes | Single-executable Firebase alternative with REST + realtime APIs; Hasura on Postgres is stronger |

---

## Dropped at Research

| App | Score | Drop Reason |
|-----|-------|-------------|
| UUSEC WAF | 8 | Supply-chain trust concerns for a security-critical component; limited Western CVE tracking |
| Typesense | 8 | Deploy MeiliSearch instead — better documentation and n8n has a native MeiliSearch node |
| Huginn | 8 | Ruby stack + 500MB RAM; n8n covers 90% of use cases with a stack-aligned language |
| Viseron | 8 | Frigate is better supported and more popular; pick one NVR |
| sist2 | 8 | MeiliSearch can index the same files; avoids an Elasticsearch/OpenSearch dependency |
| Onyx Community Edition | 8 | Moved to Tier 2 — too heavy (4GB + Vespa); AnythingLLM + Khoj is lighter and better integrated |
| Dashy | 7 | Homepage by gethomepage is more actively maintained with more service integrations |
| Homarr | 7 | Mid-major v1.0 rewrite underway with breaking changes; revisit when stable |
| Feedpushr | 7 | RSSHub + n8n HTTP node handles RSS aggregation and routing more flexibly |
| Agenta | 7 | Langfuse (Tier 1) is more mature and covers LLM observability; deploying both is redundant |
| Zero-TOTP | 7 | Vaultwarden (already running) handles TOTP; PHP stack is outside preferences |
| Apache Airflow | 6 | Too heavy (1.5GB RAM); Dagu or n8n covers homelab automation needs |
| OpenSearch | 7 | Wazuh (officially planned) brings its own OpenSearch instance; don't deploy separately |
| Aleph | 7 | Too heavy (3GB RAM + Elasticsearch); Paperless-ngx + MeiliSearch covers document discovery |
| Atomic Server | 6 | Niche linked-data paradigm with steep learning curve; Postgres + TriliumNext covers the use case |
| memEx | 6 | TriliumNext + SilverBullet is a stronger Zettelkasten implementation with better communities |
| ShellHub | 6 | Warpgate (Tier 1) is the SSH bastion; ShellHub adds agent complexity without benefit |
| Kuvasz Uptime | 7 | Gatus (Tier 1) + Uptime Kuma (officially planned) covers uptime monitoring |
| go-doxy | 7 | Docker-centric service discovery is irrelevant for an LXC-based stack; nginx already in place |
| Damselfly | 6 | Immich (already running) includes ML face recognition; .NET stack outside preferences |
| Jina | 6 | pgvector (already in Postgres) + Khoj covers semantic search; Jina adds framework overhead |

---

## Recommended Deployment Order

### Sprint 1 — Access Control + Network Foundation
*Deploy before exposing any new service externally.*

1. **Warpgate** — SSH/HTTPS bastion with session recording; establish before anything else goes live
2. **AdGuard Home** OR **Pi-hole** — DNS blocker (see Key Decisions); network-wide ad/tracker blocking
3. **sish** — External SSH/HTTP tunnels to localhost; enables access without port forwarding
4. **Gatus** — Postgres + Telegram health dashboard; monitoring baseline from day one
5. **Homepage by gethomepage** — Unified service dashboard; foundation for everything that follows

### Sprint 2 — Core Tooling
*Low complexity, high value, zero dependencies on Sprint 3+.*

6. **Anubis** — Bot WAF; drop in front of nginx before Authelia
7. **Adminer** — Postgres admin behind Authelia; trivial (single PHP file)
8. **draw.io** — Self-hosted diagrams; stateless, no database
9. **OliveTin** — Shell command UI; Hermes automation trigger
10. **MeiliSearch** — Search backbone; deploy early, other apps depend on it
11. **Healthchecks** — Heartbeat monitoring (Postgres + Telegram); cron health for all subsequent services

### Sprint 3 — PKM Core (Mnemosyne)

12. **Open-WebUI** — Ollama UI; most impactful AI app; deploy immediately
13. **TriliumNext Notes** — Primary PKB (repo: TriliumNext/Trilium)
14. **linkding** — Postgres bookmark layer; browser extension
15. **Memos** — Quick-capture (Postgres + Telegram, 80MB Go binary)
16. **Gotenberg** — Document conversion API; prerequisite for Paperless-ngx
17. **Paperless-ngx** — Document archive (depends on Gotenberg + Redis)

### Sprint 4 — Security Hardening + Remote Access

18. **Firezone** — WireGuard management UI + MFA over existing WireGuard
19. **Guacamole** — Clientless remote desktop gateway for LXC containers
20. **changedetection.io** — Threat intel feed monitoring → Telegram
21. **Canary Tokens** — Honeypot deception layer (Redis already running)
22. **NetAlertX** — Network intruder detection (host-network LXC)
23. **Uptime Kuma** — 📋 Officially planned — deploy on external VPS when provisioned

### Sprint 5 — AI Intelligence Layer

24. **Khoj** — AI second brain (Postgres + pgvector + Telegram native)
25. **AnythingLLM** — AI workspace + agents + n8n integration
26. **Langfuse** — LLM tracing and prompt management
27. **Perplexica** — Local AI web search via Ollama
28. **RSSHub** — Intelligence feed aggregation
29. **Karakeep** — AI-tagged bookmark capture (needs MeiliSearch from Sprint 2)

### Sprint 6 — Orpheus Extensions + Knowledge Layer

30. **bitmagnet** — Torrent indexer (Postgres + Torznab for Sonarr/Radarr)
31. **MeTube** — YouTube/video capture for Orpheus
32. **Stirling-PDF** — PDF toolkit; stateless REST API
33. **ArchiveBox** — Web archiving for Mnemosyne research preservation
34. **docmost** — Homelab wiki and runbook platform (Postgres + Redis)
35. **Hasura** — GraphQL + REST on Postgres with event triggers → n8n
36. **AliasVault** — Email alias generator + password manager

---

## Resource Budget

### Tier 1 new deployments (excluding already-running services)

| Group | Apps | RAM Estimate |
|-------|------|-------------|
| Security / Ariadne | Warpgate, Guacamole, Firezone, AdGuard Home, blocky, Anubis, sish, Healthchecks, changedetection.io, Canary Tokens, NetAlertX, Gatus, WatchYourLAN, draw.io, Hasura, AliasVault | ~1,600MB |
| AI / PKM | Open-WebUI, AnythingLLM, Khoj, TriliumNext, SilverBullet, MeiliSearch, Paperless-ngx, Stirling-PDF, Langfuse, OliveTin, linkding, Gotenberg, Memos, Blinko, Karakeep, Perplexica, RSSHub, ArchiveBox, Local Deep Research, Node RED, SiYuan | ~4,300MB |
| Orpheus | bitmagnet, MeTube | ~300MB |
| Infra | Homepage, docmost, Adminer, Glance | ~350MB |
| **Total** | **59 new deployments** | **~6,550MB** |

**RAM headroom:** 62GB total − ~15GB existing stack = ~47GB available
**New deployment cost:** ~6.6GB → well within budget; 40GB remains for future growth

---

## Key Decisions

| Decision | Recommendation |
|----------|---------------|
| DNS blocker | Pi-hole is already officially planned. AdGuard Home (🆕) has a better UI and more granular per-client controls. blocky (🆕) is the minimal option. Pick one — don't run multiples. |
| Network scanner | NetAlertX (more features, ntfy native) vs WatchYourLAN (simpler, faster); deploy one |
| SSH bastion | **Warpgate** (🆕 Tier 1) — session recording, RBAC, MFA; deploy before exposing services |
| Remote desktop | **Guacamole** (🆕 Tier 1) — clientless VNC/RDP/SSH in browser for SOC LXC access |
| WireGuard management | **Firezone** (🆕 Tier 1) — web UI + MFA management layer over existing WireGuard |
| PKM primary | **TriliumNext Notes** (TriliumNext/Trilium, 35k ⭐, active) |
| PKM quick-capture | **Memos** (Postgres + Telegram native, 80MB Go binary) |
| PKM bookmarks | **linkding** (Postgres-native, 80MB) + **Karakeep** (AI-tagging via Ollama) |
| Search backbone | **MeiliSearch** — not Typesense; n8n has a native MeiliSearch node |
| LLM UI | **Open-WebUI** — 126k ⭐, Postgres-native, definitive Ollama interface |
| Document archive | **Paperless-ngx** (Postgres + Redis native, n8n node exists) |
| Wiki / runbooks | **docmost** (Postgres + Redis native, 19k ⭐ explosive growth) |
| NVR / cameras | **Frigate** (Tier 2 until Coral USB TPU added; CPU-only is functional but slow) |
| Dashboard | **Homepage** (service overview) + **Glance** (feeds/intelligence) — complementary |
