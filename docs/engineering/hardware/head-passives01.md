<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek) -->
# HEAD-PASSIVES01：末端控制器被动元件与调试接插件

**2026-09-27，元件选型增量；不是 PCB 或采购放行。** 为冻结的 [HEAD-CTRL02](head-ctrl02.md) 补齐原先 193 个 MPN 待定位置：106 个电阻、84 个电容和 3 个调试跳线座，使用 23 种板上料号，另配 1 种松散跳线帽。合并清单的 242 个位置均有具体 MPN；原理图、连线与电阻/电容名义值没有改动。**有 11 个位置必须改变原封装占位，不能直接把这份表交给贴装厂。**

- [逐位置变更及原针脚网络](../../../engineering/electronics/head-passives01/selection-overlay.csv)
- [合并后的 242 位置选型 BOM](../../../engineering/electronics/head-passives01/bom-selected.csv)、[23 种新增板上料号汇总](../../../engineering/electronics/head-passives01/parts-grouped.csv)、[松散维修附件](../../../engineering/electronics/head-passives01/service-accessories.csv)
- [逐 PN 原厂规格、尺寸与来源哈希](../../../engineering/electronics/head-passives01/catalog.json)、[可复算数值及输入哈希](../../../engineering/electronics/head-passives01/selection-check.json)

“有料号”与“本电路已验证”分别记录。单价、渠道库存、热性能、贴装焊盘、控制板分层和头内装配尚未全部确认。厂商 PDF 留在本地研究目录；仓库保存原厂链接及可取得文件的 SHA-256，不重新分发厂商图纸。

## 1. 电阻收敛

以下均为 0603；除零欧跳线外，所选逐 PN 规格的额定功率为 0.1 W @70°C，本体最大 1.7×0.9×0.55 mm。普通 RC 为 ±1%、±100 ppm/K；RT 为 ±0.1%、±25 ppm/K。所有 100 kΩ 统一 RT 精密系列，避免相同阻值在采样分压位置装错精度。完整每个位置见 CSV。

| 阻值 | 料号 | 数量 | 说明 |
|---|---|---:|---|
| 10 kΩ | RC0603FR-0710KL | 24 | 上拉/下拉等 |
| 33 Ω | RC0603FR-0733RL | 13 | 数字信号串联 |
| 47 kΩ | RC0603FR-0747KL | 24 | 上拉/下拉等 |
| 12.1 kΩ | RC0603FR-0712K1L | 1 | 保留原电路用途 |
| 4.7 kΩ | RC0603FR-074K7L | 2 | EEPROM 总线上拉 |
| 49.9 Ω | RC0603FR-0749R9L | 8 | 以太网端接，仍需回流/波形校核 |
| 1 kΩ | RC0603FR-071KL | 4 | 位置采样输入 |
| 1 MΩ | RC0603FR-071ML | 4 | 保留原电路用途 |
| 6.49 kΩ | RT0603BRD076K49L | 4 | 电流限制 RIPROPI |
| 100 kΩ | RT0603BRD07100KL | 18 | 含电流/母线分压与 ADC 放电 |
| 20 kΩ | RT0603BRD0720KL | 1 | 母线分压下臂 |
| 0.10 Ω | RL0603FR-070R1L | 1 | R26，±1%、**±800 ppm/K**，不能当精密采样电阻 |
| 0 Ω | RC0603JR-070RL | 2 | R9 信号跳接；R39 台架 CHASSIS/GND 连结 |

