<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# B03 内收盒架：出图与检查

日期：2026-09-30。使用内置 image_gen 编辑，未使用 CLI/API fallback。

## 输入与变更

- 原图：[B02 自设计底座](base-b-custom02.png)，生成前已读取。
- 用户要求盒架向桌内收；随后澄清“贴墙”允许走线空间，并明确保留后沿夹装、允许夹体所需小间隙。
- 本版只调整底座的盒架、后仓维护与靠墙布置；保留已选 B 外形以及 B02 自设计骨架方向。
- 输出：[base-b-inward03.png](base-b-inward03.png)，1536 × 1024。
- 首稿侧视误留旧竖盒，造成同一视图两个盒体，已弃用；第二次编辑去掉旧盒及附件、修正桌后缘和墙线。项目仅收录第二稿。
- 本图是待确认结构提案，未覆盖 selected 目录的已选外形参考；[设计说明](../../base-design-study01.md)维护当前边界。

## 视觉检查与限制

已查看第二稿：三个视图均只表达一个横置盒体，右下盒体位于桌板下方、螺杆的桌内侧；旧桌后竖盒已移除。右下朝左为向桌内/朝使用者，朝右为墙；取盒箭头朝左，工具箭头位于夹紧螺杆下方，墙与夹体之间有必要后缝。原 B 盾形外罩、小琥珀灯和金属臂根风格保持。上方开盖为维护方向标注，不代表已完整绘制开盖运动。

这些检查只针对画面表达。各视图不是同一 CAD 的投影，螺杆横向/纵向位置、淡画远侧螺杆、反力桥和托盘挂臂遮挡仍为示意，未形成可读出的精确实体关系。不得从图测量后缝、板厚、盒体尺寸、线缆弯曲或工具余量，也不能凭图确认夹紧受力路径已成立。后续需用尺寸模型核对整个螺杆行程、扳手转动、取盒、上盖/插头、散热与腿部空间。

没有开展 CAD 干涉分析、结构计算、加工验证或实物承载测试。

## 首稿提示词

```text
Use case: precise-object-edit.
Edit target: attached ODRADEK B02 custom base board.
User correction: the desktop may sit close to a wall. A small rear allowance for the clamp and wiring is acceptable; strict zero-gap flush is NOT required. The CONTROLLER HOLDER AND BOX MUST EXTEND INWARD UNDER THE TABLE, never hang out behind it.
Make a B03 revision of the SAME custom base concept, preserving the B shield waist, blunt rounded front, graphite surfaces, small amber indicator, champagne accents, arm root, paired C cheek metal load frame, top plate, lower reaction bridge and TWO underside clamp screws. Retain the custom design, no branded clamp or PC mount.
Critical geometry:
Define FRONT / TABLE INTERIOR as LEFT in the lower-right SIDE view, rear edge as RIGHT. A light neutral wall is a vertical line beyond the rear edge on the far RIGHT. Show a small visible gap between table rear and wall, labelled "必要后缝" with no number. Only the thin fixed clamp spine and protected wiring occupy that allowance. No box, rack, outward-opening lid, or protruding cable loop may extend toward the wall.
Replace the old vertical controller behind the edge with a FLAT HORIZONTAL controller enclosure and low-profile U cradle, ENTIRELY UNDER the desktop footprint toward LEFT / interior. Custom fixed hanger arms turn INWARD and support the cradle from below, bolted to the FIXED clamp frame, never attached to clamp screws or pressure feet.
Keep the controller and solid tray area farther INBOARD than the two clamp screws, leaving an unobstructed vertical Allen-key/tool corridor directly BELOW each screw near the rear edge. Side hanger arms route around those corridors. In the side view, the screw is near the right/rear and the flat horizontal box is to its LEFT / inside. Do NOT put the box directly below the screw. Preserve two non-rotating pressure feet contacting desk underside and upper load plate pads contacting desk top.
Maintenance: box withdraws horizontally toward FRONT / LEFT from its cradle after releasing a small separate retaining screw/stop, no sliding rails or complex latch. Draw a short inward/front arrow. Keep clamp screws untouched when removing box. Ventilation and connectors face sideways or front/inward, not toward the wall, with visual vent clearance.
Rear wiring BAY remains at the rear of the top shield but its small cover is accessed from ABOVE, not swung outward toward wall; plugs recess sideways/downward within the bay. Route cable bundle through the fixed thin rear channel, then turn inward under desk to controller; no giant bend behind table, no cable passing through wood.
Composition: one consistent three-panel landscape sheet. Left large hero three-quarter view showing shield base on desk and horizontal controller cradle entirely underneath toward interior, use cutaway/transparent strip of desk if necessary to make geometry legible without moving the box outside the desk. Upper right shell-off fixed metal frame and inset inward holder attachment, show exactly two clamp screws. Lower right clean readable SIDE LAYOUT with desk extending left, wall right, small rear gap, horizontal inward controller to left of clamp screws, Allen key entering below screw, box removal arrow toward left. Side layout is the priority: obey physical front/back directions. Do not reproduce the old vertical outboard box anywhere.
Style: industrial design sketch illustration on clean white paper, precise pencil and restrained marker shading, light wood desk, large clear views, no engineering dimension numbers, no certified load, no final manufacturing implication.
Text exactly: title "ODRADEK / B03"; subtitle "内收盒架 · 靠墙布置";
panel labels "外观与内收盒架", "固定骨架与托架", "桌边布置";
short labels "向桌内收", "工具通道", "上方开盖", "必要后缝", "向前取盒";
footer "布置提案 · 后缝、尺寸与承载待验证".
Avoid: vertical tower box outside rear edge; shelf projecting toward wall; box obstructing clamp screws; invented third screw; desk drilling; suction; motorized clamp; fresh shape alternatives; giant cable loops; claims of zero rear clearance.
```

