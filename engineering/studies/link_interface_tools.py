# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Reproducible local vendor-interface probes; never export third-party BREP.

Adapted from the original work-only r4-link-interface-study.py and
r4-link-extra-probes.py. Supply --model ID=/absolute/vendor.step repeatedly.
The default report goes to stdout; --output writes a new raw measurement report,
not the curated link-interface-plan.json. CAD ownership stays with the vendor.
"""
import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path
import numpy as np
import cadquery as cq

ENGINEERING = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINEERING))
from build_layout import frame, moved
from mount_interface_study import load_vendor, circular_features, ring, bores
ROOT = ENGINEERING.parent


def cache(shape):
    return [(s, s.BoundingBox()) for s in shape.Solids()]


def aabb_gap(a, b):
    return float(np.linalg.norm([max(getattr(a,k+'min')-getattr(b,k+'max'),
                                    getattr(b,k+'min')-getattr(a,k+'max'),0.) for k in 'xyz']))


def check(a, b, minimum=False):
    """Solid-pair common, with cached boxes. Overlap sums are not union volumes."""
    aa = cache(a) if not isinstance(a,list) else a
    bb = cache(b) if not isinstance(b,list) else b
    pairs=sorted((aabb_gap(xb,yb),i,j,x,y) for i,(x,xb) in enumerate(aa) for j,(y,yb) in enumerate(bb))
    events=[]; closest=None; distance=float('inf'); booleans=0
    for lower,i,j,x,y in pairs:
        xb,yb=aa[i][1],bb[j][1]
        # Intersection volume cannot exceed the product of AABB overlaps.
        # This exact upper bound safely rejects tiny tangent-box intersections
        # below the same1e-4mm3 reporting threshold, avoiding slow OCCT tangency.
        overlap=np.prod([max(0.,min(getattr(xb,k+'max'),getattr(yb,k+'max'))-max(getattr(xb,k+'min'),getattr(yb,k+'min'))) for k in 'xyz'])
        if lower<1e-6 and overlap>1e-4:
            vol=x.intersect(y).Volume();booleans+=1
            if vol>1e-4:events.append({'a_solid':i,'b_solid':j,'intersection_mm3':vol})
        if minimum and lower<distance:
            d=x.distance(y)
            if d<distance:distance=float(d);closest=[i,j]
    result={'solid_pair_intersection_sum_mm3':sum(e['intersection_mm3'] for e in events),
            'events':events,'pair_count':len(pairs),'boolean_count':booleans,
            'method':'per-solid Boolean common; cached AABB and intersection-volume-upper-bound pruning; threshold1e-4mm3'}
    if minimum:result.update(minimum_BREP_surface_distance_mm=distance,nearest_pair=closest)
    return result


def contact(planes,z):
    selected=[dict(f) for f in planes if abs(f['z_mm']-z)<1e-5]
    for f in selected:
        f['coaxial_boundary_radii_mm']=sorted(set(round(c['radius_mm'],5) for c in f['boundary_circle_features'] if np.linalg.norm(c['xy_mm'])<1e-5))
    outer=max(max(f['coaxial_boundary_radii_mm'],default=0) for f in selected)
    chosen=[f for f in selected if abs(max(f['coaxial_boundary_radii_mm'],default=0)-outer)<1e-5]
    return {'z_mm':z,'face_indices':[f['face_index'] for f in chosen], 'area_mm2':sum(f['area_mm2'] for f in chosen),
            'coaxial_boundary_radii_mm':sorted(set(r for f in chosen for r in f['coaxial_boundary_radii_mm'])),
            'selected_faces':chosen,'other_coplanar_face_indices':[f['face_index'] for f in selected if f not in chosen],
            'selection':'outermost coaxial annular contact; split faces retained; inner coplanar faces excluded'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model',action='append',required=True,metavar='ID=STEP')
    ap.add_argument('--parameters',type=Path,default=ROOT/'engineering/parameters/r4-layout.json')
    ap.add_argument('--interfaces',type=Path,default=ROOT/'docs/engineering/sources/rh-interface-extraction.json')
    ap.add_argument('--output',type=Path)
    ap.add_argument('--layout-dir',type=Path,default=ROOT/'engineering/generated/layout')
    args=ap.parse_args();p=json.loads(args.parameters.read_text())
    models={m['id']:m for m in json.loads(args.interfaces.read_text())['models']}
    paths=dict(x.split('=',1) for x in args.model)
    shapes={key:load_vendor(Path(path),models[key]) for key,path in paths.items()}
    result={'parameters_sha256':hashlib.sha256(args.parameters.read_bytes()).hexdigest(),
            'interfaces_sha256':hashlib.sha256(args.interfaces.read_bytes()).hexdigest(),
            'vendor_CAD_published':False,'contacts':{},'joint_interfaces':[],'connections':[],
            'vendor_sources':{key:{'filename':Path(path).name,'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()} for key,path in paths.items()}}
    for key,shape in shapes.items():
        _,planes=circular_features(shape);it=models[key]['unified_joint_interface']
        result['contacts'][key]={name:contact(planes,z) for name,z in [('output',0),*it['fixed_side_contact_candidates_joint_z_mm'].items()]}
    for joint in p['joints']:
        key=joint['model']
        if key not in shapes:continue
        T=frame(joint['origin_mm'],joint['axis']);it=models[key]['unified_joint_interface']
        entry={'joint':joint['id'],'model':key,'T_world_from_joint':T.tolist(),'contacts':{}}
        for label,z in [('output',0),*it['fixed_side_contact_candidates_joint_z_mm'].items()]:
            group=it['output_holes' if label=='output' else 'fixed_through_holes']
            entry['contacts'][label]={'centre_world_mm':(T@np.array([0,0,z,1]))[:3].tolist(),
                'plane_axis_world':joint['axis'],'approach_side_world':(np.array(joint['axis'])*(-1 if label=='rear' else 1)).tolist(),
                'holes_world_mm':[(T@np.array([*point['xy_mm'],z,1]))[:3].tolist() for point in group['points']],
                'radial_boundaries_mm':result['contacts'][key][label]['coaxial_boundary_radii_mm']}
        entry['rear_axis_endpoint_world_mm']=(T@np.array([0,0,shapes[key].BoundingBox().zmin,1]))[:3].tolist()
        result['joint_interfaces'].append(entry)
    for i in range(6):
        u,d=p['joints'][i:i+2]
        if u['model'] not in shapes or d['model'] not in shapes:continue
        Tu,Td=[frame(j['origin_mm'],j['axis']) for j in [u,d]]
        v1,v2=moved(shapes[u['model']],Tu),moved(shapes[d['model']],Td)
        it=models[u['model']]['unified_joint_interface']
        row={'id':f'J{i+1}_to_J{i+2}','housing_collision':check(v1,v2),
             'axial_slab_gap_mm':moved(v2,np.linalg.inv(Tu)).BoundingBox().zmin-shapes[u['model']].BoundingBox().zmax,
             'output_head_thickness_sensitivity':{}}
        points=[q['xy_mm'] for q in it['output_holes']['points']]
        D,H=(7.22,4) if u['model']=='RH25-B' else (6,3.2)
        for t in ([5,5.5,6] if i==0 else [6]):
            heads=moved(bores(points,D/2,t,H).val(),Tu)
            row['output_head_thickness_sensitivity'][str(t)]=check(heads,v2,minimum=True)
        annulus=moved(ring(it['outer_output_pilot']['diameter_mm']/2+4,it['central_clearance_boss']['diameter_mm']/2+.3,0,6).val(),Tu)
        row['annulus6_to_downstream']=check(annulus,v2)
        dt=models[d['model']]['unified_joint_interface'];radii=result['contacts'][d['model']]['rear']['coaxial_boundary_radii_mm']
        collar=moved(ring(max(radii)+4,min(radii)+.3,dt['fixed_side_contact_candidates_joint_z_mm']['rear']-8,8).val(),Td)
        row['compact8mm_collar']={'OD_mm':2*(max(radii)+4),'ID_mm':2*(min(radii)+.3),
                  'to_upstream':check(collar,v1),'to_downstream':check(collar,v2),'to_output_annulus':check(collar,annulus)}
        if i in [2,4]:
            path=args.layout_dir/'parts-step'/f'L{i+1}_closed_beam_study.step'
            if path.exists():
                beam=cq.importers.importStep(str(path)).val()
                row['existing_beam']={'filename':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                  'to_upstream':check(beam,v1),'to_downstream':check(beam,v2),
                  'bbox_mm':[getattr(beam.BoundingBox(),a) for a in ['xmin','ymin','zmin','xmax','ymax','zmax']]}
        if d['model']=='RH25-B':
            path=ROOT/'engineering/generated/mount-study/ODR-J1-REAR-R4.step'
            if path.exists():row['D150_rear_ring_reuse_to_upstream']=check(moved(cq.importers.importStep(str(path)).val(),Td),v1)
        result['connections'].append(row)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    else:print(text)


if __name__=='__main__':main()
