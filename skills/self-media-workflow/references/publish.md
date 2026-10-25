# Publication preparation

Bind the current script and actual media/export IDs. Supply a title, optional cover text, caption, disclosure, primary action and checklist of actual/missing checks. The output is preparation, not a real external publication.

Discover the current `publish` schema. Ordinary media keeps `{"media_id":"...","export_id":"..."}`; a native or advanced timeline export uses `{"kind":"timeline","timeline_plan_id":"...","export_id":"..."}`. The export must belong to the same project and source/plan, have an actual completed job and an existing output. Do not invent a media ID for a timeline export.

Checklist rows retain source quotes in `evidence`. They may also reference actual exports using `export_ids`, but every referenced export must be bound in this submission's `assets`. These references support technical file checks; they do not certify listening, factual accuracy, rights, labeling or real publication. Leave unperformed checks missing. New ordinary and timeline exports freeze their primary video SHA256; publication rejects changed video bytes. Legacy exports without an output digest are explicitly recorded as `captured_at_submission`, not retroactively verified against their original render.

Disclose synthetic/reconstructed/mixed material and material commercial relationships. Check any current platform format, labeling, eligibility and industry requirement using current authoritative sources or the actual account. Unknown checks remain missing; do not auto-upgrade readiness from a successful API response. SRT sidecars are not burned captions, and local playback is not platform transcoding verification.
