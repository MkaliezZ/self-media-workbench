# Selected original evidence

These files are byte-preserving copies of selected actual local/cloud test records. See the [audit report](../gpu-strategies-20261021.md) for verdicts, original failures and hardware limits.

- `nvidia-final`: actual auto/CUDA, fixed snapshot `49a63f3`, original 126 ASR groups, decoded full export.
- `installed-entry-api`: separate real asynchronous CUDA job through the installed/default service; only the generated test project's result/review is selected, not its broader context/config.
- `build-initial`: genuine MSBuild long-path failure; `build-repaired`: pinned upstream build and actual CPU CLI/export contract. Native binaries/weights are retained locally, not committed here.
- `vulkan-nvidia`: actual RTX 5060 Vulkan use, native logs/JSON and original 19 coarse segment groups. This is not AMD/Intel hardware evidence or a Chinese quality pass.
- `vulkan-cut-restore`: actual cut/restore media decisions and the evaluator's initial schema-assertion failure, retained alongside the corrected verification.
- `compatibility-final`: actual three-platform run `39478474440`; `history`: initial failed ARM mock test, final Windows 46-test log, failed build log and verified GGML download metadata.

`public-subset-manifest.json` hashes the files actually present here, excluding itself. Inner smoke manifests describe the complete local package and therefore reference files intentionally absent from this public subset. Complete untouched packages/videos/failed attempts remain under the local `gpu-strategy-audit-20261021` directory. File names may reflect the original machine, but runtime source/config/assets are not hardcoded to those paths.

Native compiler/driver logs contain original CRLF and trailing spaces. This evidence directory disables Git text normalization/whitespace lint so those bytes remain verifiable; do not trim the captured logs to satisfy source-code formatting checks.
