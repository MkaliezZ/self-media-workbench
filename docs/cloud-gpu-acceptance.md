# Real cloud GPU acceptance

No paid resources are authorized for the current audit. Standard public-repository GitHub runners are allowed. Do not select larger paid runners, attach billing, create paid instances or assume that an advertised free trial is an accessible account.

## Hardware gate

Record the actual OS, native CPU architecture, exposed GPU vendor/device, driver and API. An AMD EPYC or Intel Xeon CPU does not establish a GPU. Reject CPU/software Vulkan renderers such as lavapipe, llvmpipe and SwiftShader. Native Metal device enumeration plus a completed compute command with verified readback is a prerequisite, not ASR acceptance. An Intel guest with no Metal device cannot certify an Intel Mac GPU.

The manual `intel-metal-probe.yml` workflow uses only standard `macos-15-intel` and `macos-26-intel` runners. It captures native display data and compiles/runs `metal_probe.swift`. The JSON status distinguishes `environment_unavailable` from `ready_for_actual_asr`; a green probe workflow means the probe finished, not that ASR passed. Review the artifact result rather than the badge. The compiled prerequisite binary is omitted from the artifact and identified by SHA256 in the revised probe result.

## Identical Chinese material and acceptance

Use `fixtures/chinese-talk/synthetic-zh.mkv`, SHA256 `e0deca3bc5570b27f771b8b00efa038ad0a20812e3c12a822f5e3277698f855a`. It is generated TTS, not a recorded customer. Retain its fixture metadata/reference and original bytes. Do not regenerate it for a different platform or replace a failed run.

After access and hardware gates pass, use a fresh public clone, isolated venv/state/model cache and the same multilingual small model family. NVIDIA uses CUDA; Windows AMD/Intel uses whisper.cpp Vulkan; native Intel Mac uses whisper.cpp Metal. Provision GGML weights explicitly with `scripts/setup_cpp.py` and retain its model revision/hash and build logs. `require_gpu` must forbid CPU fallback. Linux Radeon results, if obtained, do not certify the Windows Radeon driver route. AMD Instinct/ROCm or a managed inference endpoint does not certify Radeon/Vulkan.

Preserve and inspect all four actual stages:

1. Raw Chinese ASR and native engine logs, selected backend/device, positive GPU model allocation, actual completion and no fallback. Save recognition error edits and raw/format-normalized CER against the known synthetic reference separately. Reference-assisted correction is not raw ASR accuracy.
2. Subtitle groups bound to the actual ASR IDs and unchanged native offsets. Check Chinese clauses, sentence endings, readable duration and the demonstration hold. Coarse native segments cannot be split into invented word timestamps.
3. Inspect every decoded source sample in the proposed silence cut. Remove only a safe candidate overlapping A (10.91525–13.31525); preserve demonstration hold B (40.448875–42.248875). Decode the cut video and validate the real edit plan and source mapping.
4. Restore A, retain corrections/grouping, decode the restored video, verify complete 50.2-second source coverage including the video tail, and rehash source/original ASR/previous exports. Keep failed requests and revisions.

`scripts/chinese_acceptance.py` contains the existing CPU/MLX Chinese baseline. Its current `windows` and `intel` profiles explicitly select CPU; running them unchanged is not AMD/Intel/Intel-Metal acceptance. `scripts/gpu_strategy_smoke.py --require-gpu` checks actual configured ASR/full export, but does not by itself check semantic captions or the full pause/restore sequence. Neither script is a replacement for the four-stage review above.

## Free access candidates (checked 2026-10-21)

| Candidate | Access boundary | What a successful test could establish |
|---|---|---|
| [AMD Radeon Test Drive](https://www.amd.com/en/developer/resources/cloud-access.html), [Colfax](https://experience.colfax-intl.com/project/amd-rocm/), [Comino](https://www.grando.ai/promo/experience-amd-rocm-on-radeon-tm-pro) | Free evaluation subject to application/approval; no usable login or approved instance found in this audit | Exact Radeon model/API/OS exposed after access; advertised ROCm access alone is not Vulkan proof |
| [AMD Developer Cloud credits](https://www.amd.com/en/developer/resources/technical-articles/2026/how-to-claim-amd-cloud-credits.html) | Member request and approval; no credits activated here | Instinct compute on the supplied OS, not Windows Radeon acceptance |
| [Intel Cloud Services](https://cloud.intel.com/), [request guide](https://cloud.intel.com/docs/how_to_request.html) | Browser reached sign-in form; no existing login/approved instance. Current availability and free entitlement must be checked after login | Exact Arc/AI PC GPU, driver/API and OS; Xeon-only and Gaudi-only instances are unsuitable |
| Standard GitHub Intel macOS runners | Existing authorized free workflow; actual native Metal probe required | Only the hardware/API actually exposed to that guest |

Do not submit personal/company details, accept new account agreements or contact provider staff without the user's authorization. Discovery is not an application, allocation or successful hardware test. Preserve inaccessible and GPU-less environment results as such.
