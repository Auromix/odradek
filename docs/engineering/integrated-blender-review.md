<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
<!-- Required Notice: Odradek — Auromix contributors (https://github.com/Auromix/odradek) -->
# 六段连接与四瓣末端的原生 Blender 总装

本版把已经分别出图的六段金属连接、底座和 HEAD-INTEGRATED03 放入同一个可调姿态的 `.blend` 文件。7个臂轴与4个指轴均有独立控制，推杆按其两端销的位置摆动、伸缩。**这是当前结构候选的几何总装，不是完成外壳设计或制造放行的整机。**

- [原生 Blender 文件](../../engineering/generated/integrated-arm-preview/odradek-integrated-7-plus-4.blend)
- [整体检查视角](../../engineering/generated/integrated-arm-preview/arm-open-oblique.png)
- [零位结构](../../engineering/generated/integrated-arm-preview/arm-home-structure.png)
- [末端全开](../../engineering/generated/integrated-arm-preview/head-open.png)／[末端全闭](../../engineering/generated/integrated-arm-preview/head-closed.png)
- [生成与坐标证据](../../engineering/generated/integrated-arm-preview/evidence.json)／[重新打开文件的复核](../../engineering/generated/integrated-arm-preview/reopen-review.json)

![已建结构与四瓣末端](../../engineering/generated/integrated-arm-preview/arm-open-oblique.png)

## 模型包含什么

共有736个产品网格对象：六段24个原创承力件、8个底座件、7个关节目录尺寸包络、697个整头对象。每个对象保留来源、分组和体积元数据；参数、STEP、头部GLB/manifest等53份输入记录文件哈希。

连接件来自真正的原创STEP，而不是重新按示意图搭方块。头部直接使用HEAD03的命名网格，保持其正式灯片开腔、PCB包络、软垫保持键和装配坐标。7个关节在公开Blender里仍是原创目录外形包络，**没有封装原厂BREP**；真实原厂实体用于另外的[整臂碰撞研究](integrated-collision-study.md)。

臂和底座的紧固件尚未完整进入这个视觉总装；头部按HEAD03清单包含相应硬件。内部线束、关节侧腔、外观护壳、光学片保持框和中央显示实际电路尚未建成，不能从这些渲染图推定其已经可加工或布好线。

石墨色金属与琥珀灯点用于检查整臂和末端的风格关系。中央285点的环/箭头属于独立 `UI preview only - unbuilt central display` 集合，只是显示效果；没有PCB、安装或散热资格，不计入736件或质量。四瓣130/130/42/42灯点来自FPL机械快照，不能继承历史113/49点灯板的布线状态。

## 打开与调节

1. 使用Blender 4.5系列打开 `.blend`。场景保存为inspect展示姿态，四指全开。
2. 在 `11 geometric controls` 集合中选择 `J1`…`J7` 或 `FINGER_UR/UL/LL/LR`。
3. 在对象的自定义属性里修改 `q_deg`。几何随动使用保存在文件内的27条简单表达式驱动器，不依赖原生成脚本、帧回调或外部Python包。
4. `HEAD_DETACHABLE` 表达J7输出后的整头归属。产品网格、控制轴、中央UI预览与摄影灯光分集合管理，可单独隐藏。

Blender内部长度使用m，显示单位为mm。臂轴均按原始世界零位轴线建立；头face在home世界 `[0,55,804] mm`。直接拖动零件或改其父级会破坏这份受检坐标关系。

`q_deg` 的滑块上下限只是旧参数里的研究范围。它不会运行碰撞检测，也不是实机限位。历史 `reach=[0,65,0,10,0,10,0]°` 已确认存在三对肩部真实碰撞，不能执行；把它用于变换公式检查并不赋予可用资格。当前文件也没有播放动作或控制指令。肩部改型、线束和完整联合运动域需要后续版本单独验证。

## 推杆与指片的运动关系

每个指片刚体组绕其根轴转动。推杆本体围绕基端销摆动，滑杆另沿当前杆向移动；两组由同一指角计算。它们没有被简单地整体绑定到灯片上。

`β=atan2(26 cos(q−68°),123+26 sin(q−68°))`，`L=sqrt(123²+26²+2×123×26 sin(q−68°)) mm`。驱动器分别采用 `β(q)−β(0)` 和 `L(q)−L(0)`。四路机械镜像只影响基销侧向位置，所有刚体旋转均保持右手坐标。

上片闭合研究角109°、下片122°来自同一HEAD03版本。Blender从全开网格施加绝对指角，不能把已经烘焙成closed的GLB直接再次套上这一绝对角。

## 已完成的核对

| 检查 | 数量与最大误差 | 范围 |
|---|---|---|
| 臂轴层级与独立SI正运动学 | 492项，0.000134 mm以内 | 三个数学姿态的结构/固定头对象顶点；不等于姿态可达性 |
| 指片与推杆解析变换 | 1716项，0.000118 mm以内 | 四路45°、全闭与不同指角组合 |
| 独立闭合CAD对照 | 697件，包围盒差0.002744 mm以内 | 对照从BREP重新生成的closed实体，不只自查同一动画公式；网格容差门槛0.20 mm |
| 关闭自动脚本执行后重新打开 | 27驱动、492项臂顶点、697项闭合对照均通过 | 驱动器为有效简单表达式，不依赖生成时的运行环境 |

这些差值是坐标和网格一致性指标，不是物理配合公差。四张1600×1300图片已视检，整臂留有画幅余量，头部近景保留相关腕部用于观察接口；尚未完成工业设计外壳。

## 复现

先用CadQuery环境导出中间网格，再调用Blender。中间JSON约59 MB，可放在仓库外临时目录；其全部源数据均在当前候选工程文件中。

```sh
python engineering/export_integrated_arm_preview.py --output /tmp/odradek-mesh.json
blender --background --factory-startup --python engineering/blender_integrated_arm.py -- --mesh-json /tmp/odradek-mesh.json
blender --background --disable-autoexec engineering/generated/integrated-arm-preview/odradek-integrated-7-plus-4.blend --python engineering/review_integrated_blend.py -- --mesh-json /tmp/odradek-mesh.json --report engineering/generated/integrated-arm-preview/reopen-review.json
```

生成器会检查原参数、六段导出记录和头部GLB哈希。中央显示效果和渲染材质不回写精密CAD。若输入几何、器件位置、关节基准或肩部高度改变，需重新生成这一总装和受影响的碰撞/载荷证据。
