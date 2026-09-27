# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Recessed CONTACT02 LED stack and board mounts; not ECAD or thermal release."""
from pathlib import Path
import hashlib,json,math
import cadquery as cq
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from build_layout import moved

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'engineering/generated/led-petal-pocket'
SRC=ROOT/'engineering/generated/contact02-study';RET=ROOT/'engineering/generated/pad-retention-study'
SCREW_SOURCE='https://www.nbk1560.com/images/en-US/product/lowsmallheadscrew/SSH/SSH_1.pdf'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def box(x,y,z,c):return cq.Workplane('XY').box(x,y,z).translate(tuple(c)).val()
def cyl(r,z,h,x,y):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),cq.Vector(0,0,1))
def prism(w,z,h):return cq.Solid.extrudeLinear(w.translate((0,0,z)),[],cq.Vector(0,0,h))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    s=json.loads((SRC/'study.json').read_text());p=json.loads((ROOT/'engineering/parameters/r4-layout.json').read_text());face=np.array(p['head']['face_center_mm'])
    budgetpath=ROOT/'engineering/electronics/upper-petal-prototype/mechanical-power-budget.json'
    budget=json.loads(budgetpath.read_text())
    assert budget['front_LED_height_max_mm']==.8 and budget['back_bulk_cap_max_mm']==1.45
    rows=[];hashes={str((SRC/'study.json').relative_to(ROOT)):sha(SRC/'study.json'),str(budgetpath.relative_to(ROOT)):sha(budgetpath)}
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for ii,fi in enumerate([0,2]):
        f=s['fingers'][fi];L=f['length_mm'];variant='UPPER' if fi==0 else 'LOWER'
        phi=np.deg2rad(f['phi_deg']);er=np.array([np.cos(phi),np.sin(phi),0]);et=np.array([-np.sin(phi),np.cos(phi),0]);T=np.eye(4)
        T[:3,:3]=np.column_stack([er,et,[0,0,1]]);T[:3,3]=face+f['root_radius_mm']*er+[0,0,f['root_z_mm']]
        bodypath=RET/f'ODR-RET-{variant}-BLADE.step';lightpath=SRC/'parts-step'/f'{f["id"]}_light.step'
        hashes[str(bodypath.relative_to(ROOT))]=sha(bodypath);hashes[str(lightpath.relative_to(ROOT))]=sha(lightpath)
        oldbody=cq.importers.importStep(str(bodypath)).val().translate((L,0,0))
        oldlight=moved(cq.importers.importStep(str(lightpath)).val(),np.linalg.inv(T))
        clipped=oldlight.intersect(box(L-49,100,10,[(27+L-22)/2,0,5])).clean()
        top=max(clipped.Faces(),key=lambda x:x.Center().z);wire=top.outerWire().translate((0,0,-6.6))
        pocketwire=wire.offset2D(.25,kind='intersection')[0]
        body=oldbody.cut(prism(pocketwire,1.9,4.2))
        # Backward access is only a reserved aperture. The mating connector,
        # cable strain relief and closure envelope still need separate modeling.
        connector_cut=box(9,17.5,7,[43,0,3])
        body=body.cut(connector_cut)
        mount=[(33.,8. if fi==0 else 6.),(33.,-8. if fi==0 else -6.),(L-28.,0.)]
        for x,y in mount:body=body.fuse(cyl(2.75,1.9,1.5,x,y))
        for x,y in mount:body=body.cut(cyl(.8,-.1,3.6,x,y))
        body=body.clean()
        pcb=prism(wire,3.6,.8);led=prism(wire,4.4,.8);back=prism(wire,2.15,1.45)
        for x,y in mount:
            pcb=pcb.cut(cyl(1.2,3.5,1.,x,y))
            led=led.cut(cyl(3.25,4.3,1.,x,y));back=back.cut(cyl(3.25,2.,1.8,x,y))
        back=back.cut(box(10,18.5,3,[43,0,3]))
        parts={'metal':body,'PCB_outline':pcb.clean(),'front_LED_volume_reserve':led.clean(),
               'back_component_volume_reserve':back.clean(),'optical_sheet':prism(wire,6.,.6)}
        free_screws={}
        for j,(x,y) in enumerate(mount,1):
            gasket=cyl(2.75,3.4,.2,x,y).cut(cyl(1.2,3.3,.4,x,y))
            screw=cyl(2.,4.4,1.1,x,y).fuse(cyl(1.,.4,4.,x,y))
            # Thread engagement deliberately omitted from clearance solid.
            free_screws[f'screw{j}']=cyl(2.,4.4,1.1,x,y).fuse(cyl(1.,3.4,1.,x,y))
            parts[f'insulating_ring{j}']=gasket;parts[f'SSH_M2_4_{j}']=screw
        old_envelope=oldbody.fuse(oldlight).clean();outside=[];exports=[]
        for name,shape in parts.items():
            assert shape.isValid() and len(shape.Solids())>=1
            v=shape.cut(old_envelope).Volume();outside.append({'part':name,'outside_prior_envelope_mm3':v});assert v<1e-5
            path=OUT/f'{variant}-{name}.step';cq.exporters.export(shape,str(path))
            read=cq.importers.importStep(str(path)).val();assert read.isValid() and abs(read.Volume()-shape.Volume())<1e-5
            exports.append({'part':name,'path':path.name,'solids':len(read.Solids()),'volume_mm3':shape.Volume(),'sha256':sha(path)})
        # A new reserve must not silently include the mounting posts or screws.
        collision=[];checkparts=dict(parts)
        for j in range(1,4):checkparts[f'SSH_M2_4_{j}']=free_screws[f'screw{j}']
        names=list(checkparts)
        for i,a in enumerate(names):
            for b in names[i+1:]:
                vol=sum(x.intersect(y).Volume() for x in checkparts[a].Solids() for y in checkparts[b].Solids())
                collision.append({'a':a,'b':b,'intersection_mm3':vol});assert vol<1e-5,(variant,a,b,vol)
        # Direct free-shank / insulating-ring / PCB fit is part of the above;
        # no thread helices or assembly preload are implied by the pilot bore.
        r={'variant':variant,'length_mm':L,'mount_centers_root_xy_mm':mount,
           'metal_mass_before_g':oldbody.Volume()*.0027,'metal_mass_after_g':body.Volume()*.0027,
           'new_metal_volume_mm3':body.Volume(),'pocket_floor_nominal_mm':1.9,
           'PCB_bottom_top_mm':[3.6,4.4],'LED_bottom_top_mm':[4.4,5.2],
           'back_components_bottom_top_mm':[2.15,3.6],'diffuser_bottom_top_mm':[6.,6.6],
           'mixing_gap_mm':.8,'back_component_to_floor_nominal_gap_mm':.25,
           'boss_top_mm':3.4,'insulating_ring_thickness_mm':.2,'screw_cap_top_mm':5.5,
           'screw_to_sheet_clearance_mm':.5,'screw_geometric_engagement_mm':3.,'screw_tip_recess_mm':.4,
           'connector_aperture_xyz_mm':[9,17.5,6],'connector_aperture_center_xy_mm':[43,0],
           'connector_mated_bottom_if_board_bottom_3_6_mm':3.6-budget['GH_mated_reference_height_mm'],
           'nominal_external_subset_checks':outside,'static_component_intersections':collision,'parts':exports,
           'continuous_external_separation_scope':'All exported parts lie within previous rigid body/light envelope. Connector, cable, optical-sheet retention and deformation excluded.'}
        rows.append(r)
        assembly=cq.Assembly(name='LED_POCKET_'+variant)
        for name,shape in parts.items():assembly.add(shape,name=name)
        assembly.save(str(OUT/f'{variant}-assembly.step'))
        ax=axes[ii,0];W=f['width_mm'];outline=np.array([(0,-.27*W),(.18*L,-.5*W),(L,-7),(L,7),(.18*L,.5*W),(0,.27*W)])
        ax.fill(*outline.T,color='#556875',alpha=.5)
        vv=np.array([v.toTuple() for v in wire.Vertices()]);from scipy.spatial import ConvexHull
        h=ConvexHull(vv[:,:2]);poly=vv[h.vertices,:2];ax.fill(*poly.T,color='#d5b66f')
        ax.add_patch(plt.Rectangle((38.5,-8.75),9,17.5,facecolor='#e7e8e7',edgecolor='#546c71'))
        for x,y in mount:ax.add_patch(plt.Circle((x,y),3.25,facecolor='#edf0ed',edgecolor='#2c7477'));ax.add_patch(plt.Circle((x,y),1.2,facecolor='#546875'))
        ax.set(aspect='equal',xlabel='Root x / mm',ylabel='Local y / mm',title=variant+' / PCB and LED keepouts')
        ax=axes[ii,1]
        for z,h,col,label in [(0,1.9,'#566b77','metal floor'),(2.15,1.45,'#4c9990','back components'),(3.6,.8,'#37755b','PCB'),(4.4,.8,'#dfa843','LEDs'),(6,.6,'#eee0ad','optical sheet')]:
            ax.add_patch(plt.Rectangle((0,z),10,h,color=col));ax.text(10.4,z+h/2,label,va='center',fontsize=9)
        ax.plot([2,2],[3.6,-3.7],color='#c5684f',lw=3);ax.text(2,-4.7,'GH height only; full rear envelope pending',ha='center',fontsize=8)
        ax.set(xlim=(-5,26),ylim=(-6,8),xlabel='Stack schematic / no x scale',ylabel='Z from blade back / mm',title=variant+' / ordinary region and root height')
    fig.suptitle('Recessed LED packaging candidate / ordinary layers and real screw dimensions')
    fig.savefig(OUT/'led-pocket-study.png',dpi=165);plt.close(fig)
    data={'revision':'R4-LED-POCKET-01','manufacturing_release':False,'generator_sha256':sha(Path(__file__)),
       'input_sha256':hashes,'variants':rows,'screw':{'candidate':'NBK SSH-M2-4','source':SCREW_SOURCE,
       'thread':'M2x0.4','length_mm':4,'head_D_H_mm':[4,1.1],'hex_key_mm':1.3,
       'catalog_max_torque_Nm':.3,'selected_assembly_torque_Nm':None,'note':'Catalog max is not PCB mounting torque; threads/PCB/gasket need joint preload design.'},
       'limits':['Mechanical envelope allocation only; not the current 113-site ULP01/02 board.',
                 'No geometric proof for mated GH envelope, cable bends, root support interaction or connector accessibility.',
                 'Optical sheet retention, mixing quality, thermal field, dielectric isolation and component solder height not qualified.',
                 'Pockets and through connector aperture weaken blade; rigidity/stress and tolerance stack need re-evaluation.',
                 'Backing components are allocated volumes, not solid blocks of actual component material; do not use these reserve volumes as mass.',
                 'Insulating rings are custom thickness assumptions with no selected material/supplier or compressive qualification.',
                 'Screw thread represented by nominal shank and minor pilot bore; thread zone excluded only from intersection check.',
                 'No actual LED positions or copper traces assigned. Mount keepouts require redesigned final boards.']}
    (OUT/'study.json').write_text(json.dumps(data,indent=2)+'\n')
    print([(r['variant'],r['metal_mass_before_g'],r['metal_mass_after_g'],len(r['static_component_intersections'])) for r in rows])

if __name__=='__main__':main()
