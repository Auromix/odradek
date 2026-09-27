# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only source CAD probes for independent J5/J6 coax service segments.
No vendor BREP is exported; geometric probes are not a wiring release.
"""
import argparse,hashlib,json,itertools
from pathlib import Path
import cadquery as cq
import numpy as np
from scipy.spatial import ConvexHull, distance
from screen_integrated_collisions import load_structure,box
from build_link45_study import load_neighbors,make_hardware,make_parts
from build_link56_study import cylinder
from studies.link_interface_tools import check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/internal-harness02'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def axial_probe(rows,origin,axis,span,radius=3.3):
 origin=np.asarray(origin,float);axis=np.asarray(axis,float);T=np.eye(4)
 tube=cylinder(origin+axis*span[0],axis,radius,span[1]-span[0]);tb=tube.BoundingBox();hits=[];count=0
 for name,row in rows.items():
  for i,s in enumerate(row['shape'].Solids()):
   b=s.BoundingBox();overlap=np.prod([max(0.,min(getattr(tb,k+'max'),getattr(b,k+'max'))-max(getattr(tb,k+'min'),getattr(b,k+'min'))) for k in 'xyz'])
   if overlap<=1e-4:continue
   count+=1;common=tube.intersect(s)
   for k,part in enumerate(common.Solids()):
    if part.Volume()<=1e-4:continue
    bb=box(part);corners=np.array(list(itertools.product(*zip(bb[0],bb[1]))));ss=(corners-origin)@axis
    hits.append(dict(object=name,solid=i,intersection_piece=k,volume_mm3=part.Volume(),axial_interval_mm=[float(ss.min()),float(ss.max())]))
 below=[h for h in hits if h['axial_interval_mm'][1]<0];above=[h for h in hits if h['axial_interval_mm'][0]>0];cross=[h for h in hits if h not in below and h not in above]
 lo=max([h['axial_interval_mm'][1] for h in below],default=span[0]);hi=min([h['axial_interval_mm'][0] for h in above],default=span[1])
 return dict(origin_world_mm=origin.tolist(),axis_world=axis.tolist(),tube_radius_mm=radius,search_axis_interval_mm=span,actual_intersections=hits,boolean_count=count,origin_blockers=cross,free_interval_around_output_mm=[lo,hi],free_length_mm=hi-lo,lower_limiter=[h for h in below if abs(h['axial_interval_mm'][1]-lo)<1e-5],upper_limiter=[h for h in above if abs(h['axial_interval_mm'][0]-hi)<1e-5],scope='Home structure, no head; axisymmetric probe makes own-axis downstream rotations invariant. All other axes fixed. Tube encloses two D3.1 cables separated by0.4; no sheath/liner/clamps.'),tube

def ring_math(R,D,inner=None,amp=90):
 inner=max(R,45) if inner is None else inner;outer=inner+2*R;theta0=-np.pi/2;phi0=np.pi/2
 qs=np.deg2rad(np.linspace(-amp,amp,181));phis=phi0+outer/(inner+outer)*qs
 lengths=inner*(phis-theta0)+np.pi*R+outer*(phis-(theta0+qs))
 return dict(bend_radius_mm=R,OD_mm=D,inner_radius_mm=inner,outer_radius_mm=outer,amplitude_deg=amp,diameter_without_cover_mm=2*outer+D,length_mm=float(lengths[90]),length_range_error_mm=float(np.ptp(lengths)),U_angle_deg_extremes=np.rad2deg([phis.min(),phis.max()]).tolist(),fixed_endpoint_angle_deg=-90,moving_endpoint_angle_deg=[-90-amp,-90+amp],formula='phi=pi/2 + rout/(rin+rout)*q; L=rin*(phi+pi/2)+pi*R+rout*(phi+pi/2-q)',scope='Chosen concentric reversed-U planar route only; not universal 3D minimum; support, leads, friction, force, lifespan unqualified')

def connector_probe(p):
 s=cq.importers.importStep(str(p)).val();vs=np.array([v.Center().toTuple() for v in s.Vertices()]);yz=vs[:,1:];hull=yz[ConvexHull(yz).vertices];dist=distance.squareform(distance.pdist(hull));ij=np.unravel_index(np.argmax(dist),dist.shape);bb=box(s)
 return dict(filename=p.name,sha256=sha(p),solid_count=len(s.Solids()),bbox_native_mm=bb.tolist(),size_native_mm=(bb[1]-bb[0]).tolist(),long_axis='native +X',projected_YZ_witness_points_mm=[hull[ij[0]].tolist(),hull[ij[1]].tolist()],axial_insertion_required_diameter_lower_bound_mm=float(dist[ij]),proof='Two actual BREP vertices projected into connector cross-section have this separation; any containing circle must have at least that diameter. This is a lower bound, not exact smallest enclosing circle; excludes axial insertion into smaller bore, not every hypothetical tilted path.',mating_cavity_and_latch_withdrawal_qualified=False)

def j5_offset_route(rows,out):
 # Double tangent arcs: 5mm transverse shift over75mm axial run.
 R=(75.**2+5.**2)/(4*5.);theta=2*np.arctan2(5.,75.)
 low=np.array([0.,-55.,338.]);A=np.array([0.,-55.,450.]);M=np.array([0.,-57.5,487.5]);B=np.array([0.,-60.,525.]);high=np.array([0.,-60.,566.5])
 pm=A+np.array([0.,-R*(1-np.cos(theta/2)),R*np.sin(theta/2)])
 pn=B+np.array([0.,R*(1-np.cos(theta/2)),-R*np.sin(theta/2)])
 edges=[cq.Edge.makeLine(cq.Vector(*low),cq.Vector(*A)),cq.Edge.makeThreePointArc(cq.Vector(*A),cq.Vector(*pm),cq.Vector(*M)),cq.Edge.makeThreePointArc(cq.Vector(*M),cq.Vector(*pn),cq.Vector(*B)),cq.Edge.makeLine(cq.Vector(*B),cq.Vector(*high))]
 w=cq.Wire.assembleEdges(edges);body=cq.Workplane('XY',origin=tuple(low)).circle(1.55).sweep(cq.Workplane().newObject([w])).val();assert body.isValid()
 pair=[body.translate((x,0,0)) for x in [-1.75,1.75]]
 # Envelopes analytically contain the geometric path family for any |q5|<=90.
 # Below output twist angle is q*(s/L); above output compare with rotating L56.
 envelopes={'rear_to_output':cylinder(low-[0,0,1.55],[0,0,1],3.3,112+3.1),
   'early_offset':cylinder(A-[0,0,1.55],[0,0,1],4.,16+3.1),
   'beam_offset':cylinder([0,-55,466-1.55],[0,0,1],8.3,54+3.1),
   'upper_offset':cylinder([0,-60,520-1.55],[0,0,1],5.,46.5+3.1)}
 checkrows={k:{n:check(s,r['shape']) for n,r in rows.items()} for k,s in envelopes.items()}
 errors={k+'__'+n:q for k,rr in checkrows.items() for n,q in rr.items() if q['events']}
 assert not errors,errors
 L=112+2*R*theta+41.5;lam520=(112+2*R*theta-R*np.arcsin(5/R))/L;dev=2*5*np.sin(np.pi/4*(1-lam520))+3.3+(R-np.sqrt(R*R-25))
 assert dev<5 and (R-np.sqrt(R*R-16*16)+3.3)<4
 enclosure=list(envelopes.values())[0]
 for s in list(envelopes.values())[1:]:enclosure=enclosure.fuse(s)
 outside=sum(sum(v.Volume() for v in cable.cut(enclosure).Solids()) for cable in pair);assert outside<1e-4,('neutral outside envelope',outside)
 for name,s in [('J5-two-coax-home-shape',cq.Compound.makeCompound(pair)),('J5-local-family-envelope',cq.Compound.makeCompound(list(envelopes.values())))]:
  path=out/(name+'.step');cq.exporters.export(s,str(path));read=cq.importers.importStep(str(path)).val();assert read.isValid();assert abs(read.Volume()-s.Volume())<1e-3
 return dict(endpoints_world_mm=[low.tolist(),high.tolist()],s_shift_mm=5,s_axial_span_mm=75,bend_radius_mm=R,bend_angle_each_deg=float(np.rad2deg(theta)),neutral_centerline_length_mm=float(L),nominal_wire_diameter_mm=3.1,wire_center_spacing_mm=3.5,neutral_pair_gap_mm=.4,neutral_pair_outside_envelopes_mm3=outside,envelope_axial_padding_mm=1.55,envelope_checks=checkrows,envelope_errors=errors,upper_relative_envelope_radius_required_mm=float(dev),early_relative_envelope_radius_required_mm=float(R-np.sqrt(R*R-16*16)+3.3),envelope_dimensions=[dict(name=n,bbox_mm=box(s).tolist()) for n,s in envelopes.items()],torsion_screen_amplitude_deg=.18*L,extra_length_to_reach90_mm=500-L,scope='Only geometric envelope for distributed endpoint rotation; physical clamp/liner not modelled. Space below520 uses axisymmetric bounds with1.55mm axial tube padding; upper tube expressed in downstream rotating frame. All other joint axes held at home. Variable helix length/slack and combined bend/twist life not qualified.')

def render_review(out,rows,d):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import LineCollection
 from matplotlib.patches import Circle,Rectangle
 import trimesh
 from build_link56_study import projected_edges
 plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
 fig,axs=plt.subplots(2,2,figsize=(15,10),layout='constrained');fig.suptitle('INTERNAL-HARNESS02 | Actual CAD constraints + local coax path study',fontsize=17,fontweight='bold')
 ax=axs[0,0];basis=np.array([[0,1,0],[0,0,1.]])
 for n in ['J5','J6','J7','L45_rear_carrier','L56_lower_block','L56_closed_beam','L56_upper_block','L56_rear_carrier','L67_rear_carrier']:
  s=rows[n]['shape'];v,f=s.tessellate(.35,.18);mesh=trimesh.Trimesh(vertices=np.array([x.toTuple() for x in v]),faces=f,process=False);edge=projected_edges(mesh,basis);ax.add_collection(LineCollection(edge,colors='#a8b3c2' if n.startswith('J') else '#536d85',linewidths=.45,alpha=.7))
 R=282.5;th=2*np.arctan2(5.,75.);u=np.linspace(0,th,70)
 yz=np.vstack([[-55,338],[-55,450],np.c_[-55-R*(1-np.cos(u)),450+R*np.sin(u)],np.c_[-60+R*(1-np.cos(u[::-1])),525-R*np.sin(u[::-1])],[-60,566.5]])
 ax.plot(yz[:,0],yz[:,1],color='#df8512',lw=3,label='J5 coax pair (overlap in side view)');ax.plot([-112,12],[605,605],color='#128c87',lw=3,label='J6 axial local probe')
 ax.scatter([-55,-60], [338,566.5],color='#df8512',s=24)
 ax.annotate('5 mm S-offset / R282.5',xy=(-57.5,487.5),xytext=(-220,485),arrowprops={'arrowstyle':'->'},fontsize=9)
 ax.annotate('J5 local end Z566.5',xy=(-60,566.5),xytext=(-220,548),arrowprops={'arrowstyle':'->'})
 ax.annotate('J6 first blockage Y17',xy=(17,605),xytext=(52,580),arrowprops={'arrowstyle':'->'})
 ax.set(xlim=(-230,110),ylim=(320,665),xlabel='World Y (mm)',ylabel='World Z (mm)',title='A. Nominal orthographic YZ projection; CAD edges, not a machining section');ax.set_aspect('equal');ax.grid(alpha=.15)
 ax=axs[0,1];a=d['J5_offset_candidate'];labels=['J5 local S-offset','J6 local axial'];available=[a['neutral_centerline_length_mm'],124];needed=[500,100/180*1000]
 y=np.arange(2);ax.barh(y,needed,color='#e8edf3',label='Required at +/-180 deg/m');ax.barh(y,available,color=['#df8512','#128c87'],label='Proposed geometric free segment')
 for i,(av,req) in enumerate(zip(available,needed)):ax.text(av+5,i,f'{av:.1f} / {req:.1f} mm',va='center')
 ax.set(yticks=y,yticklabels=labels,xlim=(0,640),xlabel='Independent service length per joint (mm)',title='B. Free-length shortfall: necessary screen, not dynamic qualification');ax.legend(loc='upper right',fontsize=8);ax.set_ylim(-.85,1.6);ax.text(20,-.7,'J5: +271.3 mm for +/-90 deg   |   J6: +431.6 mm for +/-100 deg',fontsize=10);ax.grid(axis='x',alpha=.15)
 ax=axs[1,0]
 for r in [5,6]:ax.add_patch(Circle((0,0),r,fill=False,lw=2 if r==5 else 1,edgecolor='#73879c',linestyle='-' if r==5 else '--'))
 for x in [-1.75,1.75]:ax.add_patch(Circle((x,0),1.55,color='#df8512',alpha=.65))
 witness=np.array(d['connector']['projected_YZ_witness_points_mm']);witness-=witness.mean(axis=0);ax.plot(witness[:,0],witness[:,1],'-o',color='#b24b61',label='Complete FAKRA sample: vertex separation >=15.855')
 ax.set(xlim=(-10,10),ylim=(-10,10),xlabel='Cross-section mm',ylabel='Cross-section mm',title='C. Two bare 3.1 mm coaxes fit an assumed 6.6 mm envelope');ax.set_aspect('equal');ax.text(-9,-8.5,'Solid: D10 bore | dashed: D12\nComplete FAKRA sample fails axial insertion; no cable-life approval.',fontsize=9);ax.legend(loc='upper left',fontsize=7);ax.grid(alpha=.15)
 ax=axs[1,1];names=['CG03 / R75','Basler / R34.5*','OKI / R37*','EC-B / R81.6','EC-T / R106.5'];half=[153.1,72.45,77,168.3,220.1];ax.barh(np.arange(5),half,color=['#df8512','#a7aab4','#a7aab4','#128c87','#497287'])
 for i,x in enumerate(half):ax.text(x+3,i,f'{x:.2f}',va='center')
 ax.set(yticks=np.arange(5),yticklabels=names,xlim=(0,275),xlabel='Chosen 180-degree bend span = 2R + OD (mm)',title='D. Side-cavity scale before wall, clearance, leads or clamps');ax.set_ylim(5.8,-.6);ax.grid(axis='x',alpha=.15);ax.text(0,4.95,'* Basler: conflicting dynamic/static claim. OKI: channel / torsion not qualified.\nNo bar is a complete rotating service-loop solution.',fontsize=9)
 fig.savefig(out/'internal-harness02-review.png',dpi=150);fig.savefig(out/'internal-harness02-review.pdf');plt.close(fig)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--model',action='append',required=True);ap.add_argument('--fakra-step',type=Path,required=True);ap.add_argument('--out',type=Path,default=OUT);ap.add_argument('--reuse-axial',action='store_true');ap.add_argument('--render-only',action='store_true');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 p,rows,hashes,vendors=load_structure({n:Path(q) for n,q in (x.split('=',1) for x in a.model)});models={m['id']:m for m in json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())['models']}
 before,after=load_neighbors(models);parts,op,fp,T4,T5=make_parts(models['RH20-B']['unified_joint_interface'],models['RH17-B']['unified_joint_interface']);hw=make_hardware(op,fp,T4,T5)[0]
 for n,s in {**before,**after,**{'L45_HW_'+k:v for k,v in hw.items()}}.items():
  if '_HW_' in n:rows[n]={'shape':s,'source':'existing geometry function','pre':None}
 hashes.update({str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))})
 for f in ['engineering/screen_integrated_collisions.py','engineering/build_layout.py','engineering/mount_interface_study.py','engineering/studies/link_interface_tools.py','engineering/build_link45_study.py','engineering/build_link56_study.py','engineering/build_link34_study.py','docs/engineering/sources/camera-cable-refresh.json','docs/engineering/harness-and-connectors.md']:hashes[f]=sha(ROOT/f)
 result=dict(revision='INTERNAL-HARNESS02',source_sha256=hashes,vendor_sources=vendors,scope='Independent routing constraints and local read-only geometry probes; no baseline edits or wiring release',structure_count=len(rows),structure_solids=sum(len(v['shape'].Solids()) for v in rows.values()),probes={},manufacturing_release=False,full_harness_qualified=False)
 old=json.loads((a.out/'evidence.json').read_text()) if (a.reuse_axial or a.render_only) else None
 if old:
  for key,digest in old['source_sha256'].items():
   if key!=str(Path(__file__).relative_to(ROOT)):assert sha(ROOT/key)==digest,('stale reuse source',key)
  assert old['vendor_sources']==vendors
  assert old['connector']['sha256']==sha(a.fakra_step), 'changed connector STEP'
  result['reused_axial_probe_previous_generator_sha256']=old['source_sha256'][str(Path(__file__).relative_to(ROOT))]
  if a.render_only:
   render_review(a.out,rows,old);old['plot_regenerated_from_existing_evidence']=True;old['source_sha256']=hashes;(a.out/'evidence.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n');return
 for joint,span in [('J5',[-400,250]),('J6',[-300,200])]:
  j=next(x for x in p['joints'] if x['id']==joint);print('Probe',joint,flush=True);r,t=(old['probes'][joint],None) if old else axial_probe(rows,j['origin_mm'],j['axis'],span);assert not r['origin_blockers'],r['origin_blockers'];result['probes'][joint]=r
  r['search_end_is_physical_limit']=[bool(r['lower_limiter']),bool(r['upper_limiter'])]
  r['search_extent_is_available_local_length']=False
  if not all(r['search_end_is_physical_limit']):r['scope']+=' Search boundary is not a physical obstruction; do not infer a maximum free length from it.'
  r['clamp_plane_clearance_assumption_mm']=5;r['diagnostic_trimmed_probe_length_mm']=r['free_length_mm']-10
  r['baseline_amplitude_deg']=max(abs(x) for x in j['limit_deg']);r['required_straight_free_length_mm']=1000*r['baseline_amplitude_deg']/180
  for key in ['free_length_after_two_5mm_offsets_mm','optimistic_pure_torsion_amplitude_at180_deg_per_m','additional_length_for_this_straight_route_mm']:r.pop(key,None)
  r['length_caution']='Diagnostic straight tube only. The search interval is not an independent service segment, even where both limiters are physical. No available torsion length or length shortfall is inferred here; use separate explicitly located J5/J6 local candidates.'
  lo,hi=r['free_interval_around_output_mm'];good=cylinder(np.array(j['origin_mm'])+np.array(j['axis'])*(lo+5),j['axis'],3.3,hi-lo-10);checks={n:check(good,x['shape']) for n,x in rows.items()};assert not any(x['events'] for x in checks.values());r['trimmed_probe_per_object_checks']=checks
  path=a.out/(joint+'-coax-corridor-probe.step');cq.exporters.export(good,str(path));back=cq.importers.importStep(str(path)).val();assert back.isValid();r['probe_export']={'filename':path.name,'sha256':sha(path),'volume_error_mm3':abs(good.Volume()-back.Volume()),'status':'Original geometric clearance probe, not real installed cables'}
 result['J5_offset_candidate']=j5_offset_route(rows,a.out)
 result['J6_local_clamp_case']={'rear_clamp_y_mm':-112,'front_clamp_y_mm':12,'free_straight_length_mm':124,'torsion_screen_at180_amplitude_deg':22.32,'additional_length_for100_deg_mm':100/180*1000-124,'scope':'Plane locations only, 10mm behind physical J6 rear and5mm before L67 interference; no clamp/lead closure. Search boundary y=-300 is not a physical limit or available independent service length.'}
 result['connector']=connector_probe(a.fakra_step)
 result['ring_geometric_comparisons']=[ring_math(R,D) for R,D in [(75,3.1),(34.5,3.45),(37,3),(81.6,5.1),(106.5,7.1)]]
 result['segment_model_assumption']='Per-axis independent anti-rotation clamping. Length/angle screening is conditional on this topology, not a universal full-harness limit. Continuous coax with freely rotating low-friction guides requires a different multi-axis torsion/contact model.'
 result['joint_segments']=[dict(joint=j['id'],fixed_body_pre=i,rotating_body_pre=i+1,axis_world=j['axis'],output_origin_world_mm=j['origin_mm'],bore_mm=j['bore_mm'],baseline_angle_deg=j['limit_deg'],required_free_length_at180_mm=1000*max(abs(x) for x in j['limit_deg'])/180,endpoint_route_status='not modelled or released; separate strain relief per joint required') for i,j in enumerate(p['joints'])]
 render_review(a.out,rows,result)
 (a.out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:{x:y for x,y in v.items() if x in ['free_interval_around_output_mm','free_length_mm','lower_limiter','upper_limiter','additional_length_for_this_straight_route_mm']} for k,v in result['probes'].items()},indent=2));print('Connector',result['connector'])
if __name__=='__main__':main()
