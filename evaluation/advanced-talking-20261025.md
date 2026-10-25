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
| Apple Silicon / Intel Mac |NOT_RUN for this revision. The user approved sample publication. Native workflows will now execute after push; no new cloud result is claimed until their actual terminal results are recorded. |

The local clean-baseline HEAD is1aec729 plus this reviewed working tree; the
independent report records immutable source fingerprints. It is not a claim
that the new runtime has already been published.

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
portable and hash-pinned. The prepared
[`advanced-talking.yml`](../.github/workflows/advanced-talking.yml) executes the
full regression, actual independent cases and delivery mastering separately on
Windows, Apple Silicon and Intel Mac, uploading retained evidence. A platform
must run natively; a simulated pass or copied result does not count.

The main sample, original inputs, detailed independent reports, failed exports,
ASR engine evidence, final native plans and human review state remain in the
local delivery. The user approved sample publication on 2026-10-25. Push the reviewable change, inspect every actual workflow conclusion, repair real failures and rerun affected checks before updating platform statuses.
