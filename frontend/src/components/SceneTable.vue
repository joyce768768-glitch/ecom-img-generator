<template>
  <div class="scene-table app-card">
    <div class="toolbar flex-between">
      <div class="toolbar-left flex-row gap-sm" style="align-items: center;">
        <el-tag size="small" type="primary" effect="plain">共 {{ rows.length }} 张</el-tag>
        <span class="tip-text">填中文即可，系统自动翻译英文 Prompt</span>
      </div>
      <div class="toolbar-right flex-row gap-sm">
        <el-button
          size="small"
          type="success"
          plain
          :disabled="!hasCnWithoutEn || anyTranslating"
          :loading="batchTranslating"
          @click="handleBatchTranslate"
        >
          <el-icon><MagicStick /></el-icon> 批量翻译
        </el-button>
        <el-button size="small" type="primary" plain @click="handleAddRow">
          <el-icon><Plus /></el-icon> 新增一行
        </el-button>
        <el-button
          size="small"
          type="danger"
          plain
          :disabled="rows.length <= 1"
          @click="handleRemoveLast"
        >
          <el-icon><Minus /></el-icon> 删除最后一行
        </el-button>
      </div>
    </div>

    <el-table
      :data="displayRows"
      border
      size="small"
      class="table-body"
      :cell-style="{ padding: '6px 8px' }"
    >
      <el-table-column label="Key" width="140" align="center">
        <template #default="{ row, $index }">
          <div class="key-cell">
            <div class="key-value">{{ getDisplayKey(row, $index) }}</div>
            <div class="key-size">size:{{ row.size }}</div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="scene_cn（中文场景说明）" min-width="220">
        <template #default="{ row, $index }">
          <el-input
            :model-value="row.scene_cn"
            placeholder="中文场景说明，如：白底正面全景"
            size="small"
            @update:model-value="(v: string) => handleCnChange($index, v)"
          />
        </template>
      </el-table-column>

      <el-table-column label="scene_en（英文 Prompt）" min-width="340">
        <template #default="{ row, $index }">
          <div class="en-cell">
            <el-input
              :model-value="row.scene_en"
              type="textarea"
              :rows="2"
              placeholder="填中文后点「翻译」自动生成，或手动输入英文"
              size="small"
              @update:model-value="(v: string) => handleFieldChange($index, 'scene_en', v)"
            />
            <div class="en-row">
              <el-button
                size="small"
                type="success"
                link
                :disabled="!row.scene_cn || !needsTranslate(row)"
                :loading="translating[$index]"
                @click="handleTranslate($index)"
              >
                <el-icon><MagicStick /></el-icon> 翻译
              </el-button>
              <span v-if="row.scene_en && !needsTranslate(row)" class="translated-badge">
                ✓ 已翻译
              </span>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="size" width="110" align="center">
        <template #default="{ row, $index }">
          <el-select
            :model-value="row.size"
            size="small"
            style="width: 100%"
            :disabled="sizeDisabled"
            @update:model-value="(v: 'main' | 'detail') => handleFieldChange($index, 'size', v)"
          >
            <el-option label="main" value="main" />
            <el-option label="detail" value="detail" />
          </el-select>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="140" align="center" fixed="right">
        <template #default="{ $index }">
          <div class="actions flex-row" style="justify-content: center; gap: 4px;">
            <el-button
              size="small"
              plain
              :disabled="$index === 0"
              @click="handleMoveUp($index)"
              title="上移"
            >
              <el-icon><Top /></el-icon>
            </el-button>
            <el-button
              size="small"
              plain
              :disabled="$index === rows.length - 1"
              @click="handleMoveDown($index)"
              title="下移"
            >
              <el-icon><Bottom /></el-icon>
            </el-button>
            <el-button
              size="small"
              plain
              type="warning"
              @click="handleClearRow($index)"
              title="清空 scene_cn 和 scene_en"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Minus, Top, Bottom, Delete, MagicStick } from '@element-plus/icons-vue'
import { translateZhToEn } from '@/api'
import type { SceneItem } from '@/types'

interface Props {
  rows: SceneItem[]
  defaultSize: 'main' | 'detail'
}

const props = withDefaults(defineProps<Props>(), {
  rows: () => [],
  defaultSize: 'main'
})

const emit = defineEmits<{
  (e: 'update', next: SceneItem[]): void
}>()

const sizeDisabled = computed<boolean>(() => true)
const displayRows = computed<SceneItem[]>(() => props.rows)

// 翻译状态
const translating = reactive<Record<number, boolean>>({})
const batchTranslating = ref(false)

const hasCnWithoutEn = computed<boolean>(() =>
  props.rows.some((r) => r.scene_cn && (!r.scene_en || r.scene_en.trim() === '')),
)

const anyTranslating = computed<boolean>(() =>
  Object.values(translating).some((v) => v),
)

