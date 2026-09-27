#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Extra mass, assembly-contact and independent-root QA for support03. No baseline edits."""
import hashlib,itertools,json,math
import numpy as np
import cadquery as cq
import gripper_root_support_study as st
ROOT,OUT=st.ROOT,st.OUT

def contacts(roots):
    pairs=[('keyed_hub_lower_fork','metal_blade_with_narrow_tongue'),('removable_upper_fork','metal_blade_with_narrow_tongue'),
           ('parallel_key_3x3x8','keyed_hub_lower_fork'),('parallel_key_3x3x8','output_tenon_D10'),
           ('end_washer_D18','keyed_hub_lower_fork'),('shoulder_spacer','keyed_hub_lower_fork')]
    rows=[]
    for a,b in pairs:
        rows.append(dict(a=a,b=b,minimum_distance_mm=roots[a].distance(roots[b]),positive_intersection_mm3=roots[a].intersect(roots[b]).Volume()))
    unintended=[]
    for (a,sa),(b,sb) in itertools.combinations(roots.items(),2):
        if st.gap_bounds(st.bb(sa),st.bb(sb))>1e-5:continue
        vol=sa.intersect(sb).Volume()
        if vol>1e-5:unintended.append(dict(a=a,b=b,intersection_mm3=vol))
    return dict(designed_contact_pairs=rows,all_intra_root_positive_intersections=unintended,new_root_positive_intersections=[x for x in unintended if not ('LED_window' in x['a'] and 'original_wedge' in x['b'])],inherited_distal_placeholder_intersections=[x for x in unintended if 'LED_window' in x['a'] and 'original_wedge' in x['b']],
        contact_area_reference_mm2=dict(each_cheek_to_tongue=180-2*math.pi*1.7**2,shaft_shoulder_to_spacer=math.pi*(12**2-10.1**2)/4,
            spacer_to_hub=math.pi*(16**2-10.1**2)/4),
        note='CAD zero distance plus zero overlap confirms nominal contact, not contact pressure/preload. Contact areas exclude holes where stated; edge radii and tolerances pending.')

def mass(parts,fixed,roots,mats,layout):
    baseline=st.prev.mass_budget(parts);lookup={r['item']:r for r in baseline['mass_locations']};entries=[]
    custom={p['name']:p for p in parts if p['kind'] in baseline['custom_nominal_gross_by_kind_g']}
    steel=['shaft','shaft_shoulder','shaft_thread','spacer','gear_retention','bolt_allowance']
    for name,row in lookup.items():
        if name in custom:
            if name not in fixed:continue
            s=fixed[name];rho=.00785 if custom[name]['kind'] in steel else .0027
            entries.append(dict(item=name,mass_g=s.Volume()*rho,center_head_mm=list(s.Center().toTuple()),basis='current native cut geometry x density'))
        else:entries.append(row)
    for i,f in enumerate(layout['head']['fingers']):
        for n,s in roots[i].items():
            if n in ['metal_blade_with_narrow_tongue','LED_window_placeholder','original_wedge_pad_0','original_wedge_pad_1']:continue
            ss=st.place(s,f,st.SIGNS[i]);entries.append(dict(item=f['id']+'_'+n,mass_g=s.Volume()*st.DENSITY[mats[i][n]],center_head_mm=list(ss.Center().toTuple()),basis='native geometry x density; nominal fastener envelope mass, no measured value'))
    total=sum(e['mass_g'] for e in entries);com=sum(e['mass_g']*np.array(e['center_head_mm']) for e in entries)/total
    blades=sum(r['metal_blade_with_narrow_tongue'].Volume()*.0027 for r in roots)
    added=[dict(item='four current metal blades, measured CAD volume x 2700 kg/m3',low_g=blades,high_g=blades),
        dict(item='soft pads, adhesives and pad screws (supersede old unresolved pad proxy masses)',low_g=25,high_g=60),
        dict(item='unmodeled gear keys, fixed-carrier screws, shims; root hardware now counted explicitly',low_g=20,high_g=70),
        dict(item='factory motor combination adapter',low_g=20,high_g=50),
        dict(item='LEDs, diffusers, central display, thermal spreaders',low_g=100,high_g=220),
        dict(item='two cameras',low_g=72,high_g=72),
        dict(item='camera mounts and on-head boards',low_g=80,high_g=160),
        dict(item='covers, armor, lubricant, seals',low_g=180,high_g=330),
        dict(item='rear carrier and detachable wrist',low_g=150,high_g=300),
        dict(item='local connectors/wiring',low_g=60,high_g=120)]
    return dict(drive_root_hardware_g=total,drive_CoM_head_mm=com.tolist(),metal_blades_g=blades,
        baseline_drive_g=baseline['drive_nominal_gross_estimate_g'],drive_delta_g=total-baseline['drive_nominal_gross_estimate_g'],
        complete_head_budget_g=[total+sum(r[k] for r in added) for k in ['low_g','high_g']],allowances=added,locations=entries,
        exclusions='holds/brakes, measured factory combination, final fixed mounting fasteners, design optimization; LED/pad volume proxies are excluded from physical mass and replaced with allowances')

