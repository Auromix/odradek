# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bind current base review assets into one archive, never a production release."""
from pathlib import Path
import hashlib,json,zipfile,argparse
parser=argparse.ArgumentParser();parser.add_argument('--candidate',action='store_true');args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'engineering/base_b06';E=B/'build/exterior'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=json.loads((B/'build/base-only-verification.json').read_text())
assert checks['arm_required'] is False and checks['production_released'] is False
if not args.candidate:assert checks['pass']
else:
    assert not checks['pass'] and checks['scope']=='Partial digital candidate review; native PCB DRC unresolved'
assert checks['manifest_sha256']==sha(E/'manifest.json')
assert json.loads((B/'build/qualification/qualification-status.json').read_text())['production_released'] is False
files=[]
files += [p for p in B.iterdir() if p.is_file() and p.suffix in ('.md','.json')]
files += [p for p in (B/'build').iterdir() if p.is_file() and p.suffix in ('.json','.csv') and p.name!='review-package-checks.json']
files += [p for p in E.iterdir() if p.is_file() and p.suffix in ('.blend','.json','.png','.html','.txt')]
for folder in (E/'print-parts',E/'slice-review',B/'build/load-frame',B/'build/standalone-test',B/'build/qualification'):
    files += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
io=ROOT/'engineering/electronics/base-io-b05';lamp=ROOT/'engineering/electronics/base-light-b06'
for folder in (io/'base-io-b05',io/'manufacturing/b06-io-control01',io/'local5v',io/'controller',lamp/'manufacturing'):
    files += [p for p in folder.rglob('*') if p.is_file() and p.suffix not in ('.bak','.zipbak') and '.history' not in p.parts and '__pycache__' not in p.parts]
files += [io/'reports/b06-routed-audit.json',lamp/'pin-nets.json',lamp/'README.md',io/'README.md']
files += [io/'reports/b06-controller-native-audit.json',io/'reports/b06-controller-fit.json',io/'reports/control01-native-drc0.png']
audit=json.loads((io/'reports/b06-controller-native-audit.json').read_text())
fit=json.loads((io/'reports/b06-controller-fit.json').read_text())
assert audit['candidate_data_consistent'] and fit['pass']
assert fit['hashes'][str((E/'manifest.json').relative_to(ROOT))]==sha(E/'manifest.json')
files=sorted(set(files));assert all(p.is_file() for p in files)
readme='''B06-COMPACT-07-DFM / CURRENT ENGINEERING REVIEW ASSETS
NOT A PRODUCTION OR POWERED-OPERATION RELEASE. Physical tests: 0/21.
No arm model is required. Product print parts: five; test fixture is separate metal hardware.
Start: engineering/base_b06/standalone-validation.md and interface-contract.json.
Models: native Blender, structural STEP, five printable STL, standalone fixture STEP.
Two native JLCEDA PCBs and fabrication candidates included. Local48V-to-5V supply
and STM32 PWM candidate implemented in IO board. No current/GMSL rating inferred.
CONTROL-01 native PCB DRC0 and current manufacturing files audited.
Use manufacturing/b06-io-control01 ONLY; historical LOCAL5V files are excluded.
Firmware/host digital tests are NOT physical board tests. First-article validation required.
Schematic warnings remain open. EDA STEP is BoardOnly, not a full component-model assembly.
Offline 3D viewers embed meshes. Reference Orca 3MF includes P1S G-code:
select the actual printer and reslice before use; never run reference G-code blindly.
This asset packet is for review/fit preparation; editable generators live in the same repository.
Seven definition gates remain open; all physical measurements are blank.
CC-BY-NC-4.0 / Auromix contributors.
'''
manifest={'revision':'B06-COMPACT-07-DFM','arm_required':False,'production_released':False,
    'review_kind':'BLOCKED_CONTROL01_CANDIDATE' if args.candidate else 'DIGITAL_REVIEW',
    'IO_DRC_error_count':audit['drc_error_count'],
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
out=B/'build'/('B06-control01-candidate-review.zip' if args.candidate else 'B06-standalone-engineering-review.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('READ-ME-FIRST.txt',readme);z.writestr('ASSET-HASHES.json',json.dumps(manifest,indent=2)+'\n')
    for p in files:z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h
(B/'build/review-package-checks.json').write_text(json.dumps({'pass':True,'archive_sha256':sha(out),'asset_count':len(files),'arm_required':False,'production_released':False},indent=2)+'\n')
print('ENGINEERING_REVIEW_PACKAGE',len(files),out.stat().st_size)
