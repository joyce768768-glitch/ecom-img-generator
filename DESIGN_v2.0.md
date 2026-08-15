# ecom-image-generator v2.0 架构设计文档

> 1688 电商主图 & 详情图 AI 生成 + 自动评测平台

**版本**：v2.0（设计稿）  
**基于**：v1.1.0（已上线 imageedit 图生图）  
**日期**：2026-08-09

---

## 0. 设计目标

| 目标 | 说明 |
|---|---|
| **文生图接口** | 无参考图，纯 prompt 生成（`wan2.6-t2i`） |
| **图生图接口** | 有参考图，保持商品主体改背景（`wan2.7-image` 图像编辑） |
| **两者都接入 VL 评测** | 文生图查主体完整 + prompt 遵从；图生图额外查外形锁定 |
| **性能埋点** | 全链路 trace_id，生图/评测耗时、成功率、成本可追踪 |
| **后台评测指标看板** | 合格率、缺陷分布、性能 P95、人工校准回流 |

---

## 1. 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue3)                           │
│   生成工作台  │  评测看板  │  配置中心  │  素材库             │
└──────────┬──────────────────┬───────────────────────────────┘
           │                  │
┌──────────▼──────────────────▼───────────────────────────────┐
│                    FastAPI 后端                              │
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │
│  │ 生图服务     │   │ 评测服务     │   │ 看板/埋点服务    │   │
│  │             │   │ (Judge)     │   │                 │   │
│  │ /text2img   │   │ /eval/image │   │ /dashboard      │   │
│  │ /image2img  │   │             │   │ /metrics        │   │
│  │ /generate   │   │             │   │                 │   │
│  └──────┬──────┘   └──────┬──────┘   └────────┬────────┘   │
│         │                 │                   │            │
│         ▼                 ▼                   ▼            │
│  ┌───────────┐     ┌───────────┐      ┌──────────────┐     │
│  │ wan2.6-t2i│     │qwen3-vl-  │      │   SQLite     │     │
│  │ wan2.7-   │     │  plus     │      │ 任务/评测/埋点│     │
│  │ image     │     │           │      │              │     │
│  └─────┬─────┘     └─────┬─────┘      └──────────────┘     │
│        └──────── 共用 DASHSCOPE_API_KEY ────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**核心原则**：
- 生图服务与评测服务**完全独立**，只是复用同一个 API Key 鉴权
- 生图服务内部按「有无参考图」分发到文生图 / 图生图两个模型
- 评测服务用 `is_img2img` 开关切换校验规则，**一套模板覆盖两种任务**
- 全链路 `trace_id` 贯穿生图 → 评测 → 看板

---

## 2. 模型选型（修正版）

> ⚠️ v2.0 草案原设想「wan2.6-t2i + denoise 做图生图」**不可行**——wan2.6-t2i 是纯文生图模型，无参考图入参、无 denoise 参数。本设计已修正。

| 用途 | 模型 | 调用地址 | 机制 |
|---|---|---|---|
| 文生图 | `wan2.6-t2i` | `/services/aigc/multimodal-generation/generation` | 纯 prompt 生成，HTTP 同步 |
| 图生图 | `wan2.7-image` | 同上（model 字段不同） | messages content 传 image + text + `strength`，图像编辑保形 |
| 评测 | `qwen3-vl-plus` | `/compatible-mode/v1/chat/completions` | VL 多模态打分，强制 JSON 输出 |

**为什么不是同一模型**：
- `wan2.6-t2i` 生来只接收 prompt，不保形（v1.0.0 踩过坑：ref_img 仅风格参考）
- 图生图保形必须用图像编辑模型（`wan2.7-image`），靠 messages 传参考图 + `strength` 控制重绘幅度
- `wan2.7-image-pro` 支持 4K，可作为高配选项

