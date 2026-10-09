# SPDX-License-Identifier: CC-BY-NC-4.0
"""Scope-limited root BREP review. Touching intended mounting faces is allowed."""
import json
import cadquery as cq
import common as c

def shape(p):
    w=cq.importers.importStep(str(p));return cq.Compound.makeCompound([s for v in w.vals() for s in v.Solids()])

def main():
    O=c.OUT/'root01';D=json.loads((O/'manifest.json').read_text());F=c.frames([0]*7)
    parts={p['id']:c.transform(shape(O/'step'/(p['id']+'.step')),F[p['frame']]) for p in D['parts']}
    parts['RS03-full']=c.transform(shape(c.CACHE/'vendor/J1-full.step'),F['J1.fixed'])
    h=c.base_context();parts['B06-load-flange']=shape(c.BASE/h['base_sources']['flange_step']['path'])
    tests=[]
    keys=list(parts)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            s=parts[a].intersect(parts[b]);vol=max(0,s.Volume());dist=parts[a].distance(parts[b])
            tests.append(dict(a=a,b=b,intersection_mm3=vol,distance_mm=dist,pass_no_positive_intersection=vol<.05))
    for x in tests:assert x['pass_no_positive_intersection'],x
    # Radius/tip statements are explicit mathematical checks, not a harness
    # insertion proof or the assembled base cover's tolerance qualification.
    checks=D['theoretical_mating_checks']
    assert checks['adapter_neck_radial_gap_mm']>0 and checks['column_screw_tip_above_base_mm']>0
    result=dict(revision='A16-ROOT01',all_scoped_BREP_pairs_clear=True,pairs=tests,
      verified_sources=c.base_context(),print_meshes_closed=all(p['watertight'] for p in D['parts']),
      scope='Seven root structural parts, exact unscaled RS03, canonical B06 load flange, q1=0 reference. Fastener thread envelopes and moving shoulder are outside this test.',
      minimum_noncontact_gap_mm=min(x['distance_mm'] for x in tests if x['distance_mm']>.01),
      assembly_qualified=False,harness_qualified=False,load_qualified=False,production_release=False)
    (O/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    print('ROOT_BREP_PASS',len(tests),'pairs; min noncontact',result['minimum_noncontact_gap_mm'],flush=True)

if __name__=='__main__':main()
