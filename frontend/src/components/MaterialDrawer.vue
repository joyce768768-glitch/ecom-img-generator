<template>
  <el-drawer
    v-model="visibleLocal"
    title="历史素材库（本地缓存）"
    direction="rtl"
    size="520px"
    :before-close="handleClose"
    destroy-on-close
  >
    <template #header>
      <div class="drawer-header flex-between" style="width: 100%;">
        <div>
          <el-icon :size="18" color="$color-warning"><Collection /></el-icon>
          &nbsp;素材库 &nbsp;
          <el-tag size="small" type="info" effect="plain">{{ store.recordCount }} 条</el-tag>
        </div>
        <div class="flex-row gap-sm">
          <el-button size="small" :disabled="store.recordCount === 0" @click="handleClear">
            <el-icon><Delete /></el-icon> 清空全部
          </el-button>
          <el-button size="small" @click="store.refresh">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </div>
    </template>

    <div v-if="store.recordCount === 0" class="empty-state">
      <el-empty description="还没有保存任何素材，生成完成后记录将自动存入本地" />
    </div>

    <div v-else class="material-list">
      <div
        v-for="rec in store.records"
        :key="rec.id"
        class="record app-card"
      >
        <div class="rec-head flex-between">
          <div class="title ellipsis" :title="rec.name">{{ rec.name }}</div>
          <el-dropdown trigger="click" @command="(cmd: string) => handleCmd(cmd, rec.id)">
            <el-button link :icon="MoreFilled" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="delete" icon="Delete">删除此条</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="rec-meta flex-row gap-sm" style="flex-wrap: wrap;">
          <!-- 所属类型标签 -->
          <el-tag size="small" type="info" effect="plain" class="type-tag">
            所属：{{ rec.type_name || rec.type_id || '未知类型' }}
          </el-tag>
          <el-tag size="small" type="primary" effect="plain">{{ rec.model }}</el-tag>
          <el-tag
            size="small"
            :type="rec.dry_run ? 'warning' : 'success'"
            effect="plain"
          >
            {{ rec.dry_run ? 'Dry-Run占位' : '真实生成' }}
          </el-tag>
          <el-tag size="small" effect="plain">{{ rec.used_keys.length }} 张</el-tag>
          <span class="date">{{ fmtDate(rec.createdAt) }}</span>
        </div>

        <div class="rec-product">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="标题" class="ellipsis">{{ rec.product.title }}</el-descriptions-item>
            <el-descriptions-item label="材质">{{ rec.product.material }}</el-descriptions-item>
            <el-descriptions-item label="规格">{{ rec.product.spec }}</el-descriptions-item>
            <el-descriptions-item label="颜色">{{ rec.product.color }}</el-descriptions-item>
            <el-descriptions-item label="卖点" :span="2">
              {{ rec.product.features.join(' · ') }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="rec-images" v-if="rec.generated.length > 0">
          <div
            v-for="img in rec.generated.slice(0, 4)"
            :key="img.file"
            class="thumb"
            :title="img.file"
          >
            <img :src="img.url" :alt="img.file" loading="lazy" />
          </div>
          <div v-if="rec.generated.length > 4" class="more-thumb">
            +{{ rec.generated.length - 4 }}
          </div>
        </div>

        <div class="rec-actions flex-row" style="justify-content: flex-end; gap: 8px; margin-top: 8px;">
          <el-button
            size="small"
            type="primary"
            @click="store.reuseRecord(rec)"
          >
            <el-icon><RefreshRight /></el-icon> 一键回填表单
          </el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * MaterialDrawer.vue - 素材库抽屉组件
 * 功能：列表展示 / 一键回填（带 type_id 切换类型）/ 删除单条 / 清空 / 刷新
 */
import { computed, watch } from 'vue'
import { useMaterialStore } from '@/store/modules/material'
import type { MaterialRecord } from '@/types'
import { MoreFilled } from '@element-plus/icons-vue'

const store = useMaterialStore()

const visibleLocal = computed<boolean>(() => store.drawerVisible)
watch(visibleLocal, (val: boolean) => {
  if (val) store.refresh()
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()
function handleClose(): void {
  emit('update:modelValue', false)
  store.closeDrawer()
}

function fmtDate(ts: number): string {
  const d = new Date(ts)
  const pad = (n: number): string => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function handleCmd(cmd: string, id: string): void {
  if (cmd === 'delete') store.deleteRecord(id)
}

function handleClear(): void {
  store.clearAll()
}
</script>

<style lang="scss" scoped>
.drawer-header :deep(.el-drawer__header) { margin: 0; }
.material-list { padding-right: 4px; }
.record {
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  &:hover { box-shadow: $shadow-hover; }

  .rec-head { margin-bottom: 8px;
    .title {
      font-size: 14px;
      font-weight: 600;
      color: #1f2937;
      max-width: 360px;
    }
  }
  .rec-meta { margin-bottom: 10px;
    .type-tag {
      color: $color-info;
      background: rgba(144, 147, 153, 0.08);
      border-color: rgba(144, 147, 153, 0.2);
    }
    .date { margin-left: auto; color: $color-info; font-size: 12px; }
  }
  .rec-product { margin-bottom: 10px; }

  .rec-images {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 6px;
    margin-top: 8px;
    .thumb, .more-thumb {
      border-radius: $border-radius-sm;
      overflow: hidden;
      aspect-ratio: 1 / 1;
      background: #f3f4f6;
      display: flex; align-items: center; justify-content: center;
      border: 1px solid #e5e7eb;
      img { width: 100%; height: 100%; object-fit: cover; }
    }
    .more-thumb {
      color: $color-info;
      font-size: 12px;
      background: #fafafa;
    }
  }
}
.empty-state { padding-top: 60px; }
</style>
