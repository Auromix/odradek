<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# CD-PCB01

Native 318-component, 285-LED, Ø60×1 mm six-layer board candidate. Parent CD-EC01 is read-only; pixel coordinates, wiring and firmware mapping are unchanged. See the [design note](../../../../docs/engineering/hardware/central-display-pcb01.md).

Run `python3 rebuild.py --kicad-cli /path/to/kicad-cli --kicad-python /path/to/python-with-pcbnew` from this directory, or invoke the script with its repository-relative path. It regenerates only PCB01, replays source-matched routes and runs native ERC/DRC/parity plus independent pin/geometry checks. It does not execute the parent's build. Optional PNG: `CD_SHARP_MODULE=/path/to/sharp node tools/render_review_png.mjs`.

- `kicad/central.kicad_pcb`, `.kicad_sch`, `.kicad_pro`: authoritative native review candidate.
- `kicad/routing-plan.json`: exact native copper/zone replay, guarded by netlist and footprint hashes.
- `mechanical-interface.json`: actual head-frame poses of all 33 back components, separate package-only maximum/reference boxes and non-material planning envelopes. `package-body-dimensions.json` records exact source dimensions; no PCB lands are inflated to package height.
- `component-positions.csv`: all318 native placement readbacks; not assembly-release centroid data.
- `dfm-evidence.json`: actual LED spacing and 19 via/SMD overlap registry; resin-fill/cap approval required.
- `kicad/checks/`: real native reports, no DRC ignored checks or exclusions.
- `kicad/plots/layers/`: unmodified native layer SVGs. `front/back-review.svg` are labelled review derivatives; rear mirrored only for viewing.

Physical stackup, fabrication, assembly, thermal and electrical testing remain unapproved. This is not manufacturing release. No purchasing or external contact performed. Original project files are CC-BY-NC-4.0; supplier source facts retain their linked provenance.
