# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Export original CAD meshes for independent native Blender review scenes."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import cadquery as cq
from build_layout import moved
from build_base_study import LEG_XY

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    source_hashes={};scenes=[]
    def part(path,name,T=None,color='metal',finger=None):
        source_hashes[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
        s=cq.importers.importStep(str(path)).val();assert s.isValid() and len(s.Solids())==1
        if T is not None:s=moved(s,T)
        vv,ff=s.tessellate(.05,.12)
        return {'name':name,'vertices_mm':[v.toTuple() for v in vv],'triangles':ff,'material':color,
                'finger':finger,'source':str(path.relative_to(ROOT)),'solid_volume_mm3':s.Volume()}
    folder=ROOT/'engineering/generated/link56-study';place=json.loads((folder/'part-placements.json').read_text());parts=[]
    offset=np.eye(4);offset[:3,3]=[0,55,-450]
    for name,e in place['instances'].items():parts.append(part(folder/(e['part_id']+'.step'),name,offset@np.array(e['T_world_from_part_mm'])))
    scenes.append({'name':'01_LINK56_connection','parts':parts,'target_mm':[0,10,95],'camera_offset_mm':[450,-600,350],
        'ortho_mm':300,'floor_mm':-2,'note':'Six original parts; OEM joint and screws omitted. Nominal study, not manufacturing release.'})
    folder=ROOT/'engineering/generated/base-study';parts=[]
    for name,file,xyz in [('base_plate','ODR-BASE-PLATE-R4',[0,0,0]),('backing_plate','ODR-BASE-BACK-R4',[0,0,-38]),
        ('rear_ring','ODR-J1-REAR-R4',[0,0,49.5]),('front_ring','ODR-J1-FRONT-R4',[0,0,89.7])]+[(f'leg_{i+1}','ODR-BASE-LEG-R4',[float(x),float(y),16]) for i,(x,y) in enumerate(LEG_XY)]:
        T=np.eye(4);T[:3,3]=xyz;parts.append(part(folder/(file+'.step'),name,T))
    scenes.append({'name':'02_anchored_base','parts':parts,'target_mm':[0,0,20],'camera_offset_mm':[450,-600,400],
        'ortho_mm':380,'floor_mm':-40,'note':'Eight original parts; table, fasteners and OEM joint omitted. Base must be anchored.'})
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text());folder=ROOT/'engineering/generated/contact02-study'
    study=json.loads((folder/'study.json').read_text());face=np.array(p['head']['face_center_mm']);T=np.eye(4);T[:3,3]=-face;parts=[]
    for e in study['parts']:
        kind=e['part'];parts.append(part(folder/e['world_step'],e['finger']+'_'+kind,T,
            'amber' if kind=='light' else 'rubber' if kind.startswith('pad') else 'metal',e['finger']))
    old=ROOT/'engineering/generated/layout';manifest=json.loads((old/'manifest.json').read_text())
    for e in manifest['parts']:
        if e['name'] in ['HEAD_front_core','HEAD_screen'] or e['name'].startswith('CAM_'):
            parts.append(part(old/'parts-step'/(e['name']+'.step'),e['name'],T,'black' if e['name'].endswith(('screen','lens')) else 'metal'))
    obj=cq.Solid.makeCylinder(40,40,cq.Vector(0,0,115),cq.Vector(0,0,1));vv,ff=obj.tessellate(.05,.12)
    parts.append({'name':'STUDY_OBJECT_80x40','vertices_mm':[v.toTuple() for v in vv],'triangles':ff,'material':'object',
        'finger':None,'source':'original mathematical cylinder, not a purchased object','solid_volume_mm3':obj.Volume()})
    grasp=next(c for c in study['contact_cases'] if c['diameter_mm']==80 and c['z_limits_mm']==[115.,155.])
    pivots={}
    for f,d in zip(study['fingers'],grasp['fingers']):
        phi=np.deg2rad(f['phi_deg']);root=np.array([70*np.cos(phi),70*np.sin(phi),f['root_z_mm']])
        pivots[f['id']]={'root_mm':root.tolist(),'axis':[float(np.sin(phi)),float(-np.cos(phi)),0.],
                        'closed_deg':f['closure_study_deg'],'grasp_deg':d['components']['pad_minus']['q_deg']}
    scenes.append({'name':'03_CONTACT02_four_axes','parts':parts,'pivots':pivots,'target_mm':[0,0,55],
        'camera_offset_mm':[350,-450,700],'ortho_mm':470,'floor_mm':-80,
        'note':'Four independent finger pivots. Root drives and real PCB thickness omitted. Geometry-only animation.'})
    payload={'revision':'R4-SUBASSEMBLY-REVIEW-01','units':'mm before Blender conversion to m','scenes':scenes,
        'source_hashes':source_hashes,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'manufacturing_release':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(payload,separators=(',',':')))
    print('Exported',[(s['name'],len(s['parts'])) for s in scenes],'mesh JSON bytes',args.output.stat().st_size)

if __name__=='__main__':main()
