#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""One positive axial spider/four rods; original candidate geometry, no drive release."""
from pathlib import Path
import argparse, csv, hashlib, itertools, json, math
import numpy as np
import cadquery as cq
from scipy.integrate import cumulative_trapezoid
from r5_petal_form02 import box, common, bbox, vol
from r5_carrier01 import cyl, union, azimuth, posed, petal, qR, FINGERS
from r5_passive02 import coeff, command
from head_mass04_study import geometry_properties

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-sync01'
P=dict(rod_length_mm=100.,inner_pin_radius_mm=33.,outer_pin_radial_offset_mm=30.,outer_pin_z_mm=-34.,
       radial_range_mm=[31.,91.],rod_width_mm=12.,rod_thickness_mm=6.,pin_nominal_D_mm=4.,pin_hole_D_mm=4.3,
       clevis_inner_halfwidth_mm=4.2,clevis_outer_halfwidth_mm=8.2,spider_hub_outer_radius_mm=16.,
       spider_central_clearance_D_mm=12.,spider_plate_z_mm=[-18.,-12.],assumed_density_kg_m3=2700.)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,(np.integer,np.floating,np.bool_)):return x.item()
    raise TypeError(type(x))
def dump(n,d):(OUT/n).write_text(json.dumps(d,indent=2,default=serial,ensure_ascii=False)+'\n')
def hR(R):return np.sqrt(100.**2-(np.asarray(R)-3.)**2)
def broad(a,b):
    ba,bb=bbox(a),bbox(b)
    return bool(np.all(ba[0]<=bb[1]+1e-7) and np.all(bb[0]<=ba[1]+1e-7))
def measure(s):
    p=geometry_properties(s);m=p['volume_mm3']*2700e-9
    return dict(mass_kg=m,volume_mm3=p['volume_mm3'],COM_mm=p['com_m']*1000,inertia_COM_kg_m2=p['inertia_per_mass_m2']*m)

def build():
    # Flat rod along local X; tangent pin axis Y. Both eye ends are identical.
    rod=union([box(0,100,-3,3,-6,6),cyl(6,-3,3,x=0),cyl(6,-3,3,x=100)])
    for x in [0,100]:rod=rod.cut(cyl(2.15,-4,4,x=x))
    # Four-spoke carrier leaves the +/-Y camera/cable sectors open; not an annulus.
    spider=cyl(16,-18,-12,axis='z').cut(cyl(6,-19,-11,axis='z'))
    for phi in [45,135,225,315]:
        spoke=box(10,41,-8.2,8.2,-18,-12)
        for sign in [-1,1]:
            a,b=(4.2,8.2) if sign==1 else (-8.2,-4.2)
            ear=union([cyl(8,a,b,x=33),box(25,41,a,b,-15,0)]).cut(cyl(2.15,a-.1,b+.1,x=33))
            spoke=spoke.fuse(ear)
        spider=spider.fuse(azimuth(spoke,phi))
    spider=spider.clean()
    # Mount below CARRIER foot. Four candidate tapped M4 locations consume the
    # existing D4.5 interface; taps are nominal D3.3 drill cylinders, no thread CAD.
    lug=box(8,35,-12,12,-22,-14)
    for x,y in itertools.product([13,30],[-8,8]):lug=lug.cut(cyl(1.65,-22.1,-13.9,axis='z',x=x,y=y))
    for sign in [-1,1]:
        a,b=(4.2,8.2) if sign==1 else (-8.2,-4.2)
        ear=union([cyl(8,a,b,x=30,z=-34),box(22,35,a,b,-34,-20)]).cut(cyl(2.15,a-.1,b+.1,x=30,z=-34))
        lug=lug.fuse(ear)
    # Re-cut after adding ears so their small overlap cannot refill tap drills.
    for x,y in itertools.product([13,30],[-8,8]):lug=lug.cut(cyl(1.65,-22.1,-13.9,axis='z',x=x,y=y))
    lug=lug.clean()
    # Pins only locate bearing axes. Heads/retention/fits have not been selected.
    pin=cyl(2,-8.2,8.2)
    for s in [rod,spider,lug,pin]:assert s.isValid() and len(s.Solids())==1
    return dict(rod=rod,spider=spider,lug=lug,pin=pin)

def sync_parts(shapes,R):
    h=float(hR(R));alpha=math.degrees(math.atan2(h,R-3));Qz=-34-h
    data={'spider':shapes['spider'].translate((0,0,Qz))}
    for f,(_,_,phi) in FINGERS.items():
        data[f+'_rod']=azimuth(shapes['rod'].rotate((0,0,0),(0,1,0),-alpha).translate((33,0,Qz)),phi)
        data[f+'_lug']=azimuth(shapes['lug'].translate((R,0,0)),phi)
        for name,r,z in [('inner_pin',33,Qz),('outer_pin',R+30,-34)]:
            data[f+'_'+name]=azimuth(shapes['pin'].translate((r,0,z)),phi)
    return data

