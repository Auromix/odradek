# 工程开发记录｜R4历史与R5单驱动深化

## 当前底座唯一入口

[B06-COMPACT-02](../../engineering/base_b06/README.md)为已确认外观依据；[底座同源规则](base-authority.md)定义本体引用、只读快照和更新后的联检。B04/B05及下表R4固定底座属于历史，不与B06并列维护。

本轮从概念研究进入参数化工程设计。用户要求持续推进硬件选型、机械臂与夹爪数学、Blender 结构模型及制造图，并按完成部分提交。本目录将输入、计算、供应商证据、设计产物和验证记录分别维护。

先看[FAST-GRASP01最新需求](fast-grasp-requirements01.md)和[当前基线](current-baseline.md)：灯片面必须用于正常夹持，空载完整开合≤1秒。P16退出主末端路线；既有模型与电路保留为可复现研究。七轴本体、中央屏、灯板及相机继续作为新方案输入，不能把历史研究混成已满足新要求的采购配置。

[R5单驱动末端与独立本体](../r5-modular-design.md)包含最新概念图及确认输入。[SHOULDER-RAISE03](shoulder-raise03.md)已合并让位钢块与具体螺钉；[HEAD04](head-integrated04.md)和[HEAD-POWER01](hardware/head-power01.md)归档为旧P16集成证据。

R5最新工程入口：[削肩灯片FORM02与二维图](r5-petal-form02.md)、[折叠后径向夹持/差动数学](r5-stage01.md)、[eRob可拆腕接口](r5-wrist-erob01.md)、[独立本体质量/臂展](r5-body01.md)、[轻量EtherCAT关节](hardware/r5-light-joint01.md)、[透明夹持面材料与紧固件](hardware/r5-petal-hardware01.md)。盒体、瓶罐50–120mm为确认目标，现阶段没有完整抓取范围资格。较早[单滑块数学](r5-link01.md)、[一个主控的原生Blender](r5-linkage-blender01.md)和[折返带传动](hardware/r5-folded-drive01.md)保留为固定根轴比较方案，不与新径向机构混算。

## 当前可查看的工程结果

