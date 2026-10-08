# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopened Blender surface check of the exterior-only frame halves.
This checks surface intersections, not enclosed-solid containment or strength.
"""
import bpy,json,hashlib
from pathlib import Path
from mathutils.bvhtree import BVHTree
out=Path(bpy.data.filepath).parent
m=out/'exterior-manifest.json';D=json.loads(m.read_text())
dg=bpy.context.evaluated_depsgraph_get()
a=bpy.data.objects['B05-307-FRAME-L'];b=bpy.data.objects['B05-307-FRAME-R']
def tree(o):
 ev=o.evaluated_get(dg);mesh=ev.to_mesh();verts=[o.matrix_world@v.co for v in mesh.vertices];faces=[p.vertices[:] for p in mesh.polygons]
 t=BVHTree.FromPolygons(verts,faces,all_triangles=False,epsilon=0);ev.to_mesh_clear();return t
pairs=tree(a).overlap(tree(b))
r=dict(revision=D['revision'],manifest_sha256=hashlib.sha256(m.read_bytes()).hexdigest(),scope='Frame halves native surface intersection only',triangle_overlap_pairs=len(pairs),no_surface_intersections=not pairs,containment_checked=False,tool_access_checked=False,physical_assembly_checked=False)
(out/'frame-clearance-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
