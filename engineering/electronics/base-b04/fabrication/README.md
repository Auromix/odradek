# B04-SERVICE01 fabrication review data

This is an actual native KiCad export, not production release. Two layers, 80×50×1.6 mm; nominal 35 µm copper candidate. See ../../../../docs/engineering/base-b04-pcb.md and ../verification.json.

- 4×Ø3.2 mm NPTH; R3.5 no-copper/no-component zone; metal mounting screws are not electrical grounding.
- 6×Ø0.30 mm thermal vias in U1 exposed-pad paste area require filled/capped/planarized processing agreed with board assembler. Their coordinates are in ../verification.json. Do not silently manufacture open holes beneath the paste aperture.
- Minimum native track/clearance0.25 mm; minimum drill0.30 mm. Confirm finished-hole tolerances, annular ring, soldermask registration/bridges, stencil thickness and connector fit with the selected fabricator.
- Connector pin tails and DIP leads must fit total underboard ≤3 mm, target trimmed/soldered envelope≤2.5 mm. SMD solder-height planning0.10 mm.
- No 48V motor-current path, no EtherCAT/GMSL on this board. Input branch ≤55V steady state; transient behavior, efficiency, temperature and isolation under application conditions require prototype tests.
- Data license CC-BY-NC-4.0; Odradek / Auromix contributors. Official vendor PDFs are references, not redistributed source files.
