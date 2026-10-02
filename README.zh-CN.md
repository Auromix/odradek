# Odradek

**2026-10-03 arm body / 本体更新：** [A09直管与平板重做](docs/arm-body-redesign-a09.md) · [七轴查看器](docs/viewers/arm-body-a09/index.html)。当前本体目标为裸臂法兰总外负载3 kg，不装四瓣头；A08外观被否定，A09是加工与比例提案，尚非承载发布版。

**7自由度本体＋可拆四瓣发光夹爪，以朝向、张合与灯光表达主动注意力。**

[English](README.md) · [设计简报](docs/design-brief.md) · [方案比较](docs/concept-comparison.md) · [昵称候选](docs/nickname-candidates.md) · [路线图](docs/roadmap.md)

**2026-09-28保存点：** 先保存当前成果和草案，不再扩展复杂度。末端优先单输入正向同步，允许一对相对灯片主夹持；多级差动只保留作比较。[保存范围与未完成状态](docs/engineering/checkpoint-2026-09-28.md)。

Odradek 是 Auromix 面向非商业研究与爱好者公开设计资料的桌面／固定底座机械臂项目，灵感来自《死亡搁浅》中的探测器，面向实际操作任务。本体与末端的机构、外观和行为同步设计。

**当前为工程研究阶段，末端正按已确认的“一秒空载完整往返”重选驱动。** 灯片面本身就是夹持面，正常夹持是主功能。用户已确认2kg净工件另计头重、约700mm臂展、GMSL／GMSL2、EtherCAT、内走线与外置计算。P16无法满足新节拍，其CAD与电路保留为历史分支；现有7＋4总装不代表已实现新速度要求。见[最新设计输入](docs/engineering/fast-grasp-requirements01.md)。尚无制造发布版或2kg实测样机。

## R5：单驱动末端与独立本体

![单中央驱动的四瓣末端](docs/concepts/11-r5-single-drive-head.png)

一台中央隐藏电机带动四个有造型的灯瓣，发光面同时作为夹持面。本体保持七轴、细长比例与可拆工具接口。[查看末端和本体两张概念图、确认输入与机构研究顺序](docs/r5-modular-design.md)。生成图用于工业设计，实际闭合和承载以CAD、计算及样机为准。

最新产物包括[削肩灯片FORM02的STEP与二维图](docs/engineering/r5-petal-form02.md)、[先折叠后径向夹持及被动差动数学](docs/engineering/r5-stage01.md)、[eRob可拆腕接口](docs/engineering/r5-wrist-erob01.md)及[本体质量/臂展独立分析](docs/engineering/r5-body01.md)。首版目标是**盒体、瓶罐等日常物体，夹持宽约50–120mm**。新裸灯片已有连续间隙与有限接触证据；真实传动、最终全闭姿态及完整抓取范围仍待验证。较早[单滑块Blender](docs/engineering/r5-linkage-blender01.md)保留为独立比较，不能与新径向机构混为已完成总装。

[径向候选的原生 Blender 与使用说明](docs/engineering/r5-stage-blender01.md)现已包含28个真实灯片CAD网格，可查看Ø80圆柱和50×120mm长方盒的接触状态。一个平均输入与三个被动评审偏移表达差动约束；模型尚无真实传动、中央模块或时间仿真。

## 当前工程包

![既有结构检查总装，头部为历史P16分支](engineering/generated/raised-arm-integration01/blender/arm-open-oblique.png)

图中已合并24个原创连接件、加高35mm的肩架、修正后的底座和697对象的HEAD-INTEGRATED03快照。Blender中的关节仍为目录包络，臂侧紧固件、线束和外壳尚未完整集成，中央像素屏单独标为显示效果。[当前加高候选](docs/engineering/raised-arm-integration01.md)通过10个指定姿态的真实BREP检查，包括历史上发生肩部碰撞的姿态；离散几何通过仍不等于轨迹或带载资格。[当前基线与硬件选择](docs/engineering/current-baseline.md)统一列出P16条件8站分支与历史替代方案的区别。

