# Fresh macOS clone, installation and first task — 2026-10-21

The repaired first-use chain passed on native Apple Silicon and Intel cloud runners. The independent evaluator authored a new synthetic brief/script and deterministic execution driver from a fresh public GitHub clone, without the parent chat, private skills/models/projects or earlier test answers. The cloud driver is **automated execution of that plan, not a live cloud LLM Agent**. The evaluator then independently examined the downloaded raw calls, media and manifests; the retained reports separate runtime, content and evidence-packaging results.

[Independent final review](verified-fresh-432fb79/independent-acceptance.txt) · [Structured independent reconciliation](verified-fresh-432fb79/independent-acceptance.json).

## Final actual runs

Tested code: `432fb79cd62c5226b486880f342257140f5e97e2`.

| Environment | Actual engine/device | First task and media | Evidence |
|---|---|---|---|
| macOS 15 Apple Silicon arm64 | MLX/GPU; real Metal kernel, isolated worker, no CPU fallback | Script plus saved revision, 73 actual word groups, 12 caption groups, 30.60-second decoded export | [Run 39469031595](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39469031595), [results](verified-fresh-432fb79/macos-arm64/) |
| macOS 15 Intel x86_64 | faster-whisper/CPU; no fallback errors | Same first-use task, 73 groups, 12 captions, 30.08-second decoded export | Same run, [results](verified-fresh-432fb79/macos-intel/) |
| macOS 26 Intel x86_64, alternate capacity | faster-whisper/CPU; no fallback errors | Another fresh machine/environment, 73 groups, 12 captions, 27.92-second decoded export | [Run 39469037629](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39469037629), [results](verified-fresh-432fb79/macos26-intel/) |

Generated speech differs between hosted machines; these durations are not a CPU/GPU speed comparison. Automated assertion counts include individual word/cue checks, not independent test cases: 162 ARM and 160 on each Intel runner.

## What actually ran

Each runner performed a real public `git clone`, detached the exact tested commit and created a new `.venv` without inherited site packages. Before installation, doctor recorded absent Python runtime dependencies/models. Host Git/Python and Homebrew were available; FFmpeg/ffprobe were checked and installed when missing. This is a fresh application environment, not a bare operating system or a test of installing Git/Python itself. Shared pip cache was disabled.

Separate application state, Agent home and Hugging Face directories began empty. Model paths, backend/device and language were saved through the actual `configure` command and read back from config.json; no model/config environment override bypass was used. Pinned public tiny models were downloaded during the explicitly authorized installation stage, with actual weight SHA-256 checked against upstream LFS metadata and small files against Git blob identities:

- CTranslate2: `Systran/faster-whisper-tiny@d90ca5fe260221311c53c58e660288d3deb8d356`.
- ARM MLX: `mlx-community/whisper-tiny-mlx@6caf9c55601caafbe6508a8b0d216bdf4783c4e8`.

The manifest records requested/resolved revisions, expected/actual hashes and verification results. Models were not uploaded in the evidence package. Runtime inference was forced offline.

A different Python, in a separate environment with no product dependencies, invoked the installed Agent entry from the material directory. It selected the product venv, automatically started an identified loopback service, created the synthetic project, discovered live schemas and submitted an actual script plus a superseding revision. A later entry invocation resumed the same project, script head, export and service without creating another project or asking a human for commands/paths.

Native macOS speech generated new audio and a color-background video. The driver actually waited for ASR and export jobs to reach done. ARM required real MLX/GPU/kernel execution and would fail on CPU fallback. The review removed only the deliberately inserted non-speech pause and retained all 73 word groups, source bounds and original probabilities. Output timing matched the explicit keep intervals; every subtitle mapped to retained IDs and output bounds. All MP4s were completely decoded. Native service cleanup waited for verified process exit before snapshots.

The final driver manifests (340/348/340 entries) and complete artifact envelopes (345/353/345 entries) were rehashed after download with zero mismatches. All final caption groups last at least 1.28/1.30/1.20 seconds respectively; the full negative safety qualification remains together. This minimum is an acceptance choice for this fixture, not a universal platform rule.

## Original failures and repairs retained

The first ARM job on `c1197ee` really used MLX/GPU and passed its original functional assertions. Post-run review did **not** accept it as a clean overall pass:

1. The bundled media method still described all macOS ASR as CPU. It was corrected to distinguish native Apple Silicon MLX from Intel CPU before the first cloud run.
2. Two logs changed after manifest generation: the outer workflow tee and service shutdown log. The primary reviewer discovered the mismatches and the independent evaluator reproduced them. The repaired driver waits for shutdown; the workflow seals/verifies the full envelope after the tee closes. The new verifier returns failure against the first artifact. [Original runtime result and failed integrity check](fresh-macos-c1197ee/arm64/) remain intact.
3. Independent review found two isolated word captions lasting 0.40/0.44 seconds. The fixture review plan was revised using clause context, with every source ID retained; short-tail assertions and actual previews were added to the review process. The original SRT and review remain in the local first-run archive.

First run [39467127371](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39467127371) was later cancelled only to supersede its still-unassigned Intel job; its completed ARM job/artifact are retained. Initial alternate run 39467735061 had no assigned runners and was also superseded. Those cancellations are capacity/history records, not inference failures. The repairs changed method/audit/fixture-review code, not the ASR or rendering engine.

## Practical limits

English character-budget fit remained false and was retained; it does not measure English pronunciation or human delivery. The 40-second script remains a planned timeline and needs_review; generated speech is measured separately. This test does not establish human read-aloud/listening, real camera footage, target-player subtitle appearance, general ASR accuracy, production model performance, real account results or publication readiness. No external publishing occurred. Fresh Windows installation and earlier broader OS/GPU runs have separate reports; this round does not replace those boundaries.

Original source media, transcripts, script versions, calls/errors, configurations, subprocess exit codes, decoder evidence, first-run failures, independent review reports and final packages are retained under the local dated macOS audit directory. Public JSON removes machine-local model paths; full raw artifacts retain their original identities locally.
