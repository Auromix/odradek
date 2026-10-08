# SPDX-License-Identifier: CC-BY-NC-4.0
"""Export pinned canonical Git sources to an immutable ignored reference cache.
No network side effect. Fetch origin main separately when commit is unavailable.
"""
import json,subprocess,tarfile,io
from pathlib import Path
from context_source import ROOT,CONFIG,canonical_repo
out=ROOT/'work/arm-a11/shared-canonical'/CONFIG['pinned_commit'];out.mkdir(parents=True,exist_ok=True)
raw=subprocess.check_output(['git','-C',str(ROOT),'archive',CONFIG['pinned_commit'],'engineering/base_b05','engineering/generated/r5-petal-form02'])
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
 for member in archive.getmembers():
  p=Path(member.name)
  assert not p.is_absolute() and '..' not in p.parts and not member.issym() and not member.islnk()
 archive.extractall(out,filter='data')
print('Pinned canonical source cache:',out)
