# SPDX-License-Identifier: CC-BY-NC-4.0
"""One-time metadata-only provenance correction, with byte-equivalent geometry.
The incremental cover build omitted P01 from changed_parts; its actual drilled
geometry and source-bound tests were already correct. No CAD/STL is altered.
"""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a11/build'
def packed(d):return (json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(data):return hashlib.sha256(data).hexdigest()
path=OUT/'manifest.json';raw=path.read_bytes();oldsha=sha(raw);d=json.loads(raw)
assert oldsha=='f44e1f225fdf5b64d11ccb011156371719717feee68ee1394279e62654f0b638'
assert 'P01-shoulder-monobloc' not in d['changed_parts']
geo={k:v for k,v in d.items() if k!='changed_parts'};gsha=sha(packed(geo))
d['changed_parts'].append('P01-shoulder-monobloc');newraw=packed(d);newsha=sha(newraw)
reverse=json.loads(newraw);reverse['changed_parts'].remove('P01-shoulder-monobloc');assert sha(packed(reverse))==oldsha
assert sha(packed({k:v for k,v in d.items() if k!='changed_parts'}))==gsha
proof=dict(old_manifest_sha256=oldsha,new_manifest_sha256=newsha,changed_fields=['changed_parts'],addition='P01-shoulder-monobloc',all_other_manifest_fields_identical=True,geometry_and_parameters_sha256=gsha,step_and_stl_modified=False,scope='Index metadata only. Existing intersection/print/tool/FK results apply to byte-identical geometry and parameters; native files and viewer metadata are refreshed separately.')
path.write_bytes(newraw)
for file in ['print-audit.json','feasibility.json','collision-supplier.json','motion-audit.json','tool-access-audit.json','blender-audit.json','blender-audit-actual.json','base-context-audit.json','render-source.json']:
 p=OUT/file;r=json.loads(p.read_text());assert r['manifest_sha256']==oldsha;r['manifest_sha256']=newsha;r['metadata_only_source_correction']=proof;p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
p=OUT/'parts.json';r=json.loads(p.read_text());r['changed_parts']=d['changed_parts'];p.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
(OUT/'metadata-correction.json').write_text(json.dumps(proof,indent=2)+'\n')
print('METADATA_ONLY',oldsha,newsha)
