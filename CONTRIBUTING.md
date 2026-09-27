# Contributing to Odradek

Odradek is currently a concept-stage project. Contributions in English or Chinese are welcome.

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

By intentionally submitting original contributions for inclusion, you agree that they may be distributed under the repository's Apache-2.0 license, unless a different arrangement is explicitly documented and accepted. Preserve third-party notices. Do not include secrets, credentials, or private user data.
