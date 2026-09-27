# ULP-02 manufacturing review only — not fabrication release

These are actual KiCad 10.0.6 exports from the source-matched, ERC/DRC-checked ULP-02 independent LED coupon. They are not an authorization to order or assemble an arm-mounted PCB.

The candidate has four copper layers, 0.8 mm nominal finished thickness and 35 µm copper. The automatically generated `.gbrjob` dielectric numbers are illustrative defaults, not a qualified fabrication stackup. In2.Cu is GND. There are 223 × 0.25 mm plated drill holes and 4 × 0.30 mm thermal holes, no NPTH mounting holes.

Before fabrication: resolve manufacturer land-pattern overlays (especially NTC and exact JST part drawing), layer construction/tolerances, thermal-via filling/tenting, stencil aperture/void control, assembly polarity and connector fit. The current 4-window exposed-pad paste plan is 55.2% nominal coverage and requires assembler qualification. Candidate board thickness and electronic component heights do not include grip structure or insulation.

No first article, electrical, thermal, EMC, fatigue or arm integration test has occurred. Source and export hashes are in `../checks/rebuild-report.json`; native reports are `../checks/erc.json` and `../checks/drc.json`. License CC-BY-NC-4.0 / Auromix contributors.
