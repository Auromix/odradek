# Odradek

**2026-10-08 arm body / 本体更新：** 用户认为A11外观仍需重构，已选择[A12 A连续甲壳](docs/concepts/selected/arm-body-a12-manta-carapace/README.md)，围绕实际电机包覆、可拆背脊和活动线弯逐模块深化。新增[连续甲壳整臂造型初稿](engineering/arm_a12/whole_style01/README.md)与[七轴交互预览](docs/viewers/arm-body-a12-style/index.html)，保留真实长版拓扑；新增外罩尚未完成运动干涉和打印装配验证。内部承力结构仍为A11，[J2肩罩局部空间初稿](engineering/arm_a12/shoulder01/README.md)的检查不延伸为整臂结论；B06底座作为同源只读上下文，不代表新旧模块已完成整机适配。

[A11长版](engineering/arm_a11/README.md)与其[查看器](docs/viewers/arm-body-a11/index.html)、[验证记录](docs/engineering/arm-body-a11-validation.md)保留为历史结构基线；51个打印文件只适用于该版本受支撑试配，不移用于A12。裸法兰3 kg是目标，实物装配、温升、承力底盘和线束仍需验证。

**A 7-DOF desktop arm with a detachable four-petal luminous gripper, expressing attention through orientation, opening, and light.**

[中文说明](README.zh-CN.md) · [Design brief](docs/design-brief.md) · [Comparison](docs/concept-comparison.md) · [Nickname candidates](docs/nickname-candidates.md) · [Roadmap](docs/roadmap.md)

**2026-09-28 checkpoint:** preserve the current research and drafts without adding complexity. The preferred head uses positive single-input synchronization and permits one opposed petal pair to carry the grasp. Passive differential studies remain comparisons. [Saved scope and draft status](docs/engineering/checkpoint-2026-09-28.md).

Odradek is an independent Auromix robotics project sharing design material for noncommercial research and hobby use inspired by the articulated scanner in *Death Stranding*. The intended application is practical manipulation from a fixed desktop base. Mechanical design, appearance, and behavior develop together.

**Stage: engineering research; the head drive is being redesigned for a confirmed ≤1-second empty closed–open–closed cycle.** Gripping is the primary function and the illuminated petal face is the contact face. The user has confirmed a 2 kg net object plus head mass, approximately 700 mm reach, EtherCAT, GMSL/GMSL2 cameras, internal cabling and external computing. P16 actuators cannot meet the new cycle; their CAD and electrical branch remain historical references. The existing 7+4 assembly does not demonstrate the new speed requirement. See [current requirements](docs/engineering/fast-grasp-requirements01.md). No manufacturing release or tested 2 kg prototype exists.

## R5: single-drive head and separate arm body

![Single central drive and four shaped luminous petals](docs/concepts/11-r5-single-drive-head.png)

One concealed central actuator drives four coupled petals; their luminous faces also grip. The seven-axis body is developed separately with slender proportions and a detachable tool flange. [See both concept sheets and the current design brief](docs/r5-modular-design.md). Generated illustrations guide appearance; linkage, clearance and load capacity require engineering validation.

The latest engineering includes [revised layered petal STEP and drawings](docs/engineering/r5-petal-form02.md), a [fold-then-radial path and passive differential study](docs/engineering/r5-stage01.md), a [detachable eRob wrist adapter](docs/engineering/r5-wrist-erob01.md), and a [separate arm mass/reach study](docs/engineering/r5-body01.md). Everyday boxes, bottles and cans of approximately **50–120 mm gripping width** are the first target. Bare-petal geometry now has a continuous separation bound, but the physical mechanism, final closed posture and complete grasp range remain unqualified. The earlier [single-slider Blender rig](docs/engineering/r5-linkage-blender01.md) remains a separate comparison. See the [current baseline](docs/engineering/current-baseline.md) for evidence and remaining work.

The [native radial-candidate Blender model and guide](docs/engineering/r5-stage-blender01.md) contain 28 actual petal CAD meshes, including contact poses for an Ø80 mm cylinder and a 50×120 mm rectangular box. One mean input and three passive review offsets express the differential constraint; the physical transmission, central module and time simulation are not included.

## Engineering package

