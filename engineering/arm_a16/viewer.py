# SPDX-License-Identifier: CC-BY-NC-4.0
"""Local-only exact-source interactive viewer; cannot imply motion qualification."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
MODULED='--modules' in sys.argv
data=json.loads((ROOT/('work/arm-a16/viewer-modules-data.json' if MODULED else 'work/arm-a16/viewer-data.json')).read_text())
if MODULED:
    colors={'printed_structure':[.055,.08,.095,1],'supplier_reference':[.08,.10,.12,1]}
    for p in data['long']['parts']:
        if p['role'] in colors:p['color']=colors[p['role']]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=json.loads((HERE/'build'/('native-modules-audit.json' if MODULED else 'native-audit.json')).read_text())
assert data['long']['layout']==native['layout']
assert data['long']['sha256']==native['native_sha256']==sha(ROOT/native['native_path'])
for source in native['source_files']:assert sha(ROOT/source['path'])==source['sha256']
if MODULED:
    motion=json.loads((HERE/'build/motion07.json').read_text())
    assert motion['layout']==data['long']['layout'] and motion['sampled_clear']
    for relative,digest in motion['source_sha256'].items():assert sha(ROOT/relative)==digest
data['long']['known_conflicts']=[]
for name in ['skeleton01','hardware01','covers02']:
    review=HERE/'build'/name/'review.json'
    if not review.exists():continue
    R=json.loads(review.read_text());assert R['layout']==data['long']['layout']
    for path,digest in R['source_sha256'].items():assert sha(ROOT/path)==digest
    for pose in {x['pose'] for x in R['collisions']}:
        rows=[x for x in R['collisions'] if x['pose']==pose]
        data['long']['known_conflicts'].append(dict(q=data['long']['layout']['poses'][pose],joint=rows[0]['a']+' / '+rows[0]['b'],angle=''))
R=json.loads((HERE/'build/covers02/review-hardware.json').read_text())
assert R['layout']==data['long']['layout']
for path,digest in R['source_sha256'].items():assert sha(ROOT/path)==digest
for pose in {x['pose'] for x in R['collisions']}:
    rows=[x for x in R['collisions'] if x['pose']==pose]
    data['long']['known_conflicts'].append(dict(q=data['long']['layout']['poses'][pose],joint=rows[0]['a']+' / '+rows[0]['b'],angle=''))
script=(ROOT/'engineering/arm_a12/wrist02/build_viewer.py').read_text()
script=script.replace("ROOT=Path(__file__).resolve().parents[3]","ROOT=Path(__file__).resolve().parents[2]")
script=script.replace("OUT=ROOT/'work/arm-a12/wrist02/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a12-wrist02'","OUT=ROOT/'work/arm-a16/"+('viewer-modules' if MODULED else 'viewer-actual')+"'")
line="data=json.loads((ROOT/'work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/wrist02/public-viewer.json').read_text())"
assert line in script;script=script.replace(line,'data=MODEL')
script=script.replace("root.position.set(0,.075,.0346)","root.position.set(0,.075,0)")
script=script.replace('连续甲壳腕部深化','A16 常规结构整合').replace('腕部试配初稿 / 非制造发布','静态尺寸验证候选 / 非整臂发布').replace('腕部六件外罩','腕部外罩').replace('checked>四瓣头形态参考','disabled>四瓣头保持独立模块')
ns=dict(__file__=str(HERE/'viewer.py'),MODEL=data);exec(compile(script,str(HERE/'viewer.py'),'exec'),ns)
out=ns['OUT'];t=(out/'index.html').read_text()
t=t.replace('root.position.set(0,.075,.0346)','root.position.set(0,.075,0)')
old='A11开放基线静载估算：J2 <strong>${d.shoulder_torque.toFixed(1)} N·m</strong>（非额定结论）'
assert old in t;t=t.replace(old,'全灵足原尺寸关节 · 法兰面J7局部X110 · 3 kg仍为设计目标')
start=t.index('<p class="note">');end=t.index('</p>',start)
t=t[:start]+'<p class="note">A16采用常规法兰、板式支架和标准矩形管。底座为当前B06同一源文件的实际几何。仅根部36对静态实体检查通过；整臂紧固件、外罩、动态线束和载荷尚未放行。拖动滑条不代表姿态可执行。</p>'+t[end+4:]
t=t.replace("document.getElementById('status').textContent='腕部 CAD 试配初稿 · 非连续工作空间或整机验证'","document.getElementById('status').textContent=blocked?'此代表姿态已检出干涉，需修正':'A16结构/外罩候选；当前姿态尚未完整验证'")
t=t.replace('ODRADEK / A12','ODRADEK / A16').replace('Odradek A12','Odradek A16').replace('长版 · 691 mm','长版 · 340 /185 mm轴距')
cover_state='外罩已检出干涉，正在修正。' if any(x['pose'] for x in json.loads((HERE/'build/covers02/review.json').read_text())['collisions']+R['collisions']) else '外罩也通过上述三个配置的骨架/原厂外形/名义采购件检查；外罩安装耳与螺钉尚未设计。'
t=t.replace('仅根部36对静态实体检查通过；整臂紧固件、外罩、动态线束和载荷尚未放行。','根部及骨架/名义紧固件在三个代表静态姿态通过；'+cover_state+'动态线束和载荷未放行。')
if MODULED:
    for name in ['root-cover03','cowls04','wrist05','skins06']:
        path=HERE/'build'/name/'review.json';d=json.loads(path.read_text()) if path.exists() else json.loads((path.parent/'manifest.json').read_text())
        assert d['scoped_clear'] and d['tool_access']['scoped_clear'],name
        for relative,digest in d['source_sha256'].items():assert sha(ROOT/relative)==digest
    t=t.replace('外罩也通过上述三个配置的骨架/原厂外形/名义采购件检查；外罩安装耳与螺钉尚未设计。','全部外罩现有普通螺钉固定件；根部、肩肘、腕部、长罩按明确替换清单合并。模块分别通过三个静态配置及预留工具空间检查；实际装配、连续运动与动态线束仍需验证。')
    t=t.replace('A16 常规结构整合','A16 全外罩固定整合').replace('A16结构/外罩候选；当前姿态尚未完整验证','26个有限采样通过；任意滑条组合、线束和载荷仍未验证')
    t=t.replace('实际装配、连续运动与动态线束仍需验证。','修正J6固定点与J7罩裙后，收拢至互动、J7滚转、J6横摆共26个有限采样通过；实际装配、完整连续运动与动态线束仍需验证。')
(out/'index.html').write_text(t)
print('A16_VIEWER',out,flush=True)
