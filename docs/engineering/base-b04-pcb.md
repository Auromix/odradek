# B04 底座服务板 — 原生电路、布线与装配检查包

**B04-SERVICE01，2026-09-30；加工/装配审查候选。** 本包仅承担底座低功耗服务与状态显示，不是机械臂控制器。已有真实 KiCad 原理图、两层布线、逐针网表、BOM、Gerber/钻孔、可重建脚本和三维包络；没有实物通电、温升、EMC 或认证结论。研究源按仓库 CC-BY-NC-4.0 发布，不包含软件固件发布。

## 先看三维与接口

权威目录为 [base-b04](../../engineering/electronics/base-b04/)。主要装配文件：

- [全局坐标 STEP](../../engineering/electronics/base-b04/mechanical/base-b04-assembly.step)：可直接叠加底座总装。
- [板局部 STEP](../../engineering/electronics/base-b04/mechanical/base-b04-local.step)、[GLB](../../engineering/electronics/base-b04/mechanical/base-b04-local.glb)、[裸板 STEP](../../engineering/electronics/base-b04/mechanical/base-b04-board-only.step)。
- [机械接口 JSON](../../engineering/electronics/base-b04/mechanical-interface.json)：元件姿态、最大/参考包络、焊高、插头和服务区；[原生回读](../../engineering/electronics/base-b04/native-readback.json)记录实际孔、焊盘、走线和过孔。

板为 **80×50×1.6 mm**；局部 `u` 向右、`v` 向桌内、`z=0` 是 PCB 底面。总装 `X=-40+u, Y=-2+v, Z=23+z`。孔位 `(5,5)/(75,5)/(75,45)/(5,45)`，4×Ø3.2 NPTH；以孔心 R3.5 禁铜/禁器件。金属柱从总装 Z14 到23，安装孔不接电气地，机架保护接地另设端子。

三维模型使用原生 PCB 的真实板厚、全部钻孔，以及 **40 个已摆放器件的目录外包高度**、焊脚和对插包络，共65实体。连接器不是厂家精细 BREP；芯片盒体没有被当作金属质量。普通 SMD 加0.10 mm 焊高规划。DIP/连接器必须控制修脚与焊点到板底以下≤2.5 mm，绝对预算≤3 mm。含插头的局部包络约 `u[-9.5,87.3],v[0,50],z[-2.5,12.7]`。装配时还应消费 u<0 的30 mm、u>80 的20 mm 服务空间；这不等于已验证实际电缆弯曲半径。

| 接口 | 板上料号 / 对插件 | 定义（按板上方孔 pin1 起） | 退出方向 |
|---|---|---|---|
| J1 | Phoenix 1803277 / 1803578 | 1：20–55V 服务分支；2：RETURN | −u |
| J2 | Phoenix 1803293 / 1803594 | 1 RUN+、2 RUN−、3 FAULT+、4 FAULT−；两路独立回路 | −u |
| J3 | JST S4B-XH-A(LF)(SN) / XHP-4，4×SXH-001T-P0.6 | 1 LED共阴极GND；2 POWER阳极；3 RUN阳极；4 FAULT阳极；各阳极已有2.2k限流 | +u |

[引脚与插头合同](../../engineering/electronics/base-b04/connector-contract.json)还列出 pin1 坐标、节距和包络。J1/J2是摩擦保持，XH是摩擦锁持，不是按键释放的正锁；需要另设线束应力释放。JST目录参考高6.1 mm，模型对插规划高7.0 mm；端口投影保守预留，未把目录参考值宣称受控最大公差。插拔应断电。EtherCAT、GMSL 和电机主动力均通过各自完整屏蔽线束/穿线结构旁路，本板没有相关焊盘，也没有新 EtherCAT 从站。

## 电路与工作条件

[原生原理图](../../engineering/electronics/base-b04/kicad/base-b04.kicad_sch)按精确器件针脚和网络标签组织；[PDF](../../engineering/electronics/base-b04/previews/schematic.pdf)、[逐针表](../../engineering/electronics/base-b04/pin-net.csv)、[原生 PCB](../../engineering/electronics/base-b04/kicad/base-b04.kicad_pcb)可交叉查看。

J1经250 mA保险、100 V反接串联二极管、10 Ω/1 W串联阻尼进入 LM5164。SMBJ58A仅作局部瞬态候选，58 V为反向工作电压；额定脉冲夹位93.6 V距100 V器件限值余量很小，未证明实际线束尖峰安全，也**不承担整臂再生能量**。保险0451.250MRL的125 VDC/50 A分断能力不等于整机断电能力；外置盒必须提供受保护的服务分支，预期短路电流不能超过该元件分断条件。

5 V输出只供状态灯/测试焊盘。**5 V≤0.25 A是受监督的测试负载上限，2 W是J1输入验收预算，均不是硬件精确功率限制器。** 两个状态输入还可能由外部提供约0.606 W（30 V同时有效的计算上界），须计入整盒热预算；正常没有0.25 A测试负载时本板需求远低于测试工况。禁止把J3当通用5 V输出端，禁止把250 mA保险理解为2 W限制。

