# SPDX-License-Identifier: CC-BY-NC-4.0
"""A12 module 01: original two-piece J2 shield over pinned full-size RS04.

Dimensions mm, J2.fixed coordinates. Geometry prototype, not print release.
Never changes A11 or the canonical base. Supplier STEP stays in ignored work/.
"""
from pathlib import Path
import sys,json,math,hashlib
import numpy as np,cadquery as cq,trimesh
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'engineering/arm_a11'))
import interfaces as c
b=c.legacy
OUT=Path(__file__).parent/'build';BASE=ROOT/'engineering/arm_a11/build'
POLY=[(-70,-26),(-56,-51),(-26,-66),(12,-66),(50,-49),(67,-25),(69,5),(64,40),(40,65),(0,73),(-40,65),(-65,38),(-73,0)]
STATIONS=[(73,1.0),(83,1.02),(113.35,1.02),(134,.98),(151,.93)]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def loft(stations,inset=0):
 wp=cq.Workplane(cq.Plane(origin=b.V([0,stations[0][0],0]),normal=b.V([0,1,0]),xDir=b.V([1,0,0])))
 for i,(y,scale) in enumerate(stations):
  if i:wp=wp.workplane(offset=y-stations[i-1][0])
  # Parallel inward offsets keep the silhouette and a proper shell cavity.
  from shapely.geometry import Polygon
  pts=list(Polygon([(x*scale,z*scale) for x,z in POLY]).buffer(-inset,join_style=2).exterior.coords)[:-1]
  wp=wp.polyline([(x,-z) for x,z in pts]).close()
 return wp.loft(ruled=False).val()

def box(p,size):return cq.Solid.makeBox(*size,b.V(p))
def folded_cap(s,intercept):
 # Two deliberate oblique rear planes meet at the dorsal seam/ridge.
 # The cavity gets identical planes set2.6mm inward, so this remains a shell.
 for sign in [-1,1]:
  poly=[(-140,-10),(140,-10),(140,intercept-sign*.14*140),(-140,intercept+sign*.14*140)]
  clip=cq.Workplane('XY').workplane(offset=-110).polyline(poly).close().extrude(220).val()
  s=s.intersect(clip).fix()
 return s
def mesh(s):
 v,f=s.tessellate(.12,.15)
 m=trimesh.Trimesh([x.toTuple() for x in v],f,process=True)
 m.merge_vertices(digits_vertex=4);m.remove_unreferenced_vertices()
 assert s.isValid() and len(s.Solids())==1
 assert m.is_watertight and m.is_winding_consistent and len(m.split())==1
 return m

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 d=json.loads((BASE/'manifest.json').read_text())
 assert sha(BASE/'manifest.json')=='3b9a2291509e0666eeb8d9e73c320538a4235337ffa10af1d1915665a819b559'
 outer=folded_cap(loft(STATIONS),150)
 cavity=folded_cap(loft([(71,1.0),(83,1.02),(113.35,1.02),(134,.98),(150,.932)],2.6),147.4)
 shell=outer.cut(cavity,tol=1e-5).fix()
 # Positively enforce original housing clearance, not a stylized smaller motor.
 shell=shell.cut(b.cyl([0,71,0],[0,1,0],61.4,58.0),tol=1e-5).fix()
 # Two reused M3 clamp stations. Ribs link the clamps to the shell underside.
 for sign in [-1,1]:
  shell=shell.fuse(b.cyl([-6,113.35,sign*65],[1,0,0],5.5,12)).fix()
  shell=shell.fuse(box([-6,109.35,64 if sign>0 else -78],[12,8,14])).fix()
  shell=shell.intersect(outer).fix()
  shell=b.drill(shell,[-22,113.35,sign*65],[1,0,0],3.5,44).fix()
 # Boss unions must not undo the explicit motor-case clearance.
 shell=shell.cut(b.cyl([0,71,0],[0,1,0],61.4,58.0),tol=1e-5).fix()
 # Nominal head, washer and captive nut seats from the unchanged hardware.
 import refine
 for p in d['parts']:
  if p['role']=='hardware' and p['id'].startswith('J2-armour-'):
   s=cq.importers.importStep(str(BASE/'step'/(p['id']+'.step'))).val()
   cut=refine.clearance(p,s)
   if cut is not None:shell=shell.cut(cut,tol=1e-5).fix()
 # Three underside/rear cooling openings: no narrow decorative slit maze.
 for x in [-43,-27,26]:shell=shell.cut(box([x,91,-100],[12,24,39]),tol=1e-5).fix()
 # Shoulder bridge belongs to upstream rotor; transform into J2.fixed datum.
 support=cq.importers.importStep(str(BASE/'step/P01-shoulder-monobloc.step')).val().translate([0,0,-90])
 for delta in [(0,0,0),(.4,0,0),(-.4,0,0),(0,.4,0),(0,-.4,0),(0,0,.4),(0,0,-.4)]:shell=shell.cut(support.translate(delta),tol=1e-5).fix()
 parts=[]
 for suffix,p,size in [('left',[-110,-5,-110],[109.8,170,220]),('right',[.2,-5,-110],[109.8,170,220])]:
  s=shell.intersect(box(p,size)).fix();m=mesh(s);id='A12-201-J2-shield-'+suffix
  cq.exporters.export(s,str(OUT/(id+'.step')));m.export(OUT/(id+'.stl'))
  parts.append(dict(id=id,frame='J2.fixed',role='non_load_cover_geometry_prototype',solid_count=1,volume_mm3=s.Volume(),bbox_mm=m.bounds.tolist(),vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist(),step_sha256=sha(OUT/(id+'.step')),stl_sha256=sha(OUT/(id+'.stl'))))
 route=[[36*math.cos(t),134,-14-36*math.sin(t)] for t in np.linspace(0,math.pi,49)]
 report=dict(revision='A12-A-shoulder01',status='selected_style_geometry_prototype_not_print_release',baseline_manifest_sha256=sha(BASE/'manifest.json'),replaced_parts=['J2-armour-A','J2-armour-B'],parts=parts,retained_hardware=[h['id'] for h in d['hardware'] if h['id'].startswith('J2-armour-')],shell_nominal_skin_mm=2.6,split_gap_mm=.4,radial_motor_clearance_target_mm=1.4,wire_reservation=dict(frame='J2.fixed',centreline_mm=route,reservation_diameter_mm=10,curve_radius_mm=36,status='static_space_reservation_only_not_actual_harness',notes=['This U arc does NOT join rotary-side endpoints or establish a full harness route.','Not a selected coax bend radius; real cable, terminals and strain relief must be fixed first.','Motion, torsion, cooling and plug clearances remain unverified.']),supplier_partition_sha256={n:sha(ROOT/'work/arm-a10/vendor'/n) for n in ['J2-stator.step','J2-external-output.step']},limitations=['Attachment ribs are nominal split clamps; grip, liner, vibration and practical removal not qualified.','Three vents are planned openings, not thermal validation.','J3, bridge, root, elbow, wrist and link armour are not yet A12 redesigned.','Raw STLs are in J2 object coordinates, NOT sliced, bed-placed or released print files.'])
 (OUT/'manifest.json').write_text(json.dumps(report,separators=(',',':'))+'\n')
 print('A12_SHOULDER',[(p['id'],[round(x,2) for x in np.ptp(p['vertices_mm'],axis=0)]) for p in parts],flush=True)

if __name__=='__main__':main()
