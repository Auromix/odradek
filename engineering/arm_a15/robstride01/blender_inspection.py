# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact candidate supplier models in a local Blender inspection scene."""
import bpy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CACHE=ROOT/'work/arm-a15/robstride'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
material=bpy.data.materials.new('inspection graphite');material.diffuse_color=(.16,.22,.28,1)
for i,d in enumerate(json.loads((CACHE/'inspection-meshes.json').read_text())):
    m=bpy.data.meshes.new(d['model']+' exact supplier STEP tessellation')
    m.from_pydata([[v/1000 for v in p] for p in d['vertices_mm']],[],d['triangles']);m.update()
    o=bpy.data.objects.new(d['model'],m);scene.collection.objects.link(o)
    o.location.x=i*.13;o.data.materials.append(material)
    o['source_sha256']=d['source_sha256'];o['linear_scale']=1.;o['assembly_datum_verified']=False
    o['scope']='Raw supplier coordinates, side by side for geometry inspection. Not an arm assembly.'
scene['revision']='A15-RS01 candidate exact STEP inspection'
scene['supplier']='RobStride only';scene['selection_frozen']=False;scene['production_release']=False
bpy.ops.wm.save_as_mainfile(filepath=str(CACHE/'RS02-RS10P-exact-inspection.blend'))
print('SAVED_EXACT_SUPPLIER_INSPECTION')
