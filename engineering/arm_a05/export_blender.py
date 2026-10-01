# SPDX-License-Identifier: CC-BY-NC-4.0
"""Export the A05 JSON packaging study as editable Blender geometry.

First refresh work/arm-a05/scene.json with:
    node engineering/arm_a05/check.js
Then, from the repository root:
    blender --background --python engineering/arm_a05/export_blender.py
Optional arguments follow Blender's '--':
    --input work/arm-a05/scene.json --output engineering/models/arm-a05-packaging.blend
    --pose idle
    --verify-only engineering/models/arm-a05-packaging.blend

Geometry and joints come from model.js/check.js, in millimetres. Blender stores
metres. This is an editable packaging proposal, not manufacturer CAD, a routed
harness, a manufacturing drawing or a validated physical robot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

MM = 0.001
ROOT = Path(__file__).resolve().parents[2]
COLLECTIONS = {
    'frames': '00_Kinematic_Frames',
    'motor': '01_Motor_Envelopes',
    'structure': '02_Main_Structure',
    'base': '02_Main_Structure',
    'bracket': '03_Proposed_Brackets',
    'head': '04_Detachable_Head',
    'display': '05_Display_Details',
    'wire': '90_Wire_Reservations_HIDDEN',
    'presentation': '99_Presentation_Not_Hardware',
}


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, default=ROOT/'work/arm-a05/scene.json')
    p.add_argument('--output', type=Path, default=ROOT/'engineering/models/arm-a05-packaging.blend')
    p.add_argument('--pose', choices=['idle', 'attention', 'reference'], default='idle')
    p.add_argument('--verify-only', type=Path)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def attach(obj, role, parent=None):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection(COLLECTIONS[role]).objects.link(obj)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    return obj


def material(name, color, metal=0, roughness=.5, emission=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Emission Color'].default_value = (*color, 1)
    p.inputs['Emission Strength'].default_value = emission
    return m


def mesh_object(name, vertices, faces, role, parent, mat):
    mesh = bpy.data.meshes.new(name+'.mesh')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    attach(obj, role, parent)
    mesh.materials.append(mat)
    return obj


def cylinder(name, radius, length, role, parent, mat):
    n = 64
    v = [(radius*MM*math.cos(2*math.pi*k/n),
          radius*MM*math.sin(2*math.pi*k/n), z*length*MM/2)
         for z in [-1, 1] for k in range(n)]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
    faces += [(k, (k+1)%n, (k+1)%n+n, k+n) for k in range(n)]
    o = mesh_object(name, v, faces, role, parent, mat)
    for f in o.data.polygons[2:]:
        f.use_smooth = True
    return o


def axis_quaternion(axis):
    return Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())


def part_object(part, frames, mats):
    role, name = part['role'], part['id']
    parent = frames[part['frame']]
    if part['kind'] == 'cylinder':
        o = cylinder(name, part['r'], part['length'], role, parent, mats[role])
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = axis_quaternion(part['axis'])
        # Material detail on the existing camera cap; no invented lens geometry.
        if name.startswith('camera-'):
            o.data.materials.append(mats['glass'])
            o.data.polygons[1].material_index = 1
    elif part['kind'] == 'box':
        sx, sy, sz = [x*MM/2 for x in part['size']]
        v = [(x*sx, y*sy, z*sz) for x in [-1, 1] for y in [-1, 1] for z in [-1, 1]]
        faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
                 (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
        o = mesh_object(name, v, faces, role, parent, mats[role])
    elif part['kind'] == 'petal':
        polygon = part['polygon']
        # Keep the true polygon, including its shoulders; collision hull is not geometry.
        area = sum(polygon[k][0]*polygon[(k+1)%len(polygon)][1]
                   - polygon[(k+1)%len(polygon)][0]*polygon[k][1]
                   for k in range(len(polygon)))
        polygon = polygon if area > 0 else list(reversed(polygon))
        n = len(polygon)
        v = [(x*part['depth']*MM/2, y*MM, z*MM)
             for x in [-1, 1] for y, z in polygon]
        faces = [tuple(reversed(range(n))), tuple(range(n, 2*n))]
        faces += [(k, (k+1)%n, (k+1)%n+n, k+n) for k in range(n)]
        o = mesh_object(name, v, faces, role, parent, mats[role])
        # Same inset surface as viewer.js: 0.87 in Y, 0.83 in Z, 0.2 mm ahead.
        cy = sum(p[0] for p in polygon)/n
        cz = sum(p[1] for p in polygon)/n
        inset = [((part['depth']/2+.2)*MM,
                  (cy+(y-cy)*.87)*MM, (cz+(z-cz)*.83)*MM) for y, z in polygon]
        panel = mesh_object(name+'.light_surface', inset, [tuple(range(n))],
                            'display', o, mats['display'])
        panel['status'] = 'Viewer appearance surface; not a separate manufactured part.'
    else:
        raise ValueError(f"Unsupported source geometry: {part['kind']}")
    o.location = Vector(part.get('center', [0, 0, 0]))*MM
    o['source_part_id'] = name
    o['source_frame'] = part['frame']
    o['source_geometry_json'] = json.dumps(part, ensure_ascii=False)
    o['status'] = 'Proposed packaging envelope; no manufacturing release.'
    if role == 'motor':
        o['casing_is_fixed_to_upstream'] = True
    return o


def set_pose(layout, name):
    for j, q in zip(layout['joints'], layout['poses'][name]):
        fixed = bpy.data.objects[j['id']+'.fixed']
        fixed['angle_deg'] = float(q)
        fixed.update_tag()
    bpy.context.scene['active_pose'] = name
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def make_frames(layout):
    frames = {}
    world = bpy.data.objects.new('world', None)
    attach(world, 'frames')
    world.empty_display_type = 'PLAIN_AXES'
    world.empty_display_size = .025
    world['status'] = layout['status']
    frames['world'] = world
    parent = world
    for index, j in enumerate(layout['joints']):
        fixed = bpy.data.objects.new(j['id']+'.fixed', None)
        attach(fixed, 'frames', parent)
        fixed.location = Vector(j['offset'])*MM
        fixed.empty_display_type = 'ARROWS'
        fixed.empty_display_size = .04
        fixed['angle_deg'] = float(layout['poses']['idle'][index])
        fixed['joint_name'] = j['name']
        fixed['candidate_motor'] = j['model']
        fixed['zero_offset_deg'] = j['zero_deg']
        fixed['limits_status'] = 'Exploratory packaging limits; not certified hardware/cable limits.'
        fixed.id_properties_ui('angle_deg').update(
            min=j['limits_deg'][0], max=j['limits_deg'][1],
            soft_min=j['limits_deg'][0], soft_max=j['limits_deg'][1],
            description='Displayed joint angle in degrees; exploratory range only.')
        rotor = bpy.data.objects.new(j['id']+'.rotor', None)
        attach(rotor, 'frames', fixed)
        rotor.empty_display_type = 'CIRCLE'
        rotor.empty_display_size = .015
        rotor.rotation_mode = 'AXIS_ANGLE'
        rotor.rotation_axis_angle = (0, *Vector(j['axis']).normalized())
        fcurve = rotor.driver_add('rotation_axis_angle', 0)
        driver = fcurve.driver
        driver.type = 'SCRIPTED'
        variable = driver.variables.new()
        variable.name = 'q'
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id = fixed
        variable.targets[0].data_path = '["angle_deg"]'
        # Arithmetic-only simple expression remains usable with auto-exec disabled.
        driver.expression = f"(q + ({j['zero_deg']})) * 0.017453292519943295"
        frames[fixed.name], frames[rotor.name] = fixed, rotor
        parent = rotor
    for name, offset in [('head', layout['head_offset_mm']), ('tcp', layout['tcp_offset_mm'])]:
        o = bpy.data.objects.new(name, None)
        attach(o, 'frames', parent)
        o.location = Vector(offset)*MM
        o.empty_display_type = 'PLAIN_AXES'
        o.empty_display_size = .03
        frames[name] = o
        parent = o
    return frames


def make_wire_reservations(data, frames, mats):
    cables = data['cables']
    for i, segment in enumerate(cables['segments']):
        curve = bpy.data.curves.new(f'wire_reservation.{i+1:02d}.curve', 'CURVE')
        curve.dimensions = '3D'
        curve.resolution_u = 12
        curve.bevel_depth = data['layout']['cable_assumptions']['bundle_diameter_mm']*MM/2
        curve.bevel_resolution = 3
        # Editable piecewise-linear reservation, avoiding an invented exact spline route.
        spline = curve.splines.new('POLY')
        spline.points.add(len(segment['points'])-1)
        for point, p in zip(spline.points, segment['points']):
            point.co = (*[x*MM for x in p], 1)
        o = bpy.data.objects.new(f'wire_reservation.{i+1:02d}', curve)
        attach(o, 'wire', frames[segment['frame']])
        curve.materials.append(mats['wire'])
        o['status'] = cables['status']
        o['source_frame'] = segment['frame']
        o['is_real_routed_harness'] = False
    for i, (frame, axis, center, radius, thickness) in enumerate(cables['chambers']):
        bpy.ops.mesh.primitive_torus_add(major_radius=radius*MM, minor_radius=thickness*MM,
                                        major_segments=48, minor_segments=12)
        o = bpy.context.object
        o.name = f'movement_chamber.{i+1:02d}'
        attach(o, 'wire', frames[frame])
        o.location = Vector(center)*MM
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = axis_quaternion(axis)
        o.data.materials.append(mats['wire'])
        o.display_type = 'WIRE'
        o['status'] = 'Movement-space reservation; not an installed cable loop.'
        o['source_frame'] = frame
    c = collection(COLLECTIONS['wire'])
    c.hide_viewport = True
    c.hide_render = True


def embedded_texts(data, source_hash):
    bpy.data.texts.new('A05_Source_Scene.json').write(json.dumps(data, ensure_ascii=False, indent=2))
    script = '''"""A05 discrete pose switcher. No animation or motion validation.
