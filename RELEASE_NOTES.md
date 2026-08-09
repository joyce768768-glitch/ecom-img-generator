# Release v1.0.0 — 首个正式版

**发布日期**：2026-08-08  
**项目起始**：2026-08-07

---

## 🎉 里程碑

从零到一，一天内完成完整的电商主图/详情图 AI 生成工具，覆盖前后端全链路。

---

## ✨ 核心功能

### 图片生成
- **15 张模板**：5 张主图（800×800）+ 10 张详情图（750×1000），覆盖电商全场景
- **商品原始图参考**：上传一张商品原始图，自动切换到 `wanx2.1-t2i-turbo` 模型，通过 `ref_img` 参数实现图生图
- **4 种出图模型**：通义万相（云端·电商推荐）、DALL·E 3（云端）、Ollama SDXL / Flux（本地离线）
- **Prompt 4 层拼装**：System 全局约束 + Product 商品参数 + Reference 参考图说明 + Scene 单图场景

### 类型化配置
- 每个商品类型独立维护白名单（标题/材质/规格/颜色/卖点）
- 5 + 10 个场景模板的中文场景说明 + 英文 Prompt
- 类目专属 System Prompt
- JSON 导入/导出全量配置

### 中文填写 + 自动翻译
- 配置中心填中文场景说明
- 系统调用 Ollama gemma3 自动翻译为英文 Prompt
- 支持单条翻译 + 批量翻译

### 前端体验
- Vue 3 + TypeScript + Element Plus 工程化前端
- 左右分栏响应式布局（参数表单 + 结果画廊）
- 模板卡片可视化编辑（点击编辑 Prompt / 同步后台 / 重置默认）
- 素材库 localStorage 持久化 + ZIP 打包下载
- 模型配置弹窗（API Key 在线配置）

### Dry-Run 模式
- 零成本验证 Prompt 拼装逻辑
- 仅输出 Prompt + 占位图，不调用 API

---

## 🏗️ 技术架构

- **后端**：FastAPI + Pydantic v2 + dashscope SDK + Pillow + Ollama
- **前端**：Vue 3.4 + Vite 5 + TypeScript 5 + Element Plus 2.8 + Pinia 2
- **状态管理**：Pinia 三模块（generation / types / material）
- **API 设计**：异步任务 + 轮询状态 + RESTful 风格

---

## 📦 安装

```bash
# 后端
pip install -r requirements.txt
cp .env.example .env  # 填入 DASHSCOPE_API_KEY

# 前端
cd frontend && npm install

# 启动
python3 server.py     # 后端 :8000
npm run dev           # 前端 :5173
```

---

## 🔑 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 通义万相 API Key | 必填 |
| `DEFAULT_IMAGE_MODEL` | 默认出图模型 | `ollama_sdxl` |
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://127.0.0.1:11434` |
| `OPENAI_API_KEY` | DALL·E 3 API Key | 可选 |

---

## ⚠️ 已知限制

- 通义万相 `wanx-v1` 不支持图生图，需上传参考图后自动切换到 `wanx2.1-t2i-turbo`
- `ref_img` 为风格参考模式，商品外观一致性取决于 `ref_strength` 参数
- Ollama 本地出图需要 GPU 显存（SDXL 4GB+ / Flux 8GB+）
- 素材库使用 localStorage，上限 50 条

---

## 📝 开发日志

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
