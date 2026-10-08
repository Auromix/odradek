<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# B04-P2 底座历史三维审查包

**当前底座已切换为[B06-COMPACT-02](../base_b06/README.md)。** 本包仅作历史结构研究；其桌夹、底板、接口与检查结果不能直接移用于紧凑B06。见[同源规则](../../docs/engineering/base-authority.md)。

本包只深化桌面机械宠物的底座：飞碟盾形外罩、隐藏桌夹、内收盒架和后部接口。它是供外观、装配及打样评审的工程候选，尚未制造放行。

- [可旋转三维模型](build/index.html)：自包含 WebGL，可开关模块、展开、切换桌厚；“如何拧紧”显示长内六角工具。
- [Blender](build/ODR-BASE-B04-P2.blend)：按模块分组的实际 CAD 网格，可继续编辑；不是参数化加工源。
- [STEP 总装](build/ODR-BASE-B04-P2.step)、[GLB](build/ODR-BASE-B04-P2.glb)、[零件/孔特征清单](build/manifest.json)、[零件 BOM](build/parts-bom.csv)。加工几何以 STEP、特征清单及源参数共同为准。
- [前罩近景](build/shield-closeup.png)、[全装配](build/assembled.png)、[内部](build/open.png)、[后侧](build/rear.png)。图像由同一 CAD 导入 Blender 渲染。

## 这一版的形状和模块

外罩是围绕中央环座展开的低矮曲面护盾，保留宽肩、收腰、下扣的外沿。曲面由相互对应的周期样条截面分段放样；前后两罩以 0.8 mm 分缝分开。中央承力法兰独立，外罩不承担机械臂载荷。前方琥珀灯窗随肩部曲面变化，背后是独立 50×12 mm 灯板。

三块 PCB 各自独立：

| 模块 | 工作内容 | 本轮交付 |
|---|---|---|
| [服务板](../electronics/base-b04/README.md) | 本地低压服务、电源状态和灯驱动等，边界以其电路文档为准 | 原理图、PCB、BOM、制造导出、机械包 |
| [前灯板](../electronics/base-light-b04/README.md) | POWER / RUN / FAULT 三路 LED，四芯线接服务板 J3 | 原理图、PCB、STEP、安装/线序合同 |
| [后接口板](../electronics/base-rear-interface01/README.md) | 板载 EtherCAT RJ45 转接、48 V 接口和接地；同轴另走机械支架 | 原理图、PCB、连接器/插头范围、STEP |

后接口朝下，PCB 与载板、护罩构成可拔出的接线仓。RJ45 和动力头实际焊在 PCB 上；两个 GMSL 同轴接口固定在金属小支架上，共用模块安装位置，射频信号仍通过同轴，不经过普通 FR4 走线。没有在此处增加 EtherCAT 主站、PHY 或磁性器件。外置盒及 PC 通信架构保持既定方向，本包不设计外置计算机。

## 如何拧紧和拆装

桌夹由左右两根 M12 压紧螺杆向上顶紧，使用 **AF6 长内六角从螺杆下端插入**；交替、小步收紧，使上下压板均匀接触桌面。两側横向 M6/M8 螺钉连接骨架，不用于夹紧桌板。模型显示了真实六角入口和工具方向。尚无经过力标定的安装扭矩，不能把手拧紧等同于额定承载。

1. 先装金属承力骨架、上下软垫、钢压脚及不承力的分体保持罩，再安装桌夹。
2. 盒架朝 +Y（桌内）伸出。盒体检具为 180×150×50 mm，3 kg 是空间/载荷分配值；控制器尚未选定。安装盒体时另配 20 mm 绑带，模型已开绑带槽。
3. 接线仓先在桌外装 PCB、绝缘/接地及接头，再由上方装入后沿开口，以四颗 M4 固定。两颗凹入的 M3 固定其保护罩。
4. 灯罩和灯板先装到前罩背面；两颗 M2×6、0.3 mm 垫圈与 ruthex RX-M2x4 热熔嵌件固定灯板。嵌件外形以原厂 STEP 核对为 Ø3.6×4 mm；当前 Ø3.2 预孔需要打印试片验证热熔工艺。
5. 拆前罩时先拔灯线；拆后仓时先拆后罩，拔掉全部内外线，再松四颗 M4 向上取出。接口护罩宽 129 mm，加垫圈总包络 130 mm；底板开口宽 132 mm，左右各有 1 mm 名义间隙。护罩垫圈位为 Ø8 开边凹孔。

## 数字检查与未关闭项

[几何记录](build/geometry-checks.json)检查每件自制零件的单一有效实体、STEP 重读和封闭 STL。曲面 STEP 体积重读误差阈值为 max(0.02 mm³, 0.001%体积)，不是加工公差。[装配记录](build/assembly-verification.json)检查 15/30/60 mm 三种桌厚、螺钉头/垫圈、长工具和离散拆装位置；[静态交集记录](build/nominal-collisions.json)另存总装结果。刚体检查不含标准件之间和元件之间的全部配对；螺钉只另查头部及垫圈，螺纹啮合按堆叠另算。记录与检查脚本、源模型及实际读入的 PCB 文件散列绑定。

尚待实物关闭：打印变形与热熔嵌件保持力、螺纹/公差、桌板材质和压痕、夹紧力与承载/倾覆、线缆弯曲半径和插头释放手感、RJ45/GMSL 信号完整性、48 V 温升与上电、灯罩亮度与串光。没有完整柔性线束模型；不把直通网口的布线规则通过当作 EtherCAT 或相机链路合格。

[B04-P1 力学计算](../../docs/engineering/base-b04-strength.md)是历史计算证据，P2 的后开口和外罩已变化，不能直接作为 P2 制造/承载放行。[旧 PDF 图册](build/drawings/README.md)也只保留为 P1 检查点；它不与本版 STEP 混用。生产图册需在此轮三维评审后重新冻结。

## 重建

在仓库根目录、安装 CadQuery / trimesh 的 Python 环境中依次运行：

```sh
python engineering/base_b04/build.py
python engineering/base_b04/verify.py
python engineering/base_b04/cad_surface_normals.py
python engineering/base_b04/viewer.py
blender -b --python engineering/base_b04/blender_scene.py
```

先按三个 PCB 子包说明生成各自机械文件；本包直接读取这些原生导出。`build/index.html` 全资源内嵌；本地预览可用 `python3 -m http.server 8769 --bind 127.0.0.1 --directory engineering/base_b04/build`。

嵌件依据：[ruthex RX-M2x4 原厂页面](https://www.ruthex.de/collections/gewindeeinsatze/products/ruthex-gewindeeinsatz-m2-70-stuck-rx-m2x4-messing-gewindebuchsen)。原厂详细 CAD 不作为本项目自制件再发布；总装仅含带尺寸依据的简化外包络。
