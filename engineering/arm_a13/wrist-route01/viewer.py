# SPDX-License-Identifier: CC-BY-NC-4.0
"""Integrate pinned native exports and new native-audited parts in offline viewer."""
from pathlib import Path
import json,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;BUILD=HERE/'build';ACTUAL='--actual' in sys.argv
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/('work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else 'work/arm-a12/wrist02/public-viewer.json')
data=json.loads(source.read_text());oldnative=ROOT/('work/arm-a12/wrist02/actual-motors.blend' if ACTUAL else 'engineering/arm_a12/wrist02/build/A12-A-wrist02.blend');assert data['long']['sha256']==sha(oldnative)
native=ROOT/'work/arm-a13/wrist-route01/actual-motors.blend' if ACTUAL else BUILD/'A13-WRIST-ROUTE01.blend'
audit=json.loads((BUILD/('native-actual-audit.json' if ACTUAL else 'native-public-audit.json')).read_text());assert audit['native_sha256']==sha(native)
D=json.loads((BUILD/'integration-parts.json').read_text());assert audit['source_parts_sha256']==sha(BUILD/'integration-parts.json')
remove={'P06-yaw-to-roll','B7-output-flange','J7-bearing-cage','J7-bearing-retainer','J7-inner-spacer','J7-inner-centre-spacer'}
# Exactly mirror removed geometry from blender.py; historical head is intentionally omitted.
data['long']['parts']=[p for p in data['long']['parts'] if p['id'] not in remove and not p['id'].startswith('J7-tool-M4-nut-') and p['role']!='head_reference']
for p in D['new_parts']+D['hardware']:
 color=[.075,.13,.18,1] if p in D['new_parts'] else [.42,.45,.49,1]
 data['long']['parts'].append(dict(id=p['id'],frame=p['frame'],role=p['role'],color=color,vertices=p['vertices_mm'],faces=p['triangles']))
assert len({p['id'] for p in data['long']['parts']})==len(data['long']['parts'])
data['long']['sha256']=sha(native);data['long']['flange_from_J7_mm']=[110,0,0];data['long'].pop('shoulder_torque',None)
# Reuse the versioned viewer shell; substitute only controlled current data/labels.
script=(ROOT/'engineering/arm_a12/wrist02/build_viewer.py').read_text()
script=script.replace("OUT=ROOT/'work/arm-a12/wrist02/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a12-wrist02'","OUT=ROOT/'work/arm-a13/wrist-route01/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a13-wrist-route01'")
line="data=json.loads((ROOT/'work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/wrist02/public-viewer.json').read_text())"
script=script.replace(line,'data=INTEGRATED_DATA')
script=script.replace("checked>四瓣头形态参考","disabled>四瓣头待重新适配")
old="保留长版与七轴拓扑。腕部新增六件分体 CAD 外罩，整体其余外罩仍为 Blender 造型曲面。腕部的离散检查范围见模块报告；整臂、线束、散热及实际装配未完成验证。3 kg 是裸法兰目标；四瓣头仅为形态参考，不计入本体负载结论。"
new="长版连续甲壳，原七轴、电机与同源B06底座。新108替换105；TOOL-IF02工具面已更新为J7局部X110。73个采样姿态仅验证本轮整腕范围；动态线束尚未通过，当前未画线道。整臂、散热、实物装配和3 kg未放行，四瓣头接口待适配。"
script=script.replace(old,new).replace('连续甲壳腕部深化','整腕集成与支架修正').replace('连续甲壳 · 同源魔鬼鱼底座 · 四瓣头形态参考','连续甲壳 · 同源魔鬼鱼底座 · 端面凹腔接口').replace('腕部 CAD 试配初稿 · 非连续工作空间或整机验证','整腕离散检查通过 · 动态走线未通过 · 非整机制造发布')
# Eliminate stale whole-arm torque number; only updated tool datum is known here.
script=script.replace("t=t.replace('3 kg参考伸展：肩部','A11开放基线静载估算：J2').replace(' N·m</strong>`',' N·m</strong>（非额定结论）`')", "t=t.replace('3 kg参考伸展：肩部 <strong>${d.shoulder_torque.toFixed(1)} N·m</strong>', '工具平面：J7局部<strong>X110 mm</strong>；3 kg尚未验证')")
script=script.replace("replace('armA09','armA12').replace('A09','A12')","replace('armA09','armA13').replace('A09','A13')").replace('window.A12_MODEL','window.A13_MODEL')
namespace=dict(__file__=str(HERE/'viewer.py'),INTEGRATED_DATA=data);exec(compile(script,str(HERE/'viewer.py'),'exec'),namespace)
out=namespace['OUT'];html=(out/'index.html').read_text().replace('长版 · 691 mm','长版 · 原关节轴距');(out/'index.html').write_text(html);assert 'shoulder_torque' not in html
provenance=dict(native_sha256=sha(native),old_export_sha256=sha(source),old_native_sha256=sha(oldnative),parts_source_sha256=sha(BUILD/'integration-parts.json'),parts_count=len(data['long']['parts']),tool_plane_mm=[110,0,0],dynamic_harness_pass=False)
(out/'source.json').write_text(json.dumps(provenance,indent=2)+'\n');print('INTEGRATED_VIEWER',ACTUAL,len(data['long']['parts']))
