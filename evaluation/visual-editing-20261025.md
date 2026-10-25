# Local visual editing acceptance — 2026-10-25

## Scope

Windows local execution: complete-cue emphasis, local PNG/JPEG contain-fit placement, static video/image rectangles, immutable visual plans, source-time projection, cut/restoration, current-context discovery and task input registration. All media processing tests use actual FFmpeg; API calls use isolated FastAPI TestClient. No user project or original is changed.

Materials: self-generated four-second blue 320×240 video with sine-wave audio, a two-colour PNG and its JPEG conversion, manually aligned Chinese text. These are technical fixtures, not real speech or market evidence. No ASR quality, audio aesthetics, real-account publishing or universal semantic acceptance is claimed.

## Results

- Full suite: **53 tests passed** after fixes, including five new actual visual/API cases and two state-I/O cases. After the final static-image frame-count guard, all five visual cases passed again.
- Real outputs decoded completely. Decoded RGB samples confirmed image placement; source-image rectangle coordinates were checked after contain-fit.
- A 0.7-second pause cut moved an image event from source 2.1s to output 1.4s; restoration returned it to 2.1s. Old visual plans were rejected with 409 after review changes.
- Source and earlier export hashes stayed unchanged. Original transcript, rejected requests, failed jobs and revised plans remained.
- Real loopback HTTP task entry started its service, registered an image and exposed the new schema. An owned idle test service was stopped and the same project resumed through automatic service startup; owned test services were then stopped. This is intake/resumption evidence, not autonomous semantic completion.
- Multiple images, JPEG, captions disabled, CJK paths/fonts and literal text containing braces/backslashes/percent expressions passed real rendering. Overlong captions failed explicitly; a revised shorter version exported successfully while the failed export remained.
- Wrong project/review/run/source bindings, missing/deleted anchors, invalid rectangles, wrong image hashes, changed idempotency payload and tampered frozen images were rejected.
- Product text/code scan found no prohibited platform terms, creator name/account or tutorial video URLs.

## Failures and revisions

1. First harness run: the isolated projects parent directory was absent. Fixed the test setup; retained the failed log. No product behaviour was validated by that run.
2. Expanded run: a finished multi-image export stayed `running`. Evidence showed a complete `done` JSON temporary file and completed render/provenance, but the old job file remained. This is consistent with Windows replacement being denied while readers poll. Added shared read/write locking and bounded PermissionError retries, plus concurrent-polling and transient-denial tests. Full suite then passed. This is a state-persistence fix, not an image-filter fix.
3. HTTP harness initially assumed status.data_dir existed; verified the actual context snapshot location instead and reran successfully. No product API claim was based on that failed harness.
4. Overlong-caption rejection is an intentional guard, preserved as a failed job. It is separate from the harness/atomic-state defects above.

Raw local evidence is kept outside the public checkout: initial logs, isolated run projects, accepted/rejected attempts, failed job/temporary JSON, original/base/styled exports, frozen image/font inputs, FFmpeg process logs and inspected preview frames. The public report describes reproducible checks without distributing private machine paths or system fonts.

## Remaining boundaries

Follow-up: the initial cloud run failed on all three systems due to relative test evidence paths; both Macs also rejected copying system-font metadata. The failures and fixes are preserved in the [industry/form follow-up](industry-templates-20261025.md). The earlier 53-test result remains a Windows local result.

At the initial 53-test record, no new macOS run or independent Agent blind test had been performed for this addition; the later three-platform verification is recorded in the industry/form follow-up. Historical macOS ASR results do not cover this visual path. The existing Windows/Apple Silicon/Intel compatibility workflow now runs these tests, retains visual test evidence and provisions text-capable FFmpeg on macOS when needed; it runs on push, and no new macOS result is available at the time of this record. Font/filter availability and real frames must be checked on both Mac architectures before a cross-platform pass is claimed.

Online image search, automatic tracking/matting, complex animation, voice/music generation and external publishing are not implemented. CPU composition is separate from GPU ASR. Asset declarations do not prove factual suitability or usage rights.

Final follow-up: [run 40179335454](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40179335454) passed all three platforms with the expanded 59-test suite and real render/native-media checks. The original Windows-only scope above is historical. Independent blind/real-content acceptance remains unperformed for these additions.
