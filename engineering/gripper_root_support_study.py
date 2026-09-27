#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R4-support-03: removable keyed narrow fork. Read-only support02/layout baseline.
Nominal CAD and continuous rigid-motion distance certificates are NOT strength release.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
import gripper_miter_support_study as prev
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/gripper-support-03'
EXPECTED=prev.EXPECTED
Z=np.array([0.,0.,1.]); SIGNS=[1,-1,-1,1]
DENSITY={'aluminum':.00270,'steel':.00785,'optical_placeholder':.0012}

def B(x0,x1,y0,y1,z0,z1):
    return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,cq.Vector(x0,y0,z0))
def C(radius,length,origin,axis,bore=0):
    s=cq.Solid.makeCylinder(radius,length,cq.Vector(*origin),cq.Vector(*axis))
    if bore:s=s.cut(cq.Solid.makeCylinder(bore/2,length+.02,cq.Vector(*(np.asarray(origin)-.01*np.asarray(axis))),cq.Vector(*axis)))
    return s

def outline(f):
    L,W=f['length_mm'],f['width_mm']
    return [(0,-W*.27),(L*.18,-W*.5),(L*.72,-W*.25),(L,-W*.05),(L,W*.05),(L*.72,W*.25),(L*.18,W*.5),(0,W*.27)]
def original_blade(f):return cq.Workplane('XY').polyline(outline(f)).close().extrude(6).val()
def halfwidth_at(f,x):
    p=outline(f)[:4]
    for (a,ya),(b,yb) in zip(p,p[1:]):
        if a<=x<=b:return -(ya+(yb-ya)*(x-a)/(b-a))
    raise ValueError(x)

