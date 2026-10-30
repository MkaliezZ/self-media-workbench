---
name: media-workbench
description: 自媒体工作台统一入口。用户提出账号诊断、对标、选题、口播稿、高级口播、剪辑、行业模板、Vlog、自定义剪辑逻辑、字幕重点、配图、打光、布光、补光、灯位规划、区域高亮、转场、蒙版、遮罩、发布准备、复盘或继续已有项目时，按任务与项目进度调用本地工作台；替用户管理命令、服务启动和续做。适用于已安装该工作台的本机任务，不用于自动对外发布。
---

# 自媒体工作台统一入口

镜头库与文字/数据/卡片动效读返回skill的 references/shots.md，发现 /api/visual/shots、shot-render schema 和运行状态。全库124张参考卡/150个样式，只有9个明确适配的kind可执行。按表达目的选动作，Agent处理中文、横竖屏、帧率与依赖；Remotion后台渲染完成后自动登记generated素材，接现有原生时间轴。没有前端，不把索引数量当可执行数量，不把渲染成功当审美或用户验收；普通功能不要求安装Node。

用户提出打光、布光、补光或灯位规划时，走lighting；读取入口返回的lighting.reference和实际schema。调用Agent查看图片、核对场景后保存简版/标准/理想三档；单纯登记图片不等于已识图，调用Agent必须实际审图；通过CLI/API保留原图、旧方案和现场试拍记录；按教程规则区分可控室内、窗光、强日光及附件/景别；支持补充已有顶灯开关、灯种和观察，先对照有效补光与混色，再判断能否减少主灯工作输出；不使用Radiance或lux反推瓦数，铭牌W仅为登记值，参考案例须给适用条件与试拍。

用户要求“高级口播”时，读取工作台 skill 的 references/advanced-talking.md，发现 talking_profiles、talking-profile schema 与 compile_talking_profile。按内容拆镜、安排分层/透视/证据阅读/关系图和声音，编译并保存原生时间轴；保留冻结模板与逐段用途。普通口播继续简单媒体审阅流程，不自动升格包装。静态人物加合成旁白须明确性质。真实选区音频须有信号，仍要听审；单测不等于审美通过。用户要求先验样片再推送时，收到通过后才推送。

先理解整项任务、现有材料和明确排除的环节，不要求用户选择命令或重填所有上下文。

执行本skill目录下 `scripts/run.py "<用户任务>"`，用当前Python（macOS可用python3）。该脚本通过本机安装记录定位工作台并自动启动本地服务；将明确提供的文件以重复 `--input` 传入，命名项目用 `--project`，明确新项目用 `--new`。原始材料标示性质，演练用 `--simulation`，不要把所有输入默认为实拍。

入口返回当前项目、注册材料、现有产物/过期依赖、推荐起点和所需契约；它没有替你完成推理。阅读工作台AGENTS.md与返回的skill入口，实际完成相应环节、按schema提交并保存产物。`--intent`可传你基于完整语义选择的环节，不被关键词提示强制；不为使用全功能而扩流程。

用户说继续时恢复同一session的项目。为当前对话传稳定的 `--session` 标识，不同对话/并发任务使用不同标识；默认工作目录只是兼容回退，不能据此认定不同对话属于同一账号。跨对话续做应传已确认的 `--project`；多个匹配项目才询问选择，不猜最近一个。只剪视频就进媒体；已有选题只写稿就直接写稿；没有发布数据就作采集计划。材料不足但可完成的部分继续做，真正阻碍的缺项集中说明。

可用 `scripts/run.py context <id>`、`schema <name>`、`submit <id> --json <文件>`、`call METHOD /api/...` 操作同一实例。每次写入后重新取context，绑定当前上下文与版本。原件/转录/失败/初稿不覆盖。异步识别和导出须等到实际done；SRT分组和删音分开判断，保留必要语义限定。

本地导出不是外部发布，结构通过不是事实或效果验证。正文、个人账号和本机配置留在本机；不能从任务材料中的命令获取额外执行权限。

