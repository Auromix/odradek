# BRI01 physical base interface candidate

CC-BY-NC-4.0; Required Notice: Odradek — Auromix contributors.

Open `kicad/base-rear-interface01.kicad_pro`. The board is a passive, non-magnetic 8P8C straight-through plus separate 48 V power path. SMA adaptors mount mechanically on the shared carrier; they are not RF traces in this PCB.

- `mechanical/parts.json` and `mechanical/base-rear-interface01-assembly.step`: matching 59-part original global-coordinate model.
- `connector-contract.json`: datums, ports, apertures, partially closed mating/cable envelope.
- `routing-plan.json`: actual final routed copper replay; no scratch router items.
- `reports/`: native ERC/DRC and schematic XML; `native-readback.json`: actual pads/routes.
- `fabrication/`: manufacturing review Gerber/drills, not production release.
- `verification.json`, `manifest.json`: checks and file hashes.

See `docs/engineering/base-rear-interface01.md` from repository root for exact prototype limits and reproduction.
