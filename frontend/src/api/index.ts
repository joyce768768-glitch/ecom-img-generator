/**
 * api/index.ts - 后端接口统一封装（严格 TS 入参出参）
 */
import { httpGet, httpPost, httpPut, httpDelete, httpUpload } from '@/utils/request'
import type {
  AppConfigResp,
  GenerateReqBody,
  GenerateResp,
  TaskResultResp,
  TaskStatusResp,
  TypeFull,
  TypePayload,
  TypeSlim,
} from '@/types'

// ==============================
// 1. 基础：配置 / 生成 / 结果
// ==============================
/** 1.1 获取前端初始化配置（模型列表/类型简版/尺寸常量/基础负面词） */
export function fetchAppConfig(): Promise<AppConfigResp> {
  return httpGet<AppConfigResp>('/api/config')
}

/** 1.2 触发异步生成任务（强制：body.type_id 必填） */
export function startGeneration(body: GenerateReqBody): Promise<GenerateResp> {
  return httpPost<GenerateResp>('/api/generate', body)
}

/** 1.3 轮询任务进度（logs_since 增量日志，减少传输） */
export function pollTaskStatus(
  taskId: string,
  logsSince?: number,
): Promise<TaskStatusResp> {
  const params: Record<string, number> = {}
  if (typeof logsSince === 'number') params.logs_since = logsSince
  return httpGet<TaskStatusResp>(`/api/status/${taskId}`, { params })
}

/** 1.4 获取已生成图片清单 */
export function fetchTaskResults(taskId: string): Promise<TaskResultResp> {
  return httpGet<TaskResultResp>(`/api/results/${taskId}`)
}

// ==============================
// 2. 类型管理（配置中心 CRUD + 导入导出）
// ==============================
export interface TypeListResp {
  items: TypeSlim[]
  total: number
}

/** 2.1 类型列表（默认简版） */
export function fetchTypeList(slim = true): Promise<TypeListResp> {
  return httpGet<TypeListResp>('/api/types', { params: { slim } })
}

/** 2.2 类型详情（完整：白名单 + 15场景） */
export function fetchTypeDetail(typeId: string): Promise<TypeFull> {
  return httpGet<TypeFull>(`/api/types/${typeId}`)
}

/** 2.3 新建类型 */
export function createType(payload: TypePayload): Promise<{ ok: boolean; item: TypeFull }> {
  return httpPost<{ ok: boolean; item: TypeFull }>('/api/types', payload)
}

/** 2.4 更新类型（支持部分字段） */
export function updateType(
  typeId: string,
  payload: Partial<TypePayload> & { type_name?: string },
): Promise<{ ok: boolean; item: TypeFull }> {
  return httpPut<{ ok: boolean; item: TypeFull }>(`/api/types/${typeId}`, payload)
}

/** 2.5 删除类型 */
export function deleteType(typeId: string): Promise<{ ok: boolean; types: TypeSlim[] }> {
  return httpDelete<{ ok: boolean; types: TypeSlim[] }>(`/api/types/${typeId}`)
}

/** 2.6 复制类型（基于现有快速改出新类目） */
export function duplicateType(
  srcTypeId: string,
  newTypeName: string,
  newTypeId?: string,
): Promise<{ ok: boolean; item: TypeFull }> {
  return httpPost<{ ok: boolean; item: TypeFull }>(`/api/types/${srcTypeId}/duplicate`, {
    new_type_name: newTypeName,
    new_type_id: newTypeId,
  })
}

/** 2.7 导出所有类型（浏览器触发下载 JSON 文件） */
export async function exportTypesToFile(): Promise<void> {
  const resp = await fetch('/api/types/export', { method: 'GET' })
  if (!resp.ok) throw new Error(`导出失败 HTTP ${resp.status}`)
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const disp = resp.headers.get('Content-Disposition') || ''
  const match = disp.match(/filename="?([^"]+)"?/)
  const fname = match?.[1] || `type_configs_export_${Date.now()}.json`
  a.href = url
  a.download = fname
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

/** 2.8 导入类型（JSON 上传） */
export function importTypesFromFile(
  file: File,
  mode: 'merge' | 'replace' = 'merge',
): Promise<{ ok: boolean; mode: string; items: TypeSlim[]; total: number }> {
  const form = new FormData()
  form.append('mode', mode)
  form.append('file', file)
  return httpUpload<{ ok: boolean; mode: string; items: TypeSlim[]; total: number }>(
    '/api/types/import-file',
    form,
  )
}

/** 2.9 导入类型（JSON body 直接提交，适合 API 调试） */
export function importTypesByBody(
  data: { types: TypeFull[]; version: number },
  mode: 'merge' | 'replace' = 'merge',
): Promise<{ ok: boolean; mode: string; items: TypeSlim[]; total: number }> {
  return httpPost<{ ok: boolean; mode: string; items: TypeSlim[]; total: number }>(
    '/api/types/import',
    { mode, data },
  )
}

/** 2.10 翻译中文 → 英文（用于 scene_cn → scene_en） */
export function translateZhToEn(zhText: string): Promise<{
  ok: boolean
  zh_text: string
  en_text: string
  translated: boolean
}> {
  return httpPost('/api/translate', { zh_text: zhText })
}

/** 2.11 保存 API Key 到后端 .env 文件 */
export function saveApiKeys(params: {
  dashscope_api_key?: string
  openai_api_key?: string
}): Promise<{
  ok: boolean
  api_keys: {
    dashscope_configured: boolean
    openai_configured: boolean
  }
}> {
  return httpPost('/api/config/api-keys', params)
}
