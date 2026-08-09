# 项目开发时间统计

> ecom-image-generator — 1688 电商主图 & 详情图 AI 生成 Agent

---

## 总览

| 项 | 数据 |
|---|---|
| 项目名称 | ecom-image-generator |
| 启动时间 | **2026-08-07 08:03** |
| 当前版本 | v1.1.0 |
| 开发跨度 | 3 天（2026-08-07 ~ 2026-08-09） |
| 有效工时 | 约 25.4 小时（08-07 约 15h / 08-08 约 0.4h / 08-09 约 10h） |
| 提交记录 | 3 次 commit / 1 个 tag（v1.1.0） |
| 仓库 | github.com/joyce768768-glitch/ecom-img-generator |

---

## Day 1 — 2026-08-07（启动日，08:03–23:25，约 15 小时）

**主题：从 0 到 1 搭建全链路**

| 时段 | 事项 |
|---|---|
| 08:03 | 项目启动，确定四层解耦架构（config / image_client / prompt_builder / main）+ 双模出图（云端/本地 Ollama） |
| 08:08 | 前端方案定调：原生 JS → Vue3.4 + Vite5 + TS + Element Plus + Pinia 工程化 |
| 11:14 | 修复 server.py 枚举拼写 bug（`TONGYI_WANxiang`），交付完整 Vue3 前端代码 + 7 步自检清单 |
| 12:24 | 类型化配置中心（`/#/admin` 4 tab + 8 个 `/api/types` 接口，改 22 文件，修 6 bug） |
| 15:59 | 白名单保存 bug 修复验证（`from_dict` 反序列化 + `markDirty` 触发） |
| 16:25 | 中英翻译方案：用户填中文，Ollama gemma3 自动翻译英文（translator.py） |
| 16:50 | 翻译功能浏览器验证（批量翻译 + 单条翻译按钮） |
| 17:01 | 核心卖点改下拉多选；ModelConfigDialog 加 API Key 配置；删冗余文案 |
| 17:11–17:54 | 多轮 UI/UX 调整（类型卡片、编辑弹窗、场景编辑对话框、ID 显示） |
| 18:13 | 主图/详情模板布局（2 列卡片、勾选框、滚动条样式、按钮位置） |
| 23:06 | 图片卡片 2 列布局、编辑弹窗 z-index、「同步到后台/重置」按钮 |
| 23:11 | 通义万相 API Key 配置（.env，SDK 原生模式无需 base_url） |
| 23:25 | 商品原始图上传入口（主图首位改上传，originalImage 存 store） |

---

## Day 2 — 2026-08-08（凌晨延续，00:02–00:25，约 23 分钟）

**主题：图生图流程打通（Day 1 晚间工作跨午夜）**

| 时段 | 事项 |
|---|---|
| 00:02 | 模型调用困惑，重启后端加载 Day 1 修复代码 |
| 00:08 | 发现参考图 + 字段 prompt 未整合，改造 GenerateReqBody / PromptBuilder 接收 original_image |
| 00:17 | 图生图流程打通说明（[SYSTEM][PRODUCT][REFERENCE][SCENE] 四段） |
| 00:25 | 流程仍有问题，用户反馈失望（为 Day 3 深度调试埋下伏笔） |

---

## Day 3 — 2026-08-09（13:11–23:00，约 10 小时）

**主题：模型调试 + imageedit 核心升级 + 开源发布**

| 时段 | 事项 |
|---|---|
| 13:11 | 模型生成调试：dashscope SDK 缺失 / API Key 错误 / 尺寸不兼容，切 wanx2.1-t2i-turbo |
| 13:13–13:31 | GitHub 推送讨论 + specification 编写 + 产品团队协作流程讨论 |
| 14:46 | **三项优化**：rembg 自动抠图 + ref_strength 滑块 + 主图/详情图差异化 System Prompt |
| 15:03–15:42 | 商品参数「不设置」选项，空值跳过白名单校验（仅按参考图出图） |
| 16:02–17:44 | **核心改造**：诊断「衣架未成主体」根因（t2i 的 ref_img 仅风格参考）→ 切 `wanx2.1-imageedit` + `description_edit`，base64 data URL 解决公网访问，strength=1-ref_strength |
| 17:47–18:39 | 浏览器预览验证 imageedit（main_1 生成成功 551KB/800×800） |
| 19:10–22:53 | **开源发布**：README/RELEASE_NOTES 完整更新 → commit `00bef6e`（10 files）→ tag v1.1.0 → SSH push 到 GitHub（main + tag）→ 改名讨论 |

---

## 关键里程碑

| 日期 | 里程碑 | 版本 |
|---|---|---|
| 08-07 23:25 | 全链路打通（前端 + 后端 + 配置中心 + 翻译 + 参考图上传） | v1.0.0 雏形 |
| 08-08 00:17 | 图生图流程整合（参考图 + prompt 四段拼接） | — |
| 08-09 14:46 | 出图质量优化（rembg + ref_strength + 差异化 prompt） | — |
| 08-09 17:44 | **模型升级**：t2i → imageedit，真正保持商品主体 | v1.1.0 |
| 08-09 22:53 | 开源发布到 GitHub（commit + tag + push） | v1.1.0 |

---

## 技术演进时间线

```
08-07  架构搭建    config / image_client / prompt_builder / main 四层
                    + Vue3 前端 + 配置中心 + 翻译 + 参考图上传
                      │
08-08  流程整合     original_image 接入 PromptBuilder（四段 Prompt）
                      │
08-09  质量优化     rembg 抠图 + ref_strength 滑块 + 差异化 System Prompt
                      │
08-09  核心升级     t2i-turbo (风格参考) → imageedit (图像编辑, 保持主体)
                      │
08-09  开源发布     v1.1.0 commit + tag + push GitHub
```

---

## 工时分布

```
Day 1 (08-07)  ████████████████████████████████  15.0 h  (59%)
Day 2 (08-08)  █                                   0.4 h  ( 2%)
Day 3 (08-09)  █████████████████████              10.0 h  (39%)
               ─────────────────────────────────
               合计                                25.4 h
```

---

*统计基于 git 提交记录与开发会话日志整理，更新于 2026-08-09*
