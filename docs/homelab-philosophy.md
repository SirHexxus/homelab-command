# Homelab philosophy

This document captures the values, principles, and goals behind every decision in this homelab - from infrastructure topology to which apps get deployed.

---

## Table of contents

1. [Purpose](#purpose)
2. [The three documentation audiences](#the-three-documentation-audiences)
3. [Foundational principles](#foundational-principles)
4. [Infrastructure principles](#infrastructure-principles)
5. [Service selection criteria](#service-selection-criteria)
6. [What this homelab is not](#what-this-homelab-is-not)

---

## Purpose

This homelab serves several goals at once. None of them outranks the others:

- **Skill building** - Learn by doing. Deploy real infrastructure, make real mistakes, solve real problems.
- **Controlled experimentation** - A safe environment to break things intentionally, troubleshoot without consequence, and emerge with working knowledge that sticks.
- **Family services** - Host applications that make life easier for family and close friends. Replace paid services where a self-hosted alternative is good enough.
- **Privacy and security** - Maximize privacy and security for the people using these services. Not a feature - a baseline.
- **Saving money** - Where a self-hosted service is genuinely comparable to a paid alternative, prefer the self-hosted path.
- **Portfolio and proof of work** - Demonstrate technical depth to potential employers and the broader community through documented infrastructure, design decisions, and lessons learned.

### Current pursuits

Active projects running within this homelab, each with their own goals and timeline - but none of them is the permanent north star:

- Earning the Google Cybersecurity Certificate
- Building and documenting a SIEM stack (Argus)
- Earning the CompTIA Security+ certification
- Applying for the Kaiser Permanente CRDC Consultant III (SOC Analyst) position by June 2, 2026

> [!NOTE]
> For some time, the CRDC application was treated as the "Guiding Star" for this entire project. Along the way, I realized it's a short-term goal - an important one, but a subset of why this homelab exists. When this pursuit is complete, the homelab continues for all of the reasons above.

---

## The three documentation audiences

Every document in this repository is written for three audiences at once:

1. **People learning** - Someone following along to understand how to build similar infrastructure, or to learn from what worked and what didn't. Write as if teaching.
2. **Potential employers** - Someone evaluating technical competence, design thinking, and professional judgment. Write precisely and show your reasoning.
3. **Future self** - Someone who will return to this document having forgotten every decision and context that led here.

On that third audience: I have ADHD and executive function challenges. Documentation isn't only for some hypothetical future self - it's nearly as much for me right now. A clear, well-structured document acts as external working memory. Write as if leaving notes for someone who shares your skill level but has no current context.

When these audiences conflict, prioritize future self. The other two benefit from that same clarity.

---

## Foundational principles

These aren't rules - they're lenses for evaluating decisions. They come from a lot of places. The Unix/Linux philosophy happens to supply clean technical language for several of them.

### Do one thing well

Individual components should be simple, focused, and excellent at a single job. A service that tries to be a notes app, kanban board, database UI, and whiteboard is doing four things adequately instead of one thing well. Prefer narrow, excellent tools connected by clean interfaces over monolithic platforms.

### Composability

Components should connect cleanly to other programs - including programs that don't exist yet. That means preferring:

- Standard protocols and APIs over proprietary integrations
- REST/HTTP interfaces over custom SDKs
- Open formats (JSON, YAML, markdown) over locked-in binary formats
- Tools that expose their data for consumption by other tools

A service that can't be composed with anything else is a dead end.

### Principle of least surprise

Interfaces should behave in the most predictable way possible. A tool that silently exhausts memory, fails without logging, or enforces undocumented limits violates this principle. Operations should be transparent, recoverable, and observable.

### Separation

Separate policy from mechanism, and interfaces from engines. Configuration lives apart from code. Data storage lives apart from application logic. The "what" lives apart from the "how." IaC is this principle applied to infrastructure - the definition (policy) is separate from the runtime (mechanism).

### Adaptability

Favor rapid prototyping over perfect planning. Getting something running and wrong is better than a perfect plan that never ships. A working v0.1 beats a theoretical v1.0.

### Fail forward

Build things. Break things. This is intentional. The model is:

```
Build → Break → Troubleshoot → Fix → Learn → Iterate
```

A homelab that never breaks is a homelab that never teaches anything new.

### Everything is a file

Systems should be accessible through file interfaces wherever possible. Infrastructure is defined in files (Terraform, Ansible). Configuration is committed to version control. Data that can live as structured text (YAML, markdown, JSON) should. This makes everything auditable, diffable, and reproducible.

---

## Infrastructure principles

Concrete implementations of the principles above:

**Linux-first** - This homelab runs on Linux. Within Linux, Debian and Debian derivatives (Ubuntu, Proxmox VE) are the default. Other distros are on the table when they're the right tool - Debian is the baseline assumption.

**IaC-first** - Every service is provisioned via Terraform and configured via Ansible. No manual deployments. If it can't be reproduced from code, it doesn't exist. When a service requires Docker, Docker Compose is acceptable as a fallback - managed through Ansible like everything else.

**LXC-preferred** - Unprivileged LXC containers on Proxmox are the default deployment target. When a service requires Docker, the right place for it is a dedicated Docker host VM - not inside an LXC. Docker Compose on that VM is managed via Ansible, and the `compose.yaml` lives in IaC as the Source of Truth for that service. Docker-in-LXC is an absolute last resort. Reserve VMs for workloads that genuinely require them (pfSense, Home Assistant with USB passthrough, or a dedicated Docker host).

**Shared platform stack** - Postgres, Redis, and MinIO are the current backbone. New services should connect to existing instances rather than bundling their own. The backbone itself can grow - a new service can justify adding to it if it has a non-overlapping use case and covers something the existing stack can't.

**VLAN segmentation** - Network zones enforce security policy at the infrastructure layer, not the application layer. Services belong on VLANs appropriate to their trust level.

**Privacy by default** - No telemetry, no cloud sync, no external data flows unless explicitly configured and understood. This applies to infrastructure tooling as much as to hosted applications.

---

## Service selection criteria

When evaluating a new service for deployment, run it against these questions:

| Criterion | Question |
|-----------|----------|
| **Does one thing well** | Does it have a clearly defined, focused purpose? |
| **Composability** | Does it expose a standard API, protocol, or data format? |
| **LXC fit** | Can it run in an unprivileged LXC without Docker-in-LXC? |
| **Resource footprint** | Is its RAM and CPU profile appropriate for the single-node constraint? |
| **Stack alignment** | Does it connect to the shared platform stack, or does it bring competing dependencies? |
| **Project health** | Is development active? Are critical issues being addressed? |
| **Actual gap** | Does it fill a real, confirmed gap - or is it "nice to have"? |
| **Privacy** | Does it respect the privacy-first baseline? |
| **Least surprise** | Is it predictable to operate? Are failure modes observable and recoverable? |

A service that scores poorly on composability and stack alignment needs a strong case from the other criteria.

---

## What this homelab is not

- **Not a production environment** - Downtime is acceptable. Learning from failure is the point.
- **Not a showcase of scale** - Running 100 services is not an achievement if 80 of them are idle. Fewer, better-integrated services beat a longer list.
- **Not locked to any vendor or platform** - Every configuration and architecture decision is documented so it can be rebuilt from scratch on different hardware.
- **Not finished** - This is a living system. This document should be updated when the values evolve.

---

## Version history

- v1.0 (2026-04-13): Initial document - purpose, three audiences, UNIX principles, infrastructure conventions, service selection criteria
