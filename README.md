# Odradek

**A 7-DOF desktop arm with a detachable 4-DOF luminous gripper, expressing attention through orientation, opening, and light.**

[中文说明](README.zh-CN.md) · [Design brief](docs/design-brief.md) · [Comparison](docs/concept-comparison.md) · [Nickname candidates](docs/nickname-candidates.md) · [Roadmap](docs/roadmap.md)

Odradek is an independent Auromix robotics project sharing design material for noncommercial research and hobby use inspired by the articulated scanner in *Death Stranding*. The intended application is practical manipulation from a fixed desktop base. Mechanical design, appearance, and behavior develop together.

**Stage: R4 engineering research and geometry prototypes.** Requirements include a 2 kg end load, EtherCAT, internal cabling, and external computing. Calculations conservatively treat 2 kg as a net object. The current P16 head candidate has a 2.802 kg modeled subtotal and a 2.987–3.252 kg planning total; the actuator's speed and duty limits remain conditional. Reach is still a design assumption. Six structural links, a detachable head, coupled 7+4 mathematics and a native Blender review assembly are now integrated. There is no manufacturing release, tested 2 kg prototype, or production control firmware.

## Engineering package

![Current structural review assembly](engineering/generated/raised-arm-integration01/blender/arm-open-oblique.png)

This model combines 24 original link parts, the corrected base and the 697-object HEAD-INTEGRATED03 snapshot. Joint housings remain catalog envelopes; arm fasteners, harnesses and exterior guards are not fully integrated. The central pixel display is a separate visual preview. [Full-arm BREP checks](docs/engineering/integrated-collision-study.md) found real shoulder collisions in the historical `reach` pose; it must not be executed. The shown `inspect` pose passed the stated discrete geometry check, not trajectory or payload qualification.

| Package | Evidence and scope |
|---|---|
| [Engineering index](docs/engineering/README.md) | Requirements, assumptions, source records, and release checklist |
| [R4 layout and grasp](docs/engineering/r4-layout-and-grasp.md) | Same-parameter geometry, closure proof, conditional contact calculations, and optical sightlines |
| [Current native Blender](engineering/generated/raised-arm-integration01/blender/odradek-integrated-7-plus-4.blend) / [model guide](docs/engineering/raised-arm-integration01.md) | 736 product meshes, 11 controls, persistent actuator linkage drivers; geometric review only |
| [Integrated head STEP and evidence](docs/engineering/head-integrated03-study.md) / [coupled dynamics](docs/engineering/articulated-dynamics-review.md) | Actual candidate solids, frozen board placement and explicit mass/inertia assumptions |
| [Historical layout](docs/engineering/r4-layout-and-grasp.md) / [subassembly scenes](docs/engineering/subassembly-blender-review.md) | Earlier design stages retained for traceability |
| [A3 review drawings](engineering/generated/layout/ODR-R4-assembly-review.pdf) | Axes, dimensions, and orthographic mesh views |
| [Manual finger fixture](engineering/generated/finger-fixture/README.md) / [joint interface coupons](docs/engineering/interface-coupon-guide.md) | Unpowered printable geometry checks with dimensions |
| [Hardware BOM](docs/engineering/hardware/bom.csv) / [optical bench](docs/engineering/hardware/optical-bench-build.md) | Sourced component candidates and a concrete dual-fisheye bench chain |
| [Reproduce the calculations and CAD](engineering/README.md) | Dependencies, generation order, units, and limitations |

The old [finite-pad contact counterexample](docs/engineering/finite-pad-contact-study.md) remains documented. HEAD-INTEGRATED03 now combines the revised CONTACT-02 pads and retention, narrowed CARRIER02 roots, lamp cavities, board placement and EXT24. Its 17 scoped continuous checks pass nominal geometry conditions; dynamic harnesses, tolerances, deformation and grasp testing remain unresolved. Conditional force calculations are not a measured payload rating.

## R3: keep the silhouette, resolve closure and contact

The larger upper / smaller lower, left-right mirrored open silhouette is selected. The upper fisheye tilts upward and the lower downward; the amount remains open pending near-grasp visibility checks.

The study identifies three issues: unequal rigid lengths do not fold into one short common-depth pod, wide plates can collide before their tips reach the center, and forward curling turns the original luminous face toward the object. The leading candidate keeps each plate intact, uses different limits and real depth offsets, and places proud contact pads / structural borders on the light-facing side with recessed windows.

The [geometry study](docs/r3-closure-study.md) includes counterexamples and a continuous-domain separation result for an illustrative four-box model. This does not validate the full head or a stable grasp. The artwork's stow panel is an envelope study, not a final closed pose.

## Current direction: a detachable four-petal head

![R3 silhouette, camera, and contact study](docs/concepts/10-r3-closure-study.png)

- **Seven arm DOFs and four head DOFs.** J7 rotates the whole head about the normal to its front face. Each luminous finger has one independent opening coordinate.
- **Two close petals on each side, with left/right mirror symmetry and different upper/lower proportions.** Longer upper and shorter lower petals avoid 180-degree rotational symmetry. The grouping is inspired by the XPENG logo composition; it does not require mechanically coupled pairs.
- **The light petals are the fingers.** Forward curling turns the light face inward. Proud pads / structural borders on that same side are proposed to contact the object before the recessed windows. Empty full closure must reach a mechanical limit with real clearances; it does not imply a sealed pod or four tips meeting at one point.
- **One circular LED display in the center.** Ring graphics use pixels at its perimeter. The four fingers provide lighting. Two fisheye cameras sit above and below the screen, tilt upward/downward respectively, and rotate with the head.
- **The detachable boundary is after the J7 output flange.** Four finger actuators and local control are proposed within the head; connection specifications remain open.

![Arm integration, detachable interface, and J7 axis](docs/concepts/08-r2-modular-arm.png)

The roll sketches show finite-angle pose intent without defining travel. Open, grasping, and fully closed geometry must be reconciled in one CAD model; the R2 compact protective pod is now a historical assumption. Mechanical breathing is limited to empty, task-permitted operation; expression must not change an active grasp.

## Three, four, or five petals

![Same-scale petal-count study](docs/concepts/07-r2-petal-count-study.png)

| Count | Visual character | Role |
| --- | --- | --- |
| 3 | Light triangular silhouette; instrument or alien-tool associations | Aesthetic comparison |
| **4** | Two visually grouped pairs; balance between tool and creature | **Current mechanical direction: one DOF per finger** |
| 5 | Denser flower or biological silhouette; a hand-like reading needs an offset petal | Aesthetic comparison |

Petal count is not a DOF count. Three- and five-petal variants would require their own motion allocation; the confirmed four independent coordinates apply to the four-petal design.

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
