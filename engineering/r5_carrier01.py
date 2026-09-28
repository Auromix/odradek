#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R5-CARRIER01: one-branch nominal packaging, not a released gripper.

Original CAD + catalogue-derived envelopes. No vendor BREP is redistributed.
Run with the project's CadQuery environment. Axes: x radial, y tangent, z front.
Root origin is [R,0,20]; petal local hinge is [0,0,3.5].
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from scipy.special import betainc
from build_layout import moved
from r5_petal_form02 import box, vol, common, bbox, serial, sha
from head_mass04_study import geometry_properties, tensor_check
from screen_integrated_collisions import named_step

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-carrier01'
REV='R5-CARRIER01'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
P=dict(root_head_z_mm=20., R_mm=[31.,91.], fold_complete_R_mm=66.,
       q_deg=[0.,90.], crank_a_mm=8., crank_phase_deg=-45.,
       cam_center_y_mm=32., cam_shoulder_y_mm=28.5,
       guide_y_mm=[30.,34.], slot_width_mm=8.3, guide_wall_mm=3.,
       guide_centerline_R_step_mm=.25, bearing_center_y_mm=[-16.,16.],
       density_steel_kg_m3=7850., density_aluminium_kg_m3=2700.)
FINGERS={'UR':('upper','right',45.),'UL':('upper','left',135.),
         'LL':('lower','left',225.),'LR':('lower','right',315.)}
COLORS={'original steel':'#556a78','original aluminium':'#98a9ad',
        'catalogue bearing envelope':'#bec7cb','catalogue follower envelope':'#c6cdd1',
        'catalogue screw envelope':'#8a929a','custom pin envelope':'#85939c',
        'unknown electronics':'#ac8ac4','known petal':'#c0a668'}

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(data,indent=2,default=serial)+'\n')
def cyl(r,a,b,axis='y',x=0,z=0,y=0):
 origin={'y':(x,a,z),'z':(x,y,a),'x':(a,y,z)}[axis]
 direction={'y':(0,1,0),'z':(0,0,1),'x':(1,0,0)}[axis]
 return cq.Solid.makeCylinder(r,b-a,cq.Vector(*origin),cq.Vector(*direction))
def union(shapes):
 s=shapes[0]
 for t in shapes[1:]:s=s.fuse(t)
 return s.clean()
def xzpoly(poly,y0,y1):
 # The 2-D buffer is an explicitly polygonized nominal tool path.
 s=cq.Workplane('XY').polyline(list(poly.exterior.coords)[:-1]).close().extrude(y1-y0).val()
 return s.rotate((0,0,0),(1,0,0),90).translate((0,y1,0))
def hexsolid(af,a,b,axis='y',x=0,z=0,y=0,angle=0):
 r=af/math.sqrt(3)
 points=[(x+r*math.cos(angle+i*math.pi/3),z+r*math.sin(angle+i*math.pi/3)) for i in range(6)]
 if axis=='y':return xzpoly(__import__('shapely').geometry.Polygon(points),a,b)
 points=[(x+r*math.cos(angle+i*math.pi/3),y+r*math.sin(angle+i*math.pi/3)) for i in range(6)]
 return cq.Workplane('XY').polyline(points).close().extrude(b-a).translate((0,0,a)).val()
def pose(s,R,q,phi=0):
 t=math.radians(q);p=math.radians(phi)
 Ry=np.array([[math.cos(t),0,-math.sin(t)],[0,1,0],[math.sin(t),0,math.cos(t)]])
 Rz=np.array([[math.cos(p),-math.sin(p),0],[math.sin(p),math.cos(p),0],[0,0,1]])
 T=np.eye(4);T[:3,:3]=Rz@Ry;T[:3,3]=Rz@np.array([R,0,20.])
 return moved(s,T)
def azimuth(s,phi):return s.rotate((0,0,0),(0,0,1),phi)
def qR(R):return float(90*betainc(3,3,np.clip((91-R)/25,0,1)))
def separation(a,b):
 d=float(a.distance(b));v=common(a,b) if d<1e-7 else 0.
 return dict(distance_mm=d,overlap_mm3=v)
def broad(a,b):
 ba,bb=bbox(a),bbox(b)
 return bool(np.all(ba[0]<=bb[1]+1e-7) and np.all(bb[0]<=ba[1]+1e-7))

