# SPDX-License-Identifier: CC-BY-NC-4.0
"""Wrist02 original split non-load shields around unchanged full-size actuators.
All dimensions mm. Nominal fit solids, not an operating or load release.
"""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np,cadquery as cq,trimesh
from shapely.geometry import Polygon
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build';BASE=ROOT/'engineering/arm_a11/build'
sys.path.insert(0,str(ROOT/'engineering/arm_a11'));import interfaces as c;import refine
b=c.legacy
import collision as collision
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def box(p,size):return cq.Solid.makeBox(*size,b.V(p))
def loft(axis,stations,inset=0):
 # stations: axial position, actual radial polygon; winding plane made explicit.
 axes=[i for i in range(3) if i!=axis];n=np.eye(3)[axis];u=np.eye(3)[axes[0]];v=np.cross(n,u)
 first=np.zeros(3);first[axis]=stations[0][0];wp=cq.Workplane(cq.Plane(origin=b.V(first),normal=b.V(n),xDir=b.V(u)))
 for i,(pos,poly) in enumerate(stations):
  if i:wp=wp.workplane(offset=pos-stations[i-1][0])
  poly=Polygon(poly).buffer(-inset,join_style=2);assert poly.geom_type=='Polygon' and not poly.is_empty
  pts=list(poly.exterior.coords)[:-1];sign=v[axes[1]];wp=wp.polyline([(x,y*sign) for x,y in pts]).close()
 return wp.loft(ruled=True).val()
def taper(poly,scale):return [(a*scale,b*scale) for a,b in poly]
def mesh(s):
 assert s.isValid() and len(s.Solids())==1,(s.isValid(),len(s.Solids()))
 # Unify coplanar CAD faces before tessellation; this preserves the BREP solid.
 s=s.clean().fix()
 for tolerance in [.14,.05,.02]:
  v,f=s.tessellate(tolerance,.12)
  for precision in [5,6,4]:
   m=trimesh.Trimesh([x.toTuple() for x in v],f,process=True);m.merge_vertices(digits_vertex=precision);m.remove_unreferenced_vertices()
   m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
   if m.is_watertight and m.is_winding_consistent and len(m.split())==1:return m
  print('TESSELLATION_RETRY',tolerance,len(m.faces),m.is_watertight,m.is_winding_consistent,flush=True)
 cq.exporters.export(s,str(ROOT/'work/arm-a12/wrist02/mesh-diagnostic.step'))
 m.export(ROOT/'work/arm-a12/wrist02/mesh-diagnostic.stl')
 raise AssertionError('Closed CAD tessellation failed; diagnostic is local only')

def clearance(s):
 result=s
 for d in [(0,0,0),(.5,0,0),(-.5,0,0),(0,.5,0),(0,-.5,0),(0,0,.5),(0,0,-.5)]:result=result.fuse(s.translate(d)).fix()
 return result

