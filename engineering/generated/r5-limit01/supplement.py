#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Extra nominal geometric evidence and drawings; no impact or manufacture release."""
from pathlib import Path
import sys,itertools,math,json
import numpy as np,cadquery as cq
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'engineering'))
import r5_limit01 as c
from head_mass04_study import shift_inertia
OUT=Path(__file__).resolve().parent

def aggregate(rows):
 mass=sum(r['mass_kg'] for r in rows);p=sum(r['mass_kg']*np.array(r['COM_part_m']) for r in rows)/mass
 I=sum(np.array(r['inertia_COM_part_axes_kg_m2'])+shift_inertia(r['mass_kg'],np.array(r['COM_part_m'])-p) for r in rows)
 c.tensor_check(I)
 return dict(mass_kg=mass,COM_root_m=p,inertia_COM_root_axes_kg_m2=I)
def extra(rows,added,removed):
 d={r['id']:r['shape'] for r in rows};new={r['id']:r['shape'] for r in added}
 # A retained adjustment shim is compressed against its integral boss. A
 # thickness change translates a face; it does not rotate the face to restore
 # area contact at a new stop angle. First-contact angles use endpoint equations.
 adjustments=[]
 for tag in ['upper','lower']:
  a=math.radians(89.5 if tag=='upper' else .5)
  for h in [.95,1.,1.05]:
   delta=h-1
   if tag=='upper':
    ends=[(3.5+z*math.cos(a))/math.sin(a)+delta for z in [11.5,14.5]]
    qs=[brentq(lambda q:(3.5+z*math.cos(q))/math.sin(q)-x,math.radians(85),math.radians(94))*180/math.pi for z,x in zip([11.5,14.5],ends)]
    contact=min(qs)
   else:
    ends=[(-7.5+x*math.sin(a))/math.cos(a)+delta for x in [20,23]]
    qs=[brentq(lambda q:(-7.5+x*math.sin(q))/math.cos(q)-z,math.radians(-3),math.radians(4))*180/math.pi for x,z in zip([20,23],ends)]
    contact=max(qs)
   adjustments.append(dict(stop=tag,shim_mm=h,nominal_translation_mm=delta,edge_equation_angles_deg=qs,first_contact_angle_deg=contact,full_area_contact_only_if_nominal_1mm=h==1.))
 # Tool cylinders stop at head face; socket recesses are omitted from mass proxies.
 tools=[]
 specs=[('cap_mount_M3x12_0',c.cyl(1.6,-65,-29,x=0,z=-14),[]),('cap_mount_M3x12_10',c.cyl(1.6,-65,-29,x=10,z=-14),[]),('upper_clamp_M3x6',c.cyl(1.6,-65,-29,x=4,z=13),[]),('lower_clamp_M3x6',c.cyl(1.6,-65,-29,x=22,z=-9),[]),('upper_shim_retainer_M2x5',c.cyl(1.05,0,20,axis='x',y=-28.5,z=13),['upper_clamp_M3x6']),('lower_shim_retainer_M2x5',c.cyl(1.05,-13,7,axis='z',x=22,y=-28.5),['lower_clamp_M3x6'])]
 for target,tool,absent in specs:
  blocked=[];full=[]
  for n,s in d.items():
   if n==target or n=='fixed_fold_guide':continue
   s=c.pose(s,0,45 if next(r['group'] for r in rows if r['id']==n)=='rotor' else 0).translate((0,0,-20))
   if not c.broad(tool,s):continue
   v=c.common(tool,s)
   if v>1e-5:
    full.append(dict(part=n,overlap_mm3=v))
    if n not in absent:blocked.append(full[-1])
  assert not blocked,(target,blocked)
  tools.append(dict(target=target,nominal_tool_radius_mm=1.6 if 'M3' in target else 1.05,assembly_state='Isolated branch, q45, fixed guide absent; shim retainer before associated clamp screw',temporarily_absent_ids=absent,violations=blocked,installed_state_obstructions=full,does_not_certify_four_branch_in_situ_service=True))
 # Strict analytic own-module bounds use actual frozen petal strips.
 petalproof=[]
 for kind,hand in itertools.product(['upper','lower'],['right','left']):
  s=cq.Compound.makeCompound(list(c.petal(kind,hand).values()));v=[]
  for y in [-9.5,-20.5,-21]:
   ss=s.intersect(c.box(-1,200,-100,y,-50,50));b=c.bbox(ss) if c.vol(ss)>1e-8 else None
   v.append(dict(y_upper_mm=y,native_strip_x_min_mm=float(b[0,0]) if b is not None else None,empty=b is None))
  petalproof.append(dict(kind=kind,hand=hand,strips=v))
 small=min(r['strips'][0]['native_strip_x_min_mm'] for r in petalproof if not r['strips'][0]['empty'])
 pad=min(r['strips'][1]['native_strip_x_min_mm'] for r in petalproof if not r['strips'][1]['empty'])
 tongueR=math.hypot((3.5+14.5*math.cos(math.radians(89.5)))/math.sin(math.radians(89.5)),14.5)
 proof=dict(scope='New stationary hardware versus own frozen rotor/petals for all q in [.5,89.5], any common R; nominal analytic separators, not tolerance or wall-following proof.',petal_strip_checks=petalproof,
 upper_tongue_to_petal_radial_lower_mm=small-tongueR,upper_pad_to_petal_radial_lower_mm=pad-math.hypot(7.5,17),upper_slide_rail_to_petal_radial_lower_mm=pad-math.hypot(7,18),
 lower_bridge_to_petal_z_lower_mm=2.,outside_plate_to_petal_y_lower_mm=.5,
 root_fasteners_to_new_tongues_y_lower_mm=1.5,
 circular_root_parts_max_radius_mm=7.5,new_overlapping_root_cheek_tongue_radius_min_mm=11.5,
 cradle_base_contact_proof={'upper':'For z>=11.5, front boundary x(q,z)=(3.5+z*cosq)/sinq decreases strictly: derivative=-(z+3.5*cosq)/sin(q)^2<0. Stop face equals it only at q89.5. Other q values put the moving base farther +X.', 'lower':'For x>=20, bottom boundary z(q,x)=(-7.5+x*sinq)/cosq increases strictly: derivative=(x-7.5*sinq)/cos(q)^2>0. Stop top equals it at q.5; above this angle the moving base is above the stop. At q90 base x<=7.5.'},
 prerequisites=['Actual petal source hashes unchanged; no overhanging wires or LEDs beyond frozen CAD','New arch box/primitives remain at stated Y and Z; new-to-old fixed mounting intersections separately checked','Circular cheek/shaft geometry uses construction radii; bearings are intended fits, not inferred clearance'])
 assert min(proof[k] for k in ['upper_tongue_to_petal_radial_lower_mm','upper_pad_to_petal_radial_lower_mm','upper_slide_rail_to_petal_radial_lower_mm'])>0
 # Root-coordinate additive mass ledger; negative removal not called a physical body.
 oldtrans=[r for r in c.frozen()[0] if r['group'] in ['carrier','bearing']]
 newtrans=[r for r in rows if r['group'] in ['carrier','bearing']]
 ext=[]
 for r in added:
  b=c.bbox(r['shape']);rmax=math.hypot(91+b[1,0],max(abs(b[:,1])));rmin=math.hypot(31+b[0,0],min(abs(b[:,1])))
  ext.append(dict(id=r['id'],radial_outer_upper_mm=rmax,front_projection_radius_lower_mm=rmin,head_Z_min_mm=b[0,2]+20,head_Z_max_mm=b[1,2]+20))
 bounds=dict(added_parts=ext,new_parts_outer_D_upper_mm=2*max(r['radial_outer_upper_mm'] for r in ext),old_mechanism_outer_D_upper_mm=256.530699917,
 new_projection_to_D60_gauge_lower_mm=min(r['front_projection_radius_lower_mm'] for r in ext)-30,
 D60_is_only_a_gauge_not_actual_display_or_camera=True,
 old_mechanism_Zmin_mm=-17,new_parts_head_Zmin_mm=min(r['head_Z_min_mm'] for r in ext))
 assert bounds['new_parts_outer_D_upper_mm']<bounds['old_mechanism_outer_D_upper_mm']
 m=dict(added=aggregate(added),removed_old_fastener_proxies=aggregate(removed),old_translation_body=aggregate(oldtrans),new_translation_body=aggregate(newtrans),
 increment_per_branch_kg=sum(r['mass_kg'] for r in added)-sum(r['mass_kg'] for r in removed),
 coordinate_frame='Hinge zero-angle frame, metres; all added/replaced parts only translate radially with R, no q rotation. COM and tensor in these axes.',
 unknowns=['Exact fastener recess/thread mass','Material grade/heat treatment/actual density','Wiring/rail/palm/drive/return hardware'],rotor_unchanged=True,whole_head_mass_kg=None)
 c.dump(OUT/'adjustment-tool-own-proof.json',dict(shim_adjustment=adjustments,tools=tools,own_continuous_separators=proof))
 c.dump(OUT/'mass-and-envelope.json',dict(mass=m,envelope=bounds))
 # Reproduce the small pre-trim collision at R40. Fill the removed0.5mm slab.
 oldarch=new['external_negative_side_stop_arch'].fuse(c.box(-8,-3,-31,-21,10,10.5));guide=c.azimuth(d['fixed_fold_guide'],45)
 witness=[]
 for label,s in [('pretrim',oldarch),('final',new['external_negative_side_stop_arch'])]:
  a=c.pose(s,40,0,135);witness.append(dict(geometry=label,R_mm=40,part='stop_arch_UL_vs_guide_UR',overlap_mm3=c.common(a,guide),distance_mm=a.distance(guide)))
 assert witness[0]['overlap_mm3']>1e-5 and witness[1]['overlap_mm3']<1e-6
 c.dump(OUT/'pretrim-counterexample.json',dict(change='Upper shim/backing boss lower edge localZ10 ->10.5; contact faces and mounting bores unchanged.',witness=witness))
 return m,bounds

