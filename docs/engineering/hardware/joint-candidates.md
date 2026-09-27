# R4 关节执行器候选与接口核验

版本：2026-09-27。状态：**有来源的候选选型，尚未采购放行或制造放行**。本表不把模块参数等同于整机 2 kg 负载能力。

工作假设为 2 kg 净工件，末端模块按 2.0 kg，并检查 1.8–2.2 kg 敏感性；此前 1.2 kg 是已替换的早期预算。肩部至 TCP 的 700 mm 是初算约束，必须随实际关节堆叠、工具长度和用户确认更新。计算设备置于外部，关节内保留执行、编码反馈和 EtherCAT 从站。

## 推荐推进顺序

先采用 MYACTUATOR RH 集成谐波关节建立装配与热/重力预算，以其原厂安装图和 STEP 为接口依据。将关节等级沿臂长逐级减小，在关节之间形成细长梁；不能为了外形把标准关节轴长压短，或把中央孔径画大。Harmonic Drive SHA-IDT 作为不同供应商的完整关节备选；无框电机 + 谐波减速器 + Circulo 驱动作为后续定制金属关节路径。

首轮偏保守分配为 J1/J2 RH-25 B、J3/J4 RH-20 B、J5/J6 RH-17 B、J7 RH-14 N。七个执行器合计 **12.32 kg**，尚未含连接件、线束、外壳、底座和末端。这个重量对桌面细长机械臂并不轻；是否把 J1、J3 或 J5 降一级，需要全姿态重力矩、加速矩、输出轴承力矩和热负荷结果支持。J7 无闸必须另外处理失电姿态保持，不能依赖谐波摩擦当作制动器。

## 主候选：MYACTUATOR RH，100:1

