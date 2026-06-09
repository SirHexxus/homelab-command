# Layer 3 Ingest — Session Pickup Brief

**Purpose:** orient quickly when restarting Layer 3 work from this directory.
**Last touched:** 2026-05-27
**Authoritative task page:** `wiki/admin/Evaluate and Deploy Layer 3 Specialized Models.md`
**Related closed task:** `wiki/admin/Select Capable LLM for Tier 3 via n8n.md` (Gemini API selected 2026-05-26)

## Where we are

Re-scoped the Layer 3 evaluation against actual architecture (the n8n `Mnemosyne Ingest v1` workflow, `[[Project - Mnemosyne]]`, `[[Five-Layer AI Stack]]`). Three-phase shape agreed in principle, awaiting James's go-ahead on Phase 0.

**Phase 0 (immediate, no new infra):** wire Gemini calls into the n8n workflow for image OCR, image VLM, and URL `url_context`. Existing Gemini credential reused. PDF stays on n8n's built-in `extractFromFile` until volume justifies a swap.

**Phase 1 (per-category eval):** measure local Layer 3 candidates against the Gemini baseline. Photo-13x set is the gold corpus.

**Phase 2 (selective migration):** migrate categories where local wins on cost/privacy/latency vs. Gemini.

## Decision pending

James needs to approve Phase 0 before any n8n editing. Question on the table:
> Approve Gemini-bridge Phase 0? If yes → single n8n editing session adds three HTTP nodes; image perception and URL extraction live immediately.

## If Phase 0 is approved — first session's work

1. Open `n8n/mnemosyne-ingest-v1.json` (or the live workflow at `automation.hexxusweb.com`).
2. Switch on MIME Type **fallback branch** (currently → MinIO upload only): add parallel HTTP Request nodes calling Gemini for image OCR + image VLM. Merge results into the inbox JSON before MinIO upload.
3. Text branch: add a regex/URL-pattern detection node. If text is URL-only or URL-dominant, fork to a Gemini HTTP Request using the `url_context` tool. Merge extracted article into the inbox JSON.
4. Output contract: inline body, H2 headings (`## Extracted Text`, `## Image Description`, `## Article Content`). Frontmatter for `perception_model:`, `perception_failed:`, `perception_error:` only.
5. Soft-fail surface: if Gemini returns empty/junk, set `perception_failed: true`. Hard fails already covered by the `Mnemosyne Error Alerts` workflow.
6. Test against a fresh photo, a fresh URL share, and the Photo-13x reruns; verify clarification spawn rate drops.
7. Commit the updated workflow JSON to this repo (`n8n/mnemosyne-ingest-v1.json`).

## Open items still needing answers (Phase 1+, not Phase 0)

- Ollama instance location, version, endpoint URL (which LXC/VM/host?)
- LXC service template for non-Ollama Python services (base image, systemd vs Docker-in-LXC)
- Build `check-perception-failures` maintenance script (daily-bundle soft-fail clarifications)
- Extend `wiki/SCHEMA.md` with `perception_*:` frontmatter fields once contract is stable

## Hardware ceiling (confirmed 2026-05-26)

- Host: `puppetmaster` = T150
- CPU: 16 × Intel Xeon E-2378 @ 2.60 GHz (8 cores / 16 threads, AVX-512)
- RAM: 62.68 GiB
- **CPU-only** — Matrox G200eW3 BMC display, no discrete GPU
- Implication: Qwen2.5-VL 7B ruled out for Phase 1; 3B viable but borderline

## Phase 1 candidate shortlist (eval-time reference)

| Category | C1 | C2 | Priority |
|---|---|---|---|
| Image VLM | Moondream | Qwen2.5-VL 3B | high |
| Image OCR | PaddleOCR | docTR | high |
| URL article | Trafilatura | Jina Reader | high |
| PDF → MD | Marker | Docling | **low** (already works via n8n built-in) |

## Architectural tension to keep in mind

Five-Layer principle says Layer 4 (Gemini) should not do Layer 3 work. Phase 0 deliberately violates this for speed. Phase 1 evaluation exists specifically to migrate categories back to local Layer 3 where the math works out. Don't let Phase 0 ossify — schedule the Phase 1 eval as a follow-up gate.
