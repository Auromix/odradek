# Contributing to Odradek

Odradek is currently an engineering research project with parameterized CAD and mathematical checks, without manufacturing release or validated hardware. Contributions in English or Chinese are welcome.

## Useful contributions now

- A concrete desktop task: target objects, tool, payload including accessories, working area, and fabrication constraints.
- Concept feedback identifying a candidate, a pose, and the functional or visual issue.
- A proposed layout with seven identified arm axes: J7 rotates the entire head about its face normal. Account for four independent finger-opening coordinates in the detachable head; any finger segmentation must preserve this allocation.
- Luminous finger studies covering contact pads, load paths, drive arrangement, and collision envelopes.
- A single circular LED screen with pixel-drawn ring graphics, two upper/lower fisheyes, and lighting on the four fingers: study occlusion, readability, illumination, and heat.
- Detachable interfaces after the J7 output flange, including load paths, module mass, power/data, and finite-angle cable routing.
- Optical, lighting, packaging, cable-routing, and serviceability studies with stated assumptions.

## Evidence and design files

Separate requirements, proposals, analysis, simulation results, and physical test results. A concept image is not evidence of a functioning mechanism. Do not claim payload, tracking, safety, or fabrication readiness without supporting records.

Keep editable design sources alongside exported views when available. Use consistent joint IDs, coordinate frames, and version references across CAD, diagrams, documentation, and future URDF files. Do not submit third-party assets unless their license permits redistribution; include source and license information.

Use the concept-feedback issue template for visual review. For proposed changes, describe the affected task, the change, and what remains to be verified. Major architecture and styling decisions should be recorded in `docs/decisions.md` before being treated as selected.

## License

Original contributions within the current artwork, documentation, engineering research source, parameter, and model scope are accepted under [CC BY-NC 4.0](LICENSE), unless a different arrangement is explicitly documented and accepted. You must hold the rights needed for that contribution. You retain ownership; this policy does not assign your rights or automatically grant the maintainers commercial relicensing rights.

A commercial authorization covering third-party contributions requires separate written permission from the relevant rights holders. CC licenses lack software-specific provisions and are not recommended by Creative Commons for software; the current engineering research-source policy is explicitly limited in this respect. Before adding production control software, firmware, or SDKs, establish a suitable license with the maintainers. See [LICENSING.md](LICENSING.md) for scope, prior Apache-2.0 and PolyForm grants, and the commercial contact route.

Preserve third-party notices. Do not include secrets, credentials, or private user data.
