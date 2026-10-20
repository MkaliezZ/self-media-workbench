# Local media review

Import absolute local files with source and nature declarations. Keep the immutable copied original and every ASR run. Use actual word-group IDs/bounds; ASR groups are not verified character alignment. Correcting text does not change timing or delete audio.

VAD non-speech and subtitle gaps are candidates, not automatic deletion. Keep negatives, qualifications, meaningful pauses and demonstration time. Select only explicit pause IDs or contiguous full speech groups with reasons, binding run/SHA/revision. Empty selections restore; omitted decisions preserve. Query asynchronous jobs to done or record the failure.

Automatic SRT is a candidate. Inspect semantic grouping and short cues. caption_groups uses all retained group IDs once in source order; it changes subtitle grouping only. Review source audio/context before removing genuine mistakes, repeats or takes; do not force a cut when none is justified.

For Chinese proofreading, distinguish actual homophone/negative/number errors from simplified/traditional spelling and equivalent numeric units. Keep raw ASR and log each correction against its existing word ID; a reference script may support local review but cannot supply missing timed words or establish what was actually spoken. Do not change a correct number merely to match the reference typography. Report reference-assisted correction separately from original recognition accuracy.

Group Chinese captions by clauses and sentence boundaries, checking the actual source intervals. A short tail can join the preceding clause of the same sentence; do not join it across a full stop or a demonstration hold simply to meet a minimum duration. Preserve the source word bounds. VAD padding can extend beyond an inserted test gap; inspect the full proposed interval and retain meaningful visual time. After restoring via a new review/export, verify complete source coverage, retained corrections/caption choices, and unchanged earlier exports; re-encoding need not reproduce original bytes.

Actual exports contain separate MP4/SRT/word JSON, edit mapping and provenance. Decode/probe real output, check necessary words and restore coverage, and inspect subtitle display in its target player. Re-encoding is not byte/frame identity. Rendering does not provide B-roll composition, subtitle burning, visual effects, source separation or a current platform upload check.

Read doctor's `gpu_setup_guide` when provisioning ASR. NVIDIA prefers CUDA, Windows AMD/Intel GPU uses separately built whisper.cpp Vulkan, Apple Silicon uses MLX, and Intel Mac may use separately configured whisper.cpp Metal. Keep actual failed attempts before CPU fallback; require_gpu can forbid fallback. CT2/MLX/GGML model formats differ. Inspect actual backend/device/execution/fallback fields. Some native engines provide only coarse segment groups: retain their declared alignment and actual bounds; never fabricate per-character timing to make edits appear precise.
