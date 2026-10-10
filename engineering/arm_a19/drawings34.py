# SPDX-License-Identifier: CC-BY-NC-4.0
"""Source-bound nominal fit drawing issue for all current body parts."""
from pathlib import Path
import sys,json,csv,textwrap
import numpy as np
import cadquery as cq
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3,landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';PACK=ROOT/'manufacturing/candidates/arm-body-a19-integrated-fit'
sys.path.insert(0,str(HERE));import wrist16 as w
from hardware01 import points
from vendor import interfaces
c=w.c;g=c.cad
NOTES={
'A19-S19-fore-spine-RS03-ring':['Motor face in J4.rotor: Y104.5; native J5 axis X185 / Z0. 8mm plate, OD122 / central ID71.2.','Raised native seal relief: OD90.2, depth0.6. Do not move motor mating plane.','8xD4.5 motor holes; actual coordinates in current-native-hole-table.csv. M4x14 + washer0.8 => insertion5.2.','Four cover seats R57 at145/165/185/195deg; D3.5 through drill, D7.4 flat clearance.','Retain stock20x40x2 socket and original fore-cover seats. Extra socket drilling is intentional.'],
'A19-S19-RS03-to-J6-L':['Native J5 output plane Y40 in J5.rotor; OD70, plate10 thick. SixD4.5 holes.','M4x16 + washer0.8 => insertion5.2; verify real native6mm depth and entry chamfer.','J6 fixed interface centre X75 / Z-28.8; sixD4.5 holes on PCD51. J6 is actual RS10P, not RS02.','Existing J6 cover seats shiftedX20 with the complete local heatset/hardware set.','Use ordinary straight L webs; install output bolts before J6 blocks the shaft access.'],
'A19-C19-fore-dorsal':['Same selected long swept outline; original fixing seats retained.','End plane X119 in J4.rotor; nominal1mm planar seam to J5 cowl envelope startingX120.','Local RS03 bracket clearance is based on axis offset cuts0.5mm; not a tolerance stack guarantee.'],
'A19-C19-fore-ventral':['Same selected long swept outline; original fixing seats retained.','End plane X119 in J4.rotor. Local inner relief from actual downstream carrier at J5=115..130deg.','Shape and mounts must match current STEP; do not print an untrimmed A17 fore cover.'],
'A19-C21-J5-cowl-a':['Upper split curved carapace over actual RS03. Rear service window26x18 is a placeholder clearance.','Four cover stations shared with lower cowl: R57,145/165/185/195deg; split ownership as STEP.','DIN7984 M3x16 / nutM3 / DIN125 washers; counterboreD7.4 depth1, tab3 thick, floor2.','Low headH2 plus0.5 washer protrudes1.5 above tab; no thick flush crown in J6 swept space.'],
'A19-C21-J5-cowl-b':['Lower split curved carapace over actual RS03; preserve seam and retained rear service opening.','DIN7984 M3x16 / nutM3 / DIN125 washers; counterboreD7.4 depth1, tab3 thick, floor2.','Nominal grip10.5 + head washer0.5; rear thread5, nut2.4, exposed2.6.','Install rear nuts before cowls. Tool31 only checks nominal straight shaft, not real wrench/nut retention.'],
'A19-S22-shoulder-foot-12mm-R6':['Shoulder axis X0/Z114; motor mating planeY68.5 in J1.rotor. Face12, OD134/ID80.','Foot110x104.5x8; bottomZ30. FourD5.6 centresX+/-38,Y+/-28. Inner rootR6.','Native tenD4.5 motor holes; frontD9.8 counterboresdepth4 retain8mm grip.','Original M4x12 + washer0.8 => insertion3.2. Keep actual mounting centres.','Four R64 cover seats45/135/225/315deg retain8mm underneath ordinary open radial pockets.'],
'A19-C22-J2-cowl-b':['Lower shoulder split cover locally relieved for current12mm root bracket.','Original fixing stations and upper cowl retained. Never mix with original8mm shoulder plate.']}

