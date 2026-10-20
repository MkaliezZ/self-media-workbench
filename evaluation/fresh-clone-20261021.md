# Independent public-clone installation audit — 2026-10-21

An independent Agent, without the parent chat history or prepared task answers, received the public repository URL and a first-use task. It actually cloned GitHub and chose a new synthetic desk-reset script and system-TTS video. It did not use the existing private checkout, installed workbench skills, project store or model weights. No user command, model path or manual operation was requested.

## Environment and source identity

- Windows 10 x64; fresh CPython 3.11.15 venv, `include-system-site-packages=false`, user site disabled.
- Separate application state, Agent home and model/cache directories. Git, Python and FFmpeg/ffprobe were already available on the host: this is a fresh **application environment**, not a virgin OS test.
- Initial clone: `efaa191`. Later fetched `e650e2d`; only README/THIRD_PARTY wording changed. The runtime source was unchanged throughout this audit.
- The Agent discovered README → AGENTS.md → configure/doctor/install-skill/run → bundled methods and live schemas. Intake was not mistaken for finished content.

## Actual results

| Check | Observed result |
|---|---|
| Dependencies | Installed public wheels into the isolated venv; pip exited 0 and pip check reported no broken requirements. |
| Local model | Fresh public Systran/faster-whisper-tiny, revision `d90ca5fe260221311c53c58e660288d3deb8d356`; model.bin 75,538,270 bytes, SHA-256 `dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1`, matching Hub LFS metadata. |
| Configuration and entry | Configure, doctor and install-skill executed in isolated directories. Run automatically started an identified loopback service. |
| First script | Project `552a787761fc4d9f80b94a26abb8569a`, accepted artifact `Ad6d71bcac0b441cd9be0b33322832bfd`; simulation and needs_review retained. |
| Actual ASR | Job `cf93aaeae03346d38b56c3467e56826c` done; faster-whisper/CPU, 63 word groups, no fallback errors. This is CPU evidence, not GPU evidence. |
| Review | Two natural in/and recognition errors corrected against the synthetic source; original run and word bounds retained. Twelve caption groups; no sound deleted. |
| Export | Job `bb8e2e545fda4335ab73a9fc72d423bc` done; export `16b585bcb09f4e2fade03336c00d19b7` contains MP4, SRT, word JSON, edit decision and provenance. |
| Output verification | Full FFmpeg decode exited 0; 26.72-second source duration retained, input hash matched, all 63 IDs/bounds/probabilities preserved. Corrected exported text and SRT matched all 63 synthetic reference tokens. Twelve caption groups; separate subtitle previews inspected at 12.2 and 21 seconds. |
| Installed Agent entry | Actually invoked doctor and context using another host Python 3.13. The wrapper selected this clone's Python 3.11.15 venv and returned the same project/script head; exit 0. |

The exercised first-use chain passed after autonomous environment/network recovery. This is not a first-attempt, uninterrupted-installation result.

## Initial failures and autonomous recovery

These are not rewritten as first-command success:

1. The evaluator initially selected a nonexistent working directory, then created it and retried. Its Python launcher did not resolve an installed uv-managed interpreter; it used the launcher's listed absolute CPython path. An initial relative PowerShell invocation and a mistaken helper path were also corrected. These were evaluator/host issues, not confirmed product defects.
2. Default PyPI, a public mirror and a metadata dry-run stalled. The evaluator retained interrupted attempts, resolved compatible wheels through public PyPI JSON metadata, downloaded them in parts and verified official SHA-256 hashes before offline pip installation. Its temporary network resolver is **audit tooling, not a repository installer**. A compatible public protobuf version was selected for a truncated metadata response without changing product requirements.
3. Model download was slow; the evaluator retained the initial attempt, completed HTTP range downloads and verified the complete model hash. This was an explicitly authorized installation download; normal inference remains local-only.
4. The English script's character-rate check did not fit its planned timing. The failed estimate remains. Same-text system TTS was about 26 seconds while the script planned 35 seconds including pauses; neither establishes human read-aloud timing. The script explicitly retains this limit and unproduced demonstration shots.

The original bootstrap transcript hash was recorded before user-requested wording redaction of unrelated copied documentation. Failed commands and errors were preserved. Current source/report naming was scanned after the documentation update.

## Scope

The tested Agent could perform the task without asking the human to remember commands, but installation required substantial autonomous network troubleshooting. This does not establish an uninterrupted one-command installer. No runtime defect was confirmed in the paths exercised here; no runtime patch is attributed to an environmental workaround.

This round does not newly validate absent Git/Python/FFmpeg installation, a clean macOS installation, GPU acceleration, speech cut/restore, human subtitle/read-aloud quality, publication or marketing effectiveness. Earlier actual Windows/macOS/Metal results remain separately documented in [validation](../docs/validation.md). The unchanged runtime also passed 36 local regression tests before this audit; that is separate from this first-use test.

Full commands, failed attempts, package/model manifests, isolated configuration, source media, original ASR, submitted artifacts, decoded outputs and the independent report are retained in the local audit directory. Private paths and raw environment/download logs are not published here.
