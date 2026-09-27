#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Orthographic audit views from actual exported part meshes, no design redraw."""
import json
from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
OUT=Path(__file__).resolve().parent/'generated/head-integrated-03'

def view(ax,label):
 manifest=json.loads((OUT/('blender-parts-manifest'+('' if label=='open' else '-'+label)+'.json')).read_text());desc={p['id']:p for p in manifest['parts']};scene=trimesh.load(OUT/f'HEAD-INTEGRATED03-{label}.glb',force='scene')
 eye=np.array([.45,.3,1.]);eye/=np.linalg.norm(eye);right=np.cross([0,1,0],eye);right/=np.linalg.norm(right);up=np.cross(eye,right);rot=np.array([right,up,eye]);tri=[];col=[];depth=[]
 for name,m in scene.geometry.items():
  d=desc[name]
  # Connector unplug volumes and other empty keepouts are not opaque material.
  if d['material']=='space_reservation':continue
  p=(m.vertices*1000)@rot.T;faces=m.faces;normal=m.face_normals@eye;faces=faces[normal>1e-8];normal=normal[normal>1e-8]
  rgb=np.array(m.visual.material.baseColorFactor[:3])/255.;shade=.5+.5*normal
  if 'optical_sheet' in name:continue # remove clear cover in audit view to expose real LED locations
  tri.append(p[faces][:,:,:2]);depth.append(p[faces][:,:,2].mean(axis=1));col.append(np.column_stack([shade[:,None]*rgb,np.ones(len(faces))]))
 tri=np.concatenate(tri);depth=np.concatenate(depth);col=np.concatenate(col);order=np.argsort(depth)
 ax.add_collection(PolyCollection(tri[order],facecolors=col[order],edgecolors='none',antialiased=False));ax.set_aspect('equal');ax.set_xlim(-200,220);ax.set_ylim(-195,190);ax.axis('off');ax.set_title(('OPEN / q = 0, 0, 0, 0' if label=='open' else 'CLOSED / q = 109, 109, 122, 122 deg'),loc='left',fontweight='bold',fontsize=13,color='#253743')
 for v,txt,c in [([30,0,0],'X','#9d4142'),([0,30,0],'Y','#3c8464'),([0,0,30],'Z','#416eac')]:
  a=np.array(v)@rot.T;ax.annotate('',xy=(-160+a[0],-165+a[1]),xytext=(-160,-165),arrowprops=dict(arrowstyle='->',color=c,lw=1.5));ax.text(-160+a[0],-165+a[1],txt,color=c,fontsize=9)
fig,axs=plt.subplots(1,2,figsize=(13,6.4));fig.patch.set_facecolor('#f5f4f0')
for a,l in zip(axs,['open','closed']):a.set_facecolor('#f5f4f0');view(a,l)
fig.suptitle('ODRADEK / HEAD-INTEGRATED03',x=.055,y=.975,ha='left',fontsize=19,fontweight='bold',color='#253743');fig.text(.055,.025,'Actual CAD mesh audit views | optical covers and empty reservations hidden for visibility\nCamera / P16 / electronic packages are explicit envelopes; not manufacturing release.',fontsize=10,color='#54636c');fig.tight_layout(rect=[.02,.07,.98,.93]);fig.savefig(OUT/'HEAD-INTEGRATED03-audit-views.png',dpi=180);print(OUT/'HEAD-INTEGRATED03-audit-views.png')
