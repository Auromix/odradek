# SPDX-License-Identifier: CC-BY-NC-4.0
"""Package public or local-only exact-motor offline review viewer."""
from pathlib import Path
import json,sys,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;ACTUAL='--actual' in sys.argv
OUT=ROOT/'work/arm-a12/whole-style01/viewer-actual' if ACTUAL else ROOT/'docs/viewers/arm-body-a12-style';OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'work/arm-a12/whole-style01/actual-viewer.json' if ACTUAL else ROOT/'work/arm-a12/whole-style01/public-viewer.json').read_text())
t=(ROOT/'engineering/arm_a09/viewer.template.html').read_text().replace('armA09','armA12').replace('A09','A12')
t=t.replace('本体结构讨论','连续甲壳整体风格').replace('直管骨架 · 交叉肩部 · 收腰底座','连续甲壳 · 同源魔鬼鱼底座 · 四瓣头形态参考').replace('结构与外观提案','整体风格预览 / 非制造版')
t=t.replace('<button data-variant="slim" aria-pressed="true">短版 · 611 mm</button>','').replace('data-variant="long" aria-pressed="false"','data-variant="long" aria-pressed="true"').replace("current='slim'","current='long'").replace("build('slim')","build('long')").replace("sourceHashes:{slim:D.slim.sha256,long:D.long.sha256}","sourceHashes:{long:D.long.sha256}")
t=t.replace('root.position.set(0,.135,.0346)','root.position.set(0,.075,.0346)').replace('底座与桌夹背景','同源 B06 底座').replace('可拆护罩','A12 外罩')
t=t.replace('<label class="check"><input id="axes"', '<label class="check"><input id="head" type="checkbox" checked>四瓣头形态参考</label><label class="check"><input id="axes"')
a=t.index('<p class="note">');b=t.index('</p>',a)
note='保留长版与七轴拓扑。新增外罩为 Blender 造型曲面，尚未完成整臂运动干涉、实际线束、散热或打印装配验证。3 kg 是裸法兰目标；四瓣头仅为形态参考，不计入本体负载结论。'+('本机使用原厂完整电机模型，未经缩放。' if ACTUAL else '公开预览使用自主电机包络，原厂 CAD 留在本机。')
t=t[:a]+'<p class="note">'+note+'</p>'+t[b+4:]
a=t.index("const m=p.id.includes");b=t.index(';const o=mesh',a)
t=t[:a]+"const m=p.color?material(new THREE.Color(...p.color.slice(0,3)),p.role==='style_surface'?.25:.4):mats.core"+t[b:]
t=t.replace("o.userData.role=p.role", "o.userData.role=p.role")
a=t.index("document.getElementById('status').textContent=");b=t.index(';render()',a)
t=t[:a]+"document.getElementById('status').textContent='整体造型预览 · 新外罩及线束尚未完成运动干涉验证'"+t[b:]
t=t.replace("o.userData.role!=='printed_cover'||document.getElementById('covers').checked", "(o.userData.role!=='style_surface'||document.getElementById('covers').checked)&&(o.userData.role!=='head_reference'||document.getElementById('head').checked)")
t=t.replace("['covers','base','axes']","['covers','base','axes','head']")
t=t.replace('Vector3(0,.35,.2)','Vector3(0,.32,.33)').replace('az:45*rad,el:26*rad,distance:1.65','az:120*rad,el:22*rad,distance:1.6')
t=t.replace("q=[...D[current].layout.poses[b.dataset.pose]];setAngles()", "q=[...D[current].layout.poses[b.dataset.pose]];const fit={idle:[1,.22,.20],attention:[1.6,.32,.33],reference:[1.7,.38,.24]}[b.dataset.pose];orbit.distance=fit[0];target.set(0,fit[1],fit[2]);setAngles()")
t=t.replace('3 kg参考伸展：肩部','A11开放基线静载估算：J2').replace(' N·m</strong>`',' N·m</strong>（非额定结论）`')
# Small local script chunks keep the viewer offline and avoid a huge HTML response.
chunks=OUT/'model';chunks.mkdir(exist_ok=True)
for old in chunks.glob('*.js'):old.unlink()
setup=json.loads(json.dumps(data));lines=[]
for group in ['long','base']:
 items=data['long']['parts'] if group=='long' else data['base'];dest=setup['long']['parts'] if group=='long' else setup['base']
 for idx,m in enumerate(items):
  target=f'window.A12_MODEL.long.parts[{idx}]' if group=='long' else f'window.A12_MODEL.base[{idx}]'
  for field in ['vertices','faces']:
   dest[idx][field]=[]
   for start in range(0,len(m[field]),4000):lines.append(target+'.'+field+'.push(...'+json.dumps(m[field][start:start+4000],separators=(',',':'))+');\n')
lines.insert(0,'window.A12_MODEL='+json.dumps(setup,ensure_ascii=False,separators=(',',':'))+';\n');scripts=[];buf=''
def flush():
 global buf
 if not buf:return
 name=f'model/{len(scripts):03d}.js';(OUT/name).write_text(buf);scripts.append(name);buf=''
for line in lines:
 if len(buf.encode())+len(line.encode())>850000:flush()
 buf+=line
flush()
t=t.replace('<script>__THREE__',''.join(f'<script src="{s}"></script>' for s in scripts)+'<script>__THREE__').replace('__MODEL_DATA__','{}').replace("JSON.parse(document.getElementById('model-data').textContent)",'window.A12_MODEL')
t=t.replace('__THREE__',(ROOT/'docs/viewers/arm-body/vendor/three-r160.min.js').read_text())
(OUT/'index.html').write_text(t);(OUT/'THREE-LICENSE.txt').write_text((ROOT/'docs/viewers/arm-body/THREE-LICENSE.txt').read_text());print('VIEWER',ACTUAL,len(data['long']['parts']),len(scripts))
