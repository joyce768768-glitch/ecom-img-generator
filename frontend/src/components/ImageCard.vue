<template>
  <div class="image-card" :class="{ deleted: data.deleted }">
    <!-- 卡头：Key + 尺寸 -->
    <div class="card-head flex-between">
      <div class="flex-row gap-sm">
        <el-tag :type="groupTag" size="small" effect="dark">
          {{ groupLabel }}
        </el-tag>
        <b>{{ keyUpper }}</b>
      </div>
      <span class="size-badge">{{ data.size_kb }} KB</span>
    </div>

    <!-- 图片主体：hover遮罩操作 -->
    <div class="image-wrap" @click="$emit('preview', data)">
      <img
        :src="data.url"
        :alt="data.file"
        loading="lazy"
        @error="handleImgError"
      />
      <!-- 正在生成中的动画遮罩 -->
      <div v-if="isGenerating" class="generating-mask flex-col">
        <el-icon :size="36" class="spin"><Loading /></el-icon>
        <span>生成中...</span>
      </div>
      <div v-else class="hover-mask">
        <div class="mask-row">
          <el-button size="small" type="primary" @click.stop="$emit('preview', data)">
            <el-icon><ZoomIn /></el-icon> 放大
          </el-button>
          <el-button size="small" type="success" @click.stop="handleDownload">
            <el-icon><Download /></el-icon> 下载
          </el-button>
        </div>
        <div class="mask-row">
          <el-button
            v-if="!data.deleted"
            size="small" type="danger" plain
            @click.stop="$emit('delete', data.key)"
          >
            <el-icon><Delete /></el-icon> 删除
          </el-button>
          <el-button
            v-else
            size="small" type="warning" plain
            @click.stop="$emit('restore', data.key)"
          >
            <el-icon><RefreshLeft /></el-icon> 恢复
          </el-button>
        </div>
      </div>
    </div>

    <!-- 卡尾：中文名 + 尺寸规格 -->
    <div class="card-foot">
      <div class="cn ellipsis">{{ scn_cn }}</div>
      <div class="meta flex-between">
        <span class="size">{{ sizeStr }}</span>
        <el-tooltip content="复制 /output/ 文件名" placement="top">
          <span
            class="fname ellipsis"
            @click="copyFilename"
          >{{ data.file }}</span>
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ImageCard.vue - 单张生成图卡片组件
 * 操作：放大预览 / 单图下载 / 标记删除恢复 / 复制文件名
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { saveAs } from 'file-saver'

import type { GeneratedImage, ImageTemplate, TemplateGroup } from '@/types'
import { useGenerationStore } from '@/store/modules/generation'

interface Props {
  data: GeneratedImage
}
const props = defineProps<Props>()
defineEmits<{
  (e: 'preview', img: GeneratedImage): void
  (e: 'delete', key: string): void
  (e: 'restore', key: string): void
}>()

const store = useGenerationStore()

const keyUpper = computed<string>(() => props.data.key.replace('_', ' ').toUpperCase())
const group = computed<TemplateGroup>(() => props.data.key.startsWith('main') ? 'main' : 'detail')
const groupLabel = computed<string>(() => group.value === 'main' ? '主图' : '详情')
const groupTag = computed<'primary' | 'warning'>(() => group.value === 'main' ? 'primary' : 'warning')

const size = computed<[number, number]>(() =>
  group.value === 'main' ? [800, 800] : [750, 1000],
)
const sizeStr = computed<string>(() => `${size.value[0]}×${size.value[1]}`)
const scn_cn = computed<string>(() => {
  const t = store.templates.find((x: ImageTemplate) => x.key === props.data.key)
  return t?.scene_cn || '—'
})
const isGenerating = computed<boolean>(
  () => store.taskStatus === 'running' && store.currentKey === props.data.key,
)

const imgError = ref(false)
function handleImgError(e: Event): void {
  const t = e.target as HTMLImageElement
  t.src =
    'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300"><rect width="100%" height="100%" fill="%23eee"/><text x="50%" y="50%" fill="%23999" font-size="16" text-anchor="middle" dy=".3em">加载失败</text></svg>'
  imgError.value = true
}

async function handleDownload(): Promise<void> {
  try {
    const resp = await fetch(props.data.url)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const blob = await resp.blob()
    saveAs(blob, props.data.file)
    ElMessage.success(`已下载：${props.data.file}`)
  } catch (e) {
    ElMessage.error(`下载失败：${e instanceof Error ? e.message : String(e)}`)
  }
}

function copyFilename(): void {
  navigator.clipboard.writeText(props.data.file).then(() => {
    ElMessage.success(`已复制：${props.data.file}`)
  }).catch(() => {
    ElMessage.warning('浏览器不支持剪贴板API')
  })
}
</script>

<style lang="scss" scoped>
.image-card {
  background: #fff;
  border-radius: $border-radius;
  box-shadow: $shadow-card;
  overflow: hidden;
  transition: all .2s;
  &:hover { transform: translateY(-2px); box-shadow: $shadow-hover; }
  &.deleted { opacity: .4; filter: grayscale(.8); }

  .card-head {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f1f3;
    background: #fafbfc;
    .size-badge { font-size: 11px; color: $color-info; }
  }
  .image-wrap {
    position: relative;
    width: 100%;
    padding-top: 100%;
    overflow: hidden;
    background: #f3f4f6;
    cursor: zoom-in;

    img {
      position: absolute;
      inset: 0;
      width: 100%; height: 100%;
      object-fit: cover;
      transition: transform .3s;
    }
    &:hover img { transform: scale(1.05); }

    .hover-mask {
      position: absolute; inset: 0;
      background: rgba(0, 0, 0, .55);
      opacity: 0;
      transition: opacity .2s;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      gap: 12px;
    }
    &:hover .hover-mask { opacity: 1; }
    .mask-row { display: flex; gap: 8px; }

    .generating-mask {
      position: absolute; inset: 0;
      background: rgba(64, 158, 255, .9);
      color: #fff;
      align-items: center; justify-content: center;
      gap: 10px;
      font-size: 14px;
    }
    .spin { animation: spin 1.2s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  }
  .card-foot {
    padding: 8px 12px 12px;
    .cn { font-size: 13px; color: #303133; font-weight: 500; margin-bottom: 4px; }
    .meta { font-size: 11px; color: $color-info;
      .size { flex-shrink: 0; margin-right: 10px; }
      .fname {
        cursor: pointer;
        max-width: 150px;
        &:hover { color: $color-primary; }
      }
    }
  }
}
</style>
