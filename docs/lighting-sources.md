# 布光规则的教程依据 · 2026-10-28

当前策略版本：`tutorial-rules-v2-20261028`。不使用Radiance或模拟lux选电功率；场景判断、教程原则、几何可行性与现场试拍分开处理。规则实现见 `backend/lighting_policy.py`，新方案保存策略版本、逐条规则ID和来源ID。

## 资料与复用范围

| 来源 | 权威性与本轮实际阅读 | 授权与使用方式 |
|---|---|---|
| [R4 Web Design Primer, Chapter 14](https://pressbooks.library.torontomu.ca/webdesign/chapter/chapter-15-digital-photography-for-web-and-cross-media/)，Richard Adams、Ahmed Sagarwala，Ryerson University（现Toronto Metropolitan University），2018 | 大学开放教材；已读摄影章节与书籍许可页。用于曝光、白平衡、连续光与柔光附件的基本流程 | [书籍许可](https://pressbooks.library.torontomu.ca/webdesign/)为[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，个别另署名素材除外。保留作者、原文链接及许可；本仓库独立表述规则，未复制图片。静态摄影的f8、慢快门不变成视频默认值 |
| [R1 ARRI中文灯光手册](https://www.arri.com/resource/blob/83990/9d652bdf4480124850df62b824f2d47e/arri-lighting-handbook-chinese-data.pdf)，Bill Holshevnikoff | 专业灯光厂商手册，已读第5–15页相关内容；光源面积、溢光、曝光及主辅轮廓用途 | 版权材料，可公开阅读，不是开源教程；只作方法参考，不打包原文/图片，不把旧钨丝灯瓦数换算成现代LED |
| [R2 神牛／Simon Cade：How to Light Documentary Interviews](https://www.godox.com/solutions-video/1032.html) | 制片人实践，厂商发布；已读完整讲解正文，未声称看完视频。室内UL150单灯访谈、自然光时间变化、收音与附件 | 未核实到开放许可，只链接并独立提炼方法。存在品牌展示倾向，个案不能证明某瓦数普遍足够 |
| [R5 爱图仕／Tom Shaw：Every Shoot Is a Puzzle](https://aputure.com/en-US/articles/a-guide-to-videography-lighting-with-tom-shaw)，2026-05-06 | 摄影师实拍访谈，厂商发布；已读全文。先构图、环境曝光，再补主光；不同环境使用不同输出级别 | 版权所有，不是开源授权。仅引用链接和简短事实；不复制图片、图表或长段正文，不当品牌购买背书 |

**找到但没有进入当前规则的开放材料：**

- [SUNY／Roslin Smith《Lighting for Digital Film》](https://knightscholar.geneseo.edu/oer-ost/42/)：院校库明确标CC BY 4.0，2026年10月出版；本轮读到元数据和许可，PDF访问403、在线正文未能取得。是值得补读的开放教材，不能声称已经全文审阅或据此落规则。
- [Blender Studio：Three Point Lighting](https://studio.blender.org/training/blender-2-8-fundamentals/three-point-lighting/)：检索页标Free和CC-BY，正文请求402，未审阅视频。面向CG，渲染器光源W不能作为摄影灯电功率，不进入瓦数逻辑。
- [MIT OCW：Introduction to Lighting Demonstration](https://ocw.mit.edu/courses/21a-550j-dv-lab-documenting-science-through-video-and-new-media-fall-2012/resources/lab-10-part-2-introduction-to-lighting-demonstration/)：院校课程页面可读，所链许可CC BY-NC-SA 4.0；本轮只有课程说明，没有审看完整视频。不把NC素材并入MIT代码/商业产品，也不标成可无限制商用的开源素材。

开放许可、免费阅读和可信度是不同判断。未取得内容的教程只列候选；不以搜索摘要冒充已经学过的打光规则。

## 可执行规则

| 规则ID | 条件与动作 | 现场如何核对 |
|---|---|---|
| exposure_first · R4/R5 | 先确定最宽画面和背景曝光，再加主光，固定白平衡 | 同机位保留关灯/开灯对照，避免自动曝光抵消调整 |
| apparent_size · R1 | 根据风格选择人物看到的发光面积和距离，不以W决定柔和 | 看鼻影、眼窝、肤色和眼镜反光，兼顾柔光箱占地 |
| actual_assembly · R1/R4 | 使用实际柔光布、网格、色温与光路；输入W仅作铭牌登记 | 核对完整组合测光或试拍，不拿裸灯数据替代柔光箱 |
| headroom · R2/R5 | 先试已有灯，考虑附件、拉远、景别和光圈需要的余量 | 在预定时段/机位复拍，不能刚够一次曝光就判购买规格足够 |
| daylight_control · R2/R5 | 有窗/强日光先决定保留还是压制，优先遮光、机位或时段调整 | 先拍背景曝光；大功率个案也不是一定压过太阳的保证 |
| bounce_path · R1 | 反射/二次柔光按实际路径试拍，注意反射面色偏 | 不用到人物的直线距离或统一损耗系数估瓦数 |
| wide_coverage · R1/R5 | 宽景先检查覆盖、器材入画和活动范围 | 不把近距离头像个案当全身/宽景保证 |

这些是本仓库独立编写的条件规则，不是教程原文、官方标准、训练数据或普适采购公式。规则共用于三档；三档改变控制与投入，不自动逐档增加W。

## 瓦数如何呈现

爱图仕同一篇文章既讨论对抗日光时的600–700W级大灯，也展示夜间用80c配大柔光附件的案例。它证明环境重要，既不能得出“小灯普遍足够”，也不能得出“所有口播必须600W”。神牛UL150室内案例用于理解可控场景，不构成最低/推荐功率承诺。来源型号的级别与实际铭牌最大输入W仍要分别核对。

当前只输出带条件的案例、选型检查与余量提醒。环境未知时不默认低瓦数；已有78W等输入只标“登记”，不代表系统推荐或已验证足够。没有同附件试拍或可信测光，不输出精确所需W、型号购买结论或调光百分比。无需为迎合“偏小”而统一乘安全系数。

## 历史兼容

原Radiance适配器与解析函数只保留作开发诊断和历史证据，新方案不调用它们。旧方案JSON、图和输入不覆盖；界面不再将旧lux展示成选型依据，重新生成会保存新策略版本。历史报告中的数学通过只证明当时的数学关系，不能证明真实灯具功率选择。
