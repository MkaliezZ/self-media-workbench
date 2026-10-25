# Advanced talking-head revision: local evidence and release CI

This revision adds a distinct advanced production profile, bounded planar image
keyframes, original-pixel highlight/inversion and per-layer finish. Ordinary
ASR/review/caption editing remains available. Native scene manifests and sources
are frozen; actual selected audio intervals are checked for non-silent signal.
Signal is not a speech, transcript, listening or aesthetic certification.

## Current evidence

| Scope | Actual result |
|---|---|
| Windows full regression |78 tests passed. Seven advanced tests include actual H.264 pixels, intermediate return keys, original alpha holes, deterministic finish, inverse glyph pixels, negative keys and actual zero-PCM rejection. |
| Independent changed-material case | Seven18-second/540-frame exports;23 rejected invalid requests; source pixels, sealed decisions, intermediate perspective, original alpha holes, independent vignette/grain controls, PCM, immutable state, revision/restoration and actual owned-service restart passed. |
| Independently sealed Supplement | Three12-second/360-frame exports; original glyph multiply/invert scans and held state, real cropped alpha-mask compilation, PCM, frozen source hashes and five rejections passed. |
| Main sample |90-second/2250-frame native production with a fictional static office portrait and declared synthetic normal-rate narration. Raw original video underwent actual NVIDIA CUDA ASR;283 groups retained their bounds,48 reviewed subtitle groups,8 normal pause candidates kept. This does not establish human listening/aesthetic approval. |
| Final delivery sound | Explicit two-pass post-processing retained the native H.264 elementary-stream bytes and90-second video clock. Measured-17.22LUFS/-1.74dBTP; original native export and every process/measurement report retained locally. |
| Native release CI | All nine jobs passed on Windows, Apple Silicon ARM64 and Intel Mac x86_64. Each host passed 78 regression tests, 27 actual changed-material media checks, 23 rejected invalid requests, real restoration/restart, and 49 supplement checks with five rejected invalid requests. Actual delivery mastering preserved each host's video stream. See the [immutable run/job index](advanced-ci-20261025.json). |
| Actual ASR paths in compatibility CI | Windows and Intel Mac passed real CPU ASR/export. Apple Silicon passed both CPU baseline and actual MLX GPU ASR/export (`gpu_asr_verified=true`, no fallback). This adds no AMD/Intel Vulkan or Intel Mac Metal hardware claim. |

The runtime was published as commit `79ac8a03b10e6d618f4b8948cceb3b95c26c166c`,
based on `1aec729`. The independent report records immutable source fingerprints.
The two exact final sample movies are public release assets, with hashes in
[samples.json](../docs/demos/samples.json). Later documentation-only commits do
not change this tested runtime.

## Real failure and repair

The independent first run demonstrated a real defect: a video with an AAC
stream whose decoded PCM was entirely zero compiled and exported as a silent
talking-head film. The retained failed movie was measured at zero peak/RMS.
The fix checks actual selected source/voice-bed intervals during compilation,
save and export integrity verification. The same bad material now returns422;
an old saved bad plan returns409 on export before starting a job. An idempotent
old receipt can still be read as history, which does not authorize export.

The first full local regression also encountered a Windows font-file handle
remaining open after failed text preflight. Reading the font through an in-memory
buffer fixed it; the targeted suite and final full78-test suite passed.

Independent comparator revisions remain distinct from product defects. One
end-frame comparator initially misclassified a small H.264 prediction residual;
the scan Supplement initially used asymmetric thresholds for a255-minus-pixel
inversion. Both original scripts/failed results were retained. Corrected
comparators preserve the original source/geometry and acceptance criteria.

## Reproduce after release approval

The original input capsules in
[fixtures/independent-advanced](fixtures/independent-advanced/README.md) are
portable and hash-pinned. The
[`advanced-talking.yml`](../.github/workflows/advanced-talking.yml) executes the
full regression, actual independent cases and delivery mastering separately on
Windows, Apple Silicon and Intel Mac, uploading retained evidence. A platform
must run natively; a simulated pass or copied result does not count.

The main sample, original inputs, detailed independent reports, failed exports,
ASR engine evidence, final native plans and human review state remain in the
local delivery. The user approved publication on 2026-10-25. All three workflow
runs completed successfully on the first CI attempt; there was no failed CI job
to repair in this release. Earlier local failures and comparator revisions remain
recorded above and inside the unchanged capsules.

## Native cloud results

| Workflow | Windows | Apple Silicon | Intel Mac |
|---|---|---|---|
| [Advanced production](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40222396994) | PASS | PASS | PASS |
| [Compatibility, actual ASR and native exports](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40222396997) | PASS | PASS; actual MLX GPU | PASS; CPU ASR |
| [Independent sealed matte case](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40222396993) | PASS | PASS | PASS |

The unchanged supplement retains a historical Windows-only scope string from
its initial local report. That string is not native-host evidence; the cloud
job/runtime manifests and actual new exports establish the separately recorded
ARM64/x86_64 executions. No original sealed input or comparator was rewritten
to relabel historical results. Native technical checks do not establish human
listening, aesthetics, universal ASR accuracy or publication effectiveness.
