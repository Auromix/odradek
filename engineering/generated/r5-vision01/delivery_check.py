# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read-only delivery/provenance checks; does not replace the geometry proof."""
from pathlib import Path
import argparse, hashlib, json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true',help='Re-lock regenerated artifacts only after source/record consistency checks pass');args=parser.parse_args()
if args.refresh:
 paths=[p for p in OUT.iterdir() if p.is_file() and p.name!='verification.json']+[ROOT/'engineering/r5_vision01.py',ROOT/'docs/engineering/r5-vision01.md',ROOT/'docs/engineering/sources/r5-vision01.json']
 report=dict(revision='R5-VISION01',artifact_hash_scope='Current review artifacts; STEP timestamps/SVG IDs may change on regeneration; no byte-deterministic replay claim',artifacts={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)})
else:report=read(OUT/'verification.json')
study=read(OUT/'study.json');checks=[]
def check(name,condition):
 checks.append((name,bool(condition)));assert condition,name
for path,digest in report['artifacts'].items():check('artifact '+path,sha(ROOT/path)==digest)
for path,digest in study['source_hashes'].items():check('source '+path,sha(ROOT/path)==digest)
check('physical camera solids',study['inputs']['physical_solids']==12)
check('native camera containment',study['inputs']['native_outside_original_proxy_mm3']<1e-4)
check('CD actual object count',study['inputs']['central_actual_objects']==331)
check('CD actual containment',max(r['outside_mm3'] for r in study['inputs']['central_containment'])<1e-4)
grid=read(OUT/'finite-position-screen.json');check('finite grid count',len(grid)==35)
check('baseline real native collision',any('native_camera' in r['a'] and r['intersection_mm3']>100 for r in grid[0]['hits']))
proofs=read(OUT/'mechanical-certificates.json')
for name,p in proofs.items():
 check(name+' record count',len(p['nonrotor_certificates'])==720 and len(p['rotor_plane_certificates'])==36)
 check(name+' certified',p['certified'])
 check(name+' individual continuous certificates',all(x['certified'] and x['continuous_gap_lower_mm']>0 for x in p['nonrotor_certificates']))
 check(name+' analytical rotor separation',min(x['continuous_Z_gap_mm'] for x in p['rotor_plane_certificates'])>0)
 check(name+' camera/CD self separation',min(x['distance_mm'] for x in p['optics_internal_checks'])>0)
rays=read(OUT/'sightline-screen.json');check('conditional view cases',len(rays['cases'])==15)
check('ray count',sum(len(c['rays']) for x in rays['cases'] for c in x['cameras'])==3000)
for x in rays['cases']:
 for row in x['summary']:
  check('logical union '+x['state']+'/'+str(x['pupil_native_z_mm'])+'/'+str(row['target_z_mm']),row['either_clear']+row['both_clear']==row['upper_clear']+row['lower_clear'])
minimum=next(x for x in rays['cases'] if x['state']=='minimum50' and x['pupil_native_z_mm']==14)
check('failure domain retained',next(r for r in minimum['summary'] if r['target_z_mm']==65)['either_clear']==9)
check('not manufacturing release',study['manufacturing_release'] is False)
check('no old optical frame inheritance',study['selected_comparison']['old_optical_frame_inherited'] is False)
if args.refresh:
 report['checks_passed']=len(checks);report['physical_validation']=False
 (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'failed':0,'scope':'Artifact hashes, recorded exact-geometry certificate conditions and ray bookkeeping; not hardware/optical qualification'},indent=2))
