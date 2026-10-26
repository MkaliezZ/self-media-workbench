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

### 从组件演示到成片

先明确交付是技术演示还是供观众观看的内容。前者可以展示参数与对照；后者只保留帮助理解的文字，测试编号、引擎说明和调试信息放在交接记录。素材披露可简洁呈现。组件测试片不能仅因渲染成功就当作高级口播成片。

用户只验剪辑/特效执行时，沿用指定的原始素材和获准参考的配方，在独立项目重新登记、绑定并实际导出。参考成片仅用于比较，不能剪取或改名充当新输出。结论限定为同素材执行复现；不要擅自扩大为新图片、声音或创意生成测试。

审分镜时逐段回答“听到这句话，画面帮助观众看懂了什么”。动作教学宜展示动作前后与位置关系；整页文章只在交代上下文时出现，引用段再定位、抽离并稳定阅读。不要让同一密集海报反复承担所有视觉任务；有意保留的静态讲述段仍可成立。

导出后检查每次转场、叠层进出和关键阅读段，覆盖进入、重叠中间、稳定、退出帧；只看等间隔缩略图可能漏掉重影。尤其确认旧页退出后不会与新页正文重叠，主解释与字幕不争夺同一区域。发现可读性或叙事问题先修编排，不能以非零像素、特效数量或渲染成功代替。

记录技术检查、实际听审、视觉审片、用户成片验收四种结果及各自证据。未听审写未听审；用户拒绝后追加拒绝记录，保留旧片与已成立的技术结果，替代版本仍为 `pending_user_review`。素材重做须登记新来源和时间，不能冒充原封存输入的同条件盲测。

若交付音量不一致，Agent可对实际原生H.264导出调用 `scripts/master_audio.py --input <原片> --out <新目录>`。这是显式的交付后处理：两遍响度整理、独立报告和视频码流字节校验，原片不覆盖；需要把 result.json 与最终文件记入项目交接，不能称其为未经后处理的原生导出。它不改变语速或字幕时间。默认目标-17 LUFS、限制真峰值留出AAC余量；最终实测与听审分别报告。

## English operator note

素材登记的 `asset_id` 与时间轴中自行声明的 source `id` 不同，`evidence_source_id` 引用后者。剪辑末尾用实际 `video_duration`（新导入元数据会返回视频／音频各自时钟），旧素材可 probe 视频流；容器或音频总时长不能替代视频末帧边界。标题溢出时调整必要文案与布局后重新编译，不能删除关键解释只为通过校验。导出后接发布准备，按 [publish.md](publish.md) 绑定 timeline plan 与实际 export，不伪造 media_id。

Discover the ordinary and advanced profiles, inspect real sources, then author scene purposes and local-time effects. The compiler offsets scenes onto the native frame clock and freezes the profile manifest. Save the returned timeline unchanged and poll the actual export. Never substitute the compiler response for a finished film.

The new still-image keyframe layer supports bounded planar perspective, opacity/blur keys, alpha-preserving compositing, source-pixel highlight/inversion, selective edge defocus and restrained texture. It is not 3D, OCR, matting, tracking, acoustic alignment or an avatar/TTS/music generator. Decode checks reject silent voice paths but cannot certify speech quality. Keep the ordinary route simple and retain failed drafts and immutable revisions.

Distinguish a component demonstration from an audience-facing film. Keep debug labels in the handoff, give explanatory scenes a visible purpose, and inspect intermediate overlap frames as well as stable reading holds. Record technical, listening, visual and human-review results separately. A rejected film remains rejected even when its technical checks pass; a replacement stays pending human review, and newly created inputs are not a same-input blind retest.

For an execution-only acceptance task, reuse the specified raw assets and the recipe the user allows you to reference, register them in an isolated project, and perform a new native export. Finished reference films are comparison targets only. Report same-material execution reproducibility without expanding the task into asset generation or independent creative testing.
