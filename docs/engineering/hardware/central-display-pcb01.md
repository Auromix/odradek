<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# CD-PCB01 — 中央圆形 LED 板布局布线候选

**318 件元件、285 个 LED 的原生 KiCad 板已完成布线；KiCad 10.0.6 重建回放后 ERC、DRC、未连线、原理图一致性问题均为 0。** 全部 DRC 检查启用，无忽略项或豁免。它仍是工程候选，尚未制造、通电或得到板厂/装配方工艺认可。

[正背面总览](../../../engineering/electronics/central-display-cd01/pcb01/board-overview.png) · [原生 PCB](../../../engineering/electronics/central-display-cd01/pcb01/kicad/central.kicad_pcb) · [原生原理图](../../../engineering/electronics/central-display-cd01/pcb01/kicad/central.kicad_sch) · [验证报告](../../../engineering/electronics/central-display-cd01/pcb01/kicad/checks/verification.json) · [未过滤 DRC](../../../engineering/electronics/central-display-cd01/pcb01/kicad/checks/drc.json)

## 固定接口与重建边界

Ø60 × 1.0 mm 板，285 个 LED 的 XY、GH12 配对位置和针序、318 元件的 726 个引脚连接与父 CD-EC01 一致；716 个有网络引脚完成原生 XML/PCB 回读。CD-EC01 的元件型号、像素地址与固件初始化继续作为电气权威，本板没有重新映射灯点。LED_POWER4 名称中的 4 是支路序号，额定电压是 **3.3 V**。

PCB 位于头坐标 Z −3…−2 mm；正面 LED 按最大 0.8 mm 本体 +0.1 mm 焊高规划至 Z −1.1 mm。焊高是装配规划量，不是制造公差。GH12 使用专门依据官方 12 针安装图生成的封装，未通过改名复用 10 针焊盘；原点 (0,−14,−3)，安装面变换 X=−u、Y=−14+v、Z=−3−h，实测原生焊盘回读与该契约一致。

本目录仅读取冻结父基线，不调用父级 build.py 或改写父文件。固定布线已存入带源网表/封装哈希的 `kicad/routing-plan.json`；重建会拒绝不匹配的源数据，重新执行原生 ERC/DRC 和回读。早期未布通路由及临时会话文件留在库外工作区，不包含在交付中。

在仓库根目录运行，参数替换为本机 KiCad CLI 和带 pcbnew/wx 的 Python 路径：

```sh
python3 engineering/electronics/central-display-cd01/pcb01/rebuild.py \
  --kicad-cli /path/to/kicad-cli \
  --kicad-python /path/to/kicad-python
```

[完整执行记录](../../../engineering/electronics/central-display-cd01/pcb01/cli-report.json) 给出实际版本、命令和返回码。ERC 的 4 个原生默认忽略项在报告中明列（单次全局标签、四向节点、SPICE、封装过滤器），无自定义 ERC 豁免；DRC 则连原生默认忽略项也已启用，最终忽略列表为空。

## 铜层与真实装配间隙

| 从前到后的铜层 | 用途 |
|---|---|
| F.Cu | LED 阵列与局部 SW/CS 引出 |
| In1.Cu | 矩阵及控制线 |
| In2.Cu | 专用 GND，不布信号线；填铜回读为单一连通域 |
| In3.Cu | 矩阵及控制线 |
| In4.Cu | 矩阵及控制线 |
| B.Cu | 双 LP5860、电源、去耦及其引出 |

这证明 GND 图形连通，不代表已测得回流阻抗、EMC 或完整信号完整性。尚未指定实际板厂、材料和每层介质厚度；名义外铜 35 µm、内铜 17.5 µm 用于压降估算，成品最小厚度与层间配对要在制造时确认。

