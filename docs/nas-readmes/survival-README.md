# Survival

Community Resource Library — an offline reference archive for practical knowledge and skills.
Intended to function as a self-contained knowledge base accessible during partial or total
societal disruption, with or without internet access.

Originally sourced from the Seagate external drive (2026-03-19), merging the Community
Resource Library, the Mega Folder, and the masterFileReference Library collections.

---

## File Structure

```text
survival/
├── knowledge-base/
│   ├── agriculture/           # Farming, food production, soil, livestock
│   ├── chemistry/             # General chemistry, lab work, synthesis, safety
│   ├── combat-and-tactics/    # Military manuals, field tactics, guerrilla warfare
│   ├── communications/        # Radio, signals, electronic warfare, cryptography
│   ├── electronics/           # Electronics, electrical systems, hardware
│   ├── energy/                # Power generation, fuel, home power
│   ├── firearms/              # Firearm manuals, law, gunsmithing
│   ├── forensics/             # Investigation, ballistics, scene analysis
│   ├── how-to/                # General practical skills (cooking, crafts, automotive, etc.)
│   ├── hunting-and-trapping/  # Field hunting, trapping, tracking
│   ├── martial-arts/          # Hand-to-hand combat, fitness, conditioning
│   ├── medical/               # First aid, surgery, pharmaceuticals, field medicine
│   ├── military-guides/       # US Army and allied field manuals
│   ├── nuke-bio-chem/         # Nuclear, biological, and chemical threat response
│   ├── navigation/            # Topography, land navigation, environmental ops
│   ├── sciences/              # Mathematics, physics, biology, engineering reference
│   ├── survival-skills/       # Shelter, food, water, wilderness survival
│   ├── tracking-and-evasion/  # Tracking, counter-tracking, evasion
│   └── workshop/              # Blacksmithing, machining, welding, metallurgy
├── rachel-offline/            # Offline web archive (Khan Academy, Hesperian, Wikipedia, etc.)
├── software/                  # Reference software (see notes)
└── unsorted/                  # Content pending review and filing
```

---

## Naming Schema

**Function first, details second.** Directory and file names should immediately communicate
what something *does* or *is for* — not what it technically is.

- `medical-wound-care-guide.pdf` not `FM-21-11.pdf`
- `nuke-bio-chem/` not `NBC/`
- `agriculture/` not `farming-and-husbandry-overview/`

The goal: someone under stress with no context should be able to find what they need fast.

---

## Consumers

| Application | Platform | Role |
|---|---|---|
| Direct file access | NFS / any client | Manual retrieval — PDF viewer, browser |
| Future: web interface | TBD | Searchable, browsable knowledge base (Mneme integration planned) |

---

## Notes

- `rachel-offline/` is a browsable offline web snapshot, not a document collection —
  keep it self-contained and do not mix individual files into it
- `software/Quickload/` contains ballistics calculation software (Windows ISO only) —
  a future project is to rebuild or wrap this as a web interface so it is accessible
  from any device without a Windows dependency
- Much of this content will eventually be digested into Mneme as structured knowledge
- `unsorted/` content from The Ark (Random Stuff, Requests) should be filed or dropped
  as time allows