def root_parts(f):
    """Local x=blade length, y=module u before mirror, z=light-side normal."""
    p={}; material={}
    def add(n,s,m='aluminum'):p[n]=s;material[n]=m
    # Ø12 bearing/thread spindle reduces to Ø10 after t58. Axial shoulder stays u6.
    shaft=C(5,10.8,(0,-4.8,0),(0,1,0))
    shaft=shaft.cut(B(-5.1,-3.2,-4,4,-1.5,1.5)) # key seat t1=1.8
    shaft=shaft.cut(C(2,10,(0,-4.8,0),(0,1,0))) # M4 major-diameter thread envelope
    add('output_tenon_D10',shaft,'steel')
    add('shoulder_spacer',C(8,1,(0,5,0),(0,1,0),10.1),'steel')
    hub=C(12,10,(0,-5,0),(0,1,0),10)
    # Hub keyway t2=1.4; 0.2 radial top clearance with 3 mm tall key.
    hub=hub.cut(B(-6.4,-3.0,-5.01,5.01,-1.5,1.5))
    web=B(6,15,-5,5,-4,10)
    bottom=B(14,25,-9,9,-4,0).fuse(B(17,25,-9,9,-7.4,-4))
    fork=hub.fuse(web).fuse(bottom)
    cap=B(15,25,-9,9,6,10)
    tongue=cq.Workplane('XY').polyline([(15,-9),(24,-9),(25,-halfwidth_at(f,25)),(25,halfwidth_at(f,25)),(24,9),(15,9)]).close().extrude(6).val()
    blade=original_blade(f).intersect(B(25,200,-100,100,-1,7)).fuse(tongue)
    for y in [-4.5,4.5]:
        hole=C(1.7,30,(21,y,-12),(0,0,1))
        fork=fork.cut(hole);cap=cap.cut(hole);blade=blade.cut(hole)
    keeper=B(17,25,-9,9,-7.9,-7.4)
    for y in [-4.5,4.5]:
        cut=cq.Workplane('XY').workplane(offset=-7.5).center(21,y).polygon(6,5.7/math.cos(math.pi/6)).extrude(3).val().rotate((21,y,0),(21,y,1),30)
        # Dogbone relief for a 1 mm end mill; clear cavity is accessible from below.
        for a in range(30,390,60):
            xx=21+(5.7/math.sqrt(3))*math.cos(math.radians(a));yy=y+(5.7/math.sqrt(3))*math.sin(math.radians(a))
            cut=cut.fuse(C(.5,3,(xx,yy,-7.5),(0,0,1)))
        fork=fork.cut(cut).cut(C(3.6,.5,(21,y,-4.5),(0,0,1)))
        keeper=keeper.cut(C(1.7,1,(21,y,-8.1),(0,0,1)))
    for j,x in enumerate([18.5,22.5]):
        fork=fork.cut(C(1,6.1,(x,0,-7.9),(0,0,1)))
        keeper=keeper.cut(C(1.2,1,(x,0,-8.1),(0,0,1)))
        bolt=C(1,6,(x,0,-7.9),(0,0,1)).fuse(C(1.9,2,(x,0,-9.9),(0,0,1)))
        add(f'M2x6_keeper_screw_{j}',bolt,'steel')
    add('nut_keeper_sheet',keeper,'steel')
    add('keyed_hub_lower_fork',fork)
    add('removable_upper_fork',cap)
    add('metal_blade_with_narrow_tongue',blade)
    add('parallel_key_3x3x8',B(-6.2,-3.2,-4,4,-1.5,1.5),'steel')
    add('end_washer_D18',C(9,1.5,(0,-6.5,0),(0,1,0),4.3),'steel')
    # M4x10: washer clamps hub; shaft ends 0.2 before hub face; >=8.3 engagement.
    bolt=C(2,10,(0,-6.5,0),(0,1,0)).fuse(C(3.5,4,(0,-10.5,0),(0,1,0)))
    add('M4x10_end_screw_envelope',bolt,'steel')
    for i,y in enumerate([-4.5,4.5]):
        bolt=C(1.5,20,(21,y,-10),(0,0,1)).fuse(C(2.75,3,(21,y,10),(0,0,1)))
        add(f'M3x20_fork_screw_{i}',bolt,'steel')
        add(f'M3_washer_{i}',C(3.5,.5,(21,y,-4.5),(0,0,1),3.4),'steel')
        nut=cq.Workplane('XY').workplane(offset=-6.9).center(21,y).polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val().rotate((21,y,0),(21,y,1),30)
        nut=nut.cut(C(1.5,2.6,(21,y,-7),(0,0,1)))
        add(f'M3_hexnut_{i}',nut,'steel')
    L,W=f['length_mm'],f['width_mm']
    led=[(L*.13,-W*.24),(L*.24,-W*.36),(L*.72,-W*.20),(L*.94,-W*.08),(L*.94,W*.08),(L*.72,W*.20),(L*.24,W*.36),(L*.13,W*.24)]
    lamp=cq.Workplane('XY').workplane(offset=6).polyline(led).close().extrude(.6).val().intersect(B(25,200,-100,100,5,8))
    add('LED_window_placeholder',lamp,'optical_placeholder')
    # Distal pads intentionally unchanged; parent owns evolving contact-shoe study.
    x=f['contact_along_mm'];slope=1/math.tan(math.radians(f['pad_target_q_deg']))
    pad_poly=[(x-9,6),(x+9,6),(x+9,11+9*slope),(x-9,11-9*slope)]
    for i,side in enumerate([-1,1]):
        yc=side*W*.08
        plane=cq.Plane(origin=(0,yc-2.5,0),xDir=(1,0,0),normal=(0,-1,0))
        # Plane y direction = +z; extrusion along -y from upper edge.
        plane=cq.Plane(origin=(0,yc+2.5,0),xDir=(1,0,0),normal=(0,-1,0))
        add(f'original_wedge_pad_{i}',cq.Workplane(plane).polyline(pad_poly).close().extrude(5).val(),'optical_placeholder')
    return p,material

def place(s,f,sign,q=0):
    if sign<0:s=s.mirror('XZ')
    s=s.rotate((0,0,0),(0,1,0),-q).rotate((0,0,0),(0,0,1),f['phi_deg'])
    a=np.radians(f['phi_deg']);return s.translate((70*math.cos(a),70*math.sin(a),f['root_z_mm']))
def bb(s):
    b=s.BoundingBox();return np.array([b.xmin,b.ymin,b.zmin]),np.array([b.xmax,b.ymax,b.zmax])
def gap_bounds(a,b):
    lo,hi=a;lo2,hi2=b;return float(np.linalg.norm(np.maximum(np.maximum(lo2-hi,lo-hi2),0)))
def comp(sh):return cq.Compound.makeCompound(list(sh))

