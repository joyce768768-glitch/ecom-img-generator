# E-Commerce Image Generator

> 1688 电商主图 & 详情图 AI 批量生成工具 — 上传商品原始图，一键生成 5 张主图 + 10 张详情图

**项目开始时间**：2026-08-07  
**当前版本**：v1.0.0  
**许可证**：MIT

---

## 功能概览

| 功能 | 说明 |
|------|------|
| **15 张模板批量生成** | 5 张主图（800×800）+ 10 张详情图（750×1000），覆盖电商全场景 |
| **商品原始图参考** | 上传一张商品原始图，AI 基于参考图生成所有场景图，保持商品一致性 |
| **类型化配置** | 每个商品类型（如衣架、收纳盒）独立维护白名单、场景模板、System Prompt |
| **中文填写 + 自动翻译** | 配置中心填中文场景说明，系统调用 Ollama gemma3 自动翻译为英文 Prompt |
| **双模出图** | 云端（通义万相 / DALL·E 3）或本地（Ollama SDXL / Flux）自由切换 |
| **Prompt 可视化编辑** | 每张图支持单独编辑场景 Prompt，可同步到后台配置或重置为默认值 |
| **素材库管理** | 前端 localStorage 持久化，支持删除恢复、全部打包 ZIP 下载 |
| **Dry-Run 零成本验证** | 不调用 API，仅输出 Prompt + 占位图，快速验证 Prompt 拼装逻辑 |

---

## 技术栈

### 后端（Python）
- **FastAPI** — Web API 服务，支持异步任务轮询
- **Pydantic v2** — 请求/响应严格类型校验
- **dashscope SDK** — 通义万相图生图（wanx2.1-t2i-turbo + ref_img）
- **Pillow** — 图片下载、resize、强制归正到 1688 规范尺寸
- **Ollama** — 本地翻译（gemma3）+ 本地出图（SDXL / Flux）

