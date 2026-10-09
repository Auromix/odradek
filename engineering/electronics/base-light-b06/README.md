# B06 独立 PWM 前灯

用户已确认：程序独立调光、呼吸、闪烁。采用底座IO板就地产生的5V、PWM和RETURN48，经内部GH三芯线连接三路独立限流的琥珀LED灯板，不增加桌下5V线。PWM高电平点亮，断开或复位时47k下拉保持关闭；建议1kHz。同一IO板已加入[STM32灯控候选](../base-io-b05/controller/README.md)和UART命令接口；固件数字测试通过，IO板铺铜DRC已为0，实板和线束仍未闭环，不能作为完整通电放行。

实际原生工程在`../base-io-b05/base-io-b05/base-io-b05.eprj3`，板名称B06-LIGHT-PWM，PCB文档`pcb/PCB1.epcb2`，原理图`sch/Schematic1/P1.esch2`。与IO板共用同一个原生工程和仓库，不维护第二套独立底座。当前板50×14×1.6mm，双面铜，元件全顶面，四个NPTH；保存、复开和原生DRC检查通过。45条线路、8个过孔、12个元件。`manufacturing`为客户端实际导出的Gerber、BOM、贴片坐标、网络、IPC356与STEP；`audit.py`复核实际文件、引脚网络、钻孔、数量和指纹。

J1实际是SMT GH接口；库的封装显示名含CONN-TH，不能按显示名当作通孔件。引脚1=5V_IN、2=PWM_IN、3=GND。采用JST GHR-03V-S线端壳及SSHL-002T-P0.2端子，AWG26–30、线径/绝缘尺寸依JST资料；必须按端子编号查方向，不能按正视左右臆测。外部5V支路建议限流100mA以内，PWM为3.3V/5V逻辑，与底座共地。**不得接入48V。** 5V供电范围暂定4.75–5.25V，点灯典型约17mA；三路470Ω各自限流，保守电流上界约34mA。该上界不代表短路保护或热认证。

LED1–3：LTST-C170KFKT / C284931，605nm；R1–3：RC0603FR-07470RL / C114669，470Ω；R4：RC0603FR-071KL / C22548，1k；R5：RC0603FR-0747KL / C105579，47k；Q1：DMG2302UK-7 / C460977；D1：NSVBAT54HT1G / C179609；C1：CC0603KRX7R8BB104 / C92490，100nF/25V；J1：BM03B-GHS-TBT(LF)(SN) / C161691。采购/贴装以原生导出BOM与贴片坐标为准；未下单。

元件依据：[LiteOn LED](https://optoelectronics.liteon.com/upload/download/DS-22-99-0185/LTST-C170KFKT.pdf)、[Diodes MOSFET](https://www.diodes.com/datasheet/download/DMG2302UK.pdf)、[onsemi串联保护二极管](https://www.onsemi.com/download/data-sheet/pdf/bat54ht1-d.pdf)、[JST GH接头](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf)。GH板端高度4.05mm、插合高度7.3mm；库STEP仅作实际导出尺寸参考，不视为供应商认证模型。

全局机械坐标：STEP本地`(u,v,w)`映射为`(u−25,168.5+v,44.073+w)`，其中STEP v向后为负。板底Z44.073、板顶Z45.673；两颗M2安装孔X±23/Y163.5/Ø2.4，两枚灯窗支撑柱X±17/Y164.5穿Ø3.2 NPTH。GH位于X−5.2/Y158，插合上界预算Z52.973。原生STEP实体进入同一份Blender装配；还需真实线束弯曲、端子压接、透光效果和实物装配验证。

脚本执行顺序：`create-native.js`创建候选板/图→`schematic-native.js`使用完整原生库项重建本新图→`connect-native.js`设置PCB焊盘网络→原生ECO同步→`route_plan.py`与`route-native.js`→原生保存/复开DRC→客户端制造导出→`audit.py`。重建脚本会替换该新灯板的原理图电路，先备份，不能对其他原理图运行。早期50×10报告是历史记录，当前依据为`connected-native-50x14.json`、`routed-native-50x14.json`和`schematic-current.json`。

CC-BY-NC-4.0；Odradek / Auromix contributors。