**strength 参数说明**（替代原方案的 denoise）：
- `strength` 越大，重绘幅度越大（越偏离原图）
- 电商保形约束：`strength ≤ 0.5`（重绘不超过一半）
- 与前端 `ref_strength` 的转换：`strength = 1 - ref_strength`（ref_strength 越大越接近原图）

---

## 3. 生图服务接口设计

### 3.1 业务接口 A：文生图

**路由**：`POST /api/image/text2img`

```json
{
  "prompt": "电商商品主图，白色手持迷你小风扇，纯白背景，45度斜侧视角...",
  "negative_prompt": "扭曲变形，残缺零件，水印，杂乱背景",
  "size": "1280*1280",
  "watermark": false,
  "trace_id": "trace_xxx"
}
```

**响应**：
```json
{
  "trace_id": "trace_xxx",
  "image_url": "https://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/xxx.png",
  "model": "wan2.6-t2i",
  "duration_ms": 8200,
  "is_img2img": false
}
```

**调用底层**：`wan2.6-t2i`，无参考图、无 strength。

---

### 3.2 业务接口 B：图生图

**路由**：`POST /api/image/image2img`

```json
{
  "prompt": "基于原图保留手持小风扇完整外形不变，转电商主图，纯白背景...",
  "negative_prompt": "改变产品外形，扭曲手柄，变形扇叶，水印",
  "reference_image_url": "data:image/png;base64,...",
  "strength": 0.42,
  "size": "1280*1280",
  "watermark": false,
  "trace_id": "trace_yyy"
}
```

**响应**：同文生图，`is_img2img: true`。

**调用底层**：`wan2.7-image`，messages content 传 image + text，`strength` 控制重绘。

**strength 默认值**：
- 主图：0.42（平衡保形与净化背景）
- 详情图：0.30（微调，更贴近原图）
- 硬约束：`strength ≤ 0.5`，超过则请求拒绝（防篡改实物外形）

---

### 3.3 批量入口（兼容当前 v1.1.0 前端）

**路由**：`POST /api/generate`（保留，前端无感）

内部逻辑：
```
for each scene in selected_templates:
    if original_image:
        调用 image2img（strength 按 main/detail 取默认）
    else:
        调用 text2img
    埋点记录 trace_id / gen_prompt / is_img2img / duration
    异步队列推送评测任务
```

---

## 4. 评测服务接口设计

### 4.1 评测路由

**路由**：`POST /api/eval/image`

**入参**（三个必传）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `gen_prompt` | string | 本次生图的完整 prompt（动态传入） |
| `generated_img_url` | string | 生成图 URL |
| `is_img2img` | bool | **关键开关**：true=图生图（开启外形锁定校验），false=文生图 |

**可选**：
- `reference_img_url`：图生图任务传原图，便于 VL 对比外形（增强校验）
- `eval_mode`：`full` / `sample` / `off`（默认 `sample`）

---

### 4.2 评测 Judge 系统提示词（一套模板 + 开关）

```
# 评测任务
参照下方绘图指令评判商品图片，只输出标准 JSON 对象，禁止输出任何额外解释文字。

绘图指令：{gen_prompt}
{extra_rule}

# 评判维度
1. subject_score：0-1 浮点值。
   - 文生图：核查主体是否完整、无残缺。
   - 图生图：额外核查产品外形没有发生非允许改动（轮廓/零件布局与原图一致）。
2. prompt_fit_score：0-1 浮点值。核查背景、视角、布光、风格是否匹配绘图指令。
3. has_defect：布尔值。存在畸形部件/残缺零件/多余异物/水印/乱码文字/大面积污渍→true；无→false。
4. defect_type：字符串（仅 has_defect=true 时填）。可选：deformed / missing_part / extra_object / watermark / garbled_text / stain / other。
5. pass_ecommerce：布尔值。综合判定是否可直接上架。
   - 量化阈值：缺陷面积 <5% 且 subject_score≥0.85 且 prompt_fit_score≥0.8 → true
   - 外形篡改 / 严重畸形 has_defect=true → false

# 输出格式
{
  "subject_score": 0.0,
  "prompt_fit_score": 0.0,
  "has_defect": false,
  "defect_type": "",
  "pass_ecommerce": false
}
```

