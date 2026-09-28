# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Fixed dual-camera/CD01 packaging study. No vendor BREP is redistributed.

Native vendor camera STEP is read privately for verification only. Public STEP
contains original catalogue-derived bounding primitives. No new mounting frame
or camera optical calibration is implied by a clear geometric envelope.
"""
from pathlib import Path
import argparse, csv, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector
from OCP.gp import gp_Lin, gp_Pnt, gp_Dir
import r5_carrier01 as carrier
import gripper_root_support_study as st

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-vision01'
MOUNT=ROOT/'engineering/generated/central-display-mount01'
PCB=ROOT/'engineering/electronics/central-display-cd01/pcb01'
DEFAULT_NATIVE=ROOT.parents[1]/'work/p16-carrier-reference/ZED-X-ONE-S-Fisheye.step'
REVIEW=[('baseline',50.,-14.),('compact_retreat',50.,-35.),('wider',60.,-30.),('widest',65.,-26.)]
B,C=st.B,st.C

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def vol(s):return sum(abs(x.Volume()) for x in s.Solids())
def comp(ss):return cq.Compound.makeCompound(list(ss))
def bb(s):
 b=s.BoundingBox();return np.array([[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]])
def gap(a,b):return float(np.linalg.norm(np.maximum(0,np.maximum(a[0]-b[1],b[0]-a[1]))))
def overlap(a,b):
 # Native assembly components must be intersected separately. A single boolean
 # on this supplier compound omitted a colliding component in baseline checks.
 return sum(vol(x.intersect(y)) for x in a.Solids() for y in b.Solids() if gap(bb(x),bb(y))<1e-7)
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x))
def dump(name,data):
 OUT.mkdir(parents=True,exist_ok=True);(OUT/name).write_text(json.dumps(data,indent=2,default=serial)+'\n')
def camera_pose(s,sign,Y,Z):return s.rotate((0,0,0),(1,0,0),-sign*8).translate((0,sign*Y,Z))
def rotation(sign):
 t=math.radians(-sign*8);return np.array([[1,0,0],[0,math.cos(t),-math.sin(t)],[0,math.sin(t),math.cos(t)]])

def camera_primitives():
 body=B(-12.6,12.6,-12.6,12.6,-33.65,0).fuse(C(10.1,4.825,(0,0,0),(0,0,1)),C(8.6,9.2,(0,0,4.8),(0,0,1)))
 plate=B(-16,16,-15,15,0,4).cut(C(10.25,4.2,(0,0,-.1),(0,0,1)))
 screws=[]
 for x,y in itertools.product([-10.5,10.5],repeat=2):
  plate=plate.cut(C(1.2,4.2,(x,y,-.1),(0,0,1))).cut(C(2.2,2.1,(x,y,2),(0,0,1)))
  screws.append(C(1,6,(x,y,-4),(0,0,1)).fuse(C(1.9,2,(x,y,2),(0,0,1))))
 return dict(physical_proxy=body,front_plate=plate,M2x6_planning=comp(screws),
  FAKRA_unmated_reservation=B(-4.22,9.79,-11.16,3.05,-59.85,-33.65))

def load(native_path):
 hashes={}
 def remember(p):hashes[str(p.relative_to(ROOT))]=sha(p);return p
 manifest=read(remember(carrier.OUT/'parts-manifest.json'));rows=[]
 for r in manifest['parts']:
  path=remember(carrier.OUT/r['source_step']);rows.append(dict(r,shape=cq.importers.importStep(str(path)).val()))
 petals={}
 for f,(kind,hand,phi) in carrier.FINGERS.items():
  ps={}
  folder=ROOT/'engineering/generated/r5-petal-form02'/f'{kind}-{hand}'
  for path in sorted(folder.glob('*.step')):
   if path.stem.startswith('R5-'):continue
   remember(path);ps[path.stem]=cq.importers.importStep(str(path)).val().translate((0,0,-3.5))
  petals[f]=ps
 central={};report=read(remember(MOUNT/'study.json'))
 for name,digest in report['artifact_sha256'].items():
  if not name.endswith('.step') or name=='CD01-optical-frame.step':continue
  path=remember(MOUNT/name);assert sha(path)==digest
  central[Path(name).stem]=cq.importers.importStep(str(path)).val()
 pcb=read(remember(PCB/'mechanical-interface.json'))
 assert sha(remember(PCB/'kicad/central.kicad_pcb'))==pcb['board_sha256']
 for r in pcb['components_back']:
  if r['ref']=='J1':continue # Already counted as CD01-GH12-mated-reference.
  b=r['mcad_material_envelope'];central['CD01-PCBA-'+r['ref']]=B(*[v for pair in zip(b['head_min_mm'],b['head_max_mm']) for v in pair])
 for r in csv.DictReader(remember(MOUNT/'led-centres.csv').open()):
  x,y=float(r['x_mm']),float(r['y_mm']);central['CD01-LED-'+r['index']]=B(x-1.2,x+1.2,y-.45,y+.45,-2,-1.1)
 assert len(central)==331
 # A stronger, original containing solid includes all 331 actual nominal objects.
 bounds=comp([C(32,12.75,(0,0,-11),(0,0,1)),B(-38.25,-30,-4,4,-11,1.75),B(30,38.25,-4,4,-11,1.75)]+[C(2.5,22,(x,0,-17.9),(0,0,1)) for x in [-35.25,35.25]])
 fused=bounds.Solids()[0].fuse(*bounds.Solids()[1:])
 containment=[dict(id=n,outside_mm3=vol(s.cut(fused))) for n,s in central.items()]
 assert max(r['outside_mm3'] for r in containment)<1e-4
 sources=read(remember(ROOT/'docs/engineering/sources/p16-carrier.json'))
 expected=next(x['download_sha256'] for x in sources['sources'] if x['id']=='PC-02')
 assert sha(native_path)==expected
 native_all=cq.importers.importStep(str(native_path)).val().Solids();assert len(native_all)==14
 native=comp(s for i,s in enumerate(native_all) if i not in [7,8])
 prim=camera_primitives();outside=sum(vol(s.cut(prim['physical_proxy'])) for s in native.Solids())
 assert outside<1e-4
 for path in [Path(__file__),ROOT/'engineering/r5_carrier01.py',ROOT/'engineering/generated/r5-petal-form02/study.json']:
  remember(path)
 return rows,petals,central,bounds,native,hashes,dict(native_sha256=expected,physical_solids=12,reference_solids_excluded=[7,8],native_outside_original_proxy_mm3=outside,central_actual_objects=331,central_containment=containment)

def optics(Y,Z):
 return {f'camera_{sign}_{n}':camera_pose(s,sign,Y,Z) for sign in [-1,1] for n,s in camera_primitives().items()}

def finite_scan(rows,native):
 guide=next(r['shape'] for r in rows if r['group']=='guide')
 foot=next(r['shape'] for r in rows if r['id']=='radial_carrier_foot')
 obstacles={f'{f}_guide':carrier.azimuth(guide,phi) for f,(_,_,phi) in carrier.FINGERS.items()}
 obstacles.update({f'{f}_R31foot':carrier.pose(foot,31,0,phi) for f,(_,_,phi) in carrier.FINGERS.items()})
 results=[]
 for Y,Z in itertools.product([50,55,60,65,70],[-14,-18,-22,-26,-30,-32,-35]):
  parts=optics(Y,Z);hits=[];minimum=1e9;pair=None
  # Native physical body is checked separately from the conservative proxy.
  parts.update({f'native_camera_{s}':camera_pose(native,s,Y,Z) for s in [-1,1]})
  for n,s in parts.items():
   for k,t in obstacles.items():
    if gap(bb(s),bb(t))>minimum:continue
    d=s.distance(t)
    if d<minimum:minimum=d;pair=[n,k]
    if d<1e-6:
     v=overlap(s,t)
     if v>1e-5:hits.append(dict(a=n,b=k,intersection_mm3=v))
  results.append(dict(Y_mm=Y,Z_front_mount_mm=Z,min_gap_mm=minimum,nearest=pair,hits=hits,
   scope='Fixed four guides and four feet at R31 only; includes native camera, proxy, front plate, screws and connector reservation. This finite screen is not a full-motion certificate.'))
  print('grid',Y,Z,len(hits),minimum,flush=True)
 return results

def trig_min_z(bounds):
 vals=[]
 for x,z in itertools.product(bounds[:,0],bounds[:,2]):
  angles=[0,math.pi/2];t=math.atan2(x,z)
  for k in range(-2,3):
   q=t+k*math.pi
   if 0<=q<=math.pi/2:angles.append(q)
  vals.extend(x*math.sin(q)+z*math.cos(q)+20 for q in angles)
 return min(vals)

def translate_certificate(shape,phi,fixed):
 e=np.array([math.cos(math.radians(phi)),math.sin(math.radians(phi)),0])
 base=carrier.pose(shape,31,0,phi);b0=bb(base);bf=bb(fixed);accepted=[];calls=0;sampled=1e9;failures=[]
 def visit(lo,hi,depth):
  nonlocal calls,sampled
  a=b0+(lo-31)*e;b=b0+(hi-31)*e;sweep=np.array([np.minimum(a[0],b[0]),np.maximum(a[1],b[1])])
  lower=gap(sweep,bf)
  if lower>.05:accepted.append(lower);return
  mid=(lo+hi)/2;s=base.translate(tuple((mid-31)*e));d=s.distance(fixed);calls+=1;sampled=min(sampled,d)
  lower=d-(hi-lo)/2
  if lower>.05:accepted.append(lower);return
  if d<1e-7 or depth>=15:
   failures.append(dict(R_mm=[lo,hi],sample_R_mm=mid,sampled_distance_mm=d,intersection_mm3=overlap(s,fixed) if d<1e-7 else None));return
  visit(lo,mid,depth+1);visit(mid,hi,depth+1)
 visit(31,91,0)
 return dict(certified=not failures,continuous_gap_lower_mm=min(accepted) if accepted and not failures else None,
  accepted_intervals=len(accepted),exact_distance_evaluations=calls,minimum_evaluated_distance_mm=sampled if calls else None,failures=failures)

def certify(Y,Z,rows,petals,central_bounds):
 fixed=optics(Y,Z)|{'CD01_complete_containing_solid':central_bounds}
 records=[];minz=[]
 for f,(_,_,phi) in carrier.FINGERS.items():
  moving=[(r['id'],r['shape']) for r in rows if r['group']=='rotor']+list(petals[f].items())
  # Analytical trig bound on every original source bounding-box corner. R only
  # translates XY; this proves all rotor geometry for all q in [0,90], stronger
  # than the actual prescribed q(R). No old P16 proof is inherited.
  zl=min(trig_min_z(bb(s)) for _,s in moving)
  for name,t in fixed.items():
   g=zl-bb(t)[1,2];assert g>0,(f,name,zl,bb(t))
   minz.append(dict(finger=f,obstacle=name,moving_min_z_mm=zl,fixed_max_z_mm=bb(t)[1,2],continuous_Z_gap_mm=g))
  for r in rows:
   if r['group']=='rotor':continue
   for name,t in fixed.items():
    if r['group']=='guide':
     s=carrier.azimuth(r['shape'],phi);d=s.distance(t)
     rec=dict(certified=d>1e-7,continuous_gap_lower_mm=d,exact_distance_evaluations=1,fixed=True)
     if d<1e-7:rec['intersection_mm3']=overlap(s,t)
    else:rec=translate_certificate(r['shape'],phi,t)
    records.append(dict(finger=f,part=r['id'],obstacle=name,**rec))
 # Cameras do not automatically clear the real central display or each other.
 modulechecks=[];cams=optics(Y,Z)
 for name,s in cams.items():modulechecks.append(dict(a=name,b='CD01_complete_containing_solid',distance_mm=s.distance(central_bounds)))
 for (n,s),(k,t) in itertools.combinations(cams.items(),2):
  if n.split('_')[1]!=k.split('_')[1]:modulechecks.append(dict(a=n,b=k,distance_mm=s.distance(t)))
 ok=all(r['certified'] for r in records) and min(r['distance_mm'] for r in modulechecks)>1e-7
 return dict(Y_mm=Y,Z_front_mount_mm=Z,certified=ok,rotor_plane_certificates=minz,nonrotor_certificates=records,
  optics_internal_checks=modulechecks,minimum_continuous_lower_mm=min([r['continuous_gap_lower_mm'] for r in records if r['certified']]+[r['continuous_Z_gap_mm'] for r in minz]),
  method='Rotor analytic z support over independent q0..90; fixed guide exact BREP; carrier/bearing translation has Hausdorff speed1mm/mm. Midpoint exact distance minus half interval proves every R in31..91, with AABB broad-phase intervals. Original nominal solids only.')

def scene(rows,petals,central,Y,Z,R):
 parts=dict(central);parts.update(optics(Y,Z))
 for (f,(_,_,phi)),ri in zip(carrier.FINGERS.items(),R):
  q=carrier.qR(ri)
  parts.update({f+'_'+n:s for n,s in carrier.posed(rows,ri,q,phi).items()})
  parts.update({f+'_petal_'+n:carrier.pose(s,ri,q,phi) for n,s in petals[f].items()})
 return parts

def sightlines(rows,petals,central,Y,Z):
 states={'open':[91]*4,'folded':[66]*4,'minimum50':[31]*4,'box50x120':[31,66,31,66],'box120x50':[66,31,66,31]}
 allresults=[]
 for state,R in states.items():
  parts=scene(rows,petals,central,Y,Z,R);casters={}
  for n,s in parts.items():
   if 'physical_proxy' in n or 'FAKRA' in n:continue
   ray=IntCurvesFace_ShapeIntersector();ray.Load(s.wrapped,1e-7);casters[n]=(ray,bb(s))
  for pupil in [0.,7.,14.]:
   cameraresults=[]
   for sign in [1,-1]:
    Q=rotation(sign);eye=np.array([0,sign*Y,Z])+Q@np.array([0,0,pupil]);rays=[]
    for tz,x,y in itertools.product([20.,40.,65.,100.],np.linspace(-20,20,5),np.linspace(-20,20,5)):
     target=np.array([x,y,tz]);v=target-eye;length=np.linalg.norm(v);direction=v/length;local=Q.T@direction
     bearings=np.degrees(np.arctan2(local[:2],local[2]));line=gp_Lin(gp_Pnt(*eye),gp_Dir(*direction));hits=[]
     for n,(cast,bounds) in casters.items():
      # Own front plate is also excluded for pupil sensitivity at z=0; it is
      # not an optical entrance-pupil construction. No optics are calibrated.
      if n.startswith(f'camera_{sign}_'):continue
      if np.any(np.maximum(eye,target)<bounds[0]) or np.any(np.minimum(eye,target)>bounds[1]):continue
      cast.Perform(line,.05,length-.5)
      assert cast.IsDone()
      if cast.NbPnt():hits.append((min(cast.WParameter(i) for i in range(1,cast.NbPnt()+1)),n))
     hits.sort();rays.append(dict(target_mm=target,clear=not hits,first_hit=None if not hits else hits[0],bearing_HV_deg=bearings))
    cameraresults.append(dict(sign=sign,assumed_pupil_native_z_mm=pupil,pupil_head_mm=eye,rays=rays))
   groups=[]
   for tz in [20.,40.,65.,100.]:
    a=[r for r in cameraresults[0]['rays'] if r['target_mm'][2]==tz];b=[r for r in cameraresults[1]['rays'] if r['target_mm'][2]==tz]
    groups.append(dict(target_z_mm=tz,count=25,upper_clear=sum(r['clear'] for r in a),lower_clear=sum(r['clear'] for r in b),
     either_clear=sum(x['clear'] or y['clear'] for x,y in zip(a,b)),both_clear=sum(x['clear'] and y['clear'] for x,y in zip(a,b)),
     central_first_hit_upper=sum(not r['clear'] and r['first_hit'][1].startswith('CD01') for r in a),
     central_first_hit_lower=sum(not r['clear'] and r['first_hit'][1].startswith('CD01') for r in b),
     maximum_abs_vertical_bearing_deg=max(abs(r['bearing_HV_deg'][1]) for r in a+b)))
   allresults.append(dict(state=state,R_mm=R,pupil_native_z_mm=pupil,summary=groups,cameras=cameraresults))
  print('sightlines',state,'done',flush=True)
 return dict(cases=allresults,scope='Conditional straight-ray geometry. Pupil native z0/7/14 are sensitivity assumptions, not known physical pupil bounds. 5x5 empty target patches at head Z20/40/65/100; no opaque workpiece, lens projection, calibration or exposure. Solid windows/covers treated opaque; LED/pupil interior is not simulated. Five nominated R states do not prove continuous optical coverage.')

def export_and_draw(rows,petals,central,Y,Z,grid,proof):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 allparts=scene(rows,petals,central,Y,Z,[31]*4)
 # Only original shapes are public; private native camera BREP never enters this dict.
 assembly=cq.Assembly(name='R5-VISION01-original-envelopes')
 for n,s in allparts.items():assembly.add(s,name=n,color=cq.Color(*((.12,.25,.3) if n.startswith('camera') else (.8,.56,.16) if 'LED' in n else (.53,.59,.61))))
 path=OUT/'candidate-original-envelopes.step';assembly.save(str(path))
 sub=cq.Assembly(name='R5-VISION01-fixed-optics-original')
 for n,s in (central|optics(Y,Z)).items():sub.add(s,name=n)
 sub.save(str(OUT/'fixed-optics-original.step'))
 fig,axs=plt.subplots(1,3,figsize=(16,7));axes=[(0,1),(1,2)]
 for ax,ij in zip(axs[:2],axes):
  for n,s in allparts.items():
   if n.startswith('CD01-LED') or 'washer' in n or 'nut' in n or 'screw' in n:continue
   vv,ff=s.tessellate(.3,.15);vv=np.array([v.toTuple() for v in vv]);ff=np.array(ff)
   color='#307b87' if n.startswith('camera') else '#ba8834' if n.startswith('CD01') else '#a2b0b8'
   ax.add_collection(PolyCollection(vv[ff][:,:,ij],facecolors=color,edgecolors='none',alpha=.45))
  ax.autoscale();ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('Head '+['X','Y','Z'][ij[0]]+' [mm]');ax.set_ylabel('Head '+['X','Y','Z'][ij[1]]+' [mm]')
 axs[0].set_title('Front / R31 / original camera proxies');axs[1].set_title('Side / rear retreat and fixed display')
 ax=axs[2]
 for row in grid:
  clear=not row['hits'];ax.scatter(row['Y_mm']*2,row['Z_front_mount_mm'],c='#247e72' if clear else '#b8604e',s=55,marker='o' if clear else 'x')
 ax.scatter([2*Y],[Z],facecolors='none',edgecolors='#143943',s=190,lw=2)
 ax.set(xlabel='Camera mount baseline [mm]',ylabel='Front mounting plane Z [mm]',title='Finite native + installation screen');ax.grid(alpha=.2)
 fig.suptitle('R5-VISION01 / two cameras keep outward 8 degrees / candidate, not released assembly',fontsize=15)
 fig.text(.04,.09,'Selected comparison: mount origins (0, +/-50, -35) mm. No old optical support frame. Camera STEP remains private.',fontsize=10)
 fig.text(.04,.055,'331 real nominal CD01 parts are included. Local plates and screw/FAKRA envelopes do not establish a complete palm attachment or cable routing.',fontsize=9)
 fig.text(.04,.022,'Green grid points are a finite screen only. Selected full-range mechanical proof is separate; camera entrance pupil and image coverage remain uncalibrated.',fontsize=9)
 fig.subplots_adjust(left=.05,right=.98,bottom=.18,top=.86,wspace=.3)
 fig.savefig(OUT/'packaging-review.png',dpi=160);fig.savefig(OUT/'packaging-review.svg',metadata={'Date':None});plt.close(fig)
 return dict(public_objects=len(allparts),fixed_public_objects=len(central)+len(optics(Y,Z)),export_has_no_native_camera_geometry=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--native-camera',type=Path,default=DEFAULT_NATIVE);parser.add_argument('--phase',choices=['all','geometry','optics'],default='all');args=parser.parse_args()
 OUT.mkdir(parents=True,exist_ok=True)
 rows,petals,central,bounds,native,hashes,inputs=load(args.native_camera)
 Y,Z=50.,-35.
 if args.phase in ['all','geometry']:
  grid=finite_scan(rows,native);dump('finite-position-screen.json',grid)
  proofs={}
  for name,yi,zi in REVIEW[1:]:
   print('certificate start',name,flush=True);proofs[name]=certify(yi,zi,rows,petals,bounds);dump('mechanical-certificates.json',proofs);print('certificate',name,proofs[name]['certified'],flush=True)
  assert proofs['compact_retreat']['certified']
 else:
  grid=read(OUT/'finite-position-screen.json');proofs=read(OUT/'mechanical-certificates.json')
 if args.phase in ['all','optics']:
  rays=sightlines(rows,petals,central,Y,Z);dump('sightline-screen.json',rays)
 export=export_and_draw(rows,petals,central,Y,Z,grid,proofs['compact_retreat'])
 sourcefacts=dict(revision='R5-VISION01',license='CC-BY-NC-4.0 original work only',vendor_media_policy='Vendor STEP remains private; original containing geometry only is exported',
  inherited_primary_source='docs/engineering/sources/p16-carrier.json',native_camera=inputs,
  authority='Frozen source hashes, exact nominal BREP; no new catalog procurement qualification',source_hashes=hashes)
 dump('source-audit.json',sourcefacts)
 record=dict(revision='R5-VISION01',status='Fixed optics packaging candidate; no complete mount/frame/optical qualification',manufacturing_release=False,
  selected_comparison=dict(camera_model='ZED X One S Fisheye / ZED-414012',camera_qty=2,front_mount_origins_head_mm=[[0,Y,Z],[0,-Y,Z]],outward_pitch_deg=8,
   rotation='R_x(-sign*8deg), translation[0,sign*Y,Z]',baseline_mm=2*Y,front_mount_retreat_from_old_mm=-14-Z,
   camera_proxy_head_bboxes_mm={n:bb(s) for n,s in optics(Y,Z).items()},central_display_transform=np.eye(4),old_optical_frame_inherited=False),
  baseline_failure=[r for r in grid if r['Y_mm']==50 and r['Z_front_mount_mm']==-14][0],
  finite_grid_count=len(grid),selected_full_R_domain_certificate=proofs['compact_retreat'],other_comparison_certified={k:v['certified'] for k,v in proofs.items()},
  inputs=inputs,source_hashes=hashes,export=export,
  missing=['Camera plate-to-palm support and CD01 ear support; old optical frame is absent','FAKRA mate datum, cable bend radius/strain relief/insertion access','New palm and differential route/drive/backpack integration','Controlled assembly tolerances, fastener grade/preload/retention and thermal boundary','Calibrated entrance pupils, fisheye image masks, illumination glare and real workpiece visibility'],
  boundaries='Mechanical proof concerns only frozen FORM02/CARRIER01 versus this optical candidate. Other unbuilt parts and future topology are excluded. Native camera evidence is private; all public camera shapes are original bounds.')
 dump('study.json',record)
 print('R5-VISION01 geometry packaged',export,flush=True)

if __name__=='__main__':main()
