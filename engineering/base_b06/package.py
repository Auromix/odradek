# SPDX-License-Identifier: CC-BY-NC-4.0
"""Package only current validated print meshes; reject stale fit reports."""
from pathlib import Path
import json,hashlib,zipfile
HERE=Path(__file__).resolve().parent; OUT=HERE/'build/exterior'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((OUT/'manifest.json').read_text()); mh=digest(OUT/'manifest.json')
reports={name:json.loads((OUT/name).read_text()) for name in ('print-checks.json','solid-fit-checks.json','fit-checks.json','service-checks.json','hardware-integration-checks.json','light-fit-checks.json','slice-review-checks.json')}
assert reports['print-checks.json']['mesh_and_envelope_pass']
assert reports['hardware-integration-checks.json']['pass']
assert reports['light-fit-checks.json']['pass'] and reports['slice-review-checks.json']['pass_']
assert reports['solid-fit-checks.json']['static_solid_interference_pass']
assert reports['service-checks.json']['sampled_extraction_pass'] and reports['service-checks.json']['pcb_datum_pass']
for name in ('solid-fit-checks.json','fit-checks.json','service-checks.json','hardware-integration-checks.json','light-fit-checks.json','slice-review-checks.json'):
    assert reports[name]['manifest_sha256']==mh, f'Stale report {name}'
prints=[p['print_stl'] for p in manifest['parts'] if p.get('print_stl')]
assert len(prints)==5
checked={Path(p['path']).name:p['sha256'] for p in reports['print-checks.json']['files']}
for name in prints:assert checked[Path(name).name]==digest(OUT/name), f'Stale print check {name}'
provenance={'revision':manifest['revision'],'manifest_sha256':mh,
 'frozen_inputs':{str(p.relative_to(HERE)):digest(p) for p in sorted((HERE/'inputs').glob('*.json'))},
 'generator_sha256':{p.name:digest(p) for p in sorted(HERE.iterdir()) if p.suffix in ('.py','.html')},
 'native_blend_sha256':digest(OUT/'ODR-BASE-B06-COMPACT.blend'),
 'print_parts':prints,'print_stl_sha256':{p:digest(OUT/p) for p in prints},
 'report_sha256':{p:digest(OUT/p) for p in reports},
 'validation':{'print_mesh_pass':True,'static_closed_solid_pass':True,'solid_pairs':len(reports['solid-fit-checks.json']['pairs']),
 'root_tool_rays':sum(t['sample_rays'] for t in reports['fit-checks.json']['root_tool_rays']),
 'root_tool_rays_blocked':sum(t['blocked'] for t in reports['fit-checks.json']['root_tool_rays']),
 'lid_extraction_samples':len(reports['service-checks.json']['lid_extraction_samples']),'pcb_datum_pass':True},
 'status':'Unpowered integrated geometry candidate; routed IO PCB exported separately; complete base manufacturing release pending'}
(OUT/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
readme='''B06-COMPACT-05-LIGHT · 无动力试装包 · STL单位mm
五件打印件；采购件/接口板/机械臂承载结构不包含在打印包。
256×256×256mm床，每侧5mm检查余量；支撑、brim和打印补偿需切片检查。
后盖两颗背向M3×10，主罩四颗底面M3×10；PCB四颗M3×10。
DIN934 M3螺母10颗；灯板/灯窗两颗M2×8、DIN934 M2螺母2颗；灯窗软垫需试样。
先装内藏螺母，再装灯窗、板子、根座和主罩，最后连接后盖。
后盖检修先断电拔线、退出两颗背向螺钉，再向后退出40mm后抬起。
此路径只做离散采样；维护时须留后部工作空间，贴墙安装不能据此保证原位拆盖。
IO板及独立PWM灯板已完成原生布线/Gerber导出；完整线束、插头释放和载荷/电气验证仍未完成。禁止以本包作为整套底座制造、通电或带载放行。
CC-BY-NC-4.0 · Odradek - Auromix contributors
'''
(OUT/'PRINT-README.txt').write_text(readme)
archive=OUT/'B06-print-fit.zip'; prefix=manifest['revision']+'/'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr(prefix+'PRINT-README.txt',readme)
    for name in prints+list(reports)+['provenance.json']:
        z.write(OUT/name,prefix+name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name in prints+list(reports)+['provenance.json']:assert z.read(prefix+name)==(OUT/name).read_bytes()
print('PACKAGED',archive,len(prints),'parts')
