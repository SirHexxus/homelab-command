# Tabletop

Tabletop RPG rulebooks, GM resources, campaign materials, and character files.

---

## File Structure

```text
tabletop/
├── systems/        # System-specific rulebooks and resources (one subdir per system)
├── gm-resources/   # Generic GM material — maps, tokens, tables, hooks, items, notes, ideas
├── characters/     # Character sheets and character reference material
├── campaigns/      # Named campaigns (one subdir per campaign)
└── unsorted/       # Unsorted content pending review and filing
```

---

## Naming Schema

- **`systems/`:** one subdirectory per game system (e.g. `GURPS/`, `FATE System/`, `World of Darkness/`)
- **`campaigns/`:** one subdirectory per campaign (e.g. `Ancient Horizon/`, `Alex's Games/`)
- **Files:** preserve original filenames; no rename convention enforced

---

## Consumers

| Application | Platform | Role |
|---|---|---|
| Direct file access | NFS / any client | Manual retrieval only — not served by any application |

---

## Notes

- `gm-resources/` is for material that could apply to any campaign — if it's tied to a
  specific campaign, it belongs in `campaigns/<name>/` instead
- `unsorted/` is a staging area — file content into the appropriate directory as time allows
