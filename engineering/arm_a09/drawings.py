# SPDX-License-Identifier: CC-BY-NC-4.0
"""Flat-profile plan from original CAD parameters; verify DXF against exported solid area."""
import json,math,sys,hashlib
from pathlib import Path
import ezdxf
from shapely.geometry import LineString
from shapely.ops import polygonize
ROOT=Path(__file__).resolve().parents[2]
def run(variant='slim'):
 out=ROOT/'engineering/arm_a09/build'/variant;file=out/'manifest.json';d=json.loads(file.read_text());checks=[];panels=[]
 for p in d['parts']:
  if p['role']!='cnc_plate':continue
  doc=ezdxf.readfile(out/'dxf'/f'{p["id"]}.dxf');assert doc.units==4
  lines=[LineString([tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]]) for e in doc.modelspace() if e.dxftype()=='LINE'];polys=list(polygonize(lines));circles=[e for e in doc.modelspace() if e.dxftype()=='CIRCLE'];assert len(polys)==1 and len(circles)==2
  area=polys[0].area-sum(math.pi*e.dxf.radius**2 for e in circles);expected=p['volume_mm3']/4;assert abs(area-expected)<.001
  spec=p['manufacturing'];assert all(abs(e.dxf.radius-2.25)<1e-5 for e in circles)
  actual=sorted((round(e.dxf.center.x,5),round(e.dxf.center.y,5)) for e in circles);wanted=sorted(tuple(round(v,5) for v in xy) for xy in spec['holes_xy_mm']);assert actual==wanted
  checks.append(dict(id=p['id'],units='mm',thickness_mm=4,dxf_closed_outer_wires=1,holes=2,area_error_mm2=abs(area-expected)))
  if not p['id'].endswith('-A'):continue
  index=len(panels);origin=[55,160+index*240];scale=2.3;points=spec['outer_xy_mm'];xmin=min(v[0] for v in points);ymax=max(v[1] for v in points)
  def xy(v):return [origin[0]+(v[0]-xmin)*scale,origin[1]+(ymax-v[1])*scale]
  path='M'+' L'.join(','.join(f'{z:.3f}' for z in xy(v)) for v in points)+' Z'
  circles_svg=''.join(f'<circle cx="{xy(v)[0]}" cy="{xy(v)[1]}" r="{2.25*scale}"/>' for v in spec['holes_xy_mm'])
  labels=' / '.join(f'({x:g}, {y:g})' for x,y in spec['holes_xy_mm'])
  tube=next(t for t in d['parts'] if t['id']==f'T0{3+index}-straight-tube');tube_length=tube['bbox_size_mm'][0]
  panels.append(f'<g><text x="55" y="{origin[1]-28}" class="title">{p["id"][:-1]}A / B · 4 mm 6061板</text><path d="{path}"/><g>{circles_svg}</g><text x="55" y="{origin[1]+110}" class="small">2×Ø4.5 通孔；孔心XY：{labels} mm</text><text x="55" y="{origin[1]+139}" class="small">配套直管：20×40×2 mm；锯切长度 {tube_length:g} mm；板/管间隙0.2 mm</text></g>')
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="800" viewBox="0 0 1000 800"><style>text{font-family:Arial,"PingFang SC",sans-serif;fill:#263b48}path,circle{fill:none;stroke:#385b70;stroke-width:1.4}.title{font-size:20px}.small{font-size:16px}</style><rect width="1000" height="800" fill="#f8fafb"/><text x="55" y="55" font-size="26">ODRADEK A09 · 平面轮廓与管材方案</text><text x="55" y="90" class="small">尺寸单位mm · 草案，未冻结端座紧固；不得据此直接下单整臂加工</text>'+''.join(panels)+'<text x="55" y="685" class="small">图形由同一CAD轮廓与孔位生成，显示比例随屏幕缩放。A/B为上下两块同轮廓侧板。</text><text x="55" y="718" class="small">管内须有金属防压隔套；端座连接螺钉、配合公差与外壳固定方式尚未冻结。</text><text x="55" y="751" class="small">本页只表达侧板轮廓与管材通孔，不是总装制造图。</text></svg>'
 (out/'flat-profile-plan.svg').write_text(svg)
 (out/'dxf-audit.json').write_text(json.dumps(dict(manifest_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),checks=checks,status='profile_geometry_only'),indent=2)+'\n');print('DXF AUDIT',variant,len(checks))
if __name__=='__main__':run(sys.argv[1] if len(sys.argv)>1 else 'slim')
