# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Render the conditional ray screen; run after engineering/r5_vision01.py."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'sightline-screen.json').read_text())
fig,axs=plt.subplots(2,3,figsize=(13,9),sharex=True,sharey=True)
for row,state in enumerate(['open','minimum50']):
 for col,pupil in enumerate([0,7,14]):
  case=next(x for x in data['cases'] if x['state']==state and x['pupil_native_z_mm']==pupil)
  upper=[r for r in case['cameras'][0]['rays'] if r['target_mm'][2]==65]
  lower=[r for r in case['cameras'][1]['rays'] if r['target_mm'][2]==65]
  summary=next(x for x in case['summary'] if x['target_z_mm']==65)
  ax=axs[row,col]
  for a,b in zip(upper,lower):
   both=a['clear'] and b['clear'];one=a['clear'] or b['clear']
   ax.scatter(*a['target_mm'][:2],c='#217b76' if both else '#d29937' if one else '#aa504b',marker='o' if one else 'x',s=65)
  ax.set_title(f'{state} / pupil native Z={pupil} mm\neither {summary["either_clear"]}/25; both {summary["both_clear"]}/25',fontsize=11)
  ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlim(-26,26);ax.set_ylim(-26,26)
  if row==1:ax.set_xlabel('Target head X [mm]')
  if col==0:ax.set_ylabel('Target head Y [mm]')
fig.suptitle('Conditional rays to an empty 40 x 40 mm target patch at head Z65',fontsize=16)
handles=[Line2D([],[],marker='o',ls='',color='#217b76',label='clear from both'),Line2D([],[],marker='o',ls='',color='#d29937',label='clear from one'),Line2D([],[],marker='x',ls='',color='#aa504b',label='blocked from both')]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.105),ncol=3,frameon=False)
fig.text(.05,.08,'Cameras at mount origins (0, +/-50, -35) mm, outward 8 deg. Unknown entrance pupil: Z0/7/14 are sensitivity assumptions, not physical bounds.',fontsize=9)
fig.text(.05,.052,'No opaque workpiece or calibrated fisheye projection. Nominal solid windows/covers treated opaque. This is not image coverage or grasp success rate.',fontsize=9)
fig.text(.05,.024,'R5-VISION01 / Auromix / CC BY-NC 4.0 / candidate geometry only',fontsize=9,color='#657179')
fig.subplots_adjust(left=.07,right=.98,bottom=.21,top=.9,hspace=.30,wspace=.12)
fig.savefig(ROOT/'sightline-summary.png',dpi=165);fig.savefig(ROOT/'sightline-summary.svg',metadata={'Date':None});plt.close(fig)
