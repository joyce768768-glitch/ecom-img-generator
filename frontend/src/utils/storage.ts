/**
 * utils/storage.ts - localStorage 封装（素材库持久化）
 * 严格 TS 类型，key 前缀隔离，JSON 解析带兜底
 */
import type { MaterialRecord } from '@/types'

const KEY_PREFIX = 'img_gen_agent_'

const Keys = {
  MATERIALS: `${KEY_PREFIX}materials`,
  MODEL_PREFERENCE: `${KEY_PREFIX}model_pref`,
  NEGATIVE_PROMPT: `${KEY_PREFIX}negative_prompt`,
} as const

function safeParse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

// ---------- 素材库 ----------
export function loadMaterials(): MaterialRecord[] {
  const raw = localStorage.getItem(Keys.MATERIALS)
  const list = safeParse<MaterialRecord[]>(raw, [])
  // 按创建时间倒序
  return list.sort((a, b) => b.createdAt - a.createdAt)
}

export function saveMaterials(list: MaterialRecord[]): void {
  localStorage.setItem(Keys.MATERIALS, JSON.stringify(list))
}

export function appendMaterial(rec: MaterialRecord): MaterialRecord[] {
  const list = loadMaterials()
  list.unshift(rec)
  // 仅保留最近 50 条，防止 localStorage 爆
  const clipped = list.slice(0, 50)
  saveMaterials(clipped)
  return clipped
}

export function removeMaterial(id: string): MaterialRecord[] {
  const list = loadMaterials().filter((r) => r.id !== id)
  saveMaterials(list)
  return list
}

// ---------- 偏好 ----------
export function loadModelPreference(): string | null {
  return localStorage.getItem(Keys.MODEL_PREFERENCE)
}

export function saveModelPreference(model: string): void {
  localStorage.setItem(Keys.MODEL_PREFERENCE, model)
}

export function loadNegativePrompt(): string | null {
  return localStorage.getItem(Keys.NEGATIVE_PROMPT)
}

export function saveNegativePrompt(text: string): void {
  localStorage.setItem(Keys.NEGATIVE_PROMPT, text)
}
