# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Independent q2 shoulder-domain study; frozen baseline and CAD unchanged."""
import argparse,json,sys,math
from pathlib import Path
import numpy as np
import cadquery as cq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from screen_integrated_collisions import ROOT,load_structure,sha,box
from build_layout import frame,moved
from build_link56_study import cylinder
from mount_interface_study import ring
from studies.link_interface_tools import check,cache,aabb_gap


def setup(paths):
 p,rows,hashes,vendor=load_structure(paths)
 moving={n:r['shape'] for n,r in rows.items() if n.startswith('L23_') or n=='J3'}
 stationary={n:r['shape'] for n,r in rows.items() if n.startswith(('L12_','BASE_')) or n=='J1'}
 # All moving shapes are downstream of J2 but upstream of J3 rotation.
 # Confirm the positive-Y output-interface exception by an invariant envelope
 # against actual J2, never discard a zero-distance pair merely by adjacency.
 env=moved(ring(85,34.8,0,2.5).val().fuse(cylinder([0,0,2.5],[0,0,1],85,107.5)),frame([0,0,170],[0,1,0]));contain=[]
 for n,s in moving.items():
  for i,solid in enumerate(s.Solids()):
   q=solid.cut(env);v=abs(q.Volume()) if q.Solids() else 0;contain.append({'part':n,'solid':i,'outside_mm3':v})
 own=check(env,rows['J2']['shape']);assert not own['events'] and max(q['outside_mm3'] for q in contain)<1e-4,(own,contain)
 radius=max(math.hypot(x,z-170) for s in moving.values() for x in box(s)[:,0] for z in box(s)[:,2])
 return moving,stationary,hashes,vendor,{'J2_invariant_envelope_R_mm':85,'axial_Y_mm':[0,110],'central_void_R_Y_mm':[34.8,0,2.5],'actual_moving_per_solid_containment':contain,'envelope_to_actual_J2':own,'rotation_speed_distance_bound_mm_per_rad':radius}


def at_angle(moving,stationary,angle,minimum=False):
 aa={n:cache(s.rotate((0,0,170),(0,1,170),angle)) for n,s in moving.items()};bb={n:cache(s) for n,s in stationary.items()};events=[];checks=0;booleans=0;best=float('inf');near=None
 pairs=sorted((min(aabb_gap(xb,yb) for _,xb in a for _,yb in b),n,m) for n,a in aa.items() for m,b in bb.items())
 for lower,n,m in pairs:
  if lower>best and minimum:continue
  q=check(aa[n],bb[m],minimum=minimum);checks+=q['pair_count'];booleans+=q['boolean_count']
  if q['events']:events.append({'moving':n,'stationary':m,**q})
  if minimum:
   d=q['minimum_BREP_surface_distance_mm']
   if q['events']:d=0
   if d<best:best=d;near=[n,m]
 return {'q2_deg':float(angle),'events':events,'solid_pair_count':checks,'booleans':booleans,'minimum_distance_mm':best if minimum else None,'nearest_part_pair':near}