本板采用 **0.127 mm 最小线宽/铜间距、Ø0.40/0.20 mm 通孔** 的独立工艺候选。名义环宽 0.10 mm；孔到铜规则 0.227 mm 为名义环宽加铜间距，孔边到孔边 0.254 mm。实际钻孔补偿、成品孔、最小残余环宽、孔铜与层对准必须由制造方审查，不能套用目录通用孔公差后声称成品环宽已闭合。[JLCPCB 六层板能力](https://jlcpcb.com/6-layer-pcb)、[制造能力](https://jlcpcb.com/capabilities/Capabilities)、[中文工艺要求](https://www.jlc.com/portal/1/serviceGuide) 提供工艺范围依据；页面细项不完全相同，本项目尚未指定供应商或下单。

| 固定 2.8 mm LED 阵列的独立检查 | 名义最小值 |
|---|---:|
| 最大实体 1.7 ×0.9 mm 之间 | 1.10 mm |
| 相邻元件的保守铜焊盘联合包络之间 | 0.40 mm |
| 阻焊开窗之间，单边扩 0.05 mm | 0.30 mm |
| 专用 2.7 ×1.2 mm courtyard 之间 | 0.10 mm |
| QFN 相邻引脚铜间距 / 阻焊桥 | 0.20 / 0.10 mm |

专用 courtyard 没有改变任何 LED 的 XY、铜焊盘或本体尺寸。较小 courtyard 仍需装配方接受；阻焊颜色、对准能力、印刷与贴装公差未冻结。详细计算见 [DFM 证据](../../../engineering/electronics/central-display-cd01/pcb01/dfm-evidence.json)，原始逐层铜、阻焊、焊膏、丝印 SVG 位于 `kicad/plots/layers/`。总览为了阅读隐藏了正面密集 LED 位号，原始图层和定位 CSV 保留全部位号。

453 个通孔全部为 Ø0.40/0.20 mm。**LED 盘中孔为 0**；19 个通孔的铜环与背面 SMD 铜焊盘重叠，包括 8 个 LP5860 EP 孔和 11 个无源件附近孔。其中 14 个钻孔本身与铜焊盘相交，19 个与扩后的阻焊开窗相交。逐孔坐标、网络和关联焊盘已回读登记。

这 19 个位置保守要求**树脂填孔、盖铜和平整度审查**；普通通孔符号、默认双面盖油不表达这些制造步骤，普通阻焊塞孔不能替代。其余 434 个孔在该检查中没有 SMD 铜环重叠；制造方可评估全板填孔或受控选择性工艺。EP 四块焊膏窗合计约 55.2% 名义面积，填孔、盖铜厚度、钢网、空洞率和回流流程仍需装配确认。

## 背面 33 件的 MCAD 接口

[mechanical-interface.json](../../../engineering/electronics/central-display-cd01/pcb01/mechanical-interface.json) 是本版实际坐标入口：每件含头坐标原点、安装面 u/v/h 到头坐标的三维旋转矩阵、原生 KiCad 旋转，以及**独立的本体与规划包络**。`max_body` 是 32 件普通器件的厂家公布最大尺寸包围盒；GH 的 `max_body=null`，仅有 `mated_reference` 目录配对参考盒。`mcad_material_envelope` 为两者的带类型统一入口。`planning_envelope` 与旧 `envelope_head_*` 字段是含 PCB 焊盘及装配余量的规划集合，**不能当成同高的实体材料**。[component-positions.csv](../../../engineering/electronics/central-display-cd01/pcb01/component-positions.csv) 含全部 318 件回读坐标。**左侧安装不能镜像 PCB 或交换引脚。**

为保持去耦热端朝向芯片并释放 QFN 出线，只有以下 8 个背面电容改变了父方案占位；其余位置包括 U1/U2 和 GH12 均不变。旋转列是封装投影旋转，完整三维变换以 JSON 为准。

| 元件 | 头坐标 X / Y，mm | 投影旋转 |
|---|---|---:|
| C4 / C13 | −6 / 6.7；14 / 6.7 | 180° |
| C7 / C16 | −3.2 / 6.5；16.8 / 6.5 | 180° |
| C5 / C14 | −11.4 / 8.0；8.6 / 8.0 | 90° |
| C8 / C17 | −8.6 / 8.0；11.4 / 8.0 | 90° |

所有背面保守包络角点 R≤21.6172 mm，最低 GH 候选包络 Z=−7.45 mm，落在 R28、Z−10…−3 的预留内；33 件包络两两无重叠。普通元件包络包含最大本体/焊盘联合包络与单边 0.25 mm 装配余量，GH 使用目录配对联合包络并额外加 0.10 mm 焊高预算。本体盒不含 XY 余量、不含 PCB 铜焊盘/院界，沿安装 h 方向平移 0.10 mm 表示焊高规划；它不是焊料实际形状。32 件本体最大盒加 1 件 GH 配对参考盒亦两两无交叠，全部包含于各自规划集合内。尺寸和出处见 [package-body-dimensions.json](../../../engineering/electronics/central-display-cd01/pcb01/package-body-dimensions.json)：LP5860 为 5.1×5.1×1.0 mm，22 µF 为 2.2×1.45×1.45，三种 0603 电容为 1.7×0.9×0.9，CRCW0603 为 1.65×0.95×0.50，NTC 为 1.75×0.95×0.95。GH 仍是 18.25×7.15×4.35 mm 目录参考框；增加焊高后最低 Z−7.45。这些不是厂家 BREP 或整套制造公差证明；实际压接线、锁扣操作、拔插工具、板翘曲及整头碰撞要由下一轮 MCAD 检查。

头坐标 (−10,15)、(10,15) 各预留 4×4 mm 背面 GND 铜区，不放元件或通孔。其作用是给后续导热构件留接口；没有据此虚构已完成的热桥或散热性能。

## 电源、热与尚未完成的验证

两片 LP5860 的 VLED/VCC/VCAP/VIO 去耦先在背面局部接通，对应 GND 焊盘通过通孔回到 In2。VLED 正电源全网所有线段假设串联的保守铜阻上界约 **0.2797 Ω**；按条件上限 0.52 A 得 **0.1455 V**，3 mA 首亮档对应约 **0.0218 V**。这是 20°C、名义外铜 35 µm/内铜 17.5 µm 的线段估算，排除了过孔、焊盘、回流、接头、线束、温升和动态寄生，不能当实测电源压降。

默认仍为 3 mA 首亮；20 mA 需要电热测试后显式启用。父预算的中央板 1.81 W 工程规划、四灯片 2.264 W 基线、合计 4.074 W 保持不变；未包括相机、电机与头控制器。电流误差、MLCC 偏压降容、3.3 V 源阻抗、扫描脉冲纹波、LED/驱动温升、SPI 边沿及长线电源压降都需实测。不能由 ERC/DRC 为零推导这些物理性能成立。

当前交付为原生设计、回放脚本、源映射、真实检查和审查图层，**没有生产放行**。尚未得到具体叠层、填孔盖铜、钢网/装配、线束与散热认可；未采购、未制造、未通电。

回放保证来源匹配的元件、网络及铜几何，而不承诺跨运行逐字节相同：KiCad 载入封装时可能新建子对象 UUID，ERC/DRC 报告也有运行时间。每次重建应以当次 `verification.json` 记录的板和文件 SHA 为准；不可把上一轮 SHA 自动套到新输出。导出网表只把 `<source>` 的机器绝对路径归一化为项目相对路径，未修改 pin/net 或原生 ERC/DRC 诊断。