def build():
 rows=[]
 def add(name,s,group,representation,rho=None,mass=None,note=''):
  assert s.isValid() and len(s.Solids())==1,(name,len(s.Solids()))
  rows.append(dict(id=name,shape=s,group=group,representation=representation,
                   density_kg_m3=rho,catalogue_mass_kg=mass,note=note))
 # Split trunnions avoid drilling through the unchanged 18-mm FORM02 root.
 rotor=box(0,23,-11.8,11.8,-7.5,-3.5)
 for sign in [-1,1]:
  cheek=cyl(7.5,9.2,12.5);shoulder=cyl(5,12.5,13);journal=cyl(4,13,29 if sign==1 else 18.8)
  if sign==-1:cheek=cheek.mirror('XZ');shoulder=shoulder.mirror('XZ');journal=journal.mirror('XZ')
  rotor=union([rotor,cheek,shoulder,journal])
 for x in [7,17]:
  for y in [-4.5,4.5]:rotor=rotor.cut(cyl(1.6,-8,-3,axis='z',x=x,y=y))
 # Cross pin through the positive short shaft; torque locking is not friction.
 pinaxis=np.array([1.,0,1.])/math.sqrt(2);pinorigin=np.array([0,23.,0])-8*pinaxis
 pinhole=cq.Solid.makeCylinder(1.5,16,cq.Vector(*pinorigin),cq.Vector(*pinaxis))
 rotor=rotor.cut(pinhole).cut(cyl(1.25,-19,-11.5))
 add('rotor_split_trunnion_cradle',rotor,'rotor','original steel',7850,note='Monolithic manufacturing candidate; two short journals, no through shaft. Fits, fillets and pin retention unreleased.')
 # Separate side pedestals slide onto the journals before bolting to the foot.
 base=box(8,35,-24,24,-34,-30)
 for sign in [-1,1]:
  for x in [24,31]:base=base.cut(cyl(1.65,-35,-29,axis='z',x=x,y=16*sign))
 # Independent radial guide interface, not a commercial carriage hole pattern.
 for x in [13,30]:
  for y in [-8,8]:base=base.cut(cyl(2.25,-35,-29,axis='z',x=x,y=y))
 add('radial_carrier_foot',base,'carrier','original aluminium',2700,note='4xD4.5 mounting interface only; rail/block/backbone not selected or included.')
 for sign in [-1,1]:
  s=union([cyl(11,13,19),cyl(10,12,13),box(8,18,13,19,-26,-6),box(8,35,11,22,-30,-26)])
  # Two outward ears support removable caps; no M3 hole in the 1.5-mm annulus.
  for x in [0,10]:s=s.fuse(box(x-4,x+4,13,19,-18,-7))
  s=s.cut(cyl(9.5,13,20)).cut(cyl(8,11.5,13.01))
  for x in [0,10]:s=s.cut(cyl(1.25,12.5,20,x=x,z=-14)) # nominal M3 tap drill
  for x in [24,31]:s=s.cut(cyl(1.65,-31,-25,axis='z',x=x,y=16))
  cap=union([cyl(10,19,20)]+[box(x-4,x+4,19,20,-18,-7) for x in [0,10]])
  cap=cap.cut(cyl(8,18.5,20.5))
  for x in [0,10]:cap=cap.cut(cyl(1.65,18.5,20.5,x=x,z=-14))
  bearing=cyl(9.5,13,19).cut(cyl(4,12,20))
  if sign<0:s=s.mirror('XZ');cap=cap.mirror('XZ');bearing=bearing.mirror('XZ')
  tag='positive' if sign>0 else 'negative'
  add('bearing_pedestal_'+tag,s,'carrier','original aluminium',2700)
  add('outer_cap_'+tag,cap,'carrier','original steel',7850,note='D16 shoulder opening <= SKF D17; shield contact has not been tolerance-qualified.')
  add('SKF_607_8_2Z_'+tag,bearing,'bearing','catalogue bearing envelope',mass=.0072,note='8x19x6 catalogue annular allocation, not detailed supplier CAD.')
  for x in [0,10]:
   screw=union([cyl(1.5,14,20,x=x,z=-14),cyl(2.75,20,23,x=x,z=-14)])
   if sign<0:screw=screw.mirror('XZ')
   add('cap_M3x6_'+tag+f'_{x}',screw,'carrier','catalogue screw envelope',7850,note='ISO4762 nominal envelope; exact SKU/grade/thread engagement/torque TBD. Tap engagement is an intentional CAD intersection.')
  for x in [24,31]:
   # Bolt from below; conventional nut above side pedestal foot.
   screw=union([cyl(1.5,-34,-22,axis='z',x=x,y=sign*16),cyl(2.75,-37,-34,axis='z',x=x,y=sign*16)])
   nut=hexsolid(5.5,-26,-23.6,axis='z',x=x,y=sign*16).cut(cyl(1.5,-27,-23,axis='z',x=x,y=sign*16))
   add(f'foot_M3x12_{tag}_{x}',screw,'carrier','catalogue screw envelope',7850,note='Nominal envelope; nut contact only, no preload claim.')
   add(f'foot_M3_nut_{tag}_{x}',nut,'carrier','catalogue screw envelope',7850)
 # Detachable positive-y crank: outboard nut pocket is a genuine thin-web issue.
 cx=8/math.sqrt(2);cz=-cx
 profile=unary_union([Point(0,0).buffer(7,resolution=32),Point(cx,cz).buffer(5,resolution=32)]).convex_hull
 crank=xzpoly(profile,24.5,28.5).fuse(cyl(7,21,24.5))
 crank=crank.cut(cyl(4,20,30)).cut(cyl(2,24,29,x=cx,z=cz)).cut(pinhole)
 # Nut flat faces the shaft, leaving0.5mm nominal in the assembled condition.
 # A D10.4 service relief deliberately breaks into the shaft bore in the
 # rear hub only. It removes the earlier0.4mm sliver, while the4mm main
 # mounting plate still has2mm between D8 and D4. Install CFS off-shaft.
 nut_angle=math.radians(45)
 nut=hexsolid(7,21.3,24.5,x=cx,z=cz,angle=nut_angle).cut(cyl(2,21,25,x=cx,z=cz))
 pocket=cyl(5.2,20.9,24.5,x=cx,z=cz)
 crank=crank.cut(pocket)
 add('detachable_cam_crank',crank,'rotor','original steel',7850,note='4mm mounting seat,2mm main ligament between D8 shaft and D4 stud. Rear D10.4 service relief deliberately opens into D8 bore; no0.4mm metal sliver. CFS tightened off-shaft; net section and pin retention not strength released.')
 pin=cq.Solid.makeCylinder(1.5,14,cq.Vector(*(np.array([0,23,0])-7*pinaxis)),cq.Vector(*pinaxis))
 add('custom_D3_crosspin',pin,'rotor','custom pin envelope',7850,note='Unselected custom pin; end retention/fit/fatigue and tool path unresolved.')
 spacer=cyl(5,19,21).cut(cyl(4,18,22))
 add('positive_inner_ring_spacer',spacer,'rotor','original steel',7850,note='D10/D8x2 contacts only inner-ring abutment region. Crank crosspin locates the stack axially; zero nominal preload and no fit release.')
 washer=cyl(5,-20,-19).cut(cyl(1.6,-21,-18))
 add('negative_inner_ring_end_washer',washer,'rotor','original steel',7850,note='D10 abutment,1mm thick; negative shaft ends at -18.8 leaving0.2 nominal end gap.')
 endscrew=union([cyl(1.5,-20,-12),cyl(2.75,-23,-20)])
 add('negative_end_M3x8',endscrew,'rotor','catalogue screw envelope',7850,note='Nominal ISO4762 envelope, exact SKU/grade/preload TBD. Nominal tapped depth7.3; thread intersection intentional.')
 follower=union([cyl(4,28.5,35.5,x=cx,z=cz),cyl(2,20.5,28.5,x=cx,z=cz)])
 add('IKO_CFS4',follower,'rotor','catalogue follower envelope',mass=.004,note='D8 front-unit conservative envelope; rolling part y29.5..34.5. Catalogue mass excludes nut.')
 add('IKO_CFS4_supplied_nut',nut,'rotor','catalogue screw envelope',7850,note='Nominal AF7x3.2 envelope minus thread major diameter; calculated proxy mass, not catalogue mass.')
 # Real candidate root fastener stack. Threads are nominal cylinders.
 for x in [7,17]:
  for y in [-4.5,4.5]:
   name=f'{x}_{y:g}'
   screw=union([cyl(1.5,-12.5,3.5,axis='z',x=x,y=y),cyl(3,3.5,4.8,axis='z',x=x,y=y)])
   washer=cyl(3.5,-8,-7.5,axis='z',x=x,y=y).cut(cyl(1.6,-8.5,-7,axis='z',x=x,y=y))
   nut=hexsolid(5.5,-10.4,-8,axis='z',x=x,y=y).cut(cyl(1.5,-11,-7,axis='z',x=x,y=y))
   add('root_NBK_SSHS_M3_16_FT_'+name,screw,'rotor','catalogue screw envelope',7850,note='NBK head D6x1.3; head on FORM02 Z7; candidate underhead16. Mass is nominal solid proxy.')
   add('root_Wurth_51493_'+name,washer,'rotor','catalogue screw envelope',7850)
   add('root_Wurth_031093_'+name,nut,'rotor','catalogue screw envelope',7850)
 # Centreline kept exactly on STAGE01 at its sample stations. Width is new.
 rr=np.linspace(31,91,int(60/P['guide_centerline_R_step_mm'])+1)
 qa=np.radians(np.array([qR(x) for x in rr])-45)
 center=np.c_[rr+8*np.cos(qa),20+8*np.sin(qa)]
 line=LineString(center);outer=line.buffer(7.15,resolution=48);inner=line.buffer(4.15,resolution=48)
 guide=xzpoly(outer,30,34)
 for x in [45,94]:guide=guide.fuse(box(x-4,x+4,30,34,-16,20))
 guide=guide.cut(xzpoly(inner,29.9,34.1))
 for x in [45,94]:guide=guide.cut(cyl(2.25,29,35,x=x,z=-9))
 add('fixed_fold_guide',guide,'guide','original steel',7850,note='4mm plate, slot8.3/wall3; two D4.5 attachment holes at head x45/94,z-9. Hardening/curved-track contact/palm interface unqualified. Not a load-closed palm.')
 return rows,center