| 入口 | 内容与范围 |
|---|---|
| [工程总览](docs/engineering/README.md) | 输入、假设、一手来源和发布清单 |
| [布局、闭合与抓取](docs/engineering/r4-layout-and-grasp.md) | 同参数实体、独立角域分离、条件抓取和名义光线检查 |
| [既有原生Blender／历史P16头](engineering/generated/raised-arm-integration01/blender/odradek-integrated-7-plus-4.blend)／[模型使用说明](docs/engineering/raised-arm-integration01.md) | 736个产品网格、11个控制量、可独立重开的推杆随动；几何检查候选 |
| [整头STEP与证据](docs/engineering/head-integrated03-study.md)／[耦合动力学](docs/engineering/articulated-dynamics-review.md) | 实际候选实体、冻结灯板位置、明确的质量与惯量代理 |
| [历史布局](docs/engineering/r4-layout-and-grasp.md)／[分组件场景](docs/engineering/subassembly-blender-review.md) | 保留早期设计阶段用于追溯 |
| [A3 装配审查图](engineering/generated/layout/ODR-R4-assembly-review.pdf) | 轴坐标、布局尺寸和正交网格视图 |
| [单指手动台架](engineering/generated/finger-fixture/README.md)／[关节接口片](docs/engineering/interface-coupon-guide.md) | 可打印、无动力的孔位与几何检查件，配尺寸图 |
| [元件 BOM](docs/engineering/hardware/bom.csv)／[双鱼眼光学台架](docs/engineering/hardware/optical-bench-build.md) | 有来源的候选及具体相机—采集板—主机链 |
| [计算与 CAD 复现](engineering/README.md) | 依赖、生成顺序、单位和限制 |

旧布局的[有限双垫接触反例](docs/engineering/finite-pad-contact-study.md)继续保留。HEAD-INTEGRATED03已合并CONTACT-02软垫及保持键、CARRIER02窄根、灯腔、灯板位置和EXT24；17项指定范围的连续几何检查通过。动态线束、公差、变形与抓取试验仍未闭合，条件性力平衡不等于2 kg实测额定负载。

## 历史R3：保留外形，检查闭合与接触

已选定上两瓣大、下两瓣小、左右对称的展开外形。双鱼眼保持上下位置并向上／下略外倾，安装角需兼顾最近夹取区域。

本轮发现三项需修正的机构假设：长短刚性板不能直接收成同深度短茧；宽板过度向中心闭合会相撞；向前包合时原来的灯面会转向工件。因此优先研究完整板、不同限位与前后错层，并将凸起软垫／承力边框布置在灯面同侧，让灯窗凹入。

[几何检查与完整推导](docs/r3-closure-study.md)给出了反例，以及一个四矩形板模型的连续角域分离结果；其通过不代表整头或有效抓取通过。下图收纳区明确为包络研究，不是最终闭合姿态。

## 当前：可拆四瓣末端

![R3 外形、相机与接触候选研究](docs/concepts/10-r3-closure-study.png)

- **本体7DOF，末端优先单驱动四瓣联动。** J7轴线垂直末端正面；用户允许1电机与另外3瓣mimic随动，不再要求四个独立驱动。准确的机构映射与被动顺应仍待设计。
- **左右各一组近邻双瓣，左右镜像、非中心对称。** 上瓣较长、下瓣较短，借鉴小鹏 logo 的分组关系；视觉成组不要求动作联动。
- **灯片就是夹指。** 向前包合时灯面转向工件，最新要求由发光面本身夹持，透光接触层与承力支承正在重构；旧尖端凸垫保留为历史接触研究。空手全闭需达到有真实间隙的机械限位；不是四尖挤到同一点或密封壳。
- **中央仅圆形 LED 屏。** 环形图案由屏幕圆周像素绘制；照明由四片承担。两个鱼眼位于屏幕局部上方和下方，分别向上／下外倾，随整头旋转。
- **可拆分界在 J7 输出法兰之后。** 单个中央隐藏执行器与端侧执行接口拟置于末端内，接口规格待定。