### 前端（Vue 3 + TypeScript）
- **Vue 3.4** + **Vite 5** + **TypeScript 5**
- **Element Plus 2.8** — UI 组件库
- **Pinia 2** — 状态管理（generation / types / material 三模块）
- **JSZip + file-saver** — 批量打包下载

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue3 + TS)                      │
│  HomePage（工作台）  AdminPage（配置中心）  ProductListPage│
│         ProductForm │ PromptPreview │ ImageCard          │
│              Pinia Store (generation/types/material)     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP API (/api/*)
┌──────────────────────┴──────────────────────────────────┐
│                   后端 (FastAPI + Python)                 │
│  server.py      — API 路由 + 任务调度 + 轮询状态           │
│  prompt_builder — 4层 Prompt 拼装 (System/Product/Ref/Scene)│
│  image_client   — 工厂模式，4 种模型客户端自由切换         │
│  config.py      — .env 加载 + ModelConfig 运行时刷新       │
│  translator.py  — Ollama gemma3 中→英翻译                 │
│  type_configs   — 类型化 JSON 配置（白名单/场景/默认值）    │
└─────────────────────────────────────────────────────────┘
```

### 四层 Prompt 拼装

```
[SYSTEM]    1688 B2B 电商摄影风格全局约束 + 类目专属 System Prompt
[PRODUCT]   商品标题 / 材质 / 规格 / 颜色 / 核心卖点
[REFERENCE] 参考图说明（有上传时）— 保持商品外观一致性
[SCENE]     单图场景英文 Prompt（如 "White background studio shot..."）
```

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/你的用户名/ecom-image-generator.git
cd ecom-image-generator
```

### 2. 后端配置

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入通义万相 API Key
# DASHSCOPE_API_KEY=sk-你的密钥
```

获取通义万相 API Key：https://dashscope.console.aliyun.com/apiKey

### 3. 前端配置

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 终端1：启动后端（默认 8000 端口）
cd ecom-image-generator
python3 server.py

# 终端2：启动前端（默认 5173 端口）
cd frontend
npm run dev
```

### 5. 使用

1. 打开 http://127.0.0.1:5173
2. 顶部选择商品类型
3. 上传商品原始图（作为 15 张图的参考）
4. 勾选要生成的模板
5. 点击「批量生成」

---

## 配置中心

访问 `http://127.0.0.1:5173/#/admin` 进入配置中心：

| 配置项 | 说明 |
|--------|------|
| **类型管理** | 新增/编辑/删除商品类型，每个类型独立维护白名单和模板 |
| **主图场景** | 5 张主图的场景说明（中文填写，自动翻译英文） |
| **详情场景** | 10 张详情图的场景说明 |
| **白名单** | 标题/材质/规格/颜色/卖点（禁止手动编造，必须白名单内选） |
| **System Prompt** | 类目专属全局风格约束 |
| **API Key** | 通义万相 / DALL·E 3 密钥在线配置 |
| **导入/导出** | JSON 格式全量配置导入导出 |

---

## 支持的出图模型

| 模型 | 类型 | 模型名 | 参考图 | 说明 |
|------|------|--------|--------|------|
| 通义万相 | 云端 | wanx-v1 | ❌ 文生图 | 电商推荐，画风写实 |
| 通义万相+ | 云端 | wanx2.1-t2i-turbo | ✅ 图生图 | 上传参考图时自动切换，支持 ref_img |
| DALL·E 3 | 云端 | dall-e-3 | ❌ | OpenAI，英文 Prompt 效果佳 |
| Ollama SDXL | 本地 | stable-diffusion | ❌ | 需 4GB+ 显存 |
| Ollama Flux | 本地 | flux | ❌ | 需 8GB+ 显存，本地画质 SOTA |

---

## 项目结构

```
ecom-image-generator/
├── server.py              # FastAPI 后端服务
├── config.py              # 配置管理 + ModelConfig
├── image_client.py        # 图像客户端工厂（4 种模型）
├── prompt_builder.py      # 4 层 Prompt 拼装引擎
├── translator.py          # Ollama 中→英翻译
├── type_configs.py        # 类型配置管理器
├── type_configs.json      # 类型配置数据（白名单/场景/默认值）
├── main.py                # CLI 入口（可脱离前端单独跑）
├── requirements.txt
├── .env.example
├── FLOW.mmd               # Mermaid 业务流程图
│
├── frontend/
│   ├── src/
│   │   ├── components/    # ProductForm, ImageCard, PromptPreview, ...
│   │   ├── views/         # HomePage, AdminPage, ProductListPage
│   │   ├── store/         # Pinia: generation, types, material
│   │   ├── api/           # 后端接口封装
│   │   ├── types/         # TypeScript 类型定义
│   │   ├── styles/        # 全局样式 + SCSS 变量
│   │   └── utils/         # 请求封装 + localStorage
│   ├── vite.config.ts     # Vite 代理配置
│   └── package.json
│
└── output/                # 生成图片输出目录
    ├── main_1.png         # 主图 1
    ├── ...
    ├── detail_1.png       # 详情图 1
    └── _original_ref.png  # 上传的参考图缓存
```

---

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取前端初始化配置（模型列表/尺寸/API Key 状态） |
| POST | `/api/generate` | 启动图片生成任务（异步） |
| GET | `/api/status/{task_id}` | 轮询任务状态 + 日志 |
| GET | `/api/results/{task_id}` | 获取生成结果（图片列表） |
| GET | `/api/types` | 获取所有商品类型 |
| POST | `/api/types` | 创建商品类型 |
| PUT | `/api/types/{id}` | 更新商品类型 |
| DELETE | `/api/types/{id}` | 删除商品类型 |
| POST | `/api/translate` | 中→英翻译（Ollama gemma3） |
| POST | `/api/config/api-keys` | 在线保存 API Key |

---

## 开发说明

### 前端开发

```bash
cd frontend
npm run dev      # 开发模式（HMR 热更新）
npm run build    # 生产构建
```

### 后端开发

```bash
python3 server.py          # 启动 Web 服务（8000 端口）
python3 main.py --dry-run  # CLI 模式，仅打印 Prompt 不调用 API
```

### 添加新的商品类型

1. 前端访问 `/#/admin` → 点击「新增类型」
2. 填写类型名称、type_id
3. 配置白名单（标题/材质/规格/颜色/卖点）
4. 编辑 5 个主图场景 + 10 个详情场景
5. 点击「批量翻译」自动生成英文 Prompt
6. 保存

---

## License

MIT License — 自由使用、修改、分发。
