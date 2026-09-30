<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# B02 自设计底座：出图与检查

日期：2026-09-30。使用内置 image_gen，未使用 CLI/API fallback。

## 输入与范围

- 用户最新要求：撤销现成桌夹/托架总成的采购拼装限制，授权自行设计。
- 外观依据：[已选 B 收腰盾形](../selected/base-b-shield.png)，已先读取原图。
- 输出：[base-b-custom02.png](base-b-custom02.png)，1536 × 1024。
- 内容：同一提案的外观与下挂盒、拆壳金属骨架、桌边侧视；没有新增 A/C 造型分支。
- 当前只是沿 B 继续深化的结构构想，存放于 proposals，不覆盖 selected 中的原参考。
- 完整设计说明：[底座 B](../../base-design-study01.md)。

## 视觉与结构意图检查

已逐图查看生成结果：

- 保留收腰盾形、钝前端、圆润边缘、石墨大切面、少量金色及前部小琥珀灯。
- 拆壳图表达左右两侧金属夹体、上板和下横梁；两个螺杆位于桌下，向桌板底面施压。
- 桌边视图用一实一淡的螺杆表达前后可见性，不解释为增加第三个夹紧点。
- 下挂盒有底托和侧向挡件，图中表达独立支架连接；这是未选盒体的空间占位。
- 六角工具箭头位于盒体前方、螺杆下方，表达需要保留工具入口。
- 标题、三个视图名和布置提案说明可读。

限制：右下虽标“桌边剖面”，实际为示意侧视/局部透视，不是按剖切规则或同一 CAD 导出的制造剖视图。原图中的螺杆头、压垫连接、板件转角、螺栓孔、盒架遮挡关系与线缆弯曲尚非精确几何；不能据画面确认接触、装配可达性或 GMSL 弯曲半径。后仓盖开启和盒子侧向取出路径没有完整展开，须在后续布置模型验证。图中有金属层叠视觉，不据此锁定板厚或实体材料。

结构审阅提出并已写入说明：两侧板需金属横向连接，上板需真实桌面保护垫，盒架不得阻挡两个螺杆的全行程工具入口，插接区与夹具运动区分开，盒子独立取下，先用金属板件分件组装。未开展载荷计算、CAD 干涉、有限元、打印试装或带载试验。

## 原样生成提示词

```text
Use case: stylized-concept, reference-guided industrial design.
Reference image: the supplied ODRADEK B shield-shaped base board is the authoritative appearance reference. Continue ONLY that B silhouette, no alternative styles.
Task: make one landscape industrial design sketch sheet for a CUSTOM-DESIGNED desktop robot base, hidden desk clamp, and independent underslung controller holder. It is a proposed architecture, not a manufacturing drawing. Preserve the compact waist-shaped shield shell, blunt rounded front, dark graphite large facets, pale champagne-metal accents, small amber front indicator and matching slim robot arm root. Improve visual integration using bespoke load-bearing metal parts; no branded monitor clamp, no off-the-shelf PC rack, no bulky hand knobs.
Three panels of ONE consistent design:
1. Left hero, about 45% of sheet: three-quarter view at a flat wooden desk rear edge. Show the small shield base above the desk with only the lower arm root, plus a thin vertical rectangular external controller volume hanging BELOW the rear desk edge on a compact custom holder. The controller is a plain graphite placeholder, not a selected computer. Discreet vents face outward, no brand or invented screen. Keep the desk top readable and the lower mounting visible; adequate room between clamp tooling and holder.
2. Upper right: shell removed, same assembly. A metal top load deck supports the arm root and directly bears on protective desk-contact strips underneath. Two spaced rigid C-shaped side cheeks, one on each side of the central wiring channel, run around the rear desk edge and bolt to a lower reaction crossmember. Top deck, rear spine and lower bridge connect the two cheeks into a rigid metal assembly; plastic outer shell carries no loads. Exactly TWO vertical socket-head clamp screws go through the lower bridge, each with a captive non-rotating swivel pressure foot touching the UNDERSIDE of the desktop. The load deck touches the TOP of the desktop. Clearly show the tabletop BETWEEN the upper pads and lower pads. Tightening tool access is from below/inboard of each screw, clear of the box.
3. Lower right: simple side section or side cutaway, table extends toward LEFT and its rear edge is RIGHT. Show upper metal load deck, C cheek wrapping the edge, lower bridge, one visible upward pressing screw with its pad, the opposite screw faintly behind. In a separate path behind the clamp, a fixed rear spine extends DOWN to a detachable U-shaped bottom cradle and two short hanger cheeks supporting the controller. The holder bolts into the FIXED rear spine, not the clamp screw, moving pressure foot, or cosmetic cover. Box can be removed sideways without loosening the desk clamp. Route a bundled cable in the central stationary rear channel from recessed rear connector bay down to controller, away from screws, pressure pads and tool access. Show a short dashed path for an Allen key below the screw, not through the box.
Visual priorities: consistent same shield in all panels, credible continuous metal load path, two screws total, controller genuinely supported from below, accessible fasteners, rounded desktop-facing edges, clean slim pet-robot aesthetic. Large uncluttered views, white paper, graphite pencil contours and controlled marker shading, pale wood desk, restrained amber/gold. No numeric sizes, no rated loads, no blueprints implying final engineering.
Text exactly: title "ODRADEK / B02"; subtitle "自设计底座 · 结构构想"; panel labels "外观与下挂盒", "金属承力骨架", "桌边剖面"; short callouts only "承载上板", "夹紧螺杆", "独立盒架", "中央线槽", "外置盒占位"; footer "布置提案 · 尺寸与承载待验证".
Do not copy the old single clamp arrangement. No quick-release latch, no motorized clamp, no suction cup, no desk drilling, no extra full robot arm or gripper, no alternative A/C concepts.
```

