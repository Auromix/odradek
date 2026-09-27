# HEAD-CTRL02：P16 条件分支的头部控制电路

本版完成 **STM32G474VET6 的 100 脚分配、242 件元件级候选网表及原生 KiCad 原理图**。KiCad 10.0.6 ERC 为 0，833 个已连接脚与导出 XML 一致；完整结果在[验证报告](../../../engineering/electronics/head-ctrl02/kicad/checks/verification.json)。这不是已送板、已通电、已认证或已验证能抓取 2 kg 的控制器。

本版只适用于[四路 P16 直流推杆候选](../p16-control-interface.md)：7 个 RH 本体从站加 1 个 LAN9252 头部从站，共 8 站。旧四个 BLDC EtherCAT 伺服驱动的 12 站分支仍单独保留，二者没有混入同一个电路。两只 GMSL2 相机的视频/PoC 绕过本控制器；本板不处理视频。

## 交付入口与复现

- [原生原理图](../../../engineering/electronics/head-ctrl02/kicad/head.kicad_sch)、[矢量原理图](../../../engineering/electronics/head-ctrl02/kicad/plots/head.svg)：A0 图，放大查看。
- [100 脚 pinmux](../../../engineering/electronics/head-ctrl02/pinmux.csv)、[逐脚网表](../../../engineering/electronics/head-ctrl02/pin-net.csv)、[逐件 BOM](../../../engineering/electronics/head-ctrl02/bom.csv)。`functional_reference` 保留功能名，`ref` 是原生数字位号。
- [控制与接口契约](../../../engineering/electronics/head-ctrl02/control-contract.json)、[计算](../../../engineering/electronics/head-ctrl02/calculations.json)、[官方证据](../../../engineering/electronics/head-ctrl02/sources.json)。

在仓库根目录运行：

```sh
KICAD_CLI=/path/to/official/kicad-cli python3 engineering/electronics/head-ctrl02/rebuild.py
```

依次重建候选、运行带 `--exit-code-violations` 的 ERC、导出 XML/SVG，再做独立针脚断言与哈希记录。没有自定义 ERC 排除项或被改为忽略的电气错误。KiCad 默认不检查的单次全局标签、四路结点、SPICE 模型、封装过滤器四类也原样列在报告中；本版没有进行 SPICE 仿真。原理图的 `Footprint` 尚不赋值，候选封装记录为 `CandidateFootprint`；此前未解析封装库产生的警告已通过撤销未冻结的封装赋值解决，没有隐藏检查。**本版无 PCB，所以无 DRC、Gerber、贴片坐标或板尺寸放行。** 0603 等只是元件包络建议，电容的偏压/温升/纹波与具体采购料号仍须闭合。

## MCU 与外设分配

