# 显卡分流与实际执行验收 — 2026-10-21

前一轮中文验收的 Windows 云端任务**显式选择 CPU**，且托管机显示适配器为 Microsoft Hyper-V Video；该任务验证 CPU 保底链路，没有验证 NVIDIA GPU。本机已有的 CUDA 路径仍然可用。本次另外修复了非 Mac 自动选择“先试 CUDA、失败转 CPU”而未区分显卡厂商的实现缺口。

## 已实现策略

| 显示适配器 / 平台 | 自动策略 | 当前硬件验收 |
|---|---|---|
| Windows NVIDIA | CTranslate2 CUDA，查询真实支持的精度；可选已配置 Vulkan 次级，再转有记录的 CPU | 本机 RTX 5060 实际 CUDA 通过 |
| Windows AMD Radeon | whisper.cpp Vulkan，不试 CUDA | 卡型路由/失败契约通过；没有 AMD 实机结果 |
| Windows Intel Arc / 支持 Vulkan 的核显 | whisper.cpp Vulkan，不按 CPU 品牌判断 | 卡型路由/失败契约通过；没有 Intel GPU 实机结果 |
| Apple Silicon | 保留 MLX / Metal GPU | 云端真实 Metal kernel/ASR/导出再次通过 |
| Intel Mac 有受支持 GPU | 可配置 whisper.cpp Metal，否则保留失败原因转 CPU | Intel CPU 保底通过；新 Metal 适配器没有 Intel Mac GPU 实机结果 |

AMD/Intel 共用跨厂商 Vulkan API，分别按显示 GPU 厂商分流。未实现 Intel OpenVINO 专用适配器，也不声称给所有 AMD 卡自动安装 ROCm。详见 [Agent 策略/安装指引](../docs/accelerators.md)。显卡枚举、编译成功和 CPU 回退都不是实际 GPU 识别成功。正常识别不下载模型；显式 CPU 仍优先，`require_gpu` 禁止 CPU 回退。

## 实际执行与可追溯证据

主要运行时代码 `49a63f368d49d339b0969de8b9d0f085782fcdc6`；后续只增加构建包 MIT 通知保留和文档/证据。硬件测试记录实际后端，而不是依据设备名称标成功。

- [本机 NVIDIA 最终结果](gpu-strategies-20261021/nvidia-final/result.json)：自动选择 faster-whisper/CUDA，medium CT2 模型，`int8_float16` 来自该卡返回的支持列表；独立 CUDA 子进程实际完成识别，`fallback_errors=[]`，保留 126 个原始组，50.2 秒源视频完整导出并解码。另由已安装的统一入口/正常服务执行异步 ASR，仍为实际 CUDA、126 组，没有改用户模型/配置或原有项目；测试使用独立 session 和明确标为 generated/simulation 的新项目。
- [Vulkan 构建 39478343827](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39478343827) 在 `2f8e7bd` 上，使用 LunarG 1.4.363.0 SDK（原下载哈希和有效签名保留）与固定 whisper.cpp v1.9.5 / `d1be6fde11ac6e0407606b4e42fe72d34add8037` 编译成功，并完成真实 CLI CPU 识别/JSON/导出解码契约。构建成功没有被标成 GPU 验收。
- 将同一个编译文件（SHA256 `daa6c9152a163d2334fef85e83278aa74d6971af8d14d02037d4a481ab4eec07`）用于本机 [实际 Vulkan 测试](gpu-strategies-20261021/vulkan-nvidia/result.json)。原日志确认 RTX 5060、`using Vulkan0 backend`、77.11 MB GPU 模型分配、实际识别进程完成，无 CPU 回退，导出全片解码成功。这验证适配器真正调用 Vulkan GPU，**不能替代 AMD/Intel GPU 实机验收**。
- Vulkan tiny GGML 模型实际输出 19 个较粗的原生分段，有可见中文识别错误，未伪造字级时间戳/概率，也未套用上一轮 small 模型的中文字错率结论。原始文本完整保留。该次原生日志总耗时约 61 秒，未宣称 GPU 一定提速，也未把不同模型/机器间耗时做加速比。
- 在该 Vulkan 原始分段上另行完成 [剪除/恢复](gpu-strategies-20261021/vulkan-cut-restore/result.json)：仅删除 A 内 11.23–13.01 秒的 1.78 秒零样本静音，B 全保留；原分段 ID/源界/概率不变，实际视频再次解码；恢复覆盖 50.2 秒，恢复版与原全长导出的解码音频相同，原 ASR 和旧输出的清单哈希不变。它验证媒体映射，未冒充字幕语义精读或中文准确率验收。
- [最终三端回归 39478474440](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39478474440) 在 `49a63f3` 上，Windows、macOS ARM、macOS Intel 各 46 项测试通过，并执行真实 CPU ASR/HTTP 导出/解码；ARM 另执行实际 MLX/GPU（Metal kernel、独立 worker、无回退）。[原结果](gpu-strategies-20261021/compatibility-final/)。契约模拟涵盖 AMD/Intel/混合卡选择、显式 CPU、GPU 必需、缺驱动回退、CUDA 原生异常隔离和精度选择；模拟不等于 A/I 卡真实执行。

## 保留的失败和修订

1. `2e8f030` 的本地 44 项测试通过，但 [初次三端回归 39477741178](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39477741178) 在 ARM 上有两项测试失败：Windows 假硬件未隔离真实 Apple Silicon 判断，误入 MLX。`8d9415a` 补齐平台模拟并隔离 CUDA 原生崩溃；三端重测通过。`49a63f3` 增加实际 CUDA 支持精度选择，最终各 46 项通过。没有把此测试错误伪称为 MLX 推理缺陷。
2. [首次 Vulkan 构建 39477735784](https://github.com/MkaliezZ/self-media-workbench/actions/runs/39477735784) 失败于 MSBuild shader 子项目长路径 `FTK1011`。原构建日志保留；`2f8e7bd` 使用同盘短路径、所有权标记并从实际构建目录收集失败日志，再构建通过。没有改全局 PATH、注册表长路径或映射盘符。
3. 本地 Vulkan 剪辑辅助检查曾把实际 `keeps` 结构与漏掉 `outputOffset` 的手写字典作全等，误报失败；输出已正确生成。保留该检查失败，改为检查真实字段和覆盖后通过，未改原导出/产品数据来迁就断言。
4. 原生可执行文件为另行构建依赖，未放入本仓库。构建 helper/打包指引现同时保留固定上游的 MIT 通知；本地使用副本同样保留通知。源权重、SDK、GPU 驱动也未入库。

完整本地原包、二进制、未改日志及视频位于 `F:\Codex Workspace\Studio\gpu-strategy-audit-20261021`。公开目录为明确选取的字节保留证据子集，拥有独立清单；其中原运行清单对应完整本地包，不能对缺文件的公开子集直接运行完整包验证。没有真人/方言/长录音质量或全型号兼容性结论。
