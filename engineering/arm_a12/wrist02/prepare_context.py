# SPDX-License-Identifier: CC-BY-NC-4.0
"""Pin a read-only snapshot of the single canonical base; do not fork its design."""
from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=ROOT.parent/'odradek/engineering/base_b06/build/exterior/ODR-BASE-B06-COMPACT.blend'
manifest=src.parent/'manifest.json';provenance=json.loads((src.parent/'provenance.json').read_text())
digest=sha(src);assert digest==provenance['native_blend_sha256'];assert sha(manifest)==provenance['manifest_sha256']
cache=ROOT/'work/arm-a12/context'/digest/src.name;cache.parent.mkdir(parents=True,exist_ok=True)
if not cache.exists():shutil.copyfile(src,cache)
assert sha(cache)==digest
data=dict(base_canonical_relative_path='../odradek/engineering/base_b06/build/exterior/ODR-BASE-B06-COMPACT.blend',base_native_sha256=digest,base_manifest_sha256=sha(manifest),base_revision=provenance['revision'],read_only_cache_relative_path=cache.relative_to(ROOT).as_posix(),scope='Read-only authoritative base context; no root/base assembly qualification is inherited')
(OUT/'base-context.json').write_text(json.dumps(data,indent=2)+'\n');print('BASE_CONTEXT',data['base_revision'],digest)
