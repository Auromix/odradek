# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""CD-MOUNT01: removable circular display mechanics and bounded clearance study.

Nominal geometry only. No PCB, connector, optical or manufacturing release.
"""
from pathlib import Path
import csv, hashlib, itertools, json, math
import cadquery as cq
import numpy as np
from screen_integrated_collisions import named_step
from studies.link_interface_tools import check, cache
import p16_carrier_study as carrier
import p16_packaging_study as p16
import gripper_root_support_study as st

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/central-display-mount01'
B,C=st.B,st.C
MOUNT_X=35.25

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def union(ss):
 ss=list(ss);return ss[0].fuse(*ss[1:]).clean() if len(ss)>1 else ss[0]
def bb(s):return [v.tolist() for v in st.bb(s)]

def build(old_frame):
 # Main sleeve OD64, bore60.2; shoulder supports the PCB annulus R28..30.
 cup=C(32,11.25,(0,0,-11),(0,0,1),60.2)
 cup=cup.fuse(C(30.1,1,(0,0,-4),(0,0,1),56))
 bezel=C(32,1.5,(0,0,.25),(0,0,1),57)
 frame=old_frame
 for x in [-MOUNT_X,MOUNT_X]:
  ear=B(x-3,x+3,-4,4,-11,.25)
  # Ear includes a radial bridge to the OD64 sleeve, without touching the PCB.
  bridge=B(-MOUNT_X if x<0 else 30, -30 if x<0 else MOUNT_X,-4,4,-11,.25)
  cup=cup.fuse(ear,bridge)
  bezel=bezel.fuse(B(x-3,x+3,-4,4,.25,1.75),B(-MOUNT_X if x<0 else 30,-30 if x<0 else MOUNT_X,-4,4,.25,1.75))
  hole=C(1.1,30,(x,0,-20),(0,0,1))
  cup=cup.cut(hole);bezel=bezel.cut(hole);frame=frame.cut(hole)
 # The bore is repeated after unioning the ears so neither intrudes on the board.
 cup=cup.cut(C(30.1,3.26,(0,0,-3),(0,0,1))).clean()
 p={'CD01-cup':cup,'CD01-bezel':bezel.clean(),
    'CD01-PCB-outline':C(30,1,(0,0,-3),(0,0,1)),
    'CD01-insulating-spacer':C(29.9,1.5,(0,0,-2),(0,0,1),57),
    'CD01-window':C(29.9,.75,(0,0,-.5),(0,0,1)),
    'CD01-optical-frame':frame.clean(),
    # Back-mounted GH12 reference encloses body, full plug, solder lands and
    # +0.25mm plan/+0.10mm height planning margin. Not a supplier CAD model.
    # Source local u,v,h -> head -u,-14+v,-3-h (proper 180deg about Y).
    'CD01-GH12-mated-reference':B(-9.475,9.475,-19.8,-11.05,-7.45,-3)}
 for x in [-MOUNT_X,MOUNT_X]:
  k='L' if x<0 else 'R'
  # Accu catalog maximum head/washer/nut dimensions; thread and chamfer simplified.
  p[f'CD01-{k}-M2x20-envelope']=C(1,20,(x,0,-17.9),(0,0,1)).fuse(C(1.9,2,(x,0,2.1),(0,0,1)))
  p[f'CD01-{k}-front-washer']=C(2.5,.35,(x,0,1.75),(0,0,1),2.2)
  p[f'CD01-{k}-rear-washer']=C(2.5,.35,(x,0,-15.35),(0,0,1),2.2)
  nut=cq.Workplane('XY').workplane(offset=-16.95).center(x,0).polygon(6,4/math.cos(math.pi/6)).extrude(1.6).val()
  p[f'CD01-{k}-M2-nut-envelope']=nut.cut(C(1,2,(x,0,-17),(0,0,1)))
 rows=[]
 for r in csv.DictReader((ROOT/'engineering/generated/lighting-layout/led-coordinate-reference.csv').open()):
  if r['panel']!='circle':continue
  x,y=float(r['panel_x_mm'])*2.8/3,float(r['panel_y_mm'])*2.8/3
  rows.append(dict(index=len(rows),x_mm=x,y_mm=y,old_driver=r['driver'],old_SW=int(r['SW']),old_CS=int(r['CS'])))
 assert len(rows)==285,len(rows)
 for r in rows:
  x,y=r['x_mm'],r['y_mm'];p[f"CD01-LED-{r['index']:03}"]=B(x-1.2,x+1.2,y-.45,y+.45,-2,-1.1)
 assert all(s.isValid() and len(s.Solids())==1 for s in p.values())
 return p,rows

def motion(shapes,spec,manifest,obstacle):
 result={};obs=carrier.FastSet([obstacle])
 fingers=json.loads((ROOT/'engineering/generated/contact02-study/study.json').read_text())['fingers']
 for i,j in enumerate(manifest['finger_joints']):
  pivot=np.array(j['pivot_head_mm']);axis=np.array(j['closing_axis_head']);end=pivot+axis
  moving=[s for n,s in shapes.items() if spec[n]['group']==j['moving_group']]
  radius=0.
  for s in moving:
   lo,hi=st.bb(s)
   for point in itertools.product(*zip(lo,hi)):
    d=np.array(point)-pivot;radius=max(radius,float(np.linalg.norm(d-axis*np.dot(d,axis))))
  proof=p16.certificate(lambda q:carrier.FastSet([s.rotate(tuple(pivot),tuple(end),q) for s in moving]),lambda q:obs,radius,j['range_deg'][1],step=4)
  assert proof['certified'],(j['id'],proof)
  result[j['id']+'_rotor']=proof;print(j['id'],'rotor',proof['continuous_lower_bound_mm'],flush=True)
  V=26+160*26*(123+26)/p16.kin(0)[2]**2
  f=fingers[i]
  proof=p16.certificate(lambda q:carrier.FastSet([st.place(s,f,st.SIGNS[i]) for s in p16.envelopes(q).values()]),lambda q:obs,V,j['range_deg'][1],step=4)
  assert proof['certified'],(j['id'],proof)
  result[j['id']+'_P16']=proof;print(j['id'],'P16',proof['continuous_lower_bound_mm'],flush=True)
 return result

def draw(p,rows):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.patches import Circle,Rectangle
 fig,axs=plt.subplots(1,2,figsize=(14,8));ax=axs[0]
 for r,col in [(38,'#91a0aa'),(32,'#405c6e'),(30,'#2f947e'),(28.5,'#f3f4f2')]:ax.add_patch(Circle((0,0),r,color=col))
 for x in [-MOUNT_X,MOUNT_X]:
  ax.add_patch(Rectangle((x-3,-4),6,8,color='#405c6e'));ax.add_patch(Circle((x,0),1.1,color='white'))
 for r in rows:ax.add_patch(Rectangle((r['x_mm']-1.2,r['y_mm']-.45),2.4,.9,color='#edaf34'))
 ax.set(xlim=(-45,45),ylim=(-45,45),xlabel='Head X / mm',ylabel='Head Y / mm',title='Front | 285 LEDs, 2.8 mm pitch')
 ax.annotate('57 mm clear aperture',xy=(0,28.5),xytext=(-40,39),arrowprops={'arrowstyle':'->'})
 ax.annotate('Two M2 through holes\n70.5 mm centre distance',xy=(MOUNT_X,0),xytext=(-40,-41),arrowprops={'arrowstyle':'->'})
 ax=axs[1]
 colors={'CD01-cup':'#547185','CD01-bezel':'#253b49','CD01-PCB-outline':'#167c69','CD01-insulating-spacer':'#b8a7d2','CD01-window':'#83cdd8','CD01-optical-frame':'#afb7bd'}
 # True geometric section at Y=0; thin slice prevents drawing the far wall over the PCB.
 for n,s in p.items():
  if n.startswith('CD01-LED-'):continue
  section=s.intersect(B(-100,100,-.001,.001,-30,10))
  if section.Volume()<1e-10:continue
  v,f=section.tessellate(.1,.2);v=np.array([x.toTuple() for x in v]);f=np.array(f)
  ax.add_collection(PolyCollection(v[f][:,:,[0,2]],facecolors=colors.get(n,'#6c7177'),edgecolors='none'))
 for r in rows:
  if abs(r['y_mm'])<.01:ax.add_patch(Rectangle((r['x_mm']-1.2,-2),2.4,.9,color='#edaf34'))
 ax.set(xlim=(-42,42),ylim=(-23,9),xlabel='Head X / mm',ylabel='Head Z / mm',title='Y=0 nominal section | toward object = +Z')
 for text,xy,loc in [('1 mm PCB on annular seat',(-14,-3),(-39,-21)),('0.6 mm LED-to-window gap',(0,-.8),(-25,7)),('Rear washer / M2 nut',(MOUNT_X,-16.1),(7,-21))]:ax.annotate(text,xy=xy,xytext=loc,arrowprops={'arrowstyle':'->'},fontsize=9)
 for a in axs:a.set_aspect('equal');a.grid(alpha=.12)
 fig.suptitle('CD-MOUNT01 | removable circular pixel display',fontsize=19)
 fig.text(.06,.1,'Nominal packaging candidate, not manufacturing release. Existing optical frame gains two through holes.\nGH12 reference is behind PCB at Y=-14 (outside this section); cable and other electronics not modeled.\nRigid spacer captures PCB perimeter; optics, stack tolerance, thermal and fastener preload remain open.',fontsize=10)
 fig.subplots_adjust(top=.87,bottom=.22,wspace=.2)
 for ext in ['png','svg']:fig.savefig(OUT/('assembly-review.'+ext),dpi=160,facecolor='white')
 plt.close(fig)

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 head=ROOT/'engineering/generated/head-integrated-03';mp=head/'blender-parts-manifest.json';sp=head/'HEAD-INTEGRATED03-open.step'
 manifest=json.loads(mp.read_text());shapes=named_step(sp);spec={x['id']:x for x in manifest['parts']}
 p,rows=build(shapes['removable_optical_frame'])
 obstacle=union([C(32,12.75,(0,0,-11),(0,0,1)),B(-MOUNT_X-3,-30,-4,4,-11,1.75),B(30,MOUNT_X+3,-4,4,-11,1.75)]+[C(2.5,22,(x,0,-17.9),(0,0,1)) for x in [-MOUNT_X,MOUNT_X]])
 for n,s in p.items():
  if n=='CD01-optical-frame':continue
  outside=sum(a.cut(obstacle).Volume() for a in s.Solids());assert outside<1e-4,(n,outside)
 frame_added=p['CD01-optical-frame'].cut(shapes['removable_optical_frame']).Volume();assert frame_added<1e-4
 fixed={n:s for n,s in shapes.items() if spec[n]['group']=='head_fixed' and n not in ['removable_optical_frame','display_including_candidate_GH_keepout']}
 checks=[];hits=[];sc=cache(obstacle)
 for k,other in fixed.items():
  rr=check(sc,cache(other));checks.append(['whole_new_display_containing_solid',k,rr])
  if rr['events']:hits.append([k,rr])
 assert not hits,hits
 print('Static containing-body checks PASS',len(checks),flush=True)
 internal=[]
 boxes={n:st.bb(s) for n,s in p.items()}
 for (n,s),(k,t) in itertools.combinations(p.items(),2):
  if st.gap_bounds(boxes[n],boxes[k])>1e-5:continue
  v=sum(a.intersect(b).Volume() for a in s.Solids() for b in t.Solids())
  if v>1e-4:internal.append(dict(a=n,b=k,volume_mm3=v))
 assert not internal,internal
 # A closed obstacle union contains every new display object except the replacement
 # optical frame. That frame only loses material, so inherits its previous motion proof.
 print('Internal actual-body checks PASS',flush=True)
 proofs=motion(shapes,spec,manifest,obstacle)
 radial=max(math.hypot(r['x_mm']+sx*1.2,r['y_mm']+sy*.45) for r in rows for sx,sy in itertools.product([-1,1],repeat=2))
 draw(p,rows);art={};mass=[]
 for n,s in p.items():
  if n.startswith('CD01-LED-'):continue
  path=OUT/(n+'.step');cq.exporters.export(s,str(path));back=cq.importers.importStep(str(path)).val()
  assert back.isValid() and abs(back.Volume()-s.Volume())<1e-4
  art[path.name]=sha(path);mass.append(dict(id=n,volume_mm3=s.Volume(),bbox_head_mm=bb(s),COM_head_mm=list(s.Center().toTuple()),mass_status='No density assigned: material and stock not released'))
 with (OUT/'led-centres.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 sources=[Path(__file__),mp,sp,ROOT/'engineering/generated/lighting-layout/led-coordinate-reference.csv',ROOT/'engineering/generated/contact02-study/study.json',ROOT/'engineering/p16_packaging_study.py',ROOT/'engineering/p16_carrier_study.py',ROOT/'engineering/gripper_root_support_study.py',ROOT/'engineering/studies/link_interface_tools.py',ROOT/'engineering/screen_integrated_collisions.py',ROOT/'docs/engineering/sources/central-display-hardware01.json']
 report=dict(revision='CD-MOUNT01',manufacturing_release=False,head_coordinates='+Z toward object, unchanged from HEAD03; parent raise has no effect',parts=mass,
  LED_count=285,LED_pitch_mm=2.8,LED_envelope_mm=[2.4,.9,.9],LED_corner_max_radius_mm=radial,visible_aperture_radius_mm=28.5,minimum_LED_radial_aperture_margin_mm=28.5-radial,LED_window_gap_mm=.6,
  PCB=dict(diameter_mm=60,thickness_mm=1,z_range_mm=[-3,-2],back_electronics_allocation=dict(radius_mm=28,z_range_mm=[-10,-3],includes='All actual parts, mated connector, insulation and cable bend inside allocation must be checked. This cylinder is not a circuit.')),
  nominal_stack=dict(window_z_mm=[-.5,.25],spacer_z_mm=[-2,-.5],bezel_z_mm=[.25,1.75],seat_z_mm=[-4,-3],front_washer_z_mm=[1.75,2.1],nut_z_mm=[-16.95,-15.35],screw_underhead_z_mm=2.1,screw_tip_z_mm=-17.9),
  fasteners=dict(screw='SSC-M2-20-A2-BL',washer='HPW-M2-A2-BL',nut='HPN-M2-A2',counts=[2,4,2],catalog_total_mass_g=1.48,geometry='Maximum catalog head/washer/nut dimensions, nominal length20; no L tolerance, chamfer, thread form, preload or locking release'),
  GH12=dict(header='SM12B-GHS-TB(LF)(SN)',housing='GHR-12V-S',contacts='SSHL-002T-P0.2',local_to_head=[[ -1,0,0,0],[0,1,0,-14],[0,0,-1,-3],[0,0,0,1]],pin1_head_mm=[6.875,-12.15,-3],installed_bbox_head_mm=bb(p['CD01-GH12-mated-reference']),planning_margin_xy_mm=.25,planning_margin_height_mm=.1,wire_exit='-head Y then route TBD; cable/strain relief not included'),
  fixed_object_pair_count=len(checks),fixed_check_method='Single containing solid vs each HEAD03 fixed object; replacement frame only loses material and inherits previous clearance',fixed_intersections=hits,internal_positive_intersections=internal,continuous_motion=proofs,
  original_frame_volume_mm3=shapes['removable_optical_frame'].Volume(),new_frame_volume_mm3=p['CD01-optical-frame'].Volume(),
  frame_change='Only two diameter2.2 through holes at X+-35.25,Y0; CAD loses material, so previous frame motion containment is inherited',
  mount_hole_centres_head_mm=[[-MOUNT_X,0],[MOUNT_X,0]],washer_radial_frame_edge_margin_mm=.25,
  source_hashes={str(x.relative_to(ROOT)):sha(x) for x in sources},artifact_sha256=art,
  exclusions=['No controller/central driver PCB layout or pin assignment release','GH12 is a conservative source-based mated reference; no wires, plug insertion path or cable strain relief','No window coating/material/adhesive/gasket/optics selection','No stack tolerance/compression or fastener preload analysis; rigid nominal stack is not an assembly tolerance','No whole arm/head mass update, thermal qualification or manufacturing release'])
 for n in ['assembly-review.png','assembly-review.svg','led-centres.csv']:report['artifact_sha256'][n]=sha(OUT/n)
 (OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS',len(p),'parts',len(checks),'fixed pairs',radial,'maxLED radius',flush=True)

if __name__=='__main__':main()