原厂 [RT 6.49 kΩ 逐料号规格](https://yageogroup.com/component-documentation/download/specsheet/RT0603BRD076K49L)与 [RL 0.10 Ω 规格](https://yageogroup.com/component-documentation/download/specsheet/RL0603FR-070R1L)支持上述精度/温漂；其余独立 PN 链接收录在 catalog。零欧料号网页模板的“5%/75 V”不能作为零欧电气额定解释，最大电阻与电流尚未取得受控确认；两处均不作为电机电流通路，R39 更不是保护地导体。

### 温漂加入后，电流/电压关系

本次研究假设**电阻体温 0…70°C**、25°C 为参考点，因此 ΔT 最大 45 K；这是计算条件，不是机器人环境温度或自热认证。RT 的相对因子界限为：

```text
kmin = (1 − 0.001)(1 − 25×10⁻⁶×45) = 0.997876125
kmax = (1 + 0.001)(1 + 25×10⁻⁶×45) = 1.002126125
Rlower = Rb || (Rdischarge + Ron)
Reffective = RIPROPI || (Rt + Rlower)
Vadc / Vipropi = Rlower/(Rt + Rlower) × Rdischarge/(Rdischarge + Ron)
Itrip = VREF / (AIPROPI × Reffective)
```

4 个电阻独立取上下界，Ron 取 0/4.5 Ω，并保留父设计 VREF ±1%、DRV 电流比例 ±7.5% 的预算，枚举 **128 个端点组合**。不是把标称 6.49 kΩ 当成没有负载的单电阻。

| 量 | 计算结果 |
|---|---:|
| 名义有效 RIPROPI | 6220.8467 Ω |
| 名义 Itrip | 0.8930546 A |
| 本次 Itrip 条件区间 | **0.8206960…0.9771948 A** |
| 电流 ADC 分压比区间 | 0.3323796…0.3342784 |
| VM 采样开关闭合时分压比 | 0.1423320…0.1433783 |
| VM 开关断开时上游分压比 | 0.1660772…0.1672578 |
| VM=15 V 时断开侧最高电位 | 2.5088667 V |
| VDD=0 的 ±2 µA 开关泄漏经放电电阻产生的界限 | 0.2004252 V |

这些区间未加入电阻老化、ADC 总误差、驱动动态过冲及供电过渡；VDD=0 的泄漏规格也不能外推到任意掉电斜坡。保留后续实机限流标定。

局部功耗例子：6.49 kΩ 两端 2.5 V 约 0.965 mW；1 kΩ 两端 3.399 V、按最小阻值计算约 11.723 mW；100 kΩ 分压上臂保守承受全 15 V 约 2.255 mW。不能把这三个例子说成全部电阻均通过：33 Ω /49.9 Ω 若持续承受 3.399 V，分别约 **350/232 mW**，超过该封装 0.1 W。其实际正常信号功耗、总线争用与 PHY 波形必须单独检查。

## 2. 电容与真实封装

| 用途/数量 | 选定候选 | 标称规格 | 最大本体 L×W×H mm |
|---|---|---|---|
| 全部 100 nF，47 颗 | TDK C1608X7R1H104K080AA | 50 V、X7R、±10%、0603 | 1.7×0.9×0.9 |
| 全部 1 µF，11 颗 | TDK C1608X7R1E105K080AB | 25 V、X7R、±10%、0603 | 1.7×0.9×0.9 |
| 全部 10 nF，11 颗 | KEMET C0603C103K5RACTU | 50 V、X7R、±10%、0603 | 1.75×0.95×0.90 |
| 全部 22 nF，6 颗 | KEMET C0603C223K5RACTU | 50 V、X7R、±10%、0603 | 1.75×0.95×0.87 |
| C32，1 颗 | KEMET C0603C471J5GACTU | 470 pF、50 V、C0G、±5% | 1.75×0.95×0.87 |
| C6，1 颗 | KEMET C1206C106K3RACTU | 10 µF、25 V、X7R、±10%、**1206** | 3.4×1.8×1.8 |
| C45/51/57/63，4 颗 | KEMET C1210C106K5RACTU | 10 µF、50 V、X7R、±10%、**1210** | 3.6×2.8×2.8 |
| C83/84，2 颗 | KEMET C1210C226K4RACTU | 22 µF、16 V、X7R、±10%、**1210** | 3.5×2.72×2.8 |
| C82，1 颗 | Panasonic EEUFR1E102 | 1000 µF、25 V、铝电解、±20% | **Ø10.5×22**，脚距 5 |

这些是元件本体界限；焊锡离板高度、贴装偏差、courtyard、绝缘与维修空间另外计入。TDK 的 [100 nF](https://product.tdk.com/de/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1H104K080AA)和 [1 µF](https://product.tdk.com/de/search/capacitor/ceramic/mlcc/info?part_no=C1608X7R1E105K080AB)官方页面本次显示 Production，没有据此承诺渠道库存。KEMET 精确规格与封装尺寸按 catalog 中各独立 PN 的官方 PDF。

### VM 旁路与直流偏压

原拟给四路 VM 使用的 C1206C106K3RACTU，在官方典型曲线中 12/15 V 下约剩 4/3 µF。保留此型号给 3.3 V 的 C6；四路 VM 改用上表 **C1210C106K5RACTU**。其 [原厂 PDF](https://search.kemet.com/component-documentation/download/specsheet/C1210C106K5RACTU) p2 曲线人工估读，12 V 下约 6.5…7.0 µF、15 V 下约 5.0…5.5 µF。这些范围表达读图精度，**不是原厂保证的批次最小值**；不得把典型曲线再乘公差、温度系数就称为保证值。

[DRV8874 数据手册](https://www.ti.com/lit/ds/symlink/drv8874.pdf) p3/10 要求 0.1 µF 低 ESR 陶瓷旁路及按系统选择的 bulk，p30/31 要求结合供电响应、线感、纹波与制动方式确定。本型号没有统一的“偏压后必须至少 10 µF”条款。四路既有 100 nF 与电荷泵电容保留；本次提高局部储能支路余量，实际母线和上电波形仍要验证。

C31 的 1 µF/ESR 也单独保留验证项。[LAN9252 DS00001909C](https://ww1.microchip.com/downloads/aemDocuments/documents/UNG/ProductDocuments/DataSheets/LAN9252-Data-Sheet-DS00001909.pdf) p29/31 给 1 µF、0.1 Ω ESR 支路；它没有明确强制外串一个 0.1 Ω 电阻。[原厂评估板图纸](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/BoardDesignFiles/lan9252-hbispigpio-evb-rev-b.pdf) p4 则采用直接接地的低 ESR 1 µF。[SQFN 检查表 Rev B](https://ww1.microchip.com/downloads/en/DeviceDoc/Schematic%20Checklist%20LAN9252%20SQFN%20Rev%20B.pdf) p13 的 ≥1 µF/≤2 Ω 不能直接作为当前 TQFP `/PT` 方案已验证的完整稳定窗口。

本次不更改 R26 拓扑；其电阻体温 0…70°C 的计算范围是 0.095436…0.104636 Ω。总 ESR 还包括 MLCC 与布线随频率的影响。C31 名义 1 µF 不等于偏压/温度/公差后至少 1 µF；本板启动、阶跃与稳压稳定性尚未关闭。

### C82 的储能与装配

[Panasonic FR-A 官方规格](https://industrial.panasonic.com/cdbs/www-data/pdf/RDF0000/ABA0000C1259.pdf) p1/2/5：EEUFR1E102 名义 Ø10×20 mm，直脚 Ø0.6 mm、脚距 5 mm；尺寸公差后本体最大 Ø10.5×22 mm。100 kHz、105°C 纹波额定 2.18 A RMS；100 kHz、20°C 阻抗上限 **0.020 Ω**。官网 HTML 有单位标注不一致，以 PDF 的 Ω 表为准；该阻抗不等于任意频率 ESR，也不能外推成整机电流额定。

仅考虑初始 −20% 容差，Cmin=800 µF，理想 12→15 V 储能从名义 0.0405 J 降到 **0.0324 J**。低温、老化、ESR/ESL、母线过冲还会限制可用量；它没有批准电机回生。22 mm 最大高度也尚未放入 [56×64×30 mm 控制舱](../head-control-volume01.md)的完整双板装配。横放需要真实引脚折弯、固定及泄压间隙，不能把圆柱转 90° 就视为装配通过。

## 3. 调试跳线及封装差异

JP1/2/3 选 **Samtec TSW-102-07-T-S**，每个 2 位、2.54 mm 节距、镀锡，配 **SNT-100-BK-T** 跳线帽 3 个，正常使用均**不安装帽**。

| 位置 | 原电路针脚 | 短接用途 |
|---|---|---|
| JP1 | BOOT0 / 3V3_LOGIC | 电机禁止状态下进入启动维护 |
| JP2 | RESET_BUTTON_N / GND | 持续复位，移除短接后才释放 |
| JP3 | EE_WP / GND | 受控 EEPROM 写入期间取消写保护 |

[TSW 原厂图纸](https://suddendocs.samtec.com/prints/tsw-xxx-xx-xxx-x-xx-xxx-mkt.pdf)与[推荐孔位](https://suddendocs.samtec.com/prints/tsw-xxx-xx-x-x-xx-xxx-footprint.pdf)规定 0.100″ 节距、0.040″（约 1.02 mm）名义孔径。针长名义 10.922 mm，插接端 5.842 mm；本体高度 2.54 mm 为参考量，板上总高约 8.382 mm 也仅是名义规划值。跳线帽 [SNT 图纸](https://suddendocs.samtec.com/prints/snt-100-xx-x-x-mkt.pdf)的 5.08×2.54×6.10 mm 是参考尺寸，不可误当公差后最大包络。最终对插高度和手指拆装空间仍待纳入板形。

本次 11 处封装变化为：C6→1206；C45/51/57/63 与 C83/84→1210；C82→真实径向铝电解；JP1/2/3→真实通孔座。CSV 的 `vendor_pending` 名称是**待建立的封装规格标识**，不是已存在可下单的 KiCad 封装。其余通用 0603/1206/1210 名称也需要按端头尺寸及贴装工艺复核，不自动继承此前空间占位通过结论。

## 4. 复算与下一步

在仓库根运行，不需要 CAD 或网络依赖：

```bash
python3 engineering/electronics/head-passives01/select.py
python3 engineering/electronics/head-passives01/review.py
```

脚本核对 193 个位置覆盖、原名义 R/C 值、原两针网络、11 个封装差异、温漂端点与源文件哈希，生成 4 份 CSV、计算报告和文件清单。独立 `review.py` 使用 NumPy 节点 KCL 解法复算128个电流和16个VM端点，不调用选择脚本中的等效电阻公式；本次最大差3.85×10⁻¹³。可选 `--vendor-source-dir /local/head-passives01` 校验26份本地原厂PDF，省略时报告明确不声称校验这些PDF。独立结果见 [review JSON](../../../engineering/electronics/head-passives01/independent-review.json)。冻结原理图没有更改，因此没有把旧 ERC 结果重新宣传为新 PCB 验证，也没有生成 Gerber。

下一版控制板应消化这些真实尺寸，确定双板分工、板间针序、回流与热路径，并解决主电源/短路/回生、SPI/以太网信号、稳压与复位波形。元件选型阶段完成的是**可追溯的具体料号与变更清单**；控制器整板、整体线束和整机制造放行仍未完成。
