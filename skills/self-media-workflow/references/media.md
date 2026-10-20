# Local media review

Import absolute local files with source and nature declarations. Keep the immutable copied original and every ASR run. Use actual word-group IDs/bounds; ASR groups are not verified character alignment. Correcting text does not change timing or delete audio.

VAD non-speech and subtitle gaps are candidates, not automatic deletion. Keep negatives, qualifications, meaningful pauses and demonstration time. Select only explicit pause IDs or contiguous full speech groups with reasons, binding run/SHA/revision. Empty selections restore; omitted decisions preserve. Query asynchronous jobs to done or record the failure.

Automatic SRT is a candidate. Inspect semantic grouping and short cues. caption_groups uses all retained group IDs once in source order; it changes subtitle grouping only. Review source audio/context before removing genuine mistakes, repeats or takes; do not force a cut when none is justified.

Actual exports contain separate MP4/SRT/word JSON, edit mapping and provenance. Decode/probe real output, check necessary words and restore coverage, and inspect subtitle display in its target player. Re-encoding is not byte/frame identity. Rendering does not provide B-roll composition, subtitle burning, visual effects, source separation or a current platform upload check. macOS ASR is CPU; GPU availability and fallback must be reported from actual inference.
