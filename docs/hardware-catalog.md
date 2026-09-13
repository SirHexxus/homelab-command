# Homelab Command — Hardware Catalog
**Version:** 1.3
**Last Updated:** 2026-09-09
**Status:** Active document — update as hardware is added, removed, or changed.

---

## Servers & Primary Compute

| Device | Make/Model | Specs | Current Status | Notes |
|---|---|---|---|---|
| Proxmox Server | Dell EMC PowerEdge T150 | Intel Xeon E-2378, 62GB RAM, eno8303 (WAN NIC), eno8403 (LAN NIC) | **Active — Primary compute host** | Running pfSense VM + LXC containers. GPU slot available; RTX 3060 12GB or Intel Arc B580 planned. vmbr0 (WAN bridge), vmbr1 (VLAN-aware LAN bridge) |
| NAS Server | Dell PowerEdge R710 | Dual Intel Xeon X5650 @ 2.67GHz (24 threads), 94.4 GiB ECC RAM, general_pool (4x 3TB SAS RAIDZ, ~7.8TB raw, 4.79TB free), ssd_pool (1TB SSD, 820GB free), 4x NICs | **Active — Online at 10.0.10.30** | TrueNAS Scale 25.10.1 (Goldeye). VLAN 10 (Management). Static IP 10.0.10.30 (eno1). Hostname: truenas-r710. NICs: eno1=00:26:b9:55:a7:6d, eno2=00:26:b9:55:a7:6f, eno3=00:26:b9:55:a7:71, eno4=00:26:b9:55:a7:73 |

---

## Networking Equipment

| Device | Make/Model | Current Status | Notes |
|---|---|---|---|
| Firewall/Router | pfSense (VM on Proxmox T150) | **Active** | WAN on vmbr0, LAN on vmbr1. Managing VLANs 10/20/30/50. |
| Managed Switch | TP-Link T1600G-28PS | **Active** at 10.0.10.50 | Trunk on Port 1 to Proxmox. LACP-capable. |
| WiFi AP (Primary) | eero Pro 6 (Model K010011) | **Active** at 10.0.20.100 | Bridge mode, VLAN 20 (Trusted). Tri-band WiFi 6, dual 1Gbps ports. SSID: "HUGE Tracts of LAN" |
| WiFi AP (Reserve) | eero Pro 6 | **Idle — In reserve** | Same model as primary. Could serve as second AP for coverage expansion or mesh node. |
| IoT Hub | YoLink YS1603-UC | **Active** at 10.0.10.65 | Front gate detection only. Firmware 0383. Home Assistant integration planned. |

---

## Personal Computers & Endpoints

| Device | Make/Model | OS | Current Status | Notes |
|---|---|---|---|---|
| James's Laptop | Lenovo ThinkPad T590 | Debian 13 (XFCE) | **Active** | Primary admin workstation. Wired: 10.0.10.x, WiFi: 10.0.20.103 |
| James's Phone | Samsung Galaxy S24 FE | Android | **Active** at 10.0.20.104 | |
| Wife's Laptop | HP Pavilion x360 Convertible 15-cr0091ms | Windows 11 (Linux migration planned) | **Active** at 10.0.20.101 (hostname: DESKTOP-PRSIJDR) | Convertible touchscreen. OS migration to Debian or Ubuntu under consideration. |
| Wife's Phone | Samsung Galaxy S23 FE | Android | **Active** at 10.0.20.105 | |
| Nintendo Switch | Nintendo Switch | — | **Active** — WiFi | Connects over WiFi (eero SSID 1 → VLAN 20). Prior entry showing 10.0.10.58 on the management LAN was incorrect. Wired to HDMI 2 on the living-room TV. |
| Living Room TV | VIZIO VQD65R-1010 | SmartCast (slated for removal) | **Active** | 65" Quantum QLED, 2024. Serial LMVU19AC0802012, Material 10258020055. 120V/2.8A (~336W). Dolby Vision, Dolby Audio, DTS:X, DTS Virtual:X. I/O: 3× HDMI (HDMI 1 = eARC), optical audio out, ATSC antenna, USB 2.0 (1A). Assume 60Hz. Target panel for the HTPC project — to be network-isolated and driven as a dumb display. |
| Spare TV | TCL 65S450G | Google TV / Android TV OS 11 | **Idle — Spare** | Confirmed 65" from physical label (was catalogued as 75S450G, inferred from firmware string V8-R51MT08-LF1V058.021060 — size was a guess and was wrong). 120V/145W. Dolby Vision, Dolby Atmos, DTS-HD. Replaced as living-room TV; retired for parental-control bypass (child reached YouTube past configured locks), not a hardware fault. Earmarked for the Phase 2 office deployment (gaming-focused). |
| Work Device | Unknown make/model | Unknown | **Active** on VLAN 30 | Isolated on 10.0.30.0/24. Managed for network isolation only. |
| Jared's Laptop | ASUS ROG Flow X13 | Unknown | **Trusted guest** | Close friend, trusted network access. |

