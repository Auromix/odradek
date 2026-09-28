#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Two primary luminous faces: conditional statics, not a payload qualification."""
from pathlib import Path
import csv, hashlib, json, math
import numpy as np
from r5_passive02 import MODELS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-twocontact01'
G=9.80665

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(n,d): (OUT/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def cross(v):
    x,y,z=v
    return np.array([[0,-z,y],[z,0,-x],[-y,x,0]])

def root_case(kind,hand,mu,contact_x_mm,contacts):
    model=MODELS[kind,False]
    m=model['mass_kg'];x,y,z=model['COM_hinge_m']
    # FORM is mirrored; CARRIER keeps its positive-tangent cam orientation.
    from r5_passive02 import pieces, combine
    if hand=='left':
        pp=pieces(kind)
        pm,pc,pI=pp[0];M=np.diag([1,-1,1])
        model=combine([(pm,M@pc,M@pI@M)]+pp[1:])
        m=model['mass_kg'];x,y,z=model['COM_hinge_m']
    N=2*2*G/(contacts*mu);Ft=2*2*G/contacts
    h=.008/math.sqrt(2)
    tau=contact_x_mm/1000*N-.006*Ft-m*G*z
    cam=tau/h
    required_z=Ft+m*G-cam; external_mx=.032*cam-y*m*G
    Bnear=np.array([-N/2,0,(required_z-external_mx/.016)/2])
    Bfar=np.array([-N/2,0,(required_z+external_mx/.016)/2])
    rc=np.array([.008/math.sqrt(2),.032,.008/math.sqrt(2)])
    rp=np.array([-.006,0,contact_x_mm/1000])
    rg=np.array([-z,y,x])
    external=[(rc,np.array([0,0,cam])),(rp,np.array([N,0,-Ft])),(rg,np.array([0,0,-m*G]))]
    all_forces=external+[(np.array([0,.016,0]),Bnear),(np.array([0,-.016,0]),Bfar)]
    force=sum(f for r,f in all_forces);moment=sum(np.cross(r,f) for r,f in all_forces)
    # Rotor COM can be laterally offset, but all external X force is applied at y=0.
    assert max(abs(force))<1e-10 and max(abs(moment))<1e-10
    return dict(kind=kind,hand=hand,contacts=contacts,assumed_mu=mu,contact_x_mm=contact_x_mm,
        mass_rotor_known_kg=m,normal_N=N,friction_N=Ft,cam_N=cam,hinge_torque_Nm=tau,
        bearing_near_N=float(np.linalg.norm(Bnear)),bearing_far_N=float(np.linalg.norm(Bfar)),
        SKF607_8_static_ratio=950/max(np.linalg.norm(Bnear),np.linalg.norm(Bfar)),
        CFS4_static_ratio=1120/abs(cam),CFS4_structural_limit_ratio=919/abs(cam),
        catalogue_flat40HRC_track_ratio=799/abs(cam),
        planar4mm_width_track_proxy_ratio=799*.8/abs(cam),
        force_residual_N=float(max(abs(force))),moment_residual_Nm=float(max(abs(moment))))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cases=[root_case(k,h,mu,x,n) for k in ['upper','lower'] for h in ['left','right']
        for mu in [.2,.3,.4,.6] for x in [35.,65.,95.] for n in [2,4]]
    with (OUT/'conditional-loads.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cases[0]);w.writeheader();w.writerows(cases)
    nominal=[r for r in cases if r['contacts']==2 and r['assumed_mu']==.4 and r['contact_x_mm']==65]
    pairs=[]
    for size in [(50,50),(80,80),(120,120),(50,120),(80,120),(50,80)]:
        W=max(size);R=W/2+6
        pairs.append(dict(box_dimensions_along_grip_axes_mm=size,common_R_mm=R,
            active_face_separation_mm=W,first_pair='larger dimension; both if square',
            smaller_side_gap_each_mm=(W-min(size))/2,centered_aligned_only=True))
    # A genuine pair of point contacts has no contact moment about its own line.
    n=np.array([1,1,0])/math.sqrt(2);p=.04*n
    grasp=np.block([[np.eye(3),np.eye(3)],[cross(p),cross(-p)]])
    s=np.linalg.svd(grasp,compute_uv=False);rank=int(np.linalg.matrix_rank(grasp))
    assert rank==5
    rng=np.random.default_rng(7);torque_res=0.
    for _ in range(1000):
        f=rng.normal(size=6);w=grasp@f
        torque_res=max(torque_res,abs(n@w[3:]))
    assert torque_res<1e-12
    # Constructive, conservative traction field on two equal, fully seated,
    # uniformly pressed circular patches. Translation + spin share friction.
    # For each patch: |Ft|/A + |k| mu p <= mu p; mean radius = 2 a / 3.
    patches=[]
    for a_mm in [5.,8.,10.,15.]:
        for eccentric_mm in [0.,5.,10.,20.]:
            Ft=2*2*G/2;M=2*2*G*eccentric_mm/1000
            N=(Ft+3*M/(4*a_mm/1000))/.4
            patches.append(dict(assumed_patch_radius_mm=a_mm,eccentricity_about_pair_axis_mm=eccentric_mm,
                design_transverse_force_each_N=Ft,design_twist_Nm=M,
                sufficient_normal_each_N=N,mu=.4,
                scope='uniform circular pressure and full stick/slip friction bound; assumed patch, not a real bottle or measured skin'))
    # Independent polar quadrature of the constructive torsional coefficient.
    rr=(np.arange(200000)+.5)/200000
    mean_r=float(np.mean(2*rr*rr))
    assert abs(mean_r-2/3)<1e-10
    import cadquery as cq
    # Actual top skin face containment of a D20 illustrative patch, centered at
    # local x65,y0; bounding circles do not assert pressure or real contact area.
    patch_fit=[]
    for kind in ['upper','lower']:
        skin=cq.importers.importStep(str(ROOT/'engineering/generated/r5-petal-form02'/f'{kind}-right/compliant_skin.step')).val()
        for a_mm in [8.,10.]:
            disc=cq.Solid.makeCylinder(a_mm,.05,cq.Vector(65,0,9.4))
            outside=sum(s.Volume() for s in disc.cut(skin).Solids())
            patch_fit.append(dict(kind=kind,radius_mm=a_mm,center_local_mm=[65,0],outside_nominal_skin_mm3=outside,
                contained=outside<1e-6,scope='geometry only; does not infer pressure patch'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.hashsalt':'R5-TWOCONTACT01','svg.fonttype':'none'})
    fig,ax=plt.subplots(1,3,figsize=(14,4.8))
    ax[0].add_patch(plt.Rectangle((-25,-60),50,120,facecolor='#dae5e8',edgecolor='#29444e'))
    for X in [-60,60]:ax[0].plot([X,X],[-18,18],color='#a66d25',lw=6)
    for Y in [-60,60]:ax[0].plot([-18,18],[Y,Y],color='#a66d25',lw=6)
    ax[0].annotate('',(-25,-30),(-60,-30),arrowprops={'arrowstyle':'<->'})
    ax[0].text(-42.5,-24,'35 mm',fontsize=8,ha='center')
    ax[0].set(xlim=(-80,80),ylim=(-80,80),xlabel='Grip pair axis A [mm]',ylabel='Grip pair axis B [mm]',title='50 x 120 box / common R = 66 mm')
    ax[0].set_aspect('equal');ax[0].grid(alpha=.15)
    xs=np.linspace(.2,.6,101)
    for nc in [2,4]:ax[1].plot(xs,2*2*G/(nc*xs),label=f'{nc} load-sharing contacts')
    ax[1].set(xlabel='Assumed friction coefficient',ylabel='Normal force per active face [N]',title='2 kg workpiece / 2g screening load')
    ax[1].legend(fontsize=8);ax[1].grid(alpha=.2)
    for a in [5,10,15]:
        pp=[r for r in patches if r['assumed_patch_radius_mm']==a]
        ax[2].plot([r['eccentricity_about_pair_axis_mm'] for r in pp],[r['sufficient_normal_each_N'] for r in pp],marker='o',label=f'patch radius {a} mm')
    ax[2].set(xlabel='COM eccentricity about pair line [mm]',ylabel='Sufficient normal force per face [N]',title='Uniform circular patch model / mu = 0.4')
    ax[2].legend(fontsize=8);ax[2].grid(alpha=.2)
    fig.suptitle('R5-TWOCONTACT01 / compact synchronization changes the load case',fontsize=15)
    fig.text(.02,.015,'Conditional mechanics, not a 2 kg grasp rating. Patch radii and friction require measurement; flat and cylindrical objects differ.',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(OUT/'two-contact-loads.png',dpi=170);fig.savefig(OUT/'two-contact-loads.svg',metadata={'Date':None});plt.close(fig)
    inp=[ROOT/'engineering/r5_passive02.py',ROOT/'engineering/generated/r5-carrier01/parts-manifest.json',
        ROOT/'engineering/generated/r5-petal-form02/study.json',ROOT/'engineering/electronics/r5-cam-hardware01/budget.json']
    dump('study.json',dict(revision='R5-TWOCONTACT01',script_sha256=sha(__file__),input_hashes={str(p.relative_to(ROOT)):sha(p) for p in inp},
        decision='user accepts one opposed primary pair; positive synchronization priority',
        nominal_gravity='head minus Z; workpiece factor 2, known rotor gravity factor 1',
        contact_allocation='equal loads in one opposed upper/lower pair, centered resultant at local x65 y0',
        nominal_cases=nominal,scenario_count=len(cases),box_examples=pairs,
        point_contact_rank=rank,point_contact_singular_values=s.tolist(),point_contact_twist_residual=torque_res,
        finite_patch_model=patches,illustrative_patch_containment=patch_fit,
        polar_mean_radius_ratio=mean_r,manufacturing_release=False,
        exclusions=['finite loaded contact area and skin pressure','cylinder contact line/patch and friction measurements','dynamic motion while gripping','other gravity directions','rail or drive forces with friction','actual guide strength/contact stress','head carrier deformation','complete closed state','one-second hardware qualification']))
    print(json.dumps({'nominal_cases':nominal,'patch_fit':patch_fit,'scenarios':len(cases)},indent=2))

if __name__=='__main__':main()
