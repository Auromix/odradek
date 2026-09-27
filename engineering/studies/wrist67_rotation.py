# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Continuous q6 proof for LINK67/J7 versus J6/L56, independent of head EXT24.

Read frozen original STEP and private vendor paths. Shape supersets prove absence
of collision only after every input solid is checked for containment; a superset
collision would remain inconclusive until the actual BREP is tested.
"""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import cadquery as cq
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from screen_integrated_collisions import ROOT,OUT,sha,load_structure,box
from build_layout import frame,moved
from mount_interface_study import ring
from build_link56_study import cylinder
from studies.link_interface_tools import cache,check
import build_link67_study as l67

def run(paths):
 p,structure,hashes,vendor=load_structure(paths)
 interface=ROOT/'docs/engineering/sources/rh-interface-extraction.json';models={m['id']:m for m in json.loads(interface.read_text())['models']};i17=models['RH17-B']['unified_joint_interface'];i14=models['RH14-N']['unified_joint_interface']
 op=np.array([q['xy_mm'] for q in i17['output_holes']['points']]);fp=np.array([q['xy_mm'] for q in i14['fixed_through_holes']['points']]);T6=frame([0,0,605],[0,1,0]);T7=frame([0,55,640],[0,0,1]);hw,_,_,rows=l67.make_hardware(op,fp,T6,T7)
 prior=l67.load_prior(models);prior['J6']=structure['J6']['shape']
 half=cq.Workplane('XY').box(1000,1000,1000).translate((0,500,605)).val()
 originals={n:r['shape'] for n,r in structure.items() if n.startswith('L67') or n=='J7'};moving=dict(originals)
 # OEM output bolts are incomplete due to unknown thread length. The part below
 # Y0 belongs in the OEM rotating output, whose internal rotor is not identified
 # in the STEP. Keep the known stub separate instead of causing false collisions
 # against a rotor whose bores were incorrectly held stationary.
 moving.update({'L67_HW_'+n:s.intersect(half) if n.startswith('OUT_') else s for n,s in hw.items()})
 envelope=moved(ring(65,23.8,0,2.5).val().fuse(cylinder([0,0,2.5],[0,0,1],65,102.5)),T6)
 contained=[]
 for n,shape in moving.items():
  for i,solid in enumerate(shape.Solids()):
   outside=solid.cut(envelope);volume=abs(outside.Volume()) if outside.Solids() else 0;contained.append({'part':n,'solid':i,'outside_envelope_mm3':volume});assert volume<1e-4,(n,i,volume)
 checks={n:check(envelope,s) for n,s in prior.items()};assert not any(q['events'] for q in checks.values())
 # Verify each known internal M3 stub separately, and its full revolution against
 # external L56 structure/hardware only; no claim about unidentified OEM internals.
 stubenv=moved(cylinder([0,0,-3],[0,0,1],28.5,3),T6);stubcontain=[]
 for n,s in hw.items():
  if not n.startswith('OUT_'):continue
  internal=s.cut(half)
  for i,solid in enumerate(internal.Solids()):
   q=solid.cut(stubenv);v=abs(q.Volume()) if q.Solids() else 0;assert v<1e-4;stubcontain.append({'part':n,'solid':i,'outside_mm3':v})
 stubchecks={n:check(stubenv,s) for n,s in prior.items() if n!='J6'};assert not any(q['events'] for q in stubchecks.values())
 # Direct real-solid witness at the study endpoints and centre. These are
 # supplemental; continuous coverage comes from the rotation-invariant body.
 witnesses=[]
 targets={n:cache(s) for n,s in prior.items()}
 for angle in [-100,0,100]:
  print('q6 actual witness',angle,flush=True);events=[];count=0;bp=0
  for n,s in moving.items():
   rotated=s.rotate((0,0,605),(0,1,605),angle)
   for other,target in targets.items():
    q=check(rotated,target);count+=q['pair_count'];bp+=q['boolean_count']
    if q['events']:events.append({'part':n,'other':other,**q})
  assert not events;witnesses.append({'q6_deg':angle,'solid_pairs':count,'booleans':bp,'events':events})
 for path in [Path(__file__),ROOT/'engineering/screen_integrated_collisions.py',ROOT/'engineering/build_link67_study.py',ROOT/'engineering/build_link56_study.py',ROOT/'engineering/build_layout.py',ROOT/'engineering/mount_interface_study.py',ROOT/'engineering/studies/link_interface_tools.py']:hashes[str(path.relative_to(ROOT))]=sha(path)
 return {'revision':'WRIST67-ROTATION01','source_sha256':hashes,'vendor_sources':vendor,'requested_q6_interval_deg':[-100,100],'proven_geometric_interval_deg':[-180,180],'main_axis_world':{'point_mm':[0,0,605],'direction':[0,1,0]},'invariant_envelope_joint_coordinates_mm':{'outer_radius':65,'axial_start_end':[0,105],'centre_void_radius':23.8,'centre_void_axial_start_end':[0,2.5]},'containment_per_solid':contained,'envelope_to_prior_checks':checks,'internal_M3_stub_containment':stubcontain,'internal_M3_stub_envelope_to_external_L56':stubchecks,'actual_BREP_witnesses':witnesses,'moving_originals':['L67_output_adapter','L67_rear_carrier','L67_front_ring','J7'],'moving_known_hardware':len(hw),'stationary_targets':list(prior),'common_upstream_transforms_cancel':True,'continuous_mechanical_scope_qualified':True,'head_EXT24_included':False,'OEM_rotor_internal_thread_qualified':False,'trajectory_qualified':False,'limits':['Only LINK67, actual J7 and the reported external known screw geometry versus actual J6 and L56 originals plus known L56 hardware.','This relation survives a common upstream rigid transform; it does not address other upstream parts whose relative transform differs.','J6 OEM rotating output internals are not disassembled/classified; known internal M3 stubs tested against external L56 only, unknown complete thread lengths excluded.','No head, cables, tolerances, deformation, end stops or load/velocity/acceleration constraints. Geometric full turn is not a hardware range approval.']}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',action='append',required=True,metavar='ID=PATH');ap.add_argument('--out',type=Path,default=OUT/'wrist67-rotation.json');args=ap.parse_args();paths={n:Path(q) for n,q in (s.split('=',1) for s in args.model)}
 r=run(paths);args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('Continuous q6 geometric proof complete',flush=True)
if __name__=='__main__':main()
