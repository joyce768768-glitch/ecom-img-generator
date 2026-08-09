# Release Notes

---

## v1.1.0 — 参考图主体保持升级

**发布日期**：2026-08-09  
**上一版本**：v1.0.0

---

### 🎯 核心变更：参考图从「风格参考」升级为「图像编辑」

v1.0.0 上传参考图时切换到 `wanx2.1-t2i-turbo`，其 `ref_img` 参数仅为**风格/色调参考**，模型无法真正复刻参考图里的商品形态，导致「参考图的衣架没成为主体」。

v1.1.0 改用 **`wanx2.1-imageedit` + `description_edit`**（阿里云通用图像编辑模型）：以参考图为基底，按文本指令修改背景/场景，**真正保持商品主体不变**。

| 项 | v1.0.0 | v1.1.0 |
|---|---|---|
| 参考图模型 | wanx2.1-t2i-turbo | **wanx2.1-imageedit** |
| 调用方式 | ref_img（风格参考） | **description_edit（图像编辑）** |
| 强度参数 | ref_strength（越大越像） | strength = 1 - ref_strength（越小越接近原图） |
| 参考图传入 | 本地 URL（云端无法访问） | **base64 data URL**（公网可访问） |
| 商品主体保持 | ❌ 仅风格近似 | ✅ 真正保持主体 |

---

### ✨ 新增功能

- **rembg 自动抠图**：上传参考图时自动去除原背景（输出透明 PNG），消除背景干扰，提升商品主体识别准确性
- **ref_strength 前端滑块**：0-1 调节参考图影响强度，值越大商品主体保留越完整（默认 0.5）
- **主图/详情图差异化 System Prompt**：主图纯白底居中（`SYSTEM_PROMPT_MAIN`）、详情图场景化（`SYSTEM_PROMPT_DETAIL`），两套风格约束分层
- **商品参数「不设置」选项**：颜色/规格/材质/标题/卖点均可留空，支持仅按参考图出图，空值跳过白名单校验
- **Prompt 5 层拼装**：在 v1.0.0 的 4 层基础上新增 `[CATEGORY]` 类目专属段，`[REFERENCE]` 语义改为编辑指令

---

### 🔧 技术改进

- `image_client.py`：`TongyiWanxiangClient` 有参考图时走 imageedit 分支，新增 `_ref_to_data_url()` 把本地参考图转 base64 data URL 传入 `base_image_url`（解决阿里云服务器无法访问 127.0.0.1 的问题）
- `prompt_builder.py`：`[REFERENCE]` 段改为编辑指令风格，明确「产品主体完全不变，[SCENE] 只作用于背景/环境」
- `server.py`：保存参考图时调用 rembg 抠图；前端日志面板可见「模式=wanx2.1-imageedit 图像编辑」
- `config.py`：集中管理主图/详情图差异化 System Prompt + 电商专用负面词
- `frontend`：ProductForm 增加「不设置」选项 + ref_strength 滑块；generation store 空值跳过白名单校验

---

### ⚠️ 已知限制（更新）

- ~~通义万相 `wanx-v1` 不支持图生图，需上传参考图后自动切换到 `wanx2.1-t2i-turbo`~~ → 已改为 `wanx2.1-imageedit`
- ~~`ref_img` 为风格参考模式，商品外观一致性取决于 `ref_strength` 参数~~ → **已解决**，imageedit 真正保持商品主体
- imageedit 的 `description_edit` 输出尺寸跟随 `size` 参数，详情图竖版由 `_resize_if_needed` 归正到 750×1000
- Ollama 本地出图需要 GPU 显存（SDXL 4GB+ / Flux 8GB+）
- 素材库使用 localStorage，上限 50 条

---

### 📝 开发日志

**2026-08-09**：v1.1.0 发布
1. 诊断「参考图衣架未成为主体」根因：t2i-turbo 的 ref_img 仅风格参考
2. 切换到 wanx2.1-imageedit + description_edit，strength = 1 - ref_strength
3. base64 data URL 解决公网访问问题，main_1 验证生成成功（551KB / 800×800）
4. rembg 自动抠图 + ref_strength 滑块 + 主图/详情图差异化 System Prompt
5. 商品参数「不设置」选项，空值跳过白名单校验
6. README / RELEASE_NOTES 完整更新，.gitignore 补充 .u2net/

---
---

## v1.0.0 — 首个正式版

**发布日期**：2026-08-08  
**项目起始**：2026-08-07

---

### 🎉 里程碑

从零到一，一天内完成完整的电商主图/详情图 AI 生成工具，覆盖前后端全链路。

---

### ✨ 核心功能

#### 图片生成
- **15 张模板**：5 张主图（800×800）+ 10 张详情图（750×1000），覆盖电商全场景
- **商品原始图参考**：上传一张商品原始图，自动切换到 `wanx2.1-t2i-turbo` 模型，通过 `ref_img` 参数实现图生图
- **4 种出图模型**：通义万相（云端·电商推荐）、DALL·E 3（云端）、Ollama SDXL / Flux（本地离线）
- **Prompt 4 层拼装**：System 全局约束 + Product 商品参数 + Reference 参考图说明 + Scene 单图场景

#### 类型化配置
- 每个商品类型独立维护白名单（标题/材质/规格/颜色/卖点）
- 5 + 10 个场景模板的中文场景说明 + 英文 Prompt
- 类目专属 System Prompt
- JSON 导入/导出全量配置

#### 中文填写 + 自动翻译
- 配置中心填中文场景说明
- 系统调用 Ollama gemma3 自动翻译为英文 Prompt
- 支持单条翻译 + 批量翻译

#### 前端体验
- Vue 3 + TypeScript + Element Plus 工程化前端
- 左右分栏响应式布局（参数表单 + 结果画廊）
- 模板卡片可视化编辑（点击编辑 Prompt / 同步后台 / 重置默认）
- 素材库 localStorage 持久化 + ZIP 打包下载
- 模型配置弹窗（API Key 在线配置）

#### Dry-Run 模式
- 零成本验证 Prompt 拼装逻辑
- 仅输出 Prompt + 占位图，不调用 API

---

### 🏗️ 技术架构

- **后端**：FastAPI + Pydantic v2 + dashscope SDK + Pillow + Ollama
- **前端**：Vue 3.4 + Vite 5 + TypeScript 5 + Element Plus 2.8 + Pinia 2
- **状态管理**：Pinia 三模块（generation / types / material）
- **API 设计**：异步任务 + 轮询状态 + RESTful 风格

---

### 📝 开发日志

**2026-08-07**：项目启动，一天内完成：
1. 后端四层架构（config / image_client / prompt_builder / main）
2. FastAPI Web 服务 + 15 张模板批量生成
3. Vue 3 工程化前端 + Element Plus
4. 类型化配置中心（`/#/admin`）+ 白名单校验
5. 中→英自动翻译（Ollama gemma3）
6. 通义万相 API Key 在线配置 + ModelConfig 运行时刷新
7. 商品原始图上传 + 图生图流程打通
8. 模板卡片可视化编辑 + Prompt 同步后台

---

## License

MIT
