# SPDX-License-Identifier: CC-BY-NC-4.0
"""Package only current printable parts and matching verification reports."""
from pathlib import Path
import json,zipfile,hashlib
out=Path(__file__).resolve().parent/'build'/'exterior'
manifest=json.loads((out/'exterior-manifest.json').read_text())
custom=[p for p in manifest['parts'] if p['category']=='custom']
assert manifest['revision']=='B05-EXTERIOR-SHAPE-07' and len(custom)==8
actual={p.name for p in (out/'print-parts').glob('*.stl')}
assert actual=={Path(p['print_stl']).name for p in custom}
checks=json.loads((out/'print-checks.json').read_text())
assert checks['mesh_and_envelope_pass'] and len(checks['files'])==8
for f in checks['files']:
 path=out/'print-parts'/Path(f['path']).name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==f['sha256']
fasteners=json.loads((out/'assembly-checks.json').read_text())
assert fasteners['nominal_hardware_arithmetic_pass'] and fasteners['fastener_count']==18
assert fasteners['source_sha256']==hashlib.sha256((out/'mounting-contract.json').read_bytes()).hexdigest()
readme='''B05-EXTERIOR-SHAPE-07 八件式无动力试装候选

单位：毫米。外罩约356×253 mm，中心环台OD170/ID104，最高Z74。
8件：左右一体翼肩2、前鼻1、检修盖1、装甲环1、灯窗1、两半一体安装骨架2。
8件通过闭合、单连通体、正体积、无重复/退化面和220×220×250 mm床包络检查。
床XY各留5 mm；骨架最长208 mm，切片时另核对支撑与裙边/边沿的面积。
只平移到正坐标，尚未完成支撑、打印方向、孔槽补偿、最小壁厚和自交验证。
螺钉/螺母另购：18颗ISO7380-1 M3×10 + 18颗DIN934 M3，标准件不供打印。
两处骨架搭接名义间隙0.3 mm；两颗连接螺钉从上方装配。
先做孔槽与搭接小样，插入螺母，再装两半骨架、外罩、后盖和环台。
尚未验证实物装配、工具入口、螺母插入路径与结构强度。
骨架只固定外罩，尚未接正式机械臂承载骨架/法兰/桌夹，不可做带载动作。
灯窗固定、灯板、真实RJ45/GMSL/48V接口组件、PCB与线缆尚未完成集成。
许可：CC-BY-NC-4.0；商业使用需作者许可。
Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
'''
(out/'PRINT-README.txt').write_text(readme)
extras=['PRINT-README.txt','print-checks.json','assembly-checks.json','frame-clearance-checks.json','mounting-contract.json','exterior-manifest.json']
zip_path=out/'B05-exterior-fit-prototype.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for part in custom: z.write(out/part['print_stl'],'B05-SHAPE-07/'+part['print_stl'])
 for f in extras: z.write(out/f,'B05-SHAPE-07/'+f)
with zipfile.ZipFile(zip_path) as z:
 assert z.testzip() is None
 assert len([n for n in z.namelist() if n.endswith('.stl')])==8
print('PACKAGED',len(custom),'STLs; report hashes and archive CRC passed')
