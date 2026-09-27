# R4 输出接口试装样片

这四片用于取得实际关节后，手动检查输出孔阵、中心凸台避让和工具进入空间。**它们是 4 mm 厚的无载打印样片，不是机械臂承力转接件。** 当前只完成几何生成与文件重读检查，尚未完成实物试装。

[四页尺寸图 PDF](../../engineering/generated/interface-coupons/PDF/ODR-interface-coupons-R4.pdf) 包含每个孔的坐标和角度、图号、中心孔与外径、厚度、孔径、PCD，以及打印与检验说明。主视图按 A4 横向 1:1 绘制；打印 PDF 时选择“实际大小”，不要选择“适合页面”。尺寸标注优先于纸张实测。

## 对应件与尺寸

全部单位 mm，厚度均为 4.0。外径等于该关节输出外圆定位直径加 8；中心孔等于中央凸台直径加 0.6。中心孔是避让孔，**不形成定位配合**。

| 样片图号 | 对应关节 | 外径 | 中心贯通孔 | 固定孔 | PCD | 图案 |
|---|---|---:|---:|---|---:|---|
| ODR-CPN-RH14-N-R4 | EPS-RH-14-100-E-N-D | 58.0 | 37.6 | 8×Ø3.5贯通 | 44.0 | 非均布，按坐标 |
| ODR-CPN-RH17-B-R4 | EPS-RH-17-100-E-B-D | 68.0 | 47.6 | 16×Ø3.5贯通 | 54.0 | 非均布，按坐标 |
| ODR-CPN-RH20-B-R4 | EPS-RH-20-100-E-B-D | 78.0 | 55.6 | 16×Ø3.5贯通 | 62.0 | 均布，保留提取相位 |
| ODR-CPN-RH25-B-R4 | EPS-RH-25-100-E-B-D | 93.0 | 69.6 | 16×Ø4.5贯通 | 77.0 | 均布，保留提取相位 |

数据来自 [原厂 STEP 独立提取记录](sources/rh-interface-extraction.json) 的 `unified_joint_interface.output_holes`。该坐标系原点是输出环形接触面的轴心，+Z 朝向输出端；样片底面 z=0，顶面 z=4。孔位保持原厂 CAD 的装配相位，尚未等同于编码器电气零位。可以旋转整片找正，不能镜像、缩放或重新均布孔阵。

原厂配套 STEP/PDF 只在本地用于核验，未随本仓库再分发；来源和版本见 [关节候选](hardware/joint-candidates.md)。本样片的独立几何是根据接口尺寸重新生成的。

## 下载与复现

| 型号 | STEP | STL | DXF | 坐标 CSV |
|---|---|---|---|---|
| RH14-N | [STEP](../../engineering/generated/interface-coupons/STEP/ODR-CPN-RH14-N-R4.step) | [STL](../../engineering/generated/interface-coupons/STL/ODR-CPN-RH14-N-R4.stl) | [DXF](../../engineering/generated/interface-coupons/DXF/ODR-CPN-RH14-N-R4.dxf) | [CSV](../../engineering/generated/interface-coupons/coordinates/ODR-CPN-RH14-N-R4.csv) |
| RH17-B | [STEP](../../engineering/generated/interface-coupons/STEP/ODR-CPN-RH17-B-R4.step) | [STL](../../engineering/generated/interface-coupons/STL/ODR-CPN-RH17-B-R4.stl) | [DXF](../../engineering/generated/interface-coupons/DXF/ODR-CPN-RH17-B-R4.dxf) | [CSV](../../engineering/generated/interface-coupons/coordinates/ODR-CPN-RH17-B-R4.csv) |
| RH20-B | [STEP](../../engineering/generated/interface-coupons/STEP/ODR-CPN-RH20-B-R4.step) | [STL](../../engineering/generated/interface-coupons/STL/ODR-CPN-RH20-B-R4.stl) | [DXF](../../engineering/generated/interface-coupons/DXF/ODR-CPN-RH20-B-R4.dxf) | [CSV](../../engineering/generated/interface-coupons/coordinates/ODR-CPN-RH20-B-R4.csv) |
| RH25-B | [STEP](../../engineering/generated/interface-coupons/STEP/ODR-CPN-RH25-B-R4.step) | [STL](../../engineering/generated/interface-coupons/STL/ODR-CPN-RH25-B-R4.stl) | [DXF](../../engineering/generated/interface-coupons/DXF/ODR-CPN-RH25-B-R4.dxf) | [CSV](../../engineering/generated/interface-coupons/coordinates/ODR-CPN-RH25-B-R4.csv) |