| 部分 | 入口 | 已有证据及边界 |
|---|---|---|
| 两瓣主夹持新口径 | [TWOCONTACT01](r5-twocontact01.md) | 同步四瓣先夹盒体较大尺寸；每片约49N初筛与804N根轴承反力，有限接触斑抗转仍是条件模型 |
| 当前径向候选 Blender | [STAGE-BLENDER01](r5-stage-blender01.md) | 28个真实灯片CAD网格，展示圆柱与长方盒的不同半径接触；一个主动输入加被动评审偏移，未模拟真实差动传动 |
| 径向折叠随动器与根轴承 | [CAM-HARDWARE01](hardware/r5-cam-hardware01.md) | CFS4、双607/8-2Z、真实安装栈与逐片受力；保留大悬伸、远端接触及低摩擦下的不足 |
| 径向载体与分体根轴 | [CARRIER01](r5-carrier01.md) | 40种单件、实际短轴/曲柄/轴承/导槽及2页名义尺寸图；内件C4、无硬止挡/掌体/滑轨，256.53mm外包尚未外观协同 |
| 差动钢索、滑轮与终端 | [CABLE-HARDWARE01](hardware/r5-cable-hardware01.md) | 一套升级索轮候选、名义50/100N条件筛选；全公差、端部保持力和完整索路尚未验证 |
| 七轮差动索路包装 | [ROUTE01](r5-route01.md) | 恒索长中心线、真实轮径、偏置支承载荷与独立复算；仅轮组已到根铰后239.05mm，不作为紧凑头定案 |
| 单电机被动开合动力学 | [PASSIVE01](r5-passive01.md) | 上下瓣不同步与首次止挡的独立数学核对；先碰止挡后不能继续套用绷紧钢索约束，完整周期仍未验证 |
| 实际载体质量与回位搜索 | [PASSIVE02](r5-passive02.md) | 加入0.689221kg已建移动件、238组有限参数；不能实现完整同步周期，强阻尼和静态夹力的代价已量化 |
| eRob两轴腕部连接 | [WRIST-PAIR01](r5-wrist-pair01.md) | 一体连接件和薄裙接口、5页图与无载样件；真实固定侧螺钉纳入，线束/完整牙/强度仍待闭合 |
| eRob J5至J6细长连接 | [LINK56-EROB01](r5-link56-erob01.md) | 282g原创闭口梁、孔/工具/装入/局部运动与静载证据；底部转线具体反例保留，完整内束和整体强度未放行 |
| 单驱动运动与夹持需求 | [FAST-KIN01](fast-finger-kin01.md) | 真实单位的虚功、非线性映射项、1秒空载轨迹、接触顺应反例及转子回生；机构仍待综合 |
| 中央执行器候选 | [FAST-DRIVE01](hardware/fast-drive01.md) | 单3274+32GPT HT50与AK70/直接丝杆比较；空载速度筛查通过，静止热及实际夹力未获得资格 |
| 结构布局 | [R4 布局、闭合与抓取](r4-layout-and-grasp.md) | 同参数 74 组 STEP、7＋4 Blender、A3评审图；连接与动态线束未完整 |
| 本体数学 | [运动学与动力学](arm-mathematics.md)／[静力独立审查](arm-screening-review.md) | 解析回归、独立重量叉乘、质心敏感性；非实机额定值 |
| 独立动力学复核 | [DYNAMICS-REVIEW01](rigid-body-dynamics-review.md) | 五段21实体CAD惯量；24组独立力/矩法、拉格朗日与能量检查一致，剩余质量代理/转子/热仍未验证 |
| 7＋4耦合动力学 | [DYNAMICS-11DOF01](articulated-dynamics-review.md) | 六段24实体＋整头13刚体，去除重复L7预算；解析Jacobian/直接刚体力矩/能量/推杆虚功一致，未计量余量与夹持接触负载仍需加入 |
| 夹爪数学 | [当前抓取 LP 审查](grasp-screening-review.md)／[独立角域分离](petal-certificate-review.md) | 72 个条件接触场景；16 实体独立角域闭合证明，不含完整支承 |
| 实际物体接触 | [有限双垫研究](finite-pad-contact-study.md) | 八点共享四个指轴；Ø80 圆柱先碰骨架/灯窗，接触结构待修正 |
| 双垫受力分担 | [最低共同力矩上限](paired-pad-loadsharing.md) | 90种分担/摩擦/直径；区分一组最小夹力解与最低所需驱动上限 |
| 片尖接触鞋 | [CONTACT-02](distal-contact-study.md) | 150/100 mm 长短片、64 项实体复核；改善指定圆柱接触，驱动力矩仍需匹配 |
| 接触材料试片 | [双型四腔浇注模具](contact-pad-prototype.md) | STEP/STL/DXF/两页图纸；未打印/浇注，不含保持结构或承载资格 |
| 软垫保持候选 | [贯穿浇注键](contact-pad-retention-study.md) | 8个实体与两页特征图，保持名义外轮廓；偏心剥离和材料抗撕裂仍待验证 |
| J5→J6实体连接 | [LINK56-01](link56-structure-study.md) | 六件原创结构、40紧固件、六页图与分步装配；有效螺纹/预紧/局部强度未放行 |
| J1→J2肩架 | [LINK12-01](link12-structure-study.md) | 三件原创结构、五页图及J2连续插入证明；0.745 kg含紧固预算，预紧/材料/行程未放行 |
| J2→J3实体连接 | [LINK23-01](link23-structure-study.md) | 三件原创结构、28螺钉、五页图与四步连续装入证明；完整牙/预紧/全行程未放行 |
| J3→J4实体连接 | [LINK34-01](link34-structure-study.md) | 六件原创结构、40螺钉、六页图；q3相对J2/L23全周和连续装配已检查；后环接触刚度/预紧/完整牙待验证 |
| J4→J5实体连接 | [LINK45-01](link45-structure-study.md) | 三件原创结构、28个已知螺钉形状、六页图；局部q4/q5连续避让和装入已检查；动态相机线首弯存在明确碰撞 |
| 新增部件 Blender | [三个原生场景](subassembly-blender-review.md) | 连接件、底座和四指；五张渲染、12项层级变换检查，尚非新整机装配 |
| 当前肩部抬升总装 | [RAISED-ARM-INTEGRATION01](raised-arm-integration01.md) | +35mm肩架、736网格/11控制、10个真实实体姿态无交叠、派生数学模型独立通过；全臂路径/线束/结构强度未放行 |
| 原版结构 Blender 总装 | [原736对象与11个控制](integrated-blender-review.md) | 历史原版保留，reach存在肩部碰撞；由抬升候选继续推进 |
| 六段承力连接 | [真实接口与空间审查](link-connection-plan.md) | 全部接触面/孔阵；发现肩部螺钉及两段旧梁干涉 |
| 真实连接质量回算 | [LOADS-02肩架集成](shoulder-mass-integration.md)／[LOADS-01](candidate-loads.md) | LINK12+LINK56九实体惯量/COM回填；重头情景与底座重算，仍非整机载荷上限 |
| 末端质量影响 | [3.5–4.5 kg 敏感性](head-mass-sensitivity.md) | 2 kg净物体另计；局部搜索及全域保守界，不替代动态/热选型 |
| 材料与梁 | [截面筛选](structure-screening.md) | 6061-T6 闭口矩形梁与双管比较；不含完整连接柔度 |
| 底座 | [开腔底座及倾覆计算](base-structure-study.md) | 5种原创零件、8件装配、4页图；固定到桌架的候选，未承载放行 |
| 历史直线指驱动 | [LINEAR-01](linear-finger-drive-study.md) | 独立曲柄正逆解／速度／夹力；单程约18秒，已因1秒空载往返要求退出主路线 |
| 四路推杆控制候选 | [P16-CTRL01](p16-control-interface.md) | 4×DRV8874、12V/6A外置电源、反馈反解和静态限流角落；8从站为条件分支，实际PCB/力与占空未验证 |
| 真实直线驱动封装 | [P16-PACK-01](gripper-linear-packaging-study.md) | 原厂配合、双叉肩轴与四组独立运动；建模1.423 kg，后伸14 mm，载体/J7路径待补 |
| 窄根可拆接口 | [SUPPORT-03](gripper-root-support-study.md) | 真实键轴、叉、螺钉与捕获螺母；完整名义角域避让通过，公差/强度未放行 |
| 指轴支承 | [单指双支承与四组反例](gripper-shaft-support-study.md) | 修正带轮真实宽度，否定旧紧凑切向布局；正在重新布置传动 |
| 接口 | [试装片](interface-coupon-guide.md)／[J1与J7安装](mount-interface-study.md) | 原厂真实孔位、逐实体避让、原创尺寸图；螺纹有效起点等未冻结 |
| 打印台架 | [单指手动台架](../../engineering/generated/finger-fixture/README.md) | 四件打印件与五页图纸，无动力无载 |
| 元件 | [主 BOM](hardware/bom.csv)／[BOM口径](hardware/bom-notes.md) | 候选、blocked 和 TBD 逐项区分，不是一键采购整机表 |
| 关节运行与接口证据 | [RH-OPERATION-EVIDENCE01](rh-operation-evidence.md) | 四精确型号、官方ESI与固件关系；确认B闸无需独立外供24V、J7 N无闸；零速热额定/停止时序/满牙区间仍缺 |
| 历史P16控制电路 | [HEAD-CTRL02](hardware/head-ctrl02.md) | 100脚MCU/ESC、四路H桥、242器件原生电路；ERC0、833连接脚一致；8站条件分支，无PCB/通电资格 |
| 控制器具体被动件 | [HEAD-PASSIVES01](hardware/head-passives01.md) | 193个待定位置补齐MPN、23种板上料号及维修帽；11处封装变更、128温漂端点，未修改冻结电路或放行PCB |
| 当前内走线 | [HARNESS02](hardware/internal-harness02.md) | 真实孔与装壳FAKRA、J5缓S弯；夹持策略和动态长度仍待闭合 |
| 历史BLDC电气 | [架构](electrical-architecture.svg)／[旧线束](harness-and-connectors.md) | 7本体＋4指伺服＋1头IO，共12站，仅属BLDC替代分支 |
| 动态相机线补查 | [CAM-CABLE02](camera-cable-refresh.md) | CG03现行PDF、R34.5/R37候选及资料冲突；半径较小的候选未获动态/通道资格 |
| 工件可见性 | [实际圆柱遮挡](grasp-object-visibility.md) | 两相机可见端面45采样点；八接触点被工件遮住，需独立接触反馈 |
| 光学台架 | [采购和搭建](hardware/optical-bench-build.md) | 双鱼眼、Duo采集、AGX Orin及固定驱动链，尚未实装 |
| 单轴台架 | [采购和搭建](hardware/single-axis-bench-build.md) | IPC、电源、原厂通信转接及未放行针脚/保护项 |
| 上灯片电子样片 | [ULP-02 原生四层PCB](hardware/upper-petal-ulp02.md)／[ULP-01历史电路](hardware/upper-petal-prototype.md) | 113 LED、134器件、317针、39网；实跑ERC/DRC/未连/网表一致性均0，已导出制造审查文件，未实测或装机放行 |
| 灯片真实层叠 | [电子腔与PCB安装](led-petal-pocket-study.md) | 4.45 mm普通层叠、安装柱/低头螺钉和净截面计算；GH/线束与正式灯板未集成 |
| 正式灯板适配 | [上下片130/42点阵候选](final-petal-board-fit-analysis.md) | 212项实体包络容纳检查；侧插GH、焊高/局部深腔与热桥待ECAD/MCAD联合收敛 |
| 上下片原生电路 | [FPL-01](hardware/final-petal-fpl01.md) | 130/42点、六层0.8mm候选；完整重建ERC/DRC/未连/网表一致性均0，位置与HEAD03一致；层叠/填孔/去耦/温升未制造放行 |
| 腕部承力连接 | [J6—J7三件结构](link67-structure-study.md) | 24螺钉、零位/工具/J7连续装入已检查；末端旋转碰撞和生产公差未闭合 |
| 头部腕区避让 | [24mm加高与连续证明](wrist-extension-study.md) | q5/q7±90、q6±90及四指独立范围，头对相关腕区名义下界2.9mm；未含全臂/线束/受载公差 |
| 整臂真实实体筛查 | [六态与LINK67连续转动](integrated-collision-study.md) | zero/inspect两种指态无新增交叠；历史reach肩部有3对真实碰撞，不可执行；LINK67自身对J6/L56覆盖q6±100，尚非完整联合运动域 |
| 现状肩部几何边界 | [SHOULDER-DOMAIN01](shoulder-domain-01.md) | q2±25局部连续下界1.245mm、±20为2.643mm；首次阻塞约±27.42°，不改实机控制限位 |
| 肩部抬升候选 | [SHOULDER-RAISE01](shoulder-raise-study.md) | J2及下游抬高35mm、加长真实后叉；局部q2±90连续域最小4mm，增重0.127kg；整臂联动/结构刚度未放行 |
| 加高肩架受力初筛 | [SHOULDER-RAISE-STRENGTH01](shoulder-raise-strength-study.md) | 真实77.8mm跨度、13状态反力、孔组/净截面/梁族参照；识别薄曲环与铝牙边缘问题，未做FEA或承载放行 |
| 加强肩架候选 | [SHOULDER-RAISE02](shoulder-raise02-study.md) | 厚后环、双后柱、8块钢螺纹块；名义装入与局部运动通过，金属增重0.563117kg；真实接触/预紧未放行 |
| 肩架采购条件 | [SHOULDER-PROC01](hardware/shoulder-procurement01.md) | 6061-T651厚板、完整坯料包含检查、M4×100具体候选；受控公差/有效螺纹/材质批次仍待确认 |
| 肩部尾盖接口避让 | [SHOULDER-PORT01](shoulder-port01.md) | 两块钢件34→38mm独立候选、36连续开口通道与84原厂实体检查；未把开口通行当真实插头插拔资格 |
| 完整末端载体 | [P16-CARRIER-01](p16-carrier-study.md) | 四轴承座/P16基叉/J7后架/双鱼眼前架及236实体端态；2.727kg已建模型，根部小间隙与腕旋转仍需修订 |
| 灯爪近根修订 | [P16-CARRIER-02](p16-carrier02-study.md) | 四路同轴支承全角域名义间隙1mm；增厚钢桥、孔后截面和反力已计算，2.747kg已建模型；延伸件/正式灯板待合并 |
| 四瓣整头集成 | [HEAD-INTEGRATED03](head-integrated03-study.md) | CARRIER02＋灯腔/软垫保持＋FPL机械快照＋EXT24；两态各697实体、17项连续检查，计量模型2.802kg、规划2.987～3.252kg；电气路由/线束/护壳未定版 |
| 整头质量与惯量 | [HEAD-MASS04](head-mass04-study.md) | 262项聚合为13个刚体、重2.802kg；精确实体积分与目录惯量代理分列，P16质量分配/未知185～450g预算明确，不重复旧L7占位 |
| 历史灯光与IO | [HLIO01的609点研究](hardware/head-lighting-io-selection.md) | 历史285+2×113+2×49；当前FPL01四片344、中央拟285，合计629点，电源预算不能混用 |
| 末端控制板空间 | [HEAD-CTRL-VOLUME01](head-control-volume01.md) | 56×64×30mm完整电子装配预留，固定件最小2mm、四指/P16连续分离；实际PCB/插头/支架/热路径尚未集成 |
| 中央圆屏安装 | [CD-MOUNT01](central-display-mount01.md)／[独立装拆审查](central-display-review01.md) | 285点、Ø60PCB、杯座/压框/窗口/侧耳、GH12参考；连续避让和全开装拆空间通过，材料/公差/实际中央板与线束待闭合 |
| 中央屏几何样件图 | [CD-DRAW01](central-display-prototype01.md) | 4页A3、9份mm DXF、4个无电打印样件，保留杯座前后不同截面；不是金属制造公差版 |
| 中央屏原生电路 | [CD-EC01](hardware/central-display-cd01.md) | 285点/318器件、双LP5860、GH12逐针与ERC通过；PCB、热与整头装配另行审查 |
| 中央屏六层PCB | [CD-PCB01](hardware/central-display-pcb01.md) | 318器件、285点实际布线；独立原生DRC/未连/原理图一致性均为0，背面33器件MCAD分实体最大盒与规划包络；19个焊盘关联通孔须填孔盖铜审查 |
| 复现 | [运行说明](../../engineering/README.md) | 固定依赖、生成顺序、单位与输出边界 |
| 肩部实体刚度比较 | [SHOULDER-FEA01](shoulder-fea01.md) | 8网格24解、线弹性二次四面体、主收敛与同支承敏感性分开；尚不是螺栓接触/疲劳/整臂负载资格 |
| 放行差距 | [发布检查清单](release-checklist.md) | 对应证据和实际未完成事项 |