def frozen_carrier():
    d=json.loads((ROOT/'engineering/generated/r5-carrier01/parts-manifest.json').read_text())
    return [dict(r,shape=cq.importers.importStep(str(ROOT/'engineering/generated/r5-carrier01'/r['source_step'])).val()) for r in d['parts']]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    shapes=build();mass={n:measure(s) for n,s in shapes.items() if n!='pin'}
    for n,s in shapes.items():cq.exporters.export(s,str(OUT/(n+'.step')))
    import trimesh
    meshcheck={}
    for n in ['rod','spider','lug']:
        stl=OUT/(n+'.stl');cq.exporters.export(shapes[n],str(stl),tolerance=.03,angularTolerance=.08)
        mesh=trimesh.load(stl,force='mesh',process=True)
        err=abs(mesh.volume-vol(shapes[n]))/vol(shapes[n])
        assert mesh.is_watertight and mesh.is_winding_consistent and err<.01
        meshcheck[n]=dict(watertight=True,winding_consistent=True,relative_volume_error=err)
    # Nominal axial motion and mechanical advantage; correct branch is positive
    # radial separation, so no crossed-link inverse solution is admitted.
    r=np.linspace(.031,.091,6001);L=.1;d=r-.003;h=np.sqrt(L*L-d*d);hp=-d/h;hpp=-L*L/h**3
    assert min(d)>0 and min(h)>0
    mr=mass['rod']['mass_kg'];Ir=mass['rod']['inertia_COM_kg_m2'][1,1]
    ms=mass['spider']['mass_kg'];ml=mass['lug']['mass_kg']
    def terms(R):
        s=.091-R;d=R-.003;h=np.sqrt(.1**2-d*d);hp=-d/h;hpp=-.1**2/h**3
        hu,hpu,gu=coeff(s,'upper');hl,hpl,gl=coeff(s,'lower')
        H=2*(hu+hl)+4*ml+4*(mr*(.25+.25*hp**2)+Ir/h**2)+ms*hp**2
        Hp=-2*(hpu+hpl)+4*(.5*mr*hp*hpp-2*Ir*hp/h**3)+2*ms*hp*hpp
        G=-2*(gu+gl)-2*mr*9.80665*hp-ms*9.80665*hp
        return h,hp,hpp,H,Hp,G
    times=np.linspace(0,1,20001);arr=[]
    for t in times:
        s,sv,sa=command(t if t<=.5 else t-.5,'opening' if t<=.5 else 'closing')
        R=.091-s;v=-sv;a=-sa;h,hp,hpp,H,Hp,G=terms(R)
        F=H*a+.5*Hp*v*v+G;hd=hp*v;hdd=hp*a+hpp*v*v
        arr.append([t,R,h,v,a,hd,hdd,F,F/hp,.5*H*v*v,G])
    ar=np.array(arr)
    work=cumulative_trapezoid(ar[:,7]*ar[:,3],times,initial=0)
    potential=cumulative_trapezoid(ar[:,10]*ar[:,3],times,initial=0)
    energy_err=max(abs(work-(ar[:,9]-ar[0,9]+potential)))
    fd_h=max(abs(np.gradient(ar[:,2],times)[3:-3]-ar[3:-3,5]))
    assert energy_err<1e-4 and fd_h<1e-5
    # Head minusZ holds, one upper/lower opposed pair. No guessed friction efficiency.
    holds=[]
    for W in [50,80,120]:
        R=(W/2+6)/1000;h,hp,*_=terms(R);N=2*2*9.80665/(2*.4)
        axial=2*N/abs(hp)
        holds.append(dict(width_mm=W,R_mm=1000*R,h_mm=1000*h,normal_each_N=N,
            ideal_input_h_force_N=axial,rod_tension_each_active_N=N*.1/(R-.003),
            assumed_4mm_screw_ideal_torque_Nm=axial*.004/(2*math.pi),
            assumed_2to1_reduction_ideal_motor_torque_Nm=axial*.004/(4*math.pi),
            scope='contact normal load only; missing gravity, all friction, screw/shaft/motor qualification'))
    # This section only creates a reviewable subassembly. It does not fabricate
    # rails or silently convert conceptual pins into selected fasteners.
    rows=frozen_carrier();collision=[];poses=[31.,46.,66.,71.,76.,81.,86.,91.]
    from r5_vision01 import camera_primitives,camera_pose
    fixed_camera={f'{sign}_{name}':camera_pose(s,sign,50,-35) for sign in [-1,1] for name,s in camera_primitives().items()}
    for R in poses:
        new=sync_parts(shapes,R);old={}
        for f,(kind,hand,phi) in FINGERS.items():
            old.update({f+'_'+n:s for n,s in posed(rows,R,qR(R),phi).items()})
            from r5_carrier01 import pose
            old.update({f+'_petal_'+n:pose(s,R,qR(R),phi) for n,s in petal(kind,hand).items()})
        collisions=[];queries=0;minimum_cam=1e9
        for a,b in itertools.combinations(new,2):
            if not broad(new[a],new[b]):continue
            queries+=1;v=common(new[a],new[b])
            if v>1e-5:collisions.append(dict(a=a,b=b,overlap_mm3=v))
        for a,s in new.items():
            for b,t in old.items():
                if not broad(s,t):continue
                queries+=1;v=common(s,t)
                if v>1e-5:collisions.append(dict(a=a,b=b,overlap_mm3=v))
            for b,t in fixed_camera.items():
                # The FAKRA is merely a planning volume, not a mated cable.
                minimum_cam=min(minimum_cam,s.distance(t))
                if not broad(s,t):continue
                queries+=1;v=common(s,t)
                if v>1e-5:collisions.append(dict(a=a,b='camera_'+b,overlap_mm3=v))
        collision.append(dict(R_mm=R,exact_overlap_queries=queries,overlaps=collisions,minimum_distance_camera_including_unmated_reservation_mm=minimum_cam))
        if R in [31.,66.,91.]:
            ass=cq.Assembly(name=f'R5_SYNC01_R{R:g}')
            for n,s in new.items():ass.add(s,name=n)
            ass.save(str(OUT/f'sync-subassembly-R{R:g}.step'))
    with (OUT/'cycle.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['t_s','R_m','h_m','Rdot_m_s','Rddot_m_s2','hdot_m_s','hddot_m_s2','F_R_N','F_h_N','kinetic_J','dU_dR_N']);w.writerows(ar[::20])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.hashsalt':'R5-SYNC01','svg.fonttype':'none'})
    fig,axs=plt.subplots(1,3,figsize=(14,5))
    for R,color in [(31,'#315b69'),(66,'#be8c3b'),(91,'#80a6ae')]:
        hv=float(hR(R));axs[0].plot([33,R+30],[-34-hv,-34],'-o',color=color,label=f'R = {R} mm')
        axs[0].plot([0,33],[-34-hv-15]*2,color=color,lw=5)
    axs[0].set(xlim=(-10,140),ylim=(-160,-10),xlabel='Branch radial coordinate [mm]',ylabel='Head Z [mm]',title='One axial spider, four positive rods');axs[0].set_aspect('equal');axs[0].legend(fontsize=8)
    axs[1].plot(times,ar[:,1]*1000,label='radial R');axs[1].plot(times,ar[:,2]*1000,label='axial separation h')
    axs[1].set(xlabel='Time [s]',ylabel='Coordinate [mm]',title='Prescribed 1 s return / candidate only');axs[1].legend(fontsize=8)
    axs[2].plot(times,ar[:,8],label='ideal axial generalized force')
    axs[2].set(xlabel='Time [s]',ylabel='Force [N]',title='Known mechanical masses / no object')
    for ax in axs:ax.grid(alpha=.2)
    fig.suptitle('R5-SYNC01 / common input replaces three passive differential coordinates',fontsize=15)
    fig.text(.025,.02,'Original rod/spider/lug candidate; rails, nut, bearings, drive, retention and full closure are not designed here.',fontsize=9)
    fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(OUT/'synchronous-linkage.png',dpi=170);fig.savefig(OUT/'synchronous-linkage.svg',metadata={'Date':None});plt.close(fig)
    from matplotlib.collections import PolyCollection
    from matplotlib.backends.backend_pdf import PdfPages
    def silhouette(ax,s,axes):
        verts,tri=s.tessellate(.07,.08);xy=np.array([v.toTuple() for v in verts])[np.array(tri)][:,:,axes]
        ax.add_collection(PolyCollection(xy,facecolors='#b8cdd1',edgecolors='none',rasterized=True));ax.autoscale_view();ax.set_aspect('equal');ax.grid(alpha=.18)
    with PdfPages(OUT/'R5-SYNC01-nominal-review-dimensions.pdf') as pdf:
        fig,axes=plt.subplots(1,2,figsize=(11.7,8.3));silhouette(axes[0],shapes['rod'],[0,2]);silhouette(axes[1],shapes['lug'],[0,2])
        axes[0].set(title='ROD / radial-Z view',xlabel='Local X [mm]',ylabel='Local Z [mm]',ylim=(-30,30))
        axes[1].set(title='FOOT LUG / radial-Z view',xlabel='Carrier local X [mm]',ylabel='Head Z [mm]')
        fig.suptitle('R5-SYNC01 / nominal links and root attachment',x=.055,ha='left',fontsize=17)
        fig.text(.055,.23,'ROD: pin centers 100; end R6; Y thickness 6; two D4.3 through holes along Y.\nLUG: base X8..35 / Y +/-12 / head Z-22..-14; four nominal M4 tap drills D3.3 at X13/30,Y+/-8.\nLug pin axis [30,0,-34]; ear inner Y +/-4.2, outer +/-8.2; D4.3 through pin bores.\nCommon alloy density 2700 kg/m3 is a mass assumption. No pin retention, bearing fits, tap class or preload release.',fontsize=10,linespacing=1.6)
        fig.text(.055,.06,'Auromix / CC BY-NC 4.0 | geometry-review sheet; NOT a controlled manufacturing drawing | 1/2',fontsize=9)
        fig.subplots_adjust(left=.08,right=.94,top=.81,bottom=.38,wspace=.30);pdf.savefig(fig);plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(11.7,8.3));silhouette(axes[0],shapes['spider'],[0,1]);silhouette(axes[1],sync_parts(shapes,66)['spider'],[0,2])
        axes[0].set(title='SPIDER / front view',xlabel='Head X [mm]',ylabel='Head Y [mm]')
        axes[1].set(title='SPIDER / side at R66',xlabel='Head X [mm]',ylabel='Head Z [mm]')
        fig.suptitle('R5-SYNC01 / shared axial spider',x=.055,ha='left',fontsize=17)
        fig.text(.055,.23,'Four pin axes: radius33 at azimuth45/135/225/315; local pin Z0; D4.3 through tangent bores.\nSpoke plate: local Z-18..-12; central hub OD32 / provisional D12 clearance.\nThis hub is NOT the selected KSS nut interface; larger flange, bearing/anti-rotation, shaft and mount still need design.\nR=3+sqrt(100^2-h^2), h47.49737..96; outer pin Z-34; spider pin plane Z=-34-h [mm].',fontsize=10,linespacing=1.6)
        fig.text(.055,.06,'Auromix / CC BY-NC 4.0 | geometry-review sheet; NOT a controlled manufacturing drawing | 2/2',fontsize=9)
        fig.subplots_adjust(left=.08,right=.94,top=.81,bottom=.38,wspace=.30);pdf.savefig(fig);plt.close(fig)
    import ezdxf
    dx=ezdxf.new('R2018');dx.units=4;msd=dx.modelspace()
    msd.add_line((0,6),(100,6));msd.add_line((0,-6),(100,-6))
    msd.add_arc((0,0),6,90,270);msd.add_arc((100,0),6,-90,90)
    for x in [0,100]:msd.add_circle((x,0),2.15)
    dx.saveas(OUT/'rod-side-profile-mm.dxf')
    dyn=dict(peak_radial_speed_m_s=float(max(abs(ar[:,3]))),peak_axial_speed_m_s=float(max(abs(ar[:,5]))),
        peak_axial_acceleration_m_s2=float(max(abs(ar[:,6]))),axial_force_range_N=[float(min(ar[:,8])),float(max(ar[:,8]))],
        work_energy_residual_J=float(energy_err),axial_velocity_FD_max_error_m_s=float(fd_h),
        example_4mm_lead_2to1_peak_motor_rpm=float(max(abs(ar[:,5]))/.004*60*2),
        scope='positive rigid synchronization, inherited known rotor model; no motor/screw/pin/rail/support mass or losses')
    inputs=[ROOT/'engineering/generated/r5-carrier01/parts-manifest.json',ROOT/'engineering/r5_passive02.py',ROOT/'engineering/r5_vision01.py',ROOT/'engineering/generated/r5-petal-form02/study.json']
    dump('study.json',dict(revision='R5-SYNC01',script_sha256=sha(__file__),parameters=P,input_hashes={str(p.relative_to(ROOT)):sha(p) for p in inputs},
        original_part_mass=mass,known_added_metal_subtotal_kg=ms+4*mr+4*ml,STL_checks=meshcheck,
        h_range_mm=[float(min(hR([31,91]))),float(max(hR([31,91])))],axial_stroke_mm=float(hR(31)-hR(91)),
        collision_samples=collision,hold_conditions=holds,no_load_cycle=dyn,manufacturing_release=False,
        status='geometry and kinematics candidate only; inspect collision rows before integration',
        exclusions=['actual motor/screw and bearings','spider guide/anti-rotation and common fixed palm','pin retention and bearing fits','M4 complete thread and fixation capacity','loaded root cam capacity','full optical/cable integration','joint tolerances and elastic load sharing','full closed exterior']))
    print(json.dumps({'mass':ms+4*mr+4*ml,'dynamics':dyn,'collision_counts':[len(x['overlaps']) for x in collision]},indent=2))

if __name__=='__main__':main()
