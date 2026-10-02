<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# A06 同类机械臂负载口径核对

访问日：2026-10-02。状态：原厂公开资料研究，未做实机验证。本文仅记录 PiPER、PiPER-X、xArm6、Nova2、OpenArm 2.0 五款；ARX 由另一份来源记录覆盖。

## 本项目比较口径

已批准目标保持为 **7 轴本体、2 kg 工件净重，末端模块另计**。0.8–1.5 kg 头部质量是本轮研究范围，不是已确认的实物质量；两者相加为 **2.8–3.5 kg 末端总质量**。转接件、随动线束等应明确归入头部或本体预算，不能漏算或重复计入。

本项目的约 700 mm 是肩关节至任务 TCP 的尺寸链：当前 reference 的肩至 J7 约 550 mm 轴向尺寸，另有约 90 mm 侧偏；J7 轴心至 TCP 约 150 mm，快接口约位于 J7 后续轴向 29–32 mm 处。这不是厂商通常标注的底座至法兰工作半径。下面保留各厂商的 Reach / Working Radius 原词；端点未查清时不做同口径长短排序，也不以“载荷 × 宣传臂展”代替关节载荷计算。

## 五款公开参数

| 型号 | 本体 DOF | 原厂负载用语及数值 | 峰值与持续时间 | 原厂臂展字段 | 自重口径 | 工具是否计入负载 |
| --- | --- | --- | --- | --- | --- | --- |
| AgileX PiPER | 6 | Payload **1.5 kg**；本轮页面没有将其另列为连续额定/短时额定 | 未找到独立峰值和明确保持时间 | Reach **626 mm**；2024.09 快速手册另写工作半径 626.75 mm；未统一端点基准 | 快速手册写本体重量 **4.2 kg**；夹爪计重边界未明确 | 本轮所查页面未明确；不能写成 1.5 kg 工件净重 |
| AgileX PiPER-X | 6 | Payload **1.5 kg** | 未找到独立峰值和明确保持时间 | Reach **669 mm**；本轮产品页未定义两端基准 | **本轮原厂页面未核实**；不以经销商参数补空 | 本轮所查页面未明确；官网把夹爪列为可选附件不能证明其质量已从 Payload 中扣除 |
| UFACTORY xArm6 | 6 | Maximum Payload **5 kg**，受负载重心偏移限制 | 本轮所查资料没有单列峰值或统一的满伸保持秒数 | Reach **700 mm**；不能仅凭数字与本项目肩→TCP 等同 | V2.0.0 手册 XI1300：**12.2 kg，本体**；另一在线技术规格页：**12.5 kg，本体**，保留资料差异，原因未核实 | **包含末端执行器与工件**，见 UFACTORY Studio 的 TCP load 定义 |
| DOBOT Nova2 | 6 | Maximum Payload **2 kg** | 本轮所查资料未找到独立峰值或明确保持时间 | Working Radius **625 mm**；本轮规格表未定义两端基准 | **11 kg 机械臂**；**1.3 kg 是另列的控制器** | CR & Nova 原厂软件手册明确包含末端执行器与工件 |
| OpenArm 2.0 | 每臂 7 | Nominal Payload **4.1 kg**；定义为最差全伸姿态保持 **1 分钟** | Peak **6.0 kg**：从下垂姿态用 **3 秒**抬至最差全伸姿态，保持 **1 秒**后返回 | Key features 图写 Arm Reach **606 mm**；尺寸图端点包含所示原配夹爪前端，不能解释为裸法兰臂展 | Key features 图写 **5.5 kg / arm**；未进一步明确是否包含图示夹爪、支撑柱 | **包含末端执行器**；原厂举例 1.5 kg 工具对应 2.6 kg nominal 工件余量 |