## 已确认输入

| 项目 | 约束 |
| --- | --- |
| 使用形态 | 桌面或固定底座，执行实际操作任务 |
| 外形 | 细长、科幻机甲感；石墨色承力结构、克制的金属／琥珀色细节，与已选四瓣头部搭配 |
| 自由度 | 本体7轴，J7轴线垂直末端正面；最新末端允许1电机＋3瓣mimic，不要求4独立驱动 |
| 末端 | 上两瓣大、下两瓣小、左右镜像；灯片兼作夹指；中央圆 LED 屏；上下两鱼眼分别上下外倾 |
| 载荷要求 | 用户已确认2kg工件净重，另计可拆末端模块自重 |
| 臂展目标 | 用户已确认约700mm，按肩关节到工具中心理解；当前零姿态746mm布局仍需工作空间审查 |
| 相机接口 | 用户已确认GMSL／GMSL2同轴接口；具体完整链路仍需兼容和动态线束验证 |
| 通信 | EtherCAT；图像接口另行选型，不把相机视频封入运动总线 |
| 布线 | 内走线；各轴有限转角，与线束扭转和弯曲寿命共同确定 |
| 计算 | 控制器与视觉计算可外置；本体主要承担执行、驱动及接口导出 |
| 制造路线 | 首先 3D 打印验证形态／装配，再使用金属制造承力结构 |
| 工作方式 | 持续推进、分部分 commit；已有 GitHub 同步授权继续有效 |

