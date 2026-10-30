# 参数化镜头库接入验收 · 2026-10-30

## 范围与结果

技术验收通过。全库124张参考卡/150个样式索引；9类参数化适配可以由Agent执行，渲染成功后自动登记generated素材，进入现有原生时间轴。没有恢复前端。普通剪辑/ASR/布光继续使用原有依赖与接口。

本轮是运动语法适配与工程验收，不是上游150个样例的逐像素复刻，不证明实际账号内容的审美或运营效果。用户成片验收为 `pending_user_review`。

## 实际执行

- Windows / Python 3.11环境的完整106项回归通过，132.755秒；Remotion源代码TypeScript检查通过。
- 显式setup helper通过：固定lock安装169个npm包，使用本机Edge 149.0.4022.69的无头 `chrome-for-testing` 模式；Node25.8.1，Remotion4.0.484，React19.2.7。
- 21次实际API异步渲染：9类横屏1280×720/25fps、9类竖屏360×640/30fps、高清横屏马克笔标题1920×1080/30fps、高清竖屏前后对照1080×1920/25fps、方形640×640列表/25fps。每条5秒。
- 全部验证画幅、实际解码帧数、输出帧率、完整解码、运动中像素变化和最后1秒稳定停留；帧数分别125/150。相同请求重放返回原job，不重复登记素材。
- 9个实际生成素材进入现有原生时间轴，输出45秒/1125帧/1280×720/25fps，独立诊断音轨混入；全新进程重读21条镜头记录与22条素材。诊断音是测试信号，不是旁白或音乐；未进行听审。交付静音预览移除诊断音，保留视频流。
- 复核横竖屏稳定帧、代表性的动作中间帧与原图对照；检查文字、图表标签、两图分割和图层顺序。该复核不等于用户审美验收。
- 新版常驻服务真实HTTP可发现124张参考卡、9个适配、shot-render schema和实际可用运行状态；/ui/、/ui/lighting.html、/docs、/redoc仍404。已安装Agent入口Skill同步。
- 重启常驻服务前核对checkout/PID/命令及所有项目jobs均空闲。13个原有项目manifest的SHA256与重启前一致；演练数据保存在独立outputs目录，没有修改用户项目内容。
- 19个保留的上游源文件/许可证/配方卡，逐个按Git blob SHA-1与固定commit核对。Apache-2.0许可与修改说明随代码保留；原截图/音效/网页编辑器/发布工具未复制。

具体帧数、像素指标、哈希与范围见[机器摘要](shot-library-20261030.json)。

## 保留的失败与边界

首次完整跑到数字滚动时，中文后缀触发隐藏文本框的高度检查；修正明确行高和安全高度，单独复测后在新目录重新跑完整21条，全部通过。原始失败job、render.log、半成品和首轮输出保留，没有把首次失败覆盖成通过。

首次自动Chrome下载未完成，终止该任务后使用本机已安装Edge完成显式setup和全部本机验收。默认自动下载路径仍由Remotion提供，本机未声称下载路径通过；网络受限环境可指定兼容本机浏览器。

当前只产出不透明H.264无声片段；透明叠加层、任意卡自动执行、自动OCR/跟踪/抠像、逐字声学对齐、原生剪映导出不在本模块范围。数据_note是调用Agent的声明，不是数据真实性认证。

已添加Windows/Apple Silicon/Intel Mac的独立渲染CI工作流，但此本地验收不继承或宣称尚未观察到的云端/其他平台结果。推送后的真实CI状态须单独核对。

## 复现

```text
python scripts/setup_shots.py --browser <compatible-local-browser>
npm --prefix shot_renderer run typecheck
python -B -X utf8 -m unittest discover -s tests -v
python -B -X utf8 scripts/shot_acceptance.py --out <new-empty-output-folder>
```

使用 --compact 降低横屏技术测试分辨率；仍执行全部21条、原生时间轴与新进程恢复。--limit/--offset只用于定位问题，不能算完整验收。真实工程、帧截图、日志与静音预览保存在本机 `outputs/shotcraft-20261030-acceptance-02`，未把本机字体或用户数据放入公库。
