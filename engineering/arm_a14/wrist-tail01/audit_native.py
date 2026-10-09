# SPDX-License-Identifier: CC-BY-NC-4.0
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'engineering/arm_a14/link-shell01/audit_native.py').read_text().replace('work/arm-a14/link-shell01/actual-motors.blend','work/arm-a14/wrist-tail01/actual-motors.blend').replace('A14-LINK-SHELL01.blend','A14-WRIST-TAIL01.blend')
exec(compile(s,__file__,'exec'),dict(__file__=__file__))
