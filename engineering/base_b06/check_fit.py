# SPDX-License-Identifier: CC-BY-NC-4.0
"""Reopen native B06; check static surfaces and selected tool rays.

Blender BVH detects triangle intersections. The independent manifold3d volume check distinguishes contacts from penetrations.
"""
import bpy,json,hashlib,itertools,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
OUT=Path(bpy.data.filepath).parent
D=json.loads((OUT/'manifest.json').read_text())
DG=bpy.context.evaluated_depsgraph_get()
objects={p['id']:bpy.data.objects[p['id']] for p in D['parts']}
def tree(o):
    return BVHTree.FromObject(o,DG,epsilon=0)
trees={k:tree(o) for k,o in objects.items()}
pairs=[]
printids=[p['id'] for p in D['parts'] if p.get('print_stl')]
refids=[p['id'] for p in D['parts'] if p['assembly_role'] in ('structure','electronics')]
checks=list(itertools.combinations(printids,2))+list(itertools.product(printids,refids))
for a,b in checks:
    aa=next(p['bbox'] for p in D['parts'] if p['id']==a);bb=next(p['bbox'] for p in D['parts'] if p['id']==b)
    if any(aa['max'][i]<bb['min'][i]-.02 or bb['max'][i]<aa['min'][i]-.02 for i in range(3)):continue
    overlaps=trees[a].overlap(trees[b])
    pairs.append(dict(a=a,b=b,triangle_pairs=len(overlaps),
                      interpretation='Surface contact only; use independent closed-solid volume check to distinguish contact from penetration'))

tools=[]
for k in range(8):
    a=math.radians(22.5+45*k);x=60*math.cos(a);y=75+60*math.sin(a)
    blocked=0
    for j in range(16):
        t=j*math.tau/16
        origin=Vector(((x+6.5*math.cos(t))*.001,(y+6.5*math.sin(t))*.001,.070))
        h,_,_,_=trees['B06-301-MAIN-SHIELD'].ray_cast(origin,Vector((0,0,1)),.12)
        blocked+=h is not None
    tools.append(dict(hole=k+1,sample_rays=16,blocked=blocked,tool_diameter_mm=13,
                      scope='Vertical envelope rays Z70..190; original root geometry itself not checked'))
report=dict(revision=D['revision'],manifest_sha256=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest(),
            scope='Reference pose surface contacts and sampled tool rays; solid-fit-checks.json governs penetration',
            pairs=pairs,root_tool_rays=tools,
            surface_pairs_present=[p for p in pairs if p['triangle_pairs']],
            limits=['BVH contacts alone cannot distinguish touching from volume interference.',
                    'Expected PCB/post face contact can yield triangle pairs; read each pair.',
                    'No flange support, clamp load, motion clearance, plug latch or physical printing verification.'])
(OUT/'fit-checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SURFACE_PAIRS',len(report['surface_pairs_present']),flush=True)
for p in report['surface_pairs_present']:print(p['a'],p['b'],p['triangle_pairs'],flush=True)
print('TOOL_RAYS',sum(p['blocked'] for p in tools),flush=True)
