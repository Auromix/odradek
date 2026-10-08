# SPDX-License-Identifier: CC-BY-NC-4.0
"""Original print-bed STLs, stock tube DXF, dimensional views, grouped hardware BOM."""
from pathlib import Path
import json,hashlib,itertools,math,csv,zipfile,shutil
from collections import Counter
import numpy as np,trimesh,cadquery as cq,ezdxf
import interfaces as c
OUT=c.OUT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bom(d):
 motors=Counter(j['model'] for j in d['layout']['joints']);hardware=Counter();rows=[]
 for p in d['parts']:
  if p['role']!='hardware':continue
  name=p['material']
  if 'washer' in p['id']:
   dims=sorted(p['bbox_size_mm']);od=round(dims[-1],3);th=round(dims[0],3)
   parent=next((h for h in d['hardware'] if p['id']==h['id']+'-washer' and h['type']=='screw'),None)
   dia=parent['d'] if parent else 4 if 'T3-' in p['id'] or 'T4-' in p['id'] else 3
   name=f'steel flat washer M{dia}; OD{od:g}mm; thickness{th:g}mm'
   if dia==5:name+='; specified small OD9, NOT standard OD10; procure exact shim or enlarge pocket'
  hardware[name]+=1
 rows.extend(('motor',k,n,'Supplier source; dual encoders; CAN; delivered geometry check') for k,n in sorted(motors.items()))
 rows.extend(('hardware',k,n,'Nominal envelope; measure real fastener dimensions') for k,n in sorted(hardware.items()))
 rows.extend(('stock_tube',p['material']+f' L{p["tube_drawing"]["cut_length_mm"]}mm',1,'4xD8.2 THRU40; tolerance coupon') for p in d['parts'] if p['role']=='stock_tube')
 with (OUT/'hardware-BOM.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['category','specification','quantity','note']);w.writerows(rows)

def run():
 file=OUT/'manifest.json';d=json.loads(file.read_text());pr=OUT/'print-ready';pr.mkdir(exist_ok=True);draw=OUT/'drawings';draw.mkdir(exist_ok=True)
 checks=[]
 rotations=[]
 for perm in itertools.permutations(range(3)):
  for signs in itertools.product([-1,1],repeat=3):
   r=np.eye(3)[list(perm)]*np.array(signs)[:,None]
   if np.linalg.det(r)>.99:rotations.append(r)
 for p in d['parts']:
  if p['role'] not in ['printed_structure','printed_cover','fit_coupon']:continue
  v=np.array(p['vertices_mm']);f=np.array(p['triangles']);best=None
  for r in rotations:
   vr=v@r.T;size=np.ptp(vr,axis=0)
   if max(size)>250:continue
   # Lowest feasible height; largest flat bed contact breaks ties.
   faces=vr[f];flat=(np.ptp(faces[:,:,2],axis=1)<1e-4)&(abs(faces[:,:,2].mean(axis=1)-vr[:,2].min())<1e-4)
   area=np.linalg.norm(np.cross(faces[flat,1]-faces[flat,0],faces[flat,2]-faces[flat,0]),axis=1).sum()/2
   score=(round(size[2],3),-round(area,2))
   if best is None or score<best[0]:best=(score,r,vr,size,area)
  assert best is not None,p['id']
  _,r,vr,size,area=best;t=-vr.min(axis=0);vb=vr+t
  m=trimesh.Trimesh(vb,f,process=True);assert m.is_watertight and m.is_winding_consistent,p['id'];assert len(m.split())==1,p['id']
  path=pr/(p['id']+'.stl');m.export(path)
  re=trimesh.load(path,force='mesh');assert re.is_watertight;assert np.max(abs(re.bounds[0]))<.0001;assert np.max(abs(re.extents-size))<.001
  inv=(vb-t)@r;err=float(np.max(abs(inv-v)));assert err<1e-7
  checks.append(dict(id=p['id'],role=p['role'],path='print-ready/'+path.name,sha256=sha(path),R_print_from_cad=r.tolist(),translation_print_mm=t.tolist(),size_print_mm=size.tolist(),single_component=True,watertight=True,flat_contact_area_mm2=float(area),roundtrip_error_mm=err,orientation_status='geometric bed suggestion; slicer supports and strength direction must be checked'))
  if p['role']!='fit_coupon':
   s=cq.importers.importStep(str(OUT/'step'/(p['id']+'.step'))).val();views=[]
   for name,n in [('XY',[0,0,1]),('XZ',[0,-1,0]),('YZ',[1,0,0])]:
    svg=cq.exporters.getSVG(s,opts={'width':300,'height':250,'marginLeft':14,'marginTop':14,'projectionDir':n,'showAxes':False,'showHidden':False,'strokeWidth':.8})
    start=svg.index('<svg');inner=svg[svg.index('>',start)+1:svg.rindex('</svg>')];views.append((name,inner))
   content=''.join(f'<g transform="translate({25+310*i},95)"><text y="-15">{name}</text>{inner}</g>' for i,(name,inner) in enumerate(views))
   dims=' × '.join(f'{x:.2f}' for x in p['bbox_size_mm'])
   page=f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420"><style>text{{font:14px Arial,sans-serif;fill:#243946}}</style><rect width="1000" height="420" fill="#fff"/><text x="25" y="30" style="font-size:22px">A10 / {p["id"]}</text><text x="25" y="55">CAD bounding XYZ: {dims} mm | {p["role"]} | original CAD frame</text>{content}<text x="25" y="375">Units mm. Views fit separately; measure STEP/STL, do not scale image. Print support and fit compensation not qualified.</text><text x="25" y="402">Printed fit prototype. No 3 kg load rating. Stock metal and supplier motors are excluded from print kit.</text></svg>'
   (draw/(p['id']+'.svg')).write_text('\n'.join(line.rstrip() for line in page.splitlines())+'\n')
 # Stock tube hole drawings: x axis length, y section width20, drilled through40.
 tubeaudit=[]
 for p in d['parts']:
  if p['role']!='stock_tube':continue
  spec=p['tube_drawing'];length=spec['cut_length_mm'];holes=spec['hole_offsets_from_start_mm']
  doc=ezdxf.new('R2010');doc.units=4;msp=doc.modelspace();msp.add_lwpolyline([(0,0),(length,0),(length,20),(0,20)],close=True)
  for x in holes:msp.add_circle((x,10),4.1)
  msp.add_text(f'{p["id"]}: 6061 tube20x40x2; L={length}; 4xD8.2 THRU40; deburr',dxfattribs={'height':3}).set_placement((0,26))
  msp.add_text('Hole X from cut end: '+', '.join(str(x) for x in holes)+'; centre Y=10; sleeves OD8 ID4.5 L36',dxfattribs={'height':2.5}).set_placement((0,-8))
  for a,bb in [(0,length)]+[(0,x) for x in holes]:
   msp.add_linear_dim(base=(0,-15-5*holes.index(bb) if bb in holes else -40),p1=(a,0),p2=(bb,0),angle=0,dimstyle='Standard').render()
  path=draw/(p['id']+'.dxf');doc.saveas(path);rd=ezdxf.readfile(path);cir=[e for e in rd.modelspace() if e.dxftype()=='CIRCLE'];assert len(cir)==4;assert all(abs(e.dxf.radius-4.1)<1e-7 for e in cir)
  assert sorted(e.dxf.center.x for e in cir)==sorted(holes);tubeaudit.append(dict(id=p['id'],cut_length_mm=length,holes_x_mm=holes,dxf_units_mm=True,hole_diameter_mm=8.2))
 # A specified narrow M5 shim avoids substituting an OD10 standard washer
 # into the compact source output pockets. Original profile for manufacture.
 doc=ezdxf.new('R2010');doc.units=4;space=doc.modelspace();space.add_circle((0,0),4.5);space.add_circle((0,0),2.7)
 space.add_text('M5 small-OD flat shim: steel; OD9 ID5.4 thickness1 mm; qty9; deburr both faces',dxfattribs={'height':1.5}).set_placement((-5,8))
 doc.saveas(draw/'M5-small-OD-shim.dxf')
 # Group purchasing by exact modeled specification, not by visual object name.
 bom(d)
 report=dict(manifest_sha256=sha(file),status='unpowered_supported_geometry_assembly_prototype',bed_mm=[250]*3,print_files=len(checks),assembly_prints=sum(q['role']!='fit_coupon' for q in checks),fit_coupons=sum(q['role']=='fit_coupon' for q in checks),parts=checks,tube_drawings=tubeaudit,scope='STL topology, positive bed coordinates, dimensions, inverse transform and nominal hardware only. No sliced print or physical assembly test.')
 (OUT/'print-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (draw/'index.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>A10 part drawings</title><style>body{font-family:sans-serif;background:#e8edef;margin:30px}img{display:block;width:100%;max-width:1100px;margin:25px 0;box-shadow:0 2px 12px #0002}h1{font-weight:500}</style><h1>A10 — original print part views</h1><p>Fit prototype • STEP/STL defines dimensions • no rated-load release</p>'+''.join(f'<img alt="{p.stem}" src="{p.name}">' for p in sorted(draw.glob('*.svg'))))
 print('MANUFACTURE',len(checks),'print files',len(tubeaudit),'tube DXF',flush=True)

def archive():
 name='odradek-a10-long-print-validation';path=OUT/(name+'.zip');d=json.loads((OUT/'manifest.json').read_text());wanted=[OUT/'odradek-a10-long-validation.blend',OUT/'print-audit.json',OUT/'hardware-BOM.csv',OUT/'assembly-guide.md',OUT/'print-README.md',OUT/'parts.json',OUT/'manifest.json',OUT/'feasibility.json',OUT/'collision-full.json',OUT/'collision-supplier.json',OUT/'motion-context-audit.json',OUT/'tool-access-audit.json',OUT/'blender-audit.json']+list((OUT/'print-ready').glob('*.stl'))+list((OUT/'drawings').glob('*'))+[OUT/'step'/(p['id']+'.step') for p in d['parts'] if p['role'] in ['printed_structure','printed_cover','fit_coupon']]
 assert all(p.exists() for p in wanted)
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  for p in wanted:z.write(p,name+'/'+p.relative_to(OUT).as_posix())
  for filename in ['index.html','THREE-LICENSE.txt']:z.write(c.ROOT/'docs/viewers/arm-body-a10'/filename,name+'/viewer/'+filename)
  z.write(c.ROOT/'LICENSE',name+'/LICENSE')
  z.write(c.ROOT/'docs/engineering/arm-body-a10-validation.md',name+'/VALIDATION.md')
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None;assert len([n for n in z.namelist() if n.endswith('.stl')])==49
 (OUT/'archive-audit.json').write_text(json.dumps(dict(archive=path.name,manifest_sha256=sha(OUT/'manifest.json'),sha256=sha(path),files=len(wanted)+4,crc_pass=True,stl_files=49,one_root=name),indent=2)+'\n')
 print('ARCHIVE',path.stat().st_size,flush=True)
if __name__=='__main__':
 import sys
 archive() if '--archive' in sys.argv else bom(json.loads((OUT/'manifest.json').read_text())) if '--bom' in sys.argv else run()
