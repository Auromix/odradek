# SPDX-License-Identifier: CC-BY-NC-4.0
"""Publish model-backed tables and a self-contained printable fit kit."""
from pathlib import Path
import json,hashlib,collections,zipfile
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'engineering/arm_a08/build'
d=json.loads((OUT/'manifest.json').read_text());a=json.loads((ROOT/'docs/engineering/analysis/arm-a07-loads.json').read_text());v=json.loads((OUT/'verification.json').read_text())
assert a['target']['flange_frame']['translation_mm']==d['flange_from_J7_mm']
sha=hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()
assert a['source_manifest_sha256']==v['manifest_sha256']==sha
assert all(not r['conflicts'] for r in v['poses'].values())
audit=json.loads((OUT/'blender-audit.json').read_text());assert audit['manifest_sha256']==sha
counts=collections.Counter(p['role'] for p in d['parts']);mass=collections.defaultdict(float)
for p in d['parts']:mass[p['role']]+=p['mass_kg']
rows=[];ratings=[20,40,20,20,11,11,5]
for i in range(6,-1,-1):
 j=d['layout']['joints'][i];r=a['presets']['reference']['axes'][i];peak=a['sampled_gravity_maxima'][i];dyn=a['dynamic_screening']['reference']['additional_torque_bound_Nm'][i]
 rows.append(f"| {j['id']} | {j['model']} | {r['abs_holding_Nm']:.2f} | {r['bending_Nm']:.2f} | {peak['abs_holding_Nm']:.2f} | {dyn:.2f} | {ratings[i]} |")
