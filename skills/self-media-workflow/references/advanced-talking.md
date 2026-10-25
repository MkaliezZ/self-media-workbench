# 高级口播 / Advanced talking head

用户明确选高级口播、解释型多层包装或要求提升剪辑表现时读取。普通口播仍先走媒体审阅、删音、字幕与必要的配图；不为“高级”把每句话铺满动效。输入可以是真人视频、已声明的数字人，或用户接受的静态人物图加合成旁白。静态图不冒充口型动画。

## 入口与交付

通过统一任务入口读取实际项目状态；发现 `GET /api/visual/talking-profiles`、`schema talking-profile`。普通预设为 `ordinary_talking_head`，高级预设为 `advanced_talking_head`，中文名称为“高级口播”。任务中的关键词是保守推荐，调用 Agent 仍判断否定、范围与已有冻结模板。

Agent 做语义判断和画面设计，服务做绑定、预检和执行。高级模式按实际内容切成可循环的 `hook / anchor / metaphor / evidence / diagram / comparison / bridge / takeaway` 场景。它们是画面任务，不要求每条片子机械填齐所有类型，也不要求先写八个等长段落。

每段记录：原片/图片来源、源区间、对应口播、观众应理解什么、实际素材说明、是证据/示意/观点，以及实际图层动作。证据画面必须绑定在本段真正展示的来源上；画出一张图不等于证实论断。

`POST /api/projects/{pid}/talking-profile/compile` 把场景相对时间转换为量化后的全片帧时间；可顺次重复场景类型。`effects` 的时间相对各场景，`audio / titles / masks` 使用全片时间。编译不会保存新 head。检查返回的 `timeline_plan`，通过原生 `timeline-plans` 原样保存，再异步导出到实际 `done`。模板定义、哈希、逐段口播/用途和时钟保存在 `production_profile`；编译尝试与拒绝保留在项目的 `talking-attempts`。

每次变更取新 context。换时长、顺序、转场或音乐网格会使场景时钟失效，应重新编译，不能直接挪旧标签。恢复旧版时保留旧决定、取当前项目版本与 head、使用新 request_id 和 supersedes 保存为新版本。编译器 v1 面向不超过300秒的片段；更长节目分段执行并保留组件来源。此编译器不使用重叠转场或音乐网格，底层时间轴另有这两种功能。

## 从表达需要选技术

| 观众此刻需要 | 组合方法 | 实际边界 |
|---|---|---|
| 知道先看哪里 | 关键词保持相近位置的匹配剪辑；原文局部标黄或黑白反相扫描 | Agent核对真实字框；不提供OCR定位 |
| 理解层次 | 背景、大字、物件、前景分层；不同位移幅度制造视差；Alpha前景遮住后层 | 二维平面合成；不是三维建模、自动人物抠像 |
| 看清一段证据 | 原文定位→重点扫描→抽离→拉正→可读停留→返回 | `document_extract` 保留原像素；引用意思仍由Agent核实 |
| 看懂关系 | 节点分批入场、关系线揭示、镜头从整体到局部再回整体 | 图层/文字/线图资产分开登记；真实路径描边、复杂父子相机不在此版本 |
| 分辨两种情况 | 同一画面规则下的对照卡；次要项后退/失焦，当前项前移 | 不生成虚假的比较数据或因果结论 |
| 换一段思路 | 纸页交错、年份/章节大字、快速切换再稳定阅读 | 字体、图形、声音是独立层；不把预渲染物件当现场3D生成 |
| 回到讲述 | 清楚的人物主画面、少量辅助标签、留出安静段落 | 静态人物需明确性质；不靠全片纹理掩盖表达问题 |

## 多阶段平面透视与质感

`timeline-plan.effects` 新增 `keyframe_layer`，用于**已登记的静态图片**。动画素材/视频仍用 `motion_layer` 或 `track_matte`。

- `keys` 2–32个，`at` 是相对 cue 起点的秒数；从0严格递增到完整时长。每个 key 有 `quad / opacity / blur`。四角按正向 TL/TR/BR/BL；允许有意出画，拒绝镜像、倒置、退化及插值中途折叠。
- `easing` 可选 linear、smoothstep、ease_out_cubic。能编排进入、停留、移焦、再次移动和返回；不宣称任意三维翻转、速度曲线或自动跟踪。
- `crop` 是源图坐标；图层顺序即遮挡顺序，保留PNG原始透明洞。`shadow` 是二维投影。
- `focus_rect + edge_blur` 保持指定区域清楚并虚化边缘；这是带清晰蒙版的高斯失焦，**不等于物理景深或径向运动模糊**。
- `grayscale / vignette / chroma_pixels / grain / halftone` 是受限的图层处理。网点是纹理叠加，不是完整印刷网屏模拟。RGB位移不在边缘循环回卷，纹理随机数可复现。处理本图层，不会自动给底层视频套全局调色。
- `highlights` 使用实际源图区域，`highlight_mode=multiply` 保留原字形并乘黄色，`invert` 用原像素黑白反相。`highlight_delay / highlight_seconds` 控制逐行扫描；扫完保持到 cue 末尾。所有选区必须在 crop 内。

先对比原始、进入、中间、阅读和返回帧。检查字形/Alpha洞、遮挡次序、引用内容和安全区；不能用一张更漂亮的生成图代替实际动作。

## 声音与验收

口播需有真实源音轨或覆盖本段的独立 voice bed。编译、保存和导出会解码实际选用区间，拒绝全零或近乎无信号的路径；音轨存在不能算人声存在。能量通过也不证明是语音、内容正确或听感自然，仍需听审。

TTS、数字人、音乐生成是可选外部素材生产，当前服务不内置。Agent在获得相应授权后准备素材、登记来源，再用原生独立音轨混音。BGM按人声区间压低，音效只服务于入场、揭示和落点，不能压住说话。正常语速放不下时删改文案、保留旧稿，不靠强行加速。字幕若由生成器时间或作者编排得到，明确其来源，不冒充ASR或音素精确对齐。

交付至少包含实际影片、原始素材与性质、冻结方案、声音与阅读检查、真实失败和修订记录。单测/解码成功不等于审美通过；用户要求先验样片再发布时，保留待验收状态，收到通过后才推送。

若交付音量不一致，Agent可对实际原生H.264导出调用 `scripts/master_audio.py --input <原片> --out <新目录>`。这是显式的交付后处理：两遍响度整理、独立报告和视频码流字节校验，原片不覆盖；需要把 result.json 与最终文件记入项目交接，不能称其为未经后处理的原生导出。它不改变语速或字幕时间。默认目标-17 LUFS、限制真峰值留出AAC余量；最终实测与听审分别报告。

## English operator note

Discover the ordinary and advanced profiles, inspect real sources, then author scene purposes and local-time effects. The compiler offsets scenes onto the native frame clock and freezes the profile manifest. Save the returned timeline unchanged and poll the actual export. Never substitute the compiler response for a finished film.

The new still-image keyframe layer supports bounded planar perspective, opacity/blur keys, alpha-preserving compositing, source-pixel highlight/inversion, selective edge defocus and restrained texture. It is not 3D, OCR, matting, tracking, acoustic alignment or an avatar/TTS/music generator. Decode checks reject silent voice paths but cannot certify speech quality. Keep the ordinary route simple and retain failed drafts and immutable revisions.
