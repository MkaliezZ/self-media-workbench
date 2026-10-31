# 参数化镜头库 / Parameterized shot library

这是 Agent-only 的可选后台模块。用户描述画面需要，Agent 根据语义选择镜头并处理素材、坐标、字体、依赖、参数和服务。没有独立前端；普通剪辑和现有原生 effects 不依赖 Node。

## 发现与选择

- `GET /api/visual/shots?q=<关键词>` 搜索固定上游版本的 124 张参考卡、150 个样式索引。
- 同一检索另在 `native_cards` 返回4个原创解释型图解；`status=native_executable` 单独筛选原创可执行项。上游 `cards` 和 `adaptations` 的数量不增加，分别记录来源。
- `status=adapted_subset` 只返回有本地适配实现的卡；`reference_only` 没有可直接执行的参数接口。索引中的 `adaptations` 给出可用 `shot.kind`。
- `GET /api/visual/shots/status`、`doctor.shot_library` 检查本机可用性；schema 名为 `shot-render`。
- 必须按观看目的选动作：观点改写、重点强调、步骤递进、对比、数字解释、同时观察。不要为显得高级给每句话加动画；保留干净讲述、证据阅读和安静停留。

| shot.kind | 主要输入 | 使用与限制 |
|---|---|---|
| typewriter-rewrite | title、initial、replacement、subtitle | 打字→犹豫→删除→重打；编排时间不等于逐字语音对齐 |
| marker-title | title、subtitle | 标题落定后描画笔触；不是对原文截图标黄，后者用 document_extract |
| outline-title | title、subtitle | 空心文字收缩→实心点亮；只用于一个重点 |
| list-reveal | title、items[{label,detail}] | 2–6项错峰进入；留足逐项阅读时间 |
| card-stack | title、items[{label,detail,image?}] | 2–4张卡叠放；只让顶卡承担细节阅读，底部标签交代集合 |
| before-after | title、before、after、before_label、after_label | 两张真实登记图片随分割线揭示，保持 contain；不伪造“处理前”的劣化图片 |
| line-chart | title、points[{label,value}]、unit、data_note | 2–8个非负数据点，显示坐标与单位；数据须有真实来源或声明示意 |
| split-screen | title、items[{label,detail,image?}] | 2–4格，横屏双列、竖屏单列，不能伪造同期/同场关系 |
| digit-roll | title、value、data_note | 数字滚动到声明值；动画不证明统计真实性 |
| concept-network | title、center、nodes、direction | 节点与关系线错峰建立；无向/汇聚/发散由Agent明确选择 |
| concept-matrix | title、label、rows、columns、conclusion、data_note | 重复图标铺开→背景降权→结论，数量须声明示意或依据 |
| layered-rings | title、center、layers | 中心保留，1–3层圈与标签依次进入；不是量化强度图 |
| process-chain | title、steps；可选fail_step或step_probability | 2–7步流程；概率需要显式独立同概率假设与说明，失败与概率分镜 |

全库为 Apache-2.0 的上游配方索引；9个本地实现是选取运动语法后的参数化适配，**不是全部150个样例的原样复刻**。具体来源和固定 commit 见 `third_party/video-shotcraft/catalog.json`。不要仅因名字匹配就声称原样还原。

另4个图解为工作台原创实现，不属于上述上游。真人／资料／图解交替的选择规则、具体参数和未实现动作见[解释型图解](../../../docs/explanatory-diagrams.md)。用户给视频学习时只复用剪辑逻辑和视觉机制，不继承其中观点、数据、人物、品牌或配乐。

## 执行

读取当前 context；按实际 schema 提交 `POST /api/projects/{pid}/shot-renders`，提供新 request_id、当前 project_revision、reason 和 shot。支持 16:9、9:16、方形画幅，25/30fps，3–12秒；最后至少1秒固定阅读。颜色为不含 # 的六位 HEX。字体使用实际本机字体，可传绝对 font_path；字体只在本机任务中冻结，不自动对外分发。

图片必须先用统一任务入口登记。image/before/after 的 `{asset_id,sha256}` 来自当前项目 image_assets；不接远程网址、任意 TSX 或脚本。完整对照保留两张原图，不把生成素材当作事实证据。字号会在可读范围内适配；内容过长则缩短、分镜或减少条目，不能靠无限缩小字号通过。

返回 render_id 和普通 job。轮询已有 job API 到 done/failed/interrupted；只有 done 才可交付。成功时返回 `media_id`、素材哈希、视频路径和实际帧数，自动标为 generated。重新读 context，将该 media_id/sha256 作为原生 timeline-plan.sources 的 media，再选择源区间、编排旁白/音乐；高级口播也可把该素材作为场景 shot。渲染片段无音轨，声音由原生时间轴统一混音，避免重复混音。

`GET /api/projects/{pid}/shot-renders` 可追溯冻结请求；job.result 含最终路径和素材ID。同 request_id+完全相同请求返回原 job，不重复渲染；同 ID 改内容409。失败/服务中断后保留原任务，用新 request_id 和新 context 重试；不要冒称旧失败已通过。

## 安装与验收

运行时缺失返回503和 setup_helper。用户已授权该模块安装时，Agent 执行 `python scripts/setup_shots.py`：固定 npm lock 安装、准备兼容无头 Chrome。已有兼容浏览器可传 `--browser <absolute executable>`；可设置 SELF_MEDIA_SHOT_NODE / SELF_MEDIA_SHOT_BROWSER。只在显式 setup 下载，正常渲染不安装包、不上传素材、不打开网页。不改全局 PATH 或 npm 配置。Remotion 使用独立许可；见 docs/shot-library.md。

渲后检查完整解码、画幅、帧率与帧数；另看进入/运动中/稳定/退出帧、中文可读性、图表与原数据和图片对应关系。合成后检查声音/字幕/转场。技术通过、实际视觉审片、听审和用户验收分别记录。不能以样例数量或动画数量代替成片质量。