**开关渲染**（统一用字符串拼接，不用 Handlebars）：
```python
extra_rule = ""
if is_img2img:
    extra_rule = "【强制规则：当前为图生图任务，原始产品外形、关键结构必须完整保留，"
                 "不得擅自修改产品轮廓、零件布局；仅允许调整背景、光影、画质。】"
```

**调用参数**：`response_format={"type": "json_object"}` 强制 JSON 输出。

---

### 4.3 评测稳定性策略

| 策略 | 说明 |
|---|---|
| 多次评测取均 | 关键图评测 2-3 次，subject_score/prompt_fit_score 取均值，pass_ecommerce 多数表决 |
| 量化阈值 | pass_ecommerce 不靠 VL 主观判断，用缺陷面积 + 分数阈值硬约束 |
| 失败放行 | 评测失败默认**放行 + 标记 pending_manual**，不阻塞生图主流程（图已花钱生成） |
| 抽样模式 | 默认 `sample`（每商品评 3 张主图），上架前切 `full` |

---

## 5. 数据库设计（SQLite）

> v1.x 用 JSON 文件 + localStorage；v2.0 引入评测/看板/埋点，需要频繁写，引入 SQLite（单文件，零运维，适合当前规模）。

### 5.1 任务表 `gen_tasks`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 任务 ID |
| trace_id | TEXT | 全链路追踪 ID（生图+评测共用） |
| type_id | TEXT | 商品类型 ID |
| scene_key | TEXT | main_1 / detail_3 等 |
| size_type | TEXT | main / detail |
| is_img2img | BOOL | 文生图 / 图生图 |
| gen_model | TEXT | wan2.6-t2i / wan2.7-image |
| gen_prompt | TEXT | 完整生图 prompt |
| negative_prompt | TEXT | 负面词 |
| reference_img_url | TEXT | 参考图（图生图） |
| strength | REAL | 重绘强度（图生图） |
| generated_img_url | TEXT | 生成图 URL |
| gen_start_time | REAL | 生图开始时间戳 |
| gen_end_time | REAL | 生图结束时间戳 |
| gen_duration_ms | INT | 生图耗时 |
| gen_success | BOOL | 生图是否成功 |
| gen_error | TEXT | 错误信息 |
| image_size | TEXT | 1280*1280 |
| created_at | REAL | 创建时间 |

### 5.2 评测结果表 `eval_results`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | TEXT PK | 评测 ID |
| trace_id | TEXT | 关联 gen_tasks.trace_id |
| eval_model | TEXT | qwen3-vl-plus |
| subject_score | REAL | 主体完整性 0-1 |
| prompt_fit_score | REAL | prompt 遵从度 0-1 |
| has_defect | BOOL | 是否有缺陷 |
| defect_type | TEXT | 缺陷类型 |
| pass_ecommerce | BOOL | 是否可上架 |
| eval_count | INT | 评测次数（多次取均） |
| eval_start_time | REAL | 评测开始 |
| eval_end_time | REAL | 评测结束 |
| eval_duration_ms | INT | 评测耗时 |
| eval_success | BOOL | 评测是否成功 |
| eval_error | TEXT | 错误信息 |
| manual_override | BOOL | 人工是否 override |
| manual_pass | BOOL | 人工判定结果（override 时填） |
| created_at | REAL | 创建时间 |

### 5.3 埋点性能表 `perf_metrics`（聚合视图，从上两表汇总）

> 看板直接查的视图，按 trace_id / 日期 / 模型 聚合。