def petal(kind,hand):
 folder=ROOT/'engineering/generated/r5-petal-form02'/f'{kind}-{hand}'
 return {p.stem:cq.importers.importStep(str(p)).val().translate((0,0,-3.5)) for p in folder.glob('*.step') if not p.stem.startswith('R5-')}
def posed(rows,R,q,phi=0):
 return {r['id']:(azimuth(r['shape'],phi) if r['group']=='guide' else pose(r['shape'],R,q if r['group']=='rotor' else 0,phi)) for r in rows}

def continuous_certificate(rows):
 """Conservative boxes of construction primitives; no sampled-motion inference.

At q90, increasing either independent R only increases the radial coordinates
of that branch; C4 adjacent separating axes therefore cannot close. Pedestal
boxes are split at the actual construction pieces, avoiding a loose whole-part
box which combines the foot's width with the upper ring's inward edge.
"""
 def boxes(r):
  n=r['id'];ss=[]
  if n.startswith('bearing_pedestal'):
   ss=[cyl(11,13,19),cyl(10,12,13),box(8,18,13,19,-26,-6),box(8,35,11,22,-30,-26)]+[box(x-4,x+4,13,19,-18,-7) for x in [0,10]]
  elif n.startswith('outer_cap'):
   ss=[cyl(10,19,20)]+[box(x-4,x+4,19,20,-18,-7) for x in [0,10]]
  else:ss=[r['shape']]
  if n.endswith('negative') and len(ss)>1:ss=[s.mirror('XZ') for s in ss]
  covers=[box(*bbox(s)[:,0],*bbox(s)[:,1],*bbox(s)[:,2]) for s in ss]
  cover=union(covers);outside=vol(r['shape'].cut(cover));assert outside<1e-5,(n,outside)
  return covers,outside
 data={};containment=[]
 for f,(kind,hand,_) in FINGERS.items():
  entries=[]
  for r in rows:
   if r['group']=='guide':continue
   covers,outside=boxes(r);containment.append(dict(finger=f,part=r['id'],outside_cover_mm3=outside))
   for i,s in enumerate(covers):entries.append((r['id']+f':{i}',bbox(pose(s,31,90 if r['group']=='rotor' else 0))))
  for n,s in petal(kind,hand).items():entries.append(('FORM02_'+n,bbox(pose(s,31,90))))
  data[f]=entries
 results=[]
 for a,b in itertools.combinations(FINGERS,2):
  ang=(FINGERS[b][2]-FINGERS[a][2])%360;t=math.radians(ang)
  M=np.array([[math.cos(t),-math.sin(t),0],[math.sin(t),math.cos(t),0],[0,0,1]])
  best=(float('inf'),None,None,None)
  for na,ba in data[a]:
   for nb,bb in data[b]:
    corners=np.array(list(itertools.product(*zip(*bb))));v=corners@M.T;br=np.array([v.min(axis=0),v.max(axis=0)])
    delta=np.maximum(np.maximum(ba[0]-br[1],br[0]-ba[1]),0);d=float(np.linalg.norm(delta))
    # Check the chosen separation has the correct sign for every positive
    # radial translation, independently for the two branch coordinates.
    axes=np.where(delta>1e-8)[0];valid=[]
    va=np.array([1.,0,0]);vb=M@va
    for ax in axes:
     if ba[0,ax]>br[1,ax]:ok=va[ax]>=-1e-8 and vb[ax]<=1e-8
     else:ok=va[ax]<=1e-8 and vb[ax]>=-1e-8
     # A z-only separator is invariant to radial travel.
     if ok:valid.append(ax)
    assert valid,(a,b,na,nb,delta)
    lower=max(delta[ax] for ax in valid)
    if lower<best[0]:best=(float(lower),na,nb,valid)
  results.append(dict(pair=[a,b],lower_bound_mm=best[0]-1e-7,parts=[best[1],best[2]],separating_axes=best[3]))
 guide=next(r['shape'] for r in rows if r['group']=='guide');bg=bbox(guide)
 fold_bounds=[];package_bounds=[]
 for r in rows:
  b=bbox(r['shape']);yt=float(max(abs(b[:,1])))
  if r['group']=='guide':lo=b[0,0];hi=b[1,0]
  elif r['group']=='rotor':
   vals=[];maxvals=[]
   for x,z in itertools.product(b[:,0],b[:,2]):
    vals.append(-math.hypot(x,z) if x<0 and z>0 else min(x,-z))
    maxvals.append(math.hypot(x,z) if x>0 and z<0 else max(x,-z))
   lo=66+min(vals);hi=91+max(maxvals)
  else:lo=66+b[0,0];hi=91+b[1,0]
  if r['group']!='guide':
   assert lo>=55-2e-7 and yt<=35.5+2e-7,(r['id'],lo,yt)
   fold_bounds.append(dict(part=r['id'],continuous_R66_q0to90_radial_lower_mm=lo,abs_tangent_upper_mm=yt))
  package_bounds.append(dict(part=r['id'],independent_R31to91_q0to90_radius_upper_mm=math.hypot(hi,yt)))
 h=.25;q1=1.875*math.pi/2/25;q2=(10/math.sqrt(3))*math.pi/2/25**2
 path_second_bound=8*math.sqrt(q2*q2+q1**4)
 chord=path_second_bound*h*h/8;arc=4.15*(1-math.cos(math.pi/(4*48)))
 return dict(radial_q90_all_independent_R31_to66=dict(primitive_cover_containment=containment,pair_bounds=results,all_R_translation_monotonic_axes_verified=True),
   fold_or_mixed_body_to_body=dict(folding_R_min_mm=66,all_folding_bodies_radial_min_mm=55,any_branch_abs_tangent_max_mm=35.5,lower_bound_mm=19.5,part_bbox_extrema=fold_bounds,derivation='Exactly minimize x*cos(q)-z*sin(q) of every CAD bounding-box corner over0..90. Fixed carrier x>=-11; computed rotor bounds all exceed-11. Petal x>=0,z<=6 gives rho>=R-6. All |y|<=35.5. In mixed phase use the folding branch radial separator.'),
   fixed_guide_to_other_branch=dict(guide_radial_min_mm=bg[0,0],negative_body_tangent_extent_mm=24,continuous_lower_bound_mm=bg[0,0]-24,all_independent_phases=True),
   own_branch=dict(petal_bearing_circle_clearance_lower_mm=16.2857142857-11,petal_lower_leg_z_clearance_lower_mm=2.5,cradle_base_to_inner_shoulder_y_clearance_mm=.2,cheek_to_D16_housing_bore_radial_clearance_mm=.5,crank_to_cap_y_clearance_mm=1.,cam_lobe_to_cap_screw_z_clearance_lower_mm=11.25-(8/math.sqrt(2)+5),guide_to_non_follower_y_clearance_lower_mm=1.,bearing_journals_are_intentional_nominal_fit=True,proof='Petal strip |y|>=12 starts at x>=16.285714; positive q preserves radius and gives z>=-3.5. Upper support circles r<=11; all lower legs z<=-6, cap screws z<=-11.25. Cradle base |y|<=11.8; circular cheeks r7.5 pass D16 shoulder holes. Cam lobe center phase in [-45,+45] and radius5. Guide y>=30, non-follower rotor y<=29.'),
   follower_in_nominal_polygonized_groove=dict(slot_D_mm=8.3,follower_D_mm=8,centerline_second_derivative_bound_per_mm=path_second_bound,chord_deviation_upper_mm=chord,buffer_arc_chord_error_upper_mm=arc,radial_clearance_lower_mm=.15-chord-arc,scope='Nominal, undeformed catalogue envelope and polygonized groove only. Runout, manufacturing, bearing play, deflection, hardening and wear not included.'),
   mechanism_package_bounds=dict(parts=package_bounds,rotation_enclosing_D_upper_mm=2*max(x['independent_R31to91_q0to90_radius_upper_mm'] for x in package_bounds),excludes='FORM02 petal span; unselected rail/palm/motor/differential/skin enclosure',head_Z_min_mm=-17.,C4_internal_mechanism_is_not_bilaterally_symmetric=True),
   scope='C4 continuous cross-branch nominal envelope certificate for q(R) phases, not arbitrary q at R31. Bare FORM02 all-phase separation remains its separate certificate. Assembly self-contacts, preload, hard end stops and structural/thermal qualification are not certified.')

