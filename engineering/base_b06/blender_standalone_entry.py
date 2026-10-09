# SPDX-License-Identifier: CC-BY-NC-4.0
"""Run the base generator with a fail-closed Python file-access audit."""
import sys,runpy,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
reads=set()
def audit(event,args):
    if event!='open' or not args or not isinstance(args[0],(str,bytes)):return
    p=Path(args[0]).resolve()
    if p.name=='root-snapshot.json' or any(n.startswith(('arm_a','arm_body')) for n in p.parts):
        raise RuntimeError('Base-only build attempted an arm asset read: '+str(p))
    if HERE in p.parents and isinstance(args[1],str) and 'r' in args[1]:reads.add(p)
sys.addaudithook(audit)
if '--with-arm-root' in sys.argv:raise RuntimeError('This entry point is strictly base-only')
runpy.run_path(str(HERE/'blender_compact.py'),run_name='__main__')
report={'pass':True,'arm_assets_read':[],
 'scope':'Python file-open audit rejects root snapshot and arm_a*/arm_body* paths; native Blender external-library dependencies separately checked',
 'input_sha256':{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(reads) if p.is_file()},
 'manifest_sha256':hashlib.sha256((HERE/'build/exterior/manifest.json').read_bytes()).hexdigest()}
(HERE/'build/exterior/standalone-build-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('BASE_ONLY_READ_AUDIT_PASS')