![Existing structural review assembly — historical P16 head](engineering/generated/raised-arm-integration01/blender/arm-open-oblique.png)

This model combines 24 original link parts, a shoulder raised by 35 mm, the corrected base and the 697-object HEAD-INTEGRATED03 snapshot. Joint housings in Blender remain catalog envelopes; arm fasteners, harnesses and exterior guards are not fully integrated. The central pixel display is a separate visual preview. [The raised candidate](docs/engineering/raised-arm-integration01.md) passes the stated actual-BREP checks for ten poses, including the historical shoulder-collision pose. These discrete checks do not qualify trajectories or payload. [Current baseline and hardware choices](docs/engineering/current-baseline.md) separate the conditional eight-node P16 branch from earlier alternatives.

| Package | Evidence and scope |
|---|---|
| [Engineering index](docs/engineering/README.md) | Requirements, assumptions, source records, and release checklist |
| [R4 layout and grasp](docs/engineering/r4-layout-and-grasp.md) | Same-parameter geometry, closure proof, conditional contact calculations, and optical sightlines |
| [Existing native Blender / historical P16 head](engineering/generated/raised-arm-integration01/blender/odradek-integrated-7-plus-4.blend) / [model guide](docs/engineering/raised-arm-integration01.md) | 736 product meshes, 11 controls, persistent actuator linkage drivers; geometric review only |
| [Integrated head STEP and evidence](docs/engineering/head-integrated03-study.md) / [coupled dynamics](docs/engineering/articulated-dynamics-review.md) | Actual candidate solids, frozen board placement and explicit mass/inertia assumptions |
| [Historical layout](docs/engineering/r4-layout-and-grasp.md) / [subassembly scenes](docs/engineering/subassembly-blender-review.md) | Earlier design stages retained for traceability |
| [A3 review drawings](engineering/generated/layout/ODR-R4-assembly-review.pdf) | Axes, dimensions, and orthographic mesh views |
| [Manual finger fixture](engineering/generated/finger-fixture/README.md) / [joint interface coupons](docs/engineering/interface-coupon-guide.md) | Unpowered printable geometry checks with dimensions |
| [Hardware BOM](docs/engineering/hardware/bom.csv) / [optical bench](docs/engineering/hardware/optical-bench-build.md) | Sourced component candidates and a concrete dual-fisheye bench chain |
| [Reproduce the calculations and CAD](engineering/README.md) | Dependencies, generation order, units, and limitations |

The old [finite-pad contact counterexample](docs/engineering/finite-pad-contact-study.md) remains documented. HEAD-INTEGRATED03 now combines the revised CONTACT-02 pads and retention, narrowed CARRIER02 roots, lamp cavities, board placement and EXT24. Its 17 scoped continuous checks pass nominal geometry conditions; dynamic harnesses, tolerances, deformation and grasp testing remain unresolved. Conditional force calculations are not a measured payload rating.

## Historical R3: silhouette, closure and contact

The larger upper / smaller lower, left-right mirrored open silhouette is selected. The upper fisheye tilts upward and the lower downward; the amount remains open pending near-grasp visibility checks.

The study identifies three issues: unequal rigid lengths do not fold into one short common-depth pod, wide plates can collide before their tips reach the center, and forward curling turns the original luminous face toward the object. The leading candidate keeps each plate intact, uses different limits and real depth offsets, and places proud contact pads / structural borders on the light-facing side with recessed windows.

The [geometry study](docs/r3-closure-study.md) includes counterexamples and a continuous-domain separation result for an illustrative four-box model. This does not validate the full head or a stable grasp. The artwork's stow panel is an envelope study, not a final closed pose.

## Current direction: a detachable four-petal head

![R3 silhouette, camera, and contact study](docs/concepts/10-r3-closure-study.png)

