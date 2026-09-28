# SPDX-License-Identifier: CC-BY-NC-4.0
"""Seven-wheel cable centerline packaging candidate; NOT a physical transmission.

Original catalogue bounding cylinders and exact nominal circular centerlines.
No yokes, axle bearings, rail supports, rope eye solids or cable cut lengths.
"""
from pathlib import Path
import hashlib, itertools, json, math
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-route01'
CAT=ROOT/'engineering/electronics/r5-cable-hardware01/mechanical-interface.json'
DATA=json.loads(CAT.read_text())
RP=(DATA['pulleys']['SP3106']['root_diameter_mm']+.9652)/2
RS=(DATA['pulleys']['SP4125']['root_diameter_mm']+1.1938)/2
A=(1+math.sqrt(2))*RP
ZT=-25.; ZF=ZT-RP; ROOT_OFFSET=30.; X_SECOND=27.
PHI=np.radians([45,135,225,315])
NAMES=['UR','UL','LL','LR']
E=np.array([[math.cos(p),math.sin(p),0.] for p in PHI])

def wheel(c,axis,r,w):
    c=np.array(c);axis=np.array(axis)
    return cq.Solid.makeCylinder(r,w,cq.Vector(*(c-w/2*axis)),cq.Vector(*axis))

def configuration(R):
    R=np.array(R,dtype=float); pair=np.array([(R[0]+R[1])/2,(R[2]+R[3])/2])
    Z=-75.+pair-91.; zmean=-140.+np.mean(R)-91.
    wheels={}; routes=[]; anchors=[]
    for n,e in zip(NAMES,E):
        c=A*e+np.array([0,0,ZF]);axis=np.cross([0,0,1.],e)
        wheels['F_'+n]=wheel(c,axis,15.875,6.35)
    for k,y in enumerate([RP,-RP]):
        wheels['M_'+str(k)]=wheel([0,y,Z[k]],[0,1,0],15.875,6.35)
        i,j=([0,1] if k==0 else [3,2])  # right side first
        arcs=[]
        for idx in [i,j]:
            anchor=(R[idx]+ROOT_OFFSET)*E[idx]+np.array([0,0,ZT])
            center=A*E[idx]+np.array([0,0,ZF])
            # Horizontal inward -> downward; fixed wheel uses its inner quadrant.
            theta=np.linspace(0,math.pi/2,49)
            arc=np.array([center-RP*math.sin(t)*E[idx]+[0,0,RP*math.cos(t)] for t in theta])
            arcs.append(np.vstack([anchor,arc]));anchors.append(anchor)
        # Lower semicircle: right +X leg -> left -X leg, both at same fixed Y.
        theta=np.linspace(0,math.pi,97)
        low=np.array([[RP*math.cos(t),y,Z[k]-RP*math.sin(t)] for t in theta])
        points=np.vstack([arcs[0],low,arcs[1][::-1]])
        lengths=(R[i]+ROOT_OFFSET-A)+(R[j]+ROOT_OFFSET-A)+2*(ZF-Z[k])+2*math.pi*RP
        routes.append(dict(name='leaf_top' if k==0 else 'leaf_bottom',points=points,
                           exact_length_mm=lengths,diameter_mm=.9652,
                           own_wheels={'F_'+NAMES[i],'F_'+NAMES[j],'M_'+str(k)}))
    wheels['M_mean']=wheel([X_SECOND,0,zmean],[1,0,0],19.05,7.1374)
    theta=np.linspace(0,math.pi,97)
    low=np.array([[X_SECOND,RS*math.cos(t),zmean-RS*math.sin(t)] for t in theta])
    points=np.vstack([[X_SECOND,RS,Z[0]],low,[X_SECOND,-RS,Z[1]]])
    routes.append(dict(name='secondary',points=points,exact_length_mm=sum(Z)-2*zmean+math.pi*RS,
                       diameter_mm=1.1938,own_wheels={'M_mean'}))
    return dict(R=R,pair=pair,Z=Z,zmean=zmean,wheels=wheels,routes=routes,anchors=np.array(anchors))

def wire(points):
    return cq.Wire.makePolygon([cq.Vector(*p) for p in points],close=False)

