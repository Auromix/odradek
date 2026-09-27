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

The expression requirements—active attention, spotlight, breathing motion, and luminous end panels—come from this project's brief. Automatic sensing, tracking, and lighting control have not yet been implemented.

## R1 technical references

The user added luminous petals that also grip, and a circular LED with specific display patterns. These are project requirements / exploration inputs; the sources below inform implementation questions, not final selections.

| Source | Supported observation and project inference |
| --- | --- |
| [Yale OpenHand Model T](https://www.eng.yale.edu/grablab/openhand/model_t.html) | Published four-finger compliant, underactuated hand with a differential. Supports investigating contact adaptation; it does not validate our rigid luminous panels or provide a selected mechanism. No source CAD or assets copied. |
| [Adafruit LED Matrix Diffuser](https://learn.adafruit.com/pixel-art-matrix-display/led-matrix-diffuser) | A diffusion faceplate can protect LEDs and reduce glare / grid reflections. Protecting an LED is not evidence of suitability for clamping loads. |
| [LEDiL Guide to TIR Lenses](https://www.ledil.com/support/guide-to-tir-lenses/) | Distinct lens designs shape spot, diffuse, and wider beams. Our proposed separation of matrix display and task-light optics is an inference; beam, illumination, heat, and available space need measurement. |

The inner pads, structural finger frames, recessed display, and grasp-priority behavior are project design proposals. No component pricing, performance figures, or manufacturing readiness are inferred from these references.
