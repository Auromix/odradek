# 可复现计算与建模

## 当前底座唯一入口

[B06-COMPACT-02](base_b06/README.md)是已确认的底座外观源；前鼻、双翼和颈台一体，五件打印结构。所有本体模块遵循[底座同源规则](../docs/engineering/base-authority.md)，读取同一模型，不在本体目录维护可编辑的替代底座。B04/B05与下文R4底座只作历史研究。

新增原创工程研究源稿、参数及模型按 CC BY-NC 4.0 共享。历史 Apache / PolyForm 授权继续有效；CC 缺少软件专用条款的限制见 [LICENSING.md](../LICENSING.md)。依赖库保留各自许可，不打包重新许可。

`kinematics.py` 使用空间轴乘积形式计算位姿、Jacobian、重力、质量矩阵及数值 Christoffel 项；`gripper.py` 定义四片各自的径向转动与接触力映射。所有计算使用米、千克、秒和弧度；外部配置中的角度字段名称明确带 `_deg`。

代码不连接硬件、不发送运动指令。数值 IK 不包含碰撞或线束约束，质量和惯量假设必须在使用结果前核对。摩擦抓持下界不能作为力闭合证明。

## R5当前模块入口

[FORM02真实灯片](../docs/engineering/r5-petal-form02.md) → [STAGE01折叠/径向数学](../docs/engineering/r5-stage01.md) → [STAGE-BLENDER01原生模型](../docs/engineering/r5-stage-blender01.md)构成当前裸片研究链。Blender生成器为 `r5_stage_blender01.py`，先由CadQuery准备网格，再由Blender生成并以禁用自动脚本的进程重开核对。具体命令、输入及检查边界见模型说明。新的[eRob腕部接口](../docs/engineering/r5-wrist-erob01.md)单独保存，不与旧RH/P16整臂混成制造总装。

## 环境与单位

