# Revision and failure history

## Initial MIT implementation

New unified task API/CLI and an independently authored Python/FFmpeg renderer. The AGPL prototype renderer, private course corpus and user projects are excluded. Windows regression: 27 tests passed. Real local CPU ASR and HTTP export/decode also passed; these do not transfer the prototype's independent acceptance to this implementation.

## Interpreter selection found during integration review

The first installed wrapper used the calling Agent's Python. Agents with another interpreter could then miss the installed workbench dependencies. The wrapper now prefers the checkout's virtual environment, then the interpreter recorded privately at installation. A Windows invocation from a different bundled Python selected the recorded interpreter successfully. The cross-platform smoke also exercises the installed entry. No content answers were provided to the independent evaluator.

Subsequent actual CI failures and independent evaluation findings are appended here; initial failures must not be rewritten as first-pass success.

## Runner allocation

The initial Windows CI completed successfully. macOS 15 ARM/Intel jobs remained queued without runner names or executed steps; this is pending allocation, not a compatibility pass or an observed code failure. A manual macOS 26 ARM/Intel runner set is available to test alternate hosted capacity. Superseded queued workflows may be cancelled; their original statuses remain visible in Actions.

## Independent DSH changed-material round 1

DSH independently chose a synthetic rental-appliance account and a separate synthetic balcony TTS video, without tests, prior evaluation answers or earlier private materials. It completed five content stages, direct script entry, explicit project/session resume, actual CPU medium ASR (109 groups), full-group cut/restore, 18 caption groups and decoded export (98 groups). It caught and revised its own inaccurate median description; this initial content error and rejected requests remain in the private record. The initial report was **conditional**, not a clean pass.

Confirmed product findings and fixes:

- All-current continuation incorrectly started another topic cycle. It now returns complete/null/empty plan; an explicit next-topic request still runs topics. Complete means saved stages, not publication approval.
- Submission revision/source-vs-artifact contracts were underspecified. Schema, Agent instructions and conflict errors now state the project lock and correct evidence binding.
- Entirely unknown metrics no longer need invented collection times/anchors; numeric observations still require both. Null is not zero.
- Export words now preserve ASR ID, original source bounds and original-group probability alongside mapped output bounds.
- Correcting an English token without its original separator could join adjacent words. Corrections now retain existing edge whitespace.

Post-fix Windows regression: 30 tests passed, including completed resume, unknown-vs-numeric evidence, original/export word identity, explicit FFmpeg cut/restore/decode and correction spacing. DSH's original report was written before its 15-minute harness timeout; the timeout receipt is preserved separately and is not reported as a normal final tool exit. A bounded independent retest follows.

## Independent DSH round 2: remaining planned-metric loophole

DSH verified the completed resume fix, schema descriptions, null metrics, original IDs/bounds/probabilities and whitespace with another synthetic 13.46-second herb TTS video (26 actual ASR groups, six caption groups, fully decoded export). It also found a genuine remaining gap: numeric values without evidence/time were accepted when observation_type was planned. Round 2 was therefore still conditional; its accepted negative probe is retained, not rewritten or deleted.

The numeric guard now applies to **all** review types, including standalone/planned; future targets belong in next_experiment/stop_rule rather than observed values. The regression explicitly checks both planned and simulated numeric cases. A final independent focused retest verifies this boundary.

## Independent focused round 3: timestamp syntax

A fresh independent Agent checked 28 actual submissions on new synthetic material. Missing, numeric, derived-ratio, anchor, arithmetic and stale-version boundaries behaved correctly, but `collected_at=not-a-time` was accepted. This newly observed defect is retained in the round-3 report. Collection timestamps now require a valid ISO 8601 datetime with timezone; impossible dates, arbitrary strings and missing timezone are rejected, while unknown time remains null. This verifies syntax only, not that collection actually happened. Regression and independent boundary retest follow.

## Independent boundary round 4

The independent Agent made 28 actual submissions after the timestamp fix: invalid strings/dates/timezones were rejected; valid Z/positive/negative offsets and unknown null succeeded; unanchored direct/derived numeric values were rejected and an evidenced 18/120 derived to 15%. No new defect was found in those tested boundaries. Requests, returned attempts, revisions and source hashes remain in a separate private round; round 3 is intact. Published truth, all ISO variants and real measurements were not established.

