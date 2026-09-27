# Historical drive-envelope inputs

These scripts reproduce the numerical OBB/SAT studies used to place the R4-layout-03 motor proxies. They retain the old **assumed Ø34 × 14 mm total pulley envelope**. That width does not fit the subsequently checked Gates catalog wheel, whose total axial length is 20.6248 mm. Independent shafts, bearings and couplings also require a different package. Do not use these scripts to approve a physical drive assembly.

`pack.py` uses lower hinge z=-25 mm and emits the original search results. `pack_forward_lower.py` uses z=+50 mm; the saved single-variant result is obtained by importing it and calling `assess(70, 2.5, 2.5, (1, 1), belts=True)`. The result files contain separate source/reproduction annotations in addition to computed fields. All computed fields of the forward-lower snapshot were regenerated and compared after moving the script here; license headers and paths changed, numerical code did not.

The original source input and result remain useful for tracing why the layout changed. They are not evidence that the new, supported transmission fits inside the old head. The petal-only separation certificate has a different geometric scope.
