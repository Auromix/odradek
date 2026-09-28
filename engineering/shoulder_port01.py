#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Measure RH25-B rear apertures against RAISE02; export only our trimmed blocks.

Vendor STEP is a command-line input and is not copied/exported. Aperture sweeps
are access probes, not registered connector bodies or connector qualification.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
import numpy as np
import cadquery as cq
from build_layout import frame, moved
from build_link56_study import face_contact
from studies.link_interface_tools import check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'engineering/generated/shoulder-port01'
REV = 'SHOULDER-PORT01'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def volume(s):
    return sum(abs(a.Volume()) for a in s.Solids())


def bounds(s):
    b = s.BoundingBox()
    return [[b.xmin, b.ymin, b.zmin], [b.xmax, b.ymax, b.zmax]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--vendor-step', type=Path, required=True)
    ap.add_argument('--raise-dir', type=Path, default=ROOT/'engineering/generated/shoulder-raise02')
    ap.add_argument('--sources', type=Path, default=ROOT/'docs/engineering/sources/shoulder-port01.json')
    ap.add_argument('--out', type=Path, default=OUT)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    ip = ROOT/'docs/engineering/sources/rh-interface-extraction.json'
    it = next(x for x in json.loads(ip.read_text())['models'] if x['id']=='RH25-B')['unified_joint_interface']
    T_vendor_joint = np.array(it['T_world_from_joint_mm'])
    T2 = frame([0, 0, 205], [0, 1, 0])
    vendor = moved(cq.importers.importStep(str(args.vendor_step)).val(), np.linalg.inv(T_vendor_joint))
    assert len(vendor.Solids()) == 42
    tail = vendor.Solids()[3]
    faces = [f for f in tail.Faces() if len(f.Wires())==9 and abs(f.Center().z+103.2)<1e-5]
    assert len(faces)==1, 'Unexpected vendor version: rear planar face not identified.'
    rearface = faces[0]
    wires = rearface.Wires()
    expected = [70.3092915845604, 245.851769380642, 81.5092915845663, 2.83528736986483]
    paths = [args.raise_dir/'part-placements.json', args.raise_dir/'connections.json', args.raise_dir/'L12_rear_fork.step']
    blocks = {}
    for i in range(1,9):
        p=args.raise_dir/f'STEEL_THREAD_BLOCK_{i}.step'; paths.append(p)
        blocks[i] = moved(cq.importers.importStep(str(p)).val(), np.linalg.inv(T2))
    rear = moved(cq.importers.importStep(str(args.raise_dir/'L12_rear_fork.step')).val(), np.linalg.inv(T2))
    helpers=[ROOT/'engineering'/n for n in ['build_layout.py','build_link56_study.py','studies/link_interface_tools.py']]
    source_hashes = {str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),*helpers,ip,args.sources,*paths]}
    vendor_hash=sha(args.vendor_step)
    assert vendor_hash=='d844bc7dfe5c398b0447ea0d93eef77b7cb1bdaa0dbabd603031482c1909f07e', 'Re-identify apertures for changed OEM STEP.'
    ports={}; sweeps={}; original_checks={}
    inference=['two EtherCAT ports, inferred from paired four-contact drawing contours',
               'two power and two CAN ports, inferred from combined stepped opening',
               'BAT and RES pair, inferred from paired two-contact drawing contours',
               'indicator aperture, inferred from product-manual LED illustration']
    for i in range(4):
        w=wires[i]; f=cq.Face.makeFromWires(w)
        assert abs(f.Area()-expected[i])<1e-5
        sw=cq.Solid.extrudeLinear(w,[],cq.Vector(0,0,-60)); sweeps[i]=sw
        ports[f'A{i}']=dict(wire_index=i,area_mm2=f.Area(),centroid_joint_mm=list(f.Center().toTuple()),
                            bbox_joint_mm=bounds(f),function_group_inference=inference[i],
                            registered_connector_frame=False, axial_probe_joint_z_mm=[-163.2,-103.2])
        for bid,b in blocks.items():
            original_checks[f'A{i}__BLOCK_{bid}']=check(sw,b,minimum=True)
        original_checks[f'A{i}__REAR_FORK']=check(sw,rear,minimum=True)
    modifications={}; candidates={}; export_checks={}
    for port,bid in [(2,1),(3,8)]:
        xy=it['fixed_through_holes']['points'][bid-1]['xy_mm']; a=math.degrees(math.atan2(xy[1],xy[0]))
        f=cq.Face.makeFromWires(wires[port]).rotate((0,0,0),(0,0,1),-a)
        b=blocks[bid]; local=b.rotate((0,0,0),(0,0,1),-a)
        # Half-space approximation completely covers the original block extent.
        cutter=cq.Workplane().box(200,200,50).translate((-62,0,-108)).val()
        new=local.cut(cutter).clean().rotate((0,0,0),(0,0,1),a)
        assert new.isValid() and len(new.Solids())==1
        assert volume(new.cut(b))<1e-5
        candidates[bid]=new
        o=[xy[0],xy[1],-104.5]
        oldc=face_contact(b,rear,o,[0,0,1]); newc=face_contact(new,rear,o,[0,0,1])
        for contact in [oldc,newc]:
            contact['origin_joint_mm']=contact.pop('origin_world_mm')
            contact['normal_joint']=contact.pop('normal_world')
        assert abs(oldc['shared_planar_face_area_mm2']-newc['shared_planar_face_area_mm2'])<1e-5
        protected=cq.Solid.makeCylinder(7,15,cq.Vector(xy[0],xy[1],-114),cq.Vector(0,0,1))
        protected_removed=volume(b.cut(new).intersect(protected)); assert protected_removed<1e-5
        q=check(sweeps[port],new,minimum=True); assert not q['events'] and q['minimum_BREP_surface_distance_mm']>1
        minimum=f.BoundingBox().xmax
        modifications[f'BLOCK_{bid}']=dict(block_angle_joint_deg=a,aperture=f'A{port}',
            original_radial_inner_plane_mm=34, candidate_radial_inner_plane_mm=38,
            whole_aperture_max_radial_projection_mm=minimum,
            sufficient_plane_for_1mm_projection_margin_mm=minimum+1,
            note='A whole-aperture separating-plane sufficient bound; not a global optimum over all possible notch shapes.',
            removed_volume_mm3=b.Volume()-new.Volume(),removed_uniform_steel_mass_kg=(b.Volume()-new.Volume())*7.85e-6,
            common_rear_contact_before=oldc,common_rear_contact_after=newc,
            removed_in_thread_R7_neighbourhood_mm3=protected_removed,
            thread_major_side_min_ligament_mm=5,thread_major_inner_planar_ligament_mm=11,
            source_subset_outside_volume_mm3=volume(new.cut(b)), aperture_probe=q,
            manufacturing_release=False)
        out=args.out/f'SHOULDER-PORT01-BLOCK-{bid}-R38.step'
        world=moved(new,T2); cq.exporters.export(world,str(out))
        rt=cq.importers.importStep(str(out)).val()
        export_checks[out.name]=dict(sha256=sha(out),valid=rt.isValid(),solids=len(rt.Solids()),
            volume_error_mm3=abs(rt.Volume()-world.Volume()),bbox_error_mm=float(np.max(abs(np.array(bounds(rt))-bounds(world)))),
            frame='RAISE02 world home mm; J2=(0,0,205), preceding_joints=1',vendor_CAD_included=False)
        assert rt.isValid() and len(rt.Solids())==1 and export_checks[out.name]['volume_error_mm3']<1e-4
    final_blocks={i:candidates.get(i,b) for i,b in blocks.items()}
    candidate_checks={}
    for port,sw in sweeps.items():
        for bid,b in final_blocks.items():candidate_checks[f'A{port}__BLOCK_{bid}']=check(sw,b,minimum=True)
        candidate_checks[f'A{port}__REAR_FORK']=check(sw,rear,minimum=True)
    static={f'BLOCK_{bid}__OEM42':check(b,vendor,minimum=True) for bid,b in candidates.items()}
    assert not any(q['events'] for q in candidate_checks.values())
    assert not any(q['events'] for q in static.values())
    result=dict(revision=REV,scope='Rear-cover aperture access, not connector insertion approval.',
        source_hashes=source_hashes,OEM_STEP=dict(filename=args.vendor_step.name,sha256=vendor_hash,solid_count=42,tail_solid_index=3,tail_bbox_joint_mm=bounds(tail)),
        frames=dict(T_vendor_from_joint_mm=T_vendor_joint.tolist(),T_world_from_joint_mm=T2.tolist(),
                    axes='+Zjoint is output. Rear access moves -Zjoint = -Yworld. Xjoint=Xworld, Yjoint=-Zworld.',
                    figure='Plots use +Xjoint to right, +Yjoint up, looking from output toward rear. Rear-facing view mirrors X.'),
        rear_face_joint_z_mm=-103.2000001,parts_main_front_joint_z_mm=-104.5,nominal_tail_to_block_front_mm=1.2999999,
        apertures=ports,original_access_checks=original_checks,
        original_events={k:v for k,v in original_checks.items() if v['events']},
        modifications=modifications,candidate_access_checks=candidate_checks,candidate_static_checks=static,
        export_checks=export_checks,
        proof='Extruding the filled real rear aperture from z=-103.2 to -163.2 includes its every planar cross-section during straight rearward 60 mm travel. Volume/distance checks apply to that aperture-sized probe only. No connector origin/depth or cable bend assumed.',
        connector_qualified=False,manufacturing_release=False,
        remaining=['OEM port manufacturer/full PN and insertion datum unknown; cover contour is not connector body.',
                   'Larger plug, latch/release tool, solder/heatshrink and 14AWG cable route unverified.',
                   'No approval of thread/preload/fatigue/tolerances; RAISE02 remains unchanged.',
                   'Removing material is geometrically monotone for pre-existing external collision/assembly bounds, but no new global strength or motion approval.'])
    (args.out/'study.json').write_text(json.dumps(result,indent=2)+'\n')
    plot(wires,blocks,final_blocks,args.out)
    print(json.dumps(dict(original_events=list(result['original_events']),candidate_aperture_events=0,
                         block1_clearance=modifications['BLOCK_1']['aperture_probe']['minimum_BREP_surface_distance_mm'],
                         block8_clearance=modifications['BLOCK_8']['aperture_probe']['minimum_BREP_surface_distance_mm']),indent=2))


