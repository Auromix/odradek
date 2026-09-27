# 四灯片夹爪候选器件与装配条件

状态：非冻结候选 / 2026-09-27。目录参数不等于系统性能；未询价、未下单、未证明库存或持续抓取能力。计算见 [夹爪分析](../gripper-analysis.md)。

## 1. 指驱动：慢速短版优先验证，较快版并列保留

| 字段 | G-A：慢速短版 | G-B：较快版 |
|---|---|---|
| 电机目录系列/配置请求 | FAULHABER `2214X024BXTH`，24 V | FAULHABER `2250X024BX4`，24 V |
| 电机额定力矩 / 电流 / 转速 | 9.7 mN·m / 0.36 A / 2710 rpm | 26.2 mN·m / 0.85 A / 4870 rpm |
| 电机外径 / 本体长 / 质量 | Ø22 / 14.8 mm / 28.9 g | Ø22 / 51.8 mm / 105 g |
| 原厂齿轮箱请求 | `22GPT HT 829:1`，四级 | `22GPT HT 330:1`，四级 |
| 编码器请求 | `IE3-1024 L` | `IE3-1024 L` |
| 电机+齿轮箱 L1（不含轴伸） | 58.4 mm | 95.4 mm |
| 带编码器电机长度 | 26.5 mm | 67.6 mm |
| 带编码器组合体估算长度 | 70.1 mm | 111.2 mm |
| 再含标准轴伸 16.3 mm 的估算 | 86.4 mm | 127.5 mm |
| 每指质量下界 / 四指 | 151.4 g / 605.6 g | 227.5 g / 910.0 g |
| 用额定转速除实际减速比 | 3.268 rpm；90° 约 4.59 s | 14.758 rpm；90° 约 1.02 s |
| 使用判断 | 慢速形态和接触验证首选 | 更快动作备选，外包尺寸较大 |