## 工作假设与已确认状态

2026-09-27的[用户确认记录](confirmed-inputs-2026-09-27.md)取代旧文稿中A01、A02、A04的待确认状态。旧参数文件保留其计算快照，不会因确认动作自动改变几何或额定值。

| 编号 | 假设 | 对结果的影响 |
| --- | --- | --- |
| A01 → 已确认 | 2kg净工件，另计可拆末端模块 | 与当前研究计算口径一致 |
| A02 → 已确认近似目标 | 肩关节到TCP约700mm；当前抬升布局零姿态约746mm，旧R4-layout-03约722.10mm | 不是全姿态最大值或可达球半径；有效工作空间由关节和碰撞约束决定 |
| A03 | 旧主参数仍保留2 kg头部假设。P16条件分支HEAD-INTEGRATED03可计量模型2.802 kg、规划2.987～3.252 kg；历史直角驱动分支规划3.577～4.252 kg，另有3.5～4.5 kg预算头载荷研究 | P16已因1秒空载往返要求退出主路线，新伺服头须重新称量/计算；所有质量均非实重，计算须声明具体分支与COM |
| A04 → 已确认类别 | 相机使用GMSL／GMSL2同轴接口 | 具体相机、视频采集板、线缆和连接器必须形成经验证的兼容链 |
| A05 | 初期为低速桌面任务，运动周期、加速度和精度尚未给定 | 初步静载筛选不能证明连续热性能、动态寿命或精度 |

