# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Construct the B05 shield exterior as native Blender mesh geometry.

Run with Blender --background --python engineering/base_b05/blender_exterior.py.
The editable .blend retains the native loft surface and construction parameters.
STLs use global assembly millimetres; print-parts are translated to XYZ >= 0.
These are exterior shape/fit prototypes. Mounting supports are integrated later.
"""
import bpy
import bmesh
import json
import math
import struct
import sys
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE / "build" / "exterior"
M = .001
CENTER = (0., 75.)
SEGMENTS = 320
INNER_RADIUS = 72.6
WALL = 3.0
PARAMETERS = {
    "schema": "odradek.b05.blender-exterior.v1", "length_unit": "mm",
    "center_xy": CENTER, "wall_nominal_mm": WALL,
    "outer_half_control_points": [[0, -45], [106, -45], [131, -28], [145, 23],
                                  [138, 61], [119, 97], [90, 127], [64, 153],
                                  [37, 184], [18, 202], [0, 205]],
    "inner_body_radius_mm": INNER_RADIUS,
    "collar_radius_mm": [52, 72], "collar_top_z_mm": [74, 58.5],
    "design_intent": "Minimal alien carapace: swept shield shoulders, continuous flowing surfaces, rising neck, restrained seams",
    "splits_mm": {"main_y_min": 30.4, "front_nose_seam": "Y = 145.4 - 0.24 * abs(X); nominal 0.8 mm gap",
                  "rear_y_max": 29.6, "rear_lid_x": [-75.6, 75.6],
                  "rear_shoulder_abs_x_min": 76.4, "main_center_gap": .8},
    "rear_cable_exit": {"x": [-42, 42], "y": [-60, -33], "z": [-8, 21], "corner_radius_mm": 4},
    "light_aperture_xy_mm": [[-19, 178], [19, 184]],
    "prototype_scope": "exterior shape and unpowered fit prototype; mounting details and full assembly not released",
}


def reset_scene():
    # This generator owns its entire dedicated exterior scene. Include hidden
    # construction objects so reruns do not accumulate duplicate loft masters.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name.startswith(("01_Exterior", "02_Light", "90_Construction", "99_Render")):
            bpy.data.collections.remove(collection)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1200
    scene.render.resolution_percentage = 100
    scene.world.use_nodes = True
    world = scene.world.node_tree.nodes.get("Background")
    world.inputs[0].default_value = (.25, .29, .35, 1)
    world.inputs[1].default_value = .45
    scene.view_settings.view_transform = "AgX"
    scene.render.image_settings.file_format = "PNG"
    scene["Scope"] = PARAMETERS["prototype_scope"]
    scene["Geometry source"] = "Native Blender loft, solidify and manifold Boolean operations; not imported CAD"
    scene["Units"] = "Blender SI metres with millimetre display; all exported STL coordinates are millimetres"
    return scene


SCENE = reset_scene()
COLLECTIONS = {}
for name in ("01_Exterior_fit_parts", "02_Light_lens_fit_part", "90_Construction_native_loft", "99_Render_only"):
    collection = bpy.data.collections.new(name)
    SCENE.collection.children.link(collection)
    COLLECTIONS[name] = collection


def move_collection(obj, name):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    COLLECTIONS[name].objects.link(obj)


def activate(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh_object(name, vertices_mm, faces, collection="01_Exterior_fit_parts"):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata([tuple(c * M for c in v) for v in vertices_mm], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    COLLECTIONS[collection].objects.link(obj)
    recalc(obj)
    return obj


def recalc(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def smoothstep(lo, hi, value):
    t = max(0., min(1., (value - lo) / (hi - lo)))
    return t * t * (3 - 2 * t)


def sampled_outline():
    right = PARAMETERS["outer_half_control_points"]
    controls = right + [[-x, y] for x, y in right[-2:0:-1]]
    points = []
    for i in range(len(controls)):
        p0, p1, p2, p3 = [controls[j % len(controls)] for j in (i - 1, i, i + 1, i + 2)]
        for step in range(36):
            t = step / 36
            points.append(tuple(.5 * (2 * p1[k] + (-p0[k] + p2[k]) * t
                                           + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t * t
                                           + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t * t * t)
                                for k in (0, 1)))
    return points


OUTLINE = sampled_outline()


def cross2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def radial_boundary(theta):
    direction = (math.cos(theta), math.sin(theta))
    candidates = []
    for i, point in enumerate(OUTLINE):
        following = OUTLINE[(i + 1) % len(OUTLINE)]
        a = (point[0] - CENTER[0], point[1] - CENTER[1])
        edge = (following[0] - point[0], following[1] - point[1])
        divisor = cross2(direction, edge)
        if abs(divisor) < 1e-10:
            continue
        radius, along = cross2(a, edge) / divisor, cross2(a, direction) / divisor
        if radius > 0 and -.000001 <= along <= 1.000001:
            candidates.append(radius)
    if not candidates:
        raise ValueError(f"No outer shield intersection at angle {theta}")
    return max(candidates)


def profile_height(fraction, x, y):
    # Monotone cubic interpolation keeps the shell flowing without concentric
    # polygonal bands. The small saddle changes the highlight near each shoulder.
    keys = [(0., 58), (.09, 57.2), (.46, 43), (.67, 34), (.87, 19), (1., 8)]
    secants = [(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(keys,keys[1:])]
    slopes = [secants[0]] + [2*a*b/(a+b) if a*b>0 else 0 for a,b in zip(secants,secants[1:])] + [secants[-1]]
    z = 8.
    for i, ((a, za), (b, zb)) in enumerate(zip(keys, keys[1:])):
        if a <= fraction <= b:
            t=(fraction-a)/(b-a); h=b-a
            z=(2*t**3-3*t**2+1)*za+(t**3-2*t**2+t)*h*slopes[i]+(-2*t**3+3*t**2)*zb+(t**3-t**2)*h*slopes[i+1]
            break
    theta=math.atan2(y-CENTER[1],x)
    z-=2.2*math.sin(2*theta)**2*math.exp(-((fraction-.53)/.19)**2)
    # The selected reference has a restrained planar nose highlight and a
    # straight light slit; avoid a domed, eyebrow-like optical window.
    nose_mix=smoothstep(155,173,y)*(1-smoothstep(24,65,abs(x)))*(1-smoothstep(.86,1.,fraction))
    nose_plane=58-(y-147.6)*50/(205-147.6)-.007*x*x
    z=(1-nose_mix)*z+nose_mix*nose_plane
    rear_roof = (1 - smoothstep(22, 76, y)) * (1 - smoothstep(82, 143, abs(x)))
    return z + max(0., 54 - z) * rear_roof


def make_native_loft():
    vertices, faces = [], []
    # The first ring is the inner return wall, the last is the bottom skirt.
    rings = [("inner_return", 0.)] + [("surface",i/24) for i in range(25)] + [("outer_skirt", 1.)]
    for kind, fraction in rings:
        for index in range(SEGMENTS):
            theta = 2 * math.pi * index / SEGMENTS
            outer = radial_boundary(theta)
            radius = INNER_RADIUS + fraction * (outer - INNER_RADIUS)
            x, y = CENTER[0] + radius * math.cos(theta), CENTER[1] + radius * math.sin(theta)
            z = 52 if kind == "inner_return" else 3 if kind == "outer_skirt" else profile_height(fraction, x, y)
            vertices.append((x, y, z))
    for ring in range(len(rings) - 1):
        for index in range(SEGMENTS):
            nxt = (index + 1) % SEGMENTS
            faces.append((ring * SEGMENTS + index, (ring + 1) * SEGMENTS + index,
                          (ring + 1) * SEGMENTS + nxt, ring * SEGMENTS + nxt))
    obj = mesh_object("Native_Shield_Loft_Source", vertices, faces, "90_Construction_native_loft")
    obj["Construction"] = f"Polar correspondence between shield outline and R{INNER_RADIUS} inner opening"
    obj["Wall mm"] = WALL
    obj["Source points"] = json.dumps(PARAMETERS["outer_half_control_points"])
    # Recalc of an open annulus can select either global orientation. Ensure the
    # main sloping top has upward-facing normals before inward solidification.
    top_face = obj.data.polygons[SEGMENTS * 3]
    if top_face.normal.z < 0:
        bm = bmesh.new(); bm.from_mesh(obj.data)
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free()
    obj.hide_render = True
    return obj


def copy_mesh(obj, name):
    clone = bpy.data.objects.new(name, obj.data.copy())
    COLLECTIONS["01_Exterior_fit_parts"].objects.link(clone)
    return clone


def apply_modifier(obj, modifier):
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def make_solid_shell(source):
    obj = copy_mesh(source, "Native_Shield_Solid_Master")
    solidify = obj.modifiers.new("Nominal 3 mm wall inward", "SOLIDIFY")
    solidify.thickness = WALL * M
    solidify.offset = -1
    solidify.use_even_offset = True
    solidify.use_quality_normals = True
    apply_modifier(obj, solidify)
    recalc(obj)
    return obj


def box(name, bounds):
    lo, hi = bounds
    bpy.ops.mesh.primitive_cube_add(size=1, location=tuple((a + b) * .5 * M for a, b in zip(lo, hi)))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = tuple((b - a) * M for a, b in zip(lo, hi))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def contour_prism(name, contour, z_bounds=(-20,100)):
    n=len(contour)
    verts=[(x,y,z) for z in z_bounds for x,y in contour]
    faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh_object(name,verts,faces,"90_Construction_native_loft")


def light_lens(nose):
    # Independent closed optical blank. Intersecting the shell return wall
    # produced a second disconnected sliver in SHAPE-02, so it is not reused.
    temp=rounded_rect_prism("Lens planar contour",((-18.7,178.3),(18.7,183.7)),(0,1),2.4)
    n=len(temp.data.vertices)//2
    contour=[(v.co.x/M,v.co.y/M) for v in list(temp.data.vertices)[:n]]
    bpy.data.objects.remove(temp,do_unlink=True)
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(nose,bpy.context.evaluated_depsgraph_get())
    samples=[(0.,181.)]+[(x*f,181+(y-181)*f) for f in (.25,.5,.75,1.) for x,y in contour]
    ztop=[]
    for x,y in samples:
        hit,_,_,_=tree.ray_cast(Vector((x*M,y*M,.10)),Vector((0,0,-1)))
        if hit is None: raise ValueError('Lens sampling missed the actual nose surface')
        ztop.append(hit.z/M+.15)
    k=len(samples)
    verts=[(x,y,z-d) for d in (2.,0.) for (x,y),z in zip(samples,ztop)]
    surface=[(0,1+i,1+(i+1)%n) for i in range(n)]
    for r in range(3):
        a=1+r*n;b=a+n
        surface += [(a+i,b+i,b+(i+1)%n,a+(i+1)%n) for i in range(n)]
    faces=[tuple(reversed(f)) for f in surface]+[tuple(i+k for i in f) for f in surface]
    outer=1+3*n
    faces += [(outer+i,outer+(i+1)%n,outer+(i+1)%n+k,outer+i+k) for i in range(n)]
    return mesh_object("B05-306-LIGHT-LENS",verts,faces,"02_Light_lens_fit_part")


def boolean(obj, tool, operation):
    modifier = obj.modifiers.new(operation + " " + tool.name, "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "MANIFOLD"
    modifier.object = tool
    apply_modifier(obj, modifier)
    bpy.data.objects.remove(tool, do_unlink=True)
    recalc(obj)


def rounded_rect_prism(name, bounds_xy, z_bounds, radius, plane="XY"):
    (xmin, ymin), (xmax, ymax) = bounds_xy
    radius = min(radius, (xmax - xmin) / 2 - 1e-6, (ymax - ymin) / 2 - 1e-6)
    contour = []
    centers = [(xmax - radius, ymax - radius, 0), (xmin + radius, ymax - radius, 90),
               (xmin + radius, ymin + radius, 180), (xmax - radius, ymin + radius, 270)]
    for x, y, start in centers:
        for index in range(9):
            angle = math.radians(start + index * 90 / 8)
            contour.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    vertices = [(x, y, z) if plane == "XY" else (x, z, y) for z in z_bounds for x, y in contour]
    count = len(contour)
    faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
    for index in range(count):
        nxt = (index + 1) % count
        faces.append((index, nxt, nxt + count, index + count))
    return mesh_object(name, vertices, faces, "90_Construction_native_loft")


def bevel_and_shade(obj, width=.35):
    if width > 0:
        bevel = obj.modifiers.new("Small printable edge relief", "BEVEL")
        bevel.width = width * M
        bevel.segments = 3
        bevel.limit_method = "ANGLE"
        bevel.angle_limit = math.radians(26)
        bevel.use_clamp_overlap = True
        apply_modifier(obj, bevel)
    recalc(obj)
    obj.data.set_sharp_from_angle(angle=math.radians(27))
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def finalize_mesh(obj):
    # Native construction cleanup at 1 micrometre, far below prototype fit
    # allowances. This runs before export; the independent checker never repairs.
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.001 * M)
    bmesh.ops.dissolve_degenerate(bm, dist=0.001 * M, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    obj.data.set_sharp_from_angle(angle=math.radians(27))
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["Construction cleanup tolerance mm"] = 0.001


def collar():
    top=[(72,58.5),(70,59.5),(65,70),(63,73),(60,74),(52,74)]
    section=top+[(r,z-3.15) for r,z in reversed(top)]
    vertices = [(r * math.cos(2 * math.pi * i / SEGMENTS),
                 CENTER[1] + r * math.sin(2 * math.pi * i / SEGMENTS), z)
                for r, z in section for i in range(SEGMENTS)]
    faces = []
    for ring in range(len(section)):
        nxt_ring = (ring + 1) % len(section)
        for index in range(SEGMENTS):
            nxt = (index + 1) % SEGMENTS
            faces.append((ring * SEGMENTS + index, ring * SEGMENTS + nxt,
                          nxt_ring * SEGMENTS + nxt, nxt_ring * SEGMENTS + index))
    return mesh_object("B05-305-COLLAR", vertices, faces)


def material(name, color, metallic=.65, roughness=.29, emission=0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = color
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission:
        shader.inputs["Emission Color"].default_value = color
        shader.inputs["Emission Strength"].default_value = emission
    return mat


MATERIALS = {
    "armor": material("Graphite armor / finish reference", (.048, .059, .072, 1), .65, .29),
    "nose": material("Nose graphite / finish reference", (.048, .059, .072, 1), .65, .29),
    "rear": material("Rear enclosure graphite", (.035, .045, .056, 1), .58, .31),
    "collar": material("Titanium-grey collar", (.072, .084, .096, 1), .72, .26),
    "lens": material("Amber light-window appearance", (1., .28, .015, 1), .02, .25, 1.6),
}


def bounding_box_mm(obj):
    points = [obj.matrix_world @ Vector(p) for p in obj.bound_box]
    low = [min(p[i] for p in points) / M for i in range(3)]
    high = [max(p[i] for p in points) / M for i in range(3)]
    return {"min": low, "max": high, "size": [b - a for a, b in zip(low, high)]}


def write_stl(obj, path, translation_mm=(0, 0, 0)):
    # Explicit binary writer prevents exporter unit-setting ambiguity.
    mesh = obj.data
    mesh.calc_loop_triangles()
    with path.open("wb") as stream:
        stream.write((b"ODRADEK B05 millimetres; shape/fit prototype" + b" " * 80)[:80])
        stream.write(struct.pack("<I", len(mesh.loop_triangles)))
        for triangle in mesh.loop_triangles:
            points = [obj.matrix_world @ mesh.vertices[index].co for index in triangle.vertices]
            points = [Vector([p[i] / M + translation_mm[i] for i in range(3)]) for p in points]
            normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
            stream.write(struct.pack("<12fH", *normal, *points[0], *points[1], *points[2], 0))


def render_payload(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices, normals, faces = [], [], []
    normal_matrix = obj.matrix_world.to_3x3().inverted().transposed()
    for tri in mesh.loop_triangles:
        face = []
        for vertex_index, loop_index in zip(tri.vertices, tri.loops):
            face.append(len(vertices))
            vertices.append([v / M for v in obj.matrix_world @ mesh.vertices[vertex_index].co])
            normals.append(list((normal_matrix @ mesh.corner_normals[loop_index].vector).normalized()))
        faces.append(face)
    return {"vertices": vertices, "normals": normals, "faces": faces}


def export_part(obj, name_cn, role, mat_key, notes):
    finalize_mesh(obj)
    obj.data.materials.clear()
    obj.data.materials.append(MATERIALS[mat_key])
    obj["Part number"] = obj.name
    obj["Chinese name"] = name_cn
    obj["Status"] = "Shape review / unpowered fit prototype; mounting supports not included"
    obj["Nominal wall mm"] = WALL
    bbox = bounding_box_mm(obj)
    shift = [-v for v in bbox["min"]]
    write_stl(obj, OUT / "stl" / (obj.name + ".stl"))
    write_stl(obj, OUT / "print-parts" / (obj.name + ".stl"), shift)
    return {"id": obj.name, "name": name_cn, "category": "custom", "quantity": 1,
            "material": "PETG / ASA fit-prototype candidate; appearance finish only",
            "process": "3D print for unpowered fit; orientation/supports to be sliced",
            "color": list(MATERIALS[mat_key].diffuse_color), "color_space": "linear", "bbox": bbox,
            "stl": "stl/" + obj.name + ".stl", "print_stl": "print-parts/" + obj.name + ".stl",
            "print_translation_mm": shift, "viewer_group": "cover", "assembly_role": role,
            "wall_nominal_mm": WALL,
            "prototype_status": "外观与无动力试装原型；安装支座、实物装配及强度尚未验证",
            "notes": notes}


def render_setup():
    target = Vector((0, .080, .034))
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "Exterior_review_camera"
    move_collection(camera, "99_Render_only")
    camera.data.type = "ORTHO"
    camera.data.clip_start = .001
    camera.data.clip_end = 100
    SCENE.camera = camera
    for name, location, energy, size in (("Key softbox", (.2, .35, .55), 9, .4),
                                         ("Fill softbox", (-.4, .23, .28), 5, .35),
                                         ("Rear edge softbox", (.1, -.4, .3), 10, .3)):
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.name = name
        light.data.energy = energy
        light.data.shape = "DISK"
        light.data.size = size
        light.rotation_euler = (target - light.location).to_track_quat("-Z", "Y").to_euler()
        move_collection(light, "99_Render_only")
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.002))
    floor = bpy.context.object
    floor.name = "Render backdrop only"
    floor.data.materials.append(material("Warm neutral backdrop", (.30, .315, .325, 1), .05, .65))
    move_collection(floor, "99_Render_only")
    return camera, target


def point_camera(camera, location, target, scale):
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = scale


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for folder in ("stl", "print-parts"):
        (OUT / folder).mkdir(exist_ok=True)
    source = make_native_loft()
    master = make_solid_shell(source)
    specifications = [
        ("B05-301-ARMOR-L", "左主肩甲", ((-200, 30.4, -20), (-.4, 290, 100)), "armor", "cover"),
        ("B05-301-ARMOR-R", "右主肩甲", ((.4, 30.4, -20), (200, 290, 100)), "armor", "cover"),
        ("B05-302-NOSE", "前鼻与底座灯窗", ((-200, 30.4, -20), (200, 290, 100)), "nose", "cover"),
        ("B05-303-REAR-SHOULDER-L", "左后肩甲", ((-200, -80, -20), (-76.4, 29.6, 100)), "armor", "cover"),
        ("B05-303-REAR-SHOULDER-R", "右后肩甲", ((76.4, -80, -20), (200, 29.6, 100)), "armor", "cover"),
        ("B05-304-REAR-LID", "可拆后盖与下出线口", ((-75.6, -80, -20), (75.6, 29.6, 100)), "rear", "rear_lid"),
    ]
    objects, descriptors, payload = [], [], {}
    for pid, title, bounds, mat, role in specifications:
        print("Constructing", pid, flush=True)
        mirrored = pid.endswith("-R") and bpy.data.objects.get(pid[:-1] + "L") is not None
        if mirrored:
            obj = copy_mesh(bpy.data.objects[pid[:-1] + "L"], pid)
            for vertex in obj.data.vertices:
                vertex.co.x *= -1
            recalc(obj)
        else:
            obj = copy_mesh(master, pid)
            boolean(obj, box("Module split cutter", bounds), "INTERSECT")
            if pid == "B05-301-ARMOR-L":
                boolean(obj,contour_prism("Swept shoulder boundary",[(-200,30.4),(-.4,30.4),(-.4,144.6),(-200,96.6)]),"INTERSECT")
            if pid == "B05-302-NOSE":
                boolean(obj,contour_prism("Swept nose boundary",[(-200,97.4),(0,145.4),(200,97.4),(200,290),(-200,290)]),"INTERSECT")
        notes = ["Native Blender loft + inward 3 mm solidify + manifold Boolean partition",
                 "0.8 mm nominal panel seams; central collar/body radial gap 0.6 mm; new J1 axis XY(0,75), R70 flange reservation requires redesign",
                 "No load-bearing or manufacturing release; underside mounts are a separate integration task"]
        if pid == "B05-302-NOSE":
            lens = light_lens(obj)
            bevel_and_shade(lens, 0)
            move_collection(lens, "02_Light_lens_fit_part")
            objects.append(lens)
            descriptors.append(export_part(lens, "琥珀灯窗试装件", "cover", "lens",
                                           ["Separate lens contour, 0.3 mm nominal XY clearance", "Optical diffusion and lamp-board retention are not validated"]))
            payload[lens.name] = render_payload(lens)
            boolean(obj, rounded_rect_prism("Real light aperture", ((-19, 178), (19, 184)), (-20, 100), 2.7), "DIFFERENCE")
            notes.append("Real light aperture X -19..19, Y 178..184 mm; illumination cavity and PCB position remain integration work")
        if pid == "B05-304-REAR-LID":
            boolean(obj, rounded_rect_prism("Downward cable outlet", ((-42, -8), (42, 21)), (-60, -33), 4, "XZ"), "DIFFERENCE")
            notes.append("Actual rear-bottom cable exit, X ±42 mm, top Z 21 mm; cable comb and bend envelopes require integration")
        if not mirrored:
            # Dense curved loft edges already carry the exterior radius. A
            # mesh bevel across the thin Boolean cap can create sliver faces.
            bevel_and_shade(obj, 0)
        else:
            notes.append("Mirrored native left part for exact bilateral symmetry; face winding recalculated")
        objects.append(obj)
        descriptors.append(export_part(obj, title, role, mat, notes))
        payload[obj.name] = render_payload(obj)
    ring = collar()
    bevel_and_shade(ring, .38)
    objects.append(ring)
    descriptors.append(export_part(ring, "中央独立装甲环", "cover", "collar",
                                   ["R52 inner clearance; R72 outer radius; 144 mm print envelope",
                                    "3.15 mm vertical section thickness; top Z 74..58.5 mm", "Collar retention/supports are not included in this exterior module"]))
    payload[ring.name] = render_payload(ring)
    move_collection(master, "90_Construction_native_loft")
    source.hide_set(True); master.hide_set(True); master.hide_render = True
    bpy.data.texts.new("B05 exterior parameters.json").write(json.dumps(PARAMETERS, ensure_ascii=False, indent=2))
    bpy.data.texts.new("B05 read me.txt").write("Native Blender exterior construction. Seven armor parts plus one lens. All STL coordinates are global millimetres. Print-parts are translations only, not optimized orientations. Shape review and unpowered fit prototype only. No mounting, physical strength or finished assembly claim. Source loft and solid master remain in the hidden construction collection.")
    manifest = {"revision": "B05-EXTERIOR-SHAPE-04", "length_unit": "mm",
                "scope": PARAMETERS["prototype_scope"], "parameters": PARAMETERS,
                "parts": descriptors, "assembly_manifest": False,
                "not_verified": ["physical printing", "supports/overhangs", "minimum wall audit", "self-intersections",
                                 "mounting supports", "complete assembly clearance", "load", "optics", "cable routing"]}
    (OUT / "exterior-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    (OUT / "render-meshes.json").write_text(json.dumps(payload, separators=(",", ":")))
    camera, target = render_setup()
    point_camera(camera, (.39, .53, .34), target, .43)
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_distance = .52
                area.spaces.active.region_3d.view_location = target
                area.spaces.active.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
                area.spaces.active.clip_start = .001
                area.spaces.active.clip_end = 100
    for obj in objects:
        obj.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "ODR-BASE-B05-EXTERIOR.blend"))
    if "--no-render" not in sys.argv:
        views = [("front-three-quarter", (.39, .53, .34), .43),
                 ("top", (0, .080, .85), .40),
                 ("rear", (-.36, -.47, .26), .43)]
        for name, position, scale in views:
            point_camera(camera, position, target, scale)
            SCENE.render.filepath = str(OUT / (name + ".png"))
            bpy.ops.render.render(write_still=True)
        point_camera(camera, (.39, .53, .34), target, .43)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "ODR-BASE-B05-EXTERIOR.blend"))
    print("B05_NATIVE_EXTERIOR_COMPLETE", str(OUT), flush=True)


if __name__ == "__main__":
    main()
