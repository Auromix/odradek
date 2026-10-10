# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reuse proven seven-slider UI for current source-bound assembly."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent));import binding50 as binding
review=ROOT/'engineering/arm_a19/build/assembly25/review20.json'
assembly=ROOT/'engineering/arm_a19/build/assembly25/manifest.json'
count=len(json.loads(assembly.read_text())['parts'])
status='整合新件的有限姿态检查正在进行；未重查所有旧件对'
if review.exists():
    r=json.loads(review.read_text())
    current=hashlib.sha256(assembly.read_bytes()).hexdigest()
    if binding.assembly_compatible(r['source_sha256'].get(str(assembly.relative_to(ROOT)))) and r['changed_pair_sampled_clear']:
        status=f"变更新件有{len(r['checks'])}个有限姿态证据；另有21个整臂零件对组合证据；均未覆盖全工作空间"
code=(ROOT/'engineering/arm_a18/viewer14.py').read_text()
for old,new in [
    ('build/viewer14-source-audit.json','build/assembly25/viewer30-source-audit.json'),
    ('build/assembly12.json','build/assembly25/manifest.json'),
    ('work/arm-a18/viewer-actual14','work/arm-a19/viewer-actual30'),
    ('build/viewer14-source-audit.json','build/assembly25/viewer30-source-audit.json'),
    ('A18 整臂当前试配','A19 整臂当前试配'),('ODRADEK / A18','ODRADEK / A19'),('Odradek A18','Odradek A19'),('A18当前CAD','A19当前CAD'),
    ('当前556个自有CAD项与41件打印件；已加入触点面板和J3/J4前罩。新前罩检查159个有限姿态，其余旧件仅继承原26配置',f'当前{count}个自有CAD项与41件打印件；已整合RS03腕部、12 mm肩部支架和触点面板。'+status)]:
    code=code.replace(old,new)
exec(compile(code,str(Path(__file__)), 'exec'),dict(__file__=str(Path(__file__))))