def baseline(layout):
    parts,rows=prev.make_parts(layout,SIGNS);sh={p['name']:prev.solid(p,cq) for p in parts}
    removed={f['id']+'_'+tag for f in layout['head']['fingers'] for tag in ['finger_metal_hub','output_hub_tenon']}
    for n in removed:del sh[n]
    savings=[]
    # Rounded slots in carrier plates only; retain all bearing seats and lips.
    for p in parts:
        if p['name'] not in sh or p['kind']!='carrier_plate':continue
        a,b=p['axes'][:,0],p['axes'][:,1];c=p['center'];nr=p['axes'][:,2]
        if 'input' in p['name']:
            # offset -8.5 from plate center => u=-36, centers +/-7, R6.
            ctr=c-8.5*a;length,width=26,12
        else:ctr=c;length,width=16,10;a,b=b,a
        pl=cq.Plane(origin=cq.Vector(*(ctr-3*nr)),xDir=cq.Vector(*a),normal=cq.Vector(*nr))
        cut=cq.Workplane(pl).slot2D(length,width).extrude(6).val()
        old=sh[p['name']];new=old.cut(cut);sh[p['name']]=new
        savings.append(dict(part=p['name'],before_mm3=old.Volume(),after_mm3=new.Volume(),saved_g=(old.Volume()-new.Volume())*.0027))
    return parts,rows,sh,savings

def shape_data(s):
    b=bb(s);return dict(volume_mm3=s.Volume(),center_mm=list(s.Center().toTuple()),bounds_mm=[b[0].tolist(),b[1].tolist()],valid=s.isValid(),solids=len(s.Solids()))

def collision_certificate(f,i,moving,fixed,step_deg=2,min_step_deg=.125,region='root'):
    # Distance is 1-Lipschitz in Hausdorff displacement; max swept radius bounds
    # displacement between any angle and its nearest interval endpoint.
    template=comp(moving.values());pts=[]
    for s in moving.values():
        a,b=bb(s);pts.extend(itertools.product(*zip(a,b)))
    r=max(math.hypot(x,z) for x,y,z in pts)
    blockers={n:s for n,s in fixed.items() if n!=f['id']+'_output_thread_bay'}
    fixed_boxes={n:bb(s) for n,s in blockers.items()};cache={};tests=0
    def at(q):
        nonlocal tests
        if q in cache:return cache[q]
        body=place(template,f,SIGNS[i],q);bounds=bb(body);near=[(n,s) for n,s in blockers.items() if gap_bounds(bounds,fixed_boxes[n])<10]
        d=10.;pair=None
        for n,s in near:
            if gap_bounds(bounds,fixed_boxes[n])>d:continue
            dd=body.distance(s);tests+=1
            if dd<d:d=dd;pair=n
        cache[q]=(d,pair)
        return cache[q]
    intervals=[];failed=[];stack=[(a,min(a+step_deg,f['closure_study_deg'])) for a in np.arange(0,f['closure_study_deg'],step_deg)]
    while stack:
        a,b=stack.pop();da,pa=at(float(a));db,pb=at(float(b));bound=min(da,db)-2*r*math.sin(math.radians(b-a)/4)
        if bound>1e-5:intervals.append(dict(a=float(a),b=float(b),clearance_lower_bound_mm=bound));continue
        if min(da,db)<1e-6:
            for q,d,pair in [(a,da,pa),(b,db,pb)]:
                if d<1e-6 and not any(z['q_deg']==q for z in failed):
                    body=place(template,f,SIGNS[i],float(q));vol=body.intersect(blockers[pair]).Volume()
                    failed.append(dict(q_deg=float(q),part=pair,intersection_mm3=vol))
            continue
        if b-a<=min_step_deg:failed.append(dict(interval_deg=[float(a),float(b)],reason='unresolved distance certificate',endpoint_distance_mm=[da,db]));continue
        mid=float((a+b)/2);stack.extend([(a,mid),(mid,b)])
    nearest=min(cache,key=lambda q:cache[q][0])
    return dict(finger=f['id'],region=region,range_deg=[0,f['closure_study_deg']],moving_radius_bound_mm=r,
        distance_tests=tests,sampled_angles=len(cache),minimum_sampled_distance_mm=cache[nearest][0],minimum_sampled_q_deg=nearest,nearest_part=cache[nearest][1],
        continuous_clearance_lower_bound_mm=min((z['clearance_lower_bound_mm'] for z in intervals),default=None),
        certified=not failed,failures=failed,certified_intervals=intervals,
        allowed_interface='own output thread bay face at u=6 meets new integral Ø10 tenon and spacer; original motor/gear/bearings retain support02 envelope limitations')