## 定向修订提示词

```text
Use case: precise-object-edit.
Edit target: the attached B03 inward-cradle design board.
Critical correction: the LOWER RIGHT SIDE LAYOUT accidentally contains TWO controller boxes, including the OLD VERTICAL BOX against the wall. That is WRONG. There must be EXACTLY ONE horizontal controller, entirely under the table to the LEFT/interior of the clamp screws.
Keep the title, left hero view, upper-right frame view, colors and shield design unchanged. Redraw ONLY the lower-right panel labelled "桌边布置" to a clean, simple side elevation:
- Desk extends from left and ENDS at the inside of the fixed C-shaped clamp rear spine. No continuation of wood beyond the rear spine, no extra wood block toward the wall.
- Wall is a vertical light grey line at far right, with a visible modest gap beyond the outermost fixed spine/cable cover, labelled "必要后缝". This gap contains NO external controller, NO shelf, NO tall vertical bracket.
- EXACTLY ONE horizontal rectangular low-profile controller sits below the wood and to the LEFT of the clamp screws. Its U cradle faces inward and is supported by side hanger arms attached to the fixed frame; these arms are outside the screw tool corridors. Do not show a solid tray bridging underneath the screws.
- Delete ENTIRELY the old rightmost vertical vented controller, all its old retaining brackets and the cable loop that fed it. Replace with blank paper/air between the thin fixed rear spine and wall, and open air below it.
- At the C-clamp, one near screw and a faint far screw press upward against the table underside. Tool arrow vertically upward below near screw; Allen key stays clear of horizontal controller.
- Cable path confined to a thin channel on the fixed spine, then turns LEFT under the desk into the ONE horizontal controller. It must not turn down to any vertical box, and must not pass through wood.
- Horizontal box removal arrow points LEFT and says "向前取盒".
- Simple, legible side diagram takes priority over intricate mechanical detailing; do not draw a second computer or outboard holder.
Preserve the labels "桌边布置", "必要后缝", "工具通道", "向前取盒". Preserve footer "布置提案 · 后缝、尺寸与承载待验证". No new alternative designs, no numerical dimensions, no claim of zero rear clearance.
```