状态输入高电平工作假设18–30 V，低电平0–2 V，中间区域不定义；输入不是带施密特整形的高速GPIO。每路两只1.5 kΩ/0.25 W串联，VO617A-3隔离，1N4148WS反并联保护光耦LED，再用BC857B提供低电流LED阳极。输入最低计算电流5.40 mA，最高10.10 mA；最坏单只输入电阻约0.155 W。光耦CTR目录保证点与温度、老化、饱和条件不同，打样需覆盖实际工作温度。POWER只表示本地5 V存在；RUN/FAULT是外部给定的电平显示，灭灯不代表安全状态。没有急停/STO功能或软件逻辑。

## 降压计算与布局审查

[计算 JSON](../../engineering/electronics/base-b04/calculation.json)保存参数，独立 `verify.py` 从 kΩ/kHz 公式及电感伏秒平衡复算。采用 RON=41.2 kΩ、L=68 µH；5 V反馈158k/49.9k；Type-3注入220k/3.3nF/220pF，bootstrap为2.2nF C0G ±5%，按±0.3%温漂规划后仍在1.5–2.5nF内；未误用常见100nF。

| 项目 | 名义计算 |
|---|---:|
| 输出 | 4.9996 V |
| 开关频率 | 303.374 kHz |
| 48 V 输入导通时间 | 343.333 ns |
| 48 V 输入电感纹波 / 0.25 A负载峰值 | 0.21710 A / 0.35855 A |
| UVLO接通/关闭 | 约18.00 / 16.80 V；非完整公差保证 |
| 输入4.4 µF在55 V的储能 | 6.655 mJ；名义电容值 |

初版计算曾把频率单位写低1000倍；已修复源公式和独立断言，最终报告不沿用错误217 A纹波。C7由已停产180pF改为在产220pF，仍大于公式最低值158.2pF；C4/C5由原参考非优选料改为TDK CGA6P3X7R1E226M250AE。来源/生命周期变化记录在包内。100 V输入陶瓷与25 V输出陶瓷的实际DC偏压、电容公差和损耗仍需测量。

本板不是TI评估板的尺寸复制。C1/C2、U1、bootstrap、L1及输出电容走线已优先固定；底层为地参考面，状态输入两独立浮地区域下方明确挖空。外置盒长供线用10 Ω串联阻尼替代另加并联电解的本版方案，不能仅据纯阻性简算放行热插拔：应测真实线缆/电源阻抗、20/48/55 V启动、输出负载跳变、掉电与电压尖峰；必要时下一版增大输入缓冲。电感目录电流余量不是板级温升证明。

两层1.6 mm、候选35 µm铜；实际最低线宽/间距0.25 mm、布线默认0.35 mm，主降压段0.65–0.8 mm；通孔最小钻径0.30 mm。6只U1散热过孔位于焊盘/焊膏区域，必须与板厂确认填孔盖铜及平整度/钢网工艺，不能拿当前Gerber默认作普通开孔回流。其他普通过孔不与SMD焊膏焊盘重叠。地铜不能替代机壳保护接地。

## 交付、重建和打样边界

[验证报告](../../engineering/electronics/base-b04/verification.json)包含原生 ERC 0、DRC 0、未连0、原理图一致0，以及无忽略DRC/无排除项、101个针脚/30个网络的回读一致性、安装孔独立禁布检查、6个散热via-in-pad位置和独立单位审计。自动布线试验中间文件不作为制造成果。

[Gerber与钻孔](../../engineering/electronics/base-b04/fabrication/)是从最终原生板真实导出，**供板厂/装配方审查，不是已经完成工艺协商的生产放行包**。包括双面铜/阻焊/焊膏/丝印、板框、分离PTH/NPTH Excellon与钻孔图。采购表是 [BOM](../../engineering/electronics/base-b04/bom.csv)及[配对/线束件表](../../engineering/electronics/base-b04/harness-bom.csv)，型号来自官方目录，库存、价格和批次未验证。

可在安装 KiCad 10、可导入 `pcbnew/wx` 的 Python 和 CadQuery 的环境重建，不依赖随机再次自动布线：

```sh
python3 engineering/electronics/base-b04/rebuild.py \
  --kicad-python /path/to/kicad-python \
  --kicad-cli /path/to/kicad-cli \
  --cadquery-python /path/to/cadquery-python
```

`--check-only`保留原板，重跑检查/导出；`routing-plan.json`是最终真实走线的可回放数据。原理图UUID按引用确定；PCB中自动UUID、导出时间戳可能变化，网络/几何审计才是等效性依据。

采购前确认接头实际样件方向、导线压接/螺钉工艺和固定方式；板厂确认铜厚、成品孔公差、焊盘填孔、钢网和阻焊。首次只接受保护低能量服务电源，先查极性和绝缘，再测试20/48/55 V、两路状态以及三个外部裸LED；测试负载逐级增加，记录总输入功率、局部温度和供电尖峰。故障灯、光耦隔离和保险都不构成整臂安全系统。这些验证不在本轮3D/原生电气检查完成范围内。

关键官方依据：[TI LM5164](https://www.ti.com/lit/ds/symlink/lm5164.pdf)、[Vishay VO617A](https://www.vishay.com/docs/83430/vo617a.pdf)、[Phoenix 1803277](https://www.phoenixcontact.com/en-gb/products/pcb-header-mc-15-2-g-381-1803277)、[JST XH](https://www.jst-mfg.com/product/pdf/eng/eXH.pdf)、[Coilcraft电感](https://www.coilcraft.com/pdfs/mss1246t.pdf)。其余逐项见 [sources.json](../../engineering/electronics/base-b04/sources.json) 与BOM原厂链接。
