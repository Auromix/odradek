# BRI01 底座后部接口板

BRI01 是与 B04 服务板分离的真实接口 PCB 候选。它承接外置控制箱的专用 EtherCAT 线、主 48 V 和两条 GMSL 同轴；本体内部仍由对应线束继续上行。116 × 56 × 1.6 mm 板上有两个无磁屏蔽 RJ45、一个带锁动力插座及三个 M3 内部接线柱。双同轴转接器由共享安装点的金属托件固定，信号不经过 FR4。此包提供原生 KiCad、可重建布线、Gerber/钻孔和原创三维接口模型；状态是**原型加工审查候选**。

## 文件和机械合同

权威电气入口为 [原生项目](../../engineering/electronics/base-rear-interface01/kicad/base-rear-interface01.kicad_pro)、[网表与引脚](../../engineering/electronics/base-rear-interface01/pin-net.csv)、[BOM](../../engineering/electronics/base-rear-interface01/bom.csv)。机械集成读 [mechanical/parts.json](../../engineering/electronics/base-rear-interface01/mechanical/parts.json)，其中 59 件 `name / bbox_global / role` 对应 [总装 STEP](../../engineering/electronics/base-rear-interface01/mechanical/base-rear-interface01-assembly.step)。不要用仅有板上放置框的 `placement-envelopes.json` 代替它。三维件为原创目录外包、实际板孔和接口托件参考；不转载厂商 STEP，也不把包络体积作为零件质量。

PCB 局部 u/v 为 KiCad x/y；z=0 为背面，元件在 z=1.6 一侧。总装转换为：

`X = u − 58; Y = z − 27; Z = −9 − v`。

四个安装孔 `(6,6),(110,6),(110,50),(6,50)`，Ø3.2，全部铜层 R3.5 禁布；额外同轴托件孔 `(48,38),(68,38)` 同规格。NPTH 安装孔没有电气接地功能。J6 为独立屏蔽机架连接端，不能将它直接称为已经验证的保护接地端子。

外部插口统一朝 −Z，面板参考平面 Z−65；内部 J2 朝 +Z，嘴面 Z−9。J3 动力口中心 X38.5，J1 中心 X−38；同轴轴线在 `(X,Y)=(−10,−16),(10,−16)`。完整孔口、拔插和接线预留见 [connector-contract.json](../../engineering/electronics/base-rear-interface01/connector-contract.json)。全接口盒先拔外部插头，再随金属载板向上移出；板不靠线缆承担安装载荷。

根任务采用的护罩内前壁 Y−5 与同轴托件最前 Y−7 间隙 2 mm；内后壁 Y−35 与最长动力焊尾 Y−30.4 间隙 4.6 mm。Ø14 护罩让位孔相对 SMA 固定肩最大外接半径 5.48483 mm 有 1.51517 mm 径向名义余量。金属托件仍用自身 D 孔承扭，塑料大孔只是让位。这是零件名义外包对照，未包含全部线缆、工具和公差。

## 电气和引脚

| 接口 | 器件 | 本板连接 |
|---|---|---|
| J1 外部 / J2 内部 | Würth 615008160221，屏蔽 8P8C、无磁、无 LED | 1→1 至 8→8；四对为 1/2、3/6、4/5、7/8 |
| J1/J2 屏蔽壳 | 同上 | S1/S2→CHASSIS→J6；不接 RETURN48 |
| J3 外部动力 | Phoenix 1720466 | 自定义本板 pin1→VIN48→J4；pin2→RETURN48→J5；每极三根焊尾 |
| J4/J5 | Würth 74651173 | M3 内部动力螺柱，线缆朝 +Z；上游供电、保险和断电控制在外置箱 |
| J6 | Würth 74651173 | 屏蔽机架绑接；独立于动力回流 |
| X1/X2 | Amphenol 132170 | SMA 母—母、50 Ω 实体同轴转接；只有金属安装关系，无 PCB 网络 |

