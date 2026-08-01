# Commodity Codes & Keywords — LCS Lead Monitor

Two jobs:
1. **Portal registration cheat sheet** — the codes to select when registering as
   a vendor so alert emails actually fire (James, tonight/tomorrow).
2. **Classifier reference** — the keyword and negative-keyword lists the agent
   uses to decide equipment match (see `SKILL.md` → Classification rubric).

---

## Commodity codes by portal

| Portal | Code system | Select |
|--------|-------------|--------|
| **Cal eProcure** (CA state) | **UNSPSC** | Class **41111500** (Weight Measuring Instruments, whole class) + class **41111900** (Indicating & Recording Instruments) + commodity **73152109** (Industrial weight scale maintenance & rental service — add at the 8-digit commodity level, NOT its parent class 73152100) |
| **PlanetBids** (CA local — per agency) | **NIGP** | Class **780** (Scales & Weighing Apparatus) + the **938-series** maintenance/repair service code |
| **BidNet Direct / California Purchasing Group** | category + keyword | Scale/weighing categories + the keyword list below |
| **Arizona Procurement Portal (APP)** | **UNSPSC** (confirmed 2026-06-17) | `41111500` + `41111900`. The `73152109` service leaf is NOT in APP's UNSPSC subset — search "calibration"/"repair" for an alternative or skip (service angle covered on Cal eProcure + NIGP portals + BidNet AZ) |
| **NevadaEPro / Clark County** (Week 2) | **NIGP** | Class **780** + 938-series maintenance/repair |

### UNSPSC 41111500 children worth knowing

| Code | Description |
|------|-------------|
| 41111511 | Truck or rail scales |
| 41111518 | Axle load scales (weigh-in-motion / enforcement) |
| 41111509 | Floor or platform scales |
| 41111522 | Hopper scale |
| 41111519 | Crane scale |
| 41111506 | Animal weighing scales |
| 41111505 | Calibration weights or weight sets |
| 41111516 | Weight measuring instrument accessories |

### UNSPSC service / adjacent codes

| Code | Description | Notes |
|------|-------------|-------|
| 41111900 | Indicating and recording instruments | Weight indicators / readouts; catches RFPs that lead with the display, not the scale |
| 73152109 | Industrial weight scale maintenance and rental service | Catches service-contract / calibration RFPs (recurring LCS revenue). Subscribe at this 8-digit commodity level — NOT parent class 73152100 (= all equipment maintenance, too noisy) |

### NIGP codes (PlanetBids / BidNet / Arizona APP / NevadaEPro)

| Code | Description | Notes |
|------|-------------|-------|
| 78000 | Scales and Weighing Apparatus | Equipment — select the whole 780 class |
| 92969 | Scales incl. Weigh-In-Motion | WIM / highway axle scales; capital DOT work, often coded outside class 780 — selecting it closes a recall gap |
| 93879 | Scales and Weighing Apparatus Maintenance and Repair | Service-contract / calibration RFPs (recurring LCS revenue) |

> Note: load cells and "weighbridge" as such don't have dedicated UNSPSC leaf
> codes here — class-level 41111500 + the keyword net below covers them.
> Confirm exact NIGP code numbers in each portal's own picker; class 780 is the
> scales-and-weighing-apparatus class and the 938-series is its maintenance/repair
> service counterpart.

---

## Positive keywords (equipment match)

Set these as keyword alerts on any portal with a free-text alert field, and use
them in classification:

- truck scale, vehicle scale, weighbridge, weigh bridge
- axle scale, weigh-in-motion, WIM
- rail scale, track scale
- tank scale, hopper scale, batching scale
- floor scale, platform scale (large-capacity / foundation-mounted)
- load cell, weighing system, weigh station
- scale calibration, legal for trade, NTEP

## Negative keywords (kill these — "scale" is a noisy word)

If a hit matches a positive keyword *only* through the bare word "scale" and one
of these contexts is present, it is **not** an equipment match:

- large-scale, full-scale, at scale, scale up, scale out, scalable, scalability
- economies of scale, scale of the project, time scale, grey/gray scale
- pay scale, sliding scale, wage scale
- scale model, 1/35 scale, ho scale
- fish scale, scale removal, descaling
- dental scaling, scale and polish
- Likert scale, scale of 1 to 10, rating scale

---

## Calibration note

The negative list **will** be incomplete at launch — that's expected. During the
Week 1–3 calibration window, every false positive James marks 👎 should add a new
negative keyword (or tighten a positive one) here. This file is the single place
that tuning lives, so the classifier and the portal alerts stay in sync.