---

## Single-Board Computers & Microcontrollers

| Device | Make/Model | Qty | Current Status | Notes |
|---|---|---|---|---|
| SBC | Raspberry Pi 2 | 1 | **Idle — Undeployed** | Candidate for sensor node or lightweight service |
| SBC | Raspberry Pi 3 | 1 | **Idle — Undeployed** | Candidate for Pi-hole, Home Assistant, or PiKVM (borderline capable) |
| Microcontroller | Arduino Uno | 2-3 | **Idle — Undeployed** | Candidate for Home Assistant sensor/automation nodes |

---

## IoT & Home Automation (Reserve)

| Device | Make/Model | Qty | Current Status | Notes |
|---|---|---|---|---|
| Door Sensors | YoLink (model unknown) | 2 | **Idle — In reserve** | Undeployed. Will integrate with YoLink hub and Home Assistant when HA project begins. |
| Smart Switches | Unknown brand (Chinese manufacturer, in-outlet type) | Several | **Idle — In reserve** | Brand unknown — check label on device. Compatibility with Home Assistant TBD pending brand identification. |

---

## Undeployed Laptops & Small Servers

| Device | Make/Model | Last Known State | Notes |
|---|---|---|---|
| Laptop 1 | Apple MacBook Pro (A1286) | Functional — runs Debian | No HDD/SSD installed. Too old for macOS. Runs Debian passably. Candidate for lightweight server with SSD added. |
| Laptop 2 | Acer ES1-511-C0DV | Unknown | Reasonable physical condition. Specs/functionality unknown. |
| Laptop 3 | HP TPN-C125 | Functional but slow | Former daily driver (Windows 8.1 era). Too slow for dev work. Lightweight server candidate with built-in battery UPS. |
| Laptop 4 | Dell P57G001 | Unknown | Functionality unknown. |
| Laptop 5 | Dell Inspiron P125G002 | Unknown | Functionality unknown. |
| Tablet/Hybrid | Microsoft Surface Pro | Unknown — cannot test | 256GB storage. No charger available. Cannot assess until charger sourced. |
| Helm Server V2 | Helm HPS20-1T-W-US | **Active — Armbian deployed. Static IP reserved.** | Hexacore ARM (2x Cortex-A72 1.8GHz + 4x Cortex-A53 1.4GHz), 1TB NVMe. **Role: ntfy notification broker (IaC-ready; provisioning pending); Phase 3: syslog-ng + Vector log collector for Argus.** Static IP: 10.0.10.25 (VLAN 10). MAC: 72:c6:b9:0d:32:ac. Hostname: helm-log. See Network & Services Architecture v1.6 for placement. |
| Helm Server V1 | Helm HPS10-128-W-US | **Idle — Needs reflashing** | ARM SoC (2016-era), 2GB ECC RAM, 128GB NVMe. Limited capability. Best suited for single lightweight purpose. Armbian repurpose path available. USB-C charger available. |

---

## Open Items & Deferred Tasks

- [ ] Confirm smart switch brand (check label on device)
- [x] Confirm TV model — living room is VIZIO VQD65R-1010; spare is TCL **65S450G** (2026-09-09, from physical labels)
- [ ] Research specs for Acer ES1-511-C0DV, HP TPN-C125, Dell P57G001, Dell P125G002
- [ ] Source charger for Microsoft Surface Pro
- [ ] Migrate Nintendo Switch to appropriate VLAN (Trusted or IoT) — currently WiFi/VLAN 20; constrained by the eero 2-SSID limit
- [ ] Living Room TV (Vizio): network-isolate entirely rather than migrating to IoT — deny-all MAC block at pfSense, panel driven as a dumb display. Supersedes the IoT migration plan
- [ ] Run Cat6 drop (x2) behind the living-room TV → switch; HTPC lands on VLAN 80
- [x] Reconnect R710 to 10.0.0.0/8 network — live at 10.0.10.30 (VLAN 10)
- [ ] Identify and source GPU for Proxmox server (RTX 3060 12GB or Intel Arc B580)
- [x] Flash Helm HPS20 with Armbian (Armbian_22.11.2-build-48_Helm-v2b, 2026-02-24)
- [x] Set pfSense DHCP static mapping for Helm HPS20: MAC 72:c6:b9:0d:32:ac → 10.0.10.25
- [ ] Flash Helm HPS10 with Armbian
- [ ] Identify reserve eero Pro 6 use case (mesh expansion vs. spare)

---

*Part of the Homelab Command Project. Companion documents: Network & Services Architecture v1.9 · Project Roadmap v2.4 · Mnemosyne Design Doc v1.2 · IaC Runbook v1.5 · Argus Design Doc v1.2 · Orpheus Design Doc v1.3 · Ariadne Design Doc v1.0*
