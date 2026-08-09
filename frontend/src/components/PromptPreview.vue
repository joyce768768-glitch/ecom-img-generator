<template>
  <div class="prompt-preview app-card">
    <div class="flex-between header">
      <h3 class="title">
        <el-icon :size="20" color="#E6A23C"><Document /></el-icon>
        Prompt 实时日志 &amp; 生成进度
      </h3>
      <el-tag
        :type="statusTagType"
        effect="light"
        size="default"
      >{{ statusText }}</el-tag>
    </div>

    <!-- 进度条 -->
    <el-progress
      class="progress"
      :percentage="store.progressPercent"
      :status="progressStatus"
      :stroke-width="12"
      :text-inside="true"
    />
    <div class="progress-meta flex-row gap-md">
      <el-statistic title="已完成" :value="store.taskDone" />
      <el-statistic title="失败" :value="store.taskFailed" />
      <el-statistic title="总任务" :value="store.taskTotal" />
      <el-statistic title="耗时(s)" :value="store.elapsedSec" :precision="1" />
      <el-statistic
        v-if="store.currentKey"
        title="当前生成中"
        :value="store.currentKey"
        style="max-width: 200px"
      />
    </div>

    <el-tabs v-model="activeTab" class="tabs" type="border-card">
      <!-- Tab1: 实时日志 -->
      <el-tab-pane label="实时日志" name="logs">
        <div class="log-toolbar flex-between">
          <span class="log-count">共 {{ store.logs.length }} 条</span>
          <el-button size="small" text @click="scrollToBottom">
            <el-icon><Bottom /></el-icon> 滚动到底部
          </el-button>
          <el-button size="small" text @click="clearLogs">
            <el-icon><Delete /></el-icon> 清空
          </el-button>
        </div>
        <div ref="logBoxRef" class="log-box">
          <TransitionGroup name="log-list">
            <div
              v-for="(log, i) in store.logs"
              :key="`${log.ts}-${i}`"
              class="log-line"
              :class="log.level.toLowerCase()"
            >
              <span class="ts">{{ formatTs(log.ts) }}</span>
              <el-tag size="small" :type="logLevelTag(log.level)" effect="plain">
                {{ log.level }}
              </el-tag>
              <span class="msg">{{ log.message }}</span>
            </div>
          </TransitionGroup>
          <div v-if="store.logs.length === 0" class="empty">
            <el-empty description="点击「批量生成」后在此实时查看每张图的完整 Prompt 与调用日志" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab2: Prompt 分层预览 -->
      <el-tab-pane label="Prompt 结构说明" name="structure">
        <el-descriptions title="四层拼接架构（所有生成图共用）" border :column="1" size="small">
          <el-descriptions-item label="① System 全局约束">
            <div class="code-block">1688 B2B wholesale e-commerce product photography style, ultra
realistic photo, 8K high resolution, professional studio lighting,
crisp sharp focus, accurate product color reproduction...
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="② 商品公共变量（15张全局复用）">
            <div class="code-block">Product title: {{ store.product.title }}
Material: {{ store.product.material }}
Specification: {{ store.product.spec }}
Main color: {{ store.product.color }}
Key features: {{ store.product.features.join(', ') || '-' }}
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="③ 单图专属场景（5主+10详情各不相同）">
            <div class="code-block" style="max-height: 140px; overflow-y: auto;">
              <template v-for="t in store.templates.slice(0, 5)" :key="t.key">
                · {{ t.key }}: {{ t.scene_en.slice(0, 80) }}...<br />
              </template>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="④ 通用负面提示词（独立参数）">
            <div class="code-block">blurry, distorted shape, watermark, text overlay, logo,
multiple objects chaos, wrong color, cartoon, 3d render unrealistic,
gibberish text, typography mistakes...
            </div>
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
/**
 * PromptPreview.vue - Prompt 实时日志 + 生成进度组件
 * 展示：进度条/统计/日志流/Prompt分层说明
 */
import { computed, nextTick, ref, watch } from 'vue'
import type { ProgressProps } from 'element-plus'
import { useGenerationStore } from '@/store/modules/generation'

const store = useGenerationStore()
const activeTab = ref('logs')
const logBoxRef = ref<HTMLDivElement>()

const statusText = computed<string>(() => {
  if (store.taskStatus === 'running') return '生成中'
  if (store.taskStatus === 'done' && store.taskFailed > 0) return '部分失败'
  if (store.taskStatus === 'done') return '已完成'
  return '待启动'
})
const statusTagType = computed<'success' | 'warning' | 'danger' | 'info'>(() => {
  if (store.taskStatus === 'running') return 'warning'
  if (store.taskStatus === 'done') return store.taskFailed > 0 ? 'danger' : 'success'
  return 'info'
})
const progressStatus = computed<ProgressProps['status']>(() => {
  if (store.taskStatus === 'running') return undefined
  if (store.taskStatus === 'done') return store.taskFailed > 0 ? 'exception' : 'success'
  return undefined
})

function logLevelTag(l: string): 'success' | 'info' | 'warning' | 'danger' {
  switch (l) {
    case 'INFO': return 'info'
    case 'WARN': return 'warning'
    case 'ERROR': return 'danger'
    default: return 'success'
  }
}

function formatTs(ts: number): string {
  const d = new Date(ts * 1000)
  const pad = (n: number): string => n.toString().padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function scrollToBottom(): void {
  nextTick(() => {
    if (logBoxRef.value) logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
  })
}
function clearLogs(): void {
  store.logs.splice(0)
}

watch(
  () => store.logs.length,
  () => {
    if (activeTab.value === 'logs') scrollToBottom()
  },
)
</script>

<style lang="scss" scoped>
.prompt-preview {
  .header { margin-bottom: 12px;
    .title { margin: 0; font-size: 16px; font-weight: 600;
      display: inline-flex; align-items: center; gap: 6px; } }
  .progress { margin: 8px 0 12px; }
  .progress-meta {
    flex-wrap: wrap; gap: 24px; margin-bottom: 16px;
    :deep(.el-statistic__head) { font-size: 12px; color: $color-info; }
    :deep(.el-statistic__content) { font-size: 16px; }
  }
  .tabs { :deep(.el-tabs__content) { padding: 0; } }

  .log-toolbar {
    padding: 8px 4px; border-bottom: 1px solid #ebeef5;
    margin-bottom: 8px;
    .log-count { color: $color-info; font-size: 12px; }
  }
  .log-box {
    height: 340px;
    overflow-y: auto;
    background: #111827;
    border-radius: $border-radius-sm;
    padding: 10px 14px;
    font-family: 'SF Mono', Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.9;
  }
  .log-line {
    display: flex; align-items: flex-start; gap: 8px;
    .ts { color: #9ca3af; }
    .msg { color: #e5e7eb; word-break: break-all; flex: 1; }
    &.error .msg { color: #fca5a5; }
    &.warn  .msg { color: #fcd34d; }
  }
  .empty { padding: 40px 0; }

  .code-block {
    background: #f6f8fa;
    border: 1px solid #e5e7eb;
    border-radius: $border-radius-sm;
    padding: 8px 12px;
    font-family: 'SF Mono', Menlo, Consolas, monospace;
    font-size: 12px;
    color: #374151;
    line-height: 1.6;
    white-space: pre-wrap;
  }
}
.log-list-enter-from, .log-list-leave-to { opacity: 0; transform: translateY(-4px); }
.log-list-enter-active { transition: all .2s; }
</style>
