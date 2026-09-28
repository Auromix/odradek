<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek) -->
# CD-DRAW01：中央屏无电、无载几何样件

本套文件直接读取冻结的 CD-MOUNT01 STEP，不修改安装孔、主CAD或原有13项来源。用途是核对装配、孔位、叠层和手工拆装；没有选定透明窗口或绝缘材料，没有金属生产公差和预紧放行。禁止通电运行或安装实际负载来代替样件几何检查。

[四页A3尺寸图](../../engineering/generated/central-display-drawings01/ODR-CD01-geometry-prototype.pdf)依次包括装配真实剖面、杯座前后不同腔形、前压框，以及绝缘圈/窗口/PCB轮廓。[生成脚本](../../engineering/draw_central_display01.py)、[尺寸与导出证据](../../engineering/generated/central-display-drawings01/drawing-evidence.json)、[视觉复核](../../engineering/generated/central-display-drawings01/visual-qa.json)可用于回查。

## 名义特征与文件

全部尺寸为mm。XY原点是屏中心，方向保持HEAD坐标；PDF明确标注各视图比例。DXF采用原尺寸模型空间、`INSUNITS=4`，不能按页面适配缩放后再当1:1加工轮廓。

| 零件 | 完整几何定义 | 交付 |
|---|---|---|
| cup 杯座 | Ø64圆与居中76.5×8矩形的并集，厚11.25；2×Ø2.2贯通，中心X±35.25/Y0；前腔Ø60.2深3.25；中间Ø56座口厚1；后腔深7，具体轮廓见下文 | [DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-cup.dxf)、[STL](../../engineering/generated/central-display-drawings01/STL/CD01-cup-print-mm.stl) |
| bezel 前压框 | 同杯座XY外形和两孔；中心Ø57贯通，厚1.5 | [DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-bezel.dxf)、[STL](../../engineering/generated/central-display-drawings01/STL/CD01-bezel-print-mm.stl) |
| spacer 绝缘圈几何替身 | 外Ø59.8、内Ø57、厚1.5 | [DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-insulating-spacer.dxf)、[STL](../../engineering/generated/central-display-drawings01/STL/CD01-insulating-spacer-print-mm.stl) |
| window 窗口片材轮廓 | Ø59.8、名义厚0.75；没有新增孔、倒角或光学处理 | [尺寸DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-window.dxf)、[纯切割轮廓](../../engineering/generated/central-display-drawings01/DXF/CD01-window-cut-outline.dxf) |
| PCB dummy | Ø60×1纯轮廓替身，无铜层、器件或线缆 | [DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-PCB-outline.dxf)、[STL](../../engineering/generated/central-display-drawings01/STL/CD01-PCB-outline-print-mm.stl) |

另有绝缘圈和PCB的纯平面切割轮廓，以及[实际装配XZ剖面DXF](../../engineering/generated/central-display-drawings01/DXF/CD01-assembly-section.dxf)。现有光学框仅作为安装上下文，本册规定新增的两颗Ø2.2孔；其完整旧外形继续以原STEP为准，不能把装配剖面当成整个光学框的制造图。

**杯座后腔不是完整Ø60.2。** 原耳桥在底部留下两段X=±30平面，腔形为 `R30.1圆 ∩ |X|≤30`；平面端点Y=±2.451530mm，贯穿后侧7mm深度。前侧经过重新切孔，才是完整Ø60.2。图纸、DXF和STL均保留这两处真实细节，不用理想圆孔替代。外圆与耳边的相交点为X±31.749016/Y±4；这些交点是原圆弧和直线相交，没有暗加R或倒角。

## 打印与首件测量

STL自身不带可靠单位，导入切片器时选择 **mm、100%比例**。四件文件只把各自后基准面平移到打印Z0，没有旋转、整体缩放、孔扩大或象脚补偿。杯座对应原HEAD Z−11，前框对应Z0.25，绝缘圈对应Z−2，PCB dummy对应Z−3；耳方向沿打印X。打印朝向记录在证据JSON中。

1. 先用同批PLA或PETG、同喷嘴与拟采用的首层参数打印前框、绝缘圈及PCB dummy作为低耗首件。记录打印机、材料批次、喷嘴、层高/首层、流量、壁数、支撑和冷却；这些材料仅是无载形状验证候选，不表示绝缘或温度能力已经确认。
2. 实测总宽76.5、两孔距70.5、X/Y方向孔径、板/圈厚度、翘曲及首层外扩。小孔优先用已知直径量针或能识别误差的量具；只有螺钉“能穿过”的手感时，记录为通行检查，不能当Ø2.2尺寸验收。
3. 若出现孔缩或首层外扩，先区分XY孔偏差与首层象脚。仅在切片器中对该打印配置调整孔补偿/首层参数并复测，保留原STL及测量记录，禁止全件缩放来凑某个孔径。未有实测数据前不预填固定“加0.2mm”等补偿量。
4. 打印杯座时先检查切片：R30.1向R28的内环形成约2.1mm径向悬挑，需验证局部支撑或桥接能力，以及能否从后腔去支撑。不能让支撑残留压到PCB座或塞住两处后腔平面。1mm座厚、前腔深3.25、后腔深7及总高11.25都须实测；层高设置本身不等于获得该尺寸公差。
5. 去除可见毛刺后，先手动放入PCB dummy，再放绝缘圈和片材窗口样件、前框，轻触合拢检查。不得用螺钉预紧力把翘曲件强拉到位。记录接触、间隙、摇动和拆出情况，再决定打印参数或后续设计修改。

窗口只交付真实二维轮廓和名义厚度，供片材样件；未声称某种透明材料、打印透明片、激光工艺或刀缝补偿合格。绝缘圈打印件也只是尺寸替身。首件均未规定可接受力矩或载荷。

## 装拆边界

杯体经左右耳压在后光学框上，圆筒底缘本身不接触后框。PCB座、绝缘圈、窗口和前框虽名义接触，杯/前框还有一条并联硬限位路径；不能由图中齐平推断实际夹紧力。两颗最大Ø5后垫在现孔位对后框内外缘各有0.25mm名义余量，尚未分配孔位、垫片或打印误差。

本套无电样件优先用PCB dummy。若另装实际有线PCB，必须在最终封装前验证GH锁扣、导线释放及应力释放可达；拆卸前先断电、卸载、解绑导线，再拆后螺母和垫片，向前依次取螺钉、前框、窗口、圈和PCB。不要带着未释放的线束强拉。[独立装配审查](central-display-review01.md)中的60mm前拆证明不等于整光学架可从完成外壳中取出。

## 数值与视觉复核

DXF保留实际STEP截面得到的LINE/CIRCLE/ARC，未用网格投影补漏边。杯前/后腔、前框和三种平面零件共六个DXF截面回读成闭合线框与精确面，其净面积与独立解析值对照；五个零件的解析体积和包围盒另与STEP对照。详情见证据JSON，不把纯文件语法通过称为尺寸验证。

STL采用绝对线性偏差0.005mm、角度偏差0.05rad导出；重读后四件均为封闭、绕向一致网格，未补洞或修补几何。记录每件网格包围盒、体积误差、三角面数和原始STEP哈希。PDF已通过文本/页数检查，并实际渲染四页核读中文、尺寸、箭头及裁切；视觉记录独立保留。

复现：在仓库根目录运行 `python engineering/draw_central_display01.py --font /path/to/Chinese-capable.ttf`，需要CadQuery、ezdxf、trimesh、reportlab和pypdf。脚本会核对冻结来源；任何来源漂移会停止，不会静默把新模型当成本版图纸。