## Apple GPU addition requested after CPU compatibility

The user requested Apple GPU acceleration. Added separate local MLX weights/config, native Apple Silicon auto-selection, isolated Metal inference worker, real GPU-kernel check, actual engine/device provenance and recorded CPU fallback. Existing CUDA and shared word/VAD/edit timelines remain. Contract mocks test selection/error cases only; they are not GPU evidence. Windows regression reached 36 tests. Actual Apple GPU capability/ASR/export is measured separately by the ARM CI probe; unavailable hosted Metal must not be rewritten as GPU success.

## Independent MLX-integration round 5 on Windows

The independent Agent chose another synthetic cable-wrap subject and actually ran auto/CUDA, explicit CPU and requested-MLX/CPU-fallback ASR (24 groups). It grouped subtitles, exported generated video and decoded it, verified the original hash and retained all attempts. Pure-WAV MP4 export was explicitly rejected; the evaluator retained that input and labelled its new color-video wrapper as generated. Its unrelated Python PATH mistake was corrected explicitly. No product defect was observed in these exercised paths; this Windows round cannot validate Apple Metal or the MLX worker. ARM CI remains the separate GPU evidence source.

## Actual Apple GPU and cross-platform results

Run 39439000073 on 289dc3f passed Windows, macOS 15 Intel and macOS 15 ARM, each with 36 regression tests and actual local ASR/HTTP export/decode. ARM also ran native MLX GPU transcription: real Metal kernel verified, isolated worker, no CPU fallback, actual 15 word groups and decoded export. The first e8fd5d9 smoke had an outdated constant model label; 289dc3f corrected model/model_format while retaining the first artifact and its genuine GPU execution fields. No speed-up ratio is inferred from independently generated TTS clips.

The subsequent smoke additionally records source/plan/output durations and verifies unchanged word IDs/bounds on its keep-all export, to make timeline acceptance directly auditable. It does not alter runtime inference/rendering behavior.

Final run 39441097022 on 3cbf396 passed all three platforms (36 tests each), including actual ARM MLX GPU inference and every source/plan/output timing check. Additional run 39439555962 passed macOS 26 ARM/Intel with actual ARM GPU ASR/export/decode. Final source durations, hashes and actual device fields are retained verbatim in evaluation/verified-3cbf396 and verified-289dc3f. Later commits only finalize documentation/evidence, without changing the tested runtime.

## Independent GitHub fresh-install audit — 2026-10-21

The independent evaluator cloned efaa191 into a fresh isolated Windows application environment, later fetched documentation-only e650e2d, and actually installed public dependencies/model, configured the service, installed the Agent entry and completed a new synthetic script plus real CPU ASR/export/decode. Standard PyPI/mirror attempts stalled; host launcher/calling-path mistakes and network retries are retained separately from product defects. Its temporary official-metadata/range downloader and offline wheel installation were evaluator recovery, not a shipped bootstrap feature. pip check passed. No runtime defect was confirmed in the exercised scope, so no environmental workaround is presented as a runtime repair.

The original ASR's two recognition errors and English timing-check mismatch remain in the audit. Corrections retained all 63 IDs/bounds/probabilities; twelve caption groups and the 26.72-second output passed decode/source/timing checks. The installed wrapper was really invoked by a different Python and selected the fresh venv and same project. User-requested documentation naming changes and an explicitly recorded redaction of unrelated copied documentation were applied without removing failure commands/errors. [Detailed scope and results](../evaluation/fresh-clone-20261021.md).

## Fresh macOS installation preparation — 2026-10-21

Review for the new Apple Silicon/Intel installation audit found that the bundled media reference still described all macOS ASR as CPU. This contradicted the implemented Apple Silicon MLX adapter and the entry instructions. The reference now distinguishes native Apple Silicon MLX/Metal from Intel CPU and requires actual engine/device/execution/fallback evidence. Historical CPU test results are preserved. This is a documentation repair, not a newly observed GPU inference failure; fresh cloud results are recorded separately.
