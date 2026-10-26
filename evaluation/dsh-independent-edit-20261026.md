# DSH 同素材自主剪辑 / Independently authored same-material edit

Final film: **v03, The Judgment Loop / 判断的循环**, 89.64 seconds,
1920×1080, 25 fps, 2,241 frames. [Watch / download](https://github.com/MkaliezZ/self-media-workbench/releases/download/dsh-edit-2026-10-26/dsh-independent-edit-v03-89s.mp4).

## Scope and attribution

A fresh DSH session used a clean clone of public commit
`0639cc98b6259868e6877ef787c7fee4c87532c5`. It received 43 sealed raw/input
files, including the existing static AI presenter, synthetic narration, graphics,
music/effects and inherited CUDA ASR/captions. The earlier finished movie, edit
recipe and original project state were not supplied. DSH chose its own scenes,
effect selection, pacing and layout, writing its editorial decisions before
compilation. An audit of 278 visible tool calls found no access to the named
previous recipes or films; the filesystem was not an enforced sandbox, so this
is an observed tool-log audit, not proof of inaccessible files.

The final timeline has 14 scenes and 31 native effects: 19 keyframe layers,
five motion-text effects, six motion layers and one original-document extraction.
It includes the keyword opening, alpha presenter layers, question cards,
abstract/concrete examples, script structure, source-pixel document emphasis and
a four-step loop. Native compile/save/export routes produced the new movie;
the renderer source was unchanged.

## Retained revisions and failures

- **v01:** independently authored initial design and completed export retained.
  Review found duplicated large text, an empty spotlight area, cards covering
  eyes, and white text competing with a white shirt/bright shelving.
- **v02:** DSH's own revisions were saved. Parent orchestration interrupted the
  owned service and export; no playable v02 exists. This was an orchestration
  incident, not a confirmed rendering-engine defect. Partial output is retained.
- **v03:** the maintainer supplied actual-frame problem descriptions, not old
  recipes or replacement coordinates. DSH chose dark underlays, removed a note
  and moved comparison cards. The final version therefore includes explicit
  review feedback and is not described as an entirely unassisted blind result.
- **Audio:** a default mastering attempt produced 245 clipped decoded samples.
  The selected -18.5 LUFS / -3.5 dBTP target produced measured -18.72 LUFS /
  -3.37 dBTP with zero clipped samples under the recorded analyzer. Failed and
  intermediate masters remain retained locally.

## Technical evidence

| Item | Result |
|---|---|
| Input seal | All 43 input file hashes unchanged |
| Original project | 405 JSON/SRT/TXT records unchanged; none added |
| Native plan | `6093bf1779764bacafba071f49cfd52d` |
| Native export | `79363028c22d489b9dc4c1b3e7067b62` |
| Completed job | `ae418ca5c74f413f984bbcbe62a8b25a` |
| Native MP4 | 12,708,050 bytes; complete decode passed |
| Published mastered MP4 | 12,665,183 bytes; complete decode passed |
| Video-stream preservation | Native/mastered H.264 elementary streams match |
| Delivery manifest | 415 entries verified; 24 local viewer links exist |
| Frame review | DSH sampled 106 frames; maintainer separately sampled 42 times and full-resolution 16/33/49.5/78-second frames |

Native SHA256:
`f77a9d264ced994484b8f4a28aba15df81e91bd5482af751294a2cda375d9b87`.

Published mastered SHA256:
`192303b80720d5894217408a128ea5ed45b177e68018cf0ef67030f06dcc095b`.

Shared H.264 elementary-stream SHA256:
`a53a9d946511d60b98f6c01637b8afa9ecfb77ba1cc6ffea4d0559df7f079273`.

This publication pass rechecked the selected file's SHA256, media probe and full
decode, and extracted its README cover from the actual mastered movie. Original
test logs, frozen versions, inputs and failed attempts remain in the private
local delivery; they are not bulk-published with personal paths or runtime state.
Public file metadata is in [samples.json](../docs/demos/samples.json).

## Review and publication boundaries

Technical execution passed on this Windows host. Actual-frame review confirmed
the targeted contrast and eye-occlusion corrections. Cards still cover parts of
the lower face/torso, and the final loop's supporting footer is small; these
remain stated aesthetic limits. Human listening was not performed. The original
quality-acceptance record remains `pending_user_review`; the maintainer's current
instruction separately authorizes public README/Release display of this test film.
It does not certify a new human listening or quality pass.

No new ASR inference, asset generation, macOS acceptance, CI run, real account
analytics or social-platform publication is claimed. Existing ASR timestamps are
inherited estimates. Synthetic examples do not establish marketing outcomes.
Music and media disclosures follow the [demo licensing notes](../docs/demos/README.md).

中文：本片是同素材自主编排测试，区别于前次按原配方逐帧复现，也区别于已被拒绝的衣柜样片。
初始设计由 DSH 自主完成，最终 v03 接受了实际帧问题反馈。技术执行与视觉问题复核已有证据，
没有新增人耳听审或用户质量验收；本次维护者明确授权在 README 和 Release 公开展示。
