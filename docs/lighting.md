# 拍摄布光：三档方案

本地服务启动后，打开 `/ui/`，点击侧栏「拍摄布光 · 三档方案」；也可直接访问 `/ui/lighting.html`。无需 Node 构建、模型密钥或专业灯光软件。

## 使用

1. 上传房间照片或平面图（PNG/JPEG/WebP，每张最多10MB、2400万像素）。一张即可开始。
2. 生成简版、标准、理想三张方案卡。展开查看器材、位置、高度、摆放理由和步骤，下载 SVG 布局或完整 HTML 报告。
3. 有条件时补尺寸、人物/相机位置、窗光、障碍和已有灯具。重新生成会保留旧版本；选择当前版本的一档，试拍后记录问题与下一次调整。

**网页上传本身不解析图片。** 未补场景时，网页立即给出明确标记的默认位置草案。要根据照片内容规划，可直接对调用工作台的 Agent 说「按这张图给三档布光方案」，由它实际查看原图、登记观察与假设，再调用同一接口生成。也可在网页调整示意图并确认场景。两种方式共享项目、版本和导出，不把默认草案冒充图像识别。

简版优先可利用窗光或已有单灯；标准增加反光/负补光控制；理想在空间允许时增加分离控制。档次不等于固定灯数或固定瓦数。空间不足时卡片保留并解释条件；当前规则面向单人固定口播，不处理多人舞台、悬挂或复杂片场。

## 数据和计算

- 原始图片保留 SHA256；跨项目或被修改的原件不能用于新方案。Agent 审图需要绑定图片的文字观察，不代表额外人工验收。
- 人物、机位、障碍和灯位共用归一化坐标，文字与 SVG 同源。已知宽深时按比例绘图；未知时仅作相对示意，不显示假精确距离。高度另行声明。
- 已有灯具可登记额定输入 W。没有具体型号/附件的测光数据时，只输出能力要求和核对方法；首版没有经校准的灯具选购数据库，不自动推荐准确瓦数。
- API 可补同一附件、色温、距离条件下的满输出照度和来源，计算远场小光源直射近似；不将裸灯数据用于柔光箱，不假定调光百分比线性。输入数据有效性仍需核对。
- 候选灯架考虑边界、约22cm占地半径与障碍；该简化半径不能代替具体灯架、柔光箱、通道和消防检查。未知障碍高度按保守全高挡光。未模拟人体投影、墙面回光、真实配光曲线和柔光近场。
- 试拍记录是用户声明，不会自动标成效果通过。测量lux必须同时说明测量点及传感器方向。

## 可选 Radiance

默认不需要 Radiance；未配置时仍能生成规则方案。可使用官方发布包的 `oconv` 和 `rtrace`，配置其所在目录：

```sh
python workbench.py configure --radiance-bin /absolute/path/to/radiance/bin
python workbench.py doctor
```

也可设置进程环境变量 `SELF_MEDIA_RADIANCE_BIN`。重启旧服务后配置生效。不自动下载、不修改系统 PATH、不把二进制并入仓库。目录旁的 `lib` 作为进程 RAYPATH。

当前适配器仅把有匹配光度资料的光源校准为小球形等效光源，并对朝向相机的人脸采样面作 **direct-only** 交叉计算（`-ab 0`）。结果不是完整摄影布光仿真，不支持直接上传/执行用户 Radiance 场景或自动导入 IES。缺资料为 `insufficient_data`；未安装为 `unavailable`；失败保留原因，不冒充模拟成功。

## Agent/API

统一入口 `python workbench.py run "按照片给三档打光方案" --input /absolute/path/room.png --intent lighting`，随后按返回的布光说明实际执行。详见 [Agent 布光流程](../skills/self-media-workflow/references/lighting.md)。

| 接口 | 用途 |
|---|---|
| `GET /api/lighting/status` | 能力与可选引擎状态 |
| `POST /api/projects/{pid}/lighting/images?name=room.png` | 原始图片字节上传 |
| `POST /api/projects/{pid}/lighting/plans` | 校验场景，保存恰好三档与布局 |
| `GET /api/projects/{pid}/lighting/plans` | 版本、当前方案与选择 |
| `GET /api/projects/{pid}/lighting/plans/{id}` | 读取历史结构化方案 |
| `GET .../{id}/files/{simple.svg,standard.svg,ideal.svg,plan.json,report.html}` | 导出 |
| `POST .../{id}/select` | 选择当前方案的一档 |
| `POST .../{id}/field-checks` | 保存试拍声明 |

写操作带项目修订号；新方案需引用 `supersedes`；相同 `request_id` 和内容可幂等重放。Agent context 返回图片、版本、选择和反馈。场景/生成/选择/反馈 schema 可从 `/api/agent/v1/schemas/lighting-*` 读取。开发依据见 [规划与选型](plans/lighting-planner.md)，本次技术验收见 [记录](../evaluation/lighting-20261028.md)。真实房间、新手照图执行和换人复做仍待验证。