对应原厂来源：[PiPER 产品页](https://global.agilex.ai/products/piper)、[PiPER-X 产品页](https://global.agilex.ai/products/piper-x)、[xArm V2.0.0 手册](https://www.ufactory.cc/wp-content/uploads/2023/05/xArm-User-Manual-V2.0.0.pdf)、[xArm 在线技术规格](https://docs.xarm.ufactory.cc/8.technical_specifications.html)、[UFACTORY Studio 设置说明](https://docs.ufactory.cc/user_manual/ufactoryStudio/7.settings.html)、[Nova2 产品页](https://www.dobot-robots.com/products/nova-series/nova2.html)、[DOBOT CR & Nova 软件手册](https://a.storyblok.com/f/298593/x/64cb99cd7b/dobotstudio-pro-user-guide-cr-nova-_v2-8-0_20250307_en.pdf)、[OpenArm 2.0 General](https://docs.openarm.dev/hardware/openarm-2.0/general/)。

## 重心与时间条件

### xArm6：5 kg 对应的重心范围很紧

V2.0.0 手册印刷页 237、§1.12 Maximum Payload 明确说明最大负载取决于重心相对于工具输出法兰中心的偏移。已将该页实际渲染并核对右侧 xArm6 图：横轴为轴向偏移 Lz，纵轴为径向偏移 Lxy。图中三档标注如下。

| 图中质量档位 | Lz 图示边界 | Lxy 图示边界 |
| --- | --- | --- |
| 5 kg | 15 mm | 30 mm |
| 3 kg | 90 mm | 100 mm |
| 2 kg | 180 mm | 200 mm |

这些是该版本图中的离散档位，不据此线性插值为新载荷曲线，也不换算为任意姿态下的连续扭矩保证。本项目头部和工件的合成重心若偏离法兰较远，不能仅凭“总质量小于 5 kg”就判定满足要求。依据：[xArm 手册 §1.12，印刷页 237](https://www.ufactory.cc/wp-content/uploads/2023/05/xArm-User-Manual-V2.0.0.pdf#page=237)。

### Nova2：工具与工件合计，数值重心包络仍待补

DobotStudio Pro User Guide (CR & Nova) V2.8.0，文件名日期 2025-03-07，§4.4 Load parameters 规定负载质量包含工具和工件，且质量与偏心坐标应在机械臂允许范围内。本轮没有核实 Nova2 专属的数值载荷—重心包络；不借用 **Nova2s** 或 CR 系列的曲线。依据：[原厂软件手册 §4.4](https://a.storyblok.com/f/298593/x/64cb99cd7b/dobotstudio-pro-user-guide-cr-nova-_v2-8-0_20250307_en.pdf)。

### OpenArm 2.0：公开持续时间定义最明确

4.1 kg 的 nominal 工况和 6 kg 的 peak 工况不同；一分钟保持不能表述为不限时间连续保持。所查页面没有给出完整的工具重心偏移包络、重复该循环的占空比或稳态温升条件。需要把公开工况与自己的任务轨迹分别核对。依据：[OpenArm 2.0 Payload definition](https://docs.openarm.dev/hardware/openarm-2.0/general/#payload-definition)。

### PiPER / PiPER-X：公开简表不足以闭合工具口径

当前原厂主页均为 1.5 kg；本轮未核实另一个峰值数值，也未找到明确的满伸保持时间与工具重心曲线。PiPER-H 等其他变体的数据不能移用至 PiPER-X。没有公布时间不等于无限时保持，没有说明夹爪边界也不等于可在该数值之外再加夹爪。

## 对本项目可用的结论

1. **2 kg 工件净重与“2 kg 级机械臂”不是同一口径。** 加上研究范围内的头部，本项目工具侧总质量为 2.8–3.5 kg；Nova2 的 2 kg 明确要同时容纳工具和工件。
2. **同类产品确有轻量科研和较重协作两种设计取向。** 本表的 PiPER 与 OpenArm 2.0 自重、负载定义差别明显；xArm6 的 5 kg 数值同时附有重心约束。不能只用 kg/kg 比值给产品排序。
3. **OpenArm 2.0 是七轴、公开工况比较清楚的研究参照；xArm6 是重心约束比较清楚的参照。** 两者都不能证明本项目的结构、热、连续静止保持或线束寿命已经通过。
4. 本轮不改变 2 kg 净工件目标。后续对齐的最小输入是：完整头部质量及合成重心、工件重心范围、需要保持的姿态与时长、任务循环/速度/加速度，以及本体各段真实质量。之后才能将整臂模型结果与关节额定工况进行有效比较。

## 原始来源与版本记录

全部链接于 **2026-10-02** 访问。网页未提供版号的，日期仅表示访问日，不推断规格发布时间。

| 编号 | 原始资料 | 版本 / 位置 | 本轮提取字段与边界 |
| --- | --- | --- | --- |
| P1 | [AgileX PiPER](https://global.agilex.ai/products/piper) | 产品网页，未见版号 | 6 DOF、1.5 kg、626 mm、4.2 kg；工具、重心、保持时间未明确 |
| P1a | [PiPER 快速使用手册，原厂 PDF](https://new.agilex.ai/raw/upload/20241017/%EF%BC%88%E5%B7%B2%E5%8E%8B%E7%BC%A9%EF%BC%89%E6%AD%A3-PiPER%E4%BD%BF%E7%94%A8%E6%89%8B%E5%86%8C_%E4%B8%AD%E6%96%87%E7%89%880925_52071.pdf) | 封面 2024.09；§5 技术规格，印刷页 09；本轮从官方 PDF 的检索提取核对 | 6 DOF、有效负载 1.5 kg、本体重量 4.2 kg、工作半径 626.75 mm；未把夹爪包含关系自行补全 |
| P2 | [AgileX PiPER-X](https://global.agilex.ai/products/piper-x) | 产品网页，未见版号 | 6 DOF、1.5 kg、669 mm；自重和工具载荷计重边界本轮未核实 |
| U1 | [xArm User Manual PDF](https://www.ufactory.cc/wp-content/uploads/2023/05/xArm-User-Manual-V2.0.0.pdf) | V2.0.0；URL 路径 2023/05；印刷页 237–238、§1.12/1.13 | 已渲染核对载荷重心图；XI1300：5 kg、700 mm、6 DOF、12.2 kg robot arm only；URL 月份不当作硬件生产日期 |
| U2 | [xArm 在线技术规格](https://docs.xarm.ufactory.cc/8.technical_specifications.html) | §8；未见对应硬件版号；已直接提取原页面 HTML 表格核对 | xArm6 5 kg、6 DOF、12.5 kg robot arm only；与 U1 自重不一致，未合并为单一数值 |
| U3 | [UFACTORY Studio Settings](https://docs.ufactory.cc/user_manual/ufactoryStudio/7.settings.html) | §7.1.2 TCP | 负载包含末端执行器与工件，重心坐标相对法兰 |
| D1 | [DOBOT Nova2](https://www.dobot-robots.com/products/nova-series/nova2.html) | 产品网页，未见版号 | Maximum Payload 2 kg、Working Radius 625 mm、11 kg；J1–J6；控制器 1.3 kg 另列 |
| D2 | [DobotStudio Pro User Guide (CR & Nova)](https://a.storyblok.com/f/298593/x/64cb99cd7b/dobotstudio-pro-user-guide-cr-nova-_v2-8-0_20250307_en.pdf) | 原厂手册，Storyblok 资源地址；V2.8.0；2025-03-07；§4.4 | 工具和工件合计、偏心参数应受限；未从该软件手册取得 Nova2 专属数值包络 |
| O1 | [OpenArm 2.0 General](https://docs.openarm.dev/hardware/openarm-2.0/general/) | 页面显示 Last updated Sep 29, 2026 | 4.1 kg nominal、6 kg peak、工具计重、1 分钟与 3+1 秒的不同工况 |
| O2 | [OpenArm 2.0 Key features 原图](https://docs.openarm.dev/assets/images/openarm-2.0-204d2c840e8094cb2a8152d065040902.png) | 由 O1 链接的官方图片，已目视读取 | 7 DOF、606 mm Arm Reach、5.5 kg Weight per Arm |
| O3 | [OpenArm 2.0 尺寸原图](https://docs.openarm.dev/assets/images/v2_mech_stop_conf-e4e76fb19fb6c5e2c01f5d8fc7639325.png) | 由 O1 链接的官方图片，已目视读取 | 606 mm 尺寸端点包含图示夹爪前端；不沿用其他代际的臂展数字 |

本轮未联系厂商、未采购、未用经销商自重数字填补 PiPER-X 空项。上述数据是原厂公开声明与资料读取结果，不构成独立认证或本项目制造验收。
