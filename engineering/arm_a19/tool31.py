# SPDX-License-Identifier: CC-BY-NC-4.0
"""Actual nominal socket engagement and straight driver insertion by stage."""
from pathlib import Path
import json,sys,math
import numpy as np
import cadquery as cq
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'build/assembly25'
sys.path.insert(0,str(HERE));import wrist16 as w
c=w.c;g=c.cad;r=w.r
def main():
    path=OUT/'manifest.json';d=json.loads(path.read_text());core=json.loads((HERE/'build/wrist-core19/manifest.json').read_text());shell=json.loads((HERE/'build/wrist-shell21/manifest.json').read_text());F=w.f.frames(d['layout'],d['layout']['poses']['reference']);rows=d['parts'];tools=[]
    for p in core['screw_stacks']:
        n=np.array(p['normal']);q=np.array(p['mount_origin_mm']);bearing=q+n*(p['grip_mm']+p['washer_mm']);isfixed='fixed' in p['id']
        tools.append(dict(id=p['id'],frame='J5.fixed' if isfixed else 'J5.rotor',origin=(bearing+n*2.7).tolist(),n=n.tolist(),AF_mm=2.95,socket_nominal_AF_mm=3,engagement_mm=1.3,stage='fixed mount before output L' if isfixed else 'output L before J6 module',remove_owners_at_or_above=5 if isfixed else 6))
    n=np.array(core['motor_interface']['n'])
    for i,mount in enumerate(core['cover_mounts'],1):
        q=np.array(mount['p_mm'])-[185,62,0];bearing=q+n*11
        tools.append(dict(id=f'A19-H21-J5-cover-{i}',frame='J5.fixed',origin=(bearing+n*.7).tolist(),n=n.tolist(),AF_mm=1.95,socket_nominal_AF_mm=2,engagement_mm=1.3,stage='assembled wrist reference pose',remove_owners_at_or_above=None))
    items=[(p,r.load(ROOT/p['step_path'])) for p in rows];motor=json.loads((c.OUT/'vendor-audit.json').read_text())
    for m in motor['motors']:
        if m['joint']=='J5':
            native,_=w.motor();items.extend([(dict(p,role='supplier_reference'),s) for p,s in native]);continue
        for tag,fr in [('stator','fixed'),('external-output','rotor')]:
            file=c.CACHE/'vendor'/(m['joint']+'-'+tag+'.step');assert c.sha(file)==m['cache_step_sha256'][tag]
            items.append((dict(id=m['joint']+'-supplier-'+tag,role='supplier_reference',frame=m['joint']+'.'+fr,owner=int(m['joint'][1])-(fr=='fixed')),r.load(file)))
    results=[]
    for tool in tools:
        exclusions=[];targets=[]
        for p,s in items:
            owner=p.get('owner',int(p['frame'][1]) if p['frame'].startswith('J') else 0)
            if tool['remove_owners_at_or_above'] is not None and ((owner>=tool['remove_owners_at_or_above'] and p.get('role')!='supplier_reference') or p['frame'].startswith(('J6.','J7.')) or (p.get('role')=='printed_cover' and p['frame'] in ['J4.rotor','J5.fixed'])):
                exclusions.append(p['id']);continue
            targets.append((p,c.transform(s,F[p['frame']])))
        shape=cq.Workplane(g.plane(tool['origin'],tool['n'])).polygon(6,tool['AF_mm']/math.cos(math.pi/6)).extrude(80).val();solid=c.transform(shape,F[tool['frame']]);hits=[]
        for p,s in targets:
            if not r.overlap(solid,s):continue
            volume=r.common_volume(solid,s)
            if volume>.08:hits.append(dict(target=p['id'],volume_mm3=volume))
        results.append(dict(tool,straight_hex_length_mm=80,excluded_at_this_stage=exclusions,hits=hits));print('TOOL31',tool['id'],hits,flush=True)
    report=dict(source_assembly_sha256=c.sha(path),source_core_sha256=c.sha(HERE/'build/wrist-core19/manifest.json'),source_shell_sha256=c.sha(HERE/'build/wrist-shell21/manifest.json'),pose=d['layout']['poses']['reference'],tools=results,all_staged_nominal_drivers_clear=not any(t['hits'] for t in results),production_release=False,scope='Nominal slightly undersize straight hex shaft from1.3mm socket engagement through80mm driver length. Explicit staged removed components, no hand/handle, torque, nut restraint, tolerances, real wrench or physical assembly proof.')
    (OUT/'tool31.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