下表全部采用原厂 **RH Series-product manual-260805.pdf** 中 100:1 列。N 表示无闸，B 表示带闸；尺寸单位 mm，扭矩为模块输出侧。PDF 页号按文件第一页为 1，不是纸面页码。[官方产品与 CAD 下载入口](https://www.myactuator.com/downloads-rhseries)，[官方手册包](https://www.myactuator.com/_files/archives/cab28a_be98b58973d34f7aaa50bdf3f2aa12ed.zip)。

| 候选 / 已核实完整订货名 | 额定 / 目录峰值 N·m | N / B 质量 kg | 最大本体直径 | N / B 轴长 | N / B 中央通孔 | 证据 PDF 页 |
|---|---:|---:|---:|---:|---:|---:|
| EPS-RH-14-100-E-N-D | 11 / 28 | 0.78 / — | 70 | 81.7 / — | 10 / — | 3 |
| EPS-RH-17-100-E-N-D；EPS-RH-17-100-E-B-D | 35 / 54 | 1.11 / 1.28 | 80 | 90.2 / 104 | 15 / 12 | 6 |
| EPS-RH-20-100-E-N-D；EPS-RH-20-100-E-B-D | 50 / 80 | 1.45 / 1.75 | 90 | 82.9 / 97.4 | 14 / 12 | 8 |
| EPS-RH-25-100-E-N-D；EPS-RH-25-100-E-B-D | 108 / 157 | 2.42 / 2.74 | 110 | 89.5 / 105.2 | 22 / 22 | 10 |

共同参数：48 V 标称、20–55 V 范围，额定 25 rpm、空载 30 rpm，输入与输出各 17 bit 绝对编码器，EtherCAT / CAN BUS。轴长图注 ±0.3 mm；**不包含客户插头、插拔操作和线束弯曲空间**。RH14 当前产品手册明确标准款仅无闸；然而同日官方 CAD 包实际含 B 版 STEP 和 2D-A0 图（Ø70×94.7±0.3、通孔Ø10，质量栏为 `/`）。这是已证实的资料冲突：可研究 B 版几何，仍不能据此确认标准供货或质量预算。[RH14](https://www.myactuator.com/rh-14details)、[RH17](https://www.myactuator.com/rh-17details)、[RH20](https://www.myactuator.com/rh-20details)、[RH25](https://www.myactuator.com/rh-25details)。

额定测试的原厂条件为 24°C 环境、额定转速、温升达到 60°C 的热平衡；这不是任意外壳内或零速持续保持的无条件扭矩保证。先做模块台架热测试，再决定安装于金属散热梁还是由独立导热路径散热。全封闭 3D 打印壳不能直接承接目录额定热能力。

### 安装接口：可以开始参数化，但不能猜孔位

| 型号 | 输出定位台阶 | 输出孔阵 PCD / 螺纹数量 / 螺纹深度 | 本体定位 | 固定侧通孔 PCD / 数量 / 孔径 |
|---|---|---|---|---|
| RH14 | Ø50 h6 | Ø44 / 8×M3 / 5 | Ø70 h7 | Ø64 / 4 / Ø3.5 |
| RH17 | Ø60 h6 | Ø54 / 16×M3 / 6 | Ø80 h7 | Ø74 / 8 / Ø3.4 |
| RH20 | Ø70 h6 | Ø62 / 16×M3 / 6 | Ø90 h7 | Ø84 / 8 / Ø3.4 |
| RH25 | Ø85 h6 | Ø77 / 16×M4 / 6 | Ø110 h7 | Ø102 / 8 / Ø4.5 |

这是图面上可读的接口尺寸。**数量 + PCD 不代表均布孔阵**；例如 RH17 图有 18° / 36°标注与已占用装配螺钉，不能直接画成 16 孔均布 22.5°。孔角度、沉孔方向、盲孔底、可用螺纹长度、工具进入空间与旋转件/固定件归属，必须再由所购版本的 STEP、完整 2D 图及实物核对。CAD 可导入本地装配，但原厂模型分发权未确认，仓库只保留来源和独立接口记录。

| 官方 CAD 包 | 含量 / 用法 |
|---|---|
| [RH14 260805](https://www.myactuator.com/_files/archives/cab28a_bcc022d169b448ff82894171aa9ae1ce.zip) | 实际含 N/B 两套 STEP、2D-A0；B 版质量与供货未确认 |
| [RH17 260805](https://www.myactuator.com/_files/archives/cab28a_e83c5096831240dbb0f680b9f6b2cfeb.zip) | 分别核对 N 与 B，不混用通孔和轴长 |
| [RH20 260805](https://www.myactuator.com/_files/archives/cab28a_5ebf837a05c14a718f4c6611666c03ad.zip) | 分别核对 N 与 B，不混用通孔和轴长 |
| [RH25 260805](https://www.myactuator.com/_files/archives/cab28a_bc732701dadf4512a0d917ecaab12747.zip) | 提供 STEP 及 2D-A0 PDF；实际存在 N/B 两版 |

### 必须保留的来源冲突与未知项

1. **峰值定义不一致。** 260805 主参数表给 RH17/20/25 峰值 54/80/157 N·m，同页短时堵转表又出现更大值；后者不能替代产品允许峰值，更不能作为连续设计值。当前模型先使用较低目录峰值，要求供应商解释版本、持续时间和限流条件。
2. **制动扭矩定义缺失。** 用户手册 V1.4 §7.1 表 7-1 给 RH14/17/20/25 静态制动力矩 0.2/0.5/0.8/1.2 N·m，但未明确所在侧；RH14 行、CAD 包中的 B 图与新产品手册标准无闸相互冲突。不能直接乘速比宣称输出保持能力。须明确电机侧/输出侧、磨损后最小保持力、接合/释放时序和失电动作。
3. **制动用途。** 原厂手册把它定义为静态保持制动，限制高载高速动态制动。机械急停路径需要处理先减速、再抱闸、再撤力的时序及突然掉电工况；本项目尚未完成该验证。
4. **整件惯量未知。** 目录有电机/转子惯量，不是整个关节作为下游载荷的刚体惯量。整件 COM、旋转侧质量分配和惯量张量未核实。可用保守包络估算进行筛选，但必须标为估算并由称重/摆测/厂商数据收敛。
5. **轴承允许倾覆力矩未知。** 新册列有径向/轴向承载数据，但未足够定义本方案的组合载荷寿命，不能拿径向额定载荷乘几何半径替代寿命计算。
6. **安全功能未确认。** 未在已核实 RH 资料中找到可用于本系统声明的认证 STO / SBC 证据。EtherCAT 通信失联停机与认证撤力不是同一能力。

以上都应进入采购技术澄清单；当前没有发询价消息，也没有得到报价、库存、交期或供应商书面确认。

### EtherCAT 与内走线

官方协议包明确 CiA402，包含 CSP / CSV / CST；其 ESI、实际发货固件、同步周期、掉线响应、单位换算与 PDO 映射仍需台架验证。全臂采购必须锁定 `-E-` 版本，不能把支持 CAN 的同系列当作 EtherCAT 已满足。[协议包](https://www.myactuator.com/_files/archives/cab28a_be98b58973d34f7aaa50bdf3f2aa12ed.zip)。

RH 产品图提供 EtherCAT IN/OUT；附件表给 SH1.0 4 pin 接头。线束应按原厂的屏蔽双绞要求制作和验证，不从文字表中 T/R 对的描述猜测 100BASE-TX 引脚。RH14/17/20 电源附件为 XT30(2+2)、18 AWG；RH25 为 XT30U-F、14 AWG。额定相电流不能直接相加当作电源输入电流，也不能把随模块附送电源线视为七轴母线线径结论。

中央最小孔只有 **RH14 的 Ø10 mm**，带闸 RH17/RH20 是 Ø12 mm。需要把电源、保护地/屏蔽、EtherCAT、两根相机高速线和末端信号的真实线径与接头装配过程放进截面模型。摄像接口暂不能从 `gxxx` 猜成已定型 GMSL；摄像链路、供电方式和可穿孔接头以系统接口确认结果为准。禁止把普通柔性线缆的“能塞进去”当作反复扭转寿命合格。

J7 首版采用有限转角与受控服务回环；若要无限连续转动，需另选满足摄像协议带宽的旋转接头，不能默认一般电滑环传输高速摄像信号。关节内部走线与可拆式头之间必须有固定端应力释放和可维修的接头位置。

## 替代路径

### 完整集成关节：Harmonic Drive SHA-IDT

SHA 系列有中空轴、制动选项、双绝对编码器和 48 V EtherCAT 选项，提供原厂 2D / STEP。100:1 档附近采用其 **101** 比值：SHA-20A 连续 33.4、最大 107 N·m、2.1 kg；SHA-25A 连续 57、最大 204 N·m、3.3 kg。其连续额定条件明确使用 **320×320×16 mm 铝散热板**，不能直接套用在细长腕部。作为不同供应商备选具有完整资料，但质量、散热和接头凸出使其不宜直接替代每个 RH 型号。[产品参数](https://www.harmonicdrive.net/products/integrated-actuators/integrated-actuators/sha-integrated-with-servo-drive)。

采购时须完整指定大小、速比、制动、轴向/径向出线与 `E/ES` EtherCAT 选项，当前不编造完整订货号。MTO 选件不等同于有第三方认证的 STO，官方手册已作区分。[选型手册](https://www.harmonicdrive.net/_hd/Content/catalogs/pdf/SHA-Integrated-Brochure.pdf)、[2D 图](https://www.harmonicdrive.net/downloads/pdf-drawings/sha-integrated-actuators)、[STEP](https://www.harmonicdrive.net/downloads/stp-files/sha-integrated-actuators)。

### 定制金属关节：无框电机 + 减速器 + EtherCAT 驱动

| 元件 | 可核实候选 | 用于下一轮的决定 |
|---|---|---|
| 减速器 | Harmonic Drive CSG-20-100-2UH：额定 L10 52 N·m、平均扭矩限值64、重复峰值107、瞬时峰值191，质量0.98 kg | 这些是减速器限制，不是组合执行器连续扭矩；独立区分寿命与冲击 |
| 无框电机 | Kollmorgen TBM2G-06026 框型：外径60、内径30、A最大35.81 mm；完整绕组/传感器代码未选 | 48 V 绕组、安装散热条件、电流/速度曲线与制动/编码器空间共同选择，不能只用理论扭矩乘100 |
| 驱动 | Synapticon Circulo 7：Ø72.2、内孔20、高21.3 mm、92 g（不含编码环）；8 A rms连续、24 A rms峰值 | 其连续电流有散热安装条件；选配编码器和制动、明确订货代码及安全集成 |

来源：[CSG20](https://global.harmonicdrive.net/products/gear-units/gear-units/csg-2uh/csg-20-100-2uh)、[TBM2G 尺寸](https://www.kollmorgen.com/en-us/products/motors/direct-drive/tbm2g-series-frameless)、[TBM2G 绕组选型书](https://www.kollmorgen.com/sites/default/files/TBM2G-KM_SG_00396_RevA_EN-mobile.pdf)、[Circulo 参数](https://doc.synapticon.com/circulo/technical_specs/tech_specs_circulo.html)、[Circulo CAD / ESI](https://doc.synapticon.com/circulo/technical_specs/downloads_circulo.html)。

此路径增加定转子安装、气隙同心、轴承预紧、编码环标定、制动整合和 EMC 的工作，适合在关节需求收敛后做减重，不作为第一轮打印样机中“已完成选型”的伪完整组合。Circulo 的 STO/SBC 证书也不自动认证整台机械臂。

Synapticon ACTILINK-JP 也存在官方完整集成方案，但当前官方目录显示 Sample/RFQ；尚未取得足够的当前量产配置图纸和连续参数，不采纳经销商旧表补齐。保留为可询价候选。[官方目录](https://catalog.synapticon.com/shop/category/actilink-actuators/actilink-jp)。

## 3D 打印与金属结构的边界

打印件首先验证外壳比例、关节相对位置、线束可装配性、拆头接口和低力运动。实际 2 kg 工件验证前，动力轴承座、关节安装受力路径、螺纹连接、机械限位与固定底座需完成材料与连接设计；不要将仅尺寸相同的打印件视为金属件强度等价品。

金属版应围绕同一原厂定位台阶与孔阵建立可更换转接件，并标明基准、配合、形位、公差、材料、表面处理、紧固件等级/预紧、检验方法。关节选型、结构 COM、线束弯曲与外形互相迭代；当前的数据可启动工程装配，不能提前冻结全部制造图。

机器可读来源、型号和未决参数见 [joints.json](../sources/joints.json)。所有 `null` 表示尚未核实，不能在后续脚本中默认为零。
