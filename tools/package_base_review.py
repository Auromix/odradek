# SPDX-License-Identifier: CC-BY-NC-4.0
"""Bind current base review assets into one archive, never a production release."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'engineering/base_b06';E=B/'build/exterior'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=json.loads((B/'build/base-only-verification.json').read_text())
assert checks['pass'] and checks['arm_required'] is False and checks['production_released'] is False
assert checks['manifest_sha256']==sha(E/'manifest.json')
assert json.loads((B/'build/qualification/qualification-status.json').read_text())['production_released'] is False
files=[]
files += [p for p in B.iterdir() if p.is_file() and p.suffix in ('.md','.json')]
files += [p for p in (B/'build').iterdir() if p.is_file() and p.suffix in ('.json','.csv') and p.name!='review-package-checks.json']
files += [p for p in E.iterdir() if p.is_file() and p.suffix in ('.blend','.json','.png','.html','.txt')]
for folder in (E/'print-parts',E/'slice-review',B/'build/load-frame',B/'build/standalone-test',B/'build/qualification'):
    files += [p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
io=ROOT/'engineering/electronics/base-io-b05';lamp=ROOT/'engineering/electronics/base-light-b06'
for folder in (io/'base-io-b05',io/'manufacturing/b06-io-prototype',lamp/'manufacturing'):
    files += [p for p in folder.rglob('*') if p.is_file() and p.suffix not in ('.bak','.zipbak') and '.history' not in p.parts]
files += [io/'reports/b06-native-bom-final.json',io/'reports/b06-routed-audit.json',lamp/'pin-nets.json',lamp/'README.md']
files=sorted(set(files));assert all(p.is_file() for p in files)
readme='''B06-COMPACT-06-STANDALONE / CURRENT ENGINEERING REVIEW ASSETS
NOT A PRODUCTION OR POWERED-OPERATION RELEASE. Physical tests: 0/20.
No arm model is required. Product print parts: five; test fixture is separate metal hardware.
Start: engineering/base_b06/standalone-validation.md and interface-contract.json.
Models: native Blender, structural STEP, five printable STL, standalone fixture STEP.
Two native JLCEDA PCBs and fabrication candidates included. No current/GMSL rating inferred.
Offline 3D viewers embed meshes. Reference Orca 3MF includes P1S G-code:
select the actual printer and reslice before use; never run reference G-code blindly.
This asset packet is for review/fit preparation; editable generators live in the same repository.
Seven definition gates remain open; all physical measurements are blank.
CC-BY-NC-4.0 / Auromix contributors.
'''
manifest={'revision':'B06-COMPACT-06-STANDALONE','arm_required':False,'production_released':False,
    'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
out=B/'build/B06-standalone-engineering-review.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('READ-ME-FIRST.txt',readme);z.writestr('ASSET-HASHES.json',json.dumps(manifest,indent=2)+'\n')
    for p in files:z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for name,h in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==h
(B/'build/review-package-checks.json').write_text(json.dumps({'pass':True,'archive_sha256':sha(out),'asset_count':len(files),'arm_required':False,'production_released':False},indent=2)+'\n')
print('ENGINEERING_REVIEW_PACKAGE',len(files),out.stat().st_size)