- **Seven arm DOFs; a single-drive four-petal head is now the preferred route.** J7 rolls the head about its front normal. One motor with three mechanically coupled followers is permitted; linkage mapping and passive compliance remain to be designed.
- **Two close petals on each side, with left/right mirror symmetry and different upper/lower proportions.** Longer upper and shorter lower petals avoid 180-degree rotational symmetry. The grouping is inspired by the XPENG logo composition; it does not require mechanically coupled pairs.
- **The light petals are the fingers.** Forward curling turns the light face inward. The latest requirement makes the illuminated face itself the gripping face; the contact skin and load-bearing support are being redesigned. Earlier proud tip pads are a historical contact study. Empty full closure must reach a mechanical limit with real clearances; it does not imply a sealed pod or four tips meeting at one point.
- **One circular LED display in the center.** Ring graphics use pixels at its perimeter. The four fingers provide lighting. Two fisheye cameras sit above and below the screen, tilt upward/downward respectively, and rotate with the head.
- **The detachable boundary is after the J7 output flange.** One concealed central actuator and local execution interfaces are proposed within the head; connection specifications remain open.

![Arm integration, detachable interface, and J7 axis](docs/concepts/08-r2-modular-arm.png)

The roll sketches show finite-angle pose intent without defining travel. Open, grasping, and fully closed geometry must be reconciled in one CAD model; the R2 compact protective pod is now a historical assumption. Mechanical breathing is limited to empty, task-permitted operation; expression must not change an active grasp.

## Three, four, or five petals

![Same-scale petal-count study](docs/concepts/07-r2-petal-count-study.png)

| Count | Visual character | Role |
| --- | --- | --- |
| 3 | Light triangular silhouette; instrument or alien-tool associations | Aesthetic comparison |
| **4** | Two visually grouped pairs; balance between tool and creature | **Four shaped petals, single-drive coupling permitted** |
| 5 | Denser flower or biological silhouette; a hand-like reading needs an offset petal | Aesthetic comparison |

Petal count is not a DOF count. Three- and five-petal variants would require their own motion allocation; the latest direction permits a single actuator with coupled motion.

## Nickname candidates

**Odi** is the leading suggestion for continuity with Odradek; **Lumo** emphasizes light and breathing. Noto, Piko, Tavi, and Filo are additional options. See the [shortlist](docs/nickname-candidates.md). No nickname has been selected; the project and repository remain Odradek.

## Process and next steps

Research → R0 form exploration → R1 luminous fingers → R2 7+4 DOF and modular head → R3 silhouette and closure → **R4 sourced components, mathematics, CAD, and geometry fixtures** → complete load paths and harness routes → physical task and manufacturing validation.

The [gallery](docs/gallery.html) retains original R0/R1 artwork and exact prompts for traceability. R1's separate physical light annulus and finger-count candidates are superseded by R2.

| Document | Contents |
| --- | --- |
| [Design brief](docs/design-brief.md) | Confirmed requirements, concept assumptions, and open inputs |
| [Comparison](docs/concept-comparison.md) and [behavior](docs/behavior-spec.md) | Form, grasp, light, and attention studies |
| [Decisions](docs/decisions.md) and [roadmap](docs/roadmap.md) | Evolution and route to reproducible hardware |
| [Sources](docs/sources.md) | Research and reference roles |
| [Generation](docs/generation.md) and [review notes](docs/review-notes.md) | Prompts, AI assistance, and specific visual limitations |

Current open items include the shoulder's usable motion range, installed holding/thermal performance, complete controller and harness design, contact/fastener qualification and manufacturing tolerances. See the [release checklist](docs/engineering/release-checklist.md).

## License and commercial permissions

New original artwork, documentation, research scripts, parameters, and models are offered under **[CC BY-NC 4.0](LICENSE)**. Noncommercial research, study, hobby use, adaptation, and sharing are permitted under its terms. Sharing requires attribution, license information, and indication of changes. Commercial use requiring authorization needs a [separate written license from the authors](https://github.com/Auromix/odradek/issues/new?template=commercial-license.yml).

**Prior Apache-2.0 grants through `2d7d00f` and marked-script PolyForm grants in `698736a` through `c4f1fde` remain valid.** See [licensing scope and history](LICENSING.md), including the explicit limitations of applying CC to engineering research software. Future production control firmware needs a suitable separate license decision. Copyright notices do not themselves control all functional hardware manufacture.

The noncommercial restriction means this is not open source under the OSI definition. Contributions in English or Chinese are welcome; see [CONTRIBUTING](CONTRIBUTING.md). Third-party reference images are not included or relicensed. This project has no official affiliation with *Death Stranding*, KOJIMA PRODUCTIONS, or XPENG.
