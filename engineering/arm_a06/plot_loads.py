"""Plot conditional A06 gravity loads, not a certified payload map. CC-BY-NC-4.0."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT=Path(__file__).resolve().parents[2]
data=json.loads((ROOT/'docs/engineering/analysis/arm-a06-gravity.json').read_text())
font_path=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
font=FontProperties(fname=str(font_path)) if font_path.exists() else FontProperties()
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'path'})
fig,axes=plt.subplots(1,3,figsize=(12,4.5),layout='constrained')
spec=[('J2 肩部',1,40),('J4 肘部',3,20),('J5 腕部俯仰',4,11)]
colors=['#568898','#24596b','#be782f']
for ax,(name,i,rated) in zip(axes,spec):
 for head,color in zip([.8,1.2,1.5],colors):
  rows=[s for s in data['sensitivity'] if s['scenario']['head_kg']==head and s['scenario']['structure_scale']==1]
  x=[s['scenario']['payload_kg'] for s in rows]
  y=[s['reference']['axes'][i]['abs_holding_torque_Nm'] for s in rows]
  ax.plot(x,y,'o-',color=color,lw=1.8,ms=4,label=f'头部 {head:g} kg')
 ax.axhline(rated,color='#777777',ls='--',lw=1,label=f'目录额定 {rated} N·m')
 ax.set(xlim=(-.05,2.08),ylim=(0,rated*1.12),xticks=[0,.5,1,2])
 ax.set_title(name,fontproperties=font,pad=10)
 ax.set_xlabel('工件净重 / kg',fontproperties=font)
 ax.set_ylabel('静态保持转矩 / N·m',fontproperties=font)
 ax.grid(axis='y',color='#e5e7e9',lw=.7)
 ax.legend(prop=font,loc='lower right',frameon=False,fontsize=9)
fig.suptitle('同一套 A05 关节：头部与工件质量对静态保持的影响',fontproperties=font,fontsize=15)
fig.supxlabel('水平参考姿态；结构预算 1.40 kg。虚线仅为目录工况对照，不是封闭外壳的持续堵转能力。',fontproperties=font,fontsize=10)
out=ROOT/'docs/engineering/analysis/arm-a06-load-sensitivity'
fig.savefig(str(out)+'.png',dpi=160)
fig.savefig(str(out)+'.svg')
svg=Path(str(out)+'.svg')
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
print(str(out)+'.png')
