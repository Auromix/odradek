# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact changed STEP tessellations; supplier derivatives stay local-only."""
from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c
def main():
    path=HERE/'build/assembly25/manifest.json';d=json.loads(path.read_text());own=[]
    for p in d['parts']:
        if p['id'] not in d['added_part_ids']:continue
        assert c.sha(ROOT/p['step_path'])==p['step_sha256']
        s=w.r.load(ROOT/p['step_path']);v,t=s.tessellate(.04,.1)
        own.append(dict(p,vertices_mm=[a.toTuple() for a in v],triangles=t))
    motor,audit=w.motor();vendor=[]
    for p,s in motor:
        v,t=s.tessellate(.04,.1);vendor.append(dict(p,role='supplier_reference',vertices_mm=[a.toTuple() for a in v],triangles=t))
    output=ROOT/'work/arm-a19';output.mkdir(parents=True,exist_ok=True)
    (output/'changed-native26.json').write_text(json.dumps(dict(assembly_sha256=c.sha(path),own=own,supplier=vendor,supplier_source=audit),separators=(',',':'))+'\n')
    print('MESH26',len(own),len(vendor),flush=True)
if __name__=='__main__':main()