def serial(x):
    if isinstance(x,np.ndarray):return x.tolist()
    if isinstance(x,np.generic):return x.item()
    raise TypeError(type(x))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    poses={
        'open':[91]*4, 'folded':[66]*4, 'minimum_50mm':[31]*4,
        'box_50x120':[31,66,31,66], 'maximum_pair_offset':[91,91,31,31]
    }
    tested=list(itertools.product([31.,91.],repeat=4))+list(poses.values())
    wheel_checks=[];wire_checks=[];rope_checks=[];lengths=[]
    for R in tested:
        conf=configuration(R); lengths.append([r['exact_length_mm'] for r in conf['routes']])
        for (n,a),(m,b) in itertools.combinations(conf['wheels'].items(),2):
            d=a.distance(b);v=a.intersect(b).Volume() if d<1e-7 else 0.
            assert v<1e-7,(R,n,m,v)
            wheel_checks.append(dict(R_mm=R,a=n,b=m,distance_mm=d,overlap_mm3=v))
        wires={}
        for r in conf['routes']:
            w=wire(r['points']);wires[r['name']]=w
            # The chord can depart from its exact circle by at most this sagitta.
            sag=max(RP,RS)*(1-math.cos(math.pi/192))
            for n,b in conf['wheels'].items():
                if n in r['own_wheels']:continue
                d=w.distance(b)-r['diameter_mm']/2-sag
                assert d>0,(R,r['name'],n,d)
                wire_checks.append(dict(R_mm=R,rope=r['name'],wheel=n,tube_gap_lower_mm=d))
        for (i,a),(j,b) in itertools.combinations(enumerate(conf['routes']),2):
            d=wires[a['name']].distance(wires[b['name']])-(a['diameter_mm']+b['diameter_mm'])/2-2*sag
            assert d>0,(R,a['name'],b['name'],d)
            rope_checks.append(dict(R_mm=R,a=a['name'],b=b['name'],tube_gap_lower_mm=d))
    assert np.max(np.ptp(lengths,axis=0))<1e-10
    summaries=[]
    for name,R in poses.items():
        c=configuration(R);assembly=cq.Assembly(name='R5_ROUTE01_'+name)
        for n,s in c['wheels'].items():assembly.add(s,name=n,color=cq.Color(.43,.51,.55))
        for r in c['routes']:assembly.add(wire(r['points']),name=r['name']+'_CENTERLINE',color=cq.Color(.9,.53,.15))
        for i,a in enumerate(c['anchors']):assembly.add(cq.Solid.makeSphere(1,cq.Vector(*a)),name='ANCHOR_POINT_'+str(i),color=cq.Color(.9,.2,.15))
        assembly.save(str(OUT/(name+'.step')))
        summaries.append(dict(name=name,R_mm=R,pair_centers_Z_mm=c['Z'],mean_center_Z_mm=c['zmean'],
                              rear_pulley_Z_mm=c['zmean']-19.05,exact_centerline_lengths_mm=[r['exact_length_mm'] for r in c['routes']]))
    # Analytic wheel-only separation certificate, no discretization over R.
    # Fixed/leaf: max leaf Z=-75, leaf top=-59.125; fixed bottom=ZF-15.875.
    continuous=dict(fixed_to_leaf_Z_gap_mm=(ZF-15.875)-(-75+15.875),
                    upper_lower_leaf_Y_gap_mm=2*RP-6.35,
                    mean_to_leaf_X_gap_mm=X_SECOND-7.1374/2-15.875,
                    fixed_to_mean_Z_gap_mm=(ZF-15.875)-(-140+19.05),
                    note='Fixed-fixed shapes are constant and tested exactly; all four other classes use plane separation.')
    assert min(v for v in continuous.values() if isinstance(v,float))>0
    # Changes to the old unsolidified pull point and a terminal planning check.
    term=dict(old_R_plus13_min_straight_mm=31+13-A,new_R_plus30_min_straight_mm=31+ROOT_OFFSET-A,
              leaf_eye_axis_to_far_sleeve_example_mm=22.112,
              new_leaf_remaining_straight_mm=31+ROOT_OFFSET-A-22.112,
              minimum_secondary_straight_mm=65-30.,
              secondary_eye_axis_to_far_sleeve_example_mm=28.676,
              secondary_remaining_straight_mm=65-30-28.676,
              note='Clear centerline length only; no tails, tolerances, eye solids, clamps, yokes or anchor load paths.')
    # These are force balance requirements, not qualified yoke designs.
    loads=dict(leaf_tension_N=50.,each_fixed_90deg_wheel_resultant_N=math.sqrt(2)*50,
               each_leaf_moving_wheel_resultant_N=100.,secondary_tension_N=100.,mean_input_force_N=200.,
               leaf_carriage_offset_moment_Nm=100*math.hypot(X_SECOND,RS-RP)/1000,
               radial_carrier_lug_moment_about_root_local_Y_Nm=50*(20-ZT)/1000,
               mean_input_stroke_mm=60.,all_pulley_mass_kg=None)
    report=dict(revision='R5-ROUTE01',status='Packaging comparison only; not selected architecture or manufacturing release',
                parameters=dict(leaf_pitch_radius_mm=RP,secondary_pitch_radius_mm=RS,fixed_center_radius_mm=A,
                                radial_rope_Z_mm=ZT,fixed_center_Z_mm=ZF,pullpoint_R_offset_mm=ROOT_OFFSET,
                                leaf_open_center_Z_mm=-75.,mean_open_center_Z_mm=-140.,mean_center_X_mm=X_SECOND),
                wheel_counts={'SP3106_fixed':4,'SP3106_moving':2,'SP4125_moving':1},
                ideal_constraints=['zA=-75+(R_UR+R_UL)/2-91','zB=-75+(R_LL+R_LR)/2-91','zC=-140+sum(R)/4-91'],
                poses=summaries,tests=dict(wheel_pairs=len(wheel_checks),rope_other_wheel=len(wire_checks),rope_pairs=len(rope_checks),
                   min_wheel_gap_mm=min(r['distance_mm'] for r in wheel_checks),min_rope_other_wheel_gap_mm=min(r['tube_gap_lower_mm'] for r in wire_checks),
                   min_rope_rope_gap_mm=min(r['tube_gap_lower_mm'] for r in rope_checks),length_variation_mm=np.ptp(lengths,axis=0)),
                wheel_only_continuous_certificate=continuous,termination_screen=term,load_path_requirements=loads,
                rearward_packaging_mm=219.05,existing_root_Z_mm=20.,existing_root_to_farthest_pulley_mm=239.05,
                sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CAT,ROOT/'engineering/generated/r5-carrier01/parts-manifest.json',Path(__file__)]},
                excluded=['moving yokes and guided supports','all seven axles/spacers/retainers','three moving carriage guide mechanisms',
                          'carrier foot pull-lug','palm and motor','returns and stops','camera/display/wiring','rope eyes/tails/guards','groove profile/tolerance/contact qualification'],
                cable_cut_lengths_mm=None,scope='Cable paths are centerlines. Wheel cylinders intentionally include grooves and bearing bore; own-rope wheel overlap is not evaluated. Independent R poses do not assert dynamically reachable states. No carrier-versus-route full assembly check.')
    (OUT/'study.json').write_text(json.dumps(report,indent=2,default=serial)+'\n')
    (OUT/'sample-checks.json').write_text(json.dumps(dict(wheels=wheel_checks,rope_wheel=wire_checks,ropes=rope_checks),indent=2,default=serial)+'\n')
    draw(report)
    print(json.dumps({'tests':report['tests'],'continuous':continuous,'term':term,'loads':loads},indent=2,default=serial))

