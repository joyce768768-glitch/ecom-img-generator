/**
 * store/modules/types.ts - 类型（类目配置）store
 * ------------------------------------------------
 * 组合式写法（Pinia Setup Store），避免 Options 重载推断问题。
 * 提供：列表简版（顶部选择器 / 配置中心列表）、当前选中详情（白名单+15场景）、
 *       CRUD + 复制 + 导入导出。
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TypeFull, TypePayload, TypeSlim } from '@/types'
import {
  createType,
  deleteType,
  duplicateType,
  exportTypesToFile,
  fetchTypeDetail,
  fetchTypeList,
  importTypesFromFile,
  updateType,
} from '@/api'

export const useTypesStore = defineStore('types', () => {
  // ---------------- state ----------------
  const slimList = ref<TypeSlim[]>([])
  const currentTypeId = ref<string>('')
  const currentTypeDetail = ref<TypeFull | null>(null)
  const loadingList = ref<boolean>(false)
  const loadingDetail = ref<boolean>(false)
  const saving = ref<boolean>(false)

  // ---------------- getters ----------------
  const selectorOptions = computed(() =>
    slimList.value.map((t) => ({
      label: `${t.type_name}（主${t.main_count}/详${t.detail_count}）`,
      value: t.type_id,
    })),
  )
  const hasSelected = computed<boolean>(
    () => !!currentTypeId.value && !!currentTypeDetail.value,
  )

  // ---------------- actions ----------------
  async function loadList(): Promise<void> {
    loadingList.value = true
    try {
      const resp = await fetchTypeList(true)
      slimList.value = resp.items
      const exists = slimList.value.some((t) => t.type_id === currentTypeId.value)
      if (!exists) {
        currentTypeId.value = slimList.value[0]?.type_id || ''
        currentTypeDetail.value = null
      }
    } finally {
      loadingList.value = false
    }
  }

  async function selectType(typeId: string): Promise<TypeFull | null> {
    if (!typeId) {
      currentTypeId.value = ''
      currentTypeDetail.value = null
      return null
    }
    loadingDetail.value = true
    try {
      const d = await fetchTypeDetail(typeId)
      currentTypeId.value = typeId
      currentTypeDetail.value = d
      return d
    } finally {
      loadingDetail.value = false
    }
  }

  async function refreshCurrentDetail(): Promise<void> {
    if (currentTypeId.value) {
      await selectType(currentTypeId.value)
    }
  }

  async function create(payload: TypePayload): Promise<TypeFull | null> {
    saving.value = true
    try {
      const resp = await createType(payload)
      ElMessage.success(`类型「${resp.item.type_name}」创建成功`)
      await loadList()
      return resp.item
    } catch (_e) {
      return null
    } finally {
      saving.value = false
    }
  }

  async function update(typeId: string, payload: Partial<TypePayload>): Promise<TypeFull | null> {
    saving.value = true
    try {
      const resp = await updateType(typeId, payload)
      ElMessage.success('保存成功')
      await loadList()
      if (currentTypeId.value === typeId) {
        currentTypeDetail.value = resp.item
      }
      return resp.item
    } catch (_e) {
      return null
    } finally {
      saving.value = false
    }
  }

  async function remove(typeId: string, force = false): Promise<boolean> {
    const target = slimList.value.find((t) => t.type_id === typeId)
    if (!target) return false
    if (!force) {
      try {
        await ElMessageBox.confirm(
          `确认删除类型「${target.type_name}」？删除后无法恢复，且至少保留一个类型。`,
          '删除类型',
          { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
        )
      } catch (_e) {
        return false
      }
    }
    try {
      await deleteType(typeId)
      ElMessage.success('删除成功')
      await loadList()
      if (currentTypeId.value === typeId) {
        const nextId = slimList.value[0]?.type_id || ''
        currentTypeId.value = nextId
        currentTypeDetail.value = nextId ? await fetchTypeDetail(nextId) : null
      }
      return true
    } catch (_e) {
      return false
    }
  }

  async function duplicate(srcTypeId: string, newName: string, newTypeId?: string): Promise<TypeFull | null> {
    saving.value = true
    try {
      const resp = await duplicateType(srcTypeId, newName, newTypeId)
      ElMessage.success(`复制成功：${resp.item.type_name}`)
      await loadList()
      return resp.item
    } catch (_e) {
      return null
    } finally {
      saving.value = false
    }
  }

  async function exportFile(): Promise<void> {
    try {
      await exportTypesToFile()
      ElMessage.success('导出成功')
    } catch (_e) {
      ElMessage.error('导出失败')
    }
  }

  async function importFile(file: File, mode: 'merge' | 'replace'): Promise<boolean> {
    saving.value = true
    try {
      const resp = await importTypesFromFile(file, mode)
      ElMessage.success(`导入成功（共 ${resp.total} 个类型，模式=${resp.mode}）`)
      await loadList()
      return true
    } catch (_e) {
      return false
    } finally {
      saving.value = false
    }
  }

  return {
    // state
    slimList,
    currentTypeId,
    currentTypeDetail,
    loadingList,
    loadingDetail,
    saving,
    // getters
    selectorOptions,
    hasSelected,
    // actions
    loadList,
    selectType,
    refreshCurrentDetail,
    create,
    update,
    remove,
    duplicate,
    exportFile,
    importFile,
  }
})
