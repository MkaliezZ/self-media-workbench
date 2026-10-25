# Industry/form recipe acceptance — 2026-10-25

## Implemented scope

Seven built-in recipes: education, finance/business, beauty services, product presentation, food/local visits, home/property and narrated travel Vlog. Each has ordered semantic roles, material requirements/exclusions, emphasis defaults and horizontal/vertical image slots. These differ in structure and composition, not only colour.

The calling Agent can generate a strict custom recipe from industry, video type, viewer goal and actual materials. Roles describe story purpose, shot logic, pacing logic and audio logic. The service validates, compiles supported single-source narration-based 2D operations and freezes the definition/hash with the saved visual plan. Prose does not automatically execute new camera/mixing/time-warp operations. Unsupported visual-only, multi-source or music-driven designs are planning-only with explicit missing capabilities; compilation rejects them.

## Windows local results

Full suite: **59 tests passed**, including six new recipe cases. Actual FFmpeg output and complete decoding covered seven presets, a custom travel narrative and portrait placement. Tests used relative VISUAL_EVIDENCE_ROOT to reproduce the former CI path problem while passing absolute local assets to the API.

- Ordered beats must cover all retained groups once, preserve source order and align to complete reviewed caption groups.
- Missing roles/images, unknown versions, blank notes, omitted/duplicated words and image/protected-region overlap were rejected.
- Direct modification of compiled operations could not retain a template claim; saving recompiled and compared operations.
- Definition hashes were frozen and checked. Changing/tampering with a saved custom definition rejected a new export; existing exports retained their old definitions.
- Review updates made old plans stale. Task entry exposed recipe candidates, schemas and catalog through the existing Agent interface.
- Pure music/montage requirements validated as planning-only and were rejected by executable compilation. Invalid role definitions/unknown emphasis roles were rejected.

Materials are self-generated colour video, sine audio, a two-colour diagram and manually aligned Chinese text. They do not establish real industry aesthetics, ASR quality, listening quality, genuine experiences or publication performance. No independent blind Agent acceptance was performed in this round.

## Failures and revisions

1. [Previous cloud run](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40177772766) failed on all three platforms: preserved test paths were relative, conflicting with the API's absolute-path contract. Tests now resolve their evidence directories.
2. Both Macs also rejected copying protected system-font metadata. Font freezing now copies content without system metadata; the frozen bytes are still hashed. The original failure logs remain in local evidence.
3. First portrait case scaled geometry while preserving a non-square sample aspect ratio. The visual-plan saver correctly rejected it. The fixture now explicitly uses square pixels; the compiler also checks orientation/aspect before returning an executable draft.

New cloud results are reported separately. Local Windows success does not establish macOS execution. Existing historical ASR acceptance is not inherited as recipe/render acceptance.

Follow-up [cloud run 40178986267](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40178986267) passed on both macOS 15 Apple Silicon and Intel, including the 59-test suite and native speech/export steps. Windows failed because its newer FFmpeg removed filter_complex_script; actual failed jobs/process logs were retained. Switched to documented `-/filter_complex` file loading, preserving graph files and avoiding Windows argument-length limits. This correction requires a new cloud result before Windows cloud acceptance is claimed.

## Artifacts and reproduction

Run `python -B -X utf8 -m unittest discover -s tests -v`. Set VISUAL_EVIDENCE_ROOT to retain isolated projects, template attempts, drafts, snapshots, input assets/fonts, failed/revised outputs and FFmpeg logs. The repository does not bundle system fonts or raw private project data. Local evidence includes initial/final logs, source/output hashes and representative frames. See [recipe usage](../docs/industry-templates.md) and [generation guidance](../skills/self-media-workflow/references/recipe-generation.md).

## Final cloud verification

[Run 40179335454](https://github.com/MkaliezZ/self-media-workbench/actions/runs/40179335454), runtime commit 65f21be, completed successfully on Windows, macOS 15 Apple Silicon and macOS 15 Intel. Each platform passed all **59 tests**, including actual recipe/visual FFmpeg rendering and the fixed file-loading syntax, then completed its native speech/ASR/export smoke checks. The Apple job also completed its MLX capability/inference/fallback probe; actual device behaviour remains in its result logs, not inferred from the job name. Earlier failures remain in the previous runs and local records.

The local real-HTTP check also exported a narrated-travel recipe to terminal done, restarted its owned idle service and resumed the same project with its template preserved. All test services were stopped. These are technical checks on explicitly synthetic material. They do not constitute independent Agent blind testing, real travel footage review, audio aesthetics or industry performance acceptance.
