# 原生画面与声音时间轴 / Native visual/audio timeline

纯画面、多源和音乐打点使用源秒数与成片帧数，不要求旁白或 ASR。统一 Agent 入口接受无声视频；已有口播审阅流程继续保留。

支持视频/已登记图片的顺序编排、显式入出点、横竖屏与帧率归一化、等比留边或明确的中心裁切、保留/调整原声、独立音乐/旁白/环境/音效音轨、增益与淡入淡出、混音限幅、输出时间标题、音乐瞬态候选、审阅后的整帧卡点和版本恢复。声音独立于镜头起止，可安排明确的 J/L 衔接。

## Agent 流程

读实际素材和项目 → 查 editing_logics → 按素材编排源区间 → 检查音乐候选/原声 → 必要时对齐草案 → 核对动作与静音停留 → 保存不可变计划 → 异步导出 → 解码、画面与声音检查 → 修订或恢复。

人只需描述任务，例如：“继续这个旅行 Vlog，先交代地点，再保留走到海边的过程；音乐只在场景转换时卡点，不要删掉安静看风景的时间。”Agent 自行处理接口、坐标与服务。

| API / schema | 作用 |
|---|---|
| GET /api/visual/logics | 已归并的剪辑逻辑及组件边界 |
| timeline-plan | 源文件哈希、镜头区间、音轨、标题、可选自定义 native_timeline 配方 |
| POST /api/projects/{pid}/music-onsets | 真实音频的瞬态候选；非通用节拍/BPM 认证 |
| POST /api/projects/{pid}/timeline/align | 在批准源窗口内按审阅音乐时间对齐草案，不自动保存 |
| POST /api/projects/{pid}/timeline-plans | 绑定当前项目版本与 supersedes 保存新计划 |
| GET /api/projects/{pid}/timeline-plans | 历史计划；context 也包含计划与当前 head |
| POST /api/projects/{pid}/timeline/export | 使用 plan_id 导出并轮询 jobs |

每个计划冻结素材、声音、声明、配方和实际时间映射。裁切/恢复都新建版本，保留旧文件；恢复是按当前 head 保存旧决定的新版本。导出 timeline.mp4、timeline-plan.json、timeline-map.json、provenance.json。损坏的冻结输入或映射拒绝导出。

音乐点由 Agent 听审/检查后选择，切换量化到输出帧，误差入表；不以每个瞬态自动切一次。音轨独立安排，不进行声部分离、声音克隆、音乐生成或自动鸭音。动态跟踪、复杂图层运动和曲线变速仍未实现。原生剪切不会自动获得口播词组不切穿的保证，涉及讲话须先检查音轨和分组。

当前限制：一个小时、128 个镜头、16 条附加音轨、15–60 整数输出帧率、偶数画布 ≤3840。混合源帧率可输入；输出帧数是权威时钟，AAC/容器时长另行检查。素材不足或音轨越界会明确拒绝，不能靠隐式补镜头或截断旁白掩盖。

## 转场与透明蒙版 / Transitions and alpha masks

`transitions` 选择非末镜头、原因、时长和 fade/wipeleft/wiperight/slideleft/slideright/circleopen。转场重叠两个镜头，成片总帧数扣除重叠；音乐打点对应转场中点。单个转场须短于两侧镜头，相邻转场不得吃完整个中间镜头。使用转场时最多 32 镜头；保留硬切是正常选择，不应为展示效果滥加特效。源片声音同步交叉淡化，独立音乐不重启。

`masks` 从已登记图片/视频选局部 crop，以独立 source_in 和成片 start/end 放入静态 slot；支持矩形/椭圆、0–64 成片像素向内羽化及不透明度。现有 PNG Alpha 与形状 Alpha 相乘，透明洞不会变成实色。最多 16 层，按数组顺序叠放、位于标题下面；羽化不能大于较小边长的一半。非自动跟踪、运动蒙版、色键抠像或 AI 抠像。旧计划省略字段仍可导出和幂等重放。[详细 Agent 规则](../skills/self-media-workflow/references/timeline.md)。

Native transitions use overlapping frames and crossfade original audio; independent beds remain continuous. Rectangle/ellipse source-region masks multiply their inward-feather alpha with the original PNG alpha. They are static compositions, without tracking/matting. Inspect actual decoded pixels and sound, keep failed attempts and restore as a new immutable revision. [Acceptance](../evaluation/timeline-fx-20261025.md).

示例 `scripts/timeline_case.py` 为原创插画旅行动画与自制音乐，明确不是实拍旅行。`scripts/timeline_http_acceptance.py` 检查实际后台服务、导出和重启续做。跨系统和独立盲测结果见本轮验收记录。
