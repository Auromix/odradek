<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek) -->
# 肩部抬升后的整臂候选总装

**RAISED-ARM-INTEGRATION01：已把 +35 mm 肩架同步进实体姿态、11 自由度数学模型和原生 Blender。** 原版参数及旧研究文件保留；本版是明确分开的派生候选。五种臂姿态各配开、闭两种头部状态，共十个实体姿态未发现所检查零件之间的正体积交叠。旧 `reach` 中的三对肩部碰撞在本候选中消除；这不代表连接姿态的运动路径通过。

[原生 Blender](../../engineering/generated/raised-arm-integration01/blender/odradek-integrated-7-plus-4.blend) · [装配参数](../../engineering/generated/raised-arm-integration01/assembly-parameters.json) · [11DOF 输入](../../engineering/generated/raised-arm-integration01/model.json) · [实体姿态检查](../../engineering/generated/raised-arm-integration01/collision-poses.json) · [数学复核](../../engineering/generated/raised-arm-integration01/mathematics-review.json) · [独立重开记录](../../engineering/generated/raised-arm-integration01/blender/reopen-review.json)

![抬升肩架后的当前结构](../../engineering/generated/raised-arm-integration01/blender/arm-open-oblique.png)

## 坐标与几何一致性

J1 和固定底座保持原位；J2～J7 的轴心、下游金属零件及完整 HEAD03 在零位都平移世界 Z +35 mm。L12 输出板不动，后叉替换为 [SHOULDER-RAISE01](shoulder-raise-study.md) 的真实长腿实体，前压环抬升。L12 三件始终属于 J1 输出后的固定肩架，不错误归入 J2 转动侧。

| 零位位置 | 本候选 mm |
|---|---|
| J1 / J2 | `[0,0,105.2]` / `[0,0,205]` |
| J3 / J4 | `[0,55,255]` / `[0,0,435]` |
| J5 / J6 | `[0,-55,485]` / `[0,0,640]` |
| J7 / 头部正面 | `[0,55,675]` / `[0,55,839]` |
| 名义 TCP | `[0,55,949]`，仍是特定接触研究的定义 |

四指的局部尺寸、独立闭合角、P16 连杆及上下外倾相机未改变。主体关节的 `limit_deg` 继续只是研究边界，不是实机控制限位。原版参数中较早的灯片和头部占位尺寸没有直接复制成新的制造参数；以本版装配参数和指定 HEAD03 来源为准。

## 实体检查的结果和范围

| 本体姿态，J1～J7，度 | 头展开 | 头闭合 |
|---|---:|---:|
| `zero`: 0,0,0,0,0,0,0 | 0 对交叠 | 0 对交叠 |
| `inspect`: 0,−25,0,−95,0,−15,0 | 0 | 0 |
| `reach`: 0,65,0,10,0,10,0 | 0 | 0 |
| 肩部 +90: 0,90,0,0,0,0,0 | 0 | 0 |
| 肩部 −90: 0,−90,0,0,0,0,0 | 0 | 0 |

每个姿态检查 27,924 对对象：24 个原创连接件、8 个底座件、7 台真实原厂 BREP，以及每个头部状态的 697 个实体。先用包围盒安全排除，再逐 solid 求交，报告阈值 `1e−4 mm³`。预期安装接口也不豁免正体积交叠。毫米空间的独立旋转变换与 SI 运动学复核，最大差 `1.4211e−13 mm`。

这里未集成全臂/底座全部紧固件，未重新验证头内彼此的碰撞或原厂内部转子运动，未建线束、护壳、工件和真实桌面障碍。局部肩部 ±90° 连续证明及其已知硬件证据仍单列在 SHOULDER-RAISE01；本表的十个离散姿态不扩大该证明的对象范围，也不证明全臂联合角域或路径。

## 对桌面平面的补充检查

另以世界 Z=0 为假设的无限水平桌面，对十个相同姿态做了 [保守支持平面检查](../../engineering/generated/raised-arm-table01/study.json)。每个实际 BREP 的零位包围盒包含该实体；变换其八个角点后取最低 Z，得到该姿态下整个零件的保守高度下界，未把网格抽样最低点当作严格界。

