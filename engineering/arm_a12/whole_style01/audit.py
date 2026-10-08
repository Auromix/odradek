# SPDX-License-Identifier: CC-BY-NC-4.0
"""Scoped style-mesh and supplier-invariance audit; no assembly qualification."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'style-surfaces.json').read_text());results=[]
for p in d['style_surfaces']:
 t=trimesh.Trimesh(p['vertices_mm'],p['triangles'],process=False)
 r=dict(id=p['id'],watertight=bool(t.is_watertight),winding_consistent=bool(t.is_winding_consistent),positive_volume=bool(t.volume>0),components=len(t.split(only_watertight=False)))
 assert r['watertight'] and r['winding_consistent'] and r['positive_volume'] and r['components']==1,r
 results.append(r)
actual=json.loads((ROOT/'work/arm-a12/whole-style01/actual-viewer.json').read_text());got={p['id']:p for p in actual['long']['parts']};errors=[]
for p in json.loads((ROOT/'work/arm-a10/vendor/meshes.json').read_text()):
 q=got[p['id']];a=np.array(p['vertices_mm']);b=np.array(q['vertices']);assert a.shape==b.shape
 e=float(np.max(np.linalg.norm(a-b,axis=1)));assert e<.003,(p['id'],e)
 assert np.array_equal(p['triangles'],q['faces']),(p['id'],'topology changed')
 errors.append(dict(id=p['id'],model=p['model'],source_sha256=p['source_sha256'],export_vertex_error_mm=e))
public=json.loads((ROOT/'work/arm-a12/whole-style01/public-viewer.json').read_text());assert all(p['role']!='supplier_visual_reference' for p in public['long']['parts'])
assert actual['long']['layout']==public['long']['layout']==d['layout']
for package in [actual,public]:
 for p in package['long']['parts']:
  if p['role']=='head_reference':assert max(abs(v) for xyz in p['vertices'] for v in xyz)<400,(p['id'],'reference transform invalid')
r=dict(scope='Closed owned style meshes and actual supplier invariance ONLY',style_mesh_checks=results,supplier_groups=errors,seven_axis_layout_identical=True,public_supplier_groups=0,actual_native_sha256=actual['long']['sha256'],public_native_sha256=public['long']['sha256'],style_manifest_sha256=sha(OUT/'style-surfaces.json'),base_native_sha256=d['base_native_sha256'],full_collision_check=False,connected_harness_check=False,print_release=False,load_3kg_qualified=False)
(OUT/'audit.json').write_text(json.dumps(r,indent=2)+'\n');print('AUDIT',len(results),'closed style meshes;',len(errors),'unchanged exact supplier groups; max export error',max(p['export_vertex_error_mm'] for p in errors))
