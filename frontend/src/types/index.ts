/**
 * types/index.ts - 全局 TS 类型定义（严格模式，拒绝 any）
 * 覆盖：商品参数 / 模板 / 模型 / 类型配置(新增) / 生成状态 / 素材库 / 接口响应
 */

// ------------------------------
// 0. 基础：Type 类型配置（核心新增，配置中心编辑）
// ------------------------------
/** 单条场景配置：一张主图 / 详情图的 Prompt */
export interface SceneItem {
  key: string              // main_1 / detail_3
  scene_cn: string         // 中文展示（配置中心编辑）
  scene_en: string         // 英文Prompt（实际生成用）
  size: 'main' | 'detail'  // 对应尺寸常量
}

/** 类型 - 列表简版（用于顶部选择器 / 配置中心列表） */
export interface TypeSlim {
  type_id: string
  type_name: string
  default_title: string
  main_count: number
  detail_count: number
  titles_count: number
  materials_count: number
  specs_count: number
  colors_count: number
  features_count: number
  has_system_extra: boolean
  created_at: number
  updated_at: number
}

/** 类型 - 完整详情版（用于选中后填充表单 / 配置中心Tab编辑） */
export interface TypeFull {
  type_id: string
  type_name: string
  default_title: string
  titles: string[]
  materials: string[]
  specs: string[]
  colors: string[]
  features: string[]
  default_selected_features: string[]
  system_extra_prompt: string
  main_scenes: SceneItem[]   // 5条，有序
  detail_scenes: SceneItem[] // 10条，有序
  created_at: number
  updated_at: number
}

/** 新建 / 更新 请求体（前端提交） */
export interface TypePayload {
  type_id?: string
  type_name: string
  default_title?: string
  titles?: string[]
  materials?: string[]
  specs?: string[]
  colors?: string[]
  features?: string[]
  default_selected_features?: string[]
  system_extra_prompt?: string
  main_scenes?: SceneItem[]
  detail_scenes?: SceneItem[]
}

export interface ImportModeOptions {
  mode: 'merge' | 'replace'
  file?: File
  data?: { types: TypeFull[]; version: number; exported_at?: number }
}

// ------------------------------
// 1. 商品（基于 TypeFull 的白名单）
// ------------------------------
export interface WhitelistConfig {
  titles: string[]
  materials: string[]
  specs: string[]
  colors: string[]
  features: string[]
}

export interface ProductForm {
  title: string
  material: string
  spec: string
  color: string
  features: string[]
}

// ------------------------------
// 2. 绘图模型 & 15张图模板（模板从选中 Type 动态产出）
// ------------------------------
export type ModelType = 'cloud' | 'local'

export interface ModelOption {
  value: string          // 后端 ImageModel 枚举值
  label: string
  type: ModelType
}

export type TemplateGroup = 'main' | 'detail'

export interface ImageTemplate {
  key: string            // main_1..5 / detail_1..10
  group: TemplateGroup
  size: [number, number] // [宽, 高]
  scene_cn: string       // 中文场景描述
  scene_en: string       // 英文场景短句（传给模型）
  selected: boolean      // 是否选中生成（前端态）
}

// ------------------------------
// 3. 生成任务 / 状态 / 日志
// ------------------------------
export type TaskStatus = 'pending' | 'running' | 'done'

export interface TaskLogEntry {
  ts: number
  level: 'INFO' | 'WARN' | 'ERROR'
  message: string
}

export interface TaskStatusResp {
  task_id: string
  type_id: string
  type_name: string
  status: TaskStatus
  model: string
  dry_run: boolean
  total: number
  done: number
  failed: number
  current_key: string | null
  elapsed: number
  logs_since_next: number
  logs: TaskLogEntry[]
}

// ------------------------------
// 4. 生成图片结果
// ------------------------------
export interface GeneratedImage {
  file: string           // 文件名，如 main_1.png
  key: string            // 场景key，如 main_1
  size_kb: number
  url: string            // 相对URL如 /output/main_1.png
  deleted?: boolean      // 前端态：用户手动删除标记
}

export interface TaskResultResp {
  task_id: string
  type_id: string
  type_name: string
  status: TaskStatus
  output_dir: string
  generated: GeneratedImage[]
}

// ------------------------------
// 5. 前端配置接口聚合响应 /api/config
// ------------------------------
export interface AppConfigResp {
  models: ModelOption[]
  default_model: string
  types: TypeSlim[]
  sizes: Record<string, [number, number]>  // { main: [800,800], detail: [750,1000] }
  negative_base: string
  message: string
  api_keys: {
    dashscope_configured: boolean
    openai_configured: boolean
    ollama_configured: boolean
  }
}

// ------------------------------
// 6. 生成请求体 POST /api/generate（强制 type_id）
// ------------------------------
export interface GenerateReqBody {
  type_id: string
  model: string
  only_keys: string[]
  dry_run: boolean
  extra_negative: string
  product: ProductForm
  original_image?: string
  ref_strength?: number
}

export interface GenerateResp {
  task_id: string
  type_id: string
  type_name: string
  message: string
}

// ------------------------------
// 7. 素材库（localStorage 持久化，带 type_id 便于回填）
// ------------------------------
export interface MaterialRecord {
  id: string
  name: string                 // 素材名（用户可改，默认=标题前20字+时间）
  createdAt: number
  type_id: string              // ★ 核心新增：所属类型
  type_name: string            // 冗余快照：类型名
  product: ProductForm
  model: string
  dry_run: boolean
  generated: GeneratedImage[]
  used_keys: string[]          // 本次勾选了哪些key
}

// ------------------------------
// 8. 模型配置弹窗
// ------------------------------
export interface ModelConfigUI {
  currentModel: string
  tips: string                 // 提示文案
  negativePrompt: string       // 用户自定义负面词（追加到 negative_base）
}

// ------------------------------
// 9. 通用工具：下载/打包任务上下文
// ------------------------------
export interface DownloadAllContext {
  taskId: string
  images: GeneratedImage[]
  packaging: boolean
  progress: number
}
