# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""A bounded allocation for head electronics, not a finished board or housing."""
from pathlib import Path
import hashlib,json,math
import cadquery as cq
import numpy as np
from screen_integrated_collisions import named_step
from studies.link_interface_tools import check,cache
import p16_packaging_study as p16
import gripper_root_support_study as st

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/head-control-volume01'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def draw(shapes, spec, volume):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.patches import Rectangle
 fig,axes=plt.subplots(1,2,figsize=(13,8));fig.suptitle('HEAD-CTRL-VOLUME01 | internal electronics allocation',fontsize=18)
 for ax,k,title in zip(axes,[0,1],['FRONT / X-Z','SIDE / Y-Z']):
  for n,s in shapes.items():
   if spec[n]['group']!='head_fixed':continue
   vs,fs=s.tessellate(.8,.2);v=np.array([x.toTuple() for x in vs]);f=np.array(fs)
   color='#748896' if spec[n]['material']!='space_reservation' else '#875b87'
   ax.add_collection(PolyCollection(v[f][:,:,[k,2]],facecolors=color,edgecolors='none',alpha=.025))
  extent=28 if k==0 else 32
  ax.add_patch(Rectangle((-extent,-113),2*extent,30,facecolor='#eda843',edgecolor='#a75a00',alpha=.65,lw=2))
  for z in [-109,-94]:
   edge=25 if k==0 else 29
   ax.add_patch(Rectangle((-edge,z),2*edge,1.6,facecolor='#205b7f',edgecolor='none'))
  ax.annotate('Whole installed package reservation',xy=(0,-106),xytext=(-86,-145),arrowprops={'arrowstyle':'->'},fontsize=10)
  ax.annotate('PCB planes are provisional',xy=(0,-92.4),xytext=(-86,-158),arrowprops={'arrowstyle':'->'},fontsize=10)
  ax.set(xlim=(-95,95),ylim=(-172,20),xlabel=('Head X / mm' if k==0 else 'Head Y / mm'),ylabel='Head Z / mm',title=title)
  ax.set_aspect('equal');ax.grid(alpha=.15)
 fig.text(.07,.09,'''56 x 64 x 30 mm envelope includes parts, mated connectors, supports and insulation.
2.0 mm minimum nominal fixed-part gap; independent finger/P16 motion checked.
Grey: original metal and catalog envelopes. Purple: existing camera/display reservations. No board or harness release.''',fontsize=10)
 fig.subplots_adjust(top=.89,bottom=.20,wspace=.22)
 for suffix in ['png','svg']:fig.savefig(OUT/('allocation.'+suffix),dpi=160,facecolor='white')
 plt.close(fig)

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 head=ROOT/'engineering/generated/head-integrated-03';mp=head/'blender-parts-manifest.json';manifest=json.loads(mp.read_text());sp=head/'HEAD-INTEGRATED03-open.step'
 shapes=named_step(sp);spec={x['id']:x for x in manifest['parts']}
 # Entire allocation includes substrate, parts, mated connectors, supports and
 # dielectric/thermal provisions. The smaller board rectangle alone is not this.
 volume=cq.Solid.makeBox(56,64,30,cq.Vector(-28,-32,-113));vc=cache(volume)
 fixed=[]
 for n,s in shapes.items():
  if spec[n]['group']!='head_fixed':continue
  rr=check(vc,cache(s));dist=float(volume.distance(s));assert not rr['events'],(n,rr)
  fixed.append(dict(part=n,gap_mm=dist,representation=spec[n]['representation']))
 # All real rotating finger solids already have rigorous support-plane bounds
 # derived from their containing local AABBs and sine/cosine extrema.
 motion_path=head/'motion.json';motion=json.loads(motion_path.read_text());rot=[]
 for r in motion['wrist_extension_inheritance']['integrated_rotor_bounds']:
  low=r['minimum_world_z_bound_mm']-804
  gap=low-(-83);assert gap>0
  rot.append(dict(finger=r['finger'],range_deg=r['q_range_deg'],rotor_z_lower_bound_mm=low,volume_z_upper_mm=-83,continuous_z_gap_bound_mm=gap))
 # Native-containing P16 envelope; use a conservative global point speed bound.
 fingers=json.loads((ROOT/'engineering/generated/contact02-study/study.json').read_text())['fingers']
 beta=26*(123+26)/p16.kin(0)[2]**2;V=26+160*beta;act=[]
 for i,f in enumerate(fingers):
  proof=p16.certificate(lambda q:st.comp([st.place(s,f,st.SIGNS[i]) for s in p16.envelopes(q).values()]),lambda q:volume,V,f['closure_study_deg'],step=4)
  assert proof['certified'],(f['id'],proof);act.append(dict(finger=f['id'],**proof));print(f['id'],proof['continuous_lower_bound_mm'],flush=True)
 draw(shapes,spec,volume)
 path=OUT/'HEAD-CTRL-VOLUME01-reservation.step';cq.exporters.export(volume,str(path))
 rt=cq.importers.importStep(str(path)).val();assert rt.isValid() and abs(rt.Volume()-volume.Volume())<1e-4
 sources=[Path(__file__),mp,sp,motion_path,ROOT/'engineering/generated/contact02-study/study.json',ROOT/'engineering/p16_packaging_study.py',ROOT/'engineering/gripper_root_support_study.py',ROOT/'engineering/generated/p16-packaging-study/study.json',ROOT/'engineering/studies/link_interface_tools.py',ROOT/'engineering/screen_integrated_collisions.py']
 report=dict(revision='HEAD-CTRL-VOLUME01',head_coordinate_frame='HEAD03 face origin, +Z towards object; unaffected by rigid parent shoulder raise',
  bbox_head_mm=[[-28,-32,-113],[28,32,-83]],volume_is='Reservation for the whole installed electronics package, including connectors/supports/thermal and insulation; not a PCB or metallic part',
  provisional_board_outline_limit_mm=[50,58],stack_levels_candidate_z_mm=[-109,-94],board_candidate_thickness_mm=1.6,
  connector_warning='A50x58 substrate leaves only3mm per side within56x64. Side-facing mated plug/strain relief often exceeds this. Reduce board outline or route axially inside volume; exact connector package must fit before layout release.',
  fixed_objects=len(fixed),fixed_gap_checks=fixed,minimum_fixed_nominal_gap_mm=min(x['gap_mm'] for x in fixed),
  rotor_support_plane_proofs=rot,actuator_continuous_proofs=act,
  source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},reservation_step_sha256=sha(path),visual_artifacts={n:sha(OUT/n) for n in ['allocation.png','allocation.svg']},
  manufacturing_release=False,board_outline_frozen=False,
  exclusions=['Actual PCBs/components/fasteners/heat spreader and harness do not exist in this reservation','No connector insertion path, screw tool path, insulation or loaded tolerance stack checked','No air cooling or heat dissipation qualification','Wires leaving reservation and head detach/mating interface still unbuilt','No full-arm motion or payload approval'])
 (OUT/'study.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS allocation',report['minimum_fixed_nominal_gap_mm'],flush=True)

if __name__=='__main__':main()
