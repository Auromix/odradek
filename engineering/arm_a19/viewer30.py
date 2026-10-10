# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reuse proven seven-slider UI for current source-bound assembly."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
review=ROOT/'engineering/arm_a19/build/assembly25/review20.json'
assembly=ROOT/'engineering/arm_a19/build/assembly25/manifest.json'
status='整合新件的有限姿态检查正在进行；未重查所有旧件对'
if review.exists():
    r=json.loads(review.read_text())
    current=hashlib.sha256(assembly.read_bytes()).hexdigest()
    if r['source_sha256'].get(str(assembly.relative_to(ROOT)))==current and r['changed_pair_sampled_clear']:
        status=f"整合变更新件检查{len(r['checks'])}个有限姿态；未重查所有旧件对"
code=(ROOT/'engineering/arm_a18/viewer14.py').read_text()
for old,new in [
    ('build/viewer14-source-audit.json','build/assembly25/viewer30-source-audit.json'),
    ('build/assembly12.json','build/assembly25/manifest.json'),
    ('work/arm-a18/viewer-actual14','work/arm-a19/viewer-actual30'),
    ('build/viewer14-source-audit.json','build/assembly25/viewer30-source-audit.json'),
    ('A18 整臂当前试配','A19 整臂当前试配'),('ODRADEK / A18','ODRADEK / A19'),('Odradek A18','Odradek A19'),('A18当前CAD','A19当前CAD'),
    ('当前556个自有CAD项与41件打印件；已加入触点面板和J3/J4前罩。新前罩检查159个有限姿态，其余旧件仅继承原26配置','当前562个自有CAD项与41件打印件；已整合RS03腕部、12 mm肩部支架和触点面板。'+status)]:
    code=code.replace(old,new)
exec(compile(code,str(Path(__file__)), 'exec'),dict(__file__=str(Path(__file__))))