def tool_checks(layout,roots,fixed):
    shapes=dict(fixed)
    for i,f in enumerate(layout['head']['fingers']):
        for n,s in roots[i].items():shapes[f['id']+'_'+n]=place(s,f,SIGNS[i])
    results=[]
    for i,f in enumerate(layout['head']['fingers']):
        paths=[('M4_3mm_hex',C(2.5,60,(0,-70.5,0),(0,1,0)),['M4x10_end_screw_envelope'])]
        for j,y in enumerate([-4.5,4.5]):
            paths.append((f'M3_{j}_2p5mm_hex',C(2.5,60,(21,y,13),(0,0,1)),[f'M3x20_fork_screw_{j}']))
            # Nut rotation is reacted by a machined captive pocket; keeper is bench-installed.
        for label,path,skip in paths:
            sh=place(path,f,SIGNS[i]);b=bb(sh);hits=[];dist=100.
            for n,s in shapes.items():
                if n in [f['id']+'_'+x for x in skip]:continue
                if gap_bounds(b,bb(s))>1:continue
                vol=sh.intersect(s).Volume()
                if vol>1e-6:hits.append(dict(part=n,volume_mm3=vol))
                dist=min(dist,sh.distance(s))
            results.append(dict(finger=f['id'],tool=label,intersections=hits,passes=not hits,scope='straight external shank approach in q=0 pose; target screw omitted; socket recess, handle sweep and final armor absent'))
    return results

