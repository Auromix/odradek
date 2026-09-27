# SPDX-License-Identifier: CC-BY-NC-4.0
# Attribution: Odradek - Auromix contributors
# Historical 14 mm pulley proxy; superseded as an actual drive package.
#!/usr/bin/env python3
"""Conservative OBB/SAT packaging study. Not a manufacturing model."""
from __future__ import annotations
import argparse, itertools, json, math
from pathlib import Path
import numpy as np

PHIS=[35.,145.,225.,315.]
NAMES=['UR','UL','LL','LR']
L=70.1; D=22.; SHAFT_L=16.3; SHAFT_D=6.
CENTER_DISTANCE=45.; DZ=25.; DR=math.sqrt(CENTER_DISTANCE**2-DZ**2)
PULLEY_OD=34.; PULLEY_WIDTH=14.; BELT_WIDTH=9.; BELT_THICK=3.
PITCH_D=30.*3./math.pi; PULLEY_P=SHAFT_L/2
GAP=1.

def vec(v): return np.array(v,dtype=float)
Z=vec([0,0,1])

def obb(name, group, center, axes, half, kind):
    return dict(name=name, group=group, center=vec(center), axes=np.column_stack(axes),half=vec(half),kind=kind)

def sat(a,b,gap=GAP):
    """Maximum projection interval gap over 15 OBB candidate SAT axes.
    Positive >= gap proves separation by at least gap along that axis.
    Negative means OBB intersection (not proof exact cylinders intersect).
    """
    A=a['axes']; B=b['axes']; delta=b['center']-a['center']
    cross=np.cross(A.T[:,None,:],B.T[None,:,:]).reshape((-1,3))
    axes=np.concatenate([A.T,B.T,cross]); norm=np.linalg.norm(axes,axis=1)
    axes=axes[norm>1e-9]; axes/=np.linalg.norm(axes,axis=1)[:,None]
    gaps=np.abs(axes@delta)-np.abs(axes@A)@a['half']-np.abs(axes@B)@b['half']
    i=int(np.argmax(gaps))
    return float(gaps[i]), axes[i].tolist()

def corners(a):
    return a['center']+np.array(list(itertools.product([-1.,1.],repeat=3)))*a['half']@a['axes'].T

def build(R,q_top,q_bot,sg_top=1,sg_bot=1):
    parts=[]; rows=[]
    qs=[q_top,-q_top,q_bot,-q_bot]
    sgs=[sg_top,-sg_top,sg_bot,-sg_bot]
    for i,(phi,q,sg) in enumerate(zip(PHIS,qs,sgs)):
        theta=math.radians(phi); er=vec([math.cos(theta),math.sin(theta),0]); et=vec([-math.sin(theta),math.cos(theta),0]); u=sg*et
        hz=0 if i<2 else 50
        s=q-sg*(L/2+PULLEY_P)
        c=(R-DR)*er+s*et+vec([0,0,hz-DZ])
        f=c+u*L/2; e=f+u*SHAFT_L; p=f+u*PULLEY_P
        h=R*er+q*et+vec([0,0,hz])
        parts.append(obb(f'{NAMES[i]}_body',i,c,[u,er,Z],[L/2,D/2,D/2],'motor_body'))
        parts.append(obb(f'{NAMES[i]}_shaft',i,f+u*SHAFT_L/2,[u,er,Z],[SHAFT_L/2,SHAFT_D/2,SHAFT_D/2],'motor_shaft'))
        parts.append(obb(f'{NAMES[i]}_drive_pulley',i,p,[u,er,Z],[PULLEY_WIDTH/2,PULLEY_OD/2,PULLEY_OD/2],'drive_pulley'))
        parts.append(obb(f'{NAMES[i]}_hinge_pulley',i,h,[u,er,Z],[PULLEY_WIDTH/2,PULLEY_OD/2,PULLEY_OD/2],'hinge_pulley'))
        rows.append(dict(finger=NAMES[i],phi_deg=phi,motor_axis_sign_e_t=sg,motor_center_tangent_mm=s,hinge_pulley_tangent_mm=q,body_center_mm=c.tolist(),front_mounting_face_center_mm=f.tolist(),shaft_tip_mm=e.tolist(),drive_pulley_center_mm=p.tolist(),hinge_pulley_center_mm=h.tolist(),hinge_axis_anchor_mm=(R*er+vec([0,0,hz])).tolist(),drive_to_hinge_center_distance_mm=float(np.linalg.norm(h-p))))
    return parts,rows