J3 图中没有厂家定义的“正极”。本板自行编号：在板元件面 u向右/v向下坐标中，pin1 的一列为 u100.31，pin2 为 u92.69。线束 P3 必须按这些对应触点压接和标记；不能靠外观猜极性。J1/J2 是被动直通，不含 PHY、隔离变压器、EtherCAT 从站或 PoE 电路，也不是给普通 LAN 与 EtherCAT 互相转换的网关。

[Würth RJ45 图](https://www.we-online.com/components/products/datasheet/615008160221.pdf)给出 15 × 13.45 × 14.7 mm 名义壳体；原厂 STEP 包括更宽的 EMI 弹片，模型采用约 17.3 mm 总宽预留。原厂 KiCad 库用于交叉核对针序。这里的原创 shield 焊盘由原库 1.5 × 3.0 缩为 1.5 × 2.5 mm，仍保留 1 × 2 mm 镀孔和每向 0.25 mm 名义环宽，避免相邻 Ø3.18 NPTH 的铜间隙不足。该焊盘修改应交装配方确认焊接和机械保持，不能冒充未改动的厂家推荐图。

[Phoenix 1720466](https://www.phoenixcontact.com/en-us/products/pcb-header-pc-5-2-g-762-1720466) 的六个 Ø1.3 孔已按该准确型号原图录入：距嘴面 19.80/22.34/27.42 mm，列距7.62。其 32 A 是连接器器件规格，**不是本板额定电流**。配对正锁插头为 [1718481](https://www.phoenixcontact.com/en-us/products/pcb-plug-spc-5-2-stcl-762-1718481)，总外包23.24 × 38.45 × 19.8 mm。独立图的14.7 mm插入段不直接证明完整配对偏置；外壳当前为较大的服务预留，需实样确认。拔插须在回路断电、无负载条件下进行。

## PCB、阻抗和动力预算

四层候选：F 信号/动力、In1 CHASSIS、In2 CHASSIS、B 信号/动力；两内层在网口区域连成参考铜，没有内层信号走线。候选叠层为 [JLC04161H-7628](https://jlcpcb.com/impedance)：外层35 μm，邻近介质0.2104 mm，内层15.2 μm，芯板1.065 mm；铜加介质名义求和1.6062 mm。机械板厚仍为1.6 mm标称，最终需板厂确认成品厚度、公差、孔铜、阻焊和受控叠层。

四对各保留22 mm、线宽0.24/间距0.20 mm的并行直段。当前无阻焊的一阶估算约99.8 Ω，目标100 Ω ±10%；这不是二维场求解或测试结果。扇出包含分层、过孔和不等长，实际回读的最大对内铜线长度差约16.102 mm；**本版没有宣称整段已经做成合格 Cat6 通道**。应在准确叠层上审核扇出和回流，并用实际线缆测回损/插损或至少目标速率连续链路、错误计数及 EtherCAT 稳定性，再批准用于系统。DRC 0 不能代替该项。

动力区与网口参考区分开，主干每极在 F/B 各4 mm宽，焊盘和镀孔并联连接。按两面35 μm铜、室温ρ=1.724×10⁻⁸ Ωm及保守最长主干估计，正/回流合计3.191 mΩ；10 A时仅铜损约0.319 W/压降31.9 mV，20 A时约1.277 W/63.8 mV。数值不含接插件、压接、焊点、镀孔电流分配和升温，见 [可复算输入](../../engineering/electronics/base-rear-interface01/calculations.json)。10 A连续、20 A短时只是验证目标；20 A允许时长尚无定义，必须做封闭护罩实测和上游保护协调。没有本板额定或整臂峰值电流结论。

[74651173 螺柱](https://www.we-online.com/components/products/datasheet/74651173.pdf)的 M3 扭矩上限0.5 N·m；50 A为指定条件下的器件数据。本轮保留其1.85 mm孔、3.2 mm焊盘、5.87 mm四孔方阵。该文件虽列波峰焊曲线，警告又写不适用于波峰焊并推荐回流，不能自行忽略；装配流程应明确 THR 回流与其余连接器的工序、支撑及返修条件。

## 线束与同轴仍需关闭的接口

内部 RJ45 采用具体尺寸候选 [Stewart SS-37200-028](https://www.cinch.com/media/drawings/products/ethernet-usb/dr-stw-ss-37200-028-37200-032.pdf)，无 boot，22.78 mm参考总长，适配AWG24–26、绝缘Ø0.94–1.07、线外径≤5.97。配线候选 [HELUKABEL 800068](https://assets-cdn.helukabel.com/suppliers/Helukabel/documents/db/HELUKABEL_M800068_EN_GB.pdf)为AWG26/7、SF/UTP、芯约Ø0.95、外径5.5–5.9，固定Rmin4D，按最大径取23.6 mm。两者只是尺寸匹配，尚未验证压接屏蔽连续性与装配。

**插头总长不等于外露长度。** 定义与 Würth 真实配对的插入量 I、出线后保留直线长 S；若额外保守地将厂家R当内缘半径，90°转弯总高 `52.28 − I + S` mm。嘴面Z−9到内顶Z39有48 mm，需 `I−S≥4.28 mm`，另加安装公差。真实配对datum尚未核实，3D没有将一整只30 mm插头错误地摆在jack外。它是固定短线，不要求这段承担关节扭转。线缆应从开放上方转入本体，并单独应力释放。

内部 M3 线鼻子暂列 [TE165295](https://www.te.com/en/product-165295.html)候选：M3孔3.2、1.5–2.5 mm²、总长14.35、板厚0.79，无绝缘也无护套夹持。孔中心到筒末、筒最高点尚缺可目视受控图，因此现有 `planned-lug` 小框**并不证明该候选已装入**；需要补确定的螺母/垫片、防松、绝缘和线夹。不能将未知线端几何当成模型已完整。

[Amphenol 132170](https://www.amphenolrf.com/en-us/part/132170/7012/)为当前50 Ω转接器；原厂署名旧目录给总长22.1、可拆螺母AF8、固定肩AF9.5，长端至承靠肩面14.6、肩背16.3 mm。[原图镜像，第23页/印刷47页](https://www.farnell.com/datasheets/1681616.pdf)。Ø6.5 D孔的**总平边高度是6.0**，因此圆心到单侧平面2.75，并非直接从圆心取3.0。托件在Z−65承靠，则长端Z−50.4、短端Z−72.5。螺母/垫圈组合厚度2.5 mm仍是预留，不是受控产品尺寸；当前图下载未取得，旧图用于名义接口审查。

两路 SMA 不天然防误插，必须标 CAMERA A/B；确切 SMA 公头—目标相机接头线缆、PoC电流及6 Gb/s链路测试仍待选。18 GHz连接器规格不自动证明整个GMSL通道与PoC满足要求。托件负责耦合扭矩，FR4不作为唯一反力构件。所附L形托件只是孔位/空间参考，实际弯曲半径、材料和制造细节归底座机构确认。

## 复现与检查

```sh
python3 engineering/electronics/base-rear-interface01/rebuild.py \
  --kicad-python /path/to/KiCad/Python/bin/python3 \
  --kicad-cli /path/to/kicad-cli \
  --cadquery-python /path/to/cadquery/python
```

只检查现有板可追加 `--check-only` 并省去 CadQuery；脚本不需要供应商CAD或自动布线器。`routing-plan.json` 是最终真实铜线/过孔的回放输入；临时DSN、SES和虚拟路由定位点未加入交付板。检查使用 `--all-track-errors --schematic-parity --severity-all`，无 exclusions；最终报告、native 回读和哈希在 [verification.json](../../engineering/electronics/base-rear-interface01/verification.json) 与 [manifest.json](../../engineering/electronics/base-rear-interface01/manifest.json)。

[Gerber与钻孔](../../engineering/electronics/base-rear-interface01/fabrication/)供加工审查。下单前仍需完成受控叠层/孔铜与环宽、修改shield焊盘、混合焊接流程、接线端接、插头实配和上述电气试验的确认；此包不是整机安全认证或制造放行。
