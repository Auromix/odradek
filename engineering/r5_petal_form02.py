#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""FORM02 shoulder-cut layered CAD and fixed-q radial-stage geometry study.
No implemented drive, fold-stage, speed or payload claim.

Local x points root -> tip, y lies across the face, +z points toward an object.
Known-material parts are separate from electronic allocation volumes.
"""
from pathlib import Path
import argparse, copy, csv, hashlib, itertools, json, math
import cadquery as cq
from cadquery.occ_impl.exporters.dxf import DxfDocument
import ezdxf
import numpy as np
import trimesh
from head_mass04_study import geometry_properties, tensor_check, unit_checks
from build_link56_study import face_contact
from screen_integrated_collisions import named_step
from build_layout import moved

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'engineering/generated/r5-petal-form02'
REV='R5-PETAL-FORM02'
NOTICE='Odradek — Auromix contributors (https://github.com/Auromix/odradek)'
DEFAULT={
 'revision':REV,'units':'mm','local_frame':'+x root to tip; +y in-plane; +z luminous gripping side',
 'upper':{'length_mm':150.,'template_length_mm':150.,'width_scale':1.,'outline_knots_mm':[[0,-9],[15,-9],[21,-23],[29,-23],[51,-23],[60,-16],[143,-16],[150,-9],[150,12],[145,17],[28,17],[21,13],[15,9],[0,9]],'module_x_mm':[30.,142.],'retainer_x_start_mm':21.,'retainer_holes_mm':[[26,-19],[26,10],[146.5,-4],[146.5,7]],'section_x_mm':[7.,17.,35.,80.,125.,145.]},
 'lower':{'length_mm':100.,'template_length_mm':100.,'width_scale':1.,'outline_knots_mm':[[0,-9],[15,-9],[23,-16],[91,-16],[100,-8],[100,6],[94,12],[57,13],[49,23],[29,23],[21,18],[15,9],[0,9]],'module_x_mm':[30.,92.],'retainer_x_start_mm':21.,'retainer_holes_mm':[[26,-10],[26,15],[96.5,-4],[96.5,4]],'section_x_mm':[7.,17.,35.,65.,90.]},
 'outline_corner_radius_mm':.8,'outer_wall_to_cover_pocket_mm':2.8,'cover_radial_clearance_mm':.2,'cover_support_ledge_inset_from_pocket_mm':2.4,'skin_face_inset_from_cover_mm':1.2,'skin_to_bezel_radial_clearance_mm':.15,
 'z_mm':{'frame_back':0.,'floor_top':1.5,'frame_front':7.,'cover_seat':5.5,'cover_front':8.,'skin_flange_top':8.4,'skin_face':9.5,'retainer_back':7.,'retainer_front':9.,'PCB':[3.5,4.3],'back_electronics':[1.75,3.4],'front_LED':[4.4,5.2]},
 'root_interface_holes_mm':[[7,-4.5],[7,4.5],[17,-4.5],[17,4.5]],'root_hole_D_mm':3.2,'retainer_hole_D_mm':2.2,'retainer_countersink_major_D_mm':4.2,'retainer_countersink_angle_deg':90.,
 'densities_kg_m3':{'frame':2700.,'retainer':2700.,'bearing_cover':1200.,'compliant_skin':1030.},
 'form_preview':{'UR':{'kind':'upper','hand':'right','root_xy_mm':[46.6690475583,46.6690475583],'angle_deg':45.},'UL':{'kind':'upper','hand':'left','root_xy_mm':[-46.6690475583,46.6690475583],'angle_deg':135.},'LR':{'kind':'lower','hand':'right','root_xy_mm':[46.6690475583,-46.6690475583],'angle_deg':315.},'LL':{'kind':'lower','hand':'left','root_xy_mm':[-46.6690475583,-46.6690475583],'angle_deg':225.}},
 'qualification':{'root_pattern':'Candidate flat mechanical attachment only; not a selected shaft, hinge, hub or fastener stack.','electronics':'New outlines/reservations; no FPL board is inserted.','form_preview':'Illustrative open arrangement only, not a head assembly or motion solution.','material_density':'Nominal mass assumptions; not procurement or mechanical allowables.'}}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,(np.integer,np.floating,np.bool_)):return x.item()
 raise TypeError(type(x).__name__)
def dump(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,default=serial)+'\n')
def vol(s):return sum(abs(t.Volume()) for t in s.Solids())
def bbox(s):
 b=s.BoundingBox();return np.array([[b.xmin,b.ymin,b.zmin],[b.xmax,b.ymax,b.zmax]])
def prism(w,z0,z1):return cq.Solid.extrudeLinear(w,[],(0,0,z1-z0)).translate((0,0,z0))
def box(x0,x1,y0,y1,z0,z1):return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0).translate(((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)).val()
def top_wire(shape,z=1.):return cq.Workplane(obj=shape).faces('>Z').val().outerWire().translate((0,0,-z))
def inset(w,d):
 r=w.offset2D(-d,'intersection');assert len(r)==1;assert cq.Face.makeFromWires(r[0]).isValid();return r[0]
def hole(x,y,r,z0,z1):return cq.Solid.makeCylinder(r,z1-z0,cq.Vector(x,y,z0))
def common(a,b):return sum(vol(x.intersect(y)) for x in a.Solids() for y in b.Solids())
def transform(s,T):return moved(s,T)
def planar_profile(coords,r):
 s=cq.Workplane('XY').polyline(coords).close().extrude(1.).edges('|Z').fillet(r).val();assert s.isValid();return top_wire(s)
def combine(rows):
 mass=sum(r['mass_kg'] for r in rows);c=sum(r['mass_kg']*np.array(r['COM_local_m']) for r in rows)/mass;I=np.zeros((3,3))
 for r in rows:
  d=np.array(r['COM_local_m'])-c;I+=np.array(r['inertia_COM_local_axes_kg_m2'])+r['mass_kg']*((d@d)*np.eye(3)-np.outer(d,d))
 return dict(mass_kg=mass,COM_local_m=c,inertia_COM_local_axes_kg_m2=I,tensor_check=tensor_check(I),mass_is_assumed_not_measured=True,PCB_LED_fasteners_connector_wire_mass_included=False)

def build(kind,p):
 k=p[kind];sx=k['length_mm']/k['template_length_mm'];sy=k['width_scale'];pts=np.array(k['outline_knots_mm'])*[sx,sy];O=planar_profile(pts,p['outline_corner_radius_mm']);G=inset(O,p['outer_wall_to_cover_pocket_mm']);a,b=np.array(k['module_x_mm'])*sx;G=top_wire(prism(G,0,1).intersect(box(a,b,-100,100,-1,2)))
 P=inset(G,p['cover_radial_clearance_mm']);C=inset(G,p['cover_support_ledge_inset_from_pocket_mm']);L=inset(P,p['skin_face_inset_from_cover_mm']);Lclear=inset(L,-p['skin_to_bezel_radial_clearance_mm']);B=inset(C,.6);E=inset(B,.35);R=top_wire(prism(O,0,1).intersect(box(k['retainer_x_start_mm']*sx,1000,-100,100,-1,2)))
 z=p['z_mm'];s=prism(O,z['frame_back'],z['frame_front']);s=s.cut(prism(G,z['cover_seat'],20)).cut(prism(C,z['floor_top'],20));frame=s
 retainer=prism(R,z['retainer_back'],z['retainer_front']).cut(prism(G,6.9,z['skin_flange_top'])).cut(prism(Lclear,6.9,20))
 root_holes=np.array(p['root_interface_holes_mm'])*[sx,sy];fast_holes=np.array(k['retainer_holes_mm'])*[sx,sy]
 holechecks=[]
 for x,y in root_holes:
  probe=hole(x,y,p['root_hole_D_mm']/2,-1,10);before=common(frame,probe);assert before>0;frame=frame.cut(probe);holechecks.append(dict(pattern='root',xy_mm=[x,y],D_mm=p['root_hole_D_mm'],removed_frame_mm3=before))
 for x,y in fast_holes:
  probe=hole(x,y,p['retainer_hole_D_mm']/2,-1,11)
  # The holes must stay entirely in a solid cap of both metal components.
  for n,t,z0,z1 in [('frame',frame,0,7),('retainer',retainer,7,9)]:
   full=hole(x,y,p['retainer_hole_D_mm']/2,z0,z1);outside=vol(full.cut(t));assert outside<1e-5,(kind,n,[x,y],outside)
  frame=frame.cut(probe);retainer=retainer.cut(probe)
  r0=p['retainer_hole_D_mm']/2;r1=p['retainer_countersink_major_D_mm']/2;depth=(r1-r0)/math.tan(math.radians(p['retainer_countersink_angle_deg']/2));assert depth<z['retainer_front']-z['retainer_back'];cs=cq.Solid.makeCone(r0,r1,depth,cq.Vector(x,y,z['retainer_front']-depth));retainer=retainer.cut(cs)
  holechecks.append(dict(pattern='retainer',xy_mm=[x,y],D_mm=p['retainer_hole_D_mm'],through_both_metal_parts=True,countersink_major_D_mm=2*r1,countersink_angle_deg=p['retainer_countersink_angle_deg'],countersink_depth_mm=depth,fastener_head_must_not_exceed_z_mm=z['retainer_front'],fastener_selected=False))
 parts={'frame':frame,'retainer':retainer,'bearing_cover':prism(P,z['cover_seat'],z['cover_front']),'compliant_skin':prism(P,z['cover_front'],z['skin_flange_top']).fuse(prism(L,z['skin_flange_top'],z['skin_face'])),'PCB_blank_reservation':prism(B,*z['PCB']),'back_electronics_reservation':prism(E,*z['back_electronics']),'LED_front_reservation':prism(E,*z['front_LED'])}
 assert all(s.isValid() and len(s.Solids())==1 for s in parts.values())
 collisions={}
 for n,m in itertools.combinations(parts,2):
  v=common(parts[n],parts[m]);assert v<1e-5,(kind,n,m,v);collisions[n+'__'+m]=v
 contacts={}
 for a,b,zpos in [('frame','bearing_cover',z['cover_seat']),('bearing_cover','compliant_skin',z['cover_front']),('retainer','compliant_skin',z['skin_flange_top']),('frame','retainer',z['frame_front'])]:
  contact=face_contact(parts[a],parts[b],[0,0,zpos],[0,0,1]);assert contact['shared_planar_face_area_mm2']>1;contacts[a+'__'+b]=contact
 # Section properties of actual metal, holes included. A thin-slice convergence
 # check removes the exact in-plane slab contribution from the 3D tensor.
 sections=[]
 for x in np.array(k['section_x_mm'])*sx:
  results=[]
  for dx in [.04,.02]:
   slab=frame.intersect(box(x-dx/2,x+dx/2,-100,100,-1,12));g=geometry_properties(slab);A=g['volume_mm3']/dx;J=g['inertia_per_mass_m2']*g['volume_mm3']*1e6/dx;J[1,1]-=A*dx*dx/12;J[2,2]-=A*dx*dx/12;results.append(dict(slice_width_mm=dx,area_mm2=A,centroid_yz_mm=(g['com_m'][1:]*1000),Iyy_mm4=J[1,1],Izz_mm4=J[2,2],Iyz_tensor_mm4=J[1,2]))
  error=max(abs(results[0][q]-results[1][q])/max(abs(results[1][q]),1.) for q in ['area_mm2','Iyy_mm4','Izz_mm4']);assert error<.02;sections.append(dict(x_mm=x,result=results[1],halved_slice_relative_change=error,scope='Actual nominal frame net section only; not beam/plate deflection or strength qualification.'))
 metadata=[]
 for n,s in parts.items():
  g=geometry_properties(s);rho=p['densities_kg_m3'].get(n);mass=None if rho is None else g['volume_mm3']*rho*1e-9;I=None if mass is None else g['inertia_per_mass_m2']*mass
  metadata.append(dict(id=n,kind=kind,volume_mm3=g['volume_mm3'],bbox_local_mm=bbox(s),assumed_density_kg_m3=rho,mass_kg=mass,COM_local_m=None if mass is None else g['com_m'],inertia_COM_local_axes_kg_m2=I,mass_status='Unknown reservation; no density assigned' if mass is None else 'Nominal CAD volume times stated candidate density; not measured',representation='electronic allocation volume only' if mass is None else 'original part candidate',tensor_check=None if mass is None else tensor_check(I)))
 report=dict(kind=kind,outer_knots_mm=pts,overall_bbox_mm=bbox(cq.Compound.makeCompound(list(parts.values()))),root_holes=root_holes,retainer_holes=fast_holes,profile_areas_mm2={n:cq.Face.makeFromWires(w).Area() for n,w in [('outer',O),('cover',P),('contact_face',L),('PCB_candidate',B)]},contacts=contacts,all_pair_intersections_mm3=collisions,section_results=sections,hole_checks=holechecks,parts=metadata,known_material_subtotal=combine([r for r in metadata if r['mass_kg'] is not None]),compression_path='Object -> replaceable skin -> PC bearing cover -> perimeter shelf -> integral dark frame/floor -> candidate root pad. PCB/LED are not structural supports.',skin_tangential_retention='Peripheral flange under retainer lip with zero nominal preload; shear, peel and cyclic retention capacity are unknown.',nominal_skin_face_stand_proud_mm=z['skin_face']-z['retainer_front'],LED_to_PC_gap_mm=z['cover_seat']-z['front_LED'][1],back_electronics_to_floor_gap_mm=z['back_electronics'][0]-z['floor_top'])
 return parts,{'outer':O,'cover':P,'contact_face':L,'PCB_candidate':B,'retainer_outer':R,'retainer_opening':Lclear},report

def mirrored(s,hand):return s if hand=='right' else s.mirror('XZ')
def export_sets(families,p):
 exportqa=[];rows=[];allassembly=cq.Assembly(name=REV+'-FORM-PREVIEW-NOT-MOTION');color={'frame':'#415f6a','retainer':'#243c47','bearing_cover':'#93cad3','compliant_skin':'#f1c46e','PCB_blank_reservation':'#357964','back_electronics_reservation':'#806ca5','LED_front_reservation':'#efaa31'}
 for kind,(parts,profiles,rep) in families.items():
  for hand in ['right','left']:
   tag=kind+'-'+hand;folder=OUT/tag;folder.mkdir(parents=True,exist_ok=True);assembly=cq.Assembly(name=REV+'-'+tag);doc=DxfDocument(doc_units=4,tolerance=.01);q=[]
   for layer,w in profiles.items():doc.add_layer(layer,color=7);doc.add_shape(mirrored(w,hand),layer=layer)
   for pattern,D in [('root_holes',p['root_hole_D_mm']),('retainer_holes',p['retainer_hole_D_mm']),('retainer_countersink',p['retainer_countersink_major_D_mm'])]:
    doc.add_layer(pattern,color=1)
    for x,y in rep['retainer_holes' if pattern=='retainer_countersink' else pattern]:doc.msp.add_circle((x,y if hand=='right' else -y),D/2,dxfattribs={'layer':pattern})
   dxf=folder/'profiles.dxf';doc.document.saveas(dxf);rt=ezdxf.readfile(dxf);assert rt.header['$INSUNITS']==4;assert len(list(rt.modelspace().query('CIRCLE')))==12
   from ezdxf.bbox import extents
   bb=extents([e for e in rt.modelspace() if e.dxf.layer=='outer'],fast=False);dx=np.array([[bb.extmin.x,bb.extmin.y],[bb.extmax.x,bb.extmax.y]]);expected=bbox(mirrored(prism(profiles['outer'],0,1),hand))[:,:2];dxferr=float(np.max(abs(dx-expected)));assert dxferr<.02
   for n,s0 in parts.items():
    s=mirrored(s0,hand);file=folder/(n+'.step');cq.exporters.export(s,str(file));b=cq.importers.importStep(str(file)).val();assert b.isValid() and len(b.Solids())==1;g=geometry_properties(s);back=geometry_properties(b);assert abs(g['volume_mm3']-back['volume_mm3'])<1e-4 and np.max(abs(g['com_m']-back['com_m']))<1e-8;assembly.add(s,name=n,color=cq.Color(color[n]));item=dict(kind=kind,hand=hand,id=n,file=str(file.relative_to(OUT)),sha256=sha(file),volume_error_mm3=abs(g['volume_mm3']-back['volume_mm3']))
    if n in p['densities_kg_m3']:
     stl=folder/(n+'.stl');cq.exporters.export(s,str(stl),tolerance=.03,angularTolerance=.08);mesh=trimesh.load(stl,force='mesh',process=True);assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0;vrel=abs(mesh.volume-vol(s))/vol(s);assert vrel<.005;item.update(STL=str(stl.relative_to(OUT)),STL_sha256=sha(stl),watertight=True,STL_CAD_volume_relative_error=vrel)
    rho=p['densities_kg_m3'].get(n);mass=None if rho is None else g['volume_mm3']*rho*1e-9;item.update(assumed_density_kg_m3=rho,mass_kg=mass,COM_hand_local_m=None if mass is None else g['com_m'],inertia_COM_hand_local_axes_kg_m2=None if mass is None else mass*g['inertia_per_mass_m2'],mass_is_assumed_not_measured=True)
    q.append(item)
   a=folder/(REV+'-'+tag+'.step');assembly.save(str(a));assert len(named_step(a))==7;exportqa.append(dict(kind=kind,hand=hand,named_parts=7,STEP=str(a.relative_to(OUT)),STEP_sha256=sha(a),DXF=str(dxf.relative_to(OUT)),DXF_sha256=sha(dxf),DXF_units='mm',DXF_circle_count=12,DXF_outer_bbox_error_mm=dxferr,parts=q))
 for finger,placement in p['form_preview'].items():
  kind,hand=placement['kind'],placement['hand'];theta=math.radians(placement['angle_deg']);T=np.eye(4);T[:3,:3]=[[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]];T[:2,3]=placement['root_xy_mm']
  for n,s in families[kind][0].items():
   actual=transform(mirrored(s,hand),T);name=finger+'_'+n;allassembly.add(actual,name=name,color=cq.Color(color[n]));rows.append(dict(id=name,kind=kind,hand=hand,form_preview_transform_from_hand_local_mm=T,bbox_form_preview_mm=bbox(actual),source_geometry=f'{kind}-{hand}/{n}.step',source_sha256=sha(OUT/f'{kind}-{hand}/{n}.step'),assembly_is_kinematically_qualified=False))
 file=OUT/(REV+'-four-petal-form.step');allassembly.save(str(file));back=named_step(file);assert len(back)==28
 # Exact left/right mirror proof is on complete originals, not only silhouette.
 mirrors={}
 for kind,(parts,_,_) in families.items():
  for n,s in parts.items():
   reflected=mirrored(mirrored(s,'left'),'left');v=vol(s.cut(reflected))+vol(reflected.cut(s));assert v<1e-5;mirrors[kind+'_'+n]=v
 dump(OUT/'assembly-manifest.json',dict(revision=REV,geometry_units='mm',parts=rows,preview_step=file.name,preview_STEP_sha256=sha(file),root_layout=p['form_preview'],scope='Form arrangement only. Roots/axis/mimic/transmission and collision-free closed state not designed.'))
 return dict(per_family=exportqa,four_petal_named_objects=28,mirror_double_reflection_symmetric_difference_mm3=mirrors)

def plot(families,p):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.backends.backend_pdf import PdfPages
 colors={'frame':'#597c87','retainer':'#243c47','bearing_cover':'#acd2d6','compliant_skin':'#efc874','PCB_blank_reservation':'#4b9278','back_electronics_reservation':'#9685b5','LED_front_reservation':'#e0a451'}
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
 def polys(ax,shape,axes=(0,1),offset=(0,0),face='#678',edge='none'):
  v,f=shape.tessellate(.12,.1);tri=np.array([x.toTuple() for x in v])[np.array(f)][:,:,axes]+offset;ax.add_collection(PolyCollection(tri,facecolors=face,edgecolors=edge,linewidths=.15,rasterized=True));ax.autoscale_view()
 def profile(ax,w,**kwargs):polys(ax,prism(w,0,.02),**kwargs)
 def dim(ax,a,b,label):ax.annotate('',b,a,arrowprops={'arrowstyle':'|-|','lw':.8,'color':'#324d59'});mid=(np.array(a)+b)/2;ax.text(*mid,label,ha='center',va='bottom',fontsize=9,bbox={'facecolor':'white','edgecolor':'none','alpha':.85})
 def footer(fig,page):fig.text(.045,.035,NOTICE+f' | CC BY-NC 4.0 | nominal form candidate | {page}/3',fontsize=8,color='#607783')
 with PdfPages(OUT/'R5-PETAL-FORM02-dimensions-and-sections.pdf') as pdf:
  fig=plt.figure(figsize=(11.7,8.3));ax=fig.add_axes([.06,.22,.88,.63]);fig.suptitle('R5 / shaped luminous gripping faces',x=.045,y=.965,ha='left',fontsize=20);fig.text(.045,.905,'Four-petal orthographic form study | all four at the same scale | no head or drive assembly',fontsize=10,color='#47636e')
  for f,q in p['form_preview'].items():
   parts,profiles,rep=families[q['kind']];theta=math.radians(q['angle_deg']);T=np.eye(4);T[:3,:3]=[[math.cos(theta),-math.sin(theta),0],[math.sin(theta),math.cos(theta),0],[0,0,1]];T[:2,3]=q['root_xy_mm']
   for name in ['frame','retainer','compliant_skin']:polys(ax,transform(mirrored(parts[name],q['hand']),T),face=colors[name])
   x,y=q['root_xy_mm'];ax.text(x,y+(-11 if y>0 else 8),f,ha='center',fontsize=9)
  ax.add_patch(plt.Circle((0,0),30,fill=False,ls='--',lw=.9,color='#94a4ab'));ax.text(0,0,'Layout datum\nonly',ha='center',va='center',fontsize=8,color='#81929a');ax.set_aspect('equal');ax.set_xlim(-185,185);ax.set_ylim(-185,185);ax.set_xlabel('Form-preview X [mm]');ax.set_ylabel('Form-preview Y [mm]');ax.grid(alpha=.15)
  fig.text(.06,.12,'Upper: long near-constant-width wing, stepped shoulder, chamfered flat tip. Lower: shorter shoulder and truncated tip.',fontsize=9)
  fig.text(.06,.085,'Gold area is the compliant illuminated contact face. Left-hand shapes are real mirror parts; conductive PCBs are not mirrored.',fontsize=9);footer(fig,1);pdf.savefig(fig);fig.savefig(OUT/'four-petal-orthographic.png',dpi=180);plt.close(fig)
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('Contour parameters / right-hand parts',x=.045,y=.965,ha='left',fontsize=19)
  for i,kind in enumerate(['upper','lower']):
   ax=fig.add_axes([.07,.56-i*.34,.79,.26]);parts,profiles,rep=families[kind]
   for n in ['frame','retainer','compliant_skin']:polys(ax,parts[n],face=colors[n])
   for x,y in rep['root_holes']:ax.add_patch(plt.Circle((x,y),p['root_hole_D_mm']/2,facecolor='white',edgecolor='#182f3b',lw=.4))
   for x,y in rep['retainer_holes']:ax.add_patch(plt.Circle((x,y),p['retainer_hole_D_mm']/2,facecolor='white',edgecolor='#182f3b',lw=.4))
   b=rep['overall_bbox_mm'];L=p[kind]['length_mm'];dim(ax,[0,29],[L,29],f'{L:g} mm overall');ax.axvline(35,ls='--',color='#8978ab',lw=.7);ax.text(35,34,'A',ha='center',color='#776398');ax.set_title(kind.upper(),loc='left',fontsize=11);ax.set_aspect('equal');ax.set_xlim(-5,158);ax.set_ylim(-35,38);ax.axis('off')
   fig.text(.87,.67-i*.34,f'Width {b[1,1]-b[0,1]:.1f}\nRoot 18.0\nStack 9.5\n4 x D3.2 root\n4 x D2.2 bezel\nD4.2 x90deg CSK',fontsize=9,linespacing=1.6)
  fig.text(.07,.14,'Nominal contour corner R0.8. Shoulder stations and all contour vertices are in parameters.json / profiles.dxf.\nRoot holes are candidate flat-interface bores, not a released hinge. Fasteners, fits and process radii require review.',fontsize=10,linespacing=1.5);footer(fig,2);pdf.savefig(fig);fig.savefig(OUT/'contour-dimensions.png',dpi=180);plt.close(fig)
  fig=plt.figure(figsize=(11.7,8.3));fig.suptitle('Luminous face load path / nominal sections',x=.045,y=.965,ha='left',fontsize=19)
  for i,kind in enumerate(['upper','lower']):
   ax=fig.add_axes([.08,.55-i*.32,.57,.24]);parts,profiles,rep=families[kind];x=35.
   for n,s in parts.items():polys(ax,s.intersect(box(x-.02,x+.02,-100,100,-1,12)),axes=(1,2),face=colors[n])
   ax.set_aspect('equal');ax.set_xlim(-34,31);ax.set_ylim(-1,13);ax.set_xlabel('Local Y [mm]');ax.set_ylabel('Local Z [mm]');ax.set_title(kind.upper()+' / A-A at x35 mm',fontsize=10);ax.grid(alpha=.15)
   ax.annotate('Contact load',(0,9.5),(0,12),ha='center',fontsize=8,arrowprops={'arrowstyle':'->','lw':1.2,'color':'#b86e21'})
  note=('Z stack [mm]\n9.5   compliant contact surface\n9.0   metal bezel front\n8.4   captured skin flange\n8.0   PC cover front\n5.5   cover support shelf\n5.2   LED envelope limit\n4.3   PCB top / 3.5 bottom\n1.75  back-component limit\n1.5   integral floor top\n0.0   frame back\n\nObject -> skin -> PC cover\n-> perimeter shelf -> frame\n-> candidate root attachment\n\nElectronics carry no intended\ngripping reaction. Clearances\nare nominal and undeformed.')
  fig.text(.71,.855,note,va='top',fontsize=10,linespacing=1.45)
  fig.text(.08,.12,'Transparent cover spans the cavity and seats on a perimeter ledge. Skin flange has zero nominal preload.\nRetention, friction, cover deflection, fatigue, optical uniformity and 1-second motion remain unqualified.',fontsize=10,linespacing=1.5);footer(fig,3);pdf.savefig(fig);fig.savefig(OUT/'load-path-sections.png',dpi=180);plt.close(fig)

FINGERS={'UR':('upper','right',45.),'UL':('upper','left',135.),'LL':('lower','left',225.),'LR':('lower','right',315.)}

def interface_checks(families,p):
 """Actual contour/ledge and nominal hardware gauges; not a real screw release."""
 allrows={}
 for kind,(parts,profiles,rep) in families.items():
  O=profiles['outer'];R=profiles['retainer_outer'];opening=profiles['retainer_opening']
  frame=parts['frame'];rows=[]
  for x,y in rep['root_holes']:
   vertex=cq.Vertex.makeVertex(float(x),float(y),0)
   edge=O.distance(vertex)-p['root_hole_D_mm']/2
   gauge=hole(x,y,3.,7.,8.3).cut(hole(x,y,1.6,6.9,8.4))
   contact=face_contact(frame,gauge,[0,0,7],[0,0,1])['shared_planar_face_area_mm2']
   expected=math.pi*(3**2-1.6**2);assert abs(contact-expected)<1e-5 and edge>0
   rows.append(dict(pattern='root',xy_mm=[x,y],hole_D_mm=3.2,minimum_outer_ligament_mm=edge,head_gauge_outer_D_mm=6.,head_gauge_contact_area_mm2=contact,complete_gauge_bearing_area=True,selected_assembled_fastener=False))
  for x,y in rep['retainer_holes']:
   vertex=cq.Vertex.makeVertex(float(x),float(y),0);outer=R.distance(vertex)-2.1;inner=opening.distance(vertex)-2.1
   washer=hole(x,y,2.5,-.3,0).cut(hole(x,y,1.1,-.4,.1))
   bearing=face_contact(frame,washer,[0,0,0],[0,0,1])['shared_planar_face_area_mm2'];expected=math.pi*(2.5**2-1.1**2)
   assert outer>0 and inner>0 and abs(bearing-expected)<1e-5,(kind,x,y,outer,inner,bearing)
   # At every cone section: the top-radius cylinder is a conservative gauge.
   z=p['z_mm'];cap=prism(R,z['retainer_back'],z['retainer_front']).cut(prism(inset(profiles['cover'],-p['cover_radial_clearance_mm']),6.9,z['skin_flange_top'])).cut(prism(opening,6.9,20))
   maxhead=hole(x,y,2.1,8.,9.);outside=vol(maxhead.cut(cap));assert outside<1e-5
   rows.append(dict(pattern='retainer',xy_mm=[x,y],hole_D_mm=2.2,countersink_D_mm=4.2,countersink_conservative_full_radius_cylinder_outside_cap_mm3=outside,countersink_to_outer_edge_mm=outer,countersink_to_front_opening_mm=inner,rear_washer_D_mm=5.,rear_washer_ID_mm=2.2,rear_washer_contact_area_mm2=bearing,complete_gauge_bearing_area=True,actual_screw_head_profile_verified=False))
  allrows[kind]=dict(rows=rows,holes_moved_from_FORM01=[],nominal_flange_height_mm=.4,nominal_retainer_slot_height_mm=.4,nominal_precompression_mm=0.,minimum_countersink_outer_ligament_mm=min(x['countersink_to_outer_edge_mm'] for x in rows if x['pattern']=='retainer'),hardware_status='Geometric bearing gauges only. Actual M2 head tolerance, head proudness, tail fastening, assembly access and preload are not qualified.')
 return allrows

def radial_T(phi,R,zroot=20.):
 t=math.radians(phi);er=np.array([math.cos(t),math.sin(t),0.]);et=np.array([-math.sin(t),math.cos(t),0.]);B=np.column_stack([[0,0,1.],et,-er]);T=np.eye(4);T[:3,:3]=B;T[:3,3]=R*er+[0,0,zroot]-B@np.array([0.,0.,3.5]);assert abs(np.linalg.det(B)-1)<1e-12
 return T,er

def radial_study(families,p):
 """Continuous affine-radius proof plus independently imported finite BREP checks."""
 from scipy.spatial import ConvexHull
 parts={};vertices={};containment=[];single_mirror=[]
 for fid,(kind,hand,phi) in FINGERS.items():
  xy=np.array(families[kind][2]['outer_knots_mm']);xy[:,1]*=(1 if hand=='right' else -1);hull=xy[ConvexHull(xy).vertices]
  env=cq.Workplane('XY').polyline(hull.tolist()).close().extrude(9.5).val();vertices[fid]=np.array([[x,y,z] for x,y in hull for z in [0.,9.5]])
  parts[fid]={}
  for n,s0 in families[kind][0].items():
   s=cq.importers.importStep(str(OUT/f'{kind}-{hand}/{n}.step')).val();v=vol(s.cut(env));assert v<1e-4
   parts[fid][n]=s;containment.append(dict(finger=fid,part=n,outside_convex_prism_mm3=v,source_step=f'{kind}-{hand}/{n}.step',source_sha256=sha(OUT/f'{kind}-{hand}/{n}.step')))
   if hand=='left':
    a=geometry_properties(s0);b=geometry_properties(s);M=np.diag([1.,-1.,1.]);ce=float(np.max(abs(b['com_m']-M@a['com_m'])));ie=float(np.max(abs(b['inertia_per_mass_m2']-M@a['inertia_per_mass_m2']@M.T)));assert ce<1e-8 and ie<1e-9
    single_mirror.append(dict(kind=kind,part=n,COM_reflection_error_m=ce,inertia_per_mass_reflection_error_m2=ie))
 proof=[]
 for a,b in itertools.combinations(FINGERS,2):
  Ta,ea=radial_T(FINGERS[a][2],0);Tb,eb=radial_T(FINGERS[b][2],0);va=vertices[a]@Ta[:3,:3].T+Ta[:3,3];vb=vertices[b]@Tb[:3,:3].T+Tb[:3,3];n=ea-eb;n/=np.linalg.norm(n)
  Amin=min(float(np.min(va@n))+r*float(n@ea) for r in [31.,66.]);Bmax=max(float(np.max(vb@n))+r*float(n@eb) for r in [31.,66.]);gap=Amin-Bmax;assert gap>0
  proof.append(dict(pair=[a,b],fixed_unit_normal=n,minimum_A_projection_mm=Amin,maximum_B_projection_mm=Bmax,gap_lower_bound_mm=gap,separating_plane_offset_mm=(Amin+Bmax)/2,R_A_coefficient=float(n@ea),R_B_coefficient=float(n@eb),covers_independent_R_A_R_B_mm=[31.,66.]))
 sample=[];statefiles=[]
 for radius in [31.,46.,66.]:
  actual={fid:{n:transform(s,radial_T(FINGERS[fid][2],radius)[0]) for n,s in ps.items()} for fid,ps in parts.items()};comp={f:cq.Compound.makeCompound(list(ps.values())) for f,ps in actual.items()};assembly=cq.Assembly(name=f'{REV}-q90-R{radius:g}')
  for a,b in itertools.combinations(FINGERS,2):
   d=comp[a].distance(comp[b]);assert d+1e-6>=next(x['gap_lower_bound_mm'] for x in proof if x['pair']==[a,b]);sample.append(dict(R_mm=radius,pair=[a,b],minimum_BREP_distance_mm=d,intersection_volume_mm3=0.,intersection_reason='Strictly positive exact BREP distance plus contained-prism separation.'))
  mrows=[]
  for fid,ps in actual.items():
   kind,hand,phi=FINGERS[fid];T,_=radial_T(phi,radius)
   for n,s in ps.items():
    assembly.add(s,name=f'{fid}_{n}');g=geometry_properties(s);rho=p['densities_kg_m3'].get(n);mass=None if rho is None else g['volume_mm3']*rho*1e-9
    mrows.append(dict(id=f'{fid}_{n}',finger=fid,kind=kind,hand=hand,source_geometry=f'{kind}-{hand}/{n}.step',transform_from_hand_local_mm=T,bbox_head_mm=bbox(s),assumed_density_kg_m3=rho,mass_kg=mass,COM_head_m=None if mass is None else g['com_m'],inertia_COM_head_axes_kg_m2=None if mass is None else mass*g['inertia_per_mass_m2']))
  agg=combine([dict(mass_kg=r['mass_kg'],COM_local_m=r['COM_head_m'],inertia_COM_local_axes_kg_m2=r['inertia_COM_head_axes_kg_m2']) for r in mrows if r['mass_kg'] is not None]);agg['COM_head_m']=agg.pop('COM_local_m');agg['inertia_COM_head_axes_kg_m2']=agg.pop('inertia_COM_local_axes_kg_m2')
  assert abs(agg['mass_kg']-2*sum(families[k][2]['known_material_subtotal']['mass_kg'] for k in families))<1e-10
  file=OUT/f'{REV}-radial-q90-R{radius:g}.step';assembly.save(str(file));assert len(named_step(file))==28;mf=file.with_suffix('.json');dump(mf,dict(revision=REV,geometry_units='mm',q_deg=90,root_Z_mm=20,R_mm=radius,phi_deg={f:x[2] for f,x in FINGERS.items()},parts=mrows,known_material_subtotal=agg,kinematics_scope='A geometric radial-stage pose only. No actuator, slider, bearing or fold-stage implementation.'))
  statefiles.append(dict(STEP=file.name,sha256=sha(file),manifest=mf.name,manifest_sha256=sha(mf),named_objects=28,known_material_subtotal=agg))
 # Both finite skins include the same front-face witness point. A complete R2
 # disc is separately reported; it is not a physical pressure/contact patch.
 witness=[]
 for fid,(kind,hand,phi) in FINGERS.items():
  probe=hole(65,0,2.,9.5,10.5);area=face_contact(parts[fid]['compliant_skin'],probe,[0,0,9.5],[0,0,1])['shared_planar_face_area_mm2'];assert abs(area-math.pi*4)<1e-5
  witness.append(dict(finger=fid,point_hand_local_mm=[65.,0.,9.5],nominal_planar_R2_disc_area_mm2=area,actual_contact_patch_area_mm2=None))
 objects=[]
 for kindobj in ['cylinder','square_prism']:
  for width in [50.,80.,120.]:
   a=width/2;radius=a+6;obj=cq.Solid.makeCylinder(a,60,cq.Vector(0,0,55)) if kindobj=='cylinder' else box(-a,a,-a,a,55,115).rotate((0,0,0),(0,0,1),45)
   for fid,(kind,hand,phi) in FINGERS.items():
    T,er=radial_T(phi,radius);pt=T[:3,:3]@np.array([65.,0.,9.5])+T[:3,3];assert np.max(abs(pt-(a*er+[0,0,85.])))<1e-10
    shapechecks=[]
    for n,s in parts[fid].items():
     so=transform(s,T);d=so.distance(obj);v=common(so,obj);assert v<1e-5
     if n=='compliant_skin':assert d<1e-6
     else:assert d>.499999
     row=dict(part=n,distance_mm=d,overlap_mm3=v)
     if n=='compliant_skin' and kindobj=='square_prism':
      ca=face_contact(so,obj,pt,er)['shared_planar_face_area_mm2'];assert ca>1;row['nominal_flat_face_geometric_overlap_area_mm2']=ca
     shapechecks.append(row)
    objects.append(dict(object=kindobj,width_mm=width,square_yaw_deg=45 if kindobj=='square_prism' else None,object_Z_mm=[55.,115.],R_mm=radius,finger=fid,contact_witness_head_mm=pt,parts=shapechecks))
 # Support result is independent of width; evaluate symbolic affine mapping at
 # three widths separately from BREP. For yaw45 square, every er is a side normal.
 support=[];g=math.pi/4;Q=np.array([[math.cos(g),-math.sin(g)],[math.sin(g),math.cos(g)]])
 for width in [50.,80.,120.]:
  a=width/2;corners=np.array([Q@np.array([x,y]) for x in [-a,a] for y in [-a,a]])
  for fid,(_,_,phi) in FINGERS.items():
   _,er=radial_T(phi,0);rho=float(np.max(corners@er[:2]));assert abs(rho-a)<1e-10
   support.append(dict(width_mm=width,finger=fid,square_support_radius_mm=rho,cylinder_support_radius_mm=a,analytic_root_radius_mm=a+6))
 return dict(revision=REV,scope='Only q90, root Z20, nominal bare 28 petal solids. Independent radial coordinates R_i31..66; finite centered objects Z55..115; square yaw45. No fold, object insertion, cameras, mechanism, grip force or speed qualification.',containment=containment,single_mirror_mass_geometry_checks=single_mirror,continuous_radius_certificate=dict(method='For each pair fix unit n=(erA-erB)/norm, bound all convex-prism vertices and both independent R interval endpoints. Positive projection gap proves Euclidean separation for all contained solids.',pairs=proof,minimum_gap_lower_bound_mm=min(r['gap_lower_bound_mm'] for r in proof)),sampled_BREP_distances=sample,radial_assemblies=statefiles,finite_skin_witnesses=witness,finite_object_checks=objects,finite_object_body_query_count=len(objects)*7,independent_support_checks=support,continuous_width_contact_argument='At q90 every part lies behind front plane er dot X = R-6. For any centered cylinder diameter or aligned square width W in [50,120], choose R=W/2+6. Local [65,0,9.5] on each finite skin maps to W/2*er+[0,0,85], within object Z55..115. Before contact R>W/2+6 all petal solids are outside the object support half-space; at contact no positive overlap. This proves a nominal geometric touch, not deformation, friction, force closure or holding.',object_loading_clearance_at_width120_at_R66_mm=0.,manufacturing_release=False)

def plot_radial(radial,families):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.collections import PolyCollection
 from matplotlib.patches import Circle,Polygon
 fig,axs=plt.subplots(1,3,figsize=(14,6.4));fig.subplots_adjust(top=.80,bottom=.27,left=.055,right=.99,wspace=.27)
 for ax,R in zip(axs,[31.,46.,66.]):
  for fid,(kind,hand,phi) in FINGERS.items():
   T,_=radial_T(phi,R)
   for n in ['frame','retainer','compliant_skin']:
    so=transform(mirrored(families[kind][0][n],hand),T);v,f=so.tessellate(.15,.12);tri=np.array([x.toTuple() for x in v])[np.array(f)][:,:,:2];ax.add_collection(PolyCollection(tri,facecolors={'frame':'#668491','retainer':'#263d49','compliant_skin':'#edc46d'}[n],edgecolors='none',rasterized=True))
   _,er=radial_T(phi,R);ax.text(*((R+12)*er[:2]),fid,ha='center',va='center',fontsize=8)
  a=R-6;Q=np.array([[math.cos(math.pi/4),-math.sin(math.pi/4)],[math.sin(math.pi/4),math.cos(math.pi/4)]]);corners=np.array([Q@np.array([x,y]) for x,y in [(-a,-a),(a,-a),(a,a),(-a,a)]])
  ax.add_patch(Circle((0,0),a,fill=False,ec='#b74943',ls='--',lw=1.));ax.add_patch(Polygon(corners,fill=False,ec='#b74943',lw=.9));ax.set(aspect='equal',xlim=(-110,110),ylim=(-110,110),xlabel='Head X [mm]',ylabel='Head Y [mm]',title=f'R {R:g} / object width {2*a:g} mm');ax.grid(alpha=.15)
 fig.suptitle('FORM02 / real-layer radial contact candidate',x=.055,y=.96,ha='left',fontsize=19);fig.text(.055,.865,'All panels use the same scale. q = 90 deg; roots Z = 20 mm. Cylinders and yaw45 square prisms: Z55...115 mm.',fontsize=10)
 fig.text(.055,.095,'All 28 solids inside rebuilt convex prisms; continuous independent-radius separation >= 2.828 mm.\nNominal finite-skin contact only. Square and cylinder outlines are overlaid alternatives, not simultaneous objects.',fontsize=10);fig.text(.055,.025,NOTICE+' | CC BY-NC 4.0 | no drive / force / speed qualification',fontsize=8,color='#596f7b');fig.savefig(OUT/'radial-contact-orthographic.png',dpi=180);fig.savefig(OUT/'radial-contact-orthographic.pdf');plt.close(fig)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--parameters',type=Path);args=ap.parse_args();p=json.loads(args.parameters.read_text()) if args.parameters else copy.deepcopy(DEFAULT);OUT.mkdir(parents=True,exist_ok=True)
 families={kind:build(kind,p) for kind in ['upper','lower']};dump(OUT/'parameters.json',p);interfaces=interface_checks(families,p);dump(OUT/'interface-checks.json',interfaces);print('layer and hardware-gauge checks complete',flush=True)
 qa=export_sets(families,p);print('28 part exports / mirror / STL / DXF complete',flush=True);radial=radial_study(families,p);dump(OUT/'radial-study.json',radial);plot(families,p);plot_radial(radial,families)
 with (OUT/'parts-ledger.csv').open('w',newline='') as f:
  cols=['kind','hand','part','quantity','source_geometry','volume_mm3','assumed_density_kg_m3','mass_kg','mass_status'];writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
  for group in qa['per_family']:
   for r in group['parts']:
    writer.writerow(dict(kind=r['kind'],hand=r['hand'],part=r['id'],quantity=1,source_geometry=r['file'],volume_mm3=geometry_properties(cq.importers.importStep(str(OUT/r['file'])).val())['volume_mm3'],assumed_density_kg_m3=r['assumed_density_kg_m3'],mass_kg=r['mass_kg'],mass_status='Nominal material-density assumption' if r['mass_kg'] is not None else 'Unknown electronic reservation; excluded'))
 with (OUT/'hole-coordinates.csv').open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['kind','hand','pattern','index','x_mm','y_mm','hole_D_mm','CSK_D_mm','CSK_angle_deg','CSK_depth_mm']);writer.writeheader()
  for kind,(_,_,rep) in families.items():
   for hand in ['right','left']:
    for pat,D in [('root_holes',3.2),('retainer_holes',2.2)]:
     for i,(x,y) in enumerate(rep[pat],1):writer.writerow(dict(kind=kind,hand=hand,pattern=pat,index=i,x_mm=x,y_mm=y if hand=='right' else -y,hole_D_mm=D,CSK_D_mm=4.2 if pat=='retainer_holes' else '',CSK_angle_deg=90 if pat=='retainer_holes' else '',CSK_depth_mm=1 if pat=='retainer_holes' else ''))
 sourcefiles=[Path(__file__),ROOT/'engineering/r5_petal_form01.py',ROOT/'engineering/generated/r5-petal-form01/study.json',ROOT/'docs/engineering/hardware/r5-petal-hardware01.md',ROOT/'docs/engineering/sources/r5-petal-hardware01.json',ROOT/'engineering/head_mass04_study.py',ROOT/'engineering/build_layout.py',ROOT/'engineering/build_link56_study.py',ROOT/'engineering/screen_integrated_collisions.py'];hashes={str(f.relative_to(ROOT)):sha(f) for f in sourcefiles}
 old=json.loads((ROOT/'engineering/generated/r5-petal-form01/study.json').read_text());subtotal=2*sum(r['known_material_subtotal']['mass_kg'] for _,_,r in families.values())
 comparison={k:dict(new_mass_kg=r['known_material_subtotal']['mass_kg'],FORM01_mass_kg=old['parts'][k]['known_material_subtotal']['mass_kg'],mass_change_kg=r['known_material_subtotal']['mass_kg']-old['parts'][k]['known_material_subtotal']['mass_kg'],old_outline_knots_mm=old['parts'][k]['outer_knots_mm'],new_outline_knots_mm=r['outer_knots_mm'],hole_displacements_mm=[[0.,0.] for _ in r['retainer_holes']]) for k,(_,_,r) in families.items()}
 study=dict(revision=REV,license='CC-BY-NC-4.0',required_notice=NOTICE,source_hashes=hashes,parameters_sha256=sha(OUT/'parameters.json'),parts={kind:r for kind,(_,_,r) in families.items()},comparison_to_FORM01=comparison,four_petal_known_material_subtotal_kg=subtotal,four_petal_mass_change_from_FORM01_kg=subtotal-old['four_petal_known_material_subtotal_kg'],excluded_mass='LEDs/PCB/copper/solder/connectors/wires/fasteners/hinges/transmission/actuator are unknown and excluded, not physical zero.',radial_study_sha256=sha(OUT/'radial-study.json'),hardware_interface_checks_sha256=sha(OUT/'interface-checks.json'),nominal_radial_bare_petal_geometry_qualified=True,fold_stage_qualified=False,single_motor_mechanism_qualified=False,one_second_cycle_qualified=False,grip_force_qualified=False,manufacturing_release=False,reference_interpretation='Independent shoulder-cut candidate. Upper two y=-29 knots become -23; lower two y=25 knots become23, all other shape knots/lengths retained. Rebuilt offsets, pockets and solid layers, not clipped STL. Four orthogonal azimuths45/135/225/315 are specific to this radial contact study.',unresolved=['Zero nominal flange preload: .4mm flange in .4mm slot.','Real M2 countersunk head profile / tolerance and top<=Z9 not verified.','PC cover bending versus .3mm nominal LED gap not verified.','Material/skin wear, friction, peel and retention not released.','New left/right PCB outlines and routing required; FORM01/FPL electronics not inherited.','Bare petals exclude roots/hinges/radial guides/links/head camera/display/wiring.'])
 dump(OUT/'study.json',study);dump(OUT/'qa.json',dict(revision=REV,export_checks=qa,unit_checks=unit_checks(),all_nominal_layer_pairs_no_positive_intersection=True,all_four_contact_interfaces_positive_area=True,radial_containment_count=len(radial['containment']),minimum_continuous_radius_gap_mm=radial['continuous_radius_certificate']['minimum_gap_lower_bound_mm'],source_hashes=hashes,manufacturing_release=False));print('READY_GEOMETRY',[(k,r['known_material_subtotal']['mass_kg']) for k,(_,_,r) in families.items()],flush=True)
if __name__=='__main__':main()