## 交付与提交顺序

1. 工程输入、许可边界、可追溯参数和验证计划。
2. 供应商一手资料、关节／电气／光学／手指候选与选型差距。
3. 同源机械臂与夹爪参数、运动学、力矩、接触和结构计算及独立数值检查。
4. 精确实体 CAD、可打印分件与同参数 Blender 装配／动作模型。
5. 对应真实零件的尺寸图、BOM、装配和线束文件；依供应商图纸／分析证据逐件提升成熟度。
6. 交叉检查几何、图纸、数学和选型；发布可复现工程包与未关闭事项。

## 成熟度标识

- **设计输入**：用户已确认，或明确编号的工作假设。
- **候选**：有可追溯型号与数据，但兼容性、尺寸或负载条件还未全部满足。
- **计算通过**：仅在注明模型和载荷范围内通过；不能扩展为样机测试通过。
- **可打印形态件**：几何闭合并适合形态装配验证，不代表可带 2 kg 负载运行。
- **制造评审图**：包含尺寸与工艺意图，但还存在明确的冻结项。
- **制造发布图**：关键接口、材料、尺寸、公差、载荷及装配闭环已核验，并完成对应制造审核；不得由渲染图或包络模型自动取得该标识。

当前没有制造发布图，也没有 2 kg 样机试验结论。研发过程将持续记录并解决差距，不把未知孔位、线缆寿命、驱动安全功能或摩擦系数填成确认事实。

## 精确几何与 Blender 分工

参数文件是结构、运动学、BOM 和出图的共同输入。CadQuery／OpenCascade 的边界实体用于 STEP、STL、截面与尺寸依据；Blender 用于装配层级、关节运动、造型与内走线展示。Blender 的网格渲染不代替精密配合与公差定义。

历史外形依据见 [R3 设计简报](../design-brief.md)及[夹片闭合研究](../r3-closure-study.md)。
