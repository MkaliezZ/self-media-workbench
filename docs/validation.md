# Validation record

This MIT implementation has its own evidence; private-prototype passes do not automatically transfer. Initial regression: 27 tests; after independent findings: 30, then 31; after MLX integration: 36 Windows tests. Original logs and revisions remain in evaluation/ and [failure history](revisions.md). These tests include actual FFmpeg cut/restore/decode, not a mocked renderer.

## Actual operating-system runs

[Completed cross-platform run 39435126642](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39435126642), tested code 5f0900f, passed on Windows AMD64, macOS 15 arm64 and macOS 15 x86_64. Each performed native synthetic speech → real local CPU tiny ASR → HTTP review/export → complete MP4 decode, plus 30 regression tests and the installed Agent entry. Saved JSON is in evaluation/platform-windows-final, platform-macos-arm64 and platform-macos-intel. [Additional macOS 26 ARM/Intel probe](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39435261278) also completed successfully. These are specific OS/Python 3.11 runs, not a promise for every OS/hardware version.

Local Windows also executed medium-model CPU ASR and actual CUDA ASR after the MLX refactor, with no CUDA fallback errors. Original projects/heads/artifacts were retained locally, and the installed entry was invoked from a different Python successfully. Private paths/model/corpus are not distributed.

## Independent changed-material evaluation

DSH chose new synthetic appliance and balcony subjects, actually saved all five content phases and a separate script-only task, and performed medium CPU ASR, explicit cut/restore, 18 caption groups and decoded media export. Initial verdict was conditional. It corrected its own median-description mistake and retained submission errors. A second DSH round used another synthetic herb video (26 real groups, six caption groups, zero mismatches in exported IDs/source bounds/probabilities) and found a planned-metric evidence loophole. Both original conditional verdicts are retained.

A fresh independent Agent then made 28 focused submissions and found invalid timestamp strings were accepted; after fixing that, its next 28 actual submissions passed the tested null/evidence/arithmetic/ISO-timezone boundaries. The reports separate intentional negative probes, caller mistakes and product defects. Full raw material, attempts and reports remain privately under the task's evaluation directory; public [round-1 summary](../evaluation/independent-round1.md) and revision history do not claim first-pass success. No human account/platform/market validation occurred.

## Verified MLX GPU implementation

[Run 39439000073](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39439000073), code 289dc3f, completed successfully on **all three platforms**, with 36 regression tests per platform. Evidence JSON is in evaluation/verified-289dc3f/.

| Environment | Actual ASR evidence | Media result |
|---|---|---|
| Windows AMD64 | faster-whisper / CPU, 15 actual groups | ASR/export done, decoded |
| macOS 15 Intel x86_64 | faster-whisper / CPU, 15 actual groups | ASR/export done, decoded |
| macOS 15 Apple Silicon arm64 | CPU baseline plus **MLX / GPU**, real Metal kernel, isolated worker, 15 actual groups, no fallback errors | ASR/export done, decoded, gpu_asr_verified=true |
| Local Windows NVIDIA | medium model / CUDA after refactor, no fallback errors | Real recognition; independent round 5 also decoded the generated export |

The first MLX run e8fd5d9 also passed, but its smoke result retained a stale constant CTranslate2 model label. The subsequent 289dc3f result correctly labels MLX weights/model_format; the earlier raw artifact is retained rather than rewritten. This label bug affected evidence metadata, not the actual backend/device execution fields.

The final [source/plan/output timing run 39441097022](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39441097022), code **3cbf396**, also completed successfully on **all three platforms** with 36 tests each. Evidence is saved in evaluation/verified-3cbf396/. ARM's actual MLX GPU result has timing_verified=true: source/plan 6.6880625 seconds, decoded output 6.688027 seconds, unchanged retained IDs/bounds and all words within output. CPU baselines passed the same checks. No fallback occurred on the GPU path.

The [macOS 26 ARM/Intel run 39439555962](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39439555962), code 289dc3f, likewise passed both platforms; ARM ran actual MLX GPU ASR/export/decode. Its JSON is saved beside the 289dc3f results. Selection/fault unit tests remain explicitly mocked contract checks, separate from these real hardware runs. Subsequent documentation/evidence-only commits do not change the tested runtime.

scripts/ci_smoke.py records actual platform, architecture, backend/device, kernel execution, fallback reason, job terminal states and decoded output. gpu_asr_verified can only be true for actual MLX GPU transcription. A CPU fallback or unavailable hosted Metal must remain labelled as such. Explicit --require-gpu fails on CPU results. See [Apple GPU contract](apple-gpu.md).

## Independent fresh public clone

The [2026-10-21 installation audit](../evaluation/fresh-clone-20261021.md) used a real GitHub clone, fresh Windows venv, separate state/Agent home/cache and newly downloaded tiny model. The independent Agent requested no human commands or model paths, installed dependencies, configured the model, started the service and saved a new synthetic script. Actual CPU ASR produced 63 groups; two recognition errors were corrected while retaining original bounds, twelve subtitle groups were exported, and the 26.72-second video decoded successfully. The installed entry was invoked from another Python and selected the correct venv/project. Standard package downloads stalled and required substantial autonomous network recovery; the original failures remain. This is not a virgin-OS, clean-macOS or uninterrupted one-command installer test. No runtime defect was confirmed in this round.

## Fresh Apple Silicon and Intel installations

[Fresh macOS audit, 2026-10-21](../evaluation/fresh-macos-20261021.md): run 39469031595 on 432fb79 completed new public clones, isolated venv/state/model caches, real configure/install-skill/automatic service startup and first script/media tasks on macOS 15 ARM and Intel. ARM performed actual MLX/Metal GPU ASR without CPU fallback; Intel used faster-whisper CPU. Both retained 73 groups, repaired the fixture's short subtitle tails, exported/decoded and resumed the saved project. Separate run 39469037629 passed another new macOS 26 Intel installation. Driver and complete-artifact manifests rehashed without mismatches. Initial post-run evidence races and short captions remain documented, not rewritten as first-pass success.

## Limits

CI explicitly opts into downloading small public test models; production never downloads models automatically. GPU execution is separate from GPU performance; no fixed speed-up is promised. Timestamp/anchor/structure checks do not establish measurement truth or source entailment. TTS is not human listening, estimated script duration is not a human recording, separate SRT is not burned subtitles, and local export is not external publication or evidence of marketing effectiveness.