def draw(report):
    fig,axs=plt.subplots(1,3,figsize=(16,9))
    colors=['#ac691e','#be852d','#277f89']
    for ax,(name,R) in zip(axs,[('OPEN',[91]*4),('BOX 50 x 120',[31,66,31,66]),('MINIMUM 50 mm',[31]*4)]):
        c=configuration(R)
        for r,col in zip(c['routes'],colors):ax.plot(r['points'][:,0],r['points'][:,2],color=col,lw=1.6)
        for k in range(2):ax.add_patch(Circle((0,c['Z'][k]),15.875,facecolor='#536770',alpha=.22,edgecolor='#253941'))
        ax.add_patch(Rectangle((X_SECOND-3.5687,c['zmean']-19.05),7.1374,38.1,facecolor='#277f89',alpha=.25))
        ax.axhline(0,color='#81909a',ls=':',lw=1);ax.axhline(-219.05,color='#ad5738',ls='--',lw=.8)
        ax.set(xlim=(-110,110),ylim=(-231,18),xlabel='Head X [mm]',ylabel='Head Z [mm]',title=name)
        ax.set_aspect('equal');ax.grid(alpha=.15)
    fig.suptitle('R5 / seven-wheel differential route: nominal side projections',fontsize=20,y=.97)
    fig.text(.04,.88,'Brown: two leaf loops. Teal: secondary loop. Shaded cylinders: catalogue bounds. Y-separated wheels overlap in this projection.',fontsize=10)
    fig.text(.04,.15,'SP3106 x 6 + SP4125 x 1. Cable pitch radii 13.983 / 16.472 mm. One mean input with 60 mm travel.',fontsize=11)
    fig.text(.04,.11,'Rear pulley reaches Z -219.05 mm: 239.05 mm behind the existing root plane. No motor, support frame or return hardware included.',fontsize=11,color='#974523')
    fig.text(.04,.07,'This bulky branch is a packaging comparison. Centerlines are not cut lengths; anchor eyes, supports, rails and whole-head clearance remain unbuilt.',fontsize=10)
    fig.text(.04,.025,'Odradek / Auromix / CC BY-NC 4.0 / original nominal geometry / not a manufacturing drawing or 1-second cycle qualification',fontsize=9,color='#637480')
    fig.subplots_adjust(left=.06,right=.98,bottom=.21,top=.85,wspace=.28)
    fig.savefig(OUT/'route-comparison.png',dpi=170);fig.savefig(OUT/'route-comparison.svg');plt.close(fig)

if __name__=='__main__':main()
