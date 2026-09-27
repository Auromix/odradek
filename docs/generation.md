# Concept artwork provenance and review

Date: 2026-09-27. Method: the built-in **imagegen** tool, with visual references supplied as inputs. This is AI-assisted industrial design ideation, not CAD rendering or a reconstruction of a tested mechanism.

## R0 assets and exact prompts (historical)

| Asset | Prompt | Purpose |
| --- | --- | --- |
| [00-form-exploration.png](concepts/00-form-exploration.png) | [00-divergence.txt](../prompts/00-divergence.txt) | Six head / silhouette variants |
| [01-field.png](concepts/01-field.png) | [01-field.txt](../prompts/01-field.txt) | Four-petal modular observation head |
| [02-frame.png](concepts/02-frame.png) | [02-frame.txt](../prompts/02-frame.txt) | Three-leaf dorsal lighting and gripper coexistence |
| [03-shell.png](concepts/03-shell.png) | [03-shell.txt](../prompts/03-shell.txt) | Compact four-panel light shutter head |
| [04-attention-study.png](concepts/04-attention-study.png) | [04-attention.txt](../prompts/04-attention.txt), [park-pose refinement](../prompts/04-attention-refinement.txt) | Attention, illumination, opening / closing sequence |

The original Odradek screenshot informed the emotional role of luminous articulated panels. OpenArm imagery informed mechanical plausibility only. A user-selected industrial design sketch reference informed pen and marker technique only. Reference product logos, performance numbers, and dual-arm layout were explicitly excluded. Exact third-party reference sources are linked in [sources](sources.md); those images are not included in the repository. The generated exploration sheet guided the three candidate boards, and candidate A guided the behavior sheet.

## Reading the images

Text within each image is illustrative. The Markdown brief and comparison documents are the source for project requirements and status. Counts of visible housings do not establish the number or independence of rotary axes; hidden/coaxial axes must be resolved in a kinematic layout.

The artwork is reviewed for concept identity, visible panel configuration, spotlight / camera distinction, fixed-base use, working / parked poses, and broad cross-view consistency. Detailed geometry, joint limits, transmissions, dimensions, cable strain, heat, stiffness, tool clearance, and manufacturability remain unverified. Differences between perspective insets must be reconciled in CAD; none is an assembly drawing.

No performance, automatic tracking, or hardware safety claim is derived from these images. Candidate A is used for motion study without selecting it as the final product direction. See [review notes](review-notes.md) for concrete observations and unresolved geometry.

## R1: luminous gripping fingers and circular LED display

| Asset | Prompt | Purpose |
| --- | --- | --- |
| [05-petal-gripper-options.png](concepts/05-petal-gripper-options.png) | [05-petal-gripper-options.txt](../prompts/05-petal-gripper-options.txt) | Compare two, three, and four luminous fingers in open and grasping poses |
| [06-petal-gripper-study.png](concepts/06-petal-gripper-study.png) | [06-petal-gripper-study.txt](../prompts/06-petal-gripper-study.txt), [annotation refinement](../prompts/06-petal-gripper-refinement.txt) | D4 arm integration, holding pose, and five circular LED display examples |

R1 used the built-in imagegen tool. The existing A board supplied arm and material language, the original Odradek image supplied articulated-light emotion, and the user-selected sketch reference supplied pen/marker style for the options sheet. The generated options sheet and A board then guided the D4 study. A targeted refinement removed an incorrectly placed task-light callout; the remaining LED MATRIX callout identifies the display. Third-party images remain excluded from the repository.

D4 is a proposed direction only. The images communicate that the luminous panels themselves are fingers, with separate contact pads. Root hinges, contact planes, transmission paths, display setback, and collision-free opening still require a coherent 3D model. The five display examples are visual proposals, not implemented state feedback. R0 images and exact prompts remain unchanged as historical records.