![七轴本体、末端分离与 J7 方向](docs/concepts/08-r2-modular-arm.png)

图中 roll 表达有限角度姿态变化，角度尚未定义。开合、抓取和收拢态需在同版 CAD 中验证；R2 的紧凑保护茧原图已退为历史假设。机械呼吸仅在空手且任务允许时进行；表达动作不改变正在保持的夹持。

## 3／4／5 片的艺术比较

![同尺度三片、四片、五片比较](docs/concepts/07-r2-petal-count-study.png)

| 片数 | 视觉气质 | 当前定位 |
| --- | --- | --- |
| 3 | 三角剪影、轻巧，偏探测仪或异形工具 | 艺术比较 |
| **4** | 两组有亲疏关系，兼有工具感和生命感 | **四瓣造型主线，允许单驱动联动** |
| 5 | 轮廓更密，偏花冠或生物；偏置一片才更容易产生手掌联想 | 艺术比较 |

片数不等于主动自由度。最新四瓣主线允许单驱动联动；若改变片数，需重新定义机构，不能直接复用历史四个独立开合坐标。

## 昵称候选

建议优先考虑 **Odi／欧迪**：保留与 Odradek 的联系，只有两个音节。**Lumo／露莫** 更偏灯光与呼吸感。其他候选为 Noto／诺托、Piko／皮可、Tavi／塔维、Filo／菲洛，见[完整比较](docs/nickname-candidates.md)。昵称尚未选定，项目和仓库名保持 Odradek。

## 过程与下一步

调研 → R0 形态发散 → R1 灯片夹爪 → R2 7＋4 DOF 与模块化末端 → R3 外形与闭合 → **R4 元件、数学、CAD 与几何台架** → 完整承力连接及动态线束 → 样机任务与制造验证。

R0／R1 的原图和提示词保留在[图集](docs/gallery.html)。R1 的独立实体灯环与片数候选已由 R2 取代；旧图不代表当前要求。

- [设计简报与未知输入](docs/design-brief.md)
- [方案比较](docs/concept-comparison.md)与[行为草案](docs/behavior-spec.md)
- [决策记录](docs/decisions.md)与[路线图](docs/roadmap.md)
- [参考来源](docs/sources.md)、[生成方式和提示词](docs/generation.md)、[图像审阅记录](docs/review-notes.md)

当前继续推进肩部可用活动范围、安装后的保持与温升、完整控制器及动态线束、接触/紧固件资格和制造公差，见[工程发布清单](docs/engineering/release-checklist.md)。

## 许可与商业授权

新增原创图稿、文档、工程研究脚本、参数与模型采用 **[CC BY-NC 4.0（署名—非商业性使用）](LICENSE)**，允许非商业研究、学习、爱好者使用与修改分享；分享时须署名、保留许可信息并注明修改。需要依赖该许可的商业使用，须[联系作者取得单独书面授权](https://github.com/Auromix/odradek/issues/new?template=commercial-license.yml)。

**截至 `2d7d00f` 的 Apache-2.0 授权及 `698736a` 至 `c4f1fde` 中标明 PolyForm 的脚本授权继续有效。** 新政策不追溯收回旧权利，详见[许可范围与历史](LICENSING.md)，其中也明确 CC 用于工程研究软件的局限。正式控制固件需另选合适的软件许可；版权声明不等于对功能性硬件制造的全面限制。

带非商业限制的公开设计不属于 OSI 定义的开源项目。欢迎按[贡献说明](CONTRIBUTING.md)参与。第三方参考原图未收录，也不纳入本项目许可；项目与《死亡搁浅》、KOJIMA PRODUCTIONS 或 XPENG 无官方关联。
