# 移除前端，统一Agent入口 · 2026-10-28

按维护者最终决定，产品仅通过Agent、CLI/API使用。此前的前端易用性、配色和方形样式迭代未作为新版本保留。

## 最终变更

- 删除整个`frontend/`源码目录，移除静态页面挂载和根入口、布光状态、task intake、doctor中的界面链接。
- 关闭Swagger/ReDoc网页，保留机器可读的OpenAPI JSON、Agent能力/schema发现和原CLI/API。
- README、Agent约定、布光说明、统一入口Skill及本机已安装Skill统一使用Agent流程；历史界面截图/选型记录标为历史，现行说明不再引导打开页面。
- 原始素材、用户项目、历史方案与导出保留；媒体、布光、三档方案、顶灯上下文与版本/反馈接口继续使用。未保留只为本轮前端增加的上传、向导和主题代码。

## 实际验收

| 检查 | 结果 |
|---|---|
| 本地全量回归 | **101项通过，109.673秒** |
| 布光针对性检查 | 21项通过；包括Agent路由、schema、三档、顶灯、报告和历史 |
| 前端源码 | `frontend/`不存在，测试持续约束 |
| 真实运行服务 | `/ui`、`/ui/`、`/ui/lighting.html`、`/ui/lighting.js`、`/docs`、`/redoc`均404 |
| Agent服务 | `/openapi.json`、`/api/agent/v1/capabilities`、`/api/lighting/status`均200；根入口不再返回UI字段 |
| 已安装统一入口 | Skill与仓库SHA256一致；实际通过该Skill读取原15㎡项目，修订仍为5、当前布光方案不变 |
| 项目保护 | 原15㎡项目及其全部保存方案JSON的SHA256与移除前一致 |
| 运行进程 | 保留原Agent服务端口58788；核对归属与空闲状态后重启。独立前端验收服务已停止 |

本机`Studio/outputs/布光易用性迭代-20261028/`保留`regression-agent-only.log`、`agent-only-runtime-verification.json`等证据。前端源码退役前另存可恢复ZIP，CRC检查通过，未打包用户数据或提交公库。此前112项向导测试与界面截图属于被放弃方案的过程，不代表最终Agent-only版本的验收数量。

复现：`python -m unittest discover -s tests -v`。正常任务由Agent读取[统一约定](../AGENTS.md)，通过`python workbench.py run`执行，使用者只需提出任务并提供材料。真实内容质量、实体布光效果和人耳听审仍须相应实际验证；工具回归不代替这些验收。推送后的云端CI另查实际状态，不沿用历史通过结论。
