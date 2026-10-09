# SPDX-License-Identifier: CC-BY-NC-4.0
"""Rebuild the offline whole-arm viewer from pinned geometry, without decimation."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;BUILD=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/('work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else 'work/arm-a12/wrist02/public-viewer.json')
data=json.loads(source.read_text())
oldnative=ROOT/('work/arm-a12/wrist02/actual-motors.blend' if ACTUAL else 'engineering/arm_a12/wrist02/build/A12-A-wrist02.blend')
assert data['long']['sha256']==sha(oldnative)
native=ROOT/'work/arm-a14/wrist-tail01/actual-motors.blend' if ACTUAL else BUILD/'A14-WRIST-TAIL01.blend'
audit=json.loads((BUILD/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).read_text())
assert audit['native_sha256']==sha(native)
D=json.loads((BUILD/'parts.json').read_text());assert audit['parts_source_sha256']==sha(BUILD/'parts.json')
prior=ROOT/'engineering/arm_a13/wrist-route01/build/integration-parts.json';W=json.loads(prior.read_text())
remove={'P06-yaw-to-roll','B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-inner-centre-spacer','A12-W13-J3-rotor-lip','A12-W14-J4-rotor-lip',*D['replaces']}
data['long']['parts']=[p for p in data['long']['parts'] if p['id'] not in remove and not p['id'].startswith('J7-tool-M4-nut-') and p['role']!='head_reference']
for p in W['new_parts']+W['hardware']:
 color=[.075,.13,.18,1] if p in W['new_parts'] else [.42,.45,.49,1]
 data['long']['parts'].append(dict(id=p['id'],frame=p['frame'],role=p['role'],color=color,vertices=p['vertices_mm'],faces=p['triangles']))
for p in D['parts']:
 data['long']['parts'].append(dict(id=p['id'],frame=p['frame'],role=p['role'],color=[.075,.13,.18,1],vertices=p['vertices_mm'],faces=p['triangles']))
assert len({p['id'] for p in data['long']['parts']})==len(data['long']['parts'])
assert all(x not in {p['id'] for p in data['long']['parts']} for x in remove)
data['long']['sha256']=sha(native);data['long']['flange_from_J7_mm']=[110,0,0];data['long'].pop('shoulder_torque',None)
cache=ROOT/('work/arm-a14/wrist-tail01/viewer-data-actual.json' if ACTUAL else 'work/arm-a14/wrist-tail01/viewer-data-public.json');cache.parent.mkdir(parents=True,exist_ok=True)
cache.write_text(json.dumps(data,separators=(',',':'))+'\n')
script=(ROOT/'engineering/arm_a12/wrist02/build_viewer.py').read_text()
script=script.replace("OUT=ROOT/'work/arm-a12/wrist02/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a12-wrist02'","OUT=ROOT/'work/arm-a14/wrist-tail01/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a14-wrist-tail01'")
line="data=json.loads((ROOT/'work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/wrist02/public-viewer.json').read_text())";assert line in script
script=script.replace(line,'data=INTEGRATED_DATA')
script=script.replace('checked>四瓣头形态参考','disabled>四瓣头待重新适配').replace('腕部六件外罩','腕部外罩')
old='保留长版与七轴拓扑。腕部新增六件分体 CAD 外罩，整体其余外罩仍为 Blender 造型曲面。腕部的离散检查范围见模块报告；整臂、线束、散热及实际装配未完成验证。3 kg 是裸法兰目标；四瓣头仅为形态参考，不计入本体负载结论。'
new='保留长版、原七轴与同源B06底座。上臂/前臂为四件CAD分壳；J6后罩已收短。65个离散姿态仅检查本轮五件CAD与报告列出的保留实体。当前关节持续载荷复核未通过，动态线束、金属骨架和完整总装未放行。3 kg仍是裸法兰目标；四瓣头待适配。'
assert old in script;script=script.replace(old,new)
script=script.replace('连续甲壳腕部深化','修长连续甲壳 · 连杆CAD深化').replace('连续甲壳 · 同源魔鬼鱼底座 · 四瓣头形态参考','修长脊线 · 同源魔鬼鱼底座 · 硬折面腕部').replace('腕部试配初稿 / 非制造发布','受支撑无载试配 / 非生产发布').replace('腕部 CAD 试配初稿 · 非连续工作空间或整机验证','五件CAD离散干涉检查通过 · 关节载荷未通过 · 非生产发布')
oldtorque="t=t.replace('3 kg参考伸展：肩部','A11开放基线静载估算：J2').replace(' N·m</strong>`',' N·m</strong>（非额定结论）`')"
assert oldtorque in script
script=script.replace(oldtorque,"t=t.replace('3 kg参考伸展：肩部 <strong>${d.shoulder_torque.toFixed(1)} N·m</strong>', '工具平面：J7局部<strong>X110 mm</strong>；3 kg关节持续载荷未通过')")
script=script.replace("replace('armA09','armA12').replace('A09','A12')","replace('armA09','armA14').replace('A09','A14')").replace('window.A12_MODEL','window.A14_MODEL')
# Checkbox semantics cover both historical style shells and new native CAD skins.
script=script.replace("o.userData.role!=='style_surface'||", "!['style_surface','printed_cover','detachable_nonload_cover_supported_fit','nonload_wrist_guard_supported_fit'].includes(o.userData.role)||")
script=script.replace("p.id.startsWith('A12-WR02-')", "(p.id.startsWith('A12-WR02-')||p.id.startsWith('A14-WT-'))")
namespace=dict(__file__=str(HERE/'viewer.py'),INTEGRATED_DATA=data);exec(compile(script,str(HERE/'viewer.py'),'exec'),namespace)
out=namespace['OUT'];html=(out/'index.html').read_text().replace('长版 · 691 mm','长版 · 原关节轴距');(out/'index.html').write_text(html)
assert 'shoulder_torque' not in html
provenance=dict(native_sha256=sha(native),old_export_sha256=sha(source),old_native_sha256=sha(oldnative),wrist_core_source_sha256=sha(prior),parts_source_sha256=sha(BUILD/'parts.json'),parts_count=len(data['long']['parts']),tool_plane_mm=[110,0,0],dynamic_harness_pass=False,production_release=False)
(out/'source.json').write_text(json.dumps(provenance,indent=2)+'\n');print('CURRENT_VIEWER',ACTUAL,len(data['long']['parts']))