来源：[2214 BXT H 原厂数据表](https://www.faulhaber.com/fileadmin/Import/Media/EN_2214_BXTH_DFF.pdf)、[2250 BX4 原厂数据表](https://eshop.faulhaber.com/media/cd/65/80/1775629746/EN_2250_BX4_DFF.pdf)。两者按 2026-07-28 版核对；2250 额定值涉及原厂规定的散热条件，不可把系列宣传的 32 mN·m 或 151 mN·m 堵转扭矩当成封闭头部连续值。

`X` 表示配置请求中的系列写法，**不是已经确认可以按这一串字符采购的最终完整物料号**。请原厂确认轴端、法兰、编码器、电缆选项和最终组合订单号。组合长度由原厂组合尺寸与编码器增量推算，尚未取得对应整机组合 STEP；电缆弯曲、尾端接插件、联轴器、指轴、制动器均未计入。质量下界不含原厂连接法兰及其紧固件。

## 2. 22GPT HT 的真实边界及 CAD

| 字段 | 三级 | 四级（本轮两方案采用） |
|---|---:|---:|
| 连续输出上限 | 2.7 N·m | 3.7 N·m |
| 间歇 / 峰值 | 4 / 10 N·m | 5 / 14 N·m |
| 最大效率 | 70% | 63% |
| 最大连续输出功率 | 8 W | 7 W |
| 齿轮体长 / 质量 | 37.3 mm / 94 g | 43.6 mm / 109 g |
| 连续输入转速上限 | 9000 rpm | 9000 rpm |

四级典型空载回差 0.8°；额定载荷不能以间歇或峰值替代。原厂要求按电机组合供货。依据：[22GPT HT 原厂数据表及尺寸图](https://www.faulhaber.com/fileadmin/Import/Media/EN_22GPT_HT_FCH.pdf)、[330:1 产品页](https://eshop.faulhaber.com/cn/22GPT-HT-330-1/22GPT-HT-330-1)。

采用**仅用于动态预选的假设效率 0.50**：

| 电机 / 比值 | 电机额定扭矩乘比值再乘 0.50 | 齿轮上限封顶后 | 说明 |
|---|---:|---:|---|
| 2214 / 653 | 3.167 N·m | 3.167 N·m | 低于 μ=0.3 示例上指 3.249 N·m |
| 2214 / 829 | 4.021 N·m | 3.700 N·m | 候选；电机所需约 7.84 mN·m，热余量有限 |
| 2250 / 198 | 2.594 N·m | 2.594 N·m | μ=0.3 示例不足 |
| 2250 / 220 | 2.882 N·m | 2.882 N·m | μ=0.3 示例不足 |
| 2250 / 330 | 4.323 N·m | 3.700 N·m | 较快候选 |
| 2250 / 484 | 6.340 N·m | 3.700 N·m | 可降低动态电机负担；不能提高齿轮允许输出 |

表中力矩采用名义速比预估；829:1 的实际速比为 `107811/130 = 829.315384615…`，330:1 为 `330/1`，控制参数应采用实际速比。[FAULHABER 官方速比表 p20](https://www.faulhaber.com/fileadmin/Import/Media/EN_GEARHEADS_REDUCTION_RATIOS.pdf)

0.50 不是原厂效率下限，也不是零速保持效率。停止时应以实测热平衡、反向传动和接触力保持能力判定。

可核查的厂商 CAD：

- [22GPT HT CAD ZIP](https://eshop.faulhaber.com/media/1e/92/df/1755605016/22GPT_HT_3D-CAD.zip)：已检查压缩包目录；有 `22GPT_HT-4stage_standard+KSx.stp`、各轴端选项及 `22GPT_HT_flange_d.stp`。包内 `Specification_flange_for_22GPT_HT_20241112.txt` 将 `22xx...BX4`、`2214...BXT` 指定到 **flange_d**。不能漏掉此法兰。
- [2250 BX4 CAD ZIP](https://eshop.faulhaber.com/media/e2/g0/85/1755618901/2250_BX4_3D-CAD.zip)：内含 `2250S_BX4.stp`；文件是系列 S 外形，不能自动当作所有 X/线缆/编码器组合的最终模型。
- 2214 与编码器 CAD 从 [2214 官方产品配置页](https://eshop.faulhaber.com/en/2214-...-BXT-H/Serie-2214-...-BXT-H) 申请对应实际订单版本。本仓库此处仅记录链接，不把厂商 CAD 重新授权为项目原创文件。

四级前法兰尺寸核图：Ø22；定位止口 Ø16；6×M2、深 3 mm、PCD Ø19、60° 均布；最大拧紧 35 N·cm。标准输出轴 Ø6，单扁位，轴伸 16.3 mm。指根应另设双支承轴，通过有轴向定位的联轴器传扭；不能直接把灯片挂在减速器细轴上承担全部弯矩。轴端 KS7 带轴向螺纹可列询价选项，但最终配合、公差与承扭结构仍需确认。

## 3. 编码器与 EtherCAT：明确需要集成的部分

[IE3-1024 L 原厂图纸](https://www.faulhaber.com/fileadmin/Import/Media/EN_IE3-1024L_DFF.pdf) 给出 1024 线/转、A/B/I 及互补差分输出、TIA-422、4.5–5.5 V、典型质量 13.5 g；需差分接收器和接地/屏蔽设计。BX4 数字 Hall 版本的 Hall 与编码器供电相连，接线必须按订单图纸核对。它测的是电机轴，不直接测指根回差或传动弹性；增量编码器掉电后还需可靠回零，不能对已夹工件盲目撞限位。

| 驱动候选 | 已确认的集成条件 | 未完成 |
|---|---|---|
| FAULHABER MC 3001 B ET + `6500.00494` | MC 是板载模块；EtherCAT 通过附加板，连接客户背板 | 四通道背板、编码器差分接收、24 V 供电与保护、网络连接器、散热、ESI/状态机验证 |
| maxon EPOS4 Micro 24/5 EtherCAT `654731` | OEM 裸模组；有 EtherCAT 也仍需载板和接插件 | Hall/编码器与 7 对极 BXT 的匹配、相电流约定、载板及热设计 |

MC 方案参考 [MC 3001 B/P 技术手册](https://www.faulhaber.com/fileadmin/Import/Media/EN_7000_05071.pdf) 和 [6500.00494 数据表](https://www.faulhaber.com/fileadmin/Import/Media/EN_6500_00494_DFF.pdf)：附加板约 40×40×9.6 mm、10 g，电子侧 3–3.6 V；不能把它直接当成四轴 EtherCAT 驱动器。maxon 参考 [654731 产品页](https://www.maxongroup.com/maxon/view/product/654731) 与 [硬件手册](https://www.maxongroup.com/medias/sys_master/root/8934669221918/EPOS4-Micro-Compact-24-5-EtherCAT-Hardware-Reference-En.pdf)。两条路线都不是开箱即用四指总成，48 V 臂母线也不能直接接 24 V 指驱动。

## 4. 指轴支承

候选 **SKF W 61801**，每根指轴两只，共 8 只：12×21×5 mm，单只 5.4 g，目录基本动额定载荷 1.51 kN / 静额定载荷 0.90 kN。[SKF 官方轴承目录](https://cdn.skfmediahub.skf.com/api/public/094cc500316fc14e/pdf_preview_medium/094cc500316fc14e_pdf_preview_medium.pdf)

采用独立 Ø12 指轴和金属支座，轴承跨距可先以 16 mm 作 CAD 参数；这是设计候选，不是已完成强度选型。目录 C/C0 不是允许横向力的直接承诺。需用真实接触力、皮带张力/锥齿轮推力求轴承反力，并检查配合、轴向定位、支座刚度、低角度往复磨损和密封阻力。双轴承本身不承担绕指轴的驱动扭矩，该扭矩由轴、轮毂和传动接口承担。

## 5. 传动布置备选

### A. 直接切向同轴：首版装配基准

短版按完整 86.4 mm 轴向包络布置，四组在 z 方向错层。体积较大，但传动路径简单。必须加入 flange_d、编码器、独立指轴支承和装配工具空间；装配后再确定头部外径，不先承诺 Ø150×100 mm。

### B. 平行轴同步带：减小横向包络的候选

可先验证 `180-3MGT-09`（Gates `9400-4060`）+ `3MR-30S-09`（`7843-6011`）×2/指，30:30、中心距 45 mm；四指分别传动。[Gates 产品目录](https://www.gates.com/content/dam/documents-library/catalogs/power-transmission-catalog.pdf)

| 几何/计算项 | 结果 |
|---|---:|
| 节距 / 带宽 / 节长 | 3 / 9 / 180 mm |
| 30T 节圆直径 / 理论包角 / 啮合齿数 | 28.648 mm / 180° / 15 |
| 单只目录铝带轮质量 | 0.050 lb ≈ 22.68 g |
| 20 rpm 表值及修正 | 35.6 lb-in × 0.112985 × 1.64 × 0.85 ≈ 5.607 N·m |
| 3.249 / 3.700 N·m 的张力差 | 226.8 / 258.3 N |

修正来自 [Gates Light Power and Precision 手册](https://www.gates.com/content/dam/documents-library/catalogs/light-power-and-precision-manual.pdf) 印刷页 19：6 mm 基准宽度、9 mm 宽度系数及 180 mm 长度系数。该动态目录值不证明零速循环寿命。正常至少 6 齿啮合；本例取 15 齿，不以小轮最小目录齿数代替受力校核。输入带轮必须安装在独立双轴承中间轴上，齿轮箱通过联轴器驱动它，指根轴也单独支承；轴承力还包含预张力。目录带轮是最小孔毛坯版本，需加工成最终轴孔、可靠承扭接口和轴向定位，并校核轮毂。

5MGT 也可用，但 18T 钢轮 `P18-5MGT-15-MPB` 单只约 108.9 g，四对已约 871 g，暂不优先。同步带仍需张紧、反转寿命、柔性误差、线缆和壳内干涉验证。

### C. 轴向电机 + 90° 锥齿轮：本轮不冻结

[KHK SMSG 原厂表](https://khkgears.net/pdf/smsg.pdf) 中，1:1 配对须 R/L 同系列：

| 配对 | 目录弯曲 / 齿面力矩 | 节圆 / 孔 / 单只质量 | 判定 |
|---|---:|---|---|
| SMSG1-20R/L | 1.17 / 0.97 N·m | 20 / 6 mm / 19 g | 不足 |
| SMSG1.5-20R/L | 4.10 / 3.47 N·m | 30 / 8 mm / 74 g | μ=0.3 上指余量很小，四对 592 g |
| SMSG2-20R/L | 7.83 / 6.79 N·m | 40 / 12 mm / 150 g | 齿轮质量已 1.2 kg/四对 |

这些是特定转速、寿命、润滑和刚度条件下的计算参考值，需按 [KHK 选型说明](https://khkgears.net/pdf/2025/miter-gears.pdf) 重算实际工况。8 mm 齿轮孔不能直接装到 6 mm 减速器轴上；需中间轴、轴向推力支承、可靠轮毂连接、齿隙调整和润滑壳体。不能在 CAD 中仅画一对无来源的小锥齿轮就宣布转角传动完成。

## 6. 保持与刹车：没有已放行的轻量即插即用方案

| 候选 | 原厂事实 | 对本项目的实际判断 |
|---|---|---|
| Miki Pulley `BXR-015-10LE-006-C5` + `BEM-24ESN7-120N` | 输入端小制动器：0.06 N·m、Ø26×14 mm、30 g；控制器约 20 g；24 V 过励磁 0.2 s，随后 7 V 保持释放，约 1.4 W | 轻量优先询问原厂集成。标准 C5 孔 5 mm，与两电机 3 mm 轴不匹配；编码器已占后端，不能直接叠上。需原厂可用输入轴、专用轮毂/壳体及联合图纸 |
| Miki Pulley `BXR-050-10LE` 输出端 | 3.2 N·m、Ø71×19 mm、400 g | 低于 μ=0.3 示例上指 3.249 N·m，不能按该边界选择 |
| mayr ROBA-servostop Cobot `80 / 8981.29101` 输出端 | 名义 4 N·m、Ø80、长 20.9 mm、520 g；24 V 过励磁 / 8 V 释放保持 | 4 只已 2.08 kg，且需要自制阶梯轴/转子安装；可作为质量代价参照，排除当前轻头方案 |
| 电机电流保持 | 无新增制动器 | 可用于受保护台架；依赖供电/控制/温升，不提供失电保持 |
| 定制弹簧预紧锁止或夹紧盘 | 尚无完整结构与供应件 | 仅列待研究，不在 BOM 中记成“已实现自锁” |

来源：[Miki 原厂目录 p346–347](https://www.mikipulley-us.com/documents/Catalog/Catalog_Spring_Actuated_Brake.pdf)、[BXR-015 产品页](https://www.mikipulley-us.com/electromagnetic-brakes-e.m./spring-actuated-brakes/bxr-le-model-brake/bxr-le-set-screw-style-hub/bxr-015-10le-006-c)、[mayr 原厂目录 p8–9](https://www.mayr.com/produkte/dokumentationen/bremsen/roba-servostop/p_898000_v06_en_05_10_2023.pdf)。BXR 是保持制动器，日常停车应先由伺服减速，不能当成每次开合的摩擦停车器。

按无摩擦理想反传，仅 3.249/829 ≈ 3.92 mN·m 会折算至短版电机输入端，说明小制动器**力矩量级**可能足够；这不证明可装配，也不能用 `0.06×829` 宣称输出承载 49.7 N·m。载荷仍受 3.7 N·m 齿轮上限、冲击、反传特性、预载和结构限制。保持角度不等于保持软垫夹力；需验证长时间夹力衰减和停电捕获。

## 7. 其他执行器的排除依据

| 候选 | 原厂可核实参数 | 当前结论 |
|---|---|---|
| Actuonix L16-50-150-12-P | 50 mm 行程、56 g、12 V；200 N 最大推力，102 N 反驱门槛，20% 占空比；空载 8 mm/s | 可做慢速轻载机构。20 mm 曲柄要产生 3.249 N·m，即使最佳角度也需 162.5 N，高于反驱门槛；不能当作失电可靠保持。曲柄接近死点时还会失去力臂 |
| ROBOTIS XM540-W270 | 165 g，33.5×58.5×44 mm；12 V 的 10.6 N·m 是堵转值；TTL/RS-485 | 适合快速做动作台架；没有从该堵转数据获得连续 2 kg 夹持证明，且不是 EtherCAT |

来源：[Actuonix L16 官方数据表](https://www.actuonix.com/assets/images/datasheets/ActuonixL16datasheet.pdf)、[ROBOTIS XM540-W270 官方手册](https://emanual.robotis.com/docs/en/dxl/x/xm540-w270/)。L16 的 250 N 最大静载、200 N 最大推力、102 N 反驱门槛是三个不同量；不能互换。

## 8. 可用于参数模型的 BOM 字段

以下是**参数建议**，不是采购 BOM；所有未决字段必须保留为空或 `TBD`，不能填 0。

```yaml
status: candidate_not_frozen
quantity_finger_drives: 4
primary:
  motor_configuration_request: 2214X024BXTH
  gearbox_configuration_request: 22GPT HT 829:1
  encoder_configuration_request: IE3-1024 L
  supplier_combination_order_number: TBD
  nominal_voltage_V: 24
  motor_rated_torque_Nm: 0.0097
  motor_rated_current_A: 0.36
  motor_rated_speed_rpm: 2710
  motor_diameter_mm: 22
  motor_body_length_mm: 14.8
  motor_mass_g: 28.9
  reduction_ratio_nominal: 829
  reduction_ratio_exact_fraction: [107811, 130]
  reduction_ratio_calculated: 829.3153846153846
  gear_stages: 4
  gear_continuous_torque_limit_Nm: 3.7
  gear_max_efficiency: 0.63
  assumed_dynamic_efficiency_for_screening: 0.50
  gear_continuous_output_power_limit_W: 7
  gear_body_length_mm: 43.6
  gear_mass_without_motor_and_flange_g: 109
  gear_factory_connection_flange: flange_d
  encoder_mass_typical_g: 13.5
  motor_encoder_body_length_mm: 26.5
  motor_gear_L1_without_encoder_mm: 58.4
  motor_gear_encoder_body_length_estimate_mm: 70.1
  standard_output_shaft_diameter_mm: 6
  standard_output_shaft_extension_mm: 16.3
  total_length_with_standard_shaft_estimate_mm: 86.4
  body_mass_lower_bound_g: 151.4
  factory_flange_mass_g: TBD
  complete_combination_CAD: TBD
  zero_speed_continuous_torque_verified_Nm: TBD
  brake_model_frozen: TBD
  power_off_holding_verified: false
finger_support_candidate:
  bearing: SKF W 61801
  bearings_per_finger: 2
  bearing_dimensions_d_D_B_mm: [12, 21, 5]
  bearing_mass_g: 5.4
  bearing_span_assumption_mm: 16
  shaft_and_hub_material_and_fits: TBD
assembly:
  primary_layout: tangent_axis_direct_drive_with_z_stagger
  root_radius_assumption_mm: 65
  upper_petal_total_length_candidate_mm: 140
  lower_petal_total_length_candidate_mm: 100
  upper_contact_along_candidate_mm: 90
  lower_contact_along_candidate_mm: 70
  head_mass_budget_candidate_kg: [1.8, 2.2]
  head_envelope_collision_checked: false
```

冻结前应获得组合图纸、完整实重、背板原理图、热验证、接触力标定、停止/断电保持方案和任务节拍；所有性能数字应带测试条件，不能从本候选表直接形成产品宣传规格。