核心埋点字段：
- `trace_id` 链路
- 生图：`gen_duration_ms` / `gen_success` / `gen_model`
- 评测：`eval_duration_ms` / `eval_success` / `eval_model`
- 成本：`image_count` / `token_usage`（VL 评测 token）

---

## 6. 性能埋点设计

### 6.1 trace_id 链路

```
前端生成请求 → 后端生成 trace_id
  → 生图调用（埋点 gen_*）
  → 评测队列（复用 trace_id）
  → 评测调用（埋点 eval_*）
  → 看板（按 trace_id 串联）
```

### 6.2 埋点指标清单

| 类别 | 指标 | 来源 |
|---|---|---|
| **生图性能** | 生图平均耗时 / P95 耗时 | gen_duration_ms |
| | 生图成功率 | gen_success |
| | 文生图 vs 图生图耗时对比 | is_img2img 分组 |
| **评测性能** | 评测平均耗时 / P95 耗时 | eval_duration_ms |
| | 评测成功率 | eval_success |
| | 评测重试次数 | eval_count |
| **质量** | 合格率（pass_ecommerce=true 占比） | eval_results |
| | 各维度均分 | subject_score / prompt_fit_score |
| | 缺陷率 / 缺陷类型分布 | has_defect / defect_type |
| | 文生图 vs 图生图合格率对比 | is_img2img 分组 |
| **成本** | 日生图张数 | COUNT(gen_tasks) |
| | 日评测次数 / token 消耗 | eval_results |
| **人工** | 人工 override 率 | manual_override |
| | VL 与人工一致率 | manual_pass vs pass_ecommerce |

---

## 7. 后台评测指标看板

**路由**：`GET /api/dashboard`（聚合查询）

### 7.1 看板模块

| 模块 | 展示内容 |
|---|---|
| **合格率总览** | 今日/本周 pass_ecommerce 占比，文生图 vs 图生图对比 |
| **维度雷达** | subject_score / prompt_fit_score 均分趋势 |
| **缺陷分析** | has_defect 率 + defect_type 饼图（deformed/missing_part/...） |
| **性能监控** | 生图/评测 P95 耗时折线，成功率 |
| **模型对比** | wan2.6-t2i vs wan2.7-image 合格率/耗时对比 |
| **成本统计** | 日生图张数、评测 token 消耗、估算费用 |
| **人工校准** | override 率、VL 误判样本列表（供迭代评测 prompt） |

### 7.2 看板查询维度

- 时间：今日 / 7 日 / 30 日 / 自定义
- 类型：按 type_id（衣架/小风扇/...）
- 模式：文生图 / 图生图 / 全部
- 模型：wan2.6-t2i / wan2.7-image

---

## 8. 完整调用时序

### 8.1 文生图 + 评测

```
1. 前端 POST /api/image/text2img { prompt, ... }
2. 后端生成 trace_id，调用 wan2.6-t2i → 拿到 image_url
3. 埋点写入 gen_tasks（is_img2img=false, gen_duration_ms）
4. 异步队列推送评测任务 { gen_prompt, image_url, is_img2img=false }
5. 评测服务填充模板（不开启外形锁定规则）
6. 调用 qwen3-vl-plus，强制 JSON → 打分
7. 埋点写入 eval_results
8. 看板自动聚合统计
```

### 8.2 图生图 + 评测

```
1. 前端 POST /api/image/image2img { prompt, reference_image_url, strength, ... }
2. 后端生成 trace_id，调用 wan2.7-image（messages 传 image+text+strength）→ image_url
3. 埋点写入 gen_tasks（is_img2img=true, strength, gen_duration_ms）
4. 异步队列推送评测 { gen_prompt, image_url, is_img2img=true, reference_img_url }
5. 评测服务填充模板（开启外形锁定强制规则）
6. 调用 qwen3-vl-plus → 打分（subject_score 额外校验外形）
7. 埋点写入 eval_results
8. 看板聚合
```

### 8.3 评测失败处理

