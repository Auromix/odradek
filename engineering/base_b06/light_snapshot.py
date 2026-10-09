# SPDX-License-Identifier: CC-BY-NC-4.0
"""Tessellate the actual saved JLCEDA STEP; do not fabricate missing models."""
from pathlib import Path
import json, hashlib
import cadquery as cq
import trimesh
HERE=Path(__file__).resolve().parent
source=HERE.parent/'electronics/base-light-b06/manufacturing/B06-LIGHT-PWM.step'
shape=cq.importers.importStep(str(source)).val()
parts=[]
for i,s in enumerate(shape.Solids(),1):
    if not s.isValid():raise ValueError('Invalid native solid '+str(i))
    v,t=s.tessellate(.03,.1)
    # STEP tessellation repeats seam vertices per CAD face. Weld coincident
    # coordinates before Blender recalculates normals; never fill/repair holes.
    mesh=trimesh.Trimesh(vertices=[[p.x-25,168.5+p.y,44.073+p.z] for p in v],faces=t,process=True)
    mode='native_STEP_tessellation'
    if not mesh.is_watertight or not mesh.is_winding_consistent:
        # Some valid supplier-library BREP surfaces tessellate with coincident
        # seams. Do not repair them. A labelled, larger closed box is conservative
        # for static clearance only; preserve the untouched STEP as the source.
        b=s.BoundingBox()
        mesh=trimesh.creation.box(extents=[b.xlen,b.ylen,b.zlen])
        mesh.apply_translation([(b.xmin+b.xmax)/2-25,168.5+(b.ymin+b.ymax)/2,44.073+(b.zmin+b.zmax)/2])
        mode='conservative_native_BREP_bounding_box'
    parts.append(dict(id=f'LIGHT-NATIVE-{i:02d}',vertices_mm=mesh.vertices.tolist(),triangles=mesh.faces.tolist(),
                      volume_mm3=s.Volume(),geometry_mode=mode))
data=dict(source=str(source.relative_to(HERE.parent.parent)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
          transform='(u-25,168.5+v,44.073+w); STEP v is negative',parts=parts,
          limits=['Library STEP geometry, not supplier-certified models; solder, crimp and cable omitted.',
                  'No automatic model generation was enabled for the native export.'])
(HERE/'inputs/light-snapshot.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
print('Native light STEP solids',len(parts))