def validate(parts,gap=GAP):
    pairs=[]; bad=[]
    for a,b in itertools.combinations(parts,2):
        # Only shaft-to-body mounting and shaft-in-drive-pulley are intentional contact.
        if a['group']==b['group'] and 'motor_shaft' in (a['kind'],b['kind']) and ('motor_body' in (a['kind'],b['kind']) or 'drive_pulley' in (a['kind'],b['kind'])): continue
        g,n=sat(a,b)
        row=dict(a=a['name'],b=b['name'],separating_axis_gap_mm=g,axis=n)
        pairs.append(row)
        if g<gap-1e-9: bad.append(row)
    return bad, pairs

def envelope(parts):
    pts=np.concatenate([corners(x) for x in parts])
    return dict(coaxial_enclosing_diameter_mm=float(np.max(np.linalg.norm(pts[:,:2],axis=1))*2),z_min_mm=float(pts[:,2].min()),z_max_mm=float(pts[:,2].max()),depth_mm=float(np.ptp(pts[:,2])),aabb_min_mm=pts.min(axis=0).tolist(),aabb_max_mm=pts.max(axis=0).tolist())

def plain(part):
    return {k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in part.items()}

def belt_parts(rows,segments=36):
    # Belt centerline around equal pulleys: two semicircles and two straight spans.
    # Chord-aligned boxes are enlarged by exact arc sagitta so the discrete cover is conservative.
    out=[]; rp=PITCH_D/2
    for i,row in enumerate(rows):
        p=vec(row['drive_pulley_center_mm']); h=vec(row['hinge_pulley_center_mm']); u=vec(row['front_mounting_face_center_mm'])-vec(row['body_center_mm']); u/=np.linalg.norm(u)
        v=(h-p)/CENTER_DISTANCE; w=np.cross(u,v); w/=np.linalg.norm(w)
        def addseg(a,b,extra,label):
            direction=(b-a); length=np.linalg.norm(direction); direction/=length
            transverse=np.cross(u,direction); transverse/=np.linalg.norm(transverse)
            out.append(obb(f'{NAMES[i]}_belt_{label}',i,(a+b)/2,[u,direction,transverse],[BELT_WIDTH/2,length/2+extra+BELT_THICK/2,BELT_THICK/2+extra],'belt_cover'))
        for j,sign in enumerate([-1,1]): addseg(p+sign*rp*w,h+sign*rp*w,0,f'straight{j}')
        # p-side outward directions contain -v, h-side +v
        for idx,(c,sg) in enumerate([(p,-1),(h,1)]):
            for j in range(segments):
                a=-math.pi/2+j*math.pi/segments; b=-math.pi/2+(j+1)*math.pi/segments
                pa=c+rp*(sg*math.cos(a)*v+math.sin(a)*w)
                pb=c+rp*(sg*math.cos(b)*v+math.sin(b)*w)
                sag=rp*(1-math.cos((b-a)/2))
                addseg(pa,pb,sag,f'arc{idx}_{j}')
    return out

def assess(R,qtop,qbot,signs=(1,1),belts=False):
    p,r=build(R,qtop,qbot,*signs); bad,pairs=validate(p)
    e=envelope(p)
    res=dict(R_mm=R,q_top_mm=qtop,q_bottom_mm=qbot,axis_signs=list(signs),passes_conservative_hardware_obb_screen=not bad,minimum_tested_gap_mm=min(x['separating_axis_gap_mm'] for x in pairs),failures=bad,envelope=e,coordinates=r)
    if belts:
        bp=belt_parts(r); beltbad=[]; beltmin=float('inf')
        # Only between drive groups; own intended belt-pulley contact excluded.
        for a in bp:
            for b in p:
                if a['group']==b['group']: continue
                g,n=sat(a,b); beltmin=min(beltmin,g)
                if g<GAP-1e-9: beltbad.append(dict(a=a['name'],b=b['name'],separating_axis_gap_mm=g))
        for a,b in itertools.combinations(bp,2):
            if a['group']==b['group']: continue
            # inexpensive sphere filter before SAT
            if np.linalg.norm(a['center']-b['center'])>np.linalg.norm(a['half'])+np.linalg.norm(b['half'])+GAP: continue
            g,n=sat(a,b); beltmin=min(beltmin,g)
            if g<GAP-1e-9: beltbad.append(dict(a=a['name'],b=b['name'],separating_axis_gap_mm=g))
        res.update(belt_cover_test=dict(passes=not beltbad,minimum_tested_gap_mm=beltmin,failures=beltbad,box_count=len(bp),belt_thickness_assumption_mm=BELT_THICK),envelope_with_belt_cover=envelope(p+bp),parts=[plain(x) for x in p])
    return res

