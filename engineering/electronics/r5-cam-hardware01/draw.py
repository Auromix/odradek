#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).resolve().parent
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none','svg.hashsalt':'R5-CAM-HARDWARE01-interface'})
f,axs=plt.subplots(1,2,figsize=(14,7),gridspec_kw={'width_ratios':[1.45,1]})
a,b=axs;a.set_aspect('equal');a.set_xlim(-10,11);a.set_ylim(-9,10);a.axis('off')
def box(x,y,w,h,c,label=None):
 a.add_patch(Rectangle((x,y),w,h,facecolor=c,edgecolor='#263b50',lw=1.2))
 if label:a.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=9)
def dim(x1,x2,y,txt):
 a.annotate('',(x1,y),(x2,y),arrowprops=dict(arrowstyle='<->',color='#24374a'))
 a.text((x1+x2)/2,y+.25,txt,ha='center',fontsize=10,color='#24374a')
box(0,-5,4,10,'#dfe7ec');a.text(2,5.3,'4 mm rocker seat candidate',ha='center',fontsize=10)
box(-5.5,4,4,1.2,'#f4ce8a');box(-5.5,-5.2,4,1.2,'#f4ce8a');a.text(-5.5,-5.7,'4 mm track width; not strength release',fontsize=9,ha='center')
box(-7,-3.85,7,7.7,'#9bb1c3');box(-6,-4,5,8,'#4c8da9');a.text(-3.5,0,'outer\nring',ha='center',va='center',color='white',fontsize=10)
box(0,-2,8,4,'#8e9eac');box(4,-3.5,3.2,7,'#c09d72','nut')
for x in [4.2,4.9,5.6,6.3,7,7.7]:a.plot([x-.15,x+.15],[-2,2],color='#4d5c69',lw=.8)
a.axhline(0,color='#5c7285',lw=.8,ls='-.');a.plot([0,0],[-8,8],color='#c5433e',lw=1,ls='--')
a.text(0,8.5,'u = 0 : fixed shoulder / mounting face',color='#b53632',ha='center',fontsize=11)
a.annotate('+u to stud tip',xy=(9,7.5),xytext=(2,7.5),arrowprops=dict(arrowstyle='->'),fontsize=10,va='center')
dim(-7,8,-7.7,'B1 = 15 overall');dim(-6,-1,6.6,'C = 5');dim(0,8,-6.5,'B2 = 8');dim(4,8,6.6,'G1 = 4')
a.text(-8.3,0,'D = 8',rotation=90,va='center',fontsize=10)
a.text(8.4,-1,'M4 x 0.7\nstud 4 h6',fontsize=9)
a.set_title('Original axial interface sketch / nominal mm',fontsize=13,pad=16)
b.axis('off');b.set_title('Scope and assembly datums',fontsize=13,pad=16)
notes=[
('CFS4 catalogue','Ring u = -6 ... -1; center = -3.5\nFront assembly u = -7 ... 0\nPlain stud u = 0 ... 4; thread = 4 ... 8'),
('Mounting candidate','Seat bore 4 H6; supported seat diameter >= 7.7\nNut: 3.2 thick, AF7, corners ~8.1\nMax nut torque 0.777 Nm is a LIMIT, not a target\nHold head hex; turn nut; locking method TBD'),
('Root-bearing candidate','2 x SKF 607/8-2Z, 8 x 19 x 6\nShaft shoulder diameter 10 ... 11\nHousing shoulder opening <= 17; fillet <= 0.3\nSeparate coaxial trunnions; no throughshaft'),
('Carrier packaging example','Bearings: y = +/-16, span 32\nFollower center y = 32; shoulder y = 28.5\nStud tip y = 20.5; end-cap limit y = 20\n0.5 nominal axial gap; NOT tolerance clearance'),
('Not released','Rocker / shaft / pin / end-cap strength, fits, tools,\nanti-loosening, lubrication and four-module collisions.\nCatalogue facts are NOT a vendor solid model.')]
y=.97
for title,txt in notes:
 b.text(0,y,title,weight='bold',fontsize=11,va='top',color='#25445c');b.text(0,y-.045,txt,fontsize=10,va='top',linespacing=1.35);y-=.20
f.suptitle('R5-CAM-HARDWARE01 | CFS4 + split root support / engineering candidate',fontsize=15,y=.99)
f.text(.02,.015,'Source dimensions: IKO official CFS catalogue; SKF Rolling bearings pp.262-263. Original drawing, CC-BY-NC-4.0.',fontsize=9,color='#555')
f.tight_layout(rect=[0,.045,1,.96]);f.savefig(P/'follower-interface.svg',metadata={'Date':None});f.savefig(P/'follower-interface.png',dpi=160);plt.close(f)
