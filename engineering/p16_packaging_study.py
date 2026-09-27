#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""P16-PACK-01. Vendor STEP is read from work only and is never exported.
Our envelopes and interface geometry are nominal, not manufacturing release.
"""
from pathlib import Path
import argparse, copy, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
from OCP.gp import gp_Trsf
import gripper_root_support_study as st
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/p16-packaging-study'
P=dict(revision='P16-PACK-01',D=123.,a=26.,phase=68.,offset_u_mm=-18.,
       tip_gap_mm=14.2,base_gap_mm=22.0,cheek_mm=4.,CAD_closed_mm=97.4,catalog_closed_mm=97.,stroke_mm=50.,
       actuator_PN='P16-50-256-12-P',actuator_mass_g=95.,upper_qmax_deg=109.,lower_qmax_deg=122.)
SIGNS=st.SIGNS; B=st.B; C=st.C

def union(ss):
    ss=list(ss);return ss[0].fuse(*ss[1:]) if len(ss)>1 else ss[0]
def rigid(s,R,t):
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=t;g=gp_Trsf();g.SetValues(*T[:3,:].ravel().tolist());return s.moved(cq.Location(g))
def kin(q,offset=-18.,outward=True):
    a=math.radians(q-P['phase']);A=np.array([0.,offset,-P['D']]);Bv=np.array([P['a']*math.cos(a),offset,P['a']*math.sin(a)])
    L=np.linalg.norm(Bv-A);w=(Bv-A)/L
    R=np.column_stack([[-w[2],0,w[0]],[0,-1.,0],w])
    if not outward:R[:,:2]*=-1
    assert abs(np.linalg.det(R)-1)<1e-12
    return A,Bv,L,R

def envelope_native(L):
    # Relative to base pin, z along rod. The outer tube is square, NOT a Ø12 cylinder.
    return dict(case=B(-25.6,10.6,-10.1,10.1,-4.6,75.3),
        guide=B(-6.1,6.1,-6.1,6.1,23.3,92.5),
        slider=C(4.6,65.2,(0,0,L-69.1),(0,0,1)),
        tip=B(-4.6,4.6,-4.6,4.6,L-10.1,L+4.1))
def envelopes(q,offset=-18.):
    A,_,L,R=kin(q,offset);return {k:rigid(s,R,A) for k,s in envelope_native(L).items()}
def vendor(vdir):
    ss=cq.importers.importStep(str(vdir/'p16_50mm_in.stp')).val().Solids()
    out=cq.importers.importStep(str(vdir/'p16_50mm_out.stp')).val().Solids()
    assert len(ss)==11 and len(out)==12 and all(s.isValid() for s in ss+out)
    # The extended CAD contains an extra fixed connector omitted in the closed file.
    fixed=ss[:9]+[out[11]];moving=ss[9:11]
    return fixed,moving,ss,out

def vendor_at(fixed,moving,q,offset=-18.):
    A,_,L,R=kin(q,offset);tr=A-R@np.array([-10.5,0,-4.5])
    return st.comp([rigid(s,R,tr) for s in fixed]+[rigid(s.translate((0,0,L-97.4)),R,tr) for s in moving])

def clevis_arm(y):
    x,z=P['a']*math.cos(math.radians(68)),-P['a']*math.sin(math.radians(68))
    pl=cq.Plane(origin=(0,y,0),xDir=(1,0,0),normal=(0,-1,0))
    poly=[(x-5,z),(x-4,z-4),(x+4,z-4),(16,-8),(16,-2),(10,-2),(x-5,z+2)]
    return cq.Workplane(pl).polyline(poly).close().extrude(4).val().fuse(C(5,4,(x,y,z),(0,-1,0)))

def pin_stack(x,z,gap,lug,shoulder,tag):
    # Ø4 shoulder traverses BOTH Ø4.1 cheek bores; M3 thread is outside both supports.
    off=P['offset_u_mm'];h=gap/2;t=P['cheek_mm'];p={};ustart=off-h-t;uend=ustart+shoulder
    assert uend>=off+h+t-1e-9
    p[tag+'_SBSM_pin']=C(2,shoulder,(x,ustart,z),(0,1,0)).fuse(C(3.5,3,(x,ustart-3,z),(0,1,0))).fuse(C(1.5,7,(x,uend,z),(0,1,0)))
    external=uend-(off+h+t)
    if external>1e-8:p[tag+'_outer_stack_spacer']=C(3.5,external,(x,off+h+t,z),(0,1,0),4.1)
    p[tag+'_M3_retention_washer']=C(3.5,.5,(x,uend,z),(0,1,0),3.2)
    plane=cq.Plane(origin=(x,uend+.5,z),xDir=(1,0,0),normal=(0,1,0))
    nut=cq.Workplane(plane).polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val()
    p[tag+'_M3_retention_nut']=nut.cut(C(1.5,2.6,(x,uend+.4,z),(0,1,0)))
    sl=(gap-lug-.2)/2-.02
    for sign in [-1,1]:
        yy=off-lug/2-.02-sl if sign<0 else off+lug/2+.02
        p[f'{tag}_lug_spacer_{sign}']=C(2.75 if tag=='tip' else 3,sl,(x,yy,z),(0,1,0),4.1)
    return p

def root_parts(f):
    p,mat=st.root_parts(f);L,W=f['length_mm'],f['width_mm'];cx,cz=P['a']*math.cos(math.radians(68)),-P['a']*math.sin(math.radians(68));off=P['offset_u_mm'];gap=P['tip_gap_mm']
    # Retain root x<=25; take CONTACT02 distal silhouette and pads without altering its source.
    tongue=p['metal_blade_with_narrow_tongue'].intersect(B(14,25,-100,100,-1,7))
    body=cq.Workplane('XY').polyline([(0,-W*.27),(L*.18,-W*.5),(L,-7),(L,7),(L*.18,W*.5),(0,W*.27)]).close().extrude(6).val()
    p['metal_blade_with_narrow_tongue']=body.intersect(B(25,200,-100,100,-1,7)).fuse(tongue)
    p['LED_window_placeholder']=p['LED_window_placeholder'].intersect(B(25,L-22,-100,100,5,8))
    for k in [k for k in p if k.startswith('original_wedge')]:del p[k];del mat[k]
    slope=1/math.tan(math.radians(f['pad_target_q_deg']));s=L-9
    for i,y in enumerate([-3.5,3.5]):
        plane=cq.Plane(origin=(0,y+2.5,0),xDir=(1,0,0),normal=(0,-1,0))
        p[f'contact02_pad_{i}']=cq.Workplane(plane).polyline([(s-9,6),(s+9,6),(s+9,11+9*slope),(s-9,11-9*slope)]).close().extrude(5).val();mat[f'contact02_pad_{i}']='optical_placeholder'
    near=clevis_arm(off+gap/2+4).cut(C(2.05,5,(cx,off+gap/2-.5,cz),(0,1,0)))
    far=clevis_arm(off-gap/2).cut(C(2.05,5,(cx,off-gap/2-4.5,cz),(0,1,0)))
    bridge=B(10,16,off-gap/2-4,-5,-8,-2)
    p['keyed_hub_lower_fork']=union([p['keyed_hub_lower_fork'],near,far,bridge])
    pins=pin_stack(cx,cz,gap,6.,25.,'tip');p.update(pins);mat.update({k:'steel' for k in pins})
    assert len(p['keyed_hub_lower_fork'].Solids())==1
    return p,mat,dict(crank_near_cheek=near,crank_far_cheek=far,crank_bridge=bridge)

def base_parts():
    off=P['offset_u_mm'];gap=P['base_gap_mm'];h=gap/2;p={}
    for side,y in [('near',off+h),('far',off-h-4)]:
        shape=C(7,4,(0,y,-123),(0,1,0)).fuse(B(-7,7,y,y+4,-139,-123))
        shape=shape.cut(C(2.05,4.2,(0,y-.1,-123),(0,1,0)))
        p[side+'_base_cheek']=shape
    plate=B(-15,15,off-h-4,off+h+4,-144,-139)
    for x in [-10,10]:plate=plate.cut(C(2.2,6,(x,off,-144.5),(0,0,1)))
    p['base_bracket']=union([plate,*p.values()]);del p['near_base_cheek'];del p['far_base_cheek']
    p.update(pin_stack(0,-123,gap,8.,30.,'base'))
    return p

def cartridge_parts():
    # Separate support02 output cartridge only, transformed into the local root frame.
    p={}
    for name,u0,u1,r,bore in [('shaft_shoulder',34,36,8.65,0),('bearing_journal',12,34,6,0),('thread_bay',6,12,6,0),
            ('rear_spacer',12,14,8.65,12),('MB1',11,12,12.5,12),('KM1',7,11,11,12),
            ('bearing_A',24,34,16,12),('bearing_B',14,24,16,12),('housing',14,34,20,32),
            ('housing_front_lip',34,35.5,20,27.5),('housing_rear_cap',12,14,20,28)]:
        p['output_'+name]=C(r,u1-u0,(0,u0,0),(0,1,0),bore)
    return p

def pts(s):
    # Conservative AABB corners; simple cylindrical corners intentionally over-bound the circles.
    return np.array(list(itertools.product(*zip(*st.bb(s)))))
def radius(s):return max(math.hypot(x,z) for x,y,z in pts(s))

def certificate(shape1,shape2,velocity,hi,step=2,min_step=.125):
    """Rigorous Hausdorff speed-bound reduction of distance on continuous q intervals."""
    cache={};ok=[];fails=[]
    def at(q):
        if q not in cache:
            a,b=shape1(q),shape2(q);cache[q]=float(a.distance(b))
        return cache[q]
    todo=[(float(a),float(min(a+step,hi))) for a in np.arange(0,hi,step)]
    while todo:
        a,b=todo.pop();da,db=at(a),at(b);bound=min(da,db)-velocity*math.radians(b-a)/2
        if bound>1e-5:ok.append(bound);continue
        if b-a<=min_step or min(da,db)<1e-7:
            fails.append(dict(interval_deg=[a,b],endpoint_distances_mm=[da,db],bound_mm=bound));continue
        m=(a+b)/2;todo.extend([(a,m),(m,b)])
    q=min(cache,key=cache.get)
    return dict(certified=not fails,range_deg=[0,hi],velocity_bound_mm_per_rad=velocity,sample_count=len(cache),minimum_sample_mm=cache[q],minimum_sample_q=q,continuous_lower_bound_mm=min(ok) if ok else None,failures=fails)

def allproof(f,root,crank,base,cart):
    # beta' <= a(D+a)/Lmin²; every envelope point speed <= a + Rmax*beta'.
    Lmin=kin(0)[2];beta=P['a']*(P['D']+P['a'])/Lmin**2;Vact=26+160*beta
    hi=f['closure_study_deg'];rot=lambda s,q:s.rotate((0,0,0),(0,1,0),-q)
    old={k:v for k,v in root.items() if not k.startswith('tip_')}
    # Replace joined hub with pre-crank geometry for partitioned checks.
    old['keyed_hub_lower_fork']=st.root_parts(f)[0]['keyed_hub_lower_fork']
    oldcomp=st.comp(old.values());r=radius(oldcomp);checks={}
    checks['actuator_vs_existing_root_and_contact02']=certificate(lambda q:st.comp(envelopes(q).values()),lambda q:rot(oldcomp,q),Vact+r,hi,step=2)
    checks['case_vs_crank']=certificate(lambda q:envelopes(q)['case'],lambda q:rot(st.comp(crank.values()),q),Vact+radius(st.comp(crank.values())),hi)
    # Tube and moving end are separated from cheek inner faces by their constant u slabs.
    checks['guide_vs_cheeks']=dict(certified=True,continuous_lower_bound_mm=P['tip_gap_mm']/2-6.1,method='constant u slabs throughout 0..qmax')
    checks['slider_tip_vs_cheeks']=dict(certified=True,continuous_lower_bound_mm=P['tip_gap_mm']/2-4.6,method='constant u slabs throughout 0..qmax')
    checks['guide_slider_tip_vs_crank_bridge']=certificate(lambda q:st.comp([v for k,v in envelopes(q).items() if k!='case']),lambda q:rot(crank['crank_bridge'],q),Vact+radius(crank['crank_bridge']),hi)
    # Base cheek inner gap exceeds even the broad case width; base bridge is below the entire actuator.
    checks['actuator_vs_base_cheeks']=dict(certified=True,continuous_lower_bound_mm=P['base_gap_mm']/2-10.1,method='constant u slabs; pins/lug spacers are intentional interfaces')
    bridge=B(-15,15,-18-P['base_gap_mm']/2-4,-18+P['base_gap_mm']/2+4,-144,-139)
    checks['actuator_vs_base_bridge']=certificate(lambda q:st.comp(envelopes(q).values()),lambda q:bridge,Vact,hi)
    # Shaft, spacer and the thread-bay end intentionally meet at u=6; omit that bay.
    moving=st.comp(root.values());fixed=st.comp([s for k,s in cart.items() if k!='output_thread_bay'])
    checks['root_crank_pins_vs_output_cartridge']=certificate(lambda q:rot(moving,q),lambda q:fixed,radius(moving),hi,step=.5)
    checks['moving_vs_base_bracket']=certificate(lambda q:rot(moving,q),lambda q:st.comp(base.values()),radius(moving),hi)
    return checks,dict(beta_derivative_bound=beta,actuator_point_speed_bound_mm_per_rad=Vact)

def four_way(fingers,roots,bases,carts):
    # Per-axis bounding coordinate samples + Lipschitz margin gives independent-angle pair certificates.
    ranges=[];states={};full_points=[];drive_points=[]
    for i,f in enumerate(fingers):
        root=roots[i];qmax=f['closure_study_deg'];xyz=[];drive=[];speed=max(radius(st.comp(root.values())),89.)
        for q in np.arange(0,qmax+1,1.):
            moving=[st.place(s,f,SIGNS[i],float(q)) for s in root.values()]
            static=[st.place(s,f,SIGNS[i]) for s in list(bases.values())+list(carts.values())]
            acts=[st.place(s,f,SIGNS[i]) for s in envelopes(float(q)).values()]
            xyz.extend(np.concatenate([pts(s) for s in moving+static+acts]))
            # Exclude distal metal, windows and pads to report the drive head only.
            drive_moving=[st.place(s,f,SIGNS[i],float(q)) for k,s in root.items() if k!='metal_blade_with_narrow_tongue' and k!='LED_window_placeholder' and not k.startswith('contact02_pad')]
            drive.extend(np.concatenate([pts(s) for s in drive_moving+static+acts]))
        # AABB corners bound individual shapes; continuous motion requires a further speed margin.
        margin=speed*math.radians(.5);xyz=np.array(xyz);drive=np.array(drive);lo=xyz.min(0)-margin;hi=xyz.max(0)+margin
        ranges.append(dict(finger=f['id'],min_mm=lo.tolist(),max_mm=hi.tolist(),sample_step_deg=1,half_interval_margin_mm=margin,point_speed_bound_mm_per_rad=speed))
        full_points.extend([lo,hi]);drive_points.extend(drive)
    pairs=[]
    for a,b in itertools.combinations(ranges,2):
        lo,hi=np.array(a['min_mm']),np.array(a['max_mm']);ll,hh=np.array(b['min_mm']),np.array(b['max_mm'])
        sep=np.maximum(ll-hi,lo-hh);axis=int(np.argmax(sep));pairs.append(dict(a=a['finger'],b=b['finger'],axis='xyz'[axis],continuous_independent_gap_bound_mm=float(sep[axis]),certified=bool(sep[axis]>0)))
    dr=np.array(drive_points);margin=max(r['half_interval_margin_mm'] for r in ranges)
    return dict(module_ranges=ranges,pairs=pairs,all_independent_pairs_certified=all(r['certified'] for r in pairs),
        drive_envelope=dict(conservative_coaxial_diameter_mm=float(2*(np.linalg.norm(dr[:,:2],axis=1).max()+margin)),zmin_mm=float(dr[:,2].min()-margin),zmax_mm=float(dr[:,2].max()+margin),method='world AABB corners for each part at 1deg plus global speed margin; excludes distal blade/light/pads, enclosure and cable bend volumes'))

def stress():
    out=[]
    for F in [123.107854960616,218.785851158771,300.,500.]:
        a,b,load=19.,29.,-18.;RA=F*(b-load)/(b-a);RB=F*(load-a)/(b-a)
        assert abs(RA+RB-F)<1e-9 and abs(RA*a+RB*b-F*load)<1e-8
        row=dict(F_N=F,offset_only_bending_Nm=F*.018,near_bearing_reaction_N=RA,far_bearing_reaction_N=RB,added_pair_reaction_due_to_offset_N=F*18/10,
                 note='500N static/backdrive boundary sensitivity only, not a commanded load')
        row['crank_bridge_nominal_square_6mm_bending_upper_MPa']=math.sqrt(2)*F*13/(6*6**2/6)
        row['annular_D10_d4_at_u6_nominal_bending_MPa']=32*(F*24)*10/(math.pi*(10**4-4**4))
        row['max_linkage_torque_Nm']=F*.026
        row['annular_D10_d4_nominal_torsion_MPa']=16*(F*26)*10/(math.pi*(10**4-4**4))
        row['pin_screens']=[]
        for role,gap,lug in [('tip',P['tip_gap_mm'],6),('base',P['base_gap_mm'],8)]:
            span=gap+4;M=F*span/4-F*lug/8
            row['pin_screens'].append(dict(role=role,support_center_span_mm=span,bending_moment_Nmm=M,nominal_bending_MPa=32*M/(math.pi*4**3),double_shear_MPa=F/(2*math.pi*4**2/4),plastic_hole_bearing_MPa=F/(4*lug)))
        out.append(row)
    return dict(cases=out,bearing_geometric_centers_u_mm=[19,29],load_plane_u_mm=-18,limits='Radial-plane actuator force only; vector superposition with finger/contact/gravity and real pressure centers still required. These signed reactions are not equivalent dynamic P, life, stiffness, preload or static safety certification. Pins use ideal simple supports/uniform plastic contact; shoulder transition, fit, creep and fatigue unqualified.')

def export_assembly(path,fingers,roots,base,cart,closed=False):
    ass=cq.Assembly(name=path.stem);rows=[]
    for i,f in enumerate(fingers):
        q=f['closure_study_deg'] if closed else 0.
        for k,s in roots[i].items():
            sh=st.place(s,f,SIGNS[i],q);col=(.25,.36,.40) if 'metal_blade' in k else ((1,.68,.18) if 'LED' in k else ((.25,.58,.51) if 'pad' in k else (.58,.64,.65)))
            ass.add(sh,name=f['id']+'_'+k,color=cq.Color(*col));rows.append((f['id']+'_'+k,sh))
        for k,s in {**base,**cart,**{('P16_nominal_'+k):v for k,v in envelopes(q).items()}}.items():
            sh=st.place(s,f,SIGNS[i]);ass.add(sh,name=f['id']+'_'+k,color=cq.Color(*((.17,.2,.22) if 'P16' in k else (.5,.58,.62))));rows.append((f['id']+'_'+k,sh))
    ass.save(str(path));rt=cq.importers.importStep(str(path)).val()
    return dict(path=path.name,valid=rt.isValid(),roundtrip_solids=len(rt.Solids()),parts=len(rows)),rows

def plot(rows,path):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(13,7));ax=fig.add_subplot(121,projection='3d');aa=fig.add_subplot(122)
    polygons=[];colors=[]
    for n,s in rows:
        vv,ff=s.tessellate(.45);v=np.array([x.toTuple() for x in vv]);f=np.array(ff);col= '#e6ab39' if 'LED' in n else ('#2e887e' if 'pad' in n else ('#34434d' if 'P16' in n else '#8fa3ac'))
        polygons.extend(v[f]);colors.extend([col]*len(f))
        if n.startswith('UR_'):
            from scipy.spatial import ConvexHull
            phi=math.radians(35);rr=v[:,0]*math.cos(phi)+v[:,1]*math.sin(phi)-70
            pp=np.c_[rr,v[:,2]]
            if np.ptp(pp[:,0])>1e-5 and np.ptp(pp[:,1])>1e-5:
                hull=ConvexHull(pp);aa.fill(pp[hull.vertices,0],pp[hull.vertices,1],color=col,alpha=.75,edgecolor='#40515b',linewidth=.25)
    ax.add_collection3d(Poly3DCollection(polygons,facecolors=colors,edgecolors='none',alpha=1))
    ax.set(xlim=(-210,210),ylim=(-170,170),zlim=(-150,220),xlabel='Head x / mm',ylabel='Head y / mm',zlabel='Head z / mm');ax.set_box_aspect((420,340,370));ax.view_init(22,-63)
    aa.set(aspect='equal',xlim=(-32,48),ylim=(-150,35),xlabel='UR radial offset / mm',ylabel='Head z / mm',title='Single module / support and crank');aa.axhline(-130,c='#b54a43',ls='--',lw=1);aa.text(0,-128,'Old mounting plane -130',fontsize=8,color='#b54a43');aa.grid(alpha=.25)
    fig.suptitle('P16-PACK-01 / independent packaging candidate\nVendor CAD checked separately; displayed bodies are original conservative envelopes')
    fig.tight_layout();fig.savefig(path,dpi=150);plt.close(fig)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--vendor-dir',type=Path,default=ROOT.parents[1]/'work/p16-reference');ap.add_argument('--skip-vendor',action='store_true');ap.add_argument('--skip-motion',action='store_true');args=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);pp=ROOT/'engineering/parameters/r4-layout.json';assert hashlib.sha256(pp.read_bytes()).hexdigest()==st.EXPECTED
    contact=json.loads((ROOT/'engineering/generated/contact02-study/study.json').read_text());fingers=contact['fingers'];base=base_parts();cart=cartridge_parts();roots=[];materials=[];cranks=[]
    for f in fingers:
        p,m,c=root_parts(f);roots.append(p);materials.append(m);cranks.append(c)
        assert all(s.isValid() and len(s.Solids())==1 for s in p.values())
    internal=[]
    for label,pparts in [('upper_root',roots[0]),('lower_root',roots[2]),('base',base),('cartridge',cart)]:
        hits=[];count=0
        for (ka,sa),(kb,sb) in itertools.combinations(pparts.items(),2):
            if st.gap_bounds(st.bb(sa),st.bb(sb))>1e-5:continue
            vol=sa.intersect(sb).Volume();count+=1
            if vol>1e-5:hits.append(dict(a=ka,b=kb,intersection_mm3=vol))
        internal.append(dict(assembly=label,boolean_tests=count,intersections=hits,passes=not hits))
    assert all(x['passes'] for x in internal)
    result=dict(internal_rigid_assembly_checks=internal,parameters=P,baseline_sha256=st.EXPECTED,contact02_sha256=hashlib.sha256((ROOT/'engineering/generated/contact02-study/study.json').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),manufacturing_release=False)
    if not args.skip_vendor:
        fix,mov,ins,outs=vendor(args.vendor_dir);env=union(envelope_native(97.4).values());contain=[]
        for k,s in enumerate(fix+mov):
            native=s.translate((10.5,0,4.5));outside=native.cut(env).Volume();contain.append(dict(solid=k,outside_volume_mm3=outside,passes=outside<1e-5))
        result['vendor_containment']=contain;assert all(r['passes'] for r in contain)
        holes=[]
        for label,solids in [('closed',ins),('extended',outs)]:
            axes=[]
            for so in solids:
                for fa in so.Faces():
                    if fa.geomType()!='CYLINDER':continue
                    cy=fa._geomAdaptor().Cylinder();di=cy.Axis().Direction();loc=cy.Location()
                    if abs(cy.Radius()-2.125)<1e-6 and abs(di.Y())>.999:
                        point=[round(loc.X(),6),round(loc.Z(),6)]
                        if point not in axes:axes.append(point)
            axes.sort(key=lambda p:p[1]);assert len(axes)==2
            holes.append(dict(state=label,pin_axis_xz_native_mm=axes,pin_distance_mm=axes[1][1]-axes[0][1]))
        assert abs(holes[0]['pin_distance_mm']-97.4)<1e-7 and abs(holes[1]['pin_distance_mm']-147.4)<1e-7
        result['CAD_pin_measurements']=holes
        result['CAD_stroke_margins_mm']=[kin(0)[2]-97.4,147.4-kin(122)[2]]
        result['vendor_solids']=[11,12];result['vendor_files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.vendor_dir.glob('*') if p.suffix.lower() in ['.pdf','.stp','.zip']}
        nativechecks=[]
        # Check actual body versus metal root and crank; pin/spacer surfaces are expected contacts.
        for i in [0,2]:
            f=fingers[i];target=st.comp([s for k,s in roots[i].items() if not k.startswith('tip_')])
            for q in [0.,30.,60.,90.,f['closure_study_deg']]:
                act=vendor_at(fix,mov,q);rr=target.rotate((0,0,0),(0,1,0),-q);d=act.distance(rr)
                nativechecks.append(dict(finger=f['id'],q_deg=q,root_distance_mm=d,root_intersection_mm3=act.intersect(rr).Volume() if d<1e-7 else 0))
            # Pin/hole and washer/lug fit checked separately, not silently excluded as collisions.
            for q in [0.,f['closure_study_deg']]:
                act=vendor_at(fix,mov,q)
                for k,s in {**{k:s.rotate((0,0,0),(0,1,0),-q) for k,s in roots[i].items() if k.startswith('tip_')},**base}.items():
                    vol=sum(v.intersect(s).Volume() for v in act.Solids())
                    nativechecks.append(dict(finger=f['id'],q_deg=q,interface=k,intersection_mm3=vol,passes=vol<1e-5))
        result['native_CAD_interface_samples']=nativechecks
        assert all(x.get('passes',True) and x.get('root_intersection_mm3',0)<1e-5 for x in nativechecks)
        old=st.root_parts(json.loads(pp.read_text())['head']['fingers'][2])[0];old=st.comp([v for k,v in old.items() if k not in ['metal_blade_with_narrow_tongue','LED_window_placeholder'] and not k.startswith('original_wedge')])
        act=vendor_at(fix,mov,122,offset=0);rr=old.rotate((0,0,0),(0,1,0),-122)
        result['coplanar_counterexample']=dict(q_deg=122,intersection_mm3=sum(s.intersect(rr).Volume() for s in act.Solids()),scope='original root mechanical parts without distal blade')
        print('Vendor checks',len(nativechecks),'containment',all(r['passes'] for r in contain),flush=True)
    if not args.skip_motion:
        result['own_module_continuous_checks']={}
        for i in [0,2]:
            checks,bounds=allproof(fingers[i],roots[i],cranks[i],base,cart);result['own_module_continuous_checks'][fingers[i]['id']]=checks;result['speed_bound_derivation']=bounds
            (OUT/'study-partial.json').write_text(json.dumps(result,indent=2)+'\n');print('Own module',fingers[i]['id'],{k:v['certified'] for k,v in checks.items()},flush=True)
    result['four_module_motion']=four_way(fingers,roots,base,cart);result['load_screen']=stress()
    assert result['four_module_motion']['all_independent_pairs_certified']
    # Catalog masses for bought parts, volume*density for our own metal. P16 COM remains uncertain.
    mass=[]
    for i,f in enumerate(fingers):
        for k,s in roots[i].items():
            if materials[i][k]=='optical_placeholder':continue
            m=3.5 if k=='tip_SBSM_pin' else s.Volume()*st.DENSITY[materials[i][k]]
            mass.append(dict(part=f['id']+'_'+k,mass_g=m,head_center_mm=list(st.place(s,f,SIGNS[i]).Center().toTuple()),method='NBK catalog' if k=='tip_SBSM_pin' else 'nominal volume*density'))
        for k,s in {**base,**cart}.items():
            m=36. if k in ['output_bearing_A','output_bearing_B'] else (4. if k=='base_SBSM_pin' else s.Volume()*(.0027 if k=='base_bracket' or 'housing' in k else .00785))
            mass.append(dict(part=f['id']+'_'+k,mass_g=m,head_center_mm=list(st.place(s,f,SIGNS[i]).Center().toTuple()),method='catalog 7201/shoulder pin' if k in ['output_bearing_A','output_bearing_B','base_SBSM_pin'] else 'nominal volume*density; rings modeled simply'))
        ac=st.comp(envelopes(0).values());mass.append(dict(part=f['id']+'_P16',mass_g=95.,head_center_mm=list(st.place(ac,f,SIGNS[i]).Center().toTuple()),method='catalog mass; envelope uniform-volume centroid PROXY only, not vendor internal COM'))
    total=sum(x['mass_g'] for x in mass);com=sum(x['mass_g']*np.array(x['head_center_mm']) for x in mass)/total
    result['mass']=dict(modeled_metal_actuators_bearings_g=total,home_COM_proxy_head_mm=com.tolist(),rows=mass,exclusions='optics/cameras, real lamps/PCBs, pad retainers/material, ground carrier and its screws, armor, cable/strain relief and external control; actuator internal mass distribution unknown')
    qa,rows=export_assembly(OUT/'P16-PACK-01-open.step',fingers,roots,base,cart);qb,_=export_assembly(OUT/'P16-PACK-01-closed.step',fingers,roots,base,cart,True);result['export_QA']=[qa,qb]
    for k in ['keyed_hub_lower_fork','metal_blade_with_narrow_tongue']:
        cq.exporters.export(roots[0][k],str(OUT/(k+'.step')))
    cq.exporters.export(base['base_bracket'],str(OUT/'base_bracket.step'))
    result['checks']=dict(baseline_unchanged=hashlib.sha256(pp.read_bytes()).hexdigest()==st.EXPECTED,all_export_valid=qa['valid'] and qb['valid'],vendor_checked=not args.skip_vendor,motion_checked=not args.skip_motion)
    (OUT/'study.json').write_text(json.dumps(result,indent=2)+'\n');plot(rows,OUT/'packaging-open.png')
    partial=OUT/'study-partial.json'
    if partial.exists():partial.unlink()
    print(json.dumps(dict(mass=result['mass']['modeled_metal_actuators_bearings_g'],COM=com.tolist(),four=result['four_module_motion']),indent=2),flush=True)
if __name__=='__main__':main()