def export(rows,center):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'parts').mkdir(exist_ok=True)
 ledger=[]
 for r in rows:
  s=r['shape'];g=geometry_properties(s)
  mass=r['catalogue_mass_kg'] if r['catalogue_mass_kg'] is not None else g['volume_mm3']*(r['density_kg_m3'] or 0)*1e-9
  f=OUT/'parts'/(r['id']+'.step');cq.exporters.export(s,str(f));back=cq.importers.importStep(str(f)).val()
  assert back.isValid() and abs(vol(back)-vol(s))<1e-4
  item={k:v for k,v in r.items() if k!='shape'}|dict(source_step=str(f.relative_to(OUT)),sha256=sha(f),volume_mm3=g['volume_mm3'],mass_kg=mass,COM_part_m=g['com_m'],inertia_COM_part_axes_kg_m2=mass*g['inertia_per_mass_m2'],inertia_is_uniform_envelope_proxy=r['representation'].startswith('catalogue'),bbox_part_mm=bbox(s))
  if r['id']=='IKO_CFS4':item.update(outer_ring_spin_inertia_kg_m2=None,outer_ring_spin_sensitivity_upper_bound_kg_m2=6.4e-8,spin_note='Total4g allocation is a rigid-to-crank uniform envelope proxy. Actual ring/stud mass split and independent ring spin are unknown.0..m*R^2 is only an upper sensitivity interval, not a measured or identified inertia.')
  ledger.append(item)
 for label,R,q in [('open',91,0)]:
  actual=posed(rows,R,q);a=cq.Assembly(name=REV+'-'+label)
  for r in rows:a.add(actual[r['id']],name=r['id'],color=cq.Color(COLORS[r['representation']]))
  for n,s in petal('upper','right').items():a.add(pose(s,R,q),name='FORM02_'+n,color=cq.Color('#c9ae67' if n=='compliant_skin' else '#416b78'))
  a.save(str(OUT/(label+'.step')))
 # Four complete modules at the compact radial endpoint; geometry only.
 a=cq.Assembly(name=REV+'-four-C4-minimum-aperture')
 for f,(kind,hand,phi) in FINGERS.items():
  actual=posed(rows,31,90,phi)
  for r in rows:a.add(actual[r['id']],name=f+'_'+r['id'],color=cq.Color(COLORS[r['representation']]))
  for n,s in petal(kind,hand).items():a.add(pose(s,31,90,phi),name=f+'_FORM02_'+n,color=cq.Color('#c9ae67' if n=='compliant_skin' else '#416b78'))
 raw=OUT/'four-C4-minimum-aperture.step';a.save(str(raw))
 with raw.open('rb') as src,gzip.open(str(raw)+'.gz','wb',compresslevel=9) as dest:dest.write(src.read())
 raw.unlink()
 dump(OUT/'parts-manifest.json',dict(revision=REV,part_coordinates='Hinge at origin, except fixed guide already in head branch coords. Rotor rotates about -Y then translates to [R,0,20]. Carrier/bearing translate only. Entire branch rotates about head Z by phi. Internal C4 has no reflection.',parts=ledger,known_branch_nominal_mass_excluding_FORM02_kg=sum(r['mass_kg'] for r in ledger),scope='Assumed-material and catalogue envelope mass. No rail/palm/motor/differential/wires/complete electronics. Not whole-head mass.'))
 np.savetxt(OUT/'guide-centerline.csv',center,delimiter=',',header='radial_X_mm,head_Z_mm',comments='')
 return ledger

