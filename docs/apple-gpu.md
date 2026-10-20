# Apple Silicon GPU ASR

The Agent uses the same entry, media routes and review/export contracts. On native Apple Silicon macOS, backend=auto/device=auto tries the optional MLX engine and Metal GPU. Explicit CPU skips it; Intel Mac stays on CPU. The MLX worker runs in an isolated subprocess, so native load/kernel failures can be recorded and followed by CPU fallback rather than crashing project storage.

Install requirements-mlx.txt in the workbench's Python and configure --mlx-model with an existing local MLX model directory. It must contain config.json and model.safetensors, weights.safetensors or weights.npz. Configure --model separately with a CTranslate2 model.bin directory for CPU fallback. No normal inference path fetches Hub models; the worker runs with Hub offline mode. An explicitly authorized CI smoke can download tiny test weights. No user model/media is uploaded.

MLX supplies actual word bounds/probabilities; the adapter assigns per-run IDs and uses the existing shared 16 kHz/VAD source timeline. It does not fabricate character alignment. ASR runs/originals, word corrections, cuts, restores, grouped SRT, source/output bounds and export provenance remain separate and immutable. Different engines may recognize or align differently; reusing old-engine word IDs in a new run is invalid.

Successful GPU output records backend=mlx, device=gpu and execution.gpu_kernel_verified=true after a real Metal kernel and transcription. Dependency installation or a Metal capability probe alone is not ASR validation. CPU fallback records the actual faster-whisper/cpu result and the failed MLX reason; if neither engine has a valid local model, the job fails honestly.

`scripts/ci_smoke.py --download-ci-model --download-ci-mlx-model --backend auto --out evaluation/runs/mlx-smoke.json` explicitly tests actual capability, ASR and HTTP export on a native ARM runner. Its JSON records gpu_asr_verified separately. With --require-gpu the smoke fails unless GPU ASR actually happened. A hosted VM without exposed Metal can validate CPU fallback, but cannot establish GPU performance; use a real Mac and existing local models with --model/--mlx-model --backend mlx --require-gpu for that acceptance. See [actual evidence](validation.md).

Upstream references: [MLX Whisper API, local models and word timestamps](https://github.com/ml-explore/mlx-examples/tree/main/whisper), [MLX devices](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html).
