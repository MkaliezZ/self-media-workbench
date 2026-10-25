# Native transitions and alpha-mask acceptance

The user requested a coherent capability film because the earlier travel edit did not demonstrate appropriate transitions or real masks. Native effects now execute source-bound overlap transitions, source-region alpha composition and preserved PNG transparency. The film combines recorded public scenic inputs, original graphics/score and explicitly synthetic narration; it does not claim personal travel, product TTS/music generation, automatic image search or actual publication results.

## Retained failures and fixes

| Initial evidence | Finding | Revision |
|---|---|---|
| 041751e native Apple Silicon run [40185740695](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40185740695) | FFmpeg 7 rejected the first xfade with frame rate 1/0 | f2a04e4 added aggregate fps but did not fix the first input; retained failed [40186045373](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40186045373) |
| Same actual source filters | setpts after fps cleared frame-rate metadata on that runtime | a3c0604 moves setpts before fps; no clock tolerance relaxation |
| First independent FX film at 041751e | Title requested at frame111 appeared at112 | Native titles now use output frame-number gates, with an exact-boundary regression |
| Coherent film first native request/export | Independently rounded half-frame intervals lost two frames; mixed-aspect cover scaling left non-square SAR | Caller selects differences of absolute frame edges; renderer normalizes final SAR after fit |
| Visual review of the film's first master | A detail layer selected the scenic source's introduction card | New immutable plan selects actual wave footage, retaining the first master |
| Actual 90-second CUDA ASR without inference VAD | The next word was assigned to a preceding music-only hold (caption began56.96 for speech around60.45) | Enable inference-only VAD and retain returned original-source timestamps; new actual run begins the sentence60.55. No source media or hold is automatically cut |
| Complete styled showcase decode | A looped image extended the90s/2250-frame video to2251frames because AAC ended90.005s | Static overlays now stop at the finite main video, without an audio-duration stop flag; added a real AAC-tail decoded-frame regression |

## Independent task and scope

The independently designed observatory task and materials were sealed before receiving implementation commit041751e. It uses a different theme, mixed dimensions/fps, audio/silent sources, a diagnostic overlay and original music. The task SHA256 is `bf39387ff0ac7fe113f8144c88aec19eac27694fd48785f642dd6c43cbead9fb`. No expected product movie or main test fixture was given to the independent Agent.

At a3c0604, Windows sealed-material and freshly generated-material executions passed36 decoded pixel/audio/clock/recovery checks: full/control/restored405frames13.5s; real shape alpha/inward feather; original continuous music without restart; complete restored decoded frames/PCM equality; nine invalid effects rejected422 and stale revision409. Historical code6d3dc30 actually creates an old plan; current entry resumes, exports and replays that request without altering its original plan. The first title failure, reference-checker noise corrections and early reused stop-operation log path are disclosed, rather than describing every report as pristine.

Portable entry: `python scripts/independent_fx_acceptance.py --output <new-directory>`. [Sealed task](independent_fx/FX_BLIND_TASK.md), [procedure and limits](independent_fx/README.md). The visual diagnostic is a technical test, with a known source-text/title overlap; it is not the artistic showcase.

Native run [40186343749](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40186343749) at a3c0604 passed65 tests and real timeline/ASR/export paths on Windows, Apple Silicon and Intel Mac. Final media runtime [40187465771](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40187465771) at7d7d7da passed **66 tests on each platform**, including actual decoded six-transition pixel cases and the AAC-tail regression. Each native platform also passed the **independent sealed FX entry**, genuine historical-code resume/replay, changed-material travel task, HTTP restart and pinned real-scenery edit. Apple Silicon additionally executed actual MLX/Metal GPU ASR; hosted CPU compatibility is reported separately from the local90s NVIDIA CUDA film transcription. Raw summaries, pixel/audio measurements, historical compatibility and ASR results are retained in the run artifacts;22 selected original JSON reports and complete logs were archived locally. No platform simulation is accepted as native evidence.

The released film decodes to **1280×720,2250frames,90s video/90.005s audio**. It has42 reviewed caption cues, real local image/source-region composition and timecoded coverage. Five rendered music cuts at72–76s lie within6.531ms of analyzed score onset candidates. The final authored hold remains intact after a real pause-cut/restore comparison; the restored underlying video is byte-identical to the original export. Backend content stages are clearly presented as a workflow illustration rather than invented account data or publication outcomes.

Static masks are not automatic tracking/matting. Caption emphasis is by complete reviewed cue, without invented per-character alignment. Inference VAD reduces a demonstrated boundary error but does not certify recognition, listening quality or arbitrary speech timing. Known AI narration text supports this film's display corrections; ordinary recordings still require evidence and review.
