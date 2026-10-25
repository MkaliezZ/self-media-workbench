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

## Reproduction

`python -B -X utf8 -m unittest discover -s tests -v` and `python -B -X utf8 scripts/timeline_http_acceptance.py --out <new evidence folder>`. Set TIMELINE_EVIDENCE_ROOT and VISUAL_EVIDENCE_ROOT to retain original requests/inputs, rejected attempts, failed jobs, frozen assets, process logs and outputs. The compatibility workflow runs both checks on native Windows, macOS ARM64 and Intel; generated test media is reproducible and needs no model for the timeline path.
