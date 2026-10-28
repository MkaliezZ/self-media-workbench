# 拍摄布光

独立拍摄前任务，不要求诊断/脚本/ASR。统一入口lighting返回项目和上下文。调用Agent必须实际查看绑定图片，核对人物、机位、窗户、障碍和用途；纯网页上传生成的是明确标为假设的初稿，不是自动视觉识别。现场照片不能直接当带比例平面图。

发现capabilities与lighting-plan、lighting-scene、lighting-selection、lighting-field-check实际schema。图片经统一入口登记，或POST /api/projects/{pid}/lighting/images?name=filename上传原始二进制（每张10MB，8张/方案）。保留原图与摘要；跨项目/变更原件会拒绝。

坐标0到1，左上角原点，右x下y。人物/相机/障碍共享同一俯视关系。assessment=agent_reviewed需要绑定图片ID的observations，仍属调用Agent声明；不等于服务已做视觉认证。缺尺度不填米数；宽度与进深一同给，层高和面部高度未知留空。缺项集中询问，先交付能完成的部分。

用新request_id、当前project_revision、当前lighting_head作为supersedes提交POST /api/projects/{pid}/lighting/plans。后端实际保存简版/标准/理想三档与SVG；路由计划不是交付结果。简版侧重已有器材与低投入；标准控制阴影与重复拍摄；理想在可行空间内提高分离与稳定，不强制灯更多、更亮或RGB。审阅三档是否适合实际场景；不合适就改场景或取向另存新版本。

服务检查已知矩形障碍和灯架占地。图片外空间、器材完整尺寸、画面穿帮、眼镜/镜面、肤色和窗光变化仍需Agent与现场复核。找不到位置会给条件方案，不往墙外放灯。当前输出是确定性俯视图，不是自动房间重建、透视反投影或最终画面仿真。

input_watts是登记的额定输入功率。无匹配型号/附件测光时，给选型要求和缺项，不编瓦数、照度或调光百分比。photometry必须有来源、时间、附件、色温和有效最短距离，并与当前附件/色温匹配。计算仅为满输出轴向小光源远场直射近似；缺少近场/反射/相机标定，target_lux也是用户目标而非通用肤色标准。

Radiance可由configure --radiance-bin /absolute/bin或SELF_MEDIA_RADIANCE_BIN启用。正常任务不下载；缺引擎时仍可规划。只有匹配光度、房间与高度数据时运行自生成场景。失败保留reason，不把粗算冒充成功模拟，不执行上传的.rad命令。

独立网页/ui/lighting.html或/ui/#lighting支持上传、三档比较、点击调整人物/相机/障碍、选档、历史、SVG/报告下载和试拍记录。每次写入后重新取context/revision；Agent更新后刷新网页。field-checks记录选档、试拍图ID、曝光、测量点/方向、实际问题和下一项调整；声明记录不自动提升为真人验收通过。结构/几何、数值引擎、网页操作、实景效果分别报告。