ref=a['presets']['reference'];b=a['j7_bearing_radial_screen']
text='''<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# A07 裸臂3 kg：从J7回算至J1

本轮确认目标为**输出法兰总外负载3 kg**，暂不安装四瓣头；不能再另加历史头重或将3 kg解释为净工件。当前结果用于筛选和打印装配验证，不构成3 kg额定能力。

同一A08几何与质量台账驱动计算和Blender。轴序Z/Y/X/Y/Y/Z/X，J2竖直零位。参考伸展角为[0,90,0,0,0,0,0]。当前肩到裸法兰轴向尺寸为615.7 mm，侧偏90 mm；历史700 mm包含可拆末端任务TCP，本轮没有擅自扩展裸臂。

## 逐轴结果

单位N·m，外负载重心暂放在法兰中心。静态保持为沿关节轴投影，弯矩为垂直轴的分量，二者不可混为电机驱动转矩。

| 轴 | 条件候选 | 伸展保持 | 伸展弯矩 | 抽样最大保持 | 伸展动态附加筛查 | 目录额定转矩 |
|---|---|---:|---:|---:|---:|---:|
'''+ '\n'.join(rows)+f'''

总建模质量（含3 kg外负载）约{ref['total_mass_kg']:.3f} kg；不含底座、线束、连接器、衬垫及未来金属嵌件。打印结构采用实心体积与材料密度，实际切片、制造误差会改变质量与惯量。所有电机本体质量只计一次。

目录转矩具有明确散热条件：RS03为215×220 mm散热板；RS04的40 N·m需要345×345 mm，35 N·m采用220×200 mm；RS06为130×160 mm；RS00为90×85 mm。当前打印半壳没有复现这些条件。RS03的过载曲线脚注与额定行文字还存在不一致，供应商需解释。

**J2为当前主要约束。**不能把目录40 N·m直接解释成紧凑封闭肩部的持续保持能力。J3/J4还需要动态工况和热余量；J5/J6必须核对输出支承。J7在重心位于轴线上时静态roll重力矩近零，仍承受约{ref['axes'][6]['bending_Nm']:.2f} N·m弯矩；这不是“腕部无载荷”。当前候选不能冻结为已验证3 kg选型。

## 计算关系与交叉验证

坐标链：Tᵢ=Tᵢ₋₁·Trans(offsetᵢ)·Rot(axisᵢ,qᵢ+zeroᵢ)。质量台账中的固定壳体归属上游刚体，输出法兰与输出螺钉归属下游刚体。

从J7至J1递推：Fᵢ=Fᵢ₊₁+Σmₖg；Mᵢ=Mᵢ₊₁+(pᵢ₊₁−pᵢ)×Fᵢ₊₁+Σ(cₖ−pᵢ)×mₖg。驱动保持τᵢ=−aᵢ·Mᵢ，弯矩=‖Mᵢ−aᵢ(aᵢ·Mᵢ)‖。程序逐次与全部下游质量的直接求和比对，再通过重力势能对关节角的差分核对符号和数值。

最大虚功误差为{a['verification']['max_virtual_work_error_Nm']:.3g} N·m。1024个Halton角域样点及三个姿态只用于需求筛查，没有过滤碰撞，不能称为全局最大或可用工作空间边界。

动态筛查按每轴25°/s、30°/s²的暂定工程工况，用H(q)=Σ[mJᵥᵀJᵥ+JωᵀRIᶜRᵀJω]+反射惯量项，并由H的角度差分构造Christoffel项；附加需求上界为Σ|Hᵢⱼ|αmax+Σ|Γᵢⱼₖ|ωmax²。打印件采用均匀实体惯量；电机惯量用包络及整机质量作保守筛查，真实转子质量、惯量和内部质量分配未获证实；外负载惯量暂按以质心为圆心50 mm球内3 kg质量的上界。该表不是完整运行保证，未包含摩擦、线缆、接触、制动和热限制，也不是全部角域动态最大值。

## J7独立支承

采用两只NSK6807（35×47×7 mm）简化包络，额定基本静载C0r=4100 N。轴承中心距11 mm；法兰面在J7坐标x=65.7 mm。仅3 kg外负载、重心在法兰面时的孤立径向静力模型，前轴承反力约{b['front_reaction_N']:.2f} N，后轴承约{b['rear_reaction_N']:.2f} N。反号是力偶方向，不是负的载荷能力。

这不证明打印轴颈、笼、螺钉及电机支承可承载：未计轴向载荷、游隙、预紧、偏斜、刚度、寿命以及电机自身轴承的负载分担。当前35 mm打印轴颈必须先做配合量规和手转装配；加载版应采用金属轴颈/嵌件或经过验证的打印方案。

## 重心与发布条件

3 kg只是总质量。重心轴向每离法兰50 mm，单外负载额外弯矩增加1.4715 N·m；径向偏心50 mm，J7最不利重力roll矩为1.4715 N·m。JSON中的重心网格是需求表，不是许可包络。

采购冻结前需获得：当前封装的持续保持热曲线；J1–J6输出轴承允许载荷/寿命及连接器尺寸；真实转子惯量和摩擦；打印材料试样与连接强度/蠕变；实际线束活动范围。完成这些再冻结3 kg允许重心、速度、工作空间和断电处置。先购买少量关节做接口与热验证更有依据，不能仅凭本次计算一次采购定案。

资料：[RobStride官方固定版本](https://github.com/RobStride/Product_Information/tree/3f0cae4986e175337c7b03d891b899247b1f2933)；[NSK6807](https://www.nsk.com/au-en/engineering/products/bearings/ball-bearings/deep-groove-ball-bearings/single-row-deep-groove-ball-bearings/6807-apn.html)。详见[机器可复核结果](engineering/analysis/arm-a07-loads.json)、[打印装配指南](../engineering/arm_a08/README.md)。
'''
(ROOT/'docs/arm-body-loads-a07.md').write_text(text)
pt='<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->\n# A08 零件与几何验证\n\n'
pt+=f"清单指纹：`{hashlib.sha256((OUT/'manifest.json').read_bytes()).hexdigest()}`。\n\n"
pt+='| 分类 | 数量 | 建模质量kg |\n|---|---:|---:|\n'+''.join(f'| {k} | {n} | {mass[k]:.4f} |\n' for k,n in counts.items())
pt+='\n量规不装在机械臂上；采购件不打印。所有清单内STEP为单一有效实体，所有打印STL已重新读取检查封闭性、正体积和256 mm级平台包络。\n\n'
pt+='| 姿态 | 实体交叉检查对数 | 剩余冲突 |\n|---|---:|---:|\n'+''.join(f"| {k} | {r['pair_intersections_tested']} | {len(r['conflicts'])} |\n" for k,r in v['poses'].items())
pt+='\n螺钉与对应电机的螺纹啮合段是唯一预先定义的忽略项，因为电机包络不包含孔。其余零件均进行相交检查。该结果不检查连续运动、工具插入、真实连接器或制造公差。若存在冲突，不能把本版本描述为无干涉装配版。\n'
(OUT/'verification-summary.md').write_text(pt)
# Package only printable files plus supporting documentation, no motor/hardware geometry.
kit=OUT/'odradek-arm-a08-print-fit-kit.zip'
with zipfile.ZipFile(kit,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted((OUT/'stl').glob('*.stl')):z.write(p,'odradek-arm-a08-fit/stl/'+p.name)
 for p in [OUT/'print-manifest.json',OUT/'parts.csv',OUT/'verification-summary.md',ROOT/'engineering/arm_a08/README.md',ROOT/'LICENSE']:
  z.write(p,'odradek-arm-a08-fit/'+p.name)
with zipfile.ZipFile(kit) as z:assert z.testzip() is None
print('DOCUMENTS_AND_KIT',counts,kit.stat().st_size)
