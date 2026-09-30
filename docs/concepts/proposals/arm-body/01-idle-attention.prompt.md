<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->
# A01 双姿态：生成记录

日期：2026-09-30。使用内置 image_gen 生成并修订，未使用 CLI/API fallback。

## 确认输入与来源

用户确认“低位收拢，互动时抬起”。本轮只深化七轴本体的待机/互动姿态意图，未选择电机、减速器或确定轴系。

输入图：
1. [R5 本体研究图](../../12-r5-arm-body.png)：仅作机甲风格、连杆和维护盖视觉参考，不继承轴位与底座结构。
2. [已选四瓣展开外形原参考](../../../references/r3-approved-open-reference.png)：上大下小、左右镜像，中央圆屏和上下双鱼眼；四指独立的旧字样不继承。
3. 原对话主分支 `13fa3c8` 的 `docs/concepts/selected/base-b-shield.png`：仅参考 B 顶部罩壳外观；本分支不修改底座设计，该输入文件未重复纳入本体目录。

输出：[01-idle-attention.png](01-idle-attention.png)，1536 × 1024。待确认提案与已选外观分开。

## 视觉检查与边界

- 初稿待机前伸较大、两侧头部尺度有差别，进行了单次针对性修订。
- 修订图保留两个状态、四瓣展开、上下双相机及中央屏；待机头部低于互动头部，正面朝向用户一侧。
- 左侧连杆回折更紧，但头部仍有明显前伸，两侧头部/连杆仍不能判为严格等尺度。此图只用于姿态气质讨论，不视为已完成紧凑收纳或同一几何模型的姿态解。
- 待机下灯瓣靠近桌面；实际间隙不可从透视图量取，尚未进行桌面、灯瓣、本体间的碰撞检查。
- 肘部与桌后缘的关系缺少精确基准，因此“向桌内折叠、不依赖向墙活动”是后续设计目标，并未由本图证明。
- 没有确认七轴结构、头部视场、无碰撞运动、臂展、载荷、动作速度、保持功耗或断电行为；灯瓣在两图保持展开意向，不表示已经验证其全闭。
- 未改动原对话的底座文件。底座 B03 的向桌内收盒架及小后缝，仅作为当前相邻模块的接口方向读取。
- 下一步应以明确桌面内侧/后缘的侧视布局及统一连杆模型收敛，避免继续用生成图推断尺寸。

## 初次生成提示词

```text
Use case: stylized-concept.
Asset: one industrial-design sketch board comparing TWO POSES OF THE SAME Odradek desktop mechanical-pet arm, not two competing designs.
Reference roles:
Image 1: earlier arm-body art, use only its slender graphite link styling, restrained champagne metal details, recessed service panels and very small amber accents; its existing pose and old bulky base are NOT fixed.
Image 2: authoritative selected open head appearance. Keep FOUR luminous petal fingers, two longer shaped upper petals and two shorter shaped lower petals, left/right mirror symmetry, blunt sculpted ends rather than triangles, a central circular amber dot-matrix display, two fisheye cameras exactly above and below the display. Do not copy the obsolete text about independent fingers. Do not change the head between poses.
Image 3: authoritative B shield-shaped base APPEARANCE reference. Use only its small top shell silhouette; do not depict or redesign clamps, desktop rear wiring or external controller.
Primary request: user has chosen "低位收拢，互动时抬起". Show this behavior through the ARM BODY, keeping the head identically OPEN in both poses so no unverified petal closing mechanism is invented.
Composition: wide 3:2 white-paper board, equal left and right panels, SAME CAMERA, SAME SCALE, SAME TABLE DATUM and same slender arm hardware in both. Minimal shallow-perspective/near-orthographic three-quarter view, enough front view to see the head's screen and all four petals. Full devices within margins. Same upper-arm length, forearm length, wrist length, widths, joint sizes and head size. Do not scale the left device down. Show two long structural link segments, compact wrist, recessed axial-roll joint collars rather than many extra elbow hinges. Real joint limits and 7-axis arrangement are to be designed later; no fake axis numbering.
Left "低位待机": body folded into a compact LOW crouch near the shield base, shoulder lowered, elbow bent back over the desk interior, upper arm and forearm nesting next to/above one another with visible gaps, the open head hovering low in front of the base, face tilted slightly upward toward the person inside the desk. Keep the lower petals clearly above the desk. No link penetrates the head, base, or tabletop. The head face stays available to see a person; not face-down asleep. Total arm profile visibly lower than the right pose, with identical link lengths.
Right "抬起互动": same arm unfolds into a poised soft S / bent-elbow silhouette, raises the same head substantially above its idle position and gently reaches forward toward the viewer at the desk; keep an elbow bend and do not fully straighten. Wrist makes a slight attentive tilt, but screen and cameras remain unobscured. It should feel curious and precise rather than aggressive.
Coordinate framing: base is at rear of tabletop. Fold both poses only over the tabletop on the user's side, never projecting a large elbow behind the desk toward a wall. Indicate a faint tabletop outline and rear-edge reference in both panels. No room furniture or humans needed.
Style: polished industrial design sketch illustration, graphite pencil contours, marker shading, white paper, crisp sculpted shells, slender practical mechanical anatomy, rounded edges. Dark graphite, small satin champagne-metal interfaces, restrained amber lighting; avoid excessive vents, spikes, large cosmetic gold struts or toy eyes.
Text exactly: title "ODRADEK / ARM A01"; subtitle "低位收拢 · 互动抬起"; panel headings "低位待机" and "抬起互动"; brief callouts "头部保持朝向用户" and "肩肘抬升 · 腕部关注"; footer "同一本体双姿态 · 姿态意向，非运动验证".
No dimensions, torque ratings, timeline or certified claims. No extra concept options, no head redesign, no grasped object, no assembly explosion, no controller box, no clamp anatomy.
```

## 单次修订提示词

```text
Use case: precise-object-edit.
Edit only the attached two-pose ARM A01 sketch board. Keep the RIGHT "抬起互动" device, all titles, palette, background, and overall composition unchanged.
Fix LEFT "低位待机" geometry and size consistency:
- Current left arm still reaches far in front and its head is visibly undersized. Repose this SAME body into a genuinely compact low folded configuration, not simply a lowered wrist.
- Preserve the right-hand device's exact link lengths, joint diameters and head size. Do not shorten, telescope or duplicate links.
- In the left panel, LOWER the main elbow and turn the forearm back toward the shoulder/base so the two long links nest in a tight folded Z with a visible gap. Place the wrist and head close to the front upper region of the base, rather than at the far-right panel edge. Upper arm goes low-forward from shoulder, forearm returns back-up; compact wrist turns head outward toward user.
- Left head center should be approximately above the forward half of its shield base, with a modest forward overhang; shift it substantially left from its current location. Keep it low with lower petals safely above the tabletop.
- Copy the RIGHT head's visible size, exact four-petal shape and screen/camera proportions into the left pose. Both upper petals long and sculpted, lower petals shorter. Do not draw closed petals. Same viewing direction and OPEN angle as right head.
- Keep the low-folded body readable behind/to one side of the head, with joint and shell clearances drawn. No interpenetration, detached wrist, extra elbow or fold behind the tabletop rear edge.
- Keep left base same size and position; do not shrink the entire left device.
- Update the left annotation arrow to point at the relocated head. All text stays exactly as existing, including footer explaining pose intent, not motion validation.
This is one targeted composition/pose correction, not a new concept.
```

