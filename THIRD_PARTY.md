# License and provenance boundary

Repository-authored implementation and documentation: MIT, copyright MkaliezZ. Existing self-authored protocol, storage and validation modules were carried forward from the local prototype under the copyright holder's MIT release instruction.

The old private prototype integrated an AGPL-3.0 JavaScript video renderer. That vendor tree, its renderer functions, its caption helper and its wrapper are not included or imported in this repository. The public render path is independently written Python, which invokes the separately installed FFmpeg command-line tool and projects fully retained ASR groups through explicit keep intervals. No Node dependency remains. Historical private packages keep their original license/evidence and are not relabeled.

The optional Apple Silicon adapter calls Apple's separately installed MIT-licensed mlx-whisper/MLX packages. No upstream inference implementation or model weights are vendored. Local MLX and CTranslate2 weights keep their own licenses and are not interchangeable. See the [upstream MLX Whisper project](https://github.com/ml-explore/mlx-examples/tree/main/whisper).

The optional Vulkan/Metal subprocess adapter calls separately built MIT-licensed [whisper.cpp](https://github.com/ggml-org/whisper.cpp). The setup helper explicitly fetches pinned upstream source for a local build; no upstream implementation, binary, SDK, GPU driver or GGML model weight is vendored here. The Vulkan SDK, compiler/runtime, display driver and downloaded models keep their own licenses. Native raw outputs are retained as test/runtime evidence, not represented as repository-authored model code.

Runtime dependencies retain their own licenses: FastAPI (MIT), Pydantic (MIT), Uvicorn (BSD-3-Clause), NumPy (BSD-3-Clause), faster-whisper and CTranslate2 (MIT); development HTTPX (BSD-3-Clause). See each installed distribution for authoritative notices and transitive dependencies. Models, ONNX artifacts, optional NVIDIA libraries and FFmpeg binaries are not bundled. Their applicable licenses depend on the actual model/distribution/build. Installing a separate binary does not change that binary's license to MIT.

Public methods are repository-authored workflow instructions. Evaluation uses new synthetic content explicitly labeled as simulation; no synthetic result establishes real marketing performance.

Public demo movies include licensed music embedded in finished audiovisual works. See [demo media notices](docs/demos/README.md); that music is not relicensed as MIT and is not distributed separately.

The legacy, developer-only lighting diagnostic invokes separately installed [Radiance](https://radsite.lbl.gov/radiance/misc/license.txt) executables. No upstream source or binary is redistributed here. Repository-authored scene generation, three-tier rules, SVG output and standalone browser UI are MIT. The UI's original project screens were carried forward from the copyright holder's local prototype; no renderer vendor tree was copied. Pillow retains its HPND license. Tutorial links are method references, not licensed fixtures or a photometric database; the evaluation floor plan is self-authored synthetic material.

Current shooting plans use independent source-linked rules, not Radiance. The CC BY 4.0 educational reference is Web Design Primer, Richard Adams and Ahmed Sagarwala, Ryerson University, 2018, chapter 14; attribution, original and license links are retained in docs/lighting-sources.md and exported reports. No textbook images or long excerpts are copied. ARRI/Godox/Aputure materials remain copyrighted references; MIT OCW NC materials and unreviewed candidate textbooks are not bundled or relabeled as MIT.

Oklahoma State University Extension's Light and Color is a publicly readable copyrighted educational reference for source color and incandescent context. It is linked and credited in the source register; its text/images are not bundled or relabeled as MIT.