此前 STM32G474RET6 是 64 脚台测候选；本版占用 64 个非电源脚（含复位、调试、使能和监视脚），且需要更多同时可用的 ADC/TIM/SPI 路由，因此改为 **STM32G474VET6、LQFP100、512 KB Flash**。这次没有修改此前 BOM。脚号和 AF/ADC 依据 [ST DS12288 Rev 6 的 Table 12/13](https://www.st.com/resource/en/datasheet/stm32g474ve.pdf)核对，包括容易误读的 PB11=50、VSS=48、VDD=49、PB8/BOOT0=95。

| 功能 | 分配 | 默认/边界 |
|---|---|---|
| EtherCAT SPI1 | PA5/6/7，AF5；PA4 片选 | 2 MHz 初始候选；片选上拉 |
| LED SPI2 | PB13/14/15，AF5 | 六个独立 CS，不能同时选中 |
| 四路 PWM | PD12…15，TIM4 CH1…4，AF2 | HSI16 时 PSC=0、ARR=799，名义 20 kHz；先 CCR=0 再切 AF |
| 四路 PH / nSLEEP 请求 / nFAULT | PD8…11 / PD0…3 / PD4…7 | 请求默认低；故障脚轮询，不抢占 EXTI6/7 |
| 四个位置 / 电流 | PC0…3：ADC1 IN6…9；PA0…3：ADC1 IN1…4 | 模拟输入、无内部拉电阻；分别有滤波与掉电隔离 |
| 四瓣 NTC / 中央 NTC | PE7/8/9/10：ADC3 IN4/6/2/14；PE13：IN3 | 远端已有分压，不重复上拉 |
| 12 V / LED 3.3 V 监测 | PE11/12：ADC3 IN15/16 | 分压后经过第二颗 TMUX1511 |
| ESC IRQ / SYNC0 / SYNC1 | PC7/EXTI7、PC6/EXTI6、PC8/EXTI8 | IRQ 默认开漏低有效；SYNC 是输入 |
| 六个 LED CS | PE2/3/4/5/6、PC10 | 上右、上左、下左、下右、中央 A、中央 B |
| LED VSYNC / VIO 请求 | PC11 / PC12 | VIO 电流由负载开关提供 |
| 调试 | PA13/14 SWD；PB3 SWO；PA9/10 USART1 AF7 | 调试器 VTREF 仅检测，不向板供电 |

初始 MCU 使用内部 HSI16，未装 HSE/LSE 晶体。ADC 候选每秒 500 组、长采样时间 247.5 周期；实际 ADC 时钟、采样建立、DMA/DMAMUX、误差校准和执行时序尚未作为运行固件交付。备用脚在 CSV 中明确 NC。必须读回启动选项，保持 PG10 的复位作用并审核 PB8 启动策略。

## EtherCAT 不能只接 SPI

**LAN9252I/PT** 为 64 脚 TQFP-EP。13/17/19/50 分别接 SO/SI/SCK/SCS；REG_EN 接 3.3 V，内部 1.2 V 输出经独立滤波送 PHY，绝不把 VDDCR/OSCVDD12 当作 3.3 V 输入。原理图包含每个电源脚的旁路、12.1 kΩ RBIAS、铜缆模式和双端口模式的电阻绑带。内部稳压器 pin 6 的 1 µF/470 pF 与约 0.1 Ω ESR 要求保留为具体器件/稳定性验证项。[LAN9252 数据手册](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/LAN9252-Data-Sheet-DS00001909.pdf)

CHIP_MODE=00 选择两铜口，**并不选择 SPI PDI**。SPI 类型 0x80 需由有效 SII 配置加载到 ESC 的 PDI Control 0x0140；不能把 0x0140 当 EEPROM 地址。24FC512-I/SN 的 A0…2 接地，地址 0x50，WP 默认高，维修跳线才允许写入。当前没有伪造 Vendor ID、生产 ESI、PDO/看门狗配置或可烧录 EEPROM 镜像。[Microchip EEPROM](https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA512-24LC512-24FC512-512-Kbit-I2C-Serial-EEPROM-DS20001754.pdf)

25 MHz 选 **ASTX-H12-25.000MHZ-T** HCMOS TCXO 候选，OSCO 留空。公开参数的初始、温漂、电源、负载与首年老化相加约 6 ppm，低于 EtherCAT 25 ppm 总预算；长期老化、实际负载、焊接偏移和当前生命周期仍要确认。逻辑电源合同为 3.3 V±3%，这样目录 VOL 上界约 0.340 V，才落在 LAN OSCI 的 0.35 V 低电平上限内，不能直接沿用 TCXO 宽至 3.63 V 的供电范围。[Abracon 官方资料](https://abracon.com/Oscillators/ASTX-H12.pdf)

**TPS3808G33DBVR** 监督 3.3 V，CT 通过 100 kΩ 拉高，180…420 ms 复位延时；LAN 所有相关电源与时钟稳定后仍需至少 25 ms。保守留出的其余建立窗口约 155 ms，必须实测。SYS_RESET_N 经 **SN74LVC2G07DCKR 双开漏缓冲**分成 MCU_RESET_N 和 ESC_RESET_N。MCU/调试器较短复位脉冲不会直接注入 LAN；PC9 可以独立拉低 ESC_RESET_N 至少 1 ms。ESC 复位同时撤销硬件电机许可，固件必须锁存禁止并重新握手，不能在复位释放后自动续动。此修订修复了最初“全部复位脚短接”无法保证 LAN ≥200 µs 输入脉宽的缺口。[双开漏缓冲资料](https://www.ti.com/lit/ds/symlink/sn74lvc2g07.pdf)、[TPS3808](https://www.ti.com/lit/ds/symlink/tps3808.pdf)

双端口用 **Pulse J0011D01BNL** 集成磁性 RJ45 作台架候选；TD±/RD±、TXCT/RXCT、49.9 Ω 终端及 22 nF 按[官方 EVB Rev B 第 5 页](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/BoardDesignFiles/lan9252-hbispigpio-evb-rev-b.pdf)重新绘制。屏蔽与逻辑地间暂为可复核的台架 0 Ω 联接，未认证为 PE/EMC 方案。该 RJ45 目录温区 0…70°C，不能因 MCU/ESC 是工业温级就宣称整板 −40…85°C。内置 RH SH1.0 接头的厂商与受控针脚视图未闭合，因此没有直接发明一条 RH 到头板转接线。

## 四路驱动、电流测量与默认状态

每路 **DRV8874PWPR** 含 22 nF CPH—CPL、100 nF VCP—VM、VM 100 nF 与 10 µF 候选去耦、EP/PGND 回流、故障上拉和输入下拉。PMODE=GND，IMODE 有意浮空。**OUT1 与 OUT2 都接电机，OUT2 不是 GND。** REF3125AIDBZR 提供 2.5 V；其启动、输出电容与四路负载仍需台测。[DRV8874](https://www.ti.com/lit/ds/symlink/drv8874.pdf)、[REF31](https://www.ti.com/lit/gpn/REF31)

四路 nSLEEP 的逻辑为：

```text
nSLEEP[i] = SLEEP_REQ[i] AND MCU_ARM AND EXT_PERMIT AND SYS_RESET_N AND ESC_RESET_N
```

用一颗 SN74LVC08A 和单门 SN74LVC1G08 实现，所有请求默认拉低。EXT_PERMIT 只是 **0/3.3 V 本地原型联锁**，不能接 24 V，也不是 STO、安全继电器或经验证的停机链。EN=0 是两端拉低的电制动，nSLEEP=0 是高阻滑行；失电能否保住工件仍未知。IWDG、失链时限、故障恢复与反向间隙尚待固件及单指台测。

IPROPI 不能直接进 ADC，也不能仅凭内部钳位的文字说明假定其瞬态安全。本版采用：

```text
IPROPI ──100k── I_DIV ──TMUX1511── I_ADC
   │             │                    │
 6.49k          100k                 100k || 10nF
   │             │                    │
  GND           GND                  GND
```

TMUX 选择信号直接来自监督器 SYS_RESET_N，避免普通逻辑门在低电压未定义区提前接通 ADC；MCU 不直接改变隔离开关状态。与旧 P16CTRL01 的裸 6.19 kΩ 不同，必须把支路负载算进限流：导通等效约 **6220.85 Ω**、ADC 比例约 1/3、静态 Itrip **0.89305 A**；按基准整板±1%、所有电阻±0.1%、驱动电流增益±7.5%求角落为 **0.82162…0.97610 A**。隔离关闭时约 0.88380 A。隔离状态改变时必须保持电机禁止；供电有效后至少等候 2 ms 滤波建立。

用 DRV 的 5.75 V **绝对最大应力界限作保护算术检查，绝不把它当运行目标**：隔离关闭时 I_DIV≤2.878 V，低于 TMUX 掉电允许的 3.6 V；导通后 ADC 约≤1.92 V。TMUX 掉电泄漏最大±2 µA，与 100 kΩ 形成约 0.2002 V 的正向预算。负向泄漏、MCU 输入漏电叠加、非零供电过渡、ESD和接错电机线未由这组静态数证明，均需测量；该网络不是隔离栅或任意过压保护器。[TMUX1511](https://www.ti.com/lit/ds/symlink/tmux1511.pdf)

ADC 电流滤波约 0.340 ms，属于诊断。电容瞬时加载会改变 IPROPI 比较支路，斩波消隐/去毛刺还会产生超调；静态 Itrip 不是峰值保证，更不能转译成抓力。位置电位器由同一 3V3_A 激励，1 kΩ/10 nF 加 1 MΩ 弱下拉使断线趋零；弱下拉造成负载误差，需逐轴端点校准。反馈断线/短路、盲目寻零和任意掉电序列还未完成测试。

## 灯片与电源接口

J11…J14 对应 FPL01 四片 GH10，针序与已交付灯板逐脚自动核验；上两片各 130 点、下两片各 42 点。J15 为中央两颗 LP5860 的 GH12 候选，额外 pin 11 是第二个 CS，pin 12 是地。中央圆形像素板本身尚未设计，不能把本头板原理图当它的 PCBA。

VIO 由一颗 **TPS22919DCKR** 控制，五个 VLED 分路另有五颗开关；MCU GPIO 只驱动 ON。该器件的自保护不能当作 GH 1 A 线束的协调保险。VIO 关断前先把 SPI/CS/VSYNC 置低或高阻，上电时片选先保持高阻，待 VIO 有效后才拉高并初始化全黑。现阶段不支持热插拔。[TPS22919](https://www.ti.com/lit/ds/symlink/tps22919.pdf)

FPL 的 47 kΩ/NTC/1 kΩ/100 nF 已在灯片，头板不重复上拉；中央需实现同一温度接口。2 MHz、60 Hz 传六颗 LP5860 的 2376 字节完整帧，仅载荷已用 57.024% 时间，还没有计指令/读回与抖动。四灯片 **2.264 W** 基线保留；中央另加约 0.5182 A VLED 预算，总瞬态 VLED 约 1.6 A。首亮仍从 3 mA 开始，20 mA、亮度温控和密闭头部温升必须实测。[LP5860](https://www.ti.com/lit/ds/symlink/lp5860.pdf)

| 口 | 候选 | 电气合同 |
|---|---|---|
| J16 12 V | B6P-VH / VHR-6N | 1=VM，2=GND，3…6 NC；用六位外形区别二位电机口，防错能力尚需实体确认 |
| J17 逻辑 3.3 V | B3P-VH / VHR-3N | 1=3V3_LOGIC，2=GND，3 NC；±3%，外部 1 A 规划源 |
| J18 LED 3.3 V | B4P-VH / VHR-4N | 1=3V3_LED，2=GND，其余 NC；±3%，独立外部 3 A 规划源 |
| 四个电机口 | B2P-VH / VHR-2N | 1=OUT1，2=OUT2；不同于 P16 原厂五芯插头 |
| 四个电位器口 | BM03B-GHS-TBT / GHR-03V-S | 1=低端，2=滑端，3=高端；需核实原厂线色与针1后制作适配线 |
| 四片灯 / 中央 | BM10B-GHS-TBT / BM12B-GHS-TBT | 分别配 GHR-10V-S / GHR-12V-S、SSHL-002T-P0.2 |

VH 端子候选 SVH-21T-P1.1，具体线规/工具与压接拉力测试未完成。GH/VH 候选均能在 [JST GH](https://www.jst-mfg.com/product/index.php?lang=2&series=105)和[VH 官方目录](https://www.jst-mfg.com/product/index.php?lang=2&series=262)核查。Pin 编号是板端针号，不能把线色当作对插视图；多极外形不同也未被写成已通过防误插试验。

这轮没有把 24→5→3.3 V 电源级虚画成已经完成。输入来自外置、受控且限流的独立稳压源；电源级、保险/浪涌/反接与线束保护应与真实板栈共同定型。12 V 四路电机故障情景沿用 4.028 A、加 25% 为 5.035 A 的规划预算，外置 LRS-75-12 仍是候选。

1000 µF 从 12→15 V 只有 **0.0405 J**，不是回生吸收结论；15 V 是 P16 上限，不是钳位设定。板上没有声称 TVS 可以吸收未知能量。电容 MPN/纹波、负载回灌、主动泄放、源能否吸收电流和熔断配合未闭合前，**仅允许逻辑/LED 受限台测，电机动力阶段保持不放行**。

## MCAD 和下阶段边界

已读取[HEAD-CTRL-VOLUME01 空间预留](../../../engineering/generated/head-control-volume01/study.json)：头坐标 X±28、Y±32、Z−113…−83 mm，总 56×64×30 mm。每层 50×58 mm 只是可行性目标；两层分为逻辑/ESC与驱动/电源是建议，板间连接器尚未定义。当前原理图是统一逻辑网络，不是已经划分好的两张可叠 PCB。

RJ45 本体、VH 配对高度、GH 出线、1000 µF 实物、支柱/绝缘/热桥都必须算在上述体积内；每侧 3 mm 边余量显然不足以自动容纳侧插线束。下一版可能改用朝 Z 的接口、减小板形、使用独立磁性接口或压缩连接器数量，均需电气和机械重新审核，不擅自给本轮放置图背书。电源地使用低阻连续参考面，在桥和电源入口控制大电流环路，模拟回流在器件本地接地；没有以人为割裂地平面替代真实回流设计。

RH 更新已合入边界：[原厂证据](../rh-operation-evidence.md)指明带 B 制动模块由自身 DC 口供电，**本板不输出外置 24 V 抱闸电源；J7 RH14 N 没有抱闸**。本原型门控也不代表 RH 已具有经过证实的 STO/SBC。

余下必须闭合：SII/ESI与栈看门狗、分板/板间针序、全部元件完整 MPN与温漂偏压、正式封装、受控 PCB 回流与热设计、配对线束、掉电与短路保护、回生与单指标定。ERC 的作用只限于本次针脚类型与网络一致性，不能替代上述工作。

原创电路与分析：CC BY-NC 4.0。Odradek — Auromix contributors（https://github.com/Auromix/odradek）。厂商文档与器件商标沿用原权利，不并入本仓库许可证。