本版实际使用 Python 3.12.14、CadQuery 2.8.0 / OCP 7.9.3.1.1、Blender 4.5.14 LTS；其余 Python 版本见 [requirements-lock.txt](requirements-lock.txt)。记录的是本次环境快照，不保证所有平台均有对应二进制包。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r engineering/requirements-lock.txt
```

以下命令从仓库根目录运行，`python` 应指向上述环境。Blender 使用自身 Python，不要往其中安装 CadQuery。需要中文图纸的命令通过 `--font` 传入可用的中文 TrueType 字体；字体不随项目分发。

参数源为 [r4-layout.json](parameters/r4-layout.json)。CAD 输入输出为 mm；数学核心为 m / kg / s / rad；Blender 网格转换为 m 后以 mm 显示。修改几何参数后必须按依赖重生成，不能只改渲染图。

## 数学与静力

```sh
python engineering/verify_math.py
python engineering/arm_screening.py
python engineering/head_mass_sensitivity.py
python engineering/review_arm_screening.py > docs/engineering/analysis/arm-static-independent-review.json
python engineering/grasp_screening.py
python engineering/finite_pad_contacts.py
python engineering/structure_screening.py
python engineering/structure_screening.py --check
```

数学回归覆盖解析单摆、耦合 2R、外力矩、Jacobian、势能梯度、动力学能量恒等式、可达/不可达 IK 和接触虚功。机械臂静力复核使用独立旋转递推与重量叉乘；梁模型有 60 项公式/数值检查。它们均不代表硬件验证。当前实机惯量、摩擦、转子耦合和热条件未知，不从这些检查推导额定速度或精度。

有限双垫研究读取已有主 CAD，计算物体先接触的实体、八点共享四轴力矩以及 BREP 反例。当前 Ø80 圆柱先碰骨架/灯窗，不能由旧单点例题推出可抓取；完整结果见[接触研究](../docs/engineering/finite-pad-contact-study.md)。

## 几何、图纸与 Blender

```sh
python engineering/build_layout.py
python engineering/certify_petal_separation.py
python engineering/check_layout.py
python engineering/check_optical_sightlines.py
python engineering/draw_layout.py --font /path/to/Chinese-font.ttf
blender --background --factory-startup --python engineering/build_blender.py
```

`build_layout.py` 读取当前参数、接口提取记录及已保存的指驱动布置输入；输出解析 STEP、单件 STEP/STL 和 manifest。STEP 可能包含导出时间戳，重新生成后的文件哈希不必字节一致；须重新生成引用这些文件哈希的证书并审阅几何变化。更换传动、支承或结构不能只复制旧分析结论。

分离证明只覆盖四片结构、灯窗和八垫的名义平面实体；采样碰撞另列对象和范围。碰撞布尔必须遍历每个 solid；直接对厂商 compound 求交会漏报，详见[安装接口研究](../docs/engineering/mount-interface-study.md)。

Blender 保存 7＋4 层级和 360 帧几何演示，另输出三视角渲染。原生层级 TCP 与独立矩阵计算在三姿态下检查到小于 0.001 mm。动画不含真实速度、加速度、控制或抓取轨迹资格验证。

新增 LINK56、固定底座及 CONTACT-02 的[原生分组件检查包](../docs/engineering/subassembly-blender-review.md)独立保存为 `generated/component-reviews/odradek-r4-subassemblies.blend`，含三个场景和五张渲染。使用 `export_component_reviews.py --output /tmp/odradek-component-meshes.json` 从已有 STEP 导出，然后由 Blender 执行 `blender_component_reviews.py -- --mesh-json /tmp/odradek-component-meshes.json`。它没有将三个研究机械集成为新整臂。

更新的[整体结构检查包](../docs/engineering/integrated-blender-review.md)保存为 `generated/integrated-arm-preview/odradek-integrated-7-plus-4.blend`，已合并六段24原创连接件、底座和HEAD03，736产品网格、11控制量。复现用 `export_integrated_arm_preview.py` → `blender_integrated_arm.py` → `review_integrated_blend.py`；具体命令与27条持久驱动、697件独立闭合CAD对照见说明。历史reach已查到肩部真实碰撞，不是可执行姿态；外壳、线束和完整臂侧紧固件尚未建成。

独立 [P16-PACK-01](../docs/engineering/gripper-linear-packaging-study.md) 把真实线性执行器接口、双剪销叉和近根支承接到 CONTACT02，尚缺整头载体。执行 `python engineering/p16_packaging_study.py --vendor-dir /path/to/vendor-reference` 后，再运行 `python engineering/p16_pin_stack_drawing.py` 和 `python engineering/p16_packaging_verify.py --vendor-dir /path/to/vendor-reference`。原厂CAD仅作为本地核对输入，公开包只包含原创保守包络；使用跳过检查的调试选项不能复用完整验证结论。

## 无动力打印件与接口研究

独立上灯片 [ULP-02原生KiCad](electronics/upper-petal-prototype/ulp02/kicad/README.md)含真实四层PCB、原理图、重放布线、逐针核对和C99例程。执行其 `rebuild.py --kicad-cli /path/to/kicad-cli --kicad-python /path/to/kicad-python` 可从源完整重建并实际运行ERC/DRC、317针网表和113灯点校验，再导出Gerber/钻孔审查文件。已在KiCad10.0.6独立重跑成功；这是电测样片，不是已经适配CONTACT02的正式灯板。

```sh
python engineering/build_interface_coupons.py --font /path/to/Chinese-font.ttf
python engineering/build_finger_fixture.py --font /path/to/Chinese-font.ttf
```

接口片使用已提取的真实孔坐标；单指台架包含打印方向、孔坐标、STEP/STL、五页尺寸图及几何限位检查。只能用于无动力形态/装配；与金属生产设计不同。厂商 STEP 不重新分发，需要重新提取或运行安装研究时，按对应[接口研究说明](../docs/engineering/mount-interface-study.md)传入自行取得的原厂文件。

## 文件成熟度

`generated/layout` 是 74 组几何布局，含明显占位及已记录的待修正问题；`generated/interface-coupons` 和 `generated/finger-fixture` 是无载打印检查件；`generated/mount-study` 是安装接口候选。**均不是完整制造发布包。** 参见[发布清单](../docs/engineering/release-checklist.md)，不要把能打开 STEP、网格水密或有限采样不碰撞等同于可承受 2 kg。
