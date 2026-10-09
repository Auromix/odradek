# SPDX-License-Identifier: CC-BY-NC-4.0
"""Exact CAD for a removable base-only test fixture, NOT product parts.

No arm asset is read. Bolt envelopes follow the project CAD convention;
threads are pilot bores with explicit machining callouts, not helices.
This is a manufacturing-review candidate, not a qualified loading apparatus.
"""
from pathlib import Path
import hashlib,json,math
import cadquery as cq
import load_frame as cad

HERE=Path(__file__).resolve().parent
OUT=HERE/'build/standalone-test'
contract=json.loads((HERE/'interface-contract.json').read_text())
IF=contract['mechanical']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    for n in ('step','stl','drawings'):(OUT/n).mkdir(exist_ok=True)
    cad.PARTS.clear()
    z=IF['base_mating_plane_z'];cx,cy=contract['datum']['axis_xy']
    # One machined blank: 8mm adapter disk + integral D84 boss to Z100.
    s=cad.cyl(cx,cy,z,67,8).fuse(cad.cyl(cx,cy,z+8,42,34)).clean()
    p=cad.add('B06-T01-TEST-ADAPTER',s,'S355','Turn/mill from solid blank; no weld',
        ['OD134, lower datum A Z58, disk8; boss OD84 to Z100',
         'Datum A and top boss seat flatness0.10; parallelism0.10; deburr0.5',
         'Review tolerances: OD134 +/-0.10; disk/boss heights +/-0.10; XY hole centres +/-0.10',
         'Do not print or substitute polymer; test apparatus requires its own inspection'])
    for i in range(IF['hole_count']):
        a=math.radians(IF['first_hole_deg']+IF['hole_step_deg']*i)
        cad.hole(p,cx+60*math.cos(a),cy+60*math.sin(a),z,6.6,8,'D6.6 THRU; PCD120, phase22.5deg; ISO4762 M6x20 + ISO7089 washer')
    positions=[]
    for i in range(4):
        a=math.radians(45+90*i);x=cx+30*math.cos(a);y=cy+30*math.sin(a);positions.append((x,y))
        cad.hole(p,x,y,100,6.8,20,'M8x1.25-6H blind, full thread16, drill20; PCD60 phase45deg',axis=(0,0,-1))
    # Positive four-bolt attachment avoids a screw-in post unwinding in yaw.
    post=cad.cyl(cx,cy,100,42,8).fuse(cad.cyl(cx,cy,108,15,480))
    hexpart=cq.Workplane('XY').polygon(6,24/math.cos(math.pi/6)).extrude(20).translate((cx,cy,588)).val()
    post=post.fuse(hexpart).clean()
    p=cad.add('B06-T02-TEST-POST',post,'S355','Turn/mill from solid blank; no weld',
        ['Flange OD84 x8, shaft OD30 from Z108 to588, top AF24 x20; top Z608',
         'Datum A flange underside Z100; flatness0.10; shaft perpendicularity0.15 over500',
         'Review tolerances: OD30 +/-0.10; flange thickness +/-0.10; hole centres +/-0.10',
         'Lateral force applied at Z558, 500mm above base datum; 300N gives150Nm at base',
         'Top AF24 is torque-test drive; axial load through inspected rated M10 lifting accessory, not printed hardware'])
    for x,y in positions:cad.hole(p,x,y,100,8.5,8,'D8.5 THRU; ISO4762 M8x25 + ISO7089 washer')
    cad.hole(p,cx-16,cy,558,8.5,32,'D8.5 THRU, load-pin centre Z558; rated pin/clevis selection pending',axis=(1,0,0))
    cad.hole(p,cx,cy,608,8.5,20,'M10x1.5-6H blind; full thread15, drill20; rated axial lifting accessory',axis=(0,0,-1))
    for i in range(8):
        a=math.radians(22.5+45*i);x=cx+60*math.cos(a);y=cy+60*math.sin(a)
        cad.washer(f'T-HW-M6-W-{i+1}',x,y,66,12,6.4,1.6)
        cad.bolt(f'T-HW-M6-{i+1}',x,y,67.6,6,20,10,6,af=5)
    for i,(x,y) in enumerate(positions,1):
        cad.washer(f'T-HW-M8-W-{i}',x,y,108,16,8.4,1.6)
        cad.bolt(f'T-HW-M8-{i}',x,y,109.6,8,25,13,8,af=6)
    parts=list(cad.PARTS);assembly=cq.Assembly();items=[]
    for p in parts:
        s=p['shape'];assert s.isValid() and len(s.Solids())==1,p['id']
        step=OUT/'step'/(p['id']+'.step');stl=OUT/'stl'/(p['id']+'.stl')
        cq.exporters.export(s,str(step));cq.exporters.export(s,str(stl),tolerance=.03,angularTolerance=.08)
        r=cq.importers.importStep(str(step)).val()
        assert r.isValid() and abs(r.Volume()-s.Volume())<max(.01,s.Volume()*1e-7)
        b=s.BoundingBox()
        item={k:v for k,v in p.items() if k!='shape'}
        item.update(name=p['id'],category='fixture',assembly_role='fixture',viewer_group='fixture',quantity=1,
            stl='stl/'+stl.name,step='step/'+step.name,print_stl=None,
            color=[.72,.46,.15],bbox={'min':[b.xmin,b.ymin,b.zmin],'max':[b.xmax,b.ymax,b.zmax]},
            prototype_status='独立试验工装候选；装置自身须先校验',step_sha256=sha(step),stl_sha256=sha(stl))
        items.append(item);assembly.add(s,name=p['id'])
    # Exact nominal intersections vs base structural BREP. Only specifically
    # matched threaded pairs are classified; all other positive overlaps fail.
    base=list(cad.make(30));pairs=[];threadpairs=[]
    import itertools
    combinations=list(itertools.combinations(parts,2))+[(a,b) for a in parts for b in base if not b['id'].startswith('HW-ROOT-')]
    for a,b in combinations:
        aa,bb=a['shape'].BoundingBox(),b['shape'].BoundingBox()
        if any(getattr(aa,k+'max')<=getattr(bb,k+'min')+1e-6 or getattr(bb,k+'max')<=getattr(aa,k+'min')+1e-6 for k in 'xyz'):continue
        v=a['shape'].intersect(b['shape']).Volume()
        if v<=.001:continue
        ids={a['id'],b['id']}
        thread=('B06-104-LOAD-FLANGE' in ids and any(k.startswith('T-HW-M6-') and '-W-' not in k for k in ids)) or ('B06-T01-TEST-ADAPTER' in ids and any(k.startswith('T-HW-M8-') and '-W-' not in k for k in ids))
        (threadpairs if thread else pairs).append({'a':a['id'],'b':b['id'],'volume_mm3':v})
    assert not pairs,pairs
    assembly.export(str(OUT/'B06-standalone-fixture.step'))
    report={'revision':'B06-TEST-01','length_unit':'mm','parts':items,'source_sha256':sha(Path(__file__)),
        'interface_contract_sha256':sha(HERE/'interface-contract.json'),
        'release':'Test fixture manufacturing REVIEW; not qualified or approved for applied loads',
        'not_included':['rated pin/clevis and lifting eye','force sensor, calibrated load source, restraint and rigid test table'],
        'thread_engagement_mm':{'M6_base':10.4,'M8_post':15.4},
        'exact_brep_interferences':pairs,'classified_thread_overlaps':threadpairs,
        'screening':{'shaft_max_nominal_bending_MPa':32*150000/(math.pi*30**3),
                     'shaft_nominal_torsion_MPa':16*40000/(math.pi*30**3),
                     'limits':'Nominal unnotched shaft only; no hole stress concentration, plate bending, bolts/preload, fatigue or apparatus qualification'},
        'arm_assets_read':[]}
    (OUT/'fixture-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    # Native CAD projections, not an illustrative mesh. Use mm coordinates.
    for p in parts[:2]:
        cq.exporters.export(p['shape'],str(OUT/'drawings'/(p['id']+'-front.svg')),opt={'projectionDir':(0,1,0),'showHidden':True,'width':650,'height':800})
        cq.exporters.export(p['shape'],str(OUT/'drawings'/(p['id']+'-top.svg')),opt={'projectionDir':(0,0,1),'showHidden':True,'width':650,'height':650})
    print('STANDALONE_FIXTURE',len(items),'valid exported BREP solids; no arm assets')
if __name__=='__main__':build()
