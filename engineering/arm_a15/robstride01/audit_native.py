# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen and check exact candidate-model scene against CAD tessellation."""
from pathlib import Path
import bpy, json, math
ROOT=Path(__file__).resolve().parents[3]
CACHE=ROOT/'work/arm-a15/robstride'
HERE=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(CACHE/'RS02-RS10P-exact-inspection.blend'),use_scripts=False)
rows=[]
for d in json.loads((CACHE/'inspection-meshes.json').read_text()):
    o=bpy.data.objects[d['model']]
    assert o.type=='MESH' and tuple(o.scale)==(1.,1.,1.) and len(o.modifiers)==0
    assert len(o.data.vertices)==len(d['vertices_mm']) and len(o.data.polygons)==len(d['triangles'])
    error=max(math.dist([v*1000 for v in p.co],q) for p,q in zip(o.data.vertices,d['vertices_mm']))
    assert error<.005
    assert all(list(p.vertices)==q for p,q in zip(o.data.polygons,d['triangles']))
    assert o['source_sha256']==d['source_sha256'] and not o['assembly_datum_verified']
    rows.append(dict(model=d['model'],vertices=len(o.data.vertices),triangles=len(o.data.polygons),max_local_vertex_error_mm=error,object_scale=list(o.scale),modifiers=len(o.modifiers)))
assert bpy.context.scene['production_release']==False
assert len([o for o in bpy.data.objects if o.type=='MESH'])==2
(HERE/'build/native-audit.json').write_text(json.dumps(dict(revision='A15-RS01',reopened_with_scripts_disabled=True,models=rows,scene_scope='Raw exact supplier inspection, not arm assembly',production_release=False),indent=2)+'\n')
print('NATIVE_EXACT_GEOMETRY_VERIFIED',rows)