运行 [build_interface_coupons.py](../../engineering/build_interface_coupons.py) 需要 Python、CadQuery、NumPy、trimesh、ezdxf、reportlab，以及含中文字符的 TrueType 字体。原厂 STEP 不参与本步骤，输入是已经提取的 JSON。

```sh
python engineering/build_interface_coupons.py --font /path/to/Chinese-capable-font.ttf
```

可通过 `--source` 和 `--output` 显式指定输入和输出目录；脚本没有用户机器目录硬编码。`verification.json` 记录输入提取文件 SHA256、每件原厂源 STEP 的 SHA256、输出几何校验和文件哈希。DXF 使用毫米，只有外轮廓、中心孔和螺钉孔三个图层；它不包含 CNC 工艺、螺纹、沉孔或表面处理定义。

## 打印和手动试装

建议 PLA 或 PETG、0.20 mm 层高、4 道壁、100% 填充；XY 平面直接贴打印床面，+Z 向上。此件不需要支撑。不要通过整体缩放补偿小孔，否则 PCD 和所有孔中心位置也会改变；先做打印机孔径校准，再使用局部孔补偿并记录数值。

打印试装阶段建议检验：外径和厚度相对标称 ±0.20，孔径为标称 +0.20/0，孔中心的 X/Y 坐标分别在 ±0.15 内。这些是本次试装样片的评估建议，不是经验证的打印机能力，也不是后续金属连接件的制造公差。最窄孔间材料区域需检查是否破损，轻微清理毛刺后再试。

试装时关节必须断电并被独立稳固支撑：

1. 核对收到的完整型号、制动版本及资料版本；不同版本不能仅凭外形复用本片。
2. 将样片轻放在输出环面，确认中心孔避开凸台，板面没有被中央凸台顶起。
3. 转动整片观察每个孔的对应关系，记录不可达、干涉、需要工具避让的位置。不要强压、敲入或靠拧紧螺钉拉平打印件。
4. 原关节的螺纹在孔内后缩；本设计没有选定螺钉长度。须先确认孔深、螺纹始端、有效啮合及底部余量，不能直接套用“板厚 + 6 mm”之类经验长度。
5. 记录实际尺寸、照片、孔偏差、打印材料和补偿设置，再决定承力转接件的配合和结构。

本次样片不承担关节、臂杆、末端或工件重量，不用于通电运动、夹持力测试或 2 kg 负载验证。样片孔阵检查通过，也只说明对应实物的孔位和避让关系通过这项检查。

## 已完成的文件检查

- CadQuery 实体有效、单一实体、解析体积相符；顶面闭合边界数量与中央孔 + 螺钉孔数量相符。
- STEP 导出后重新导入，有效性、单实体、体积通过。
- STL 重读后水密、单体；Euler 数与每件贯通孔总数一致，离散体积误差小于 0.3%。
- DXF 重读审计通过，单位为毫米；圆实体数、孔坐标及孔径与源参数一致。
- 四页中文 PDF 逐页渲染检查，确认文字、孔号、坐标表和边界布局。

可核查结果见 [verification.json](../../engineering/generated/interface-coupons/verification.json)。这些是数字文件检查，不代替实体试装或制造验收。
