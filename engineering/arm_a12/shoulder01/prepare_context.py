# SPDX-License-Identifier: CC-BY-NC-4.0
"""Freeze a read-only canonical native cache for reproducible A12 module views."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent/'build'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 src=ROOT.parent/'odradek/engineering/base_b06/build/exterior/ODR-BASE-B06-COMPACT.blend'
 digest=sha(src);cache=ROOT/'work/arm-a12/context'/digest/src.name;cache.parent.mkdir(parents=True,exist_ok=True)
 if not cache.exists():shutil.copy2(src,cache)
 assert sha(src)==digest and sha(cache)==digest,'Canonical source changed during snapshot'
 data=dict(base_canonical_relative_path='../odradek/engineering/base_b06/build/exterior/ODR-BASE-B06-COMPACT.blend',base_native_sha256=digest,read_only_cache_relative_path=cache.relative_to(ROOT).as_posix(),scope='One immutable cache of canonical source; never an editable independent base',shoulder_manifest_sha256=sha(OUT/'manifest.json'),baseline_public_native_sha256=sha(ROOT/'engineering/arm_a11/build/odradek-a11-long-validation.blend'),baseline_actual_native_sha256=sha(ROOT/'work/arm-a11/odradek-a11-long-actual-motors.blend'))
 (OUT/'inputs.json').write_text(json.dumps(data,indent=2)+'\n');print('A12_CONTEXT_PINNED',digest,flush=True)
if __name__=='__main__':main()