def drawings(rows,added):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.backends.backend_pdf import PdfPages
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42})
 def draw(ax,s,axes=(0,2),color='#738792',alpha=1):
  v,f=s.tessellate(.08,.13);v=np.array([p.toTuple() for p in v]);ax.add_collection(PolyCollection(v[np.array(f)][:,:,axes],facecolors=color,edgecolors='none',alpha=alpha,rasterized=True));ax.autoscale_view()
 def fmt(ax,xlab,ylab):ax.set_aspect('equal');ax.grid(alpha=.14);ax.set_xlabel(xlab);ax.set_ylabel(ylab)
 def footer(fig,n):fig.text(.04,.022,c.NOTICE+f' | CC BY-NC4.0 | nominal stop candidate, not manufacture release | {n}/2',fontsize=7,color='#64747d')
 with PdfPages(OUT/'R5-LIMIT01-local-dimensions.pdf') as pdf:
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('R5 / guarded hinge stops on the translating carrier',x=.045,y=.96,ha='left',fontsize=17)
  for i,q in enumerate([.5,89.5]):
   ax=fig.add_axes([.055+i*.47,.42,.415,.43]);
   for r in rows:
    if r['group']=='guide':continue
    s=c.pose(r['shape'],0,q if r['group']=='rotor' else 0).translate((0,0,-20))
    if r['id'] in ['upper_guard_contact_bridge','lower_guard_contact_bridge']:
     ss=s.intersect(c.box(-100,100,-10.67,-10.63,-100,100))
     draw(ax,ss,color='#b4824f')
    elif r['origin']==c.REV:draw(ax,s,color='#b4824f',alpha=.12)
    elif r['id']=='rotor_split_trunnion_cradle':draw(ax,s.intersect(c.box(-100,100,-10.67,-10.63,-100,100)),color='#345e73',alpha=.9)
    elif r['id'] in ['bearing_pedestal_negative','outer_cap_negative']:draw(ax,s,color='#9fadb2',alpha=.25)
   ax.set_xlim(-13,36);ax.set_ylim(-24,27);fmt(ax,'Hinge local X [mm]','Hinge local Z [mm]');ax.set_title(f'Section Y=-10.65 / q={q:g} deg',loc='left',fontsize=11)
   ax.plot(0,0,'+',color='#2c485c');ax.text(1,1,'axis',fontsize=7)
   ax.annotate('2 x M3 / 10mm pitch',(5,-14),(14,-23),arrowprops={'arrowstyle':'->'},fontsize=8)
   if i==0:ax.annotate('Lower matched face\n0.5 deg guard',(21.5,-7.31),(-12,-9),arrowprops={'arrowstyle':'->'},fontsize=8)
   else:ax.annotate('Upper matched face\n89.5 deg guard',(3.614,13),(11,23),arrowprops={'arrowstyle':'->'},fontsize=8)
  fig.text(.06,.325,'Nominal contact: 6.9003 mm2 per end; the original steel cradle is unchanged.\nThe 0.5 deg guards reserve angular room for calibration and deformation; no physical tolerance budget is closed.\nAt q89.5 the stop blocks further closing. It cannot react the opposite opening moment of object grip.',fontsize=10,linespacing=1.55,va='top')
  fig.text(.06,.19,'Slot8.3 / followerD8 permits a nearby assembly band reaching about -1.540..91.540 deg (sampled).\nA clipped nominal path fits the ideal groove, but two rigid constraints can still jam with runout or tolerance.\nThis candidate is an angle fence, not a controller, a return mechanism or proof of contact with a slot wall.',fontsize=10,color='#805b3b',linespacing=1.5,va='top')
  footer(fig,1);pdf.savefig(fig);fig.savefig(OUT/'stop-end-positions.png',dpi=180);plt.close(fig)
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('Stop module / sections / nominal fixing and adjustment',x=.045,y=.96,ha='left',fontsize=17)
  d={r['id']:r['shape'] for r in rows}
  ax=fig.add_axes([.055,.47,.39,.39]);
  for r in added:
   if 'lower' not in r['id']:draw(ax,r['shape'],axes=(1,2),color='#b4824f',alpha=.85)
  for n in ['rotor_split_trunnion_cradle','outer_cap_negative']:draw(ax,d[n],axes=(1,2),color='#47697b',alpha=.3)
  fmt(ax,'Local Y [mm]','Local Z [mm]');ax.set_xlim(-34,-7);ax.set_ylim(-20,22);ax.set_title('Axial view / upper stop',loc='left',fontsize=11)
  for y in [-26,-23.5,-20,-11.8,-9.5]:ax.axvline(y,ls=':',lw=.5,color='#586c76');ax.text(y,21,str(y),rotation=90,va='top',fontsize=7)
  ax2=fig.add_axes([.51,.50,.44,.33])
  arch=d['external_negative_side_stop_arch'];draw(ax2,arch,color='#ab7847')
  fmt(ax2,'Local X [mm]','Local Z [mm]');ax2.set_xlim(-12,33);ax2.set_ylim(-24,23);ax2.set_title('Outer plate / mounting pattern',loc='left',fontsize=11)
  for x,z,label in [(0,-14,'D3.2'),(10,-14,'D3.2'),(4,13,'3.2 x 3.5 slot'),(22,-9,'3.5 x 3.2 slot')]:ax2.annotate(label,(x,z),(x+3,z+4),arrowprops={'arrowstyle':'->','lw':.6},fontsize=7)
  fig.text(.055,.365,'Plate:2.5 thick at Y-26..-23.5; spacersD6/D3.2 x3.5 to original capY-20.\nReplace only two negative-sideM3x6 by nominalM3x12: same endY-14, original5mm Al engagement.\nBridge clamp: M3x6; upper steel engagement3.0mm / lower3.5mm. Retained backing shims:1.00mm nominal.\nUpper contact tongue:Y-23.5..-9.5, Z11.5..14.5; lower:X20..23, sameY. CAD defines angled faces.',fontsize=9.5,linespacing=1.5,va='top')
  fig.text(.055,.20,'Assembly: off-palm, guide absent; fit backing shims and M2 retainers before the adjacent M3 clamp screws.\nFit module at an intermediate angle, then install the fixed guide and measure both stop angles.\nFlat shims change first-contact angle and create edge contact: regrind or remeasure contact before loading.\nTwo inline cap screws leave peel/preload and thin-cap compliance unresolved. Impact torque is unspecified.',fontsize=9.5,color='#805b3b',linespacing=1.5,va='top')
  footer(fig,2);pdf.savefig(fig);fig.savefig(OUT/'stop-stack-and-mounting.png',dpi=180);plt.close(fig)

if __name__=='__main__':
 rows,added,removed=c.build();extra(rows,added,removed);drawings(rows,added)
 c.dump(OUT/'supplement-sources.json',{str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__),ROOT/'engineering/r5_limit01.py',ROOT/'engineering/generated/r5-carrier01/parts-manifest.json']})
 print('SUPPLEMENT DONE',flush=True)
