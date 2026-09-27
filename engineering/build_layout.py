# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Create dimensioned layout envelopes, never labelled production parts.

Output STEP/STL geometry is original analytic geometry, not vendor CAD. Link
rails are route studies without fasteners; the head reserves drive volume.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import cadquery as cq
from scipy.spatial.transform import Rotation
from OCP.gp import gp_Trsf

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/layout'


def frame(origin, zaxis, xaxis=None):
    z=np.asarray(zaxis,dtype=float);z/=np.linalg.norm(z)
    x=np.array([1.,0,0]) if xaxis is None else np.asarray(xaxis,dtype=float)
    if abs(x@z)>.99:x=np.array([0.,1,0])
    x=x-(x@z)*z;x/=np.linalg.norm(x);y=np.cross(z,x)
    T=np.eye(4);T[:3,:3]=np.column_stack([x,y,z]);T[:3,3]=origin
    return T


def moved(shape,T):
    # Use an explicit rigid transform: constructing gp_GTrsf from a generic
    # matrix does not set its transform form in every OCCT binding version.
    trsf=gp_Trsf();trsf.SetValues(*np.asarray(T)[:3,:].reshape(-1).tolist())
    return shape.moved(cq.Location(trsf))


def tube_between(a,b,outer=18,wall=3):
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    length=np.linalg.norm(b-a)
    shape=cq.Workplane('XY').circle(outer/2).circle((outer-2*wall)/2).extrude(length).val()
    return moved(shape,frame(a,b-a))


