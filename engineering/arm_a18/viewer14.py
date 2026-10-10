# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reuse the established seven-slider viewer with current local-only CAD."""
from pathlib import Path
import json,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit=json.loads((HERE/'build/viewer14-source-audit.json').read_text())
path=ROOT/audit['data_path'];assert sha(path)==audit['data_sha256']
assert sha(HERE/'build/assembly12.json')==audit['assembly_sha256']
data=json.loads(path.read_text())
script=(ROOT/'engineering/arm_a12/wrist02/build_viewer.py').read_text()
script=script.replace("ACTUAL='--actual' in sys.argv",'ACTUAL=True')
old="data=json.loads((ROOT/'work/arm-a12/wrist02/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/wrist02/public-viewer.json').read_text())"
assert old in script;script=script.replace(old,'data=MODEL')
script=script.replace("OUT=ROOT/'work/arm-a12/wrist02/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a12-wrist02'","OUT=ROOT/'work/arm-a18/viewer-actual14'")
script=script.replace('ROOT=Path(__file__).resolve().parents[3]','ROOT=Path(__file__).resolve().parents[2]')
ns=dict(__file__=str(HERE/'viewer14.py'),MODEL=data);exec(compile(script,str(HERE/'viewer14.py'),'exec'),ns)
out=ns['OUT'];html=(out/'index.html').read_text()
html=html.replace('root.position.set(0,.075,.0346)','root.position.set(0,.075,0)')
html=html.replace('连续甲壳腕部深化','A18 整臂当前试配').replace('腕部试配初稿 / 非制造发布','41件打印试配 / 非生产放行')
html=html.replace('ODRADEK / A12','ODRADEK / A18').replace('Odradek A12','Odradek A18')
html=html.replace('长版 · 691 mm','长版 · 340 /185 mm轴距')
html=html.replace('checked>四瓣头形态参考','disabled>四瓣头独立模块').replace('腕部六件外罩','腕部外罩')
html=html.replace("o.userData.wrist=p.id.startsWith('A12-WR02-')","o.userData.wrist=p.role==='printed_cover'&&/^J[567]\\./.test(p.frame)")
html=html.replace("o.userData.role!=='style_surface'||document.getElementById('covers').checked","!['style_surface','printed_cover'].includes(o.userData.role)||document.getElementById('covers').checked")
start=html.index('<p class="note">');end=html.index('</p>',start)
html=html[:start]+'<p class="note">长版、灵足原厂电机实际几何、同源B06底座。当前556个自有CAD项与41件打印件；已加入触点面板和J3/J4前罩。新前罩检查159个有限姿态，其余旧件仅继承原26配置；任意滑条组合、连续轨迹、线束、公差、热及3 kg运行未放行。拖动仅供形态检查。</p>'+html[end+4:]
html=html.replace('A11开放基线静载估算：J2','当前CAD静态筛选：J2')
html=html.replace('腕部 CAD 试配初稿 · 非连续工作空间或整机验证','A18当前CAD · 当前任意姿态未验证可执行性')
(out/'index.html').write_text(html)
audit['viewer_html_sha256']=sha(out/'index.html');audit['model_chunk_sha256']={p.name:sha(p) for p in sorted((out/'model').glob('*.js'))}
(HERE/'build/viewer14-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
print('A18_VIEWER_READY',out,flush=True)