def plot(wires,old,new,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Section
    from OCP.gp import gp_Pln,gp_Pnt,gp_Dir
    fig,axs=plt.subplots(1,2,figsize=(13.6,6.8))
    for ax,bs,title in zip(axs,[old,new],['Frozen RAISE02: two aperture shadows obstructed','PORT01 candidate: only blocks 1 / 8 inner planes -> 38']):
        for i,b in bs.items():
            op=BRepAlgoAPI_Section(b.wrapped,gp_Pln(gp_Pnt(0,0,-108.5),gp_Dir(0,0,1)),False);op.Build()
            for e in cq.Shape(op.Shape()).Edges():
                pts=np.array([e.positionAt(t).toTuple() for t in np.linspace(0,1,65)])
                ax.plot(pts[:,0],pts[:,1],color='#424b58',lw=1.0)
            c=b.Center();r=math.hypot(c.x,c.y);ax.text(c.x*60/r,c.y*60/r,str(i),ha='center',va='center',fontsize=10)
        ax.add_patch(Circle((0,0),47.4,fill=False,ls='--',lw=.7,color='#a0a0a0'))
        for i in range(4):
            for e in wires[i].Edges():
                pts=np.array([e.positionAt(t).toTuple() for t in np.linspace(0,1,65)])
                ax.plot(pts[:,0],pts[:,1],color='#c22c33' if i in [2,3] else '#0c8495',lw=2)
            c=cq.Face.makeFromWires(wires[i]).Center();ax.annotate(f'A{i}',(c.x,c.y),xytext=(c.x-8,c.y-7),fontsize=9,
                arrowprops=dict(arrowstyle='-',lw=.6))
        ax.set_title(title,fontsize=10);ax.set_xlim(-73,73);ax.set_ylim(-70,70);ax.set_aspect('equal');ax.grid(alpha=.25)
        ax.set_xlabel('Joint X / mm');ax.set_ylabel('Joint Y / mm')
    fig.suptitle('RH25-B rear cover aperture projection vs original steel blocks — measured CAD, not plug qualification',fontsize=12)
    fig.text(.5,.02,'Output-side coordinate view (rear view mirrors X). Apertures at Z=-103.2; block section at Z=-108.5.\nDashed circle: tail R47.4. Candidate preserves original mounting holes, bearing region and outer keys.',ha='center',fontsize=9)
    fig.subplots_adjust(bottom=.14,top=.9,wspace=.18)
    fig.savefig(out/'aperture-shadow-comparison.png',dpi=170)
    plt.close(fig)


if __name__=='__main__':
    main()
