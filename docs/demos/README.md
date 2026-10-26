# 样片 / Demo films

三条视频是工作台实际导出的成片。点击封面或 MP4 链接播放／下载；GitHub 是否内嵌播放取决于浏览器。视频存放在 Release 附件，不增加源码克隆体积。

These are actual workbench exports. Click a cover or MP4 link to watch/download; inline playback depends on your browser. Movies live in release assets, keeping source clones small.

## 最新 DSH 自主剪辑 / Latest DSH independently authored edit

[![DSH edit: The Judgment Loop](dsh-independent-edit-v03.jpg)](https://github.com/MkaliezZ/self-media-workbench/releases/download/dsh-edit-2026-10-26/dsh-independent-edit-v03-89s.mp4)

[89.64 秒 MP4 / 89.64-second MP4](https://github.com/MkaliezZ/self-media-workbench/releases/download/dsh-edit-2026-10-26/dsh-independent-edit-v03-89s.mp4) · v03 · 1920×1080 · 25 fps · 2241 frames

DSH 在新会话中根据同一套原始素材自主编排，未收到旧成片或配方。14 场景、31 个效果包括关键词开头、Alpha 人物分层、问题卡、抽象/具体对照、原文标黄抽离和四步循环。v03 经实际帧反馈修订；技术执行通过，人耳听审未进行。静态 AI 人物、合成旁白和原 CUDA ASR 数据均继承，没有新素材生成或新 ASR。公开展示获维护者授权；技术结果与人工质量验收分开记录。

DSH authored a new edit from the same raw assets in a fresh session, without the previous film or recipe. Its 14 scenes and 31 effects include keyword opening, alpha presenter layers, question cards, comparisons, original-document extraction and a four-step loop. v03 incorporates frame-based feedback. Technical execution passed; human listening was not performed. The static AI presenter, synthetic narration and earlier CUDA ASR are inherited. Public display is authorized separately from human quality acceptance.

Explicit audio mastering preserves the native H.264 stream; measured -18.72 LUFS / -3.37 dBTP. [Audit, revision history and limits](../../evaluation/dsh-independent-edit-20261026.md).

## 高级口播 / Advanced talking head

[![90-second advanced talking head](advanced-talking.jpg)](https://github.com/MkaliezZ/self-media-workbench/releases/download/showcase-2026-10-25/advanced-talking-90s.mp4)

[90 秒 MP4 / 90-second MP4](https://github.com/MkaliezZ/self-media-workbench/releases/download/showcase-2026-10-25/advanced-talking-90s.mp4) · 1920×1080 · 25 fps · 2250 frames

| 时间 / Time | 内容与技术 / Content and technique |
|---|---|
| 00:00 | 关键词匹配剪辑、纸页透视、视频填字与前景穿插 / Keyword match cuts, planar papers, video-in-text and foreground occlusion |
| 00:05 | 账号判断的三个问题 / Three questions for account diagnosis |
| 00:21 | 具体选题对照、原像素反相强调 / Topic comparison and source-pixel inverse emphasis |
| 00:38 | 答案、例子与适用条件 / Answer, example and conditions |
| 00:48 | 原文扫描标黄、抽离拉正、放大阅读再收回 / Original-pixel highlight scan, extraction, rectification, reading hold and return |
| 01:01 | 数据边界、移动聚光灯 / Data limits and moving spotlight |
| 01:12 | 保留原稿、单点修订假设 / Retained original and one-change hypothesis |
| 01:22 | 运营循环与收束 / Operating loop and conclusion |

人物是有室内背景的 AI 静态图片，无口型动画。旁白由外部 TTS 以正常语速生成，属于明确声明的模拟原始视频。实际 CUDA ASR 产生 283 个模型词组，审阅成 48 组字幕；原时间边界不变，8 处正常停顿保留。画面合成由原生时间轴执行。交付响度整理保留原视频码流；-17.22 LUFS、-1.74 dBTP。ASR 时间是模型估计，不能等同于逐字声学确定性。

The presenter is a static AI office portrait with no lip animation. External normal-rate TTS forms the declared simulated source video. Actual CUDA ASR produced 283 model groups, reviewed into 48 caption groups without changing their bounds; eight normal pauses were kept. Native timelines execute the composition. Explicit delivery mastering preserves the video stream (-17.22 LUFS, -1.74 dBTP). Model-estimated timestamps are not guaranteed character-level acoustic alignment.

## 剪辑特效声画版 / Editing effects with audio

[![Editing effects with audio](effects-with-audio.jpg)](https://github.com/MkaliezZ/self-media-workbench/releases/download/showcase-2026-10-25/effects-with-audio-95s.mp4)

[95.8 秒 MP4 / 95.8-second MP4](https://github.com/MkaliezZ/self-media-workbench/releases/download/showcase-2026-10-25/effects-with-audio-95s.mp4) · 1920×1080 · 25 fps · 2395 frames

| 时间 / Time | 技术 / Technique |
|---|---|
| 00:00 | 文章逐行标黄、抽离、转正放大、收回 / Document highlight, extract, rectify, enlarge, return |
| 00:14 / 00:22 | 移动聚光灯、截图局部放大 / Moving spotlight and source crop magnification |
| 00:30 / 00:38 | 视频画中画入场、强调文字动效 / Video PiP entrance and kinetic text |
| 00:44 / 00:48 | 横向与纵向揭示 / Horizontal and vertical reveals |
| 00:56 / 01:01 / 01:06 | 视频填字、亮度与反向遮罩 / Video-in-text, luma and inverted mattes |
| 01:11 / 01:16 | 羽化圆形窗口、分屏 / Feathered circular portal and split reveal |
| 01:21 / 01:26 | 原 PNG 透明洞与前景遮挡、圆形与方向转场 / Original PNG alpha holes, foreground occlusion, circle and directional transitions |

旁白为外部合成声音，含 BGM、旁白时音乐压低与轻音效。图形是自制演示素材；不是实拍剪辑质量或运营效果的证明。

Externally synthesized narration, BGM ducking and light sound effects accompany self-authored demonstration graphics. This is not evidence of live-footage editing quality or marketing performance.

## 媒体许可与完整性 / Media licensing and integrity

仓库自有代码和文档采用 MIT。三条成片中的配乐是 **Digital Clouds — Alejandro Magaña (A. M.)**，适用 [Mixkit Stock Music Free License](https://mixkit.co/license/modal/musicFree/)。配乐作为合成视频的一部分使用，其权利不被重新声明为 MIT；不提供独立音乐文件。图形、剪辑与合成由本项目制作，人物是虚构的 AI 图像，旁白是合成声音。

Repository-authored code and documentation use MIT. All three films include **Digital Clouds — Alejandro Magaña (A. M.)** under the [Mixkit Stock Music Free License](https://mixkit.co/license/modal/musicFree/), embedded in the finished video. Its rights are not relicensed as MIT; no standalone music is distributed. Graphics, edits and compositing are project-authored; the fictional presenter is AI-generated and narration is synthetic.

Exact file sizes, SHA256 hashes and probes: [samples.json](samples.json). Implementation and retained failures: [advanced production acceptance](../../evaluation/advanced-talking-20261025.md) and the [latest DSH edit audit](../../evaluation/dsh-independent-edit-20261026.md). Public showcase authorization and each film's quality-review status are recorded separately; platform CI does not certify audience response.
