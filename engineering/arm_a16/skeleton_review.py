# SPDX-License-Identifier: CC-BY-NC-4.0
"""Report rather than suppress whole-core static collisions."""
import json,itertools
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import common as c

def load(p):
    w=cq.importers.importStep(str(p));return cq.Compound.makeCompound([s for v in w.vals() for s in v.Solids()])
BOUNDS={}
def bounds(s):
    key=s.hashCode()
    if key not in BOUNDS:
        b=Bnd_Box();BRepBndLib.Add_s(s.wrapped,b,False);BOUNDS[key]=b.Get()
    return BOUNDS[key]
def overlap(a,b):
    x=bounds(a);y=bounds(b)
    return not any(x[k+3]<=y[k]+1e-5 or y[k+3]<=x[k]+1e-5 for k in range(3))
def common_volume(a,b):
    # Analytic broad phase per source solid avoids a huge all-compound boolean.
    total=0
    for s in a.Solids():
        for t in b.Solids():
            if overlap(s,t):total+=max(0,s.intersect(t).Volume())
    return total
def main():
    vendor=json.loads((c.OUT/'vendor-audit.json').read_text())
    assert vendor['layout']==c.L,'Vendor cache belongs to another layout; finish source regeneration first.'
    for m in vendor['motors']:
        for suffix,hash in m['cache_step_sha256'].items():assert c.sha(c.CACHE/'vendor'/(m['joint']+'-'+suffix+'.step'))==hash
    items=[];root=c.OUT/'root01';O=c.OUT/'skeleton01';sources={}
    for directory in [root,O]:
        D=json.loads((directory/'manifest.json').read_text())
        sources[str((directory/'manifest.json').relative_to(c.ROOT))]=c.sha(directory/'manifest.json')
        for p in D['parts']:sources[str((directory/'step'/(p['id']+'.step')).relative_to(c.ROOT))]=c.sha(directory/'step'/(p['id']+'.step'))
        items.extend((p,load(directory/'step'/(p['id']+'.step'))) for p in D['parts'])
    for j in c.L['joints']:
        for suffix,fr in [('stator','fixed'),('external-output','rotor')]:
            items.append((dict(id=j['id']+'-supplier-'+suffix,frame=j['id']+'.'+fr),load(c.CACHE/'vendor'/(j['id']+'-'+suffix+'.step'))))
    checks=[];collisions=[]
    for pose,q in c.L['poses'].items():
        F=c.frames(q);world=[(p,c.transform(s,F[p['frame']])) for p,s in items]
        count=0
        for (a,s),(b,t) in itertools.combinations(world,2):
            if a['id'].startswith('J') and b['id'].startswith('J') and 'supplier' in a['id'] and 'supplier' in b['id'] and a['id'][:2]==b['id'][:2]:continue
            if not overlap(s,t):continue
            count+=1;print('PAIR',pose,a['id'],b['id'],flush=True);v=common_volume(s,t)
            if v>.08:collisions.append(dict(pose=pose,a=a['id'],b=b['id'],volume_mm3=v))
        checks.append(dict(pose=pose,positive_bbox_pairs=count,part_count=len(world)))
        print('STATIC_POSE',pose,'tested',count,'collisions',len(collisions),flush=True)
    R=dict(revision='A16-SKELETON01',layout=c.L,source_sha256=sources,vendor_audit_sha256=c.sha(c.OUT/'vendor-audit.json'),checks=checks,collisions=collisions,scoped_clear=not collisions,
      scope='Root, new bracket/tube core, unchanged J7 cartridge,14 exact supplier external partitions;3 named static configurations. No fasteners, covers, wires, base shell or motion interpolation.',
      whole_motion_qualified=False,production_release=False)
    (O/'review.json').write_text(json.dumps(R,indent=2)+'\n');print('COLLISIONS',collisions,flush=True)
if __name__=='__main__':main()
