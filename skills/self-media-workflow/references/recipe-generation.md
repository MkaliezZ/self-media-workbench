# Generate an editing recipe from logic

Use when existing presets do not fit or the user requests a new industry/video type. The calling Agent designs the recipe. The server validates/compiles; it does not invoke another model or discover content by itself.

Separate **industry**, **video form**, **viewer goal** and **material constraints**. Travel is an industry/topic; Vlog is a form. Do not assume every travel clip needs drone footage, a music montage or a fixed cut rate. Choose the structural logic from the actual story:

| Viewer need | Possible semantic progression | Crucial condition |
|---|---|---|
| Understand | question → mechanism → evidence → boundary | Explanations do not fabricate evidence |
| Repeat an operation | goal → action → result → reproducibility | Required steps and meaningful waits survive |
| Experience a journey | expectation → encounter → response → reflection | Actual scene/action relationships survive |
| Compare | criteria → comparable observations → tradeoffs | Comparable definitions/conditions exist |
| Understand a person | question → answer → follow-up → synthesis | Actual recorded statements are not reconstructed |
| Follow an event | setting → key event → response → aftermath | Reordering does not invent causality |

These are reasoning patterns, not mandatory script formulas. Use 2–8 meaningful roles only when actual material supports them. Every role defines purpose, shot_logic, pacing_logic and audio_logic. Explain which shots/information matter, why a hold/cut is appropriate, and what original sound should remain. A different title or palette alone is not new editing logic.

Read `schema editing-recipe`. Generate a strict custom_* definition with industry, video_type, viewer_goal, roles, material requirements, avoid rules, horizontal/vertical slots, emphasis roles and captions. Validate via validate_editing_recipe; status structure_validated with semantic_verdict not_verified is not content acceptance. Store the design with the project/work output; validation alone does not save it.

Use execution_mode=narrated_single_source_2d only for already oriented single-source video with actual reviewed ASR groups and supported caption/image/static-region operations. Original audio stays synchronized. The prose shot/pacing/audio logic guides the Agent's review; it does not automatically perform new camera movements, mixing or multi-source assembly.

For pure visual Vlog, multiple sources, reviewed music edges or independent audio tracks, use native_timeline mode and read timeline.md. Select actual source seconds, explicit audio intervals and approved music edges; attach the custom recipe to timeline-plan.recipe. Do not use the ASR compiler or invent spoken IDs. Unsupported tracking, complex group animation, time-warp or generated music stays planning_only with missing_capabilities; do not substitute a different effect silently.

An executable custom recipe is passed as editing-template.custom_definition. Bind the actual source/review and map complete retained words to roles as described in [industry.md](industry.md). Compile, inspect, save unchanged and export. The service freezes the custom definition/hash and rejects operation tampering. A new recipe version is a new plan; old definitions/exports remain. Inspect actual frames/audio before calling the result usable.
