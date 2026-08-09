/**
 * store/modules/material.ts - 素材库 Pinia Store
 * localStorage 持久化：历史商品配置 + 生成记录 + 一键回填
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import type { MaterialRecord, ProductForm } from '@/types'
import {
  appendMaterial,
  loadMaterials,
  removeMaterial,
  saveMaterials,
} from '@/utils/storage'
import { useGenerationStore } from './generation'

export const useMaterialStore = defineStore('material', () => {
  const records = ref<MaterialRecord[]>([])
  const drawerVisible = ref(false)

  const recordCount = computed<number>(() => records.value.length)

  function refresh(): void {
    records.value = loadMaterials()
  }

  function openDrawer(): void {
    refresh()
    drawerVisible.value = true
  }

  function closeDrawer(): void {
    drawerVisible.value = false
  }

  /** 保存一组新的素材记录（生成完会自动调一次，这里给手动触发） */
  function saveRecord(rec: MaterialRecord): void {
    records.value = appendMaterial(rec)
    ElMessage.success(`已存入素材库：${rec.name.slice(0, 20)}`)
  }

  /** 点击「复用」：把商品参数回填到 generationStore 表单（带 type_id 切换类型） */
  function reuseRecord(rec: MaterialRecord): void {
    const gen = useGenerationStore()
    const p: ProductForm = {
      title: rec.product.title,
      material: rec.product.material,
      spec: rec.product.spec,
      color: rec.product.color,
      features: [...rec.product.features],
    }
    gen.applyMaterialProduct(p, rec.used_keys, rec.type_id)
    closeDrawer()
  }

  /** 手动删除记录（带确认弹窗） */
  async function deleteRecord(id: string): Promise<void> {
    try {
      await ElMessageBox.confirm('确定删除该条素材记录吗？（仅删除本地缓存记录，图片文件保留）',
        '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    } catch {
      return
    }
    records.value = removeMaterial(id)
    ElMessage.success('已删除')
  }

  /** 复制记录（生成新 id 的副本） */
  function duplicateRecord(id: string): void {
    const src = records.value.find((r) => r.id === id)
    if (!src) return
    const copy: MaterialRecord = {
      ...JSON.parse(JSON.stringify(src)),
      id: `prod_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`,
      name: `${src.name}（副本）`,
      createdAt: Date.now(),
    }
    records.value = appendMaterial(copy)
    ElMessage.success('已复制')
  }

  /** 清空全部 */
  async function clearAll(): Promise<void> {
    if (records.value.length === 0) {
      ElMessage.info('素材库已为空')
      return
    }
    try {
      await ElMessageBox.confirm(`确定清空全部 ${records.value.length} 条素材记录吗？`,
        '清空确认', { type: 'error', confirmButtonText: '全部清空', cancelButtonText: '取消' })
    } catch {
      return
    }
    saveMaterials([])
    records.value = []
    ElMessage.success('素材库已清空')
  }

  return {
    records,
    drawerVisible,
    recordCount,
    refresh,
    openDrawer,
    closeDrawer,
    saveRecord,
    reuseRecord,
    deleteRecord,
    duplicateRecord,
    clearAll,
  }
})