def independent_roots(layout,roots):
    # Entire new root lies in a sphere centered at its preserved hinge. Rotating it
    # around that hinge cannot leave this sphere, regardless of another finger q.
    rr=[]
    for i,f in enumerate(layout['head']['fingers']):
        near={n:s for n,s in roots[i].items() if n not in ['metal_blade_with_narrow_tongue','LED_window_placeholder','original_wedge_pad_0','original_wedge_pad_1']}
        near['tongue']=roots[i]['metal_blade_with_narrow_tongue'].intersect(st.B(-20,25,-100,100,-20,20))
        R=max(np.linalg.norm(c) for s in near.values() for c in itertools.product(*zip(*st.bb(s))))
        phi=math.radians(f['phi_deg']);a=np.array([70*math.cos(phi),70*math.sin(phi),f['root_z_mm']]);rr.append((R,a))
    pair=[dict(a=layout['head']['fingers'][i]['id'],b=layout['head']['fingers'][j]['id'],sphere_gap_mm=float(np.linalg.norm(rr[i][1]-rr[j][1])-rr[i][0]-rr[j][0])) for i,j in itertools.combinations(range(4),2)]
    rd=[]
    for i,(rad,anchor) in enumerate(rr):
        point=cq.Vertex.makeVertex(*anchor)
        for j,f in enumerate(layout['head']['fingers']):
            if i==j:continue
            distal=st.comp([s.intersect(st.B(25,200,-100,100,-20,20)) for n,s in roots[j].items() if n in ['metal_blade_with_narrow_tongue','LED_window_placeholder','original_wedge_pad_0','original_wedge_pad_1']])
            R=max(math.hypot(x,z) for x,y,z in itertools.product(*zip(*st.bb(distal))))
            q=np.arange(0,f['closure_study_deg']+.01,2).tolist()
            if q[-1]!=f['closure_study_deg']:q.append(f['closure_study_deg'])
            distances=[st.place(distal,f,st.SIGNS[j],a).distance(point)-rad for a in q]
            bound=min(distances)-2*R*math.sin(math.radians(2)/4)
            rd.append(dict(root=layout['head']['fingers'][i]['id'],distal=f['id'],minimum_sample_gap_mm=min(distances),independent_continuous_lower_bound_mm=bound,passed=bound>0))
    return dict(root_sphere_radii_mm=[x[0] for x in rr],root_root_pairs=pair,root_other_distal_pairs=rd,
        all_passed=all(x['sphere_gap_mm']>0 for x in pair) and all(x['passed'] for x in rd),
        scope='all independent q in upper 0..114 lower 0..126 for any new root vs other roots/distals; unchanged distal vs distal separation remains the baseline geometric question')

def assembly_tools(report):
    arr=[]
    for r in report['tool_approach']:
        own=[p for p in r['intersections'] if p['part'].startswith(r['finger']+'_')]
        arr.append(dict(finger=r['finger'],tool=r['tool'],in_full_head=r['passes'],on_separate_module=not own,
            required_sequence='preassemble upper hub before lower modules; remove lower module for upper hub replacement' if not r['passes'] else 'external approach clear in modeled q0 head'))
    return arr