def main():
 path=OUT/'manifest.json';d=json.loads(path.read_text());parts=[p for p in d['parts'] if p['role'] in ['printed_cover','printed_structure','purchased_structure']];assert len(parts)==47
 target=PACK/'drawings';target.mkdir(exist_ok=True);file=target/'47-current-part-fit-drawings.pdf';pdf=canvas.Canvas(str(file),pagesize=landscape(A3));pdf.setTitle('Odradek A19 - 47 current part nominal fit drawings')
 pdf.setAuthor('Auromix / Odradek');records=[]
 def txt(x,y,text,size=8,bold=False):
  pdf.setFont('Helvetica-Bold' if bold else 'Helvetica',size);pdf.drawString(x*mm,y*mm,text)
 def line(a,b):pdf.line(a[0]*mm,a[1]*mm,b[0]*mm,b[1]*mm)
 for index,p in enumerate(parts,1):
  src=ROOT/p['step_path'];assert c.sha(src)==p['step_sha256'];s=cq.importers.importStep(str(src)).val();assert s.isValid()
  bb=s.BoundingBox();lo=np.array([bb.xmin,bb.ymin,bb.zmin]);hi=np.array([bb.xmax,bb.ymax,bb.zmax]);samples=[]
  for edge in s.Edges():
   count=2 if edge.geomType()=='LINE' else 96
   samples.append(np.array([edge.positionAt(float(t)).toTuple() for t in np.linspace(0,1,count)]))
  pdf.setStrokeColorRGB(.25,.31,.35);pdf.setLineWidth(.16*mm);pdf.rect(10*mm,10*mm,400*mm,277*mm)
  txt(17,277,p['id'],13,True);txt(17,268,f"Frame {p['frame']} | {p['role']} | mm | NOMINAL SUPPORTED FIT ISSUE",9)
  txt(17,259,'STEP defines geometry. All BREP edges shown, including hidden edges. Each view has its own stated scale.',8)
  views=[]
  for k,(label,axes) in enumerate([('XY',(0,1)),('XZ',(0,2)),('YZ',(1,2))]):
   mn=lo[list(axes)];mx=hi[list(axes)];span=mx-mn;scale=min(105/max(span[0],1),117/max(span[1],1),1.2);origin=np.array([24+130*k,117.])
   txt(origin[0],247,label+' / positive axes right and up',8,True)
   pdf.setStrokeColorRGB(.18,.23,.27);pdf.setLineWidth(.14*mm)
   for pts in samples:
    q=(pts[:,axes]-mn)*scale+origin;path2=pdf.beginPath();path2.moveTo(q[0,0]*mm,q[0,1]*mm)
    for a,b in q[1:]:path2.lineTo(a*mm,b*mm)
    pdf.drawPath(path2)
   pdf.setStrokeColorRGB(.55,.40,.20);pdf.setLineWidth(.15*mm)
   # Overall dimensions use exact CAD bounding box, not mesh extents.
   y=origin[1]-6;line([origin[0],y],[origin[0]+span[0]*scale,y])
   for x in [origin[0],origin[0]+span[0]*scale]:line([x-1.2,y-1.2],[x+1.2,y+1.2])
   x=origin[0]-5;line([x,origin[1]],[x,origin[1]+span[1]*scale])
   for y2 in [origin[1],origin[1]+span[1]*scale]:line([x-1.2,y2-1.2],[x+1.2,y2+1.2])
   txt(origin[0],103,f'W {span[0]:.3f} / H {span[1]:.3f} / scale {scale:.4f}',8)
   txt(origin[0],97,f'CAD lower-left {label}: {mn[0]:.3f}, {mn[1]:.3f}',7)
   views.append(dict(axes=label,mm_on_page_per_cad_mm=scale,minimum_mm=mn.tolist(),maximum_mm=mx.tolist()))
  notes=NOTES.get(p['id'],[p.get('note') or p.get('material','Retained part; source STEP and current assembly govern.'),'Retained nominal source geometry. Critical pilots, bearing seats and nut fit require physical measurement.'])
  y=85
  for note in notes:
   for text in simpleSplit(note,'Helvetica',8,380*mm):txt(17,y,text,8);y-=4.5
  assert y>40,(p['id'],y)
  txt(17,34,'No metal GD&T or general tolerance released. Calibrate printer and measure real hardware before drilling critical features.',8)
  txt(17,27,'Printed structural parts require external support, all power off and no payload. Purchased steel/aluminum parts are not printed.',8)
  txt(17,19,'STEP SHA256 '+p['step_sha256'][:24]+'... | Source assembly '+c.sha(OUT/'manifest.json')[:16]+'...',7)
  txt(373,19,f'{index} / {len(parts)}',8)
  records.append(dict(page=index,id=p['id'],frame=p['frame'],step_sha256=c.sha(src),bbox_mm=np.r_[lo,hi].tolist(),views=views));pdf.showPage()
  print('DRAW34',index,p['id'],flush=True)
 pdf.save()
 features=[];inf=interfaces();inf[4]=w.interface()
 assert [x['model'] for x in inf]==[j['model'] for j in d['layout']['joints']]
 for interface in inf:
  for pattern,origin in [('fixed_front_fasteners',interface['fixed_mm']),('output_fasteners',interface['out_mm'])]:
   for k,delta in enumerate(points(interface,pattern),1):
    xyz=np.array(origin)+delta;features.append(dict(joint=interface['joint'],model=interface['model'],pattern=pattern,index=k,frame=interface['joint']+('.fixed' if pattern.startswith('fixed') else '.rotor'),x_mm=xyz[0],y_mm=xyz[1],z_mm=xyz[2],axis_x=interface['n'][0],axis_y=interface['n'][1],axis_z=interface['n'][2],drawing=interface['model_source'][pattern].get('drawing','See original source dimension record')))
 with (target/'current-native-hole-table.csv').open('w') as fp:
  writer=csv.DictWriter(fp,fieldnames=list(features[0]));writer.writeheader();writer.writerows(features)
 # Independently check the new J5 plate holes against their own exact STEP.
 verified=[]
 for id,pattern,origin,offset,depth in [('A19-S19-fore-spine-RS03-ring','fixed_front_fasteners',inf[4]['fixed_mm'],[185,62,0],8),('A19-S19-RS03-to-J6-L','output_fasteners',inf[4]['out_mm'],[0,0,0],10)]:
  p=next(x for x in parts if x['id']==id);shape=cq.importers.importStep(str(ROOT/p['step_path'])).val();n=np.array(inf[4]['n'])
  for k,delta in enumerate(points(inf[4],pattern),1):
   q=np.array(origin)+offset+delta;probe=g.cyl(q-n*.02,n,1.95,depth+.04);vol=shape.intersect(probe).Volume();assert vol<1e-5,(id,k,vol)
   verified.append(dict(id=id,index=k,hole_central_probe_diameter_mm=3.9,intersection_mm3=vol))
 report=dict(revision='A19-CURRENT-DRAWINGS34',source_assembly_sha256=c.sha(OUT/'manifest.json'),pdf_sha256=c.sha(file),pages=records,current_native_hole_table_sha256=c.sha(target/'current-native-hole-table.csv'),new_J5_native_hole_CAD_checks=verified,production_release=False,scope='47 exact source BREP all-edge orthographics with nominal bbox dimensions, current native interface coordinates, and14 new J5 central bore checks. Not hidden-line removal, full feature GD&T, sliced/printed tolerance, real mating or metal qualification.')
 (target/'drawing-source-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('DRAWINGS34_DONE',len(parts),len(features),len(verified),flush=True)
if __name__=='__main__':main()
