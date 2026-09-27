# Sources and reference roles

Research accessed 2026-09-27. These references inform design intent; their specifications are not Odradek performance claims. Third-party reference images are not redistributed in this repository.

| Source | Role in this project |
| --- | --- |
| [PlayStation: Odradek glossary](https://blog.de.playstation.com/2025/06/25/death-stranding-2-on-the-beach-glossar/) | Original inspiration: shoulder sensor, illuminated articulated panels |
| [PlayStation: Death Stranding day-one tips](https://blog.playstation.com/2019/11/07/hit-the-ground-running-with-these-day-one-death-stranding-tips/) | Direction and rotation communicate attention in the game |
| [KOJIMA PRODUCTIONS: Ludens interview](https://www.kojimaproductions.jp/EXPLORING-LUDENS-YojiShinkawa) | Layered equipment design and physical model assembly considerations |
| [Enactic OpenArm hardware](https://github.com/enactic/openarm_hardware) | An open hardware reference for CAD and assembly assets |
| [OpenArm 2.0 motor selection](https://docs.openarm.dev/hardware/openarm-2.0/motor/) | Actuator selection, load, rigidity, and compact packaging considered together |
| [OpenArm 2.0 gripper](https://docs.openarm.dev/hardware/openarm-2.0/gripper/) | Camera packaging, finger visibility, and tool integration |
| [Franka Research 3](https://franka.de/franka-research-3-arm) | Product detailing and joint / axis markings; not an open hardware baseline |
| [Kinova Gen3 user guide](https://www.kinovarobotics.com/uploads/User-Guide-Gen3-R07.pdf) | Large/small actuator allocation and enclosure collision limits; PDF pp. 26 and 70 |
| [Design Council: Double Diamond](https://www.designcouncil.org.uk/resources/the-double-diamond/) | Discover, Define, Develop, Deliver as an iterative divergence / convergence framework |

The design process here adapts that general framework to industrial design: research, brief, form exploration, concept development, review, mechanical packaging, prototyping, and validation. It is not a claim that all industrial design teams follow an identical linear process.

The original expression requirements—active attention, spotlight, breathing motion, and luminous end panels—came from this project's brief. R2 retains attention and breathing but assigns lighting to the fingers and uses only a display at the center. Automatic sensing, tracking, and lighting control have not yet been implemented.

## R1 technical references (historical exploration)

The user added luminous petals that also grip, and a circular LED with specific display patterns. These are project requirements / exploration inputs; the sources below inform implementation questions, not final selections.

| Source | Supported observation and project inference |
| --- | --- |
| [Yale OpenHand Model T](https://www.eng.yale.edu/grablab/openhand/model_t.html) | Published four-finger compliant, underactuated hand with a differential. Supports investigating contact adaptation; it does not validate our rigid luminous panels or provide a selected mechanism. No source CAD or assets copied. |
| [Adafruit LED Matrix Diffuser](https://learn.adafruit.com/pixel-art-matrix-display/led-matrix-diffuser) | A diffusion faceplate can protect LEDs and reduce glare / grid reflections. Protecting an LED is not evidence of suitability for clamping loads. |
| [LEDiL Guide to TIR Lenses](https://www.ledil.com/support/guide-to-tir-lenses/) | Distinct lens designs shape spot, diffuse, and wider beams. Our proposed separation of matrix display and task-light optics is an inference; beam, illumination, heat, and available space need measurement. |

The inner pads, structural finger frames, recessed display, and grasp-priority behavior are project design proposals. No component pricing, performance figures, or manufacturing readiness are inferred from these references.


## R2 visual inputs and reference roles

| Source | Role and attribution |
| --- | --- |
| [PlayStation Share of the Week, 2021-10-01](https://blog.latam.playstation.com/2021/10/01/share-de-la-semana-death-stranding-directors-cut/) | Odradek close-up by **@momentohermano42**, a player photograph selected by PlayStation; *Death Stranding Director's Cut*. Used for thin articulated supports, uneven petal proportions, and luminous surface texture. |
| [Odradek gameplay image collection](https://deathstranding.fandom.com/wiki/Odradek?file=OdradekPointing.png) | Community-hosted pointing screenshot, used for directional gesture. This is not an official mechanical drawing. |
| [XPENG published logo image, Cision](https://news.cision.com/se/xpeng/i/xpeng-logo-horizontal-black,c3010388) | Actual image supplied to imagegen for the user's requested left/right close-pair composition. The drawing adapts proportions to gripper fingers; it does not reproduce a logo badge or imply affiliation. |
| User-selected industrial design sketch | Existing style reference supplied for fine-line drawing, blue-gray marker shading, pale ground, and whitespace. It provides no product geometry or performance evidence. |

The original game close-up suggests four broad panels plus a narrower upper panel. The current four-finger design is this project's choice, not a claim that the original Odradek has four fingers. Dots and patterns visible in game images do not establish an actual programmable LED implementation; the circular display is our design proposal.

R2's mechanical assignments, modular boundary, two cameras, and software-drawn screen ring come from the user's requirements and this project's stated assumptions. The references do not verify those mechanisms.


## R3 geometric and viewing study

The selected silhouette is the user's crop of this project's generated R2 open-head image. R3 preserves that visual identity. Its geometric dimensions are arbitrary normalized study parameters, not measurements inferred from the image.

- [OpenCV fisheye model and calibration](https://docs.opencv.org/4.13.0/db/d58/group__calib3d__fisheye.html): camera-coordinate ray angles, projection, calibration and rectification. The outward-tilt overlap formula is this project's own two-dimensional derivation.
- [Basler depth and occlusion guidance](https://docs.baslerweb.com/stereovisard/tutorials/image_tuning/depth_tuning): a region visible in only one camera cannot be assumed to support stereo matching.
- [Robotiq grasp-mode explanation](https://assets.robotiq.com/website-assets/support_documents/document/online/2F-85_2F-140_TM_InstructionManual_HTML5_20190206.zip/2F-85_2F-140_TM_InstructionManual_HTML5/Content/1.%20General_Presentation.htm): contact region and palm support matter for encompassing grasps. No mechanism or performance figures are transferred to this project.