def main():
    p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text())
    interfaces=json.loads((ROOT/'docs/engineering/sources/rh-interface-extraction.json').read_text())
    interfaces={m['id']:m['unified_joint_interface'] for m in interfaces['models']}
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'meshes').mkdir(exist_ok=True);(OUT/'parts-step').mkdir(exist_ok=True)
    assembly=cq.Assembly(name='Odradek_R4_layout_NOT_FOR_MANUFACTURE');parts=[]
    def add(name,shape,attachment,color,category='envelope',finger=None):
        if not shape.isValid() or len(shape.Solids())<1:
            raise ValueError(f'Invalid geometry: {name}')
        cq.exporters.export(shape,str(OUT/'meshes'/f'{name}.stl'),tolerance=.12,angularTolerance=.15)
        cq.exporters.export(shape,str(OUT/'parts-step'/f'{name}.step'))
        assembly.add(shape,name=name,color=cq.Color(*color))
        bb=shape.BoundingBox()
        parts.append({'name':name,'attachment':attachment,'finger':finger,'category':category,
                      'material_color':color,'mesh':f'meshes/{name}.stl','volume_mm3':shape.Volume(),
                      'bbox_mm':[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax]})
    graphite=(.025,.032,.043);metal=(.28,.32,.36);amber=(.80,.34,.035);light=(1.,.62,.16)
    base=cq.Workplane('XY').box(230,190,12,centered=(True,True,False)).edges('|Z').fillet(12)
    base=base.faces('>Z').workplane().pushPoints([(-95,-75),(95,-75),(-95,75),(95,75)]).hole(9)
    add('BASE_layout',base.val(),0,graphite,'base_study')
    for i,j in enumerate(p['joints']):
        iface=interfaces[j['model']]; boss=iface['central_clearance_boss']['height_above_output_contact_mm']
        T=frame(j['origin_mm'],j['axis']);bottom=boss-j['length_mm']
        body=cq.Workplane('XY').workplane(offset=bottom).circle(j['diameter_mm']/2).circle(j['bore_mm']/2).extrude(j['length_mm']).val()
        add(j['id']+'_housing_envelope',moved(body,T),i,graphite)
        # The shaft/output is shown separately to preserve moving-side ownership.
        pilot=iface['outer_output_pilot']['diameter_mm']; points=[h['xy_mm'] for h in iface['output_holes']['points']]
        disk=cq.Workplane('XY').circle(pilot/2).circle(j['bore_mm']/2+1).extrude(4)
        disk=disk.faces('>Z').workplane().pushPoints(points).hole(3.4 if pilot<80 else 4.4)
        add(j['id']+'_output_visual',moved(disk.val(),T),i+1,metal,'output_visual')
        collar=cq.Workplane('XY').workplane(offset=bottom+8).circle(j['diameter_mm']/2+.6).circle(j['diameter_mm']/2).extrude(5)
        add(j['id']+'_accent',moved(collar.val(),T),i,amber,'trim')
    # Closed rectangular beam is the stiffness-screening candidate; removable
    # armour does not substitute for the load path. End adapters remain open.
    for i in [2,4]:
        a=np.asarray(p['joints'][i]['origin_mm'],dtype=float)
        b=np.asarray(p['joints'][i+1]['origin_mm'],dtype=float)
        a[2]+=12;b[2]-=p['joints'][i+1]['diameter_mm']/2+8
        mid=(a+b)/2;length=np.linalg.norm(b-a)
        beam=cq.Workplane('XY').rect(60,40).rect(54,34).extrude(length).val()
        add(f'L{i+1}_closed_beam_study',moved(beam,frame(a,b-a)),i+1,metal,'beam_study')
        shell=cq.Workplane('XY').polyline([(-34,-24),(34,-24),(32,24),(-32,24)]).close().extrude(length)
        cut=cq.Workplane('XY').rect(62,44).extrude(length)
        shell=shell.cut(cut).val()
        add(f'L{i+1}_shell_study',moved(shell,frame(a,b-a)),i+1,graphite,'shell_study')
    h=p['head'];face=np.asarray(h['face_center_mm'],dtype=float)
    # Open truss reservation, not a fictional solid head that hides missing motors.
    rear=np.asarray(h['mount_origin_mm'],dtype=float)
    for z in [rear[2],face[2]-14]:
        ring=cq.Workplane('XY').circle(105).circle(94).extrude(5).val()
        T=np.eye(4);T[:3,3]=[face[0],face[1],z]
        add(f'HEAD_ring_{int(z)}',moved(ring,T),7,graphite,'head_reservation')
    for angle in [45,135,225,315]:
        r=np.deg2rad(angle);offset=np.array([99*np.cos(r),99*np.sin(r),0])
        a=rear+offset;b=face+offset;b[2]-=14
        add(f'HEAD_rail_{angle}',tube_between(a,b,10,2),7,metal,'head_reservation')
    front=cq.Workplane('XY').circle(h['central_core_diameter_mm']/2).extrude(6)
    tabs=cq.Workplane('XY').box(32,128,6,centered=(True,True,False))
    front=front.union(tabs)
    T=np.eye(4);T[:3,3]=face-[0,0,6]
    front=moved(front.val(),T)
    screen=cq.Workplane('XY').circle(h['screen_diameter_mm']/2).extrude(1).val()
    T[:3,3]=face+[0,0,1]
    add('HEAD_screen',moved(screen,T),7,(.025,.03,.035),'screen')
    for sign in [-1,1]:
        centre=face+np.array([0,sign*h['camera_baseline_mm']/2,0])
        pitch=-sign*np.deg2rad(h['camera_outward_pitch_deg'])
        T=np.eye(4);T[:3,:3]=Rotation.from_rotvec([pitch,0,0]).as_matrix();T[:3,3]=centre
        camera=cq.Workplane('XY').box(25,25,34.2,centered=(True,True,False)).translate((0,0,-34.2)).val()
        lens=cq.Workplane('XY').circle(10).extrude(5).val()
        clearance=cq.Workplane('XY').box(27,27,40,centered=(True,True,False)).translate((0,0,-35.2)).val()
        front=front.cut(moved(clearance,T))
        add(f'CAM_{sign}_module',moved(camera,T),7,metal,'camera_envelope')
        add(f'CAM_{sign}_lens',moved(lens,T),7,(.025,.055,.07),'camera_envelope')
    drive=json.loads((ROOT/'analysis/gripper-drive-packaging-forward-lower.json').read_text())
    for item in drive['coordinates']:
        fid=item['finger'];phi=np.deg2rad(item['phi_deg'])
        et=np.array([-np.sin(phi),np.cos(phi),0]);axis=et*item['motor_axis_sign_e_t']
        body_center=face+np.array(item['body_center_mm'])
        body=cq.Workplane('XY').circle(11).extrude(70.1).val()
        add('HEAD_DRIVE_'+fid+'_motor_proxy',moved(body,frame(body_center-axis*35.05,axis)),7,metal,'unconfirmed_drive_envelope')
        shaft=cq.Workplane('XY').circle(3).extrude(16.3).val()
        add('HEAD_DRIVE_'+fid+'_shaft_proxy',moved(shaft,frame(face+item['front_mounting_face_center_mm'],axis)),7,metal,'unconfirmed_drive_envelope')
        for wheel,key in [('input','drive_pulley_center_mm'),('output','hinge_pulley_center_mm')]:
            shape=cq.Workplane('XY').circle(17).circle(3 if wheel=='input' else 6).extrude(14).val()
            add('HEAD_DRIVE_'+fid+'_'+wheel+'_pulley_proxy',moved(shape,frame(face+item[key]-axis*7,axis)),7,amber,'assumed_pulley_envelope')
        a=np.asarray(item['drive_pulley_center_mm']);b=np.asarray(item['hinge_pulley_center_mm'])
        r=90/(2*np.pi);C=np.linalg.norm(b-a)
        belt=cq.Workplane('XY').slot2D(C+2*(r+1.5),2*(r+1.5)).extrude(9)
        hole=cq.Workplane('XY').slot2D(C+2*(r-1.5),2*(r-1.5)).extrude(9)
        add('HEAD_DRIVE_'+fid+'_belt_proxy',moved(belt.cut(hole).val(),frame(face+(a+b)/2-axis*4.5,axis,b-a)),7,graphite,'assumed_belt_envelope')
        # Non-load-bearing face cover: reserve 2 mm around the assumed belt.
        clearance=cq.Workplane('XY').slot2D(C+2*(r+3.5),2*(r+3.5)).extrude(13).val()
        front=front.cut(moved(clearance,frame(face+(a+b)/2-axis*6.5,axis,b-a)))
    add('HEAD_front_core',front,7,graphite,'head_reservation')
    for f in h['fingers']:
        phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0]);et=np.array([-np.sin(phi),np.cos(phi),0])
        root=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
        T=np.eye(4);T[:3,:3]=np.column_stack([er,et,[0,0,1]]);T[:3,3]=root
        L,W,thick=f['length_mm'],f['width_mm'],f['thickness_mm']
        outline=[(0,-W*.27),(L*.18,-W*.5),(L*.72,-W*.25),(L,-W*.05),(L,W*.05),(L*.72,W*.25),(L*.18,W*.5),(0,W*.27)]
        body=cq.Workplane('XY').polyline(outline).close().extrude(thick).val()
        window=[(L*.13,-W*.24),(L*.24,-W*.36),(L*.72,-W*.20),(L*.94,-W*.08),(L*.94,W*.08),(L*.72,W*.20),(L*.24,W*.36),(L*.13,W*.24)]
        led=cq.Workplane('XY').workplane(offset=thick).polyline(window).close().extrude(.6).val()
        add('F_'+f['id']+'_structure',moved(body,T),7,graphite,'finger_study',f['id'])
        add('F_'+f['id']+'_light',moved(led,T),7,light,'finger_light',f['id'])
        # Paired proud pads protect the recessed luminous area.
        for side in [-1,1]:
            s=f['contact_along_mm'];qh=np.deg2rad(f['pad_target_q_deg']);slope=1/np.tan(qh)
            pad=cq.Workplane('XZ').polyline([(s-9,thick),(s+9,thick),(s+9,11+9*slope),(s-9,11-9*slope)]).close().extrude(5).translate((0,side*W*.08+2.5,0)).val()
            add(f'F_{f["id"]}_pad_{side}',moved(pad,T),7,(.27,.30,.32),'contact_candidate',f['id'])
    assembly.save(str(OUT/'odradek-layout.step'))
    manifest={'revision':p['revision'],'status':'NOT FOR MANUFACTURE: envelope and rail routing study',
              'parameters_sha256':hashlib.sha256((ROOT/'engineering/parameters/r4-layout.json').read_bytes()).hexdigest(),
              'length_unit':'mm','parts':parts,'parameters':'../../parameters/r4-layout.json',
              'omissions':['exact brackets and fasteners','true motor combination/pulley hubs','independent shaft supports and tensioners','qualified harness paths','collision-qualified full mechanism motion']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Remove only obsolete exports in these generator-owned directories.
    for directory,suffix in [('meshes','.stl'),('parts-step','.step')]:
        valid={part['name']+suffix for part in parts}
        for old in (OUT/directory).glob('*'+suffix):
            if old.name not in valid:old.unlink()
    print(f'Created {len(parts)} valid analytic solids/groups, STEP and mesh manifest at {OUT}')


if __name__=='__main__':main()
