# R5-HEAD-SERVO01

Engineering comparison: external MC5010 S ET versus one head-mounted Gold Solo Twitter configuration for the R5-LINK01 direct 2.5 mm-lead actuator. Not a PCB, fabrication output, certified safety circuit or energizing instruction.

From repository root:

```sh
python3 engineering/electronics/r5-head-servo01/build.py
python3 engineering/electronics/r5-head-servo01/verify.py
```

`build.py` reads frozen R5-LINK01 CSV inputs and recreates four numerical files plus `study.json`. It uses Python's standard library. The 1001-point CSV integration differs slightly from the denser upstream calculation; both value and residual are retained. It does not rebuild or modify any mechanical input.

`connection-map.csv`, `candidate-bom.csv` and `catalogue-geometry-evidence.json` are audited reference data, not outputs of `build.py`. Their primary-source IDs resolve in `docs/engineering/sources/r5-head-servo01.json`; `verify.py` checks archived sources and input/output hashes when those private work archives are present. A checkout without the vendor archives cannot reproduce the source-archive checks; it can still reproduce the numerical demand and inspect the recorded hashes. No vendor PDFs or STEP files are redistributed.

Read `docs/engineering/hardware/r5-head-servo01.md` for phase-current definition, document-revision/STO, heat, low-inductance compatibility, harness and regeneration boundaries. In particular 287.171 N is a single 112 mm sphere case, not the bound for the user's 50–120 mm box/bottle range.

SPDX-License-Identifier: CC-BY-NC-4.0
Odradek — Auromix contributors (https://github.com/Auromix/odradek)
