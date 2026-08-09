<template>
  <el-dialog
    v-model="visibleLocal"
    title="绘图模型配置"
    width="620px"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-tabs v-model="activeTab">
      <!-- 模型选择 -->
      <el-tab-pane label="模型选择" name="model">
        <div class="model-list">
          <div
            v-for="m in genStore.modelOptions"
            :key="m.value"
            class="model-card"
            :class="{ active: m.value === currentLocal }"
            @click="currentLocal = m.value"
          >
            <div class="mc-head flex-between">
              <div class="flex-row gap-sm">
                <el-radio :model-value="currentLocal" :label="m.value" />
                <b>{{ m.label }}</b>
              </div>
              <el-tag
                size="small"
                :type="m.type === 'cloud' ? 'danger' : 'success'"
                effect="light"
              >
                {{ m.type === 'cloud' ? '云端商用' : '本地离线免费' }}
              </el-tag>
            </div>
            <div class="mc-desc">
              <template v-if="m.value === 'tongyi_wanxiang'">
                通义万相 · 阿里DashScope，电商素材推荐，中文Prompt友好
                <el-tag
                  :type="genStore.apiKeyStatus.dashscope_configured ? 'success' : 'danger'"
                  size="small"
                  effect="plain"
                  style="margin-left: 6px"
                >
                  {{ genStore.apiKeyStatus.dashscope_configured ? '已配置Key' : '未配置Key' }}
                </el-tag>
              </template>
              <template v-else-if="m.value === 'dalle3'">
                DALL·E3 · OpenAI出品，通用能力强画质高
                <el-tag
                  :type="genStore.apiKeyStatus.openai_configured ? 'success' : 'danger'"
                  size="small"
                  effect="plain"
                  style="margin-left: 6px"
                >
                  {{ genStore.apiKeyStatus.openai_configured ? '已配置Key' : '未配置Key' }}
                </el-tag>
              </template>
              <template v-else-if="m.value === 'ollama_sdxl'">
                Ollama SDXL · 本地部署 stable-diffusion，显存≥4GB即可，<b>免费无需密钥</b>
              </template>
              <template v-else-if="m.value === 'ollama_flux'">
                Ollama Flux · 本地开源SOTA画质，显存≥8GB推荐，<b>免费无需密钥</b>
              </template>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- API Key 配置 -->
      <el-tab-pane label="API Key 配置" name="apikey">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          title="API Key 会保存到后端 .env 文件，重启后端服务即可生效。密钥仅保存在本地，不会上传。"
          style="margin-bottom: 16px"
        />
        <el-form label-position="top">
          <el-form-item label="通义万相 DASHSCOPE_API_KEY">
            <div class="key-row">
              <el-input
                v-model="dashscopeKey"
                type="password"
                show-password
                placeholder="输入阿里 DashScope API Key"
                :disabled="savingKeys"
              />
              <el-tag
                :type="genStore.apiKeyStatus.dashscope_configured ? 'success' : 'info'"
                size="small"
                effect="plain"
                style="margin-left: 8px"
              >
                {{ genStore.apiKeyStatus.dashscope_configured ? '已配置' : '未配置' }}
              </el-tag>
            </div>
          </el-form-item>
          <el-form-item label="DALL·E3 OPENAI_API_KEY">
            <div class="key-row">
              <el-input
                v-model="openaiKey"
                type="password"
                show-password
                placeholder="输入 OpenAI API Key"
                :disabled="savingKeys"
              />
              <el-tag
                :type="genStore.apiKeyStatus.openai_configured ? 'success' : 'info'"
                size="small"
                effect="plain"
                style="margin-left: 8px"
              >
                {{ genStore.apiKeyStatus.openai_configured ? '已配置' : '未配置' }}
              </el-tag>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              :loading="savingKeys"
              @click="handleSaveKeys"
            >
              保存 API Key
            </el-button>
            <el-button @click="handleClearKeys" :disabled="savingKeys">清空</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 负面提示词 -->
      <el-tab-pane label="负面提示词" name="negative">
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          title="负面提示词会随每次生成请求一并传入，可自定义补充。系统内置通用负面词已默认生效。"
          style="margin-bottom: 16px"
        />
        <el-form label-position="top">
          <el-form-item label="自定义负面提示词（保存到 generationStore，提交生成时一并携带）">
            <el-input
              v-model="negativePrompt"
              type="textarea"
              :rows="6"
              placeholder="例如：low quality, bad anatomy, extra fingers..."
            />
          </el-form-item>
          <el-form-item label="系统内置通用负面词（固定生效，不可改）">
            <el-input
              type="textarea"
              :rows="4"
              readonly
              :model-value="genStore.negativeBase"
            />
          </el-form-item>
        </el-form>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <div class="flex-between" style="width: 100%;">
        <el-button @click="handleResetNagative">重置负面词</el-button>
        <div class="flex-row gap-sm">
          <el-button @click="visibleLocal = false">取消</el-button>
          <el-button type="primary" @click="handleConfirm">应用配置</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * ModelConfigDialog.vue - 模型配置弹窗
 * 功能：模型选择/API Key配置/负面Prompt自定义/部署指引
 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useGenerationStore } from '@/store/modules/generation'