def plots(roots):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    colors={'keyed_hub_lower_fork':'#9ab1bb','removable_upper_fork':'#708d9e','metal_blade_with_narrow_tongue':'#637e8e','LED_window_placeholder':'#f4c365','parallel_key_3x3x8':'#d78948','output_tenon_D10':'#9faaa8','nut_keeper_sheet':'#c38d59'}
    def draw(ax,p,explode=False):
        allpolys=[];allcolors=[]
        for n,s in p.items():
            if n.startswith('original_wedge'):continue
            # Labeled section view: actual blade and LED cropped only for illustration.
            if n in ['metal_blade_with_narrow_tongue','LED_window_placeholder']:s=s.intersect(st.B(-20,40,-30,30,-20,30))
            off=(0,0,0)
            if explode:
                if n=='removable_upper_fork':off=(0,0,20)
                elif n in ['metal_blade_with_narrow_tongue','LED_window_placeholder']:off=(0,0,10)
                elif n.startswith('M3x20'):off=(0,0,26)
                elif n.startswith('M3_hexnut') or n.startswith('M3_washer'):off=(0,0,-10)
                elif n in ['nut_keeper_sheet'] or n.startswith('M2x6'):off=(0,0,-18)
                elif n in ['end_washer_D18','M4x10_end_screw_envelope']:off=(0,-18,0)
                elif n=='parallel_key_3x3x8':off=(-10,0,0)
                elif n=='output_tenon_D10':off=(0,22,0)
            verts,faces=s.translate(off).tessellate(.25);v=np.array([x.toTuple() for x in verts]);polys=v[np.array(faces)]
            # Small coplanar triangles avoid mplot3d painter-depth artifacts over the thin LED.
            refined=[];todo=list(polys)
            while todo:
                t=todo.pop()
                if max(np.linalg.norm(t[0]-t[1]),np.linalg.norm(t[1]-t[2]),np.linalg.norm(t[2]-t[0]))<=2:
                    refined.append(t);continue
                a,b,c=t;ab=(a+b)/2;bc=(b+c)/2;ca=(c+a)/2
                todo.extend([np.array([a,ab,ca]),np.array([ab,b,bc]),np.array([ca,bc,c]),np.array([ab,bc,ca])])
            allpolys.extend(refined);allcolors.extend([colors.get(n,'#bac3c6')]*len(refined))
        pc=Poly3DCollection(allpolys,facecolors=allcolors,edgecolors=allcolors,linewidths=0,alpha=1,shade=True,lightsource=matplotlib.colors.LightSource(azdeg=300,altdeg=40));ax.add_collection3d(pc)
        ax.set_xlim(-18,44);ax.set_ylim(-35,30);ax.set_zlim(-30,44);ax.set_box_aspect((62,65,74));ax.view_init(elev=24,azim=-58);ax.set_xlabel('Blade x / mm');ax.set_ylabel('Tangent u / mm');ax.set_zlabel('Light normal h / mm');ax.grid(False)
    fig=plt.figure(figsize=(14,8));a=fig.add_subplot(121,projection='3d');b=fig.add_subplot(122,projection='3d');draw(a,roots);draw(b,roots,True)
    a.set_title('Assembled near-root detail',pad=16);b.set_title('Exploded: keyed hub, tongue, cheek, captive nuts',pad=16)
    fig.suptitle('R4-support-03 | 18 mm narrow fork; removable metal light carrier',fontsize=15,y=.97)
    fig.text(.035,.055,'Blade / light shown only through x = 40 mm; full parts retained in STEP. Near-root mating surfaces are modeled explicitly.\nIllustration of nominal assembly; threads, fits, fillets, preload and payload rating are not released. CC BY-NC 4.0',fontsize=10)
    fig.subplots_adjust(top=.85,bottom=.14,left=.02,right=.97,wspace=.05);fig.savefig(OUT/'root-interface.png',dpi=160);plt.close(fig)

def main():
    report=json.loads((OUT/'R4-support-03.json').read_text());raw=(ROOT/'engineering/parameters/r4-layout.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==st.EXPECTED
    l=json.loads(raw);p,rows,fixed,savings=st.baseline(l);rr=[st.root_parts(f) for f in l['head']['fingers']];roots=[x[0] for x in rr];mats=[x[1] for x in rr]
    r=dict(revision='R4-support-03',mass=mass(p,fixed,roots,mats,l),contacts=contacts(roots[0]),assembly_access=assembly_tools(report),independent_root_motion=independent_roots(l,roots))
    (OUT/'root-interface-details.json').write_text(json.dumps(r,indent=2,default=lambda x:x.item())+'\n');plots(roots[0])
    print(json.dumps(dict(mass={k:v for k,v in r['mass'].items() if k not in ['locations','allowances']},contacts=r['contacts'],rootmotion=r['independent_root_motion']),indent=2,default=lambda x:x.item()))
if __name__=='__main__':main()