def section_screen(rows):
 """Nominal beam-section diagnostic of the actual relieved crank.
Not FEA, no allowable/yield/fatigue or stress-concentration conclusion.
"""
 crank=next(r['shape'] for r in rows if r['id']=='detachable_cam_crank')
 T=np.eye(4);u=1/math.sqrt(2);T[:3,:3]=[[u,0,-u],[0,1,0],[u,0,u]]
 sh=moved(crank,T);out=[];F=np.array([282*u,0,282*u])
 for s in [4.25,4.75,5.25,5.75]:
  records=[]
  for dx in [.04,.02]:
   slab=sh.intersect(box(s-dx/2,s+dx/2,0,40,-20,20));g=geometry_properties(slab)
   A=g['volume_mm3']/dx;I=g['inertia_per_mass_m2']*g['volume_mm3']*1e6/dx
   I[1,1]-=A*dx**2/12;I[2,2]-=A*dx**2/12
   c=g['com_m']*1000;M=np.cross(np.array([8,32,0])-c,F)
   C=-I[1,2];B=np.linalg.solve(np.array([[I[2,2],C],[C,I[1,1]]]),np.array([-M[2],M[1]]))
   v,_=slab.tessellate(.02,.05);v=np.array([p.toTuple() for p in v]);sigma=F[0]/A+(v[:,1:]-c[1:])@B
   records.append(dict(slice_width_mm=dx,area_mm2=A,centroid_y_t_mm=c[1:],I_about_y_mm4=I[1,1],I_about_t_mm4=I[2,2],I_tensor_yt_mm4=I[1,2],force_st_N=F[[0,2]],moment_syt_Nmm=M,maximum_abs_axial_plus_linear_bending_MPa=float(max(abs(sigma))),average_transverse_shear_MPa=F[2]/A,torsion_about_s_is_not_resolved_Nmm=M[0]))
  rel=max(abs(records[0][k]-records[1][k])/abs(records[1][k]) for k in ['area_mm2','I_about_y_mm4','I_about_t_mm4'])
  assert rel<.01
  out.append(dict(section_s_mm=s,convergence_relative_change=rel,result=records[1]))
 torque=282*8/math.sqrt(2)/1000;pinforce=torque/.004
 return dict(load=dict(follower_N=282,head_force='+Z at q90; normal-load-only conditional grip screen',application_in_crank_basis_mm=[8,32,0],catalogue_load_inputs='CAM-HARDWARE01, not a measured grasp'),basis='s=(x-z)/sqrt2 along center line; t=(x+z)/sqrt2 transverse; y tangent unchanged',
   actual_crank_sections=out,nominal_shaft_torque_Nm=torque,unnotched_D8_shaft_torsional_shear_MPa=16*torque*1000/(math.pi*8**3),D3_pin_double_shear_average_MPa=pinforce/(2*math.pi*1.5**2),
   removed_sliver=dict(previous_back_hub_ligament_mm=.4,current_service_relief_D_mm=10.4,deliberate_opening_to_shaft_bore=True,full_main_plate_thickness_mm=4,main_plate_root_to_stud_hole_nearest_ligament_mm=2,crosspin_line_to_relief_edge_min_mm=8-5.2-1.5),
   interpretation='Sections are between root-bore edge s4 and stud-bore edge s6. They include actual relief. Beam linear bending and average shear are diagnostics, not complete stresses; out-of-plane torsion, bore contact, crosspin bearing/notches, fatigue and preload require a separate analysis. No material allowable or FEA is asserted.')

