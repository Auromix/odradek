# DYNAMICS-REVIEW01 — 独立力矩与能量复核

本轮将五段已完成连接件的21个原创金属实体惯量接入同一七轴模型，并用两种独立算法复核动力学。结果是**数学实现一致**，不是整机驱动、运动范围或2kg任务通过。L45、模块内转子分配、四指运动及真实头部惯量仍未纳入这一模型。

## 参数与真实CAD的边界

[质量加载器](../../engineering/structural_mass_model.py)逐个重读LINK12/23/34/56/67的原件STEP，检查有效单实体、源哈希、密度2.70g/cm³、COM与坐标变换。直接对含孔的实体积分质量和质心惯量，不用外包盒替代。惯量记录在零件局部质心坐标，`orientation_home`给局部到零姿态世界的旋转；单位为kg·m²。平移项只在需要改变转动参考点时加入，不重复叠加到质心惯量。

各段另有0.20/0.15/0.15/0.10/0.10kg紧固余量，放在对应金属COM，采用50mm立方体的惯量代理。它们不是称重。本例保留L45的0.35kg及J7接口L7的0.15kg旧预算；将4.5kg头部预算COM设为Z784、TCP设为Z914，对应24mm延伸条件。**这不是对真实头部装配的整体平移**，原L7预算仍留在原接口位置。今后接入包含adapter/EXT24的整头质量时，必须删除对应旧L7预算，避免双计。

七个关节模块仍采用目录整模块质量、外形中点COM和圆柱惯量，并归属上游壳体。这不是内部电机、减速器和输出转子的真实惯量分配。额外折算电机转子惯量缺失，当前置零不能成为电机选型依据。四指被一个刚性头预算替代，尚无七臂轴与四指的耦合惯量。

## 两条算法

原有 [运动学实现](../../engineering/kinematics.py) 使用各实体的线速度/角速度Jacobian：

```text
M(q) = Σ[m JvᵀJv + Jwᵀ R Icom Rᵀ Jw] + diag(Jrotor)
G(q) = −Σ[Jvᵀ m g]
cᵢ(q,q̇) = ½Σⱼₖ(∂Mᵢⱼ/∂qₖ + ∂Mᵢₖ/∂qⱼ − ∂Mⱼₖ/∂qᵢ)q̇ⱼq̇ₖ
τ = Mq̈ + c + G − Jtoolᵀ Wenvironment
```

原实现对M作中心差分获得科氏项。新增 [独立复核](../../engineering/review_rigid_body_dynamics.py) 采用Rodrigues刚体变换、轴原点速度和轴方向导数，直接计算实体加速度：

```text
żⱼ = ωupstream,j × zⱼ
ȯⱼ = Σₖ<ⱼ [zₖ × (oⱼ−oₖ)]q̇ₖ
v = Σⱼ [zⱼ × (p−oⱼ)]q̇ⱼ
a = Σⱼ {[zⱼ × (p−oⱼ)]q̈ⱼ
       + [żⱼ × (p−oⱼ) + zⱼ × (v−ȯⱼ)]q̇ⱼ}
ω = Σⱼ zⱼq̇ⱼ
α = Σⱼ (zⱼq̈ⱼ + żⱼq̇ⱼ)
F = m(a−g)
Ncom = Iworld α + ω × (Iworld ω)
τⱼ += zⱼ · [(p−oⱼ) × F + Ncom]
```

每个实体只对其之前的活动轴求和。新增算法不调用原Arm类的Jacobian、质量矩阵、科氏项或body_states，也不通过差分得到刚体加速度。两者只共享输入约定；独立Rodrigues变换来自已有静力审查代码。

外力约定为环境作用于TCP的`[Fx,Fy,Fz,Mx,My,Mz]`，均在基坐标表示，力矩参考点是TCP。独立方法逐轴扣除`z·[(pTCP−o)×F+M]`。把同一个工件既加入实体质量又作为重力外力输入会双计，当前模型只把2kg工件作为实体。

## 实际执行的复核

24组固定随机种子的q/q̇/q̈覆盖输入关节范围，速度取±0.8rad/s、加速度±1.5rad/s²，附加随机TCP外力±20N和力矩±3Nm。它们是数值检查输入，未经碰撞、线束或任务认证，不能下载到控制器执行。

| 检查 | 结果 |
|---|---:|
| 独立力/矩法与原逆动力学最大差 | 8.92×10⁻¹¹N·m |
| 能量功率恒等式最大残差 | 5.38×10⁻⁹W |
| 单摆闭式解析解最大误差 | 8.89×10⁻¹⁶N·m |
| 人工折算转子惯量算例差 | 1.61×10⁻¹³N·m |

同时将M差分步长从10⁻⁵rad缩到5×10⁻⁶rad复核，并检查各姿态M正定。功率检查通过独立实体速度计算动能和势能，沿`q(t±h)=q±hq̇+½h²q̈`及`q̇(t±h)=q̇±hq̈`差分能量，与无外力情况下`τ·q̇`比较。单摆使用`τ=(Iyy+ml²)q̈−mgl sinq`闭式解；人工转子算例只测试代码项，不声称其数值属于任何RH模块。

原始24组输入、力矩、残差、最小特征值和源哈希保存在 [review.json](../../engineering/generated/dynamics-review/review.json)，完整输入模型为 [model.json](../../engineering/generated/dynamics-review/model.json)。没有从这些数值推出全域最大力矩、允许加速度或热额定值。

## 复现与后续

```sh
python engineering/review_rigid_body_dynamics.py
# 也可复核另一个符合相同SI单位和preceding_joints约定的模型：
python engineering/review_rigid_body_dynamics.py --model /path/to/model.json --out /path/to/result
```

本次完成真实五段惯量的可追溯加载以及动力学独立核验。下一步将L45、真实整头/四指质量、线路和壳体加入同一装配，再对经几何约束筛选的具体任务轨迹计算峰值与RMS；关节热、摩擦、制动、弹性、接触与实机试验需分别闭合。

原创分析：CC BY-NC 4.0。Odradek — Auromix contributors (https://github.com/Auromix/odradek)。