Run this text once, then call set_pose('idle'), set_pose('attention') or
set_pose('reference') from Blender's Python Console.
"""
import bpy, json
_layout = json.loads(bpy.data.texts['A05_Source_Scene.json'].as_string())['layout']
def set_pose(name):
    if name not in _layout['poses']:
        raise ValueError('Available poses: ' + ', '.join(_layout['poses']))
    for joint, angle in zip(_layout['joints'], _layout['poses'][name]):
        obj = bpy.data.objects[joint['id'] + '.fixed']
        obj['angle_deg'] = float(angle)
        obj.update_tag()
    bpy.context.scene['active_pose'] = name
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()
'''
    bpy.data.texts.new('A05_Poses.py').write(script)
    readme = f'''A05 — EDITABLE PACKAGING STUDY / 可编辑装配占位研究

Not manufacturing CAD. No claim of 2 kg load capability, strength, thermal
performance, complete collisions, cable life or manufacturability.

Units: source millimetres -> Blender metres, metric display in millimetres.
Source scene SHA256: {source_hash}
Every source part is a separate named mesh under its original local frame.
Motor casings belong to Jn.fixed, never their own Jn.rotor. Each next joint's
fixed frame follows the preceding rotor. J2's displayed zero includes -90deg.

EDIT: select J1.fixed ... J7.fixed and edit the custom angle_deg property.
Preset switch: run A05_Poses.py in Text Editor, then in the Python Console:
  set_pose('idle')
  set_pose('attention')
  set_pose('reference')
Alternatively:
  exec(bpy.data.texts['A05_Poses.py'].as_string()); set_pose('attention')
The presets are discrete arrangements; no unverified animation is installed.

Collection 90_Wire_Reservations_HIDDEN is disabled in viewport and rendering.
Enable its viewport/render flags only to inspect conceptual ducts/chambers.
They are discontinuous reservations, NOT a constant-length routed harness.
No through-bore in any motor is assumed. These curves and toroids are editable.

Petal light insets match the existing viewer. Camera color is surface appearance;
no new lens hardware is invented. Presentation camera/lights are not hardware.

REBUILD from repository root:
  node engineering/arm_a05/check.js
  blender --background --python engineering/arm_a05/export_blender.py
VERIFY saved file independently:
  blender --background --disable-autoexec --python engineering/arm_a05/export_blender.py -- --verify-only engineering/models/arm-a05-packaging.blend

Original proxy geometry only. No vendor CAD mesh is embedded.
'''
    bpy.data.texts.new('START_HERE_A05.txt').write(readme)


def presentation():
    scene = bpy.context.scene
    corners = [obj.matrix_world @ Vector(corner)
               for obj in bpy.data.objects if 'source_part_id' in obj
               for corner in obj.bound_box]
    focus = Vector(tuple((min(p[i] for p in corners)+max(p[i] for p in corners))/2
                         for i in range(3)))
    world = scene.world or bpy.data.worlds.new('A05_Studio')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.045, .052, .066, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .4
    for name, position, energy, size in [('Key', (.4, -.8, 1.2), 90, 1.1),
                                          ('Fill', (-.4, .7, .65), 55, .9),
                                          ('Rim', (.7, .8, 1.1), 90, .8)]:
        lamp = bpy.data.lights.new('Studio.'+name, 'AREA')
        lamp.energy, lamp.shape, lamp.size = energy, 'DISK', size
        o = bpy.data.objects.new(lamp.name, lamp)
        attach(o, 'presentation')
        o.location = position
        o.rotation_euler = (Vector((.25, .04, .3))-o.location).to_track_quat('-Z', 'Y').to_euler()
    cam = bpy.data.cameras.new('Packaging_View')
    o = bpy.data.objects.new(cam.name, cam)
    attach(o, 'presentation')
    o.location = focus + Vector((.93, -1.395, .53))
    o.rotation_euler = (focus-o.location).to_track_quat('-Z', 'Y').to_euler()
    view_inverse = o.rotation_euler.to_matrix().transposed()
    projected = [view_inverse @ (p-focus) for p in corners]
    spans = [max(p[i] for p in projected)-min(p[i] for p in projected) for i in range(2)]
    cam.type, cam.ortho_scale, cam.lens = 'ORTHO', max(spans[0], spans[1]*4/3)*1.2, 48
    cam.clip_start, cam.clip_end = .001, 20
    scene.camera = o
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1050
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = 'AgX'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                s = area.spaces.active
                s.clip_start, s.clip_end = .001, 20
                s.shading.type = 'MATERIAL'
                s.region_3d.view_distance = 1.1
                s.region_3d.view_location = focus
                s.region_3d.view_rotation = o.rotation_euler.to_quaternion()


def expected_frames(layout, angles):
    frames = {'world': Matrix.Identity(4)}
    parent = frames['world']
    for joint, angle in zip(layout['joints'], angles):
        fixed = parent @ Matrix.Translation(Vector(joint['offset'])*MM)
        rotor = fixed @ Matrix.Rotation(math.radians(angle+joint['zero_deg']), 4, Vector(joint['axis']))
        frames[joint['id']+'.fixed'] = fixed
        frames[joint['id']+'.rotor'] = rotor
        parent = rotor
    frames['head'] = parent @ Matrix.Translation(Vector(layout['head_offset_mm'])*MM)
    frames['tcp'] = frames['head'] @ Matrix.Translation(Vector(layout['tcp_offset_mm'])*MM)
    return frames


def verify(data):
    layout = data['layout']
    result = {'source_parts': len(data['parts']), 'poses': {}}
    original_pose = bpy.context.scene.get('active_pose', 'idle')
    for name, angles in layout['poses'].items():
        set_pose(layout, name)
        expected = expected_frames(layout, angles)
        worst = 0
        for frame, matrix in expected.items():
            actual = bpy.data.objects[frame].matrix_world
            error = max(abs(actual[r][c]-matrix[r][c]) for r in range(4) for c in range(4))
            worst = max(worst, error)
            assert error < 3e-6, (name, frame, error)
        for part in data['parts']:
            obj = bpy.data.objects[part['id']]
            assert obj.parent.name == part['frame'], (obj.name, obj.parent.name)
            expected_center = expected[part['frame']] @ (Vector(part.get('center', [0, 0, 0]))*MM)
            assert (obj.matrix_world.translation-expected_center).length < 2e-6
        result['poses'][name] = {'max_frame_matrix_error': worst,
                                  'tcp_mm': [round(x/MM, 6) for x in bpy.data.objects['tcp'].matrix_world.translation]}
    set_pose(layout, original_pose)
    assert collection(COLLECTIONS['wire']).hide_viewport
    assert collection(COLLECTIONS['wire']).hide_render
    assert len([o for o in bpy.data.objects if 'source_part_id' in o]) == len(data['parts'])
    assert len(bpy.data.actions) == 0, 'No animation should be installed'
    result.update(objects=len(bpy.data.objects), meshes=len(bpy.data.meshes),
                  collections=len(bpy.data.collections),
                  joint_drivers=sum(len(o.animation_data.drivers) for o in bpy.data.objects if o.animation_data),
                  wire_objects=len(collection(COLLECTIONS['wire']).objects),
                  animation_actions=len(bpy.data.actions))
    return result


def main():
    args = arguments()
    if args.verify_only:
        bpy.ops.wm.open_mainfile(filepath=str(args.verify_only.resolve()))
        data = json.loads(bpy.data.texts['A05_Source_Scene.json'].as_string())
        report = verify(data)
        report['verified_file'] = str(args.verify_only)
        print('A05_VERIFY '+json.dumps(report))
        return
    raw = args.input.read_bytes()
    data = json.loads(raw)
    assert data['layout']['units'] == 'mm'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name in sorted(set(COLLECTIONS.values())):
        collection(name)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene['status'] = 'Editable A05 packaging study, not manufacturing release.'
    scene['source_scene_sha256'] = hashlib.sha256(raw).hexdigest()
    mats = {
        'motor': material('Motor_Envelope_Gunmetal', (.15, .20, .25), .5, .34),
        'structure': material('Main_Structure_Graphite', (.105, .13, .17), .45),
        'bracket': material('Proposed_Bracket_Titanium', (.31, .37, .40), .55),
        'head': material('Head_Envelope_Charcoal', (.075, .095, .12), .3),
        'display': material('Amber_Light_Surface', (1, .48, .08), .1, .3, .55),
        'base': material('Base_Datum', (.10, .12, .15), .4),
        'wire': material('Reservation_Only_Teal', (.04, .55, .52), 0, .5, .2),
        'glass': material('Camera_Front_Surface', (.018, .075, .095), .25, .12),
    }
    frames = make_frames(data['layout'])
    for part in data['parts']:
        part_object(part, frames, mats)
    make_wire_reservations(data, frames, mats)
    embedded_texts(data, scene['source_scene_sha256'])
    set_pose(data['layout'], args.pose)
    presentation()
    report = verify(data)
    bpy.ops.object.select_all(action='DESELECT')
    fixed = frames['J2.fixed']
    fixed.select_set(True)
    bpy.context.view_layer.objects.active = fixed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # No .blend1 backup artefact is needed for this deterministic generated model.
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()), compress=True)
    report['saved_file'] = str(args.output)
    report['source_scene_sha256'] = scene['source_scene_sha256']
    print('A05_EXPORT '+json.dumps(report))


if __name__ == '__main__':
    main()
