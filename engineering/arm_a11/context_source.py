# SPDX-License-Identifier: CC-BY-NC-4.0
"""Read the single canonical base/head source or an immutable Git export cache."""
from pathlib import Path
import json,hashlib,os
ROOT=Path(__file__).resolve().parents[2]
CONFIG=json.loads((Path(__file__).parent/'context-source.json').read_text())
def canonical_repo():
 candidates=[]
 if os.environ.get('ODRADEK_CANONICAL_REPO'):candidates.append(Path(os.environ['ODRADEK_CANONICAL_REPO']))
 candidates.extend([ROOT.parent/'odradek',ROOT/'work/arm-a11/shared-canonical'/CONFIG['pinned_commit']])
 for path in candidates:
  manifest=path/'engineering/base_b05/build/exterior/exterior-manifest.json'
  params=path/'engineering/generated/r5-petal-form02/parameters.json'
  if not manifest.exists() or not params.exists():continue
  if hashlib.sha256(manifest.read_bytes()).hexdigest()!=CONFIG['base_manifest_sha256']:
   raise RuntimeError('Canonical base changed. Update the shared interface and repeat A11 audits before claiming fit.')
  assert hashlib.sha256(params.read_bytes()).hexdigest()==CONFIG['head_parameters_sha256']
  return path
 raise RuntimeError('Canonical sources missing. Run prepare_context.py after fetching the pinned main commit, or set ODRADEK_CANONICAL_REPO.')
