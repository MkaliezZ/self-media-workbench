# Native timeline acceptance — 2026-10-25

## Implementation and reconciled logic

Source seconds and output frames are independent of ASR. Silent/multiple-source video and registered stills can be assembled with explicit trims, contain/cover, independent original/voice/music/effect audio, gains/fades/limiting, native timed titles, reviewed onset grids, frame quantization and immutable cut/restore versions. Aligning a draft never extends beyond the approved source window or silently truncates incompatible audio. Originals, frozen plans, earlier exports and failures remain.

The preset catalog now contains 12 recipes. Five omitted mechanisms were restored: faceless reference-led explanation, evidence-led science, life/scene narrative, game/screen-event replay and first-person explanation. The separate logic catalog describes eight mechanisms and their component limits. Complex layer animation, automatic tracking/matting, time-warp, source separation and music generation remain excluded rather than being inferred from a template name.

## Initial local evidence

Windows full suite: **64 tests passed**. Five native cases exercised actual FFmpeg generation/render/decode, scene identity against actual source frames, exact 300-frame/12-second output, mixed orientation/frame rates, independent delayed audio, preserved silence, still-image holds, source hashes, cut to 11 seconds and restore to 12, immutable old export, head/revision/idempotency/bounds errors and corrupt-map rejection.

Actual loopback HTTP case started its owned service, imported sources with/without audio, detected musical onset candidates, aligned a draft, exported to terminal done, decoded output, restarted its owned idle service and resumed the same project/head. The selected interior onset targets differed from output-frame edges by approximately 2–8 ms in the authored fixture; this is one controlled clip, not a general music-beat accuracy claim.

The illustrated coastal case uses four locally authored scenes and original tonal/percussion music. It is explicitly generated material, not real travel footage. Meaningful silent visual holds remain. Technical pixel/waveform checks do not establish listening aesthetics, genuine travel experience or publication quality.

## First observations and revisions

- The first onset output was systematically early by about 24 ms because the timestamp used the window start. It was corrected to the analysis-window centre. Actual authored onsets were then checked; the original analysis output is retained.
- Silent-media import had formerly been rejected at the shared import endpoint. It now records has_audio=false and permits native assembly; the ASR route separately rejects silent sources instead of making a failed transcription job.
- Old full-video, sound-design and complex-effect observations are not promoted to completed research or tested artistic methods. The method catalog explicitly preserves unsupported components and excludes promotional/client-review content.

Independent fresh-clone, changed-material acceptance and native Windows/Apple Silicon/Intel cloud runs are recorded below when executed. Initial local evidence alone is not their completion.

## Native-clock failure and correction

The first native [cloud run](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40181258207) exposed a real clock defect on macOS: the requested 300-frame montage decoded to 298 frames, and an 11-second revision measured 10.92 seconds. The strict checks failed; their thresholds were not relaxed. Normalized segment clocks now use filter frame limits, exact PCM sample clocks, explicit concat durations and no intermediate B-frame reordering. A container-wide video-frame limit that could stop other streams early was removed. The final video/audio clocks are explicitly bounded, and the exporter now reads actual decoded frame counts/durations into timeline-verification.json and fails if they disagree with the saved map. Segment PCM sample counts and video frames are also checked by the acceptance suite.

The corrected Windows native cases passed again. Native Mac re-execution is required; a Windows pass is not substituted. The initial Mac artifacts/logs and the first timing analysis remain in local evidence.

A further native diagnostic reported 299/300 video frames and 11.96-second video while audio was now exactly 12 seconds. That intermediate correction was insufficient and remained a failure. Export errors now include measured clocks, and test folders are retained before setup so setup failures keep native files. Redundant container-wide stop times were then removed: finite video-frame/audio-sample filters are the sole end conditions, with explicit CFR/encoder time bases. Final decoded verification remains strict.

The original large failure artifact remains remotely retained. A range-based read archived selected actual segments/map/MP4 locally: each first-run Mac segment reported a container duration one frame shorter than its decoded frame count, and the first final MP4 decoded to 298 frames/11.92 seconds. A large full-archive transfer was stopped; selected raw evidence and logs were preserved. Later artifacts exclude system font binaries while retaining font hashes.

## Independent changed-material check

An independent Agent designed/sealed its task and four travel-animation/music inputs before receiving product commit 380f904. It then freshly cloned the public repository, used only the documented entry/capabilities and its own sources, and executed baseline/cut/restored exports. On Windows these measured 16/15/16 seconds and 480/450/480 frames, with zero music-clock lag and unchanged original hashes; baseline/restored MP4 hashes were identical on that host. See [the independent case and its declared limits](independent_travel/README.md).

The first independent image checker incorrectly assumed pure-black padding. It was corrected to compare only source-bearing pixels without changing the sealed task/materials or error threshold. Its report-path reuse and reconstruction are explicitly disclosed, rather than claimed as untouched original evidence. This was a measurement repair, separate from the real Mac product-clock defect. Its portable changed-material entry has been added to each native OS job; platform results will be recorded after execution.

## Reproduction

`python -B -X utf8 -m unittest discover -s tests -v` and `python -B -X utf8 scripts/timeline_http_acceptance.py --out <new evidence folder>`. Set TIMELINE_EVIDENCE_ROOT and VISUAL_EVIDENCE_ROOT to retain original requests/inputs, rejected attempts, failed jobs, frozen assets, process logs and outputs. The compatibility workflow runs both checks on native Windows, macOS ARM64 and Intel; generated test media is reproducible and needs no model for the timeline path.
