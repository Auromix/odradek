# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek - Auromix contributors (https://github.com/Auromix/odradek)
"""Construct the B06 shield exterior as native Blender mesh geometry.

Run with Blender --background --python engineering/base_b06/blender_compact.py.
The editable .blend retains the native loft surface and construction parameters.
STLs use global assembly millimetres; print-parts are translated to XYZ >= 0.
These are unpowered exterior shape and fastening fit prototypes.
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
CENTER = (0.,75.)
SEGMENTS = 240
INNER_RADIUS = 84.
WALL = 3.
PARAMETERS = {
 "schema":"odradek.b06.compact.v1", "length_unit":"mm", "center_xy":CENTER,
 "wall_nominal_mm":WALL,
 "outer_half_control_points":[[0,-38],[76,-38],[97,-26],[114,-3],[119,15],[118,25],[108,38],[98,48],[96,63],[95,79],[98,89],[103,103],[105,117],[101,128],[86,145],[57,171],[25,182],[0,185]],
 "inner_body_radius_mm":84, "collar_radius_mm":[68,84], "collar_top_z_mm":[74,60],
 "design_intent":"One continuous four-petal-family manta shield; reduced wing span; no visible top fixing holes; integral neck",
 "prototype_scope":"Five printed cosmetic/PCB locating parts; A11 root snapshot and connector envelopes; no load chassis or PCB release",
 "printer_volume_mm":[256,256,256], "outer_limit_xy_mm":[240,230],
 "fastening":"Four underside M3x10 screws with captive M3 nuts; rear lid two bottom M3x10; lamp two M2x6",
}


def reset_scene():
    # This generator owns its entire dedicated exterior scene. Include hidden
    # construction objects so reruns do not accumulate duplicate loft masters.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in list(bpy.data.collections):
        if collection.name.startswith(("01_Exterior", "02_Light", "03_Exterior", "04_Purchased", "90_Construction", "99_Render")):
            bpy.data.collections.remove(collection)
    for text in list(bpy.data.texts):
        if text.name.startswith(("B06 exterior parameters.json", "B06 read me.txt")):
            bpy.data.texts.remove(text)
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
    scene["Geometry source"] = "Native Blender loft, solidify and exact Boolean operations; not imported CAD"
    scene["Units"] = "Blender SI metres with millimetre display; all exported STL coordinates are millimetres"
    return scene


SCENE = reset_scene()
COLLECTIONS = {}
for name in ("01_Exterior_fit_parts", "02_Light_lens_fit_part", "03_Exterior_mount_carriers", "04_Purchased_fasteners_reference", "90_Construction_native_loft", "99_Render_only"):
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
    # Boolean caps may retain a flattened tetrahedron attached along a
    # non-manifold edge. Remove only four-face/four-vertex fragments whose
    # shortest altitude is below the declared 10 micrometre construction grid.
    unseen=set(bm.faces)
    fragments=[]
    while unseen:
        face=unseen.pop(); component={face}; pending=[face]
        while pending:
            current=pending.pop()
            for edge in current.edges:
                if len(edge.link_faces)!=2: continue
                for adjacent in edge.link_faces:
                    if adjacent in unseen:
                        unseen.remove(adjacent); component.add(adjacent); pending.append(adjacent)
        vertices={v for f in component for v in f.verts}
        if len(component)==1 and len(vertices)==3:
            # A zero-volume triangle sheet may attach to a solid along an
            # edge with three incident faces; it has no manifold neighbour.
            fragments.extend(component)
        if len(component)==4 and len(vertices)==4:
            origin=next(iter(vertices)).co
            volume=abs(sum((f.verts[0].co-origin).dot((f.verts[1].co-origin).cross(f.verts[2].co-origin))/6 for f in component))
            largest_area=max(f.calc_area() for f in component)
            if largest_area and 3*volume/largest_area < .01*M:
                fragments.extend(component)
    obj["Submicrometre Boolean cap faces removed"]=len(fragments)
    if fragments: bmesh.ops.delete(bm,geom=fragments,context="FACES")
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


SURFACE_FRACTIONS=sorted(set([i/40 for i in range(41)]+[.69,.73,.77]))


def profile_height(fraction,x,y):
    r=math.hypot(x,y-CENTER[1])
    outer=INNER_RADIUS+(r-INNER_RADIUS)/fraction if fraction>1e-8 else INNER_RADIUS
    crown=60-.22*(r-INNER_RADIUS)
    chine_r=INNER_RADIUS+.69*(outer-INNER_RADIUS)
    chine_z=60-.22*(chine_r-INNER_RADIUS)
    edge_z=8+3*smoothstep(94,118,abs(x))
    apron=chine_z+(edge_z-chine_z)*(fraction-.69)/.31
    blend=smoothstep(.66,.72,fraction)
    z=crown*(1-blend)+apron*blend
    rear=(1-smoothstep(2,35,y))*(1-smoothstep(64,99,abs(x)))
    lifted=max(z,44)+max(0.,3-abs(z-44))**2/12
    return z*(1-rear)+lifted*rear


def make_native_loft():
    rings=[(68,68),(68,74),(71,73),(77,65),(84,60)]
    vertices=[(r*math.cos(2*math.pi*i/SEGMENTS),75+r*math.sin(2*math.pi*i/SEGMENTS),z) for r,z in rings for i in range(SEGMENTS)]
    fractions=sorted(set([i/40 for i in range(1,41)]+[.66,.69,.72]))
    for f in fractions:
        for i in range(SEGMENTS):
            t=2*math.pi*i/SEGMENTS;outer=radial_boundary(t)
            r=INNER_RADIUS+f*(outer-INNER_RADIUS);x=r*math.cos(t);y=75+r*math.sin(t)
            vertices.append((x,y,profile_height(f,x,y)))
    for i in range(SEGMENTS):
        t=2*math.pi*i/SEGMENTS;r=radial_boundary(t)
        vertices.append((r*math.cos(t),75+r*math.sin(t),3))
    count=len(rings)+len(fractions)+1
    faces=[(k*SEGMENTS+i,(k+1)*SEGMENTS+i,(k+1)*SEGMENTS+(i+1)%SEGMENTS,k*SEGMENTS+(i+1)%SEGMENTS) for k in range(count-1) for i in range(SEGMENTS)]
    o=mesh_object('Native_Shield_Loft_Source',vertices,faces,'90_Construction_native_loft')
    if o.data.polygons[SEGMENTS*7].normal.z<0:
        bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    o.hide_render=True
    return o


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
    temp=rounded_rect_prism("Lens planar contour",((-18.7,168.3),(18.7,173.7)),(0,1),2.4)
    n=len(temp.data.vertices)//2
    contour=[(v.co.x/M,v.co.y/M) for v in list(temp.data.vertices)[:n]]
    bpy.data.objects.remove(temp,do_unlink=True)
    from mathutils.bvhtree import BVHTree
    tree=BVHTree.FromObject(nose,bpy.context.evaluated_depsgraph_get())
    samples=[(0.,171.)]+[(x*f,171+(y-171)*f) for f in (.25,.5,.75,1.) for x,y in contour]
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
    return mesh_object("B06-306-LIGHT-LENS",verts,faces,"02_Light_lens_fit_part")


def boolean(obj, tool, operation):
    # Keep the editable scene in SI metres, but perform CSG in millimetres
    # to avoid tolerance artifacts in small screw seats on the curved loft.
    for operand in (obj, tool):
        bm = bmesh.new(); bm.from_mesh(operand.data)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(operand.data); bm.free()
        for vertex in operand.data.vertices: vertex.co *= 1000
        operand.location *= 1000
        operand.data.update()
    bpy.context.view_layer.update()
    modifier = obj.modifiers.new(operation + " " + tool.name, "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "MANIFOLD"
    modifier.object = tool
    apply_modifier(obj, modifier)
    for vertex in obj.data.vertices: vertex.co *= .001
    obj.location *= .001
    obj.data.update()
    bpy.data.objects.remove(tool, do_unlink=True)
    bpy.context.view_layer.update()
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
    # Native construction cleanup at 10 micrometre, far below prototype fit
    # allowances. This runs before export; the independent checker never repairs.
    cleanup_mm = .01 if obj.name == "B06-301-MAIN-SHIELD" else .001
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Snap construction vertices to the same 10 micrometre grid before welding.
    # This avoids near-coincident cap slivers splitting after float32 STL export.
    for v in bm.verts:
        v.co = Vector([round(c / M, 2 if cleanup_mm == .01 else 3) * M for c in v.co])
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=cleanup_mm * M)
    bmesh.ops.dissolve_degenerate(bm, dist=cleanup_mm * M, edges=list(bm.edges))
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    # Boolean clipping can leave an pair of coincident opposite
    # triangles (zero enclosed volume). Remove only that exact zero-volume artifact;
    # preserve all legitimate disconnected solids so validation can reject them.
    bm.verts.index_update()
    bm.normal_update()
    groups={}
    for f in bm.faces:
        groups.setdefault(tuple(sorted(v.index for v in f.verts)),[]).append(f)
    artifacts=[]
    for pair in groups.values():
        if len(pair)==2 and all(len(f.verts)==3 for f in pair):
            if pair[0].normal.dot(pair[1].normal)<-0.99999:
                artifacts.extend(pair)
    obj["Zero-volume Boolean artifact faces removed"]=len(artifacts)
    if artifacts:
        bmesh.ops.delete(bm,geom=artifacts,context="FACES")
    # Partition clipping can also leave one isolated triangle sheet. Such a
    # sheet encloses no solid and is not part of this closed-shell design.
    # Keep all multi-face disconnected components for the independent gate.
    sheets=[f for f in bm.faces if len(f.verts)==3 and all(len(e.link_faces)==1 for e in f.edges)]
    obj["Isolated Boolean triangle sheets removed"]=len(sheets)
    if sheets: bmesh.ops.delete(bm,geom=sheets,context="FACES")
    # Boolean caps may retain a flattened tetrahedron attached along a
    # non-manifold edge. Remove only four-face/four-vertex fragments whose
    # shortest altitude is below the declared 10 micrometre construction grid.
    unseen=set(bm.faces)
    fragments=[]
    while unseen:
        face=unseen.pop(); component={face}; pending=[face]
        while pending:
            current=pending.pop()
            for edge in current.edges:
                if len(edge.link_faces)!=2: continue
                for adjacent in edge.link_faces:
                    if adjacent in unseen:
                        unseen.remove(adjacent); component.add(adjacent); pending.append(adjacent)
        vertices={v for f in component for v in f.verts}
        if len(component)==1 and len(vertices)==3:
            # A zero-volume triangle sheet may attach to a solid along an
            # edge with three incident faces; it has no manifold neighbour.
            fragments.extend(component)
        if len(component)==4 and len(vertices)==4:
            origin=next(iter(vertices)).co
            volume=abs(sum((f.verts[0].co-origin).dot((f.verts[1].co-origin).cross(f.verts[2].co-origin))/6 for f in component))
            largest_area=max(f.calc_area() for f in component)
            if largest_area and 3*volume/largest_area < .01*M:
                fragments.extend(component)
    obj["Submicrometre Boolean cap faces removed"]=len(fragments)
    if fragments: bmesh.ops.delete(bm,geom=fragments,context="FACES")
    # Native Boolean edges below the declared 10 micrometre construction
    # grid collapse when encoded in float32 STL. Dissolve them in the native
    # source, before export; never repair a failed STL after the fact.
    bmesh.ops.dissolve_degenerate(bm, dist=cleanup_mm*M, edges=list(bm.edges))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    # Retriangulate coplanar Boolean caps as polygons so collinear inserted
    # vertices cannot leave zero-altitude triangles in the exported source.
    for _ in range(2):
        bm=bmesh.new();bm.from_mesh(obj.data)
        bmesh.ops.dissolve_limit(bm,angle_limit=1e-6,verts=list(bm.verts),edges=list(bm.edges),delimit={'NORMAL'})
        bmesh.ops.triangulate(bm,faces=list(bm.faces))
        bmesh.ops.dissolve_degenerate(bm,dist=(.01 if obj.name == "B06-301-MAIN-SHIELD" else .001)*M,edges=list(bm.edges))
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(obj.data);bm.free()
    obj.data.update()
    obj.data.set_sharp_from_angle(angle=math.radians(27))
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj["Construction cleanup tolerance mm"] = cleanup_mm


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
    "armor": material("Graphite armor / finish reference", (.048, .059, .072, 1), .58, .36),
    "nose": material("Nose graphite / finish reference", (.048, .059, .072, 1), .58, .36),
    "rear": material("Rear enclosure graphite", (.035, .045, .056, 1), .58, .31),
    "collar": material("Titanium-grey collar", (.072, .084, .096, 1), .72, .26),
    "support": material("Black exterior carrier",(.022,.030,.040,1),.15,.46),
    "hardware": material("Black screw hardware",(.016,.021,.027,1),.65,.34),
    "nut": material("Purchased nut reference",(.18,.21,.25,1),.75,.32),
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
        stream.write((b"ODRADEK B06 millimetres; shape/fit prototype" + b" " * 80)[:80])
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
    # Final closed source part only: tiny Boolean edges are below the10um
    # construction grid and collapse in float32STL. Do not touch open lofts
    # or intermediate Boolean cutters with this operation.

    finalize_mesh(obj)
    obj.data.materials.clear()
    obj.data.materials.append(MATERIALS[mat_key])
    obj["Part number"] = obj.name
    obj["Chinese name"] = name_cn
    obj["Status"] = "Shape and exterior fastening trial; full chassis and PCB not integrated"
    obj["Nominal wall mm"] = WALL if role != "cover_support" else 0
    bbox = bounding_box_mm(obj)
    shift = [-v for v in bbox["min"]]
    write_stl(obj, OUT / "stl" / (obj.name + ".stl"))
    write_stl(obj, OUT / "print-parts" / (obj.name + ".stl"), shift)
    return {"id": obj.name, "name": name_cn, "category": "custom", "quantity": 1,
            "material": "PETG / ASA fit-prototype candidate; appearance finish only",
            "process": "3D print for unpowered fit; orientation/supports to be sliced",
            "color": list(MATERIALS[mat_key].diffuse_color), "color_space": "linear", "bbox": bbox,
            "stl": "stl/" + obj.name + ".stl", "print_stl": "print-parts/" + obj.name + ".stl",
            "print_translation_mm": shift, "viewer_group": "cover_support" if role=="cover_support" else "cover", "assembly_role": role,
            "wall_nominal_mm": WALL if role != "cover_support" else None,
            "prototype_status": "外罩紧固试装候选；实物装配、整机集成及强度尚未验证",
            "notes": notes}


def render_setup():
    target = Vector((0, .075, .037))
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