def mass_summary(rows,ledger):
 # Use actual transformed CAD properties, not old nominal mass sums.
 byid={x['id']:x for x in ledger};states=[]
 for label,R,q in [('open',91,0),('folded',66,90),('minimum_aperture',31,90)]:
  pieces=[]
  for f,(kind,hand,phi) in FINGERS.items():
   for r in rows:
    s=posed([r],R,q,phi)[r['id']];g=geometry_properties(s);m=byid[r['id']]['mass_kg']
    pieces.append((m,g['com_m'],m*g['inertia_per_mass_m2']))
   for n,s in petal(kind,hand).items():
    rho={'frame':2700.,'retainer':2700.,'bearing_cover':1200.,'compliant_skin':1030.}.get(n)
    if rho is None:continue
    g=geometry_properties(pose(s,R,q,phi));m=g['volume_mm3']*rho*1e-9;pieces.append((m,g['com_m'],m*g['inertia_per_mass_m2']))
  m=sum(x[0] for x in pieces);c=sum(x[0]*x[1] for x in pieces)/m;I=np.zeros((3,3))
  for mi,ci,Ii in pieces:
   d=ci-c;I+=Ii+mi*((d@d)*np.eye(3)-np.outer(d,d))
  states.append(dict(state=label,R_mm=R,q_deg=q,known_mass_kg=m,COM_head_m=c,inertia_COM_head_axes_kg_m2=I,tensor_check=tensor_check(I)))
 return dict(states=states,per_branch_mass_by_group_kg={g:sum(x['mass_kg'] for x in ledger if x['group']==g) for g in ['rotor','carrier','bearing','guide']},whole_head_mass_kg=None,unknown_excluded=['rail and carriage','palm backbone and guide fixation screws','motor/transmission/differential','return mechanism and hard stops','all actual PCB/LED/connectors/cables','real central display/cameras'],mass_is_assumed_not_measured=True,CFS4_outer_ring_mass_split_and_spin_unidentified=True)

def assembly_tools(rows):
 d={r['id']:r['shape'] for r in rows};cx=8/math.sqrt(2);cz=-cx
 # A diameter gauge, not a selected torque-rated socket. Required off-shaft
 # assembly is demonstrated because the same gauge hits the installed shaft.
 socket=cyl(5,-8,24.4,x=cx,z=cz).cut(hexsolid(7.2,-9,25,x=cx,z=cz,angle=math.radians(45)))
 crank=d['detachable_cam_crank'];v=common(socket,crank);assert v<1e-5
 shaft_overlap=common(socket,d['rotor_split_trunnion_cradle']);assert shaft_overlap>0
 gauge_rows=[dict(gauge='D10_socket_envelope_AF7.2',against='detached_crank',overlap_mm3=v),dict(gauge='same_socket',against='assembled_trunnion',overlap_mm3=shaft_overlap,meaning='Install and torque follower on detached crank; assembled-side wrench operation is not possible with this gauge.')]
 cq.exporters.export(socket,str(OUT/'parts'/'offshaft_socket_space_gauge.step'))
 # Only rigidly co-moving self pairs; cap-tapped screws and one axial end screw
 # intentionally represent thread major cylinders inside pilot holes.
 moving={r['id']:r['shape'] for r in rows if r['group']=='rotor'}
 moving|={'FORM02_'+n:s for n,s in petal('upper','right').items()}
 positive=[];intentional=[]
 for a,b in itertools.combinations(moving,2):
  sa,sb=moving[a],moving[b]
  if not broad(sa,sb):continue
  v=common(sa,sb)
  if v>1e-5:
   row=dict(pair=[a,b],overlap_mm3=v)
   if set([a,b])==set(['negative_end_M3x8','rotor_split_trunnion_cradle']):intentional.append(row)
   else:positive.append(row)
 assert not positive,positive
 # Gap in bearing shoulders and backlash are not converted into preload.
 return dict(tool_gauges=gauge_rows,co_moving_self_interference=positive,intentional_thread_envelope_intersections=intentional,
   sequence=['Bolt unchanged FORM02 root to the steel cradle, using rear washers/nuts before the side pedestals.',
   'Place each607/8 bearing in its separate side pedestal; slide both assemblies axially onto the two short journals. Fits and press tooling are unreleased.',
   'Attach removable bearing caps, bolt separate pedestal feet to the radial mounting foot, fit the negative inner-ring washer/end screw.',
   'Off the root shaft, hold the CFS head with its1.5hex and rotate the supplied nut using an actual qualified tool. This D10 gauge only proves nominal space.',
   'Slide positive inner-ring spacer and preassembled crank/follower onto the positive journal; align and insert the D3 crosspin. Pin end retention is not designed.',
   'Install fixed guide last, approaching along-Y from y>34. It passes around the D8 follower through the8.3 groove; all other positive-y parts end below y30.',
   'Mount carrier onto an independently designed radial guide and bolt the fixed slot to a palm backbone. Those structures are not included or released.'],
   unresolved=['No positive hard0/90 end stops; prescribed q range is still an assembly/operation constraint.',
   'No four-installed-branches field-service tool route; prototype sequence is off-palm.',
   'Socket/punch/hex keys above are space gauges, not selected manufactured tools or torque capability evidence.',
   'Crosspin retention, shaft fits, bearing preload, thread runout and fastener locking/torques remain open.'])