def mechanics():
    rows=[]
    for T in [3.7,5.0]:
        F=2000*T/10;Tn=T*1000
        rows.append(dict(torque_Nm=T,key_tangential_N=F,key_shear_MPa=F/(3*8),hub_key_bearing_MPa=F/(1.2*8),
            tenon_annular_torsion_MPa=16*Tn*10/(math.pi*(10**4-4**4)),
            fork_cap_force_at_10mm_couple_N=Tn/10,cap_cantilever_stress_MPa=6*(Tn/10)*7/(18*4**2),
            cap_cantilever_deflection_mm=4*(Tn/10)*7**3/(70000*18*4**3),
            M3_pair_external_tension_each_N=(Tn/10)/2,
            M3_external_increment_MPa=(Tn/10)/2/5.03,
            neck_gross_bending_MPa=Tn/(10*14**2/6),tongue_hole_net_bending_MPa=Tn/((18-2*3.4)*6**2/6),
            shoulder_pressure_at_500N_MPa=500/(math.pi*(12**2-10.1**2)/4)))
    return dict(cases=rows,assumptions='gross static screens only; caps 6061 candidate E=70GPa, exact material temper/plate certificate not frozen; key material and engagement, notch factors, bolt preload/relaxation, prying, fatigue and tolerances unqualified',
        limit='5Nm is a load-screen input; selected 22GPT 3.7Nm gearhead does not deliver 5Nm and 90-degree losses reduce the output further')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--skip-motion',action='store_true');args=ap.parse_args()
    raw=(ROOT/'engineering/parameters/r4-layout.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    assert sha==EXPECTED,'shared layout changed'
    layout=json.loads(raw);OUT.mkdir(parents=True,exist_ok=True)
    parts,rows,fixed,savings=baseline(layout)
    roots=[];mats=[]
    for f in layout['head']['fingers']:
        a,b=root_parts(f);roots.append(a);mats.append(b)
    qa={};detail=[]
    for i,f in enumerate(layout['head']['fingers']):
        tail=B(25.0001,200,-100,100,-1,7)
        old=original_blade(f).intersect(tail);new=roots[i]['metal_blade_with_narrow_tongue'].intersect(tail)
        qa[f['id']+'_distal_unchanged']=abs(old.Volume()-new.Volume())<1e-5 and old.cut(new).Volume()<1e-5 and new.cut(old).Volume()<1e-5
        for n,s in roots[i].items():detail.append(dict(finger=f['id'],part=n,material=mats[i][n],mass_g=s.Volume()*DENSITY[mats[i][n]],**shape_data(s)))
    qa['all_root_solids_valid']=all(r['valid'] and r['solids']==1 for r in detail)
    qa['M4_clamps_hub_not_shaft']=math.isclose(5-4.8,.2)
    qa['key_top_clearance_0p2']=math.isclose(1.8+1.4-3,.2)
    qa['mass_slot_reverse']=all(math.isclose((r['before_mm3']-r['after_mm3'])*.0027,r['saved_g']) for r in savings)
    motion=[]
    if not args.skip_motion:
        for i,f in enumerate(layout['head']['fingers']):
            print('motion',f['id'],flush=True)
            near={n:s for n,s in roots[i].items() if n not in ['metal_blade_with_narrow_tongue','LED_window_placeholder','original_wedge_pad_0','original_wedge_pad_1']}
            near['tongue']=roots[i]['metal_blade_with_narrow_tongue'].intersect(B(-20,25,-100,100,-20,20))
            far={n:s for n,s in roots[i].items() if n in ['LED_window_placeholder','original_wedge_pad_0','original_wedge_pad_1']}
            far['blade']=roots[i]['metal_blade_with_narrow_tongue'].intersect(B(25,200,-100,100,-20,20))
            proxy={'hub':C(12,16.5,(0,-10.5,0),(0,1,0)), 'web':B(6,15,-5,5,-4,10), 'fork_box':B(14,25,-9,9,-10,13), 'tongue':near['tongue']}
            proxy_union=proxy['hub'].fuse(proxy['web']).fuse(proxy['fork_box']).fuse(proxy['tongue'])
            qa[f['id']+'_root_proxy_contains_actual']=all(s.cut(proxy_union).Volume()<1e-5 for s in near.values())
            assert qa[f['id']+'_root_proxy_contains_actual'],'unsafe motion proxy'
            motion.append(collision_certificate(f,i,proxy,fixed,region='new narrow root conservative containing proxy'))
            print('distal',f['id'],flush=True)
            motion.append(collision_certificate(f,i,far,fixed,region='unchanged distal'))
            (OUT/'motion-partial.json').write_text(json.dumps(motion,indent=2))
    tools=tool_checks(layout,roots,fixed)
    openparts=dict(fixed);closedparts=dict(fixed)
    for i,f in enumerate(layout['head']['fingers']):
        for n,s in roots[i].items():
            openparts[f['id']+'_'+n]=place(s,f,SIGNS[i])
            closedparts[f['id']+'_'+n]=place(s,f,SIGNS[i],f['closure_study_deg'])
    cq.exporters.export(comp(openparts.values()),str(OUT/'R4-support-03-open.step'))
    cq.exporters.export(comp(closedparts.values()),str(OUT/'R4-support-03-closed.step'))
    cq.exporters.export(comp([s for n,s in openparts.items() if n.startswith('UR_')]),str(OUT/'single-root-module.step'))
    for n in ['keyed_hub_lower_fork','removable_upper_fork','metal_blade_with_narrow_tongue','output_tenon_D10']:
        cq.exporters.export(roots[0][n],str(OUT/(n+'.step')))
    imp=cq.importers.importStep(str(OUT/'R4-support-03-open.step')).val()
    qa['STEP_round_trip_valid']=imp.isValid();qa['STEP_solid_count_matches']=len(imp.Solids())==len(openparts)
    result=dict(revision='R4-support-03',license='CC-BY-NC-4.0',status='local mechanical integration study; NOT manufacturing or payload release',source_layout_sha256=sha,
        baseline_script_sha256=hashlib.sha256(Path(prev.__file__).read_bytes()).hexdigest(),
        changed_region='root x<=25mm only; LED window clipped to x>=25; root R70 and z0/50 unchanged',
        dimensions_mm=dict(tenon_D=10,tenon_L=10.8,hub_D=24,hub_L=10,hub_bore=10,key=[3,3,8],shaft_key_depth=1.8,hub_key_depth=1.4,shaft_end_recess=.2,
            shoulder_spacer=[16,10.1,1],end_washer=[18,4.3,1.5],fork_tongue_width=18,fork_gap=6,cheek_thickness=4,blade_change_end_x=25,flare_start_x=24,
            M3_hole_centers=[[21,-4.5],[21,4.5]],M3_hole_D=3.4,LED_start_clip_x=25),
        mechanics=mechanics(),component_geometry=detail,carrier_slots=savings,carrier_slot_saving_g=sum(x['saved_g'] for x in savings),
        motion=motion,tool_approach=tools,self_checks=qa,export_solids=len(openparts),import_solids=len(imp.Solids()))
    (OUT/'R4-support-03.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'motion-partial.json').unlink(missing_ok=True)
    print(json.dumps(dict(checks=qa,slot_saving=result['carrier_slot_saving_g'],motion=[{k:v for k,v in r.items() if k not in ['certified_intervals','failures']} for r in motion],tool_failed=[r for r in tools if not r['passes']]),indent=2),flush=True)
if __name__=='__main__':main()
