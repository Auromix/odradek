# SPDX-License-Identifier: CC-BY-NC-4.0
"""Export per-CAD-face tessellation with analytic surface normals for rendering.
Geometry is unchanged; separate vertices preserve holes and section boundaries.
"""
from pathlib import Path
import json
import cadquery as cq
ROOT=Path(__file__).resolve().parent/'build'
result={}
for name in ['B04-301-COVER-FRONT','B04-301-COVER-REAR','B04-302-LIGHT-LENS']:
    shape=cq.importers.importStep(str(ROOT/'parts'/(name+'.step'))).val()
    vertices=[];faces=[];normals=[]
    for face in shape.Faces():
        vs,fs=face.tessellate(.035,.09)
        offset=len(vertices)
        for v in vs:
            vertices.append(v.toTuple());normals.append(face.normalAt(v).toTuple())
        faces.extend([[i+offset for i in f] for f in fs])
    result[name]={'vertices':vertices,'faces':faces,'normals':normals}
    print(name,len(vertices),len(faces),flush=True)
(ROOT/'cad-surface-meshes.json').write_text(json.dumps(result,separators=(',',':')))
