# video-shotcraft attribution and adaptation record

Upstream: https://github.com/Vincentwei1021/video-shotcraft

Pinned commit: 1266a3ec4831289c4d893d42dd5102723658039a

Copyright 2026 Wei Yihao. Code and documentation under Apache License 2.0; see LICENSE.

`catalog.json` retains the selected upstream gallery's 124-card / 150-style reference metadata, with added status and adaptation mappings. Only the named nine local adaptations are executable. URLs in reference metadata link upstream preview/source material; they are not local render assets or a redistribution of those videos.

The selected files under `demos/`, `references/` and `assets/` are unmodified source/reference snapshots, not a standalone runnable copy of upstream. Their imported fixtures, product imagery, branded artwork, music, browser editor and publishing scripts are not bundled.

Modified implementation: `shot_renderer/src/shots.tsx` adapts the selected motion grammar into bounded, content-driven Chinese layouts with shared timing, local-font freezing, registered images and a final reading hold. This is not a pixel-identical port. `shot_renderer/src/vendor/DigitRoll.tsx` retains the upstream component with an added provenance/modification header, and is called through a normalized frame wrapper. Marker path geometry is adapted from MarkerUnderlineTitle.buildStroke with a fixed seed.

Workbench-authored orchestration/validation is MIT. The derived TSX files above retain Apache-2.0 provenance. Remotion/React and all transitive dependencies keep their own licenses; Remotion has independent commercial-use terms. No license for third-party fonts, audio or original product screenshots is granted by this repository.
