# Local visual editing / 本地视觉编辑

The calling Agent selects semantic cues and relevant local images. The service validates and renders a source-bound plan using FFmpeg. Use the existing Agent task entry; people do not need another command. The applicable skill is [visual.md](../skills/self-media-workflow/references/visual.md).

调用 Agent 负责理解文案、选重点、判断图片相关性；服务执行严格校验和真实合成。统一任务入口支持 PNG/JPEG 输入并保存项目副本。`context.visual_plans` 返回历史方案与过期状态。

| Capability / 功能 | Current scope / 当前范围 |
|---|---|
| Emphasis / 字幕重点 | 完整已审阅字幕组变色并轻微放大；没有字符级时序 |
| Image cues / 配图打点 | 本地 PNG/JPEG；归一化槽位等比容纳；实际保留 ASR 组锚点 |
| Region highlight / 区域提示 | 图片原图区域变换或视频区域静态矩形；无跟踪 |
| Restore / 恢复 | 剪切、恢复、换识别或审阅版本使旧方案过期；重新核对保存后重算时间 |
| Export / 导出 | visual.mp4 与普通 MP4/SRT/JSON 并存；原件、旧导出、失败记录保留 |

No online image search, automatic matting/tracking, complex animation, music or voice generation is shipped. All composition currently uses CPU; this does not change GPU ASR selection. Image declarations are not independently verified rights or factual evidence.

## Dependency checks / 依赖检查

`doctor.visual_editing` and GET `/api/visual/status` check FFmpeg `drawtext`, `drawbox`, `overlay`, `scale`, and an installed CJK font. Existing FFmpeg/ffprobe and libx264 are also required. A custom installed TTF/TTC/OTF can be supplied as captions.font_path; the service freezes that font into the private project. The repository does not bundle system fonts.

Visual composition targets FFmpeg 7 or newer and reads its graph using `-/filter_complex`, the [documented option-file syntax](https://github.com/FFmpeg/FFmpeg/blob/master/doc/fftools-common-opts.texi). This avoids command-line length limits and the removed legacy filter_complex_script option in newer builds. Ordinary source/caption files remain separate and literal text expansion is disabled.

Windows defaults to Microsoft YaHei/SimHei; macOS defaults to PingFang and installed fallback fonts. Verify actual paths rather than assuming every system has them. Inputs must be square-pixel, already oriented video and static, already oriented PNG/JPEG; normalize rotated media explicitly before planning.

On macOS, if the installed FFmpeg lacks drawtext, the Agent can provision a full-featured build. Homebrew's [ffmpeg-full formula](https://formulae.brew.sh/formula/ffmpeg-full) includes text rendering dependencies; [ffmpeg@7](https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/f/ffmpeg%407.rb) is another versioned build with freetype/harfbuzz. Check current platform availability and choose the applicable installed build. Use its bin directory only in the task/service process environment, re-run doctor, and restart only an owned idle service. Do not globally relink or overwrite unrelated installations. Installation success alone is not rendering acceptance.

## Acceptance / 验收

`python -B -X utf8 -m unittest discover -s tests -p test_visual_editing.py -v` performs real FFmpeg composition, pixel checks, pause cut/restoration, stale-plan rejection, immutable original/export checks, image intake, idempotency and rejected-attempt retention. The media is self-generated colour video, sine audio and manually aligned Chinese text; it does not measure real speech recognition or listening quality. Set VISUAL_EVIDENCE_ROOT to preserve test projects, failed attempts and outputs. Windows results do not establish macOS execution; both macOS architectures must run these checks independently.
