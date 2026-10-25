# Portable independent deep-sea matte case

This capsule carries the original sealed inputs and task for the 20-second/600-frame Windows blind case, plus a self-contained runner and pixel/audio verifiers. It uses the repository's documented CLI/HTTP API. It does not import a showcase, product test, prior checkout or historical test helper. No exported movie, frozen font binary, model or paid asset is included. All source illustration/video/audio is original synthetic material, not real observation.

The calling Agent runs:

```text
python portable/run_case.py --repo <current-checkout> --out <new-output-directory>
```

When this capsule lives inside a checkout, `--repo` may be omitted; the runner searches its parents for `workbench.py` and `AGENTS.md`. The output directory must not exist. The Agent manages setup, dependencies and automatic loopback service startup; people do not supply JSON, IDs or startup commands. `--no-install` requires prerequisites already present. `--also-v1` also runs the retained initial measurement algorithm for comparison, without substituting its result for V2.

Requirements: native Python3.11+, FFmpeg/ffprobe, and the current checkout's runtime dependencies. Missing Python packages are installed from that checkout's requirements; missing FFmpeg can use an already available Homebrew/Chocolatey. No global PATH is edited. Run separately on actual Windows, Apple Silicon and Intel macOS; `summary.json` records the real host and commit. A previous Windows score is never assigned to a Mac run. Retain the output evidence even on failure. Public artifact uploads should apply the pipeline's frozen-font-binary exclusions after verification, retaining font hashes and diagnostics; do not redistribute copied system TTF/TTC/OTF files.

The runner imports the sealed inputs, exports full/ordering-control/restored versions, checks 11 illegal cases without changing head/revision, and invokes V2 against actual decoded output. The numerical source-clock, alpha/luma/inversion, ROI, feather-profile, layer-order, music and restored-content criteria are unchanged. New host fonts apply only to ASCII phase labels. All original Chinese glyphs are already pixels in the sealed inputs, so acceptance needs no Windows font.

## Integrity and provenance

`sealed/original-seal.json` is the original pre-implementation seal, byte-for-byte. Windows path separators in its relative keys are normalized only when locating files. Fourteen of its fifteen entries are included unchanged. The omitted original preparation FFmpeg probe contains a Windows absolute filename; it is not an input or a criterion and remains intact in the original Windows evidence. Its exact hash and omission reason are recorded in `BUNDLE-EXCEPTIONS.json`. The runner freshly probes actual files on each host. No sealed hash was rewritten or replaced.

`sealed/generate_matte_materials.py` is the unchanged creation record. It refers to the Windows system font used when authoring these bitmaps, so regeneration on another host is **not** promised to preserve binary hashes. The runner does not execute this record: it uses the original sealed PNG/MP4/WAV files and verifies their original hashes. No font file is carried.

`source-records/` keeps the exact first/revised Windows checker and first driver source. Those archival scripts have their original relative helper/creation assumptions; they are not runtime dependencies. `portable/verify_v1.py` and `verify_v2.py` preserve their respective numeric logic while replacing only output/material locations and decoder imports with arguments and the self-contained `decode_media.py`. V1's original luma-boundary probe and pooled corner percentile remain visible; V2 follows the sealed stable-ROI median rule. The correction did not change source pixels or the0.04/0.03 thresholds.

The real historical overflow-plan validation remains a separate Windows record. This main-case capsule neither depends on that private project data nor claims a Mac replay of the historical case. Original `REPORT-3109dc2` remains PARTIAL. This capsule also does not claim native hard-mask `feather` parameter testing (its input PNG already has the feather gradient), transparent-video codecs, mixed-alpha luma combinations, automatic matting, arbitrary curves or aesthetic/real-business validation.

`CAPSULE-MANIFEST.json` hashes the capsule's own files. Outputs should remain outside this folder; do not include output state or frozen font files when publishing the source case.
