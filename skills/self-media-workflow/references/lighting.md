# 拍摄布光

独立拍摄前任务，不要求诊断/脚本/ASR。统一入口lighting返回项目和上下文。调用Agent必须实际查看绑定图片，核对人物、机位、窗户、障碍和用途；单纯登记图片不是自动视觉识别，缺失条件须标明假设。现场照片不能直接当带比例平面图。

发现capabilities与lighting-plan、lighting-scene、lighting-selection、lighting-field-check实际schema。图片经统一入口登记，或POST /api/projects/{pid}/lighting/images?name=filename上传原始二进制（每张10MB，8张/方案）。保留原图与摘要；跨项目/变更原件会拒绝。

坐标0到1，左上角原点，右x下y。人物/相机/障碍共享同一俯视关系。assessment=agent_reviewed需要绑定图片ID的observations，仍属调用Agent声明；不等于服务已做视觉认证。缺尺度不填米数；宽度与进深一同给，层高和面部高度未知留空。缺项集中询问，先交付能完成的部分。

用新request_id、当前project_revision、当前lighting_head作为supersedes提交POST /api/projects/{pid}/lighting/plans。后端实际保存简版/标准/理想三档与SVG；路由计划不是交付结果。简版侧重已有器材与低投入；标准控制阴影与重复拍摄；理想在可行空间内提高分离与稳定，不强制灯更多、更亮或RGB。审阅三档是否适合实际场景；不合适就改场景或取向另存新版本。

服务检查已知矩形障碍和灯架占地。图片外空间、器材完整尺寸、画面穿帮、眼镜/镜面、肤色和窗光变化仍需Agent与现场复核。找不到位置会给条件方案，不往墙外放灯。当前输出是确定性俯视图，不是自动房间重建、透视反投影或最终画面仿真。

按仓库 docs/lighting-sources.md 和 backend/lighting_policy.py 的教程规则工作：先构图与背景曝光，再主光面积/距离，再阴影和分离控制。补ambient_condition（unknown/controlled/window_mixed/bright_daylight）、modifier_strategy（unknown/softbox/bounce）、framing（head_shoulders/waist_up/wide）即可选择分支。三档不对应固定W；强日光先控环境，反射/宽景关注实际光路与覆盖余量。

input_watts是登记的额定输入功率，不是系统推荐或验证足够。来源案例的灯具级别也不等于实际最大输入W。新方案保存policy_version、rules、selection_guidance与来源；不调用Radiance、不从lux或渲染器W反推所需电功率。photometry仅保留供审阅，缺实际附件测试不能给精确W、调光百分比或采购保证。旧适配器仅作历史开发诊断，不通过安装或配置重新启用产品计算。

工作台仅通过Agent、CLI/API使用。Agent完成图片登记、三档比较、人物/相机/障碍关系、选档与试拍记录，并向用户交付SVG/报告；每次写入后重新取context/revision。field-checks记录选档、试拍图ID、曝光、测量点/方向、实际问题和下一项调整；声明记录不自动提升为真人验收通过。结构/几何、工具执行和实景效果分别报告。


已有顶灯/环境灯写入scene.existing_lights，记录kind、mounting、basis、可选point、input_watts/cct_k（未知null）、state、face_effect、note。kind=incandescent不能仅凭照片暖色推断；情景假设用basis=assumed。face_effect非unknown需note，声明不是独立实测。读取existing_light_assessments区分待对照、有用面部补光、仅背景、不利阴影/混色及关闭状态。可调暗主灯不等于已验证可降低额定采购W；不能用顶灯W相减。顶灯投影不占灯架地面空间，记录后重新生成版本，不覆盖无顶灯方案。