def continuous_domain(moving,stationary,radius):
 memo={}
 def sample(a):
  key=round(float(a),12)
  if key not in memo:
   memo[key]=at_angle(moving,stationary,key,True)
   print('distance',key,memo[key]['minimum_distance_mm'],flush=True)
  return memo[key]
 def certificate(lo,hi,clearance):
  leaves=[];queries=0
  def visit(a,b,depth=0):
   nonlocal queries
   mid=(a+b)/2;q=sample(mid);queries+=1
   # Every point displacement from the middle angle is at most R*delta.
   # Distance between two sets is 1-Lipschitz in this one-sided displacement.
   displacement=radius*math.radians((b-a)/2)
   lower=q['minimum_distance_mm']-displacement
   if not q['events'] and lower>clearance+1e-6:
    leaves.append({'interval_deg':[a,b],'midpoint_deg':mid,'midpoint_distance_mm':q['minimum_distance_mm'],'rotation_displacement_bound_mm':displacement,'continuous_distance_lower_bound_mm':lower});return
   assert depth<24 and b-a>1e-5,('Unproved interval',a,b,lower,clearance)
   visit(a,mid,depth+1);visit(mid,b,depth+1)
  visit(lo,hi)
  assert abs(sum(x['interval_deg'][1]-x['interval_deg'][0] for x in leaves)-(hi-lo))<1e-9
  return {'interval_deg':[lo,hi],'required_nominal_clearance_mm':clearance,'leaves':leaves,'minimum_certified_clearance_mm':min(x['continuous_distance_lower_bound_mm'] for x in leaves),'no_gaps_in_interval_partition':True,'sample_queries':queries}
 certificates=[certificate(-25,25,1.),certificate(-20,20,2.)]
 transitions=[]
 for sign in [-1,1]:
  lo,hi=25.,30.;assert not sample(sign*lo)['events'] and sample(sign*lo)['minimum_distance_mm']>1e-6;assert sample(sign*hi)['events'] or sample(sign*hi)['minimum_distance_mm']<=1e-6
  while hi-lo>.0025:
   mid=(lo+hi)/2;q=sample(sign*mid)
   if q['events'] or q['minimum_distance_mm']<=1e-6:hi=mid
   else:lo=mid
  transitions.append({'sign':sign,'magnitude_free_point_deg':lo,'magnitude_contact_or_overlap_point_deg':hi,'free_point':sample(sign*lo),'contact_or_overlap_point':sample(sign*hi),'interpretation':'Local transition in25..30deg, not by itself a proof of no earlier contact.'})
 neg=transitions[0]['magnitude_free_point_deg']-.05;pos=transitions[1]['magnitude_free_point_deg']-.05
 extended=certificate(-neg,pos,.01);certificates.append(extended)
 return {'displacement_bound_mm_per_rad':radius,'distance_method':'Exact per-solid BREP distance and Boolean common at each midpoint; no mesh-distance or projection proxy.','proof':'Moving point velocity magnitude <= R about fixed J2, so Hausdorff displacement over half interval <= R*deltaRadians. Subtract this from exact midpoint minimum distance. All accepted closed leaves cover the entire specified interval.','certificates':certificates,'local_contact_transitions':transitions,'first_obstruction_from_zero_magnitude_brackets_deg':{'negative':[neg,transitions[0]['magnitude_contact_or_overlap_point_deg']],'positive':[pos,transitions[1]['magnitude_contact_or_overlap_point_deg']]},'distance_samples':list(memo.values()),'recommended_research_domain_deg':[-25,25],'recommendation_status':'Derived nominal local shoulder-only domain with >=1mm proved geometric separation to specified objects; not an executable full-arm limit or tolerance/load/cable approval.'}


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',action='append',required=True);ap.add_argument('--out',type=Path,default=ROOT/'engineering/generated/shoulder-domain-01');args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True);paths={n:Path(q) for n,q in (s.split('=',1) for s in args.model)}
 moving,stationary,hashes,vendor,proof=setup(paths);r={'revision':'SHOULDER-DOMAIN01','sources_sha256':hashes,'vendor_sources':vendor,'moving':list(moving),'stationary':list(stationary),'own_J2_interface':proof,'samples':[],'scope':'J2 single-axis relative L23/J3 versus J1/BASE/L12. No L34 onwards, no fingers/cables/objects/hardware or coupled q3 domain qualification. Original motors/baseline limits unchanged.','hardware_qualified':False}
 for angle in [-90,-75,-65,-60,-45,-30,-25,0,25,30,45,60,65,75,90]:
  print('q2',angle,flush=True);q=at_angle(moving,stationary,angle);r['samples'].append(q);print([(x['moving'],x['stationary'],x['solid_pair_intersection_sum_mm3']) for x in q['events']],flush=True);(args.out/'study.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 r['continuous']=continuous_domain(moving,stationary,proof['rotation_speed_distance_bound_mm_per_rad'])
 for path in [Path(__file__),ROOT/'engineering/screen_integrated_collisions.py',ROOT/'engineering/build_layout.py',ROOT/'engineering/mount_interface_study.py',ROOT/'engineering/studies/link_interface_tools.py']:r['sources_sha256'][str(path.relative_to(ROOT))]=sha(path)
 r['generator_sha256']=sha(Path(__file__));(args.out/'study.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('Shoulder domain complete',flush=True)
if __name__=='__main__':main()
