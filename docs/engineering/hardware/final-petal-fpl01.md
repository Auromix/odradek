# FPL-01 上下灯片原生 ECAD 候选

上下两板已完成实际布线及从源文件重建：上片 130 个 LED、151 个电气器件，下片 42 个 LED、63 个电气器件；另外各有 3 个板内安装孔。KiCad 10.0.6 原生 ERC、DRC、未连线和原理图/PCB 一致性均为 0 项，针脚网表分别 351 / 175 条逐项一致，C99 模拟传输检查通过。所有结果为数字设计检查，尚未上电或制造放行。

[源文件与完整复现说明](../../../engineering/electronics/final-petal-fpl01/README.md) · [实际重建记录](../../../engineering/electronics/final-petal-fpl01/rebuild-report.json) · [机械接口候选](../../../engineering/electronics/final-petal-fpl01/mechanical-interface-candidate.json)

| 项目 | 上片 | 下片 |
|---|---:|---:|
| 灯点 | 130 | 42 |
| 原理图器件数（不含安装孔） | 151 | 63 |
| LP5860 有效 CS | 18 | 13 |
| 扫描配置 / 有灯 SW 数 | 11 / 11 | 11 / 4 |
| 20 mA 时最大同时亮灯数 | 14 | 13 |
| VLED 峰值 / 平均电流 | 280 / 236.364 mA | 260 / 76.364 mA |
| 每板输入预算（含 0.05 W 逻辑） | 0.830 W | 0.302 W |
| 过孔数（含 4 个 QFN 热过孔） | 230 | 142 |
| 焊盘相交过孔待填孔/铜帽工艺确认 | 22 | 24 |
| 原生 ERC / DRC / 未连 / 一致性问题 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |

四片合计 2.264 W 基线，中央点阵及控制板另计。每板独立的 BOM、原理图、板、寄存器及 LED 坐标表放在 `upper/`、`lower/`；不要沿用 ULP-02 的 113 点帧表。

![FPL-01 原生板审查视图](../../../engineering/electronics/final-petal-fpl01/board-overview.png)

图中独立缩放；后视仅显示镜像，电路板未镜像。

## 原生板与验证

- [上片原理图](../../../engineering/electronics/final-petal-fpl01/upper/kicad/petal.kicad_sch)、[上片 PCB](../../../engineering/electronics/final-petal-fpl01/upper/kicad/petal.kicad_pcb)、[上片检查](../../../engineering/electronics/final-petal-fpl01/upper/kicad/checks/verification.json)、[上片几何/极性/电阻审计](../../../engineering/electronics/final-petal-fpl01/upper/kicad/checks/native-board-audit.json)。
- [下片原理图](../../../engineering/electronics/final-petal-fpl01/lower/kicad/petal.kicad_sch)、[下片 PCB](../../../engineering/electronics/final-petal-fpl01/lower/kicad/petal.kicad_pcb)、[下片检查](../../../engineering/electronics/final-petal-fpl01/lower/kicad/checks/verification.json)、[下片几何/极性/电阻审计](../../../engineering/electronics/final-petal-fpl01/lower/kicad/checks/native-board-audit.json)。

开发中的四层布线保留完整地层后仍有拥塞，最终使用六层工程候选：F / In1 / In3 / In4 / B 可走线，In2 专用于 GND。两板 In2 填充各为一个连续铜岛，未放置信号线。名义总厚仍是 0.8 mm，但各介质、铜厚、阻抗和生产厚度公差没有与板厂冻结；此阶段未输出声称可直接投产的 Gerber。没有降低 0.15 mm 线宽/间距或用 DRC 排除项掩盖错误。KiCad 自身默认未启用的可选检查在原始报告中列明，不声称全部可选规则均启用。

按 20°C、35 μm 候选铜厚估算，把同一网络所有线段作为串联上界，上片 VLED 迹线压降约 32.2 mV、最大 SW 上界 74.9 mV；下片相应约 20.1 mV 和 47.9 mV。此模型不含过孔、焊接接触、地回路或升温，不能当成整网电压仿真。上片 LP5860 VLED 引脚到 C3 的直线为 6.4 mm、0.15 mm 宽；下片 2.9 mm。特别是上片去耦回路，仍需测电源瞬态和鬼影，不能从 DRC 推断高频性能。

## 机械协同

保留机械适配研究的所有点位、板轮廓与安装孔。上板 U1 在 X80；下板 U1 在 X56。普通背面件当前布局已与 HEAD-INTEGRATED03 候选包络协同，但其电气 CSV 快照不是最终灯点地址权威；最终地址以本目录 `mapping-revision.json` 和 `register-plan.json` 为准。两个放置表物理数据未再移动。

侧插正锁 GH 采用 `SM10B-GHS-TB(LF)(SN)` 与 `GHR-10V-S`，导线朝 −X。依据 [JST GH 官方目录](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf) 重建 10 个信号焊盘与 2 个固定焊盘；底面翻转后的全部 12 个中心坐标与机械定义相差小于 1 μm。配对框 X39.425…46.575、Y±7.875、Z−0.75…3.6 仍是目录参考包络，没有受控公差/样件插拔验证。左右机械模块安装同一电气板时不能镜像铜层或引脚。

PCB Z3.6…4.4，正面 LED 最大本体 0.8 mm 加规划焊高 0.10 mm，顶面 Z5.3；到透光件下表面的混光间隙 0.7 mm。C1/C2 背面最低 Z2.05，局部底腔 Z1.8，名义间隙 0.25 mm；实际装配厚度与焊高待测。背面 X62…66、Y−7…−3 保留无器件/信号/过孔的地铜区，但到金属仍有 1.7 mm，绝缘导热界面未设计；尤其上板该区远离 X80 的 U1，不能声称已经形成导热桥。

## 上电与剩余边界

例程先设置 3 mA、全黑及主亮度 0，读回成功后才完成启用；20 mA 是明确独立的修改序列。C99 测试覆盖全部拟装灯点的帧地址、未装位置置零、初始化命令和回调失败，但没有实物 MCU/线束/LP5860 测试。先以限流电源和低速 SPI 验证暗态、寄存器与单点，再按图案分级增加电流并记录电源纹波、温升与光学表现。

生产前仍需确认六层 0.8 mm 工艺、铜厚及孔铜，22/24 处焊盘相交过孔的填孔铜帽平整度、QFN 钢网与焊接，JST 受控配对尺寸和压接线束，实际焊高/装配公差、去耦瞬态与温升。板通过数字检查不意味着整头照明、夹持能力或相机系统已经通过验证。

CC-BY-NC-4.0 · Odradek — Auromix contributors
