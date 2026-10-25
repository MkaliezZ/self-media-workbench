# 常用信息动效 / Source-bound motion effects

`timeline-plan.effects` 提供可复用的原生动作组件，不需要生成图片来代替效果。Agent 负责阅读原文、选择真实区域、安排语义时机；服务冻结来源并执行逐帧合成。`doctor.visual_editing.motion` 检查Pillow及FFmpeg qtrle编码器，依赖由requirements.txt安装，使用CPU合成。

| kind | 实际动作 | 主要输入 |
|---|---|---|
| document_extract | 原文黄标逐行扫入→段落从原位置抽离→透视拉正/放大→保留阅读→收回原位 | 已登记图片、source_rect、每行highlights、四点page_quad、target_rect、quote及各阶段时长 |
| motion_layer | 图片/视频裁切、位移、缩放、平面旋转、透明度、阴影、横/纵线性揭示 | 已登记图片/视频、source_in、crop、from_rect/to_rect、入出时长、animation及easing |
| spotlight | 非重点区域压暗，焦点按两端位置移动，边缘羽化 | from_rect/to_rect、形状、羽化、压暗量及入出淡化 |
| motion_text | 文字滑入/缩放/淡入，指定真实子串着色 | text、accent、slot、font_height、入出时段 |

原始资料截图是像素来源。`quote`是调用Agent核对的文字声明，服务保留选区像素，不把它当作OCR校验。`highlights`必须位于source_rect内部。page_quad按左上、右上、右下、左下给出，须为凸四边形；抽离段落用真实原图像素变形，正向展示保持选区比例。高亮用乘色保留黑字，支持多行依次出现。

页面四点保持正向阅读顺序：上/下边的左点在右点左侧，左/右边的上点在下点上方，并保持顺时针凸形。镜像或倒置角点会拒绝，避免反字及转正插值途中退化；不把此组件当作翻面/旋转180度的三维动画。

document_extract的流程在start/end内执行：原文出现、依次标黄、一次抽离到target_rect、阅读停留、收回。end之后整个效果层退出、底图恢复原样；当前没有“归位后持续保留黄标”的状态，也没有先到一个目标再到第二目标的多阶段关键帧。需要这些精确编排时明确列为缺项，不能用更改原始底图假装组件已支持。

动效直接以成片帧为时钟，按effects数组顺序叠加，在普通字幕标题下面。前后位置属于明确编排的双端关键帧，提供smoothstep/ease_out_cubic；不是自动对象跟踪、自动OCR、人物抠像、任意曲线或三维场景引擎。motion_text的编排时间不等于字符声学对齐；实际口播字幕强调仍用ASR绑定的visual-plan。

`motion_layer.animation=pop` 在编排矩形内执行居中的65%→100%缩放入场，区别于只有位移/透明度的move。motion_text超出slot的水平宽度或垂直字形范围时明确拒绝渲染，调整字号、区域或拆段后保存新方案，不静默裁掉文字。accent按原文首个完整匹配的字符范围着色，可以跨显式换行。

同一效果可换已登记资料、实际选区与时间参数，保留不可变计划、原始素材、字体和旧导出。恢复旧决定须读取当前head后新建版本。旧计划不含effects仍可导出和幂等重放。修改原件、字体或映射会拒绝导出。

限制：最多32项，动效时间轴≤300秒，画布面积≤1920×1920；素材区间必须实际存在，选区至少2像素。motion_layer目标按明确矩形重采样，调用者若需保留比例应选择相同比例的端点；document_extract自动按选区比例放入target_rect。视频图层以输出fps逐帧解码，保留解码得到的Alpha；具体透明视频格式仍需实测，不能据此推断自动抠像。

可直接请求：“把这篇资料的这两句标黄，再抽出来放大正向展示，其他内容压暗，最后收回原位。”Agent查timeline-plan schema并处理坐标、服务和导出，不让人记命令。

复现入口为 `scripts/motion_showcase.py --out <新目录>`，可用 `--video <已授权本地视频>` 替换诊断视频。它使用原创文章、示例UI和实际原生接口生成56秒功能展示；没有账户成绩或外部报道。源码和schema可复用，并非只交付一个演示视频。实际结果和保留的修订见[验收记录](../evaluation/motion-effects-20261025.md)。

The native `effects` array executes document highlighting/extraction/rectification/return, image/video endpoint transforms and linear reveals, authored moving spotlights and kinetic text. Source pixels and immutable plan state are retained. Geometry and timing are explicitly authored: no automatic OCR, object tracking, matting or acoustic character-alignment claim. CPU composition uses Pillow plus a finite RGBA layer encoded by FFmpeg; the final decoded frame clock is checked against the saved map.