def search(R):
    # deterministic coarse survey, followed by bounded fine grids around best cells.
    feasible=[]
    for signs in itertools.product([-1,1],repeat=2):
        for qtop in np.arange(-20,21,2.):
            for qbot in np.arange(-20,21,2.):
                p,_=build(R,qtop,qbot,*signs)
                bad,_=validate(p)
                if not bad: feasible.append((envelope(p)['coaxial_enclosing_diameter_mm'],float(qtop),float(qbot),signs))
    feasible.sort(key=lambda x:(x[0],abs(x[1])+abs(x[2])))
    if not feasible:return None
    best=feasible[0]
    seeds=[]
    for x in feasible:
        if x[3] not in [s[3] for s in seeds]:seeds.append(x)
    for _,qt,qb,signs in seeds:
        for qtop in np.arange(qt-2,qt+2.0001,.25):
            for qbot in np.arange(qb-2,qb+2.0001,.25):
                p,_=build(R,qtop,qbot,*signs); bad,_=validate(p)
                if not bad:
                    cand=(envelope(p)['coaxial_enclosing_diameter_mm'],float(qtop),float(qbot),signs)
                    if cand[0]<best[0]-1e-9 or (abs(cand[0]-best[0])<1e-9 and abs(cand[1])+abs(cand[2])<abs(best[1])+abs(best[2])):best=cand
    return assess(R,best[1],best[2],best[3],belts=True)

def analytic_pair_minimum(R):
    # Equalize motor-body radial envelope and driven-pulley radial envelope.
    a=L+PULLEY_P; b=PULLEY_WIDTH/2; rho=R-DR
    q=((rho+D/2)**2+a*a-(R+PULLEY_OD/2)**2-b*b)/(2*(a+b))
    result=assess(R,q,q,belts=True)
    result['derivation']=dict(body_radius_squared='(R-DR+D/2)^2 + (L+p-q)^2',hinge_pulley_radius_squared='(R+OD/2)^2 + (q+W/2)^2',q_equal_envelope_mm=q,condition='0 <= q <= L/2+p; choose shaft direction so body tangent offset magnitude is L/2+p-q',interpretation='Conditional lower bound for each assembly in this fixed radial/z family; if all assemblies pass, attained global radial-envelope minimum for this family, not a finished head minimum')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); args=ap.parse_args()
    # symmetry parent example s_top=-25, s_bot=-25 with shafts +et on UR/LL
    q_example=-25+(L/2+PULLEY_P)
    results=dict(status='PARAMETRIC ENVELOPE SCREEN ONLY; NOT FOR MANUFACTURE',units='mm, deg',assumptions=dict(body_length_mm=L,body_length_status='70.1 is provisional combined motor+gearhead+encoder input, vendor combination drawing pending',body_diameter_mm=D,shaft_length_mm=SHAFT_L,shaft_diameter_mm=SHAFT_D,pulley_outer_diameter_mm=PULLEY_OD,pulley_width_mm=PULLEY_WIDTH,pulley_envelope_status='assumed flange/hub bounding dimensions; not a selected orderable pulley',pulley_center_from_mounting_face_mm=PULLEY_P,nominal_shaft_axial_space_each_side_mm=(SHAFT_L-PULLEY_WIDTH)/2,pulley_pitch_diameter_mm=PITCH_D,belt_pitch_length_mm=180.,equal_pulley_center_distance_mm=CENTER_DISTANCE,belt_length_check_mm=2*CENTER_DISTANCE+math.pi*PITCH_D,belt_width_mm=BELT_WIDTH,belt_thickness_assumption_mm=BELT_THICK,pulley_axis_separation_z_mm=DZ,pulley_axis_separation_radial_mm=DR,obb_separation_requirement_mm=GAP,phi_deg=PHIS,head_z_axis='forward toward object',excluded=['mounting plates, fasteners, wire exits, bearing supports, tensioner, guards','display and cameras','finger structure, moving sweep and workpiece','tooth engagement, stiffness, loads, shaft stresses and bearing life']),parent_example={str(R):assess(R,q_example,q_example,belts=True) for R in [65,70]},grid_search_domain=dict(q_top_mm=[-20,20],q_bottom_mm=[-20,20],coarse_step_mm=2,fine_step_mm=.25,fine_radius_mm=2,mirror_symmetric_shaft_sign_combinations=4),grid_candidates={str(R):search(R) for R in [65,70]},analytic_pair_minima={str(R):analytic_pair_minimum(R) for R in [65,70]})
    Path(args.output).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    for key,rs in [('parent example',results['parent_example']),('grid',results['grid_candidates'])]:
        for R,r in rs.items():
            print(key,R, None if r is None else {k:r[k] for k in ['q_top_mm','q_bottom_mm','axis_signs','passes_conservative_hardware_obb_screen','minimum_tested_gap_mm','envelope']})
            if r: print('hardware failures',len(r['failures']),'belt',r['belt_cover_test']['passes'],len(r['belt_cover_test']['failures']))