function needsTranslate(row: SceneItem): boolean {
  if (!row.scene_cn) return false
  if (!row.scene_en || row.scene_en.trim() === '') return true
  return false
}

function cloneRows(): SceneItem[] {
  return props.rows.map((r) => ({ ...r }))
}

function getDisplayKey(row: SceneItem, idx: number): string {
  if (row.key && row.key.trim().length > 0) {
    return row.key
  }
  return `${props.defaultSize}_${idx + 1}`
}

function handleFieldChange<K extends keyof SceneItem>(
  idx: number,
  field: K,
  value: SceneItem[K]
): void {
  const next = cloneRows()
  next[idx][field] = value
  emit('update', next)
}

function handleCnChange(idx: number, value: string): void {
  const next = cloneRows()
  next[idx].scene_cn = value
  // 如果修改了中文，清空英文以提示需要重新翻译
  if (next[idx].scene_en && next[idx].scene_en.trim() && !isEnglish(next[idx].scene_cn)) {
    next[idx].scene_en = ''
  }
  emit('update', next)
}

function isEnglish(text: string): boolean {
  return !/[\u4e00-\u9fff]/.test(text)
}

async function handleTranslate(idx: number): Promise<void> {
  const row = props.rows[idx]
  if (!row.scene_cn || !needsTranslate(row)) return

  translating[idx] = true
  try {
    const resp = await translateZhToEn(row.scene_cn)
    if (resp.translated && resp.en_text) {
      const next = cloneRows()
      next[idx].scene_en = resp.en_text
      emit('update', next)
      ElMessage.success(`翻译完成：${resp.en_text}`)
    } else {
      ElMessage.warning('翻译服务不可用，请手动输入英文')
    }
  } catch (_e) {
    ElMessage.error('翻译失败，请检查后端服务')
  } finally {
    translating[idx] = false
  }
}

async function handleBatchTranslate(): Promise<void> {
  const rowsToTranslate = props.rows
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => r.scene_cn && (!r.scene_en || r.scene_en.trim() === ''))

  if (rowsToTranslate.length === 0) {
    ElMessage.info('没有需要翻译的行')
    return
  }

  batchTranslating.value = true
  const next = cloneRows()
  let successCount = 0

  for (const { r, i } of rowsToTranslate) {
    translating[i] = true
    try {
      const resp = await translateZhToEn(r.scene_cn)
      if (resp.translated && resp.en_text) {
        next[i].scene_en = resp.en_text
        successCount++
      }
    } catch (_e) {
      // 跳过失败的，继续下一个
    } finally {
      translating[i] = false
    }
  }

  emit('update', next)
  batchTranslating.value = false
  ElMessage.success(`批量翻译完成：成功 ${successCount}/${rowsToTranslate.length}`)
}

function generateNewKey(): string {
  const existingKeys = new Set(props.rows.map((r) => r.key))
  const baseIdx = props.rows.length + 1
  let candidate = `${props.defaultSize}_${baseIdx}`
  let suffix = 1
  while (existingKeys.has(candidate)) {
    candidate = `${props.defaultSize}_${baseIdx}_${suffix++}`
  }
  return candidate
}

function handleAddRow(): void {
  const next = cloneRows()
  next.push({
    key: generateNewKey(),
    scene_cn: '',
    scene_en: '',
    size: props.defaultSize
  })
  emit('update', next)
}

function handleRemoveLast(): void {
  if (props.rows.length <= 1) return
  const next = cloneRows()
  next.pop()
  emit('update', next)
}

function handleMoveUp(idx: number): void {
  if (idx <= 0) return
  const next = cloneRows()
  ;[next[idx - 1], next[idx]] = [next[idx], next[idx - 1]]
  emit('update', next)
}

function handleMoveDown(idx: number): void {
  if (idx >= props.rows.length - 1) return
  const next = cloneRows()
  ;[next[idx], next[idx + 1]] = [next[idx + 1], next[idx]]
  emit('update', next)
}

function handleClearRow(idx: number): void {
  const next = cloneRows()
  next[idx].scene_cn = ''
  next[idx].scene_en = ''
  emit('update', next)
}
</script>

<style lang="scss" scoped>
.scene-table {
  background: $bg-card;
  border-radius: $border-radius;
  padding: $gap-sm;
  box-shadow: $shadow-card;
}

.toolbar {
  margin-bottom: $gap-sm;

  .tip-text {
    color: $color-info;
    font-size: 12px;
  }
}

.table-body {
  width: 100%;
}

.key-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  .key-value {
    font-weight: 600;
    font-size: 13px;
    color: $color-primary;
  }

  .key-size {
    font-size: 11px;
    color: $color-info;
  }
}

.en-cell {
  .en-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 4px;
  }

  .translated-badge {
    font-size: 11px;
    color: #67c23a;
  }
}

.actions {
  :deep(.el-button) {
    padding: 4px 6px;
  }
}
</style>
