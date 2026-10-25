# DSH changed-material blind audit / DSH 换素材盲测

Status: **fix applied; independent product retest and native release CI pending**.
This is a live release record. A local test pass is not the independent verdict.

## Independent setup

DSH cloned public commit `91b267a0e0796e34119fe73ce94c1e8c42455611`, designed
an original synthetic rental-home account task, and sealed 18 input files before
its first README/AGENTS/schema read. The tool-event order was independently
checked. It did not receive previous fixtures, prior results or expected answers.
It reused an already suitable local Python, created separate project/service
state and downloaded a compatible small ASR model. This is not a pristine-OS
installation claim.

Original seal SHA256:
`1dc0635b62132729cc17e1931ccf4f7fdb149ad3a9c1d30decd73334ac8b6caa`.

Inputs include 37.831429 seconds of declared Windows SAPI Chinese speech, an
original 1080×1440 article, a 1080×1920 true-alpha foreground, and explicitly
synthetic account/review data. No actual platform publication occurred.

## Initial result and actual fixes

The initial DSH verdict was **conditional**, retained rather than replaced:

- Diagnosis → topics → script → publication preparation → simulated review
  produced actual persisted artifacts. Script v1 → v2 → restored-v1 remained
  readable. Resume, a second isolated project and owned-service restart worked.
- Actual faster-whisper small CUDA inference was verified (`int8_float16`,
  `gpu_inference_verified=true`). Original 105 ASR groups and three corrected
  recognition errors were retained. Ordinary cut/restore and advanced native
  exports actually decoded.
- **Product defect:** a 4096-byte truncated MP4 raised an uncaught probe error,
  returned HTTP 500 and left an unregistered copied original. It did not advance
  the project or create an export job. The fix returns an explanatory 422 and
  deletes only that newly generated import directory; the caller's input remains.
- **Maintainer follow-up defect:** an actually truncated finite-RIFF WAV was
  accepted as a 45 ms recording because ffprobe returned success. The isolated
  API reproduced HTTP 200. The fix checks declared RIFF extent before registration;
  this case now has a real regression, in addition to probe-error cleanup.
- **Contract gap:** native/advanced exports lacked a publication asset binding.
  They now bind a timeline plan and a real completed export without inventing a
  media ID. Checklist export references must also be bound publication assets.
  New ordinary and native primary videos freeze their SHA256; changed bytes,
  wrong plans/projects/types and missing/uncompleted exports are rejected.
  Older exports explicitly capture a hash at submission; they are not retroactively
  certified as unchanged from their original render.

The frozen independent-retest patch is based on the same public baseline:
`21c02938b083f3edee8f8db02ff46fb4c9b63ee608fe8eb38170a6614b620aa9`.
It contains runtime and operator docs, excluding the maintainer's regression-test
answers. Local current-code regression: **80 tests passed in 103.095 s**.

## Evidence-method failures and revisions

These are distinct from product defects. The initial report and analyzer were
archived with byte hashes; DSH confirmed originals and archive copies unchanged.

| Initial evidence weakness | Revised independent evidence |
|---|---|
| A field labeled measured yellow RGB and a dwell duration were literals | Actual decoded-pixel statistics and frame PTS; previous values retained |
| Frame cache used filename stem/time only | Fresh run directories plus tested-video SHA bindings |
| Four zero-error anchors compared subtitles with their own ASR timestamps | Claim retracted. Independent sealed-PCM silence detection uses four phrase starts at three thresholds; maximum error 0.0961–0.1251 s, under the sealed 0.8 s limit. This is phrase onset evidence, not word/phoneme ground truth. |
| A dangling subtitle phrase passed timing-only checks | DSH performed a new semantic review and actual subtitle/native-title exports; original SRT and videos remain |

The maintainer also retained an **invalid** raw SAPI timing experiment: its events
exceeded the actual WAV duration despite matching PCM. It is excluded as an
uncalibrated reference. A separate explicit-output-rate experiment paired all 80
events by source character positions independently of ASR and found a maximum
15 ms calibrated difference. Its scope and different-format PCM distinction are
retained; it does not replace human acoustic annotation.

Operator mistakes (CLI option position, a reserved shell variable, encoding,
layout/source-ID/stream-clock confusion and unsupported claims) remain separately
classified. Correctly rejected requests are not advertised as product bugs.

## Current retest and CI

DSH is applying the hash-pinned patch to its original checkout, restarting only
its owned idle service, and retesting the original corrupt input, truncated WAV
and PNG, real new exports, publication bindings, byte-tamper rejection and workflow
continuation. The original orphan remains historical evidence; success requires
no new failed-import residue. Terminal results and native CI links will be recorded
here after actual completion.

Tests: [import regressions](../tests/test_local_api.py),
[actual native publication binding/tamper regression](../tests/test_native_timeline.py),
[ordinary visual-output digest checks](../tests/test_visual_editing.py).

## 中文结论与边界

初次 DSH 盲测为有条件通过，发现的损坏视频 500／残留问题已修复；维护者追加的真正截断 WAV 被误接受反例也已修复，并补齐高级成片接发布准备的绑定。当前本机 80 项完整回归通过，DSH 正式复测与三平台 CI 尚待终态，不能提前写成全部通过。

首次失败、错误测量、修订脚本、旧字幕与旧片均保留。修复后的接口仍不把技术文件检查自动升级为人工听审、审美、事实／权利核验、真实发布或运营效果。全部账号与复盘指标均为合成测试数据。