def plots(rows):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.backends.backend_pdf import PdfPages
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
 def draw(ax,s,axes=(0,2),color='#738792',alpha=1):
  v,f=s.tessellate(.15,.16);v=np.array([p.toTuple() for p in v]);ff=np.array(f)
  ax.add_collection(PolyCollection(v[ff][:,:,axes],facecolors=color,edgecolors='none',alpha=alpha,rasterized=True));ax.autoscale_view()
 def footer(fig,n):fig.text(.045,.025,NOTICE+f' | CC BY-NC4.0 | nominal packaging / not manufacture release | {n}/2',fontsize=7,color='#5c727c')
 with PdfPages(OUT/'R5-CARRIER01-dimensions-and-assembly.pdf') as pdf:
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('R5 / one radial carrier + split hinge + fixed guide',x=.045,y=.96,ha='left',fontsize=18)
  ax=fig.add_axes([.06,.47,.52,.38]);R=66;q=90
  for r in rows:draw(ax,posed([r],R,q)[r['id']],color=COLORS[r['representation']])
  for n,s in petal('upper','right').items():draw(ax,pose(s,R,q),color='#c6a763' if n=='compliant_skin' else '#456e7c',alpha=.75)
  ax.set_aspect('equal');ax.set_xlim(20,115);ax.set_ylim(-25,178);ax.set_xlabel('Branch radial X [mm]');ax.set_ylabel('Head Z [mm]');ax.grid(alpha=.15);ax.set_title('Side / folded at R66 / upper petal',loc='left')
  ax.annotate('Root Z20',(66,20),(95,62),arrowprops={'arrowstyle':'->'},fontsize=8)
  ax.annotate('Fixed plate 4mm\nslot8.3 / wall3',(46,26),(22,80),arrowprops={'arrowstyle':'->'},fontsize=8)
  ax2=fig.add_axes([.6,.46,.35,.39])
  for f,(kind,hand,phi) in FINGERS.items():
   for r in rows:draw(ax2,posed([r],31,90,phi)[r['id']],axes=(0,1),color=COLORS[r['representation']])
   for n,s in petal(kind,hand).items():draw(ax2,pose(s,31,90,phi),axes=(0,1),color='#c6a763' if n=='compliant_skin' else '#456e7c',alpha=.7)
  ax2.add_patch(plt.Circle((0,0),30,fill=False,ls='--',color='#c37436'));ax2.set_aspect('equal');ax2.set_xlim(-115,115);ax2.set_ylim(-115,115);ax2.set_xlabel('Head X [mm]');ax2.set_ylabel('Head Y [mm]');ax2.set_title('C4 support / R31 / bilateral petals',loc='left',fontsize=10);ax2.grid(alpha=.15)
  fig.text(.06,.34,'Frozen stage inputs: rootZ20; R31..91; q0..90; a8 / phase-45deg. Fixed slotY30..34.\n607/8-2Z: 8x19x6, centersY+/-16; CFS4: D8 x5 rolling width atY29.5..34.5.\nGuide attachment bores: D4.5, head(X,Z)=(45,-9),(94,-9); no palm attachment model.',fontsize=10,linespacing=1.6,va='top')
  fig.text(.06,.18,'The C4 steel guides are exposed in this prototype. No enclosure proves a mirror-symmetric exterior.\nNo radial rail, motor, differential, return spring, hard stops or working cameras are included.\nThe D60 x8 disc is a clearance gauge only. Neither 1-second motion nor a 2kg grasp is qualified.',fontsize=10,color='#89583d',linespacing=1.6,va='top')
  footer(fig,1);pdf.savefig(fig);fig.savefig(OUT/'packaging-overview.png',dpi=180);plt.close(fig)
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('Axial stack / service access / load path',x=.045,y=.96,ha='left',fontsize=18)
  ax=fig.add_axes([.06,.51,.60,.34]);sel=['rotor_split_trunnion_cradle','bearing_pedestal_positive','outer_cap_positive','SKF_607_8_2Z_positive','positive_inner_ring_spacer','detachable_cam_crank','IKO_CFS4','IKO_CFS4_supplied_nut']
  for r in rows:
   if r['id'] in sel:draw(ax,r['shape'],axes=(1,2),color=COLORS[r['representation']],alpha=.7)
  ax.set_aspect('equal');ax.set_xlim(7,38);ax.set_ylim(-18,13);ax.set_xlabel('Local tangent Y [mm]');ax.set_ylabel('Hinge-relative Z [mm]');ax.grid(alpha=.2);ax.set_title('Actual solids / +Y bearing and follower side',loc='left')
  for y,label in [(13,'13'),(19,'19'),(21,'21'),(24.5,'24.5'),(28.5,'28.5'),(30,'30'),(34,'34')]:ax.axvline(y,color='#71828a',ls=':',lw=.5);ax.text(y,12,label,rotation=90,va='top',fontsize=7)
  fig.text(.70,.83,'Cam seat:4mm\nD4H6 candidate / backingD10\nAF7 nut:3.2mm\nThread tail:0.8mm nominal\nSeat -> guide gap:1.5mm\nTrack rolling-edge allowance:0.5mm\n\nRear service relief:D10.4\nMain seat hole ligament:2mm\nD3 pin:custom, unretained\nInner spacer:D10/D8 x2',fontsize=10,va='top',linespacing=1.5)
  fig.text(.06,.39,'1  Attach petal to U cradle with four M3 screws, washers and rear nuts.\n2  Slide separate bearing pedestals onto short journals; fit caps and foot bolts.\n3  Assemble CFS on the detached crank: hold the head, turn the supplied nut.\n4  Fit spacer and crank to shaft, then crosspin. Install the fixed guide last.\n5  Connect to a separately qualified rail/backbone; no complete palm is supplied.',fontsize=10,linespacing=1.7,va='top')
  fig.text(.06,.12,'Load: face -> FORM02 frame -> M3 interface -> steel cradle/short shaft -> crank/pin -> CFS -> fixed guide.\nBearing reaction also flows through two pedestals into the radial foot. Catalog ratings do not qualify\nthis custom load path. Fits, pin retention, fastener preload, fatigue and impact stops remain open.',fontsize=9,color='#89583d',linespacing=1.4,va='top')
  footer(fig,2);pdf.savefig(fig);fig.savefig(OUT/'axial-stack-and-assembly.png',dpi=180);plt.close(fig)

