# SPDX-License-Identifier: CC-BY-NC-4.0
"""Review drawing from reopened EDA primitives; not Gerber or fabrication drawing."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
ROOT=Path(__file__).resolve().parent
d=json.loads((ROOT/'reports/b06-power-reopened.json').read_text())['value']
colors={'VIN48':'#cc6b35','RETURN48':'#437693','CHASSIS':'#6d8465'}
fig,ax=plt.subplots(figsize=(12,7.2))
fig.subplots_adjust(left=.07,right=.98,bottom=.15,top=.85)
fig.patch.set_facecolor('#f6f5f1');ax.set_facecolor('#f6f5f1')
ax.add_patch(Rectangle((0,0),116,56,facecolor='#e5e9df',edgecolor='#243239',lw=1.3))
for l in d['lines']:
    if l['layer']!=1:continue
    ax.plot([l['startX']*.0254,l['endX']*.0254],[-l['startY']*.0254,-l['endY']*.0254],
            color=colors[l['net']],lw=l['lineWidth']*.0254*5.5,solid_capstyle='round')
for p in d['pads']:
    x,y=p['x']*.0254,-p['y']*.0254
    # Ellipse pad diameters in this board are round; shield slots shown as outer bounds.
    color=colors.get(p['net'],'#929ca2') if p['net'] else '#f6f5f1'
    ax.add_patch(Circle((x,y),max(p['pad'][1:])*.0254/2,fc=color,ec='#455057',lw=.6))
    ax.add_patch(Circle((x,y),p['hole'][1]*.0254/2,fc='#f6f5f1',ec='#455057',lw=.45))
for i in range(1,9):
    a,b=[p for p in d['pads'] if p['net']==f'ETH_{i}']
    ax.plot([a['x']*.0254,b['x']*.0254],[-a['y']*.0254,-b['y']*.0254],lw=.55,ls='--',color='#adb3b5',zorder=1.1)
for text,x,y in [('J1 / rear DATA',20,54),('J2 / internal DATA',58,2),('J3 / rear 48V',96.5,54),
                 ('J4 / VIN48',101,5),('J5 / RETURN48',85,5),('J6 / CHASSIS',42,26)]:
    ax.text(x,y,text,ha='center',fontsize=8,color='#25323b')
ax.set_xlim(-2,118);ax.set_ylim(58,-2);ax.set_aspect('equal')
ax.set_xlabel('native PCB u / mm');ax.set_ylabel('native PCB v / mm')
ax.spines[['top','right']].set_visible(False)
fig.suptitle('B06 rear interface | Native power-routing review',fontsize=16,color='#25323b')
ax.set_title('Top shown; bottom power copper matches. 2.4 mm per layer. Data dashed = UNROUTED. Inner pours omitted.',fontsize=9,pad=14)
fig.text(.5,.035,'Saved + reopened: 34 power segments / 14 pads connected / 16 remaining DATA DRC errors / NOT FOR FABRICATION',ha='center',fontsize=9,color='#714b34')
fig.text(.5,.01,'Review illustration: round/slot pad outlines simplified. Use the native EDA project for full geometry.',ha='center',fontsize=8,color='#667377')
fig.savefig(ROOT/'reports/b06-power-review.png',dpi=150)
fig.savefig(ROOT/'reports/b06-power-review.svg')