def main():
 OUT.mkdir(exist_ok=True);(OUT/'step').mkdir(exist_ok=True);(OUT/'stl-object').mkdir(exist_ok=True)
 D=json.loads((BASE/'manifest.json').read_text());assert sha(BASE/'manifest.json')=='3b9a2291509e0666eeb8d9e73c320538a4235337ffa10af1d1915665a819b559'
 profile5=[(-64,-5),(-49,-32),(-20,-48),(15,-48),(40,-25),(48,0),(42,26),(18,48),(-15,54),(-46,35)]
 profile7=[(-48,-10),(-43,-31),(-24,-44),(8,-47),(34,-38),(46,-17),(48,8),(39,35),(15,50),(-14,50),(-39,32)]
 specs=[
  dict(j=5,axis=1,split=0,stations=[(36.5,taper(profile5,1)),(48,taper(profile5,1.025)),(70,taper(profile5,1.025)),(86,taper(profile5,1)),(94,taper(profile5,.98))],inner_positions=[34,48,70,86,91.4],motor_keepout=(1,[0,34,0],44.7,54),front_opening=None),
  dict(j=6,axis=2,split=0,stations=[(49.4,[(-94,-18),(-92,-28),(-45,-34),(16,-35),(34,-23),(37,0),(34,23),(16,35),(-45,34),(-92,28)]),(75,[(-63,-18),(-60,-30),(-33,-35),(17,-35),(34,-23),(37,0),(34,23),(17,35),(-33,35),(-60,30)]),(96,[(-40,-21),(-34,-34),(-15,-36),(15,-36),(34,-22),(37,0),(34,22),(15,36),(-15,36),(-34,34)]),(106,[(-34,-18),(-25,-31),(-10,-35),(12,-35),(31,-22),(35,0),(31,22),(12,35),(-10,35),(-25,31)])],inner_positions=[47.4,75,96,103.4],motor_keepout=(2,[0,45,0],29.7,56),front_opening=None),
  dict(j=7,axis=0,split=1,stations=[(-32,taper(profile7,.735)),(-22,taper(profile7,.755)),(9,taper(profile7,.775)),(30,taper(profile7,1)),(51,taper(profile7,1)),(61,taper(profile7,.985))],inner_positions=[-29.4,-22,9,30,51,62],motor_keepout=(0,[-28,0,0],29.7,61),front_opening=True)]
 parts=[];hardware=[];provenance={};discarded=[]
 for spec in specs:
  j=spec['j'];axis=spec['axis'];n=np.eye(3)[axis];st=spec['stations'];outer=loft(axis,st);inner=loft(axis,[(p,st[i][1]) for i,p in enumerate(spec['inner_positions'])],2.6)
  shell=outer.cut(inner,tol=1e-5).fix()
  a,org,r,l=spec['motor_keepout'];org=np.array(org,float)
  # Coordinates are actual X/Y/Z; axis2 origin needs its axial Z component.
  if j==6:org=np.array([0,0,45.])
  keepout=b.cyl(org,np.eye(3)[a],r,l);shell=shell.cut(keepout,tol=1e-5).fix()
  if j==7:
   shell=shell.cut(b.cyl([31.8,0,0],[1,0,0],42.8,27),tol=1e-5).fix()
   shell=shell.cut(b.cyl([56.8,0,0],[1,0,0],31.4,12),tol=1e-5).fix()
  # Preserve the two existing M3 through-bolt stations on each split clamp.
  bolts=[p for p in D['parts'] if p['id'].startswith(f'J{j}-armour-') and 'machining' in p]
  for bolt in bolts:
   m=bolt['machining'];p=np.array(m['p']);dir=np.array(m['n']);boss=b.cyl(p,dir,5.7,m['plate'])
   # Connect the boss to the actual shell sidewall before any keepout recut.
   axes=[k for k in range(3) if k!=spec['split']];start=p.copy();start[spec['split']]=-6
   size=[12,12,12];start[axes[0]]-=6;start[axes[1]]-=6
   shell=shell.fuse(boss).fuse(box(start,size)).intersect(outer).fix()
   shell=b.drill(shell,p-dir*18,dir,3.5,48).fix()
  shell=shell.cut(keepout,tol=1e-5).fix()
  if j==7:shell=shell.cut(b.cyl([31.8,0,0],[1,0,0],42.8,27),tol=1e-5).fix()
  # Recesses use unchanged head/washer/nut nominal geometry, not guessed seats.
  for p in D['parts']:
   if p['role']=='hardware' and p['frame']==f'J{j}.fixed':
    f=BASE/'step'/(p['id']+'.step');s=cq.importers.importStep(str(f)).val();cut=refine.clearance(p,s)
    if cut is not None:shell=shell.cut(cut,tol=1e-5).fix()
  # Positive rigid-frame structural relief, including J7 cartridge and retainer.
  supports=[]
  if j==6:supports.append(cq.importers.importStep(str(BASE/'step/P05-wrist-pitch-to-yaw.step')).val().translate([-75,0,0]))
  if j==7:
   supports.extend(cq.importers.importStep(str(BASE/'step'/(name+'.step'))).val() for name in ['J7-bearing-cage','J7-bearing-retainer'])
   supports.append(cq.importers.importStep(str(BASE/'step/P06-yaw-to-roll.step')).val().translate([-25,0,0]))
  for support in supports:shell=shell.cut(clearance(support),tol=1e-5).fix()
  # Actual neighbour screw clearances. J6 output screws share the J7 rigid
  # frame; J6 fixed screws receive a full annular yaw sweep, not pose hiding.
  if j==7:
   for part in D['parts']:
    if part['role']!='hardware' or not part['id'].startswith(('J6-output-','J6-fixed-')):continue
    source=cq.importers.importStep(str(BASE/'step'/(part['id']+'.step'))).val()
    if part['id'].startswith('J6-output-'):
     shell=shell.cut(clearance(source.translate([-25,0,0])),tol=1e-5).fix()
    else:
     bounds=source.BoundingBox();v=np.array(part['vertices_mm']);centre=np.mean([v.min(0),v.max(0)],axis=0);radius=math.hypot(centre[0],centre[1]);minor=max(bounds.xlen,bounds.ylen)/2+.5
     annulus=b.ring([-25,0,bounds.zmin-.5],[0,0,1],radius+minor,max(.1,radius-minor),bounds.zlen+1)
     shell=shell.cut(annulus,tol=1e-5).fix()
  # Discrete source-solid pockets are explicit design samples. Independent
  # intermediate poses are audited separately; this is no continuous sweep proof.
  if j in [6,7]:
   collision.ld.LAYOUT=D['layout'];collision.ld.TARGET['flange_frame']['translation_mm']=D['flange_from_J7_mm']
   cases=list(D['layout']['poses'].values())
   for joint,values in [(5,[-90,0,130]),(6,[-60,60]),(7,[-90,90])]:
    for angle in values:
     q=list(D['layout']['poses']['attention']);q[joint-1]=angle;cases.append(q)
   names=['P04-distal-socket','T04-stock-tube','T4-M4-4','T4-M4-4-washer','T4-crush-sleeve-4'] if j==6 else ['P04-distal-socket','P05-wrist-pitch-to-yaw']
   for name in names:
    meta=next(p for p in D['parts'] if p['id']==name);shape=clearance(cq.importers.importStep(str(BASE/'step'/(name+'.step'))).val())
    seen=set()
    for q in cases:
     frames,_=collision.ld.fk(q);p0,r0=frames[f'J{j}.fixed'];p1,r1=frames[meta['frame']];translation=r0.T@(p1-p0);rotation=r0.T@r1;signature=tuple(np.round(np.r_[translation,rotation.ravel()],5))
     if signature in seen:continue
     seen.add(signature);cut=collision.transformed(shape,translation,rotation)
     a=shell.BoundingBox();z=cut.BoundingBox()
     if any(getattr(a,k+'max')<=getattr(z,k+'min') or getattr(z,k+'max')<=getattr(a,k+'min') for k in ['x','y','z']):continue
     shell=shell.cut(cut,tol=1e-5).fix()
  # One service/vent outlet per shell, visible on the rear rather than random slits.
  if j==5:shell=shell.cut(box([-29,83,-61],[20,19,17]),tol=1e-5).fix()
  if j==6:
   shell=shell.cut(box([-62,-9,57],[26,18,20]),tol=1e-5).fix()
   # Remove thin rear-mouth lips left by the sampled socket pockets. These
   # explicit symmetric scallops replace unprintable grazing edges in CAD.
   for y in [22,-42]:shell=shell.cut(box([-88,y,47],[25,20,15]),tol=1e-5).fix()
  if j==7:
   shell=shell.cut(box([-35,-13,21],[18,26,25]),tol=1e-5).fix()
   # Explicit rectangular carrier recess includes the observed J6 +20/+40
   # and coupled-pose contacts with >1 mm bounding-box allowance. This is
   # a local design relief, not proof for a continuously swept joint domain.
   shell=shell.cut(box([-14,-16,36.2],[26,32,6]),tol=1e-5).fix()
  for side in ['A','B']:
   at=[-180,-180,-180];size=[360,360,360];k=spec['split']
   if side=='A':at[k]=.2;size[k]=179.8
   else:size[k]=179.8
   s=shell.intersect(box(at,size)).fix();id=f'A12-WR02-J{j}-shield-{side}'
   solids=sorted(s.Solids(),key=lambda q:q.Volume(),reverse=True)
   if len(solids)>1:
    kept=solids[0];fraction=kept.Volume()/sum(q.Volume() for q in solids)
    print('TRIM_ISLANDS',id,fraction,[(q.Volume(),q.Center().toTuple()) for q in solids[1:]],flush=True)
    assert fraction>.95,'Relief destroyed a major cover section; redesign required'
    discarded.append(dict(id=id,retained_volume_fraction=fraction,removed=[dict(volume_mm3=q.Volume(),centroid_mm=q.Center().toTuple()) for q in solids[1:]],reason='Remove small disconnected tail slivers created by neighbouring-part relief; no disconnected printable pieces retained'))
    s=kept
   m=mesh(s)
   step=OUT/'step'/(id+'.step');stl=OUT/'stl-object'/(id+'.stl');cq.exporters.export(s,str(step));m.export(stl)
   parts.append(dict(id=id,frame=f'J{j}.fixed',role='non_load_split_cover_fit_prototype',vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),bbox_mm=m.bounds.tolist(),volume_mm3=s.Volume(),solid_count=1,step_sha256=sha(step),stl_sha256=sha(stl)))
   print('PART',id,np.round(np.ptp(m.vertices,axis=0),1),flush=True)
  hardware.extend(p['id'] for p in D['parts'] if p['role']=='hardware' and p['id'].startswith(f'J{j}-armour-'))
  for kind in ['stator','external-output']:
   path=ROOT/'work/arm-a10/vendor'/(f'J{j}-{kind}.step');provenance[path.name]=sha(path)
 report=dict(revision='A12-A-WRIST02',status='split_shield_geometry_fit_prototype_not_print_release',baseline_manifest_sha256=sha(BASE/'manifest.json'),whole_style_manifest_sha256=sha(ROOT/'engineering/arm_a12/whole_style01/build/style-surfaces.json'),parts=parts,discarded_relief_slivers=discarded,replaced_style_parts=['A12-W06-J5-fixed-guard','A12-W07-J6-fixed-guard','A12-W08-J7-fixed-guard'],retained_hardware=hardware,supplier_partition_sha256=provenance,nominal_wall_mm=2.6,split_gap_mm=.4,case_radial_keepout_gap_mm=1.2,case_contact='Existing clamp datums retained; no direct fastening to new supplier holes. Soft liners and physical retention test not completed.',wire_notes=['J5 underside/J6 rear/J7 dorsal openings are empty service ports.','Ports do not establish connector size, radius or a connected harness.','No through-bore in any motor is assumed.'],limitations=['Non-load-bearing cosmetic trial parts, not powered-operation guards.','No liner, clip registration, heat rejection, tolerance-stack or printer process qualification.','Source-neighbour relief uses ten explicit design poses; independent intermediate tests and all other A12 surfaces remain separate. No continuous path clearance is asserted.'])
 (OUT/'manifest.json').write_text(json.dumps(report,separators=(',',':'))+'\n');print('WRIST02_COMPLETE',len(parts),flush=True)
if __name__=='__main__':main()
