# Configuration and protocol

All configuration is local. `workbench.py configure` writes the operating system's app-data config.json; no global PATH modification or uploaded config is needed. Precedence is process environment, private config, portable defaults.

| Environment | configure option | Meaning |
|---|---|---|
| SELF_MEDIA_STATE_DIR | process-only | Application state/config/services/session root |
| SELF_MEDIA_DATA_DIR | --data-dir | Existing or new project store |
| SELF_MEDIA_MODEL | --model | Local faster-whisper/CTranslate2 model directory containing model.bin |
| SELF_MEDIA_DEVICE | --device | auto, cpu, cuda; macOS auto selects CPU |
| SELF_MEDIA_LANGUAGE | --language | ASR language (default zh; empty enables detection) |
| SELF_MEDIA_CUDA_DLL_DIRS | --cuda-dll-dir (repeatable) | Optional Windows NVIDIA DLL directories; process-local, never a global PATH change |
| SELF_MEDIA_SKILL_ROOT | --skill-root | Optional private skill; default public bundled methods |
| SELF_MEDIA_LIBRARY | --library | Optional private knowledge root; absent is supported |

Task API: POST /api/agent/v1/tasks, schema at /api/agent/v1/schemas/task. The unified CLI uses this same route. Fields include task, optional intent, project, new_project, input_paths, material declarations, simulation, session_key and request_id. Text is snapshotted; supplied audio/video is copied by the media API. Same source contents/nature can be reused. A request_id retries the exact successful intake, not a different task.

Routing is state-aware assistance to the calling Agent, not an LLM hidden inside the server. The Agent interprets the full user request, can set intent, handles project ambiguity and uses the returned context/schemas to actually generate and submit artifacts. The service checks source IDs/exact quotes, dependencies, revisions, timing and metric arithmetic; it does not prove truth/rights or automatically approve publication.

Each project keeps original sources, versions, events, contexts, attempted submissions, tasks, media runs/reviews and immutable export directories. A changed upstream marks dependent outputs stale. A 409 needs a fresh read and actual reconsideration. No implicit overwrite, no auto silence deletion, no external publication.

The runtime auto-picks a free loopback port and records its identity per checkout. For integrations requiring a fixed port, run `python workbench.py serve --port 8765` and pass `--base-url http://127.0.0.1:8765` before CLI subcommands. An occupied unrelated service is never terminated.
