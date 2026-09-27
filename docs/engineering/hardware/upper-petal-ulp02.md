# 上灯片 ULP-02：113 点四层 LED 电测板

一块独立上灯片已经落实为真实 KiCad 原理图和 PCB。**ERC、DRC、未连接、原理图/PCB 不一致均为 0**；317 引脚与源网络表逐一相符，113 颗 LED 的坐标及极性未改变。它是 HLIO-R03 独立电测样片，尚未制造/装配/测试，不承诺装入 CONTACT02 正式夹指。

- [电路、功耗、映射、完整 BOM 和固件样例](../../../engineering/electronics/upper-petal-prototype/ulp02/README.md)
- [原生项目、完整重建命令及检查证据](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/README.md)
- [最终 PCB](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/upper-petal.kicad_pcb)、[原理图](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/upper-petal.kicad_sch)、[原始 DRC](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/checks/drc.json)
- [Gerber / 钻孔制造审查文件及未闭合项](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/fabrication-review/README.md)

![ULP-02 正面铜层](../../../engineering/electronics/upper-petal-prototype/ulp02/kicad/plots/board-front.png)

新矩阵将两列相邻灯点归为同一 SW，同行的奇偶列分别使用 14 个 CS。11 行扫描不变，最大行 14 灯，20 mA 时峰值 **280 mA**，3 mA 初次点亮时 42 mA。全亮平均上界仍是 205.455 mA；软件 ON/OFF、DC、PWM、SRAM 地址及 C99 例程均从同一 ULP-02 映射生成。不可继续使用 ULP-01 地址或 220 mA 峰值预算。

板上 134 件，包括 113×Würth 150060YS75000、LP5860RKPR、NCU18XH103F6SRB、JST GH10 和所有本地无源件。F.Cu 放 LED，非 LED 元件在背面；In2.Cu 保留连续 GND，227 个过孔，800 段走线。源网表和封装 hash 改动会阻止旧布线快照重放。

0.15/0.15 mm 最小线宽/间距已实际检查；项目没有加入单项豁免，工具默认忽略项完整保留在报告。数字 CAD 检查不等于板厂能力、温升或装机验收。受控封装复核、叠层、热孔/钢网、外部保护电源和线束、首板电测、热/EMI 与相机条纹仍需完成。

普通区域候选总层叠 4.45 mm；包含 GH 配对接头的根部为 10.3 mm，均不含装配公差、支撑、绝缘和线弯余量。主机械模型没有为此板更改。

许可证 CC-BY-NC-4.0；Auromix contributors。