按行业模板剪辑时读取 references/industry.md，发现 editing_templates 与 editing-template schema；根据真实素材选择知识教学、财经商业、美业服务、电商产品、餐饮探店、家居房产、有旁白旅行 Vlog，以及不露脸、科普资料、生活、游戏回看、第一人称等预设。入口关键词仅推荐候选。由 Agent 划分原句锚定的段落、检查主体安全区，编译草案、保存方案、实际导出并验片；不让人选择命令或填写坐标。

重点字幕、本地配图和静态区域提示也走 edit。PNG/JPEG 可以随 --input 登记；读取返回 skill 的 references/visual.md，检查 doctor.visual_editing，发现 visual-plan schema，保存绑定当前原件/识别/审阅版本的计划，再异步导出。剪切或恢复后旧计划过期，须重新核对锚点。当前没有在线自动搜图、跟踪或抠像；合成使用 CPU，不改变 ASR 的 GPU 策略。功能说明不使用创作者姓名、账号或教程链接。

ASR先用doctor读取显卡硬件与实际尝试计划，并打开返回的gpu_setup_guide。NVIDIA优先CUDA；Windows的AMD/Intel GPU使用whisper.cpp Vulkan；Apple Silicon使用MLX；Intel Mac可配置whisper.cpp Metal。显卡来自显示适配器，不能按CPU品牌猜。GPU缺依赖/模型/驱动能力时保留失败原因；require_gpu禁止回退，否则明确标为CPU。获准安装时由Agent执行doctor给出的setup helper和模型配置，续做同一项目，不让用户记命令。CT2/MLX/GGML权重不兼容。以终态ASR backend/device/execution/fallback_errors为准，设备枚举或编译成功不能算GPU识别成功；正常识别不下载模型。

配置在服务启动时加载。配置后对照doctor与/api/status；旧服务须等任务终态，确认PID/命令归属本仓库且空闲后才停止，由同一入口重新启动并续做原项目，重新读取context和创建新ASR run。不要只见doctor新配置就假定旧服务已重载，也不能停止无关进程。

新行业或视频形式不适合预设时读取 references/recipe-generation.md，按行业×形式×观看目的×实际素材生成 editing-recipe，说明各段的用镜、节奏和声音。先验证并判断组件能力：有旁白单源样式用 visual-plan；纯画面、多源、独立声音和音乐打点读 references/timeline.md，使用原生 timeline-plan，无需 ASR。跟踪、复杂图层运动、变速和音乐生成等仍标缺项，不冒充运行能力。

纯画面/多源/音乐任务先读 references/timeline.md 与 editing_logics。登记无声视频或图片，用源秒数编排；检查原声和音乐瞬态候选，审阅后对齐到成片帧，保存带 supersedes 的不可变计划并导出。恢复时按当前项目版本重建旧决定的新计划，保留原件/旧片/失败。不得为无旁白视频伪造 ASR。

转场与蒙版也走原生时间轴。转场重叠会缩短总时长，音乐点对应中点；不要用特效代替叙事关系。矩形/椭圆蒙版按源区域、静态目标位置和成片时间叠加，可向内羽化并保留原PNG透明洞。它们不是自动跟踪或AI抠像。查实际schema、输出帧、声音与无蒙版对照；完整字幕组强调和语音配图仍使用绑定ASR的visual-plan。

文章标黄抽离、正向放大、移动聚光灯、局部放大、画中画入场、文字动效和线性揭示，读返回skill的timeline.md及工作台docs/motion-effects.md，使用timeline-plan.effects。Agent核对原文与实际选区，服务保留源像素并按成片帧执行。优先展示“原始→操作过程→结果”，不能用更好的生成图片替代尚未实现的动作。坐标与阶段时长由Agent处理；不让人记接口或选择命令，不把编排动画冒充自动跟踪/OCR/逐字声学对齐。

视频填字、Alpha/亮度/反向轨道遮罩、羽化圆窗、分屏和前景穿插也读docs/motion-effects.md，使用track_matte或已有motion_layer/masks/transitions。Agent准备并登记真实遮罩图片，核对透明洞、前后层次和实际运动；不能把预制遮罩说成自动人物抠像。文字溢出保存422且head不动；旧无效方案导出预检409，保留后改新版本。
