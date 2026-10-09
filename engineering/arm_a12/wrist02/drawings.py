# SPDX-License-Identifier: CC-BY-NC-4.0
"""Source-BREP orthographic review sheets, not manufacturing approval drawings."""
from pathlib import Path
import json,html,hashlib,re
import cadquery as cq
OUT=Path(__file__).parent/'build'
def main():
 d=json.loads((OUT/'manifest.json').read_text());folder=OUT/'drawings';folder.mkdir(exist_ok=True);records=[]
 for p in d['parts']:
  step=OUT/'step'/(p['id']+'.step');assert hashlib.sha256(step.read_bytes()).hexdigest()==p['step_sha256'];s=cq.importers.importStep(str(step)).val();bb=s.BoundingBox()
  panels=[]
  for k,(label,axis) in enumerate([('沿 X 方向',(1,0,0)),('沿 Y 方向',(0,1,0)),('沿 Z 方向',(0,0,1))]):
   svg=cq.exporters.getSVG(s,dict(width=320,height=320,marginLeft=16,marginTop=16,projectionDir=axis,showAxes=False,showHidden=True,strokeWidth=.65,strokeColor=(42,63,77),hiddenColor=(163,175,182)))
   svg=svg[svg.index('<svg'):];svg=re.sub(r'<svg\s',f'<svg x="{36+k*370}" y="150" ',svg,count=1)
   panels.append(svg+f'<text x="{196+k*370}" y="505" text-anchor="middle" class="label">{label}</text>')
  frame=html.escape(p['frame']);joint=int(p['id'].split('-J')[1][0]);axis='X' if joint in [5,6] else 'Y';datums={5:'Y72.25 / Z±49',6:'Y±33.5 / Z84.70',7:'X−1.70 / Z±33.50'}[joint]
  text=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800"><style>text{{font-family:Arial,'PingFang SC',sans-serif;fill:#273e4d}}.title{{font-size:26px;font-weight:600}}.label{{font-size:17px}}.small{{font-size:15px}}</style><rect width="1200" height="800" fill="#f6f8f8"/><text x="36" y="48" class="title">{p['id']} · 分体外罩试配投影</text><text x="36" y="85" class="label">CAD 坐标系：{frame}　单位：mm　版本：A12-A-WRIST02</text><text x="36" y="120" class="small">投影来自 STEP 实体。非制造批准图；安装衬垫、打印收缩与实际紧固效果待实物验证。</text>{''.join(panels)}<path d="M36 540H1164" stroke="#b8c5cc"/><text x="36" y="580" class="label">包络：X {bb.xlen:.2f} × Y {bb.ylen:.2f} × Z {bb.zlen:.2f}</text><text x="36" y="616" class="small">本零件下界：({bb.xmin:.3f}, {bb.ymin:.3f}, {bb.zmin:.3f})　上界：({bb.xmax:.3f}, {bb.ymax:.3f}, {bb.zmax:.3f})</text><text x="36" y="651" class="small">分缝：{axis} = ±0.20　名义缝隙：0.40　名义皮厚：2.60　夹紧螺钉通孔：Ø3.50</text><text x="36" y="686" class="small">两处 M3 夹紧站位（完整模块固定系）：{datums}　保留 A11 M3×20 / 六角螺母 / 垫圈</text><text x="36" y="726" class="small">3D CAD 是本试配零件几何定义。曲面壁厚与完整公差链未在本轮批准；不得据此加工承力件。</text><text x="36" y="767" class="small">STEP SHA256：{p['step_sha256']}</text></svg>'''
  text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
  target=folder/(p['id']+'.svg');target.write_text(text);records.append(dict(id=p['id'],step_sha256=p['step_sha256'],svg_sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
 (folder/'sources.json').write_text(json.dumps(dict(parts=records,scope='Orthographic source-BREP review sheets, not a released dimension/tolerance manufacturing drawing'),indent=2)+'\n');print('DRAWINGS',len(records))
if __name__=='__main__':main()
