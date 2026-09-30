<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# BASE STUDY 01 图稿来源与提示词

- 工具：内置 image_gen，初稿生成后进行一次局部修改；未使用 CLI/API 回退。
- 初稿参考：[机械臂视觉语言](12-r5-arm-body.png)、[四瓣头视觉语言](11-r5-single-drive-head.png)。它们只约束风格，不用于继承旧底座的尺寸、夹具或负载结论。
- 最终资产：[13-base-study01.png](13-base-study01.png)。
- 初稿输出：exec-2f4fbb66-0633-411f-a457-6de53b8c4de1.png；修改输出：exec-6f93a77d-c8b7-4697-a9b7-560d98e04879.png。
- 图稿用途：底座外观候选比较与布置讨论，不是 CAD 导出的多视图或制造图。

## 初稿提示词

```text
Use case: stylized-concept.
Asset type: one landscape industrial design comparison board for the Auromix Odradek desktop robotic pet project.
Primary request: create THREE alternative BASE designs only, with practical hidden desk-edge clamp and rear concealed wiring, to help the owner choose the visual direction. This is an industrial design sketch, not a manufacturing drawing.
Input images: Image 1 is the EXISTING ARM visual-language reference: slender graphite structural forms, chamfered edges, champagne-metal joints. Do NOT copy its large bolted floor-style foot. Image 2 is the approved FOUR-PETAL HEAD visual-language reference: angular broad shoulders, tapering truncated ends, warm amber light, left-right symmetry. Use their style only; do not redraw the head or whole arm.

Layout: a beautiful editorial industrial design sketch board, white/off-white paper, landscape 3:2, high resolution, thin graphite construction strokes, restrained marker shading, crisp accurate perspective. Top title in clean readable typography: "ODRADEK / BASE STUDY 01". Three evenly spaced columns A, B, C. Each has a large front-three-quarter view of its base mounted at the BACK EDGE of a pale wood desktop, viewed from the user side. All use identical viewpoint, desktop, scale and the SAME short vertical first-joint collar with a short cut-off lower-arm stub; omit the rest of the arm. Each base has a visually compact but credible volume beneath the collar, NOT an impossibly wafer-thin motor housing. The tabletop itself is a small isolated rectangular segment, not a room scene. In normal top views the clamp mechanics and connectors are concealed.
A label: "A  圆角椭圆". Broad low oval footprint, gentle soft sides, restrained machined chamfers, quiet companion character, one tiny amber status accent only.
B label: "B  收腰盾形". A refined left-right-symmetric faceted shield footprint, FRONT toward user tapered to a BLUNT rounded nose, restrained concave side waist, broad REAR for recessed connector access, a few broad graphite planes with rounded edge transitions, champagne detail at the collar. Visually the most balanced sci-fi companion. No sharp spikes, no excessive greebles.
C label: "C  窄长鞍座". A narrow side-to-side, elongated FRONT-TO-BACK saddle footprint, body flowing from the joint collar to a slim covered rear cable spine that reaches the table edge. It must visibly differ from A and B in plan silhouette. Not a long tail hanging beyond the desk.

Under each large view, include a small monochrome TOP-VIEW silhouette thumbnail to make the three footprints immediately comparable.
Bottom third: TWO larger detail illustrations for candidate B only, with clean callout leaders:
1) "隐藏式桌夹" — simple side cutaway at the actual desk edge: upper load-bearing chassis resting on top of table; structural bridge goes around OUTSIDE the desk edge; lower padded clamp jaw presses UP onto the UNDERSIDE of tabletop; accessible captive adjustment screw underneath within a slim shroud. Show the desk as solid wood in section. Do NOT place any clamp screw, rod or wire THROUGH the desk. No desk drilling, suction cups, exposed large clamp handle in normal view. Separate shell from metal structural chassis by subtle shading. This is packaging intent, not a claimed verified mechanism.
2) "后盖与下行线束" — rear three-quarter detail of B with only a small rear service cover lifted away by an arrow; connectors mounted on a removable RECESSED interface plate: one rectangular network-port placeholder for EtherCAT, two small circular coax placeholders for GMSL, one distinct power-connector placeholder. Connected cables turn downward with visibly gentle loops and strain relief, gathered into one flexible sleeve routed down BEHIND the desk edge next to the clamp, never squeezed between desk and clamp pads. The shroud hides cables in normal view. Use only two short extra text labels: "可更换接口板" and "线束避开夹持区". Do not draw an external controller box, CPU, display, keyboard or computer.

Materials: satin charcoal graphite shell, darker recesses, sparse champagne metal, tiny warm amber accents. Light, poised, sophisticated mechanical pet, refined science-fiction mecha family. No full light rings on the base, no large illuminated faces or logo, no sharp fins, no four exposed mounting feet, no tabletop bolt holes, no unnecessary vents or fan grilles.
Text at bottom, exactly and legibly: "外观与布置候选 · 尺寸、夹持承载与线束空间待验证".
No fake dimension numbers, no 2kg performance badge, no equations, no CAD certification language, no watermarks. Sparse annotation with generous white space. The board must visually convey how hidden clamp and rear wiring fit at the desk edge without pretending structural validation.
```

## 局部修改提示词

```text
Use case: precise-object-edit. Edit this existing Odradek BASE STUDY 01 industrial design comparison board. Preserve the overall layout, the A/B/C labels, the three main rendered base designs, all materials/colors, the two left top-view thumbnails, and the lower-left hidden clamp illustration exactly.
Make ONLY these three localized clarity corrections:
1. The small C TOP VIEW currently has its amber FRONT pointing left. Redraw only this small top-view thumbnail rotated/reoriented so the base's long axis is VERTICAL on the page, amber rounded front toward BOTTOM of page and elongated rear cable spine toward TOP. Match the front-to-back orientation used in the A and B top views; keep C narrow across the page and elongated front-to-back. The large C three-quarter illustration stays unchanged.
2. In the lower-right rear access detail, the Chinese label "可更换接口板" must point at the recessed connector-carrying metal PANEL still attached inside the base, not at the floating plain cover. Reposition its leader accordingly. Add the short clear Chinese label "可拆后盖" pointing at the detached plain outer cover. Preserve generous whitespace, no crossed annotation leaders.
3. In that same lower-right detail only, show four connected cable positions on the actual panel: ONE rectangular network connection, TWO small circular coax connections, ONE larger distinct DC power connection, with each cable visibly originating at its corresponding connector. Remove the phantom extra row of plugs below the visible sockets. Route those four cables gently DOWN behind the desk, past a strain-relief clamp and into the common sleeve. Keep cables OUTSIDE the wood and OUTSIDE the clamping contact surfaces. These are generic packaging placeholders, not rated connector specifications.
Keep all other pixels and artwork as close as possible. Retain the bottom disclaimer exactly: "外观与布置候选 · 尺寸、夹持承载与线束空间待验证". No new dimension annotations, performance claims, logos or watermark.
```

## 图稿检查与剩余限制

三种主要外形、统一臂根视觉语言、桌边夹持示意及后部下行线束已经呈现。修改版将接口面板和外盖的标注分开，并调整 C 俯视缩略图的朝向。

图稿仍不是同一参数模型的投影：C 的俯视缩略图没有完整对应大视图的后部长尾；后仓线端与插座不构成逐一精确的插接说明，不能据此清点实际接口或判断弯曲半径。候选选择以各列大视图和方案文字为准。夹具强度、桌面接触压力、后盖拆卸空间、线束余量与旋转关节走线均待真实结构验证。

