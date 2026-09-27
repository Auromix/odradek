#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""R4-support-01: independent shaft/load/envelope study, NOT manufacturing CAD.

Run with the repository engineering environment. numpy/matplotlib required;
--cad additionally requires cadquery. Never modifies shared layout parameters.
All geometry is nominal mm. SI calculations are explicitly cross-checked.
"""
from pathlib import Path
import argparse, hashlib, itertools, json, math
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = '4349d1797b906b67a7bc396fcb84bc439c2d70dd0b337659e552cee293d2dd81'
OUT = ROOT / 'engineering/generated/gripper-support'
P = dict(revision='R4-support-01', motor_body_length_mm=70.1, motor_body_diameter_mm=22.,
         motor_shaft_length_mm=16.3, motor_shaft_diameter_mm=6.,
         coupling_diameter_mm=20., coupling_length_mm=30., coupling_insertion_mm=10.,
         bearing_d_mm=10., bearing_D_mm=26., bearing_B_mm=8.,
         pulley_L_mm=.812*25.4, pulley_W_mm=.400*25.4, pulley_E_mm=.306*25.4,
         pulley_flange_D_mm=1.250*25.4, pulley_hub_D_mm=.776*25.4,
         pulley_tooth_OD_mm=1.098*25.4, belt_width_mm=9., belt_thickness_allowance_mm=3.,
         pulley_teeth=30, pitch_mm=3., center_distance_mm=45., axis_z_difference_mm=25.,
         belt_plane_u_mm=2.5, bearing_to_pulley_gap_mm=2., plate_thickness_mm=10.,
         retention_bay_mm=4., coupling_to_retention_gap_mm=1., shaft_diameter_mm=10.,
         input_shaft_length_mm=65., output_shaft_length_mm=67.,
         head_diameter_reference_mm=210., required_projection_gap_mm=1.)

def v(x): return np.array(x, dtype=float)
Z=v([0,0,1])

def stack():
    # Drawing Type 6F: E is the projecting hub; L includes flange stack.
    # Hub faces -u. The centered flange allocation is a nominal drawing reading.
    half=(P['pulley_L_mm']-P['pulley_E_mm'])/2
    a=-half-P['pulley_E_mm']; b=half; gap=P['bearing_to_pulley_gap_mm']
    ba=[a-gap-P['bearing_B_mm'],a-gap]; bb=[b+gap,b+gap+P['bearing_B_mm']]
    pa=[a-gap-P['plate_thickness_mm'],a-gap]
    pb=[b+gap,b+gap+P['plate_thickness_mm']]
    ra=[pa[0]-P['retention_bay_mm'],pa[0]]
    rb=[pb[1],pb[1]+P['retention_bay_mm']]
    cr=ra[0]-P['coupling_to_retention_gap_mm']; cl=cr-P['coupling_length_mm']
    front=cl-(P['motor_shaft_length_mm']-P['coupling_insertion_mm'])
    inp=[cr-P['coupling_insertion_mm'],cr-P['coupling_insertion_mm']+P['input_shaft_length_mm']]
    hub=[rb[1]+1,rb[1]+11]
    op=[ra[0]-2,ra[0]-2+P['output_shaft_length_mm']]
    return dict(pulley_limits=[a,b],flange_limits=[-half,half],hub_limits=[a,-half],
                bearing_A=ba,bearing_B=bb,plate_A=pa,plate_B=pb,retention_A=ra,retention_B=rb,
                coupling=[cl,cr],motor_body=[front-P['motor_body_length_mm'],front],
                motor_shaft=[front,front+P['motor_shaft_length_mm']],input_shaft=inp,output_shaft=op,
                finger_hub=hub,bearing_centers=[sum(ba)/2,sum(bb)/2])

def box(name, group, c, axes, half, kind, **extra):
    return dict(name=name,group=group,center=v(c),axes=np.column_stack(axes),half=v(half),kind=kind,**extra)

def sat(a,b):
    A=a['axes']; B=b['axes']; delta=b['center']-a['center']
    axes=np.concatenate([A.T,B.T,np.cross(A.T[:,None,:],B.T[None,:,:]).reshape(-1,3)])
    axes=axes[np.linalg.norm(axes,axis=1)>1e-9]; axes/=np.linalg.norm(axes,axis=1)[:,None]
    gaps=np.abs(axes@delta)-np.abs(axes@A)@a['half']-np.abs(axes@B)@b['half']
    return float(max(gaps))

def corners(a):
    return a['center']+np.array(list(itertools.product([-1.,1.],repeat=3)))*a['half']@a['axes'].T

def envelope(parts):
    pts=np.concatenate([corners(x) for x in parts]); r=np.linalg.norm(pts[:,:2],axis=1)
    return dict(coaxial_obb_enclosing_diameter_mm=float(2*max(r)),z_min_mm=float(pts[:,2].min()),
                z_max_mm=float(pts[:,2].max()),depth_mm=float(np.ptp(pts[:,2])),
                aabb_min_mm=pts.min(axis=0).tolist(),aabb_max_mm=pts.max(axis=0).tolist())

def build(layout):
    s=stack(); parts=[]; rows=[]
    dr=math.sqrt(P['center_distance_mm']**2-P['axis_z_difference_mm']**2)
    for i,f in enumerate(layout['head']['fingers']):
        phi=math.radians(f['phi_deg']); er=v([math.cos(phi),math.sin(phi),0]); et=v([-math.sin(phi),math.cos(phi),0])
        sg=1 if f['id'] in ('UR','LL') else -1; u=sg*et
        hinge=f['root_radius_mm']*er+f['root_z_mm']*Z+P['belt_plane_u_mm']*u
        driver=hinge-dr*er-P['axis_z_difference_mm']*Z
        vv=(hinge-driver)/P['center_distance_mm']; w=np.cross(u,vv)
        name=f['id']; axes=[u,vv,w]
        def cyl(label, origin, lim, radius, kind, bore=0):
            parts.append(box(name+'_'+label,i,origin+u*(sum(lim)/2),axes,
                [(lim[1]-lim[0])/2,radius,radius],kind,shape='cylinder',bore_mm=bore,limits_u_mm=lim))
        def block(label, origin, lim, vmid, whalf, vhalf, kind, wmid=0):
            parts.append(box(name+'_'+label,i,origin+u*(sum(lim)/2)+vv*vmid+w*wmid,axes,
                [(lim[1]-lim[0])/2,vhalf,whalf],kind,shape='box',limits_u_mm=lim))
        cyl('motor',driver,s['motor_body'],11,'motor')
        cyl('motor_shaft',driver,s['motor_shaft'],3,'motor_shaft')
        cyl('coupling',driver,s['coupling'],10,'coupling')
        for role,origin in [('input',driver),('output',hinge)]:
            for side in ['A','B']:
                cyl(role+'_bearing_'+side,origin,s['bearing_'+side],13,'bearing',10)
                cyl(role+'_retention_'+side,origin,s['retention_'+side],6.1,'retention_allowance',10)
            cyl(role+'_shaft',origin,s[role+'_shaft'],5,'shaft')
            cyl(role+'_pulley_flange',origin,s['flange_limits'],P['pulley_flange_D_mm']/2,'pulley_flange',10)
            cyl(role+'_pulley_hub',origin,s['hub_limits'],P['pulley_hub_D_mm']/2,'pulley_hub',10)
        cyl('finger_metal_hub',hinge,s['finger_hub'],12,'finger_hub',10)
        for side in ['A','B']:
            block('bearing_bridge_'+side,driver,s['plate_'+side],22.5,17,39.5,'bridge_plate')
        # Connecting rib in the free region between pulleys, clear of belt spans.
        block('central_tie',driver,[s['plate_A'][1],s['plate_B'][0]],22.5,5,2,'tie')
        front=s['motor_body'][1]
        cyl('motor_flange',driver,[front,front+2],17,'motor_mount',10.5)
        for j,ww in enumerate([-15,15]):
            block('motor_bridge_'+str(j),driver,[front+2,s['plate_A'][0]],0,2,5,'motor_mount',ww)
        # Conservative full annular cover at each pulley plus two straight spans.
        # Own pulley contact is intentional. Geometry never claims exact teeth.
        rp=P['pulley_teeth']*P['pitch_mm']/(2*math.pi)
        for k,origin in [('drive',driver),('hinge',hinge)]:
            cyl('belt_'+k+'_cover',origin,[-4.5,4.5],rp+1.5,'belt_cover')
        for j,ww in enumerate([-rp,rp]):
            block('belt_span_'+str(j),driver,[-4.5,4.5],22.5,1.5,22.5,'belt_cover',ww)
        rows.append(dict(finger=name,phi_deg=f['phi_deg'],axis_u=u.tolist(),
            root_anchor_mm=(f['root_radius_mm']*er+f['root_z_mm']*Z).tolist(),
            driver_belt_plane_center_mm=driver.tolist(),hinge_belt_plane_center_mm=hinge.tolist(),
            motor_front_center_mm=(driver+front*u).tolist(),
            motor_center_mm=(driver+sum(s['motor_body'])/2*u).tolist(),
            finger_hub_center_mm=(hinge+sum(s['finger_hub'])/2*u).tolist(),
            motor_retraction_from_previous_mm=(-8.15-front),
            exact_motor_cylinder_radial_diameter_mm=2*math.hypot(f['root_radius_mm']-dr+11,
                max(abs(P['belt_plane_u_mm']+x) for x in s['motor_body']))))
    return parts,rows

def collision_report(parts):
    # Inter-module only: within a module, shaft/bearing/housing intersections are
    # intentional mating contacts, not an invitation to silently ignore other parts.
    pairs=[]
    for a,b in itertools.combinations(parts,2):
        if a['group']==b['group']:continue
        gap=sat(a,b)
        pairs.append(dict(a=a['name'],b=b['name'],projection_gap_mm=gap))
    bad=[x for x in pairs if x['projection_gap_mm']<P['required_projection_gap_mm']-1e-9]
    return dict(scope='inter-module conservative OBB screen only; exact solid tests are separate',
                pairs_tested=len(pairs),required_projection_gap_mm=1,
                passes=not bad,minimum_projection_gap_mm=min(x['projection_gap_mm'] for x in pairs),
                flagged_pairs=bad)

def beam(F, contact=0):
    s=stack(); a,b=s['bearing_centers']; x=sum(s['finger_hub'])/2
    RB=(F*(0-a)+contact*(x-a))/(b-a); RA=F+contact-RB
    # Signed shear/moment integration for three point loads. Exact for this beam.
    load=[(a,RA),(0,-F),(b,RB),(x,-contact)]
    def moment(q):return sum(f*(q-t) for t,f in load if t<=q)
    M=max(abs(moment(q)) for q in [a,0,b,x])
    E=205000.; d=10.; I=math.pi*d**4/64; J=2*I; T=3700.
    # No overhung contact in center-deflection expression; contact case is reactions/stress only.
    deflection=F*(-a)**2*b**2/(3*E*I*(b-a)) if contact==0 else None
    sigma=32*M/(math.pi*d**3); tau=16*T/(math.pi*d**3)
    return dict(belt_resultant_N=F,example_contact_N=contact,bearing_A_reaction_N=RA,
                bearing_B_reaction_N=RB,max_bending_Nmm=M,bending_MPa=sigma,torsional_MPa=tau,
                von_mises_gross_MPa=math.sqrt(sigma**2+3*tau**2),
                belt_plane_deflection_mm=deflection,SKF_static_ratio_C0_over_max_radial=1960/max(abs(RA),abs(RB)),
                note='gross circular shaft; no keyway/groove/fit/axial/impact/fatigue allowance; no acceptance')

def mechanics():
    dp=P['pulley_teeth']*P['pitch_mm']/math.pi; delta=2*3.7/(dp/1000)
    rows=[beam(F) for F in [delta,400,600,800]]
    contact=[beam(F,sign*50) for F in [400,600,800] for sign in [-1,1]]
    return dict(pitch_diameter_mm=dp,belt_pitch_length_mm=2*45+math.pi*dp,
        torque_screen_Nm=3.7,tension_difference_N=delta,
        tension_cases=[dict(resultant_N=F,tight_N=(F+delta)/2,slack_N=(F-delta)/2) for F in [400,600,800]],
        input_shaft=rows,output_shaft_with_50N_overhung_example=contact,
        shaft_E_MPa_assumption=205000,key_shear_MPa=2*3700/(10*3*6),
        key_bearing_MPa=4*3700/(10*3*6),key_note='3x3x6 mm effective rectangular key assumption; material and notch details pending',
        NBK_nominal_torque_ceiling_Nm_at_30C=6,NBK_nominal_ratio_to_screen=6/3.7,
        NBK_60C_elastomer_rating_Nm=6*.7,NBK_twist_deg_at_3_7Nm=math.degrees(3.7/87),
        screening_only=True)

def self_checks(m,parts,rows):
    s=stack();a,b=s['bearing_centers'];checks={}
    checks['belt_length_reverse']=math.isclose(m['belt_pitch_length_mm'],180,abs_tol=1e-10)
    checks['tension_torque_reverse']=math.isclose(m['tension_difference_N']*m['pitch_diameter_mm']/2000,3.7,abs_tol=1e-12)
    checks['gates_inch_to_mm']=math.isclose(P['pulley_L_mm']/25.4,.812,abs_tol=1e-12)
    checks['motor_shaft_engagement']=math.isclose(s['motor_shaft'][1]-s['coupling'][0],10,abs_tol=1e-12)
    checks['independent_shaft_engagement']=math.isclose(s['coupling'][1]-s['input_shaft'][0],10,abs_tol=1e-12)
    checks['two_bearings_each_of_two_shafts_per_finger']=sum(x['kind']=='bearing' for x in parts)==16
    checks['center_distances']=all(math.isclose(np.linalg.norm(v(r['driver_belt_plane_center_mm'])-v(r['hinge_belt_plane_center_mm'])),45,abs_tol=1e-10) for r in rows)
    checks['force_moment_equilibrium']=all(abs(r['bearing_A_reaction_N']+r['bearing_B_reaction_N']-r['belt_resultant_N']-r['example_contact_N'])<1e-9 and abs(r['bearing_B_reaction_N']*(b-a)-r['belt_resultant_N']*(-a)-r['example_contact_N']*(sum(s['finger_hub'])/2-a))<1e-8 for r in m['input_shaft']+m['output_shaft_with_50N_overhung_example'])
    r=m['input_shaft'][2];d=.01; Is=math.pi*d**4/64
    si=r['belt_resultant_N']*((-a)/1000)**2*(b/1000)**2/(3*205e9*Is*((b-a)/1000))*1000
    checks['SI_mm_deflection_cross_check']=math.isclose(si,r['belt_plane_deflection_mm'],rel_tol=1e-12)
    checks['input_shaft_covers_supports']=s['input_shaft'][1]>s['retention_B'][1]
    checks['output_shaft_covers_finger_hub']=s['output_shaft'][1]>s['finger_hub'][1]
    if not all(checks.values()):raise AssertionError(checks)
    return checks

def serialize(x):
    if isinstance(x,np.ndarray):return x.tolist()
    raise TypeError(type(x))

def plots(parts,results):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon, Circle, Rectangle
    colors={'motor':'#4c6170','coupling':'#e7aa48','bearing':'#1c9394','bridge_plate':'#c8d6dc','belt_cover':'#343a40','finger_hub':'#c56d45'}
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    for ax,xy,title in [(axes[0],(0,1),'XY projection'),(axes[1],(0,2),'XZ projection')]:
        for p in parts:
            pts=corners(p)[:,xy];center=pts.mean(axis=0)
            # Convex hull monotonic chain, avoids scipy dependency.
            ps=sorted(set(map(tuple,pts.tolist())))
            def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
            lo=[];hi=[]
            for q in ps:
                while len(lo)>=2 and cross(lo[-2],lo[-1],q)<=0:lo.pop()
                lo.append(q)
            for q in reversed(ps):
                while len(hi)>=2 and cross(hi[-2],hi[-1],q)<=0:hi.pop()
                hi.append(q)
            ax.add_patch(Polygon(lo[:-1]+hi[:-1],facecolor=colors.get(p['kind'],'#a6b1b7'),edgecolor='#293f49',alpha=.32,lw=.6))
        if xy==(0,1):ax.add_patch(Circle((0,0),105,fill=False,color='#c3463e',linestyle='--',lw=1.8,label='Old nominal diameter 210'))
        ax.autoscale();ax.set_aspect('equal');ax.grid(alpha=.18);ax.set_title(title);ax.set_xlabel('X / mm');ax.set_ylabel(('Y' if xy==(0,1) else 'Z')+' / mm')
    e=results['envelope']
    fig.suptitle(f"R4-support-01 | REJECTED FOUR-MODULE PACKAGING; not manufacturing CAD\nBounding diameter {e['coaxial_obb_enclosing_diameter_mm']:.1f} mm; inter-module OBB flags {len(results['collisions']['flagged_pairs'])}",fontsize=13)
    fig.tight_layout(rect=(0,.06,1,.92));fig.text(.04,.02,'Unresolved: shaft fits, pulley keyway, finger yoke, mounting, optical core, cables and moving sweep. CC BY-NC 4.0',fontsize=9)
    fig.savefig(OUT/'four-module-layout.svg');fig.savefig(OUT/'four-module-layout.png',dpi=170);plt.close(fig)
    s=stack(); fig,ax=plt.subplots(figsize=(14,5.8));
    for key,y,height,color in [('motor_body',2,1,'#4c6170'),('motor_shaft',2.4,.2,'#81959f'),('coupling',2.05,.9,'#e7aa48'),('input_shaft',2.4,.2,'#81959f'),('output_shaft',.4,.2,'#81959f')]:
        a,b=s[key];ax.add_patch(Rectangle((a,y),b-a,height,fc=color,ec='black',lw=.6));ax.text((a+b)/2,y+height+.08,key.replace('_',' '),ha='center',fontsize=8)
    for y in [.0,2.0]:
        for side in ['A','B']:
            a,b=s['bearing_'+side];ax.add_patch(Rectangle((a,y),b-a,1,fc='#1c9394',ec='black'));ax.text((a+b)/2,y+.5,side,ha='center',va='center',color='white')
        a,b=s['pulley_limits'];ax.add_patch(Rectangle((a,y-.1),b-a,1.2,fc='#c56d45',ec='black',alpha=.65));ax.text((a+b)/2,y+.5,'30T',ha='center')
    a,b=s['finger_hub'];ax.add_patch(Rectangle((a,0),b-a,1,fc='#c56d45',ec='black'));ax.text((a+b)/2,1.08,'finger hub',ha='center',fontsize=8)
    ax.axvline(0,color='#d6503f',ls='--');ax.text(1,3.3,'Belt center plane u = 0',color='#ae3629')
    for key,y in [('motor_body',3.9),('coupling',3.5),('pulley_limits',-1.0)]:
        a,b=s[key];ax.annotate('',(a,y),(b,y),arrowprops=dict(arrowstyle='<->',lw=.7));ax.text((a+b)/2,y+.12,f'{b-a:.4g} mm',ha='center',fontsize=9)
    ax.set_xlim(-145,45);ax.set_ylim(-1.6,4.5);ax.set_yticks([]);ax.set_xlabel('Local u / mm (shaft axis; diagram vertical axis is schematic)');ax.grid(axis='x',alpha=.15)
    ax.set_title('Single finger: gearhead → flexible coupling → two-bearing input shaft → belt → two-bearing finger shaft\nBearing span %.4f mm; separate locating/floating housing design and shaft fit remain required' % (s['bearing_centers'][1]-s['bearing_centers'][0]),fontsize=11)
    fig.tight_layout();fig.savefig(OUT/'single-finger-stack.svg');fig.savefig(OUT/'single-finger-stack.png',dpi=170);plt.close(fig)

def cad(parts):
    import cadquery as cq
    shapes=[];byname={};checks=[]
    for p in parts:
        c=p['center'];u=p['axes'][:,0];vv=p['axes'][:,1];h=p['half']
        if p['shape']=='cylinder':
            sh=cq.Solid.makeCylinder(float(h[1]),float(2*h[0]),cq.Vector(*(c-u*h[0])),cq.Vector(*u))
            if p.get('bore_mm',0):
                sh=sh.cut(cq.Solid.makeCylinder(p['bore_mm']/2,float(2*h[0]+.2),cq.Vector(*(c-u*(h[0]+.1))),cq.Vector(*u)))
        else:
            plane=cq.Plane(origin=cq.Vector(*c),xDir=cq.Vector(*u),normal=cq.Vector(*p['axes'][:,2]))
            sh=cq.Workplane(plane).box(float(2*h[0]),float(2*h[1]),float(2*h[2])).val()
            if p['kind']=='bridge_plate':
                for offset in [-22.5,22.5]:
                    origin=c+vv*offset-u*(h[0]+.1)
                    # Nominal 24 mm through-opening backs only the outer ring;
                    # 26 mm counterbore is 8 mm deep. Fits/endplay not specified.
                    sh=sh.cut(cq.Solid.makeCylinder(12,float(2*h[0]+.2),cq.Vector(*origin),cq.Vector(*u)))
                    if p['name'].endswith('_A'):origin+=u*2.1
                    sh=sh.cut(cq.Solid.makeCylinder(13,8.1,cq.Vector(*origin),cq.Vector(*u)))
        if not sh.isValid():raise AssertionError(p['name'])
        shapes.append(sh);byname[p['name']]=sh
        checks.append(dict(name=p['name'],valid=sh.isValid(),volume_mm3=sh.Volume()))
    # Exact intersections only for the conservative OBB flags; still envelope CAD,
    # not vendor CAD or a completed fit/tolerance model.
    exact=[]
    for pair in collision_report(parts)['flagged_pairs']:
        a=byname[pair['a']];b=byname[pair['b']]
        vol=a.intersect(b).Volume()
        exact.append(dict(**pair,envelope_intersection_volume_mm3=vol,envelope_distance_mm=a.distance(b)))
    compound=cq.Compound.makeCompound(shapes)
    cq.exporters.export(compound,str(OUT/'R4-support-01-envelope.step'))
    cq.exporters.export(cq.Compound.makeCompound([shapes[i] for i,p in enumerate(parts) if p['group']==0]),str(OUT/'single-finger-envelope.step'))
    back=cq.importers.importStep(str(OUT/'R4-support-01-envelope.step')).val()
    return dict(component_count=len(shapes),all_shapes_valid=all(x['valid'] for x in checks),
                step_roundtrip_valid=back.isValid(),step_solid_count=len(back.Solids()),
                exact_envelope_intersections_for_obb_flags=exact,
                scope='nominal envelopes with bearing holes; NOT full machine geometry, not load approval')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cad',action='store_true');args=ap.parse_args()
    raw=(ROOT/'engineering/parameters/r4-layout.json').read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=EXPECTED:raise SystemExit('Shared layout hash changed; explicitly review this independent study before updating EXPECTED.')
    layout=json.loads(raw);parts,rows=build(layout);m=mechanics();report=collision_report(parts)
    result=dict(revision=P['revision'],license='CC-BY-NC-4.0',status='NOT RELEASED; previous compact drive envelope invalidated',
                source_layout_sha256=sha,parameters=P,local_stack_mm=stack(),mechanics=m,coordinates=rows,
                envelope=envelope(parts),collisions=report,self_checks=self_checks(m,parts,rows),
                exclusions=['full fingers/yokes and their motion','optical core/cameras/display','wires, fasteners and covers','motor combined drawing','manufacturing fits and tolerances','holding brake and payload rating'],parts=parts)
    OUT.mkdir(parents=True,exist_ok=True)
    if args.cad:result['cad_qa']=cad(parts)
    plots(parts,result)
    (OUT/'R4-support-01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=serialize)+'\n')
    (OUT/'collision-report.json').write_text(json.dumps(dict(revision=P['revision'],source_layout_sha256=sha,obb=report,cad_qa=result.get('cad_qa')),indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['revision','envelope','self_checks']},indent=2))
    print('OBB flags:',len(report['flagged_pairs']))
    if 'cad_qa' in result:print('Exact envelope intersections:',sum(x['envelope_intersection_volume_mm3']>1e-6 for x in result['cad_qa']['exact_envelope_intersections_for_obb_flags']))

if __name__=='__main__':main()
