# SPDX-License-Identifier: CC-BY-NC-4.0
"""J7 supported plastic fit cartridge. Units mm; no powered/load release.

Subtract material only from the pinned A11 bearing housing and retainer.
Supplier interfaces, bearing stack and all screw stations stay unchanged.
"""
from pathlib import Path
import sys, json, math, hashlib, csv
import numpy as np
import cadquery as cq
import trimesh

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / 'build'
BASE = ROOT / 'engineering/arm_a11/build'
sys.path.insert(0, str(ROOT / 'engineering/arm_a11'))
import interfaces as c
import collision
b = c.legacy
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def mesh(shape):
    assert shape.isValid() and len(shape.Solids()) == 1
    shape = shape.clean().fix()
    for tolerance in [.10, .03]:
        verts, faces = shape.tessellate(tolerance, .12)
        m = trimesh.Trimesh([v.toTuple() for v in verts], faces, process=True)
        m.merge_vertices(digits_vertex=5)
        m.update_faces(m.nondegenerate_faces())
        m.update_faces(m.unique_faces())
        m.remove_unreferenced_vertices()
        if m.is_watertight and m.is_winding_consistent and len(m.split()) == 1:
            return m
    raise RuntimeError('CAD tessellation not a single closed oriented mesh')


def main():
    for folder in ['step', 'stl-object', 'print-bed']:
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    source = json.loads((BASE / 'manifest.json').read_text())
    assert sha(BASE / 'manifest.json') == '3b9a2291509e0666eeb8d9e73c320538a4235337ffa10af1d1915665a819b559'
    source_parts = {p['id']: p for p in source['parts']}
    sources = {}
    def load(name):
        path = BASE / 'step' / (name + '.step')
        sources[str(path.relative_to(ROOT))] = sha(path)
        return cq.importers.importStep(str(path)).val()

    original_cage = load('J7-bearing-cage')
    cage = original_cage
    # Six open radial windows, between the six axial bolt stations.
    # The 3 mm axial end webs, bearing seats and r=35 bolt bosses remain.
    for k in range(6):
        a = math.radians(60*k)
        cage = cage.cut(b.cyl([36.3, 41*math.cos(a), 41*math.sin(a)], [1,0,0], 8.5, 14.9)).fix()
    original_retainer = load('J7-bearing-retainer')
    retainer = original_retainer
    for k in range(6):
        a = math.radians(60*k)
        retainer = retainer.cut(b.cyl([54.1, 45*math.cos(a), 45*math.sin(a)], [1,0,0], 13, 2.7)).fix()

    # A11's integral D60 flange and rear D37 stop trap the two ID35 bearings.
    # Split the front flange, keep the motor through-bolt path and axial stack.
    original_output = load('B7-output-flange')
    front_box = cq.Solid.makeBox(50,200,200,b.V([57.7,-100,-100]))
    journal = original_output.cut(front_box).fuse(b.cyl([57.7,0,0],[1,0,0],10,2)).clean().fix()
    flange = original_output.intersect(front_box).cut(b.cyl([57.6,0,0],[1,0,0],10.1,2.3)).clean().fix()
    definitions = [
        ('A13-J7-101-bearing-housing', cage, 'J7.fixed', 'modified_print_structure', 'J7-bearing-cage'),
        ('A13-J7-102-bearing-retainer', retainer, 'J7.fixed', 'modified_print_structure', 'J7-bearing-retainer'),
        ('A13-J7-103-output-journal', journal, 'J7.rotor', 'modified_print_structure', 'B7-output-flange'),
        ('A13-J7-104-inner-spacer', load('J7-inner-spacer'), 'J7.rotor', 'inherited_fit_structure', 'J7-inner-spacer'),
        # This carrier is in J6.rotor in A11; express it in J7.fixed for this local fixture.
        ('A13-J7-105-carrier', load('P06-yaw-to-roll').translate([-25,0,0]), 'J7.fixed', 'inherited_fit_structure', 'P06-yaw-to-roll'),
        ('A13-J7-106-detachable-flange', flange, 'J7.rotor', 'modified_print_structure', 'B7-output-flange'),
    ]
    for diameter in [47.10, 47.20, 47.35]:
        definitions.append((f'A13-J7-G-seat-{diameter:.2f}', b.ring([0,0,0],[1,0,0],28,diameter/2,7), 'coupon', 'fit_coupon', None))
    for diameter in [34.85, 34.95, 35.05]:
        # Flat flange lets the actual bearing be removed by hand after gauging.
        s = b.cyl([0,0,0],[1,0,0],21,2).fuse(b.cyl([2,0,0],[1,0,0],diameter/2,7)).clean()
        definitions.append((f'A13-J7-G-journal-{diameter:.2f}', s, 'coupon', 'fit_coupon', None))

    parts = []
    shapes = {}
    for id, shape, frame, role, replaces in definitions:
        shape = shape.clean().fix()
        m = mesh(shape)
        step = OUT/'step'/(id+'.step')
        cq.exporters.export(shape, str(step))
        object_stl = OUT/'stl-object'/(id+'.stl')
        m.export(object_stl)
        # +X becomes bed +Z: axial bores stay vertical, bearing shoulders stay flat.
        rotation = np.array([[0,0,-1],[0,1,0],[1,0,0]], float)
        if id == 'A13-J7-106-detachable-flange':
            # Broad output flange sits on the bed; avoid a 12.5 mm radial
            # cantilever if the narrow journal were printed below the flange.
            rotation = np.array([[0,0,1],[0,1,0],[-1,0,0]], float)
        bed = m.copy()
        bed.vertices = bed.vertices @ rotation.T
        translation = -bed.bounds[0]
        bed.apply_translation(translation)
        print_stl = OUT/'print-bed'/(id+'.stl')
        bed.export(print_stl)
        size = np.ptp(bed.vertices, axis=0)
        assert max(size[:2]) <= 230 and size[2] <= 240
        p = dict(id=id, frame=frame, role=role, replaces=replaces,
                 vertices_mm=m.vertices.tolist(), triangles=m.faces.tolist(),
                 bbox_mm=m.bounds.tolist(), volume_mm3=shape.Volume(),
                 centroid_mm=list(shape.Center().toTuple()),
                 solid_count=1, stl_closed=True,
                 print_size_mm=size.tolist(),
                 print_rotation=rotation.tolist(), print_translation_mm=translation.tolist(),
                 step_sha256=sha(step), object_stl_sha256=sha(object_stl), print_stl_sha256=sha(print_stl),
                 solid_PETG_mass_kg=shape.Volume()*1.27e-6,
                 print_scope='Supported unpowered fit only; slicer/support and physical fit pending')
        parts.append(p)
        shapes[id] = shape
        print('PART', id, np.round(size,2), flush=True)

    # Explicit proof that both changed parts only remove source material.
    subtraction = []
    for name, before, after in [('housing',original_cage,cage),('retainer',original_retainer,retainer)]:
        added = collision.volume(after.cut(before))
        assert added < .0001
        subtraction.append(dict(part=name, before_mm3=before.Volume(), after_mm3=after.Volume(),
                                removed_fraction=1-after.Volume()/before.Volume(), added_volume_mm3=added))

    # Axial stack derives from pinned actual output plane and the owned CAD.
    inf = c.I[6]
    assert np.max(abs(inf['out'] - np.array([25.7,0,0]))) < 1e-8
    fixed = [[float(t) for t in (inf['fixed']+v)] for v in b.xy_holes(inf,'fixed_front_fasteners')]
    output = [[float(t) for t in (inf['out']+v)] for v in b.xy_holes(inf,'output_fasteners')]
    stack = dict(axis='+X', motor_model='RS00', fixed_plane_x_mm=25.3,
        output_plane_x_mm=25.7, housing_span_x_mm=[33.3,54.2],
        bearing_seats=[dict(span_x_mm=[36.2,43.2],nominal_ID_mm=47.2),dict(span_x_mm=[47.2,54.2],nominal_ID_mm=47.2)],
        outer_ring_stop_span_x_mm=[43.2,47.2], outer_ring_stop_ID_mm=44.8,
        rear_seat_relief_span_x_mm=[33.3,36.2],
        journal_OD_mm=34.95, inner_stop_span_x_mm=[34.2,36.2],
        inner_spacer_span_x_mm=[54.2,57.7], retainer_span_x_mm=[54.2,56.7],
        flange_span_x_mm=[57.7,65.7], nominal_retainer_rotor_gap_mm=1.0,
        detachable_flange_pilot=dict(male_OD_mm=20.0,male_length_mm=2.0,female_ID_mm=20.2,female_depth_mm=2.2,
                                     physical_fit_required=True,uses_original_six_M3x40_output_bolts=True),
        six_cartridge_bolts=dict(PCD_mm=70,angle_start_deg=30,diameter_mm=3.5),
        fixed_hole_centres_mm=fixed,output_hole_centres_mm=output,
        end_flange=dict(OD_mm=60,PCD_mm=45,count=3,clearance_mm=4.5,angle_start_deg=30),
        fixed_motor_screw=dict(size='M3x12 button',nominal_engagement_mm=3.5,usable_front_thread_depth='unverified: measure before installation'),
        output_motor_screw=dict(size='M3x40 socket',nominal_engagement_mm=4.0,source_blind_depth_mm=5.0,actual_bottoming_check='required'),
        bearing=dict(part='6807',size_mm=[35,47,7],quantity=2,physical_axial_shimming='measure endplay; avoid deformation preload'))
    (OUT/'interface.json').write_text(json.dumps(stack, indent=2)+'\n')

    # Check the changed shapes against the exact local supplier stator and
    # rigid carrier, purchased bearing envelopes, rotating journal and screws.
    checks = []
    targets = [('carrier',shapes['A13-J7-105-carrier'])]
    for name in ['J7-6807-1','J7-6807-2']:
        targets.append((name, load(name)))
    for p in source['parts']:
        if p['id'].startswith(('J7-cage-', 'J7-fixed-')):
            targets.append((p['id'],load(p['id'])))
    vendor = ROOT/'work/arm-a10/vendor/J7-stator.step'
    sources[str(vendor.relative_to(ROOT))] = sha(vendor)
    targets.append(('RS00-supplier-stator',cq.importers.importStep(str(vendor)).val()))
    for name, s in [('housing',cage),('retainer',retainer)]:
        for target, t in targets:
            v = collision.volume(collision.common_solids(s,t))
            checks.append(dict(a=name,b=target,volume_mm3=v))
        for angle in [-90,-45,0,45,90]:
            for id in ['A13-J7-103-output-journal','A13-J7-106-detachable-flange']:
                rotor = shapes[id].rotate([0,0,0],[1,0,0],angle)
                checks.append(dict(a=name,b=id,J7_deg=angle,
                                   volume_mm3=collision.volume(collision.common_solids(s,rotor))))
    # CAD-based assembly-pass checks: bearings load from opposite housing
    # ends, then the cartridge slides onto the journal before flange fitting.
    assert stack['journal_OD_mm'] < 35 and 37 > 35 and 60 > 35
    assembly_checks = []
    # Inner rings are represented by the purchased bearing envelopes. The
    # 20 mm front pilot is below ID35; the integral D37 stop stays behind them.
    for name in ['J7-6807-1','J7-6807-2']:
        s=load(name)
        for travel in [0,10,25,40]:
            v=collision.volume(collision.common_solids(journal,s.translate([travel,0,0])))
            assembly_checks.append(dict(moving=name,travel_x_mm=travel,against='bare journal before fitting flange',volume_mm3=v))
    pilot_overlap=collision.volume(collision.common_solids(journal,flange))
    assert pilot_overlap < .05
    assert all(row['volume_mm3'] <= .05 for row in assembly_checks)
    bad = [row for row in checks if row['volume_mm3'] > .05]
    audit = dict(scope='Only changed J7 housing/retainer against local nominal components; not whole arm, wires, covers or continuous motion',
                 exact_checks=checks, overlaps=bad, subtractive_proof=subtraction,
                 bearing_insertion_samples=assembly_checks,detachable_flange_overlap_mm3=pilot_overlap,
                 physical_assembly_pending=True)
    (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    assert not bad, bad

    # Local owned assembly context plus nominal steel fasteners and bearings.
    context = []
    for p in source['parts']:
        if p['id'].startswith(('J7-cage-', 'J7-fixed-', 'J7-output-', 'J7-6807-', 'FLANGE-')) and p['role']=='hardware':
            s = load(p['id']);m = mesh(s)
            context.append(dict(id=p['id'],frame=p['frame'],role='purchased_hardware_reference',
                                vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist()))
    s=load('J7-motor-envelope');m=mesh(s)
    context.append(dict(id='J7-motor-envelope',frame='J7.fixed',role='owned_motor_envelope_reference',
                        vertices_mm=m.vertices.tolist(),triangles=m.faces.tolist()))
    # The actual raw supplier shapes are never placed in the public manifest.
    manifest = dict(revision='A13-J7-FIT01',status='supported_unpowered_plastic_fit',
        material_route='Plastic prototype first; independently redesigned metal structure later',
        baseline_manifest_sha256=sha(BASE/'manifest.json'), sources=sources,
        parts=parts,owned_context=context, interface_file='interface.json',
        keeps_motor_geometry_and_interfaces=True,keeps_J7_axis_and_arm_length=True,
        complete_arm_print_release=False,assembly_screws_unchanged=True,
        reduction=subtraction, printing=dict(bed_check_mm=[230,230,240],
        material_candidate='PETG for first dimensional trial; material is not strength-qualified',
        slicing_pending=True,default_housing_seat_mm=47.2,default_journal_mm=34.95,
        coupon_selection_required=True))
    (OUT/'manifest.json').write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    audit['manifest_sha256']=sha(OUT/'manifest.json')
    (OUT/'fit-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    with (OUT/'parts.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['id','role','quantity','x_bed_mm','y_bed_mm','z_bed_mm','solid_PETG_kg','frame'])
        for p in parts:w.writerow([p['id'],p['role'],1,*[round(v,2) for v in p['print_size_mm']],round(p['solid_PETG_mass_kg'],5),p['frame']])
    print('PASS',len(parts),'print files;',len(checks),'local checks;','reduction',subtraction,flush=True)


if __name__ == '__main__':
    main()
