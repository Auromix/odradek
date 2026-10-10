# SPDX-License-Identifier: CC-BY-NC-4.0
"""Strict compatibility for one unused historical catalogue diameter correction.
Numerical/geometry reports are retained unchanged, never relabelled as reruns.
"""
from pathlib import Path
import json,hashlib,copy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25';ASSEMBLY=OUT/'manifest.json';BRIDGE=OUT/'catalogue-binding50.json';BASE=OUT/'baselines/assembly25-before-catalogue50.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def validate():
 if not BRIDGE.exists():return None
 b=json.loads(BRIDGE.read_text());old=json.loads(BASE.read_text());new=json.loads(ASSEMBLY.read_text());expected=copy.deepcopy(old)
 assert expected['layout']['joints'][4]['model']=='RS03'and expected['layout']['joints'][4]['diameter_mm']==57
 expected['layout']['joints'][4]['diameter_mm']=106
 assert expected==new,'Compatibility is limited to exactly one catalogue metadata field'
 assert b['historical_assembly_sha256']==sha(BASE)and b['current_assembly_sha256']==sha(ASSEMBLY)
 return b
def assembly_compatible(digest):
 if digest==sha(ASSEMBLY):return True
 b=validate();return bool(b and digest==b['historical_assembly_sha256'])
def require_source_digest(path,digest):
 path=Path(path)
 if path.resolve()==ASSEMBLY.resolve() and assembly_compatible(digest):return
 assert sha(path)==digest,str(path)
def apply():
 assert not BRIDGE.exists(),'Apply once; subsequent calls use validate()'
 old=json.loads(ASSEMBLY.read_text());assert old['layout']['joints'][4]['model']=='RS03'and old['layout']['joints'][4]['diameter_mm']==57
 BASE.write_bytes(ASSEMBLY.read_bytes());old_sha=sha(BASE);new=copy.deepcopy(old);new['layout']['joints'][4]['diameter_mm']=106;ASSEMBLY.write_text(json.dumps(new,indent=2)+'\n')
 b=dict(revision='A19-CATALOGUE-METADATA-BINDING50',historical_assembly_path=str(BASE.relative_to(ROOT)),historical_assembly_sha256=old_sha,current_assembly_sha256=sha(ASSEMBLY),field='layout.joints[4].diameter_mm',before=57,after=106,model='RS03',reference='RS03 catalogue nominal106mm. Native1:1STEP interfaces used throughout CAD, never this old display diameter.',all_other_JSON_fields_identical=True,all_part_STEP_paths_hashes_frames_and_mass_budget_identical=True,axis_offsets_limits_zero_and_poses_identical=True,evidence_policy='Prior reports retain original assembly hashes and numerical results; strict validator accepts only this single unused catalogue metadata change. No numerical check or render claimed rerun because of metadata. Manufacturing package carries both assembly inputs and this bridge.',production_release=False)
 BRIDGE.write_text(json.dumps(b,indent=2)+'\n');validate();print('BINDING50',old_sha,b['current_assembly_sha256'])
if __name__=='__main__':
 if BRIDGE.exists():validate();print('BINDING50_VALID')
 else:apply()
