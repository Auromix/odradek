# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Read vendor STEP interfaces without redistributing vendor CAD.

Example:
 python engineering/extract_vendor_interfaces.py \
   --model 'RH17-B=/path/to/vendor.step' --output /path/to/results.json

This is geometric evidence, not an automatic manufacturing release. A cylindrical
surface may belong to a bore, screw, boss or occupied assembly hole. Thread grade,
usable thread length, tolerances and accessible tool paths require the 2D drawing
and real assembly. Coordinates below are millimetres after OCC STEP import.
"""
import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

# PCD filters are independently read from vendor installation drawings. They do
# not prescribe the actual angular distribution or certify hole accessibility.
PCDS = {14: (44., 64.), 17: (54., 74.), 20: (62., 84.), 25: (77., 102.)}
# Independently cross-checked against 260805 installation drawing front view and
# side elevations. Output surface is the annulus around the central clearance
# boss, not the very front boss face. These surfaces are assembly candidates;
# the manufacturer does not label one unique prescribed mounting datum.
INTERFACES = {
  14: dict(sign=1, central_boss_height=2., central_boss_diameter=37.,
           tip_to_fixed_front=12., tip_to_fixed_rear=32.5,
           output_pilot_diameter=50., output_recess=9., thread='M3', thread_depth=5.,
           output_channel_radius=1.7, output_count=8, fixed_channel_radius=1.75,
           fixed_count=4, evidence_page=3),
  17: dict(sign=1, central_boss_height=2., central_boss_diameter=47.,
           tip_to_fixed_front=12.5, tip_to_fixed_rear=37.7,
           output_pilot_diameter=60., output_recess=9.6, thread='M3', thread_depth=6.,
           output_channel_radius=1.7, output_count=16, fixed_channel_radius=1.7,
           fixed_count=8, evidence_page=6),
  20: dict(sign=-1, central_boss_height=2.5, central_boss_diameter=55.,
           tip_to_fixed_front=14., tip_to_fixed_rear=40.,
           output_pilot_diameter=70., output_recess=10.5, thread='M3', thread_depth=6.,
           output_channel_radius=1.7, output_count=16, fixed_channel_radius=1.7,
           fixed_count=8, evidence_page=8),
  25: dict(sign=1, central_boss_height=2., central_boss_diameter=69.,
           tip_to_fixed_front=17.5, tip_to_fixed_rear=47.7,
           output_pilot_diameter=85., output_recess=13., thread='M4', thread_depth=6.,
           output_channel_radius=2.2, output_count=16, fixed_channel_radius=2.25,
           fixed_count=8, evidence_page=10),
}


def unified_interface(model, size):
    cfg=INTERFACES[size]
    axis=np.asarray(model['frame']['axis_direction_world'])
    origin=np.asarray(model['frame']['axis_origin_world_mm'])
    x=np.asarray(model['frame']['basis_u_world'])
    z=cfg['sign']*axis
    y=np.cross(z,x)
    lo,hi=model['axial_extent_mm']
    tip=hi if cfg['sign']>0 else lo
    surface=tip-cfg['sign']*cfg['central_boss_height']
    O=origin+surface*axis
    fixed_front=tip-cfg['sign']*cfg['tip_to_fixed_front']
    fixed_rear=tip-cfg['sign']*cfg['tip_to_fixed_rear']
    plane_coords=[p['axis_coordinate_mm'] for p in model['perpendicular_planar_face_groups']]
    for value in [surface,fixed_front,fixed_rear]:
        if not any(abs(value-p)<1e-4 for p in plane_coords):
            raise ValueError(f"{model['id']}: expected contact plane absent from STEP: {value}")
    def select_group(pcd,radius,count,contact):
        candidates=[g for g in model['off_axis_cylinder_groups_on_drawing_pcds']
           if abs(g['pcd_mm']-pcd)<1e-4 and abs(g['cylinder_radius_mm']-radius)<1e-4
           and g['count_unique_centres']==count
           and min(abs(s-contact) for s in g['axis_coordinate_range_mm'])<1e-4]
        if len(candidates)!=1:
            raise ValueError(f"{model['id']}: expected one hole group at PCD {pcd}, found {len(candidates)}")
        group=candidates[0]
        points=[]
        for c in group['centres']:
            delta=np.asarray(c['transverse_world_point_mm'])-origin
            xx,yy=np.dot(delta,x),np.dot(delta,y)
            angle=math.degrees(math.atan2(yy,xx))%360.
            if abs(angle-360.)<1e-5:angle=0.
            points.append({'angle_deg':round(angle,5),'xy_mm':rvec([xx,yy])})
        points=sorted(points,key=lambda p:p['angle_deg'])
        return {'pcd_mm':pcd,'count':len(points),'points':points,
           'measured_channel_diameter_mm':2*radius,
           'evidence_axial_world_range_mm':group['axis_coordinate_range_mm'],
           'evidence_axial_joint_z_range_mm':sorted(round(cfg['sign']*(ss-surface),5)
                                  for ss in group['axis_coordinate_range_mm'])}
    out=select_group(PCDS[size][0],cfg['output_channel_radius'],cfg['output_count'],surface)
    fixed=select_group(PCDS[size][1],cfg['fixed_channel_radius'],cfg['fixed_count'],fixed_rear)
    bbox=model['world_bbox_mm']; centre=.5*(np.asarray(bbox['min'])+np.asarray(bbox['max']))
    R=np.column_stack([x,y,z]);T=np.eye(4);T[:3,:3]=R;T[:3,3]=O
    pilot_segments=[]
    for cylinder in model['coaxial_cylindrical_surfaces']:
        if abs(2*cylinder['radius_mm']-cfg['output_pilot_diameter'])>1e-4:
            continue
        zz=sorted(cfg['sign']*(ss-surface) for ss in cylinder['axis_coordinate_range_mm'])
        if zz[0]>-10 and zz[1]<1e-4:
            pilot_segments.append(zz)
    if not pilot_segments:
        raise ValueError(f"{model['id']}: output pilot cylinder absent")
    nearest_pilot=max(pilot_segments,key=lambda zz:zz[1])
    return {'status':'geometrically identified contact candidates; mounting-side choice and tolerances unapproved',
       'T_world_from_joint_mm':[[float(round(a,7)) for a in row] for row in T],
       'definition':'+Z toward output, origin on output annular contact plane; X is projected vendor +X, or +Y when shaft is along X; Y=Z cross X.',
       'output_contact_plane_world_axis_coordinate_mm':round(surface,7),
       'central_clearance_boss':{'diameter_mm':cfg['central_boss_diameter'],
          'height_above_output_contact_mm':cfg['central_boss_height'],
          'function':'clearance boss; no h6 fit specified for this diameter'},
       'outer_output_pilot':{'diameter_mm':cfg['output_pilot_diameter'],'fit_from_drawing':'h6',
          'nearest_straight_cylinder_joint_z_mm':rvec(nearest_pilot),
          'axial_fit_length_mm':None,'note':'Different feature from central clearance boss; straight cylinder intervals are retained in raw extraction; usable fit length requires selected mating lip and drawing review.'},
       'output_holes':out,
       'thread_depth_reference':{'reference':'output annular contact plane at joint z=0',
          'drawing_recess_depth_mm':cfg['output_recess'],'drawing_thread':cfg['thread'],
          'drawing_thread_depth_mm':cfg['thread_depth'],
          'warning':'Clearance-channel and thread-start details differ in STEP; drawing notation and screw engagement must be confirmed before manufacturing. Do not equate total screw insertion with thread engagement.'},
       'fixed_side_contact_candidates_joint_z_mm':{'front':round(cfg['sign']*(fixed_front-surface),5),
          'rear':round(cfg['sign']*(fixed_rear-surface),5)},
       'fixed_side_selected_contact':None,
       'fixed_through_holes':fixed,
       'body_bbox_centre_in_joint_frame_mm':rvec(R.T@(centre-O)),
       'physical_com_in_joint_frame_mm':None,
       'evidence':'RH Series-product manual-260805.pdf page '+str(cfg['evidence_page'])+' and per-model 2D-A/A0 plus STEP',
       'unresolved':['Fixed flange can be approached from front or rear; no unique manufacturer-labelled datum assumed.',
          'Output versus housing clocking is the STEP assembly state, not a verified encoder electrical zero.',
          'Contact-face identification is geometric; flatness, finish, assembly gap and preload remain manufacturing requirements.']}



def xyz(p):
    return np.array([p.X(), p.Y(), p.Z()], dtype=float)


def rvec(v):
    return [float(round(x, 7)) for x in v]


def axial_bounds(face, axis):
    b = face.BoundingBox()
    corners = np.array([[x, y, z] for x in (b.xmin, b.xmax)
                        for y in (b.ymin, b.ymax) for z in (b.zmin, b.zmax)])
    ss = corners @ axis
    return float(ss.min()), float(ss.max())


def extract(name, path):
    imported = cq.importers.importStep(str(path))
    shape = imported.val()
    faces = shape.Faces()
    cylinders = []
    for index, face in enumerate(faces):
        a = BRepAdaptor_Surface(face.wrapped)
        if a.GetType() == GeomAbs_Cylinder:
            cylinder = a.Cylinder()
            cylinders.append((index, face, cylinder))
    if not cylinders:
        raise ValueError(f'{name}: no analytic cylinders found')
    # Largest-radius cylindrical surface identifies these rotary actuator axes.
    # The inference is retained explicitly so it can be checked against drawings.
    main = max(cylinders, key=lambda x: x[2].Radius())[2]
    axis = xyz(main.Axis().Direction())
    if axis[np.argmax(np.abs(axis))] < 0:
        axis = -axis
    loc = xyz(main.Axis().Location())
    origin = loc - np.dot(loc, axis) * axis
    u = np.array([1., 0., 0.])
    if abs(np.dot(u, axis)) > .9:
        u = np.array([0., 1., 0.])
    u -= np.dot(u, axis) * axis
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    m = re.search(r'RH[-_]?(14|17|20|25)', name, re.I)
    pcdfilter = PCDS[int(m.group(1))] if m else ()
    groups = {}
    coaxial = []
    planes = defaultdict(lambda: {'area_mm2': 0., 'face_count': 0})
    for index, face, c in cylinders:
        direction = xyz(c.Axis().Direction())
        if abs(np.dot(direction, axis)) < 1 - 1e-8:
            continue
        p = xyz(c.Axis().Location())
        centre = p - np.dot(p, axis)*axis
        offset = centre-origin
        radial_distance = float(np.linalg.norm(offset))
        smin, smax = axial_bounds(face, axis)
        if radial_distance < 1e-5:
            coaxial.append({'radius_mm': round(c.Radius(), 7),
                            'axis_coordinate_range_mm': rvec([smin, smax]),
                            'area_mm2': round(face.Area(), 7)})
            continue
        if c.Radius() > 5.:
            continue
        pcd = 2*radial_distance
        if pcdfilter and not any(abs(pcd-x) < .01 for x in pcdfilter):
            continue
        angle = math.degrees(math.atan2(np.dot(offset,v), np.dot(offset,u))) % 360.
        if abs(angle-360.) < 1e-6: angle = 0.
        key = (round(pcd, 5), round(c.Radius(), 5), round(smin, 5), round(smax, 5))
        group = groups.setdefault(key, {'pcd_mm': key[0], 'cylinder_radius_mm': key[1],
                        'axis_coordinate_range_mm': [key[2], key[3]],
                        'centres': {}, 'face_count': 0})
        # STEP commonly divides one cylindrical wall into two semicircular faces.
        # Deduplicate centres while retaining face count and the precise interval.
        group['centres'][round(angle, 5)] = {'angle_deg': round(angle, 5),
                    'transverse_world_point_mm': rvec(centre),
                    'coordinates_uv_mm': rvec([np.dot(offset,u),np.dot(offset,v)])}
        group['face_count'] += 1
    for face in faces:
        a = BRepAdaptor_Surface(face.wrapped)
        if a.GetType() != GeomAbs_Plane:
            continue
        plane = a.Plane()
        if abs(np.dot(xyz(plane.Axis().Direction()), axis)) < 1 - 1e-8:
            continue
        if face.Area() < 20.:
            continue
        s = round(float(np.dot(xyz(plane.Location()), axis)), 5)
        planes[s]['area_mm2'] += face.Area()
        planes[s]['face_count'] += 1
    clean_groups=[]
    for key, group in sorted(groups.items()):
        cs = sorted(group.pop('centres').values(),key=lambda x:x['angle_deg'])
        group['count_unique_centres'] = len(cs)
        group['angles_deg'] = [x['angle_deg'] for x in cs]
        group['centres'] = cs
        clean_groups.append(group)
    b=shape.BoundingBox()
    bounds=axial_bounds(shape,axis)
    return {'id':name,'input_filename':path.name,'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'units':'mm (CadQuery/OCC imported STEP coordinates)',
        'solid_count':len(shape.Solids()),'face_count':len(faces),
        'world_bbox_mm':{'min':rvec([b.xmin,b.ymin,b.zmin]),'max':rvec([b.xmax,b.ymax,b.zmax]),
                         'extent':rvec([b.xlen,b.ylen,b.zlen])},
        'frame':{'axis_inference':'axis of maximum-radius analytic cylinder; largest component made positive',
          'axis_origin_world_mm':rvec(origin),'axis_direction_world':rvec(axis),
          'basis_u_world':rvec(u),'basis_v_world':rvec(v),
          'angle_definition':'atan2(offset dot v, offset dot u), degrees in [0,360); u cross v = axis',
          'axial_coordinate_definition':'dot(world point, axis); not offset to mounting face'},
        'axial_extent_mm':rvec(bounds),'axial_span_mm':round(bounds[1]-bounds[0],7),
        'drawing_pcd_filters_mm':list(pcdfilter),
        'coaxial_cylindrical_surfaces':sorted(coaxial,key=lambda x:(x['radius_mm'],x['axis_coordinate_range_mm'])),
        'perpendicular_planar_face_groups':[{'axis_coordinate_mm':s,'total_area_mm2':round(g['area_mm2'],5),
                         'face_count':g['face_count']} for s,g in sorted(planes.items())],
        'off_axis_cylinder_groups_on_drawing_pcds':clean_groups,
        'limitations':['Geometric features only; not all listed cylinders are available mounting holes.',
           'Thread form, fit, preload, tolerances, accessibility and rotating/fixed-side ownership are not inferred.',
           'STEP axes/origins and clocking are vendor-specific; retain the provided basis during CAD transfer.',
           'No material densities or physical COM/inertia have been inferred from STEP volume.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',action='append',required=True,metavar='NAME=STEP_PATH')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    models=[]
    for arg in args.model:
        name,sep,filename=arg.partition('=')
        if not sep or not name:
            parser.error('--model requires NAME=STEP_PATH')
        model=extract(name,Path(filename))
        size_match=re.search(r'RH[-_]?(14|17|20|25)',name,re.I)
        if size_match:
            model['unified_joint_interface']=unified_interface(model,int(size_match.group(1)))
        models.append(model)
    payload={'schema_version':'1.0','method':'Analytic STEP cylinder axes, radii and perpendicular planar faces',
       'software':{'cadquery':cq.__version__},'status':'measured CAD geometry, not released manufacturing interfaces',
       'source_notice':'Vendor CAD is not redistributed. Obtain original inputs from sources/joints.json.',
       'models':models}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'output':str(args.output),'models':[
       {'id':m['id'],'bbox':m['world_bbox_mm'],'axis':m['frame']['axis_direction_world'],
        'pcd_groups':len(m['off_axis_cylinder_groups_on_drawing_pcds'])} for m in models]},indent=2))


if __name__=='__main__':
    main()
