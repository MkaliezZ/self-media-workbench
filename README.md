# Self Media Workbench · 自媒体 Agent 工作台

An MIT-licensed local workbench for AI Agents on Windows and macOS. Your Agent chooses the relevant feature, resumes the right project, creates content, reviews edits and delivers versioned results. No browser form, Node runtime or model API key is required.

**对 Agent 直接说任务即可：**“诊断这个账号并选题”“只改这份口播稿”“剪这个视频并检查字幕”“继续上次项目做复盘”。统一入口会准备项目、材料、状态和起点；调用它的 AI Agent 继续完成推理和执行。入口返回计划本身不冒充完成了内容创作。

## Install

Python 3.11+ and FFmpeg/ffprobe are required for the complete media workflow. Text workflows do not need FFmpeg or an ASR model.

```sh
git clone https://github.com/MkaliezZ/self-media-workbench.git
cd self-media-workbench
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
choco install ffmpeg
```

macOS Terminal (use `python3` to create the venv if `python` is unavailable):

```sh
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
brew install ffmpeg
```

For runtime only, install requirements.txt; add requirements-asr.txt for transcription. requirements-dev.txt includes both plus test dependencies. Installation does not download an ASR model. Configure an existing local CTranslate2 faster-whisper model:

```sh
python workbench.py configure --model /absolute/path/to/faster-whisper-model
python workbench.py doctor
python workbench.py install-skill
```

`install-skill` installs the `media-workbench` entry into your local Codex skills directory and records this checkout and its Python interpreter privately. The wrapper prefers the checkout's `.venv`, then the recorded interpreter, so an Agent's unrelated Python does not need the same dependencies. Other Agents can simply read [AGENTS.md](AGENTS.md). Keep this checkout available after installing the skill. No machine-specific location record is committed.

## One Agent entry, multiple tasks

The Agent calls these itself; the human does not have to remember commands:

```sh
python workbench.py run "只写这份素材的口播稿，不剪辑" --input /absolute/path/source.txt
python workbench.py run "继续这个项目做选题"
python workbench.py run "复盘我的项目" --project "project name" --input /absolute/path/metrics.json
```

The entry automatically starts/reuses an identified loopback service, registers inputs and returns the project, context, current/stale artifacts and recommended phase. It does **not** silently call an external LLM. The calling Agent reads the task-specific method, creates artifacts and executes the discovered tools. This works with Codex, DSH or another tool-capable Agent.

| Function | Output |
|---|---|
| Diagnosis / optional benchmark | Evidence, priority issue, next action |
| Topic selection | Material-backed alternatives and chosen problem |
| Script | Spoken text, shots, timing estimates and action |
| Local editing | Actual ASR, explicit cuts/restoration, reviewed SRT grouping, MP4/SRT/JSON |
| Publication preparation | Title/caption/disclosure and real asset bindings |
| Review | Defined metrics or collection plan, hypothesis and next experiment |

A focused task can enter script/edit/review directly. Complete workflows resume the earliest missing or stale phase. Same-session “continue” resumes the current project; ambiguous project matches require selection rather than guessing. `--session` separates independent concurrent chats. Unknown source facts and missing metrics stay unknown. Old drafts, rejected requests and revisions are retained.

State defaults to the operating system's private application-data directory. `configure --data-dir ...` can reuse an existing project store without moving or deleting it. `--skill-root` and `--library` optionally use private method/knowledge directories. Restart a running service after changing configuration. [Configuration and protocol](docs/configuration.md).

## Platform and validation scope

Windows supports CPU and NVIDIA CUDA when its optional runtime is available, with explicit CPU fallback. macOS Intel/Apple Silicon uses CTranslate2 **CPU**, not a claimed Metal/CUDA backend. FFmpeg export and state/protocol features use the same Python implementation on both systems.

CI targets Windows, macOS ARM64 and macOS Intel. It runs protocol/routing tests, real FFmpeg cut/restore/decode tests and an opt-in tiny-model ASR smoke using native synthetic speech. Actual run results, not this matrix declaration, establish compatibility. [Validation records](docs/validation.md).

MP4 and SRT are separate outputs. There is no automatic external publishing, burned-caption/compositing feature or guarantee of content/marketing effectiveness. Actual model recognition, subtitles, meaningful pauses, production readiness and platform requirements still need review by the Agent and, where required, people.

## License and private materials

MIT applies to this repository's own code and documentation. The previous private prototype used an AGPL renderer; this public version replaces that path with its own Python/FFmpeg implementation and includes none of that vendor code. Dependencies and separately installed FFmpeg/model binaries retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).

No Feishu course bodies, private reading ledger, user media, model weights, CUDA DLLs, credentials or machine-specific config are included. The optional private-library adapter does not publish its input corpus.
