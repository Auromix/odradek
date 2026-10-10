# SPDX-License-Identifier: CC-BY-NC-4.0
"""Current CAD budget screens; never substitute for metal/thermal qualification."""
from pathlib import Path
import json,csv,math
import numpy as np
import feasibility01 as f
HERE=Path(__file__).resolve().parent;OUT=HERE/'build'

def review(rows,budget,q,layout,sources):
    # This budget follows the actual FRONT10/IF09 parts, rather than A17 masses.
    spring_budget=budget+[dict(id='spring-bracket-allowance',owner=2,frame='J2.rotor',mass_kg=.15,com_mm=[55,0,0])]
    def tau_at(theta):
        v=q.copy();v[:,1]=theta
        return np.array([f.torque(layout,v,p,spring_budget)[:,1] for p in [0,3]])
    A=tau_at(0);B=tau_at(90)
    err=max(float(np.max(abs(tau_at(a)-A*np.cos(np.radians(a))-B*np.sin(np.radians(a))))) for a in [-60,35,110])
    assert err<1e-9
    prior=json.loads((OUT/'feasibility01.json').read_text())
    pin=next(p for p in prior['counterbalance_candidates'] if p['model']=='01625025')
    limit=22.8;force_rows=[]
    for angle in range(-60,111):
        t=A*np.cos(np.radians(angle))+B*np.sin(np.radians(angle))
        length,lever,_,_=f.geometry(np.array([angle]),pin['a_mm'],pin['b_mm'],pin['fixed_pin_x_mm']);k=float(lever[0])
        if abs(k)<1e-9:
            lo=0.;hi=None;ok=bool(t.min()>=-limit and t.max()<=limit)
        else:
            x=(-limit-t)/k;y=(limit-t)/k
            lo=max(0.,float(np.max(np.minimum(x,y))));hi=float(np.min(np.maximum(x,y)));ok=hi>=lo
        force_rows.append(dict(J2_deg=angle,eye_length_mm=float(length[0]*1000),assist_lever_m=k,
            raw_min_Nm=float(t.min()),raw_max_Nm=float(t.max()),required_measured_force_min_N=lo,
            required_measured_force_max_N=hi,sampled_force_window_nonempty=ok))
    path=OUT/'spring-required-force13.csv'
    with path.open('w') as fp:
        w=csv.DictWriter(fp,fieldnames=list(force_rows[0]));w.writeheader();w.writerows(force_rows)

    # Gross rectangular tube geometry ONLY, using current CAD ownership and
    # gravity. Every assigned moving body contributes an absolute moment, so
    # cancellation cannot make this preliminary static envelope smaller.
    # No claim of joint reactions, drilled-section strength or elastic FEA.
    bodies=budget+[dict(frame=j['id']+'.fixed',mass_kg=j['mass_kg'],com_mm=j['motor_center']) for j in layout['joints']]
    grouped={}
    for body in bodies:
        frame=body['frame'];item=grouped.setdefault(frame,[]);item.append(body)
    grouped={frame:(sum(b['mass_kg'] for b in bs),np.array([b['com_mm'] for b in bs]),np.array([b['mass_kg'] for b in bs])) for frame,bs in grouped.items()}
    width,height,wall=20.,40.,2.
    area=width*height-(width-2*wall)*(height-2*wall)
    Iy=(width*height**3-(width-2*wall)*(height-2*wall)**3)/12
    Iz=(height*width**3-(height-2*wall)*(width-2*wall)**3)/12
    Zy=Iy/(height/2);Zz=Iz/(width/2);Am=(width-wall)*(height-wall)
    tubes=[]
    for id,joint,cut,length in [('A16-S105-upper-stock-tube',3,[50.,0,0],220.),('A16-S108-fore-stock-tube',4,[20.,62.,0],55.)]:
        row=next(p for p in rows if p['id']==id);maxima=np.zeros(5);worst=None
        # Four side-centreline through holes, each crossing two2mm walls.
        nominal_drilled_volume=area*length-8*math.pi*(4.5/2)**2*wall
        assert abs(row['volume_mm3']-nominal_drilled_volume)<1e-5
        attached={frame:body for frame,body in grouped.items() if frame.startswith('J') and
                  (int(frame[1])>joint or frame==f'J{joint}.rotor')}
        moving_mass=sum(body[0] for body in attached.values())+3
        for angles in q:
            frames=f.frames(layout,angles);T=frames[f'J{joint}.rotor'];R=T[:3,:3];point=T[:3,:3]@np.array(cut)+T[:3,3]
            gravity=R.T@np.array([0.,0.,-9.81]);moments=np.zeros(3)
            for frame,(_,coms,masses) in attached.items():
                W=frames[frame];global_points=coms@W[:3,:3].T+W[:3,3]
                local=(global_points-point)@R/1000
                moments+=np.abs(np.cross(local,masses[:,None]*gravity)).sum(axis=0)
            loc=(frames['flange'][:3,3]-point)@R/1000
            moments+=np.abs(np.cross(loc,3*gravity))
            axial=abs(gravity[0])*moving_mass/area
            bending=moments[1]*1000/Zy+moments[2]*1000/Zz
            torsion=moments[0]*1000/(2*Am*wall)
            vm=math.sqrt((axial+bending)**2+3*torsion**2)
            values=np.r_[moments,axial+bending,vm]
            if values[-1]>maxima[-1]:worst=angles.tolist()
            maxima=np.maximum(maxima,values)
        tubes.append(dict(id=id,frame=row['frame'],section_point_mm=cut,width_height_wall_mm=[width,height,wall],
          CAD_volume_mm3=row['volume_mm3'],gross_area_mm2=area,gross_Iy_mm4=Iy,gross_Iz_mm4=Iz,
          gross_Zy_mm3=Zy,gross_Zz_mm3=Zz,assigned_moving_mass_with_payload_kg=moving_mass,
          component_abs_sum_moment_max_Nm=maxima[:3].tolist(),gross_normal_stress_envelope_MPa=float(maxima[3]),
          gross_von_mises_bending_torsion_only_MPa=float(maxima[4]),worst_sample_deg=worst,
          net_drilled_section_fasteners_socket_strength_or_deflection_qualified=False))
    result=dict(revision='A18-CURRENT-STATIC-SCREEN13',source_sha256=sources,
       reconstruction_error_Nm=err,sample_count=len(q),payload_cases_kg=[0,3],
       force_requirement_table_sha256=f.c.sha(path),numerical_pin_candidate=pin,
       force_windows_nonempty=all(p['sampled_force_window_nonempty'] for p in force_rows),
       provisional_motor_residual_limit_Nm=limit,supplier_force_curve_confirmed=False,
       tube_gross_section_screen=tubes,metal_structure_qualified=False,production_release=False,
       limitations=['Unfiltered finite poses; not a reachable workspace or dynamic analysis.',
       'Spring pin geometry is a numerical candidate with no built or collision-qualified brackets.',
       'Stress envelopes use whole nominal moving masses as assigned to the tube; exact load paths, sockets, holes, fatigue, local stresses, contacts and buckling are absent.',
       'Thin-wall closed-section torsion estimate excludes transverse shear and local corner stress.',
       'No material allowable, safety factor, stiffness, manufacturing tolerances or physical certification was applied.'])
    (OUT/'qualification13.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result,force_rows
