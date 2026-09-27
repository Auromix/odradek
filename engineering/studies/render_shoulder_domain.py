# SPDX-License-Identifier: CC-BY-NC-4.0
# Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek)
"""Plot recorded exact samples and rigorous interval bounds; no interpolation proof."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties,fontManager

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('output',type=Path);ap.add_argument('--font',type=Path);a=ap.parse_args();d=json.loads(a.input.read_text());c=d['continuous'];font=FontProperties(fname=str(a.font)) if a.font else None
 if a.font:
  fontManager.addfont(str(a.font));plt.rcParams['font.family']=font.get_name()
 plt.rcParams.update({'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'font.size':11})
 fig,ax=plt.subplots(figsize=(11,6));fig.patch.set_facecolor('#f6f7f3');ax.set_facecolor('#f6f7f3')
 q=sorted(c['distance_samples'],key=lambda x:x['q2_deg']);ax.scatter([x['q2_deg'] for x in q],[x['minimum_distance_mm'] for x in q],s=9,color='#273d48',label='真实 BREP 距离采样',zorder=4)
 ax.axvspan(-25,25,color='#58b39d',alpha=.10)
 for i,cert in enumerate(c['certificates'][:2]):
  xx=[];yy=[]
  for leaf in cert['leaves']:xx.extend(leaf['interval_deg']);yy.extend([leaf['continuous_distance_lower_bound_mm']]*2)
  ax.plot(xx,yy,lw=1.4,color=['#157968','#c47d18'][i],label=f"全区间下界：{cert['interval_deg']}°")
 for sign,ends in [(-1,c['first_obstruction_from_zero_magnitude_brackets_deg']['negative']),(1,c['first_obstruction_from_zero_magnitude_brackets_deg']['positive'])]:
  lo,hi=sorted([sign*x for x in ends]);ax.axvspan(lo,hi,color='#be4b39',alpha=.6,label='首次阻塞位置带' if sign==-1 else None)
 ax.axhline(1,color='#157968',lw=.7,ls='--');ax.axhline(2,color='#c47d18',lw=.7,ls='--')
 ax.set_xlim(-31,31);ax.set_ylim(-.15,max(x['minimum_distance_mm'] for x in q)+.7)
 ax.set_xlabel('q2 / °');ax.set_ylabel('名义最小间隙 / mm');ax.grid(axis='y',color='#d7dcda',lw=.5);fig.legend(loc='lower center',bbox_to_anchor=(.5,.095),ncol=2,frameon=False,fontsize=9)
 fig.suptitle('J2 肩部局部连续间隙研究',x=.08,ha='left',fontsize=21,color='#203c49');fig.text(.08,.89,'黑点是精确距离采样；彩色折阶是覆盖完整角度区间的保守下界。',fontsize=11,color='#48616b')
 fig.text(.08,.05,'q1=0；仅 L23/J3 对 J1/BASE/L12。紧固件、后续连杆、线束与负载变形未纳入。',fontsize=10,color='#48616b');fig.text(.08,.018,'这是派生几何研究域，未修改原参数，不是可执行控制限位或制造放行。',fontsize=10,color='#8b4939')
 fig.subplots_adjust(left=.09,right=.97,top=.84,bottom=.24);a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=180);plt.close(fig)
if __name__=='__main__':main()