def checks(rows,center):
 # Own-branch actual interference; joint contacts and threads are separately identified.
 rot=[r for r in rows if r['group']=='rotor'];fixed=[r for r in rows if r['group'] in ['carrier','bearing']]
 cases=[]
 for q in np.linspace(0,90,19):
  # fixed root frame is enough: all R translates equally, guide checked separately.
  moving={r['id']:pose(r['shape'],31,q) for r in rot}
  moving.update({'FORM02_'+n:pose(s,31,q) for n,s in petal('upper','right').items()})
  fixedsh={r['id']:pose(r['shape'],31,0) for r in fixed}
  violations=[];minimum=None
  for a,sa in moving.items():
   for b,sb in fixedsh.items():
    if not broad(sa,sb):continue
    v=common(sa,sb)
    if v>1e-5:violations.append(dict(pair=[a,b],overlap_mm3=v))
  cases.append(dict(q_deg=float(q),violations=violations));print('own',q,len(violations),flush=True)
 dump(OUT/'own-branch-samples.json',cases)
 # Fixed guides: mirror counterexample is retained, C4 checked on current Y32.
 guide=next(r['shape'] for r in rows if r['group']=='guide')
 guidepairs={}
 for style in ['C4','bilateral_mirror_counterexample']:
  gs={f:azimuth(guide if style=='C4' or f in ['UR','LL'] else guide.mirror('XZ'),phi) for f,(_,_,phi) in FINGERS.items()}
  guidepairs[style]=[dict(pair=[a,b],**separation(gs[a],gs[b])) for a,b in itertools.combinations(gs,2)]
 # Four-module mixed/end-state samples use group compounds, retain positive overlaps.
 samples=[]
 statepairs=[(31,90),(66,90),(91,0),(78.5,qR(78.5))]
 # All 6 pairs and 16 independent endpoint/midfold state combinations.
 modules={}
 for f,(kind,hand,phi) in FINGERS.items():
  for R,q in statepairs:
   shapes=posed(rows,R,q,phi)|{'FORM02_'+n:pose(s,R,q,phi) for n,s in petal(kind,hand).items()}
   modules[(f,R,q)]={n:(s,bbox(s)) for n,s in shapes.items()}
 for a,b in itertools.combinations(FINGERS,2):
  for (Ra,qa),(Rb,qb) in itertools.product(statepairs,repeat=2):
   x,y=modules[(a,Ra,qa)],modules[(b,Rb,qb)]
   todo=[]
   for na,(sa,ba) in x.items():
    for nb,(sb,bb) in y.items():
     delta=np.maximum(np.maximum(ba[0]-bb[1],bb[0]-ba[1]),0);bound=float(np.linalg.norm(delta))
     # BREP pair distance is only needed when the box lower bound can improve
     # the current minimum. Exact fixed guide and bare-petal certificates
     # are reported separately, not inferred from these sparse samples.
     todo.append((bound,na,nb,sa,sb))
   todo.sort(key=lambda z:z[0]);dmin=float('inf');winner=None;viol=[]
   for bound,na,nb,sa,sb in todo:
    if bound>dmin+1e-7:break
    result0=separation(sa,sb)
    if result0['distance_mm']<dmin:dmin=result0['distance_mm'];winner=[na,nb]
    if result0['overlap_mm3']>1e-5:viol.append(dict(parts=[na,nb],**result0))
   result=dict(distance_mm=dmin,nearest_parts=winner,overlap_violations=viol,overlap_mm3=sum(v['overlap_mm3'] for v in viol))
   samples.append(dict(pair=[a,b],R_mm=[Ra,Rb],q_deg=[qa,qb],**result))
  print('pair',a,b,'done',flush=True)
 # Central display gauge is deliberately not actual optics.
 gauge=cq.Solid.makeCylinder(30,8,cq.Vector(0,0,-8))
 gauges=[]
 for R,q in statepairs:
  sh=cq.Compound.makeCompound(list(posed(rows,R,q).values()))
  gauges.append(dict(R_mm=R,q_deg=q,**separation(sh,gauge)))
 b=bbox(guide);rmin=float(b[0,0]);ymin=float(b[0,1])
 return dict(own_branch_5deg_samples=cases,guide_pair_checks=guidepairs,four_branch_independent_state_samples=samples,central_D60_Zminus8_to0_gauge=gauges,
   continuous_bare_petal_to_guide=dict(own_y_clearance_mm=ymin-23,adjacent_radial_clearance_mm=rmin-23,formula='All FORM02 y in [-23,23], rho>=R-6>=25. Guide x>=rmin,y>=30. Adjacent/opposite rotated branches separated by a fixed coordinate plane.',FORM02_and_STAGE_hashes_required=True),
   scope='5deg own-module and 96 cross-module samples are not continuous whole-module certificates; positive overlaps are blockers, zero samples do not prove all angles. Fixed guides/bare petals have independent coordinate inequalities.')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build-only',action='store_true');ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
 rows,center=build()
 if not args.check_only:ledger=export(rows,center)
 else:ledger=json.loads((OUT/'parts-manifest.json').read_text())['parts']
 dump(OUT/'continuous-certificate.json',continuous_certificate(rows))
 dump(OUT/'assembly-and-tool-checks.json',assembly_tools(rows))
 dump(OUT/'crank-section-screen.json',section_screen(rows))
 dump(OUT/'mass-summary.json',mass_summary(rows,ledger))
 if not args.build_only:dump(OUT/'geometry-checks.json',checks(rows,center))
 if not args.check_only:plots(rows)
 dump(OUT/'parameters.json',P)
 dump(OUT/'source-hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'engineering/generated/r5-petal-form02/study.json',ROOT/'engineering/generated/r5-stage01/study.json',ROOT/'engineering/electronics/r5-cam-hardware01/mechanical-interface.json',ROOT/'engineering/electronics/r5-cam-hardware01/budget.json']})
 print('DONE',flush=True)
if __name__=='__main__':main()
