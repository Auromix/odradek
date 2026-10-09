# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bed-orient wrist cosmetic fit STLs only; no load/operating release."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 d=json.loads((OUT/'manifest.json').read_text());folder=OUT/'fit-print';folder.mkdir(exist_ok=True);records=[]
 for p in d['parts']:
  source=OUT/'stl-object'/(p['id']+'.stl');assert sha(source)==p['stl_sha256'];m=trimesh.load_mesh(source,process=True)
  assert m.is_watertight and m.is_winding_consistent
  axis=[1,0,0] if 'J7-' in p['id'] else [0,1,0]
  angle=(np.pi/2 if 'J7-' in p['id'] else -np.pi/2)*(1 if p['id'].endswith('-A') else -1)
  matrix=trimesh.transformations.rotation_matrix(angle,axis);m.apply_transform(matrix);shift=-m.bounds[0];m.apply_translation(shift)
  assert np.all(m.bounds[0]>=-1e-5) and np.all(np.ptp(m.vertices,axis=0)<180)
  path=folder/(p['id']+'.stl');m.export(path);r=trimesh.load_mesh(path,process=True)
  assert r.is_watertight and r.is_winding_consistent and abs(r.volume-m.volume)<max(.01,m.volume*1e-5)
  records.append(dict(id=p['id'],source_sha256=sha(source),bed_stl_sha256=sha(path),rotation_matrix=matrix.tolist(),translation_mm=shift.tolist(),bed_dimensions_mm=np.ptp(m.vertices,axis=0).tolist(),cad_solid_volume_mm3=p['volume_mm3'],petg_solid_mass_estimate_kg=p['volume_mm3']*1.27e-6))
 (OUT/'fit-print-manifest.json').write_text(json.dumps(dict(wrist_manifest_sha256=sha(OUT/'manifest.json'),units='mm',parts=records,orientation='Split face down, each part separately. Orientation candidate only; slicer/support review and machine process pending.',material='PETG cosmetic fit prototype assumption; density 1.27g/cm3 for solid mass estimate, not measured or selected vendor',hardware='Reuse six M3x20 through screws, six M3 hex nuts and twelve nominal 0.5mm flat washers from A11',release='Unpowered supported wrist-cover fit trials ONLY; liners/retention/thermal and whole-arm fit pending'),indent=2)+'\n')
 print('FIT_PRINT',len(records),'parts',sum(x['petg_solid_mass_estimate_kg'] for x in records),'kg nominal solid PETG')
if __name__=='__main__':main()