import {
  saveNegativePrompt,
  saveModelPreference,
} from '@/utils/storage'

interface Props {
  modelValue: boolean
}
const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
}>()

const genStore = useGenerationStore()
const activeTab = ref('model')

const visibleLocal = computed<boolean>(() => props.modelValue)
watch(visibleLocal, (v: boolean) => {
  if (!v) return
  currentLocal.value = genStore.currentModel
  negativePrompt.value = genStore.extraNegative
  dashscopeKey.value = ''
  openaiKey.value = ''
})
watch(visibleLocal, (v: boolean) => emit('update:modelValue', v))

const currentLocal = ref<string>(genStore.currentModel)
const negativePrompt = ref<string>(genStore.extraNegative)
const dashscopeKey = ref('')
const openaiKey = ref('')
const savingKeys = ref(false)

async function handleSaveKeys(): Promise<void> {
  const params: { dashscope_api_key?: string; openai_api_key?: string } = {}
  if (dashscopeKey.value.trim()) {
    params.dashscope_api_key = dashscopeKey.value.trim()
  }
  if (openaiKey.value.trim()) {
    params.openai_api_key = openaiKey.value.trim()
  }
  if (!params.dashscope_api_key && !params.openai_api_key) {
    ElMessage.warning('请至少填写一个 API Key')
    return
  }
  savingKeys.value = true
  try {
    const ok = await genStore.saveApiKeysToBackend(params)
    if (ok) {
      ElMessage.success('API Key 保存成功')
    } else {
      ElMessage.error('保存失败，请检查后端服务')
    }
  } finally {
    savingKeys.value = false
  }
}

async function handleClearKeys(): Promise<void> {
  savingKeys.value = true
  try {
    const ok = await genStore.saveApiKeysToBackend({
      dashscope_api_key: '',
      openai_api_key: '',
    })
    if (ok) {
      dashscopeKey.value = ''
      openaiKey.value = ''
      ElMessage.success('已清空 API Key')
    }
  } finally {
    savingKeys.value = false
  }
}

function handleResetNagative(): void {
  negativePrompt.value = ''
  saveNegativePrompt('')
  genStore.extraNegative = ''
  ElMessage.success('已重置负面提示词')
}

function handleConfirm(): void {
  saveModelPreference(currentLocal.value)
  saveNegativePrompt(negativePrompt.value)
  genStore.currentModel = currentLocal.value
  genStore.extraNegative = negativePrompt.value
  ElMessage.success(
    `已应用：模型=${currentLocal.value}，负面词已保存（${negativePrompt.value.length > 0 ? '已设置' : '空'}）`,
  )
  emit('update:modelValue', false)
}
</script>

<style lang="scss" scoped>
.model-list { display: flex; flex-direction: column; gap: 10px; }
.model-card {
  border: 1px solid #ebeef5;
  border-radius: $border-radius;
  padding: 12px 16px;
  cursor: pointer;
  transition: all .15s;
  background: #fff;
  &.active {
    border-color: $color-primary;
    background: rgba(64,158,255,.05);
    box-shadow: $shadow-hover;
  }
  &:hover { transform: translateY(-1px); }
  .mc-head { margin-bottom: 6px; }
  .mc-desc {
    font-size: 12px;
    color: #606266;
    line-height: 1.7;
    padding-left: 28px;
  }
}
.key-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
</style>
