# Homelab Command — Hardware Catalog
**Version:** 1.1  
**Last Updated:** 2026-02-19  
**Status:** Active document — update as hardware is added, removed, or changed.

---

## Servers & Primary Compute

| Device | Make/Model | Specs | Current Status | Notes |
|---|---|---|---|---|
| Proxmox Server | Dell EMC PowerEdge T150 | Intel Xeon E-2378, 62GB RAM, eno8303 (WAN NIC), eno8403 (LAN NIC) | **Active — Primary compute host** | Running pfSense VM + LXC containers. GPU slot available; RTX 3060 12GB or Intel Arc B580 planned. vmbr0 (WAN bridge), vmbr1 (VLAN-aware LAN bridge) |
| NAS Server | Dell PowerEdge R710 | SSD boot disk, 1TB SSD datastore, 9TB ZFS pool (4x 3TB SAS HDDs, RAIDZ), 4x NICs (1 configured) | **Disconnected — Offline** | Running TrueNAS Scale. Was primary services host pre-pfSense migration. Reconnection to 10.0.0.0/8 network is a planned task. |

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
| Nintendo Switch | Nintendo Switch | — | **Active** (seen at 10.0.10.58) | Currently on LAN. Should migrate to Trusted or IoT VLAN. |
| Living Room TV | TCL 75S450G *(unconfirmed)* | Android TV OS 11 | **Active** at 10.0.20.102 | Model assumed from firmware string V8-R51MT08-LF1V058.021060. Physical label inaccessible due to wall mount. Security patch May 2023 — outdated. IoT VLAN migration recommended. |
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
| Helm Server V2 | Helm HPS20-1T-W-US | **Idle — Needs reflashing** | Hexacore ARM (2x Cortex-A72 1.8GHz + 4x Cortex-A53 1.4GHz), 1TB NVMe. Strong candidate for Pi-hole, lightweight services, or self-hosted email. Armbian repurpose path confirmed. USB-C charger available. |
| Helm Server V1 | Helm HPS10-128-W-US | **Idle — Needs reflashing** | ARM SoC (2016-era), 2GB ECC RAM, 128GB NVMe. Limited capability. Best suited for single lightweight purpose. Armbian repurpose path available. USB-C charger available. |

---

## Open Items & Deferred Tasks

- [ ] Confirm smart switch brand (check label on device)
- [ ] Confirm TV model when label becomes accessible
- [ ] Research specs for Acer ES1-511-C0DV, HP TPN-C125, Dell P57G001, Dell P125G002
- [ ] Source charger for Microsoft Surface Pro
- [ ] Migrate Nintendo Switch to appropriate VLAN (Trusted or IoT)
- [ ] Plan Living Room TV migration to IoT VLAN
- [ ] Reconnect R710 to 10.0.0.0/8 network
- [ ] Identify and source GPU for Proxmox server (RTX 3060 12GB or Intel Arc B580)
- [ ] Flash Helm HPS20 and HPS10 with Armbian
- [ ] Identify reserve eero Pro 6 use case (mesh expansion vs. spare)

---

*Part of the Homelab Command Project. Companion documents: Network & Services Architecture v1.4 · Project Roadmap v1.2 · Second Brain Design Doc v1.1 · IaC Runbook v1.1 · Argus Design Doc v1.1 · Media Stack Design Doc v1.1 · Ariadne Design Doc v1.0*