安装底板/背板等固定锚固件按预期穿越桌面，因此从此项排除，安装开孔和桌板厚度另查。剩余 728 个对象均在假设平面上方；固定 J1 的最低名义界为 2.0 mm。J2 输出后的活动集合，在肩部±90°、头展开时最接近桌面，上灯片的保守高度下界为 **20.772 mm**；头闭合时为 102.216 mm，其余所测姿态至少 121.517 mm。

这不包含物体、工具、线束、护壳、全臂详细紧固件或实际桌面上的障碍，也未扣除挠度/制造误差；不能把20.772mm直接设成运动安全距离。复现：`python engineering/raised_arm_table_screen.py`。

## 数学模型的变化

沿用 [DYNAMICS-11DOF01](articulated-dynamics-review.md) 的六段金属与 HEAD-MASS04 十三个刚体，去除的旧头预算、L7 重复预算不重新加入。L12 三件替换为新 CAD 质量、COM 及完整世界轴中央惯量；因此其惯量坐标变换设为单位阵，避免重复旋转。

0.20 kg 的 L12 紧固件预算保留，COM 暂放在新金属聚合 COM，旧代理惯量保留；这不是已知螺钉重新称重。其余下游身体、工具点和头部坐标都同步抬升。模型小计 **21.510480 kg**，包括固定 J1 与 2 kg 物体；固定安装底座、头部未计量部件等不在其中，不能当作完整机器重量。

在八组既有数学状态上重算：解析 Jacobian 对独立位姿差分最大误差 `8.977e−11`；直接 Newton/Euler 与质量矩阵/科氏/重力表达的力矩最大差 `8.945e−8 N·m`；质量矩阵最小特征值 `1.17635e−4`，均为正。还验证了全部下游 COM 在任意所测 q1 下始终只抬升 35 mm，以及重力广义力不变。原因是 J1 绕世界竖直轴，J2 以后的相对力臂保持原样；这不说明肩架的局部弯矩、挠度或失电保持条件不变。

2 kg 物体仍作为固定于 TCP 的刚体处理。指轴力只包含指机构自重/惯性；实际夹持接触力、摩擦及物体力矩必须通过接触 Jacobian 另加，不能把本检查当作 2 kg 抓持验收。型号热保持额定、真实转子分配、摩擦和驱动模型仍待验证。

## Blender 与复现

Blender 4.5.14 LTS 中有 736 个产品网格、11 个 `q_deg` 控制及 27 条原生简单表达式驱动。推杆本体会绕底部销轴转动，滑杆沿变化后的轴线伸缩。四幅视图均已检查；零位全景加大取景范围以留出边缘空间。中央 285 点环形/箭头是单独标明的 UI 预览，没有借此宣称中央电路板已经完成。

生成阶段有 492 项本体、1716 项指/推杆点变换检查，以及 697 项独立闭态 CAD 包围界核对；最大闭态网格界误差约 0.002735 mm。在禁用 Python 自动执行后重新打开 `.blend`，27 个简单表达式驱动和独立 CAD 核对继续通过，无需处理器或外部 Python 回调。模型是结构评审资产，未完成护壳、线束和负载放行。

```bash
python engineering/export_integrated_arm_preview.py --output /private/work/base-mesh.json
python engineering/integrate_raised_shoulder.py \
  --base-mesh /private/work/base-mesh.json --mesh-output /private/work/raised-mesh.json \
  --model RH25-B=/private/vendor/RH25.step --model RH20-B=/private/vendor/RH20.step \
  --model RH17-B=/private/vendor/RH17.step --model RH14-N=/private/vendor/RH14.step
blender --background --factory-startup --python engineering/blender_integrated_arm.py -- \
  --mesh-json /private/work/raised-mesh.json --out engineering/generated/raised-arm-integration01/blender \
  --home-scale 1.37 --home-target-z 0.46
blender --background --disable-autoexec \
  engineering/generated/raised-arm-integration01/blender/odradek-integrated-7-plus-4.blend \
  --python engineering/review_integrated_blend.py -- \
  --mesh-json /private/work/raised-mesh.json \
  --report engineering/generated/raised-arm-integration01/blender/reopen-review.json
```

原厂源文件需匹配既有受控哈希，不随本项目重新分发。生成脚本保持旧基线只读。下阶段仍需肩架实际刚度/连接/公差、线束和控制板实体，以及联合轨迹和实物测试。
