# GPU strategy for the calling Agent

Run `doctor` from the installed entry. Read `gpu_hardware`, `asr_attempt_plan`, model/dependency status and `gpu_setup_guide`. Display inventory is **not** execution proof. Use actual terminal ASR `backend`, `device`, `execution`, `routing` and `fallback_errors`. A CPU result is CPU even when the machine has a GPU.

| Native platform / display GPU | Preferred ASR strategy | Required local assets | Failure policy |
|---|---|---|---|
| Windows NVIDIA, including hybrid NVIDIA + Intel | faster-whisper / CTranslate2 CUDA | CT2 model, matching CUDA/cuBLAS/cuDNN | Optional configured Vulkan secondary, then recorded CPU fallback |
| Windows AMD Radeon | whisper.cpp Vulkan | Vulkan-capable display driver, Vulkan build, GGML model | Retained native logs, then recorded CT2 CPU fallback |
| Windows Intel Arc or supported integrated graphics | whisper.cpp Vulkan | Same Vulkan requirements; detect the **GPU**, not the Intel CPU brand | Same recorded fallback; old/unsupported drivers do not establish GPU support |
| macOS Apple Silicon | MLX / Metal GPU | MLX dependency and distinct local MLX weights | Recorded CT2 CPU fallback |
| macOS Intel, with supported AMD/Intel GPU | Optional whisper.cpp Metal | Metal-capable hardware/runtime, Metal build and GGML model | Recorded CT2 CPU fallback; support depends on the actual Mac, not CPU architecture alone |
| No detected usable GPU | CT2 CPU | CT2 model | CPU is labelled explicitly; never attempt CUDA just because the OS is Windows |

Vulkan is intentionally shared across AMD and Intel. These are separate vendor routes into a cross-vendor GPU API. ROCm has device/OS compatibility constraints and is not installed automatically for every AMD card. An OpenVINO-specific Intel adapter is not implemented; do not claim it exists. NVIDIA retains its established CUDA path rather than being redirected to Vulkan by default. CPU VAD, FFmpeg decoding/encoding and ASR acceleration are distinct; GPU ASR does not imply GPU video export.

## Agent provisioning and resume

Normal transcription never downloads code/models. When installation/GPU setup is authorized, the Agent handles provisioning; the human need not remember commands or paths. Keep existing config/projects, inspect the missing component and use process-local dependencies. `doctor` points to the setup helper and this guide; return to the same project after setup and create a new ASR run.

- NVIDIA: install the ASR requirements in the workbench interpreter, inspect actual CTranslate2 CUDA capability and provision compatible NVIDIA libraries when missing. `--cuda-dll-dir` registers trusted directories for this process; do not edit global PATH. CUDA runtime, cuBLAS and cuDNN must match the installed CTranslate2 version; a driver name alone is insufficient.
- AMD/Intel on Windows: use `scripts/setup_cpp.py --acceleration vulkan --download-model small --configure` from the workbench interpreter after Git/CMake/MSVC and Vulkan SDK are available. The helper uses pinned upstream source `v1.9.5` / `d1be6fde11ac6e0407606b4e42fe72d34add8037`, compiles the CLI, explicitly downloads and LFS-verifies the chosen GGML model, then saves paths without changing other config fields. It can resume its own build directory but refuses a mismatched source checkout. `--model` reuses an existing verified GGML file instead.
- Vulkan SDK is a **build** dependency, not a model or GPU driver. The Agent may use LunarG's supported copy-only installer (`copy_only=1`) in a managed directory and pass `--vulkan-sdk`; it need not change system PATH/registry. Do not replace the user's display driver automatically. The repository's `vulkan-build.yml` gives an actual isolated build recipe, including SDK signature and download hash records.
- Windows MSBuild shader subprojects can exceed MAX_PATH. For a long requested workspace the helper chooses a short, hashed `.smw-build` directory on the same drive and writes an ownership marker; `workspace` in the result is authoritative. This is a local build cache, without drive mapping/global long-path edits. If that drive root is not writable, the Agent must choose a short writable `--workspace` and retain the failed attempt. It never resets a mismatched checkout or deletes old build evidence.
- Intel Mac: the same helper with `--acceleration metal` uses Xcode command line tools and embeds the Metal library. Apple Silicon should keep its existing MLX strategy; these model formats are not interchangeable.

Configuration accepts `asr_backend=whisper.cpp`, `cpp_executable`, `cpp_model`, `cpp_gpu_index`, and `device=vulkan|metal`, as well as auto/CPU/CUDA/MLX. Mixed-device Vulkan indices are the native CLI's namespace, not WMI adapter order or CUDA indices. The default is native index 0; select another only from the native device logs. `configure --require-gpu` forbids CPU fallback; `--no-require-gpu` allows it again. An explicit CPU choice remains CPU.

## Proof and timing boundaries

The subprocess adapter retains unmodified native JSON, stdout, stderr, command, binary/model SHA256 and failed attempts under that ASR run's `engine/` directory. A Vulkan/Metal success requires process completion plus native GPU backend selection and positive GPU model-buffer allocation. A compiled `VULKAN=1` string or a discovered device is insufficient. These logs plus completed inference establish use of the GPU backend, not a GPU speed-up ratio or a separate per-kernel profiler trace.

Native token bounds/probabilities are preserved when the engine provides complete ordered valid coverage. Missing/zero/invalid token alignment falls back to the **actual segment** bounds with `alignment=model_segment_group` and null probability, never invented character/word timings. Such groups are coarse: the Agent cannot split their audio at arbitrary characters. Check the actual review/group boundaries before cutting; change engines if finer alignment is required. There is no reference-text substitution in this adapter.

`scripts/gpu_strategy_smoke.py --require-gpu` exercises an actual configured GPU and decoded export. Contract mocks verify selection/failure behavior only. The standard GitHub Windows runner is CPU acceptance; real NVIDIA, AMD and Intel GPU results must remain separately labelled. See [current validation](validation.md).

Upstream primary references: [CTranslate2 hardware](https://opennmt.net/CTranslate2/hardware_support.html), [whisper.cpp Vulkan/Metal/build](https://github.com/ggml-org/whisper.cpp), [CLI full JSON/timestamps](https://github.com/ggml-org/whisper.cpp/tree/master/examples/cli), [LunarG copy-only installer](https://vulkan.lunarg.com/doc/view/latest/windows/getting_started.html).