```
评测超时/异常 → eval_success=false, eval_error=...
生成图默认放行 + 标记 pending_manual
看板「待人工评测」列表展示，人工补评
```

---

## 9. 配置管理

### 9.1 生图配置（存数据库 `gen_config`）

| 字段 | 默认值 |
|---|---|
| generate_base_url | https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation |
| text2img_model_id | wan2.6-t2i |
| image2img_model_id | wan2.7-image |
| api_key | sk-xxxx（全局共用） |
| text2img_default_prompt | （按类目配置） |
| text2img_neg_prompt | 扭曲变形，残缺零件，多余部件... |
| image2img_default_prompt | 基于原图保留外形不变... |
| image2img_neg_prompt | 改变产品外形，扭曲手柄... |
| default_strength_main | 0.42 |
| default_strength_detail | 0.30 |
| max_strength | 0.5（硬约束） |
| default_image_size | 1280*1280 |
| watermark_switch | false |

### 9.2 评测配置（存数据库 `eval_config`）

| 字段 | 默认值 |
|---|---|
| eval_base_url | https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions |
| eval_model_id | qwen3-vl-plus |
| eval_system_prompt_template | （见 4.2） |
| eval_mode | sample |
| eval_repeat_count | 2（关键图评测次数） |
| subject_score_threshold | 0.85 |
| prompt_fit_score_threshold | 0.80 |
| defect_area_threshold | 0.05 |

> api_key 不单独存，全局共用生图密钥。

### 9.3 配置分层原则

| 层 | 存储 | 理由 |
|---|---|---|
| 生图/评测参数 | 数据库 | 运行时可调，看板需要 |
| 类目 prompt 模板 | type_configs.json（保留 v1.x） | 低频改，配置中心已完善 |
| 任务/评测/埋点数据 | 数据库 | 频繁写，看板查询 |

---

## 10. 落地分阶段

### Phase 1｜模型升级 + 数据库基建（低风险）
- `wanx2.1-imageedit` → `wan2.7-image`（图生图），文生图接 `wan2.6-t2i`
- 引入 SQLite，建 gen_tasks / eval_results 表
- 生图埋点接入（trace_id + gen_*）
- 同参考图对比新旧模型保形效果

### Phase 2｜评测 Judge 模块（核心价值）
- 接 `qwen3-vl-plus`，实现 /api/eval/image
- 评测模板 + is_img2img 开关
- 默认抽样评测（每商品 3 张主图）
- 验证 VL 打分稳定性（同图评 2 次看波动），调稳 prompt
- eval_results 入库

### Phase 3｜看板 + 全量评测 + 校准回流
- /api/dashboard 聚合查询 + 前端看板页
- 评测切全量模式
- 人工 override 记录 + VL 误判分析
- 性能 P95 / 成本统计
- 迭代评测 prompt

---

## 11. 关键决策备忘

| 决策 | 结论 | 理由 |
|---|---|---|
| 图生图模型 | wan2.7-image（非 wan2.6-t2i+denoise） | t2i 纯文生图不保形，必须图像编辑模型 |
| 重绘参数 | strength（非 denoise） | dashscope 实际参数名，strength≤0.5 保形 |
| 评测模型 | qwen3-vl-plus（非 qwen3-vl-max） | max 版本官方未确认，plus 为当前 VL 最强 |
| 评测模板 | 一套 + is_img2img 开关 | 避免维护两套 prompt |
| 模板渲染 | 字符串拼接（非 Handlebars） | 与代码一致，配置存占位符 |
| 数据库 | SQLite | 单文件零运维，适合当前规模 |
| 评测失败 | 放行 + 待人工 | 不阻塞主流程，不浪费已生成图 |
| pass_ecommerce | 量化阈值 | 不靠 VL 主观，缺陷面积+分数硬约束 |

---

*设计稿，待评审。基于 v1.1.0 已验证的 imageedit 思路演进。*
