<template>
  <div class="product-form app-card">
    <div class="form-header flex-between">
      <div class="flex-row gap-sm" style="align-items: center;">
        <h3 class="title">
          <el-icon :size="20" color="$color-primary"><Goods /></el-icon>
          商品参数录入
        </h3>
        <el-tag v-if="genStore.currentProductId" size="small" type="primary" effect="plain">
          ID: {{ genStore.currentProductId }}
        </el-tag>
      </div>
      <el-select
        v-model="selectedTypeId"
        placeholder="请选择类型"
        style="width: 180px"
        filterable
        :loading="typesStore.loadingList || typesStore.loadingDetail"
        @change="handleTypeChange"
      >
        <el-option
          v-for="opt in typesStore.selectorOptions"
          :key="opt.value"
          :label="opt.label"
          :value="opt.value"
        />
      </el-select>
    </div>

    <div ref="formWrapperRef" class="form-wrapper">
      <!-- 类型未选：禁用遮罩 -->
      <div v-if="!typesStore.hasSelected" class="disabled-mask">
        <div class="mask-inner">
          <el-icon :size="48" color="#f56c6c"><Warning /></el-icon>
          <div class="mask-tip">请先在顶部选择类型</div>
        </div>
      </div>

      <el-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        label-width="88px"
        label-position="right"
        class="form-body"
        :disabled="!typesStore.hasSelected"
        @submit.prevent
      >
        <el-form-item label="商品标题" prop="title">
          <el-select
            v-model="formState.title"
            placeholder="请选择上架标题（仅白名单）"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="t in genStore.whitelist.titles"
              :key="t"
              :label="t"
              :value="t"
            />
          </el-select>
          <el-alert
            v-if="typesStore.hasSelected && genStore.whitelist.titles.length === 0"
            type="warning"
            :closable="false"
            show-icon
            title="当前类型的标题白名单为空，请先去「配置中心」配置"
            style="margin-top: 8px"
          />
        </el-form-item>

        <div class="row-2col">
          <el-form-item label="材质" prop="material">
            <el-select v-model="formState.material" placeholder="白名单内材质" style="width: 100%">
              <el-option
                v-for="m in genStore.whitelist.materials"
                :key="m"
                :label="m"
                :value="m"
              />
            </el-select>
            <el-alert
              v-if="typesStore.hasSelected && genStore.whitelist.materials.length === 0"
              type="warning"
              :closable="false"
              show-icon
              title="材质白名单为空，请先去「配置中心」配置"
              style="margin-top: 8px"
            />
          </el-form-item>

          <el-form-item label="规格" prop="spec">
            <el-select v-model="formState.spec" placeholder="白名单内规格" style="width: 100%">
              <el-option
                v-for="s in genStore.whitelist.specs"
                :key="s"
                :label="s"
                :value="s"
              />
            </el-select>
            <el-alert
              v-if="typesStore.hasSelected && genStore.whitelist.specs.length === 0"
              type="warning"
              :closable="false"
              show-icon
              title="规格白名单为空，请先去「配置中心」配置"
              style="margin-top: 8px"
            />
          </el-form-item>
        </div>

        <div class="row-2col">
          <el-form-item label="颜色" prop="color">
            <el-select v-model="formState.color" placeholder="选择主颜色" style="width: 100%">
              <el-option
                v-for="c in genStore.whitelist.colors"
                :key="c"
                :label="c"
                :value="c"
              >
                <span style="display:inline-block;vertical-align:middle;">
                  <span
                    class="color-dot"
                    :style="{ background: colorHex(c) }"
                  />&nbsp;{{ c }}
                </span>
              </el-option>
            </el-select>
            <el-alert
              v-if="typesStore.hasSelected && genStore.whitelist.colors.length === 0"
              type="warning"
              :closable="false"
              show-icon
              title="颜色白名单为空，请先去「配置中心」配置"
              style="margin-top: 8px"
            />
          </el-form-item>

          <el-form-item label="绘图模型" prop="model">
            <el-select v-model="formState.model" style="width: 100%">
              <el-option
                v-for="m in genStore.modelOptions"
                :key="m.value"
                :label="m.label"
                :value="m.value"
              >
                <div class="model-opt">
                  <el-tag
                    :type="m.type === 'cloud' ? 'danger' : 'success'"
                    size="small"
                    effect="light"
                    style="margin-right: 8px"
                  >
                    {{ m.type === 'cloud' ? '云端' : '本地' }}
                  </el-tag>
                  {{ m.label }}
                </div>
              </el-option>
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="核心卖点">
          <el-select
            v-model="formState.features"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择核心卖点（可多选）"
            style="width: 100%"
          >
            <el-option
              v-for="f in genStore.whitelist.features"
              :key="f"
              :label="f"
              :value="f"
            />
          </el-select>
          <el-alert
            v-if="typesStore.hasSelected && genStore.whitelist.features.length === 0"
            type="warning"
            :closable="false"
            show-icon
            title="核心卖点白名单为空，请先去「配置中心」配置"
            style="margin-top: 8px"
          />
        </el-form-item>

        <el-form-item label="Dry-Run">
          <el-switch
            v-model="formState.dryRun"
            active-text="仅输出Prompt占位图（零成本验证）"
            inactive-text="真实调用API生成图片"
          />
        </el-form-item>

        <el-form-item label="主图模板">
          <div ref="mainTplRef" class="tpl-picker main" :data-count="genStore.mainTemplates.length + 1">
            <!-- 商品原始图上传卡片（第一位） -->
            <div class="tpl-chip upload-card" @click="triggerOriginalUpload">
              <input
                ref="originalUploadInput"
                type="file"
                accept="image/*"
                style="display: none"
                @change="handleOriginalUpload"
              />
              <div v-if="genStore.originalImage" class="upload-thumb-wrap">
                <img :src="genStore.originalImage" class="upload-thumb" />
                <div class="upload-overlay">
                  <el-button size="small" type="primary" round>
                    <el-icon><Upload /></el-icon> 重新上传
                  </el-button>
                </div>
              </div>
              <div v-else class="upload-placeholder">
                <el-icon :size="18" color="#909399"><Upload /></el-icon>
                <span class="upload-text">上传商品原始图</span>
              </div>
            </div>
            <!-- 主图模板 -->
            <div
              v-for="t in genStore.mainTemplates"
              :key="t.key"
              class="tpl-chip"
              :class="{ active: t.selected }"
              @click="genStore.toggleTemplate(t.key)"
            >
              <el-checkbox
                class="chip-check"
                :model-value="t.selected"
                @click.stop
              />
              <div class="chip-title">{{ t.key.replace('main_', '主图') }}</div>
              <div class="chip-cn ellipsis">{{ t.scene_cn || '点击编辑场景' }}</div>
              <div class="chip-size-row">
                <span class="chip-size">{{ t.size[0] }}×{{ t.size[1] }}</span>
                <el-icon class="chip-edit-icon" @click.stop="openSceneEditor(t)"><Edit /></el-icon>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="详情模板">
          <div ref="detailTplRef" class="tpl-picker detail" :data-count="genStore.detailTemplates.length">
            <div
              v-for="t in genStore.detailTemplates"
              :key="t.key"
              class="tpl-chip"
              :class="{ active: t.selected }"
              @click="genStore.toggleTemplate(t.key)"
            >
              <el-checkbox
                class="chip-check"
                :model-value="t.selected"
                @click.stop
              />
              <div class="chip-title">{{ t.key.replace('detail_', '详情图') }}</div>
              <div class="chip-cn ellipsis">{{ t.scene_cn || '点击编辑场景' }}</div>
              <div class="chip-size-row">
                <span class="chip-size">{{ t.size[0] }}×{{ t.size[1] }}</span>
                <el-icon class="chip-edit-icon" @click.stop="openSceneEditor(t)"><Edit /></el-icon>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" @click="handleSubmit">
            <el-icon><MagicStick /></el-icon>
            批量生成 {{ genStore.selectedCount }} 张图
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- ============ 场景编辑 Dialog ============ -->
    <el-dialog
      v-model="sceneEditorVisible"
      :title="`编辑场景：${sceneEditorData?.key || ''}`"
      width="520px"
      append-to-body
      :close-on-click-modal="false"
      z-index="9999"
    >
      <el-form label-width="110px">
        <el-form-item label="Key">
          <el-tag type="info" effect="plain">{{ sceneEditorData?.key }}</el-tag>
          <span class="form-hint">（不可修改）</span>
        </el-form-item>
        <el-form-item label="中文场景" required>
          <el-input
            v-model="sceneEditorData.scene_cn"
            type="textarea"
            :rows="2"
            placeholder="如：白底正面全景"
            :disabled="sceneEditorTranslating"
          />
        </el-form-item>
        <el-form-item label="英文 Prompt">
          <div class="en-edit-row">
            <el-input
              v-model="sceneEditorData.scene_en"
              type="textarea"
              :rows="3"
              placeholder="填中文后点「翻译」自动生成，或手动输入英文"
            />
            <el-button
              size="small"
              type="success"
              :icon="MagicStick"
              :disabled="!sceneEditorData?.scene_cn"
              :loading="sceneEditorTranslating"
              @click="handleEditorTranslate"
            >翻译</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <div class="footer-left">
            <el-button
              :loading="sceneEditorResetting"
              @click="resetFromBackend"
            >重置（恢复后台默认）</el-button>
            <el-button
              type="warning"
              :loading="sceneEditorSyncing"
              @click="syncToBackend"
            >同步到后台配置</el-button>
          </div>
          <div class="footer-right">
            <el-button @click="sceneEditorVisible = false">取消</el-button>
            <el-button type="primary" @click="saveSceneEditor">保存修改</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * ProductForm.vue - 商品参数录入表单组件
 * 核心：必须先选类型（typesStore.hasSelected）才可用
 * 表单校验：必填 + 白名单限制（禁止手动输入编造值）
 */
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning, MagicStick, Edit, Upload } from '@element-plus/icons-vue'
import { useGenerationStore } from '@/store/modules/generation'
import { useTypesStore } from '@/store/modules/types'
import { translateZhToEn } from '@/api'
import type { ImageTemplate, SceneItem } from '@/types'

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'before-generate'): boolean
}>()

const genStore = useGenerationStore()
const typesStore = useTypesStore()
const formRef = ref<FormInstance>()

// 模板容器引用（用于日志排查样式错乱）
const mainTplRef = ref<HTMLElement | null>(null)
const detailTplRef = ref<HTMLElement | null>(null)
const formWrapperRef = ref<HTMLElement | null>(null)

const selectedTypeId = computed<string>({
  get: () => typesStore.currentTypeId,
  set: () => {},
})

// ============ 日志工具：排查模板渲染与滚动条样式问题 ============
const LOG_TAG = '[ProductForm]'
function logTplLayout(stage: string): void {
  const main = mainTplRef.value
  const detail = detailTplRef.value
  const wrapper = formWrapperRef.value
  const mainInfo = main
    ? { count: main.children.length, offsetWidth: main.offsetWidth, scrollHeight: main.scrollHeight, clientHeight: main.clientHeight }
    : null
  const detailInfo = detail
    ? { count: detail.children.length, offsetWidth: detail.offsetWidth, scrollHeight: detail.scrollHeight, clientHeight: detail.clientHeight }
    : null
  const wrapperInfo = wrapper
    ? { offsetWidth: wrapper.offsetWidth, scrollHeight: wrapper.scrollHeight, clientHeight: wrapper.clientHeight, scrollTop: wrapper.scrollTop }
    : null
  // eslint-disable-next-line no-console
  console.log(LOG_TAG, stage, {
    main: mainInfo,
    detail: detailInfo,
    wrapper: wrapperInfo,
    mainTplCount: genStore.mainTemplates.length,
    detailTplCount: genStore.detailTemplates.length,
  })
}

async function handleTypeChange(val: string): Promise<void> {
  if (genStore.isRunning) {
    try {
      await ElMessageBox.confirm(
        '当前有正在运行的生成任务，切换类型将可能影响结果一致性。确认继续切换？',
        '任务进行中',
        { type: 'warning', confirmButtonText: '继续切换', cancelButtonText: '取消' },
      )
    } catch {
      return
    }
  }
  // eslint-disable-next-line no-console
  console.log(LOG_TAG, 'handleTypeChange 开始', { from: typesStore.currentTypeId, to: val })
  await genStore.applyTypeToWorkbench(val)
  await nextTick()
  logTplLayout('handleTypeChange 完成')
}

interface LocalFormState {
  title: string
  material: string
  spec: string
  color: string
  features: string[]
  model: string
  dryRun: boolean
}
const formState = reactive<LocalFormState>({
  title: genStore.product.title,
  material: genStore.product.material,
  spec: genStore.product.spec,
  color: genStore.product.color,
  features: [...genStore.product.features],
  model: genStore.currentModel,
  dryRun: genStore.dryRun,
})

watch(
  () => [genStore.product, genStore.currentModel, genStore.dryRun],
  () => {
    formState.title = genStore.product.title
    formState.material = genStore.product.material
    formState.spec = genStore.product.spec
    formState.color = genStore.product.color
    formState.features = [...genStore.product.features]
    formState.model = genStore.currentModel
    formState.dryRun = genStore.dryRun
  },
  { deep: true },
)

const loading = computed<boolean>(() => genStore.taskStatus === 'running')

// ---------------- 商品原始图上传 ----------------
const originalUploadInput = ref<HTMLInputElement | null>(null)

function triggerOriginalUpload(): void {
  originalUploadInput.value?.click()
}

function handleOriginalUpload(e: Event): void {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请上传图片文件')
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片不能超过 5MB')
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    const dataUrl = reader.result as string
    genStore.setOriginalImage(dataUrl)
    ElMessage.success('商品原始图已上传')
  }
  reader.onerror = () => {
    ElMessage.error('图片读取失败')
  }
  reader.readAsDataURL(file)
  // 重置 input value 允许重复上传同一张图
  input.value = ''
}

// ---------------- 场景编辑器 ----------------
const sceneEditorVisible = ref(false)
const sceneEditorTranslating = ref(false)
const sceneEditorData = reactive<{ key: string; scene_cn: string; scene_en: string; group: 'main' | 'detail' }>({
  key: '',
  scene_cn: '',
  scene_en: '',
  group: 'main',
})

function openSceneEditor(t: ImageTemplate): void {
  sceneEditorData.key = t.key
  sceneEditorData.scene_cn = t.scene_cn
  sceneEditorData.scene_en = t.scene_en
  sceneEditorData.group = t.group
  sceneEditorVisible.value = true
}

async function handleEditorTranslate(): Promise<void> {
  if (!sceneEditorData.scene_cn) return
  sceneEditorTranslating.value = true
  try {
    const resp = await translateZhToEn(sceneEditorData.scene_cn)
    if (resp.translated && resp.en_text) {
      sceneEditorData.scene_en = resp.en_text
      ElMessage.success('翻译完成')
    } else {
      ElMessage.warning('翻译服务不可用，请手动输入英文')
    }
  } catch (_e) {
    ElMessage.error('翻译失败，请检查后端服务')
  } finally {
    sceneEditorTranslating.value = false
  }
}

// 同步/重置 loading 状态
const sceneEditorSyncing = ref(false)
const sceneEditorResetting = ref(false)

/** 保存修改：仅更新本地模板，不持久化到后端 */
function saveSceneEditor(): void {
  const key = sceneEditorData.key
  const cn = sceneEditorData.scene_cn.trim()
  const en = sceneEditorData.scene_en.trim()
  if (!cn) {
    ElMessage.warning('请填写中文场景说明')
    return
  }
  const tpl = genStore.templates.find((t) => t.key === key)
  if (tpl) {
    tpl.scene_cn = cn
    tpl.scene_en = en
  }
  sceneEditorVisible.value = false
  ElMessage.success('已保存到本地')
}

/** 同步到后台配置：更新本地 + 持久化到后端 */
async function syncToBackend(): Promise<void> {
  const key = sceneEditorData.key
  const cn = sceneEditorData.scene_cn.trim()
  const en = sceneEditorData.scene_en.trim()
  if (!cn) {
    ElMessage.warning('请填写中文场景说明')
    return
  }
  sceneEditorSyncing.value = true
  try {
    // 1. 更新本地模板
    const tpl = genStore.templates.find((t) => t.key === key)
    if (tpl) {
      tpl.scene_cn = cn
      tpl.scene_en = en
    }
    // 2. 持久化到后端
    const detail = typesStore.currentTypeDetail
    if (detail) {
      const isMain = key.startsWith('main')
      const scenes: SceneItem[] = isMain ? detail.main_scenes : detail.detail_scenes
      const idx = scenes.findIndex((s) => s.key === key)
      if (idx >= 0) {
        scenes[idx].scene_cn = cn
        scenes[idx].scene_en = en
      }
      const payload = {
        type_name: detail.type_name,
        [isMain ? 'main_scenes' : 'detail_scenes']: isMain ? [...detail.main_scenes] : [...detail.detail_scenes],
      }
      await typesStore.update(detail.type_id, payload)
    }
  } finally {
    sceneEditorSyncing.value = false
  }
}

/** 重置：从后台重新拉取默认配置，覆盖当前编辑 */
async function resetFromBackend(): Promise<void> {
  const key = sceneEditorData.key
  sceneEditorResetting.value = true
  try {
    await typesStore.refreshCurrentDetail()
    const detail = typesStore.currentTypeDetail
    if (!detail) return
    const isMain = key.startsWith('main')
    const scenes: SceneItem[] = isMain ? detail.main_scenes : detail.detail_scenes
    const scene = scenes.find((s) => s.key === key)
    if (scene) {
      sceneEditorData.scene_cn = scene.scene_cn
      sceneEditorData.scene_en = scene.scene_en
      // 同步更新本地模板
      const tpl = genStore.templates.find((t) => t.key === key)
      if (tpl) {
        tpl.scene_cn = scene.scene_cn
        tpl.scene_en = scene.scene_en
      }
    }
    ElMessage.success('已从后台重置为默认配置')
  } finally {
    sceneEditorResetting.value = false
  }
}

const formRules: FormRules = {
  title: [{ required: true, message: '请选择商品标题', trigger: 'change' }],
  material: [{ required: true, message: '请选择材质', trigger: 'change' }],
  spec: [{ required: true, message: '请选择规格', trigger: 'change' }],
  color: [{ required: true, message: '请选择颜色', trigger: 'change' }],
}

function colorHex(cnName: string): string {
  const map: Record<string, string> = {
    '象牙白': '#FFFFF0', '典雅黑': '#3B3B3B', '原木色': '#C4A27A',
    '樱花粉': '#FFB7C5', '薄荷绿': '#B5EAD7', '深空灰': '#4A4A4A',
    '香槟金': '#D7B98E',
  }
  return map[cnName] || '#CCCCCC'
}

async function handleSubmit(): Promise<void> {
  const canProceed = emit('before-generate')
  if (canProceed === false) return

  try {
    await formRef.value?.validate()
  } catch {
    ElMessage.warning('请完善必填项')
    return
  }
  genStore.product.title = formState.title
  genStore.product.material = formState.material
  genStore.product.spec = formState.spec
  genStore.product.color = formState.color
  genStore.product.features = [...formState.features]
  genStore.currentModel = formState.model
  genStore.dryRun = formState.dryRun

  emit('submit')
  await genStore.startGenerate()
}

// ============ 模板渲染监听：模板数据变化时记录布局日志 ============
watch(
  () => [genStore.mainTemplates.length, genStore.detailTemplates.length],
  async () => {
    await nextTick()
    logTplLayout('templates 数量变化')
  },
)

// ============ 滚动条 & 宽度变化监听：ResizeObserver ============
let resizeObserver: ResizeObserver | null = null
let lastWrapperWidth = 0

onMounted(() => {
  // 初次挂载完成后记录一次布局
  void nextTick().then(() => logTplLayout('onMounted'))

  // 监听左侧模块（form-wrapper）宽度变化，主图模板自适应换行时输出列数
  const wrapper = formWrapperRef.value
  if (wrapper && typeof ResizeObserver !== 'undefined') {
    lastWrapperWidth = wrapper.offsetWidth
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.round(entry.contentRect.width)
        if (w !== lastWrapperWidth) {
          lastWrapperWidth = w
          // eslint-disable-next-line no-console
          console.log(LOG_TAG, 'ResizeObserver 宽度变化', {
            wrapperWidth: w,
            mainCols: mainTplRef.value
              ? getComputedStyle(mainTplRef.value).gridTemplateColumns.split(' ').length
              : null,
            detailCols: detailTplRef.value
              ? getComputedStyle(detailTplRef.value).gridTemplateColumns.split(' ').length
              : null,
          })
        }
      }
    })
    resizeObserver.observe(wrapper)
  }
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<style lang="scss" scoped>
.product-form {
  .form-header {
    margin-bottom: 16px;
    .title {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .sub { font-weight: 400; font-size: 12px; color: $color-info; margin-left: 4px; }
  }

  .form-wrapper {
    position: relative;
  }

  .disabled-mask {
    position: absolute;
    inset: 0;
    background: rgba(245, 247, 250, 0.88);
    z-index: 10;
    border-radius: $border-radius;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(2px);
    .mask-inner {
      text-align: center;
      .mask-tip {
        margin-top: 12px;
        font-size: 20px;
        font-weight: 600;
        color: $color-danger;
      }
    }
  }

  .row-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 16px;
    :deep(.el-form-item) { margin-bottom: 18px; }
  }
  .color-dot {
    display: inline-block;
    width: 14px; height: 14px;
    border-radius: 50%;
    border: 1px solid #ddd;
    vertical-align: middle;
  }
  .model-opt { display: inline-flex; align-items: center; }

  /* el-form-item__content 是 flex 容器，tpl-picker 需强制占满宽度 */
  :deep(.el-form-item__content) {
    .tpl-picker {
      width: 100%;
    }
  }

  /* 主图模板：一行 2 张，填满容器宽度 */
  .tpl-picker.main {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
    padding-right: 4px;
    width: 100%;
  }

  /* 详情模板：一行 2 张，填满容器宽度 */
  .tpl-picker.detail {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
    margin-top: 8px;
    padding-right: 4px;
    width: 100%;
  }

  .tpl-chip {
    position: relative;
    border: 1px solid #ebeef5;
    border-radius: $border-radius-sm;
    padding: 3px 5px;
    cursor: pointer;
    transition: all .15s;
    background: #fcfcfd;
    &.active {
      border-color: $color-primary;
      background: rgba(64,158,255,.06);
      box-shadow: $shadow-hover;
    }
    &:hover { transform: translateY(-1px); }

    /* 勾选框：绝对定位到右上角 */
    .chip-check {
      position: absolute;
      top: 3px;
      right: 3px;
      z-index: 2;
      margin: 0;
      height: auto;
      :deep(.el-checkbox__inner) {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        /* 用 flex 居中对勾 */
        display: flex;
        align-items: center;
        justify-content: center;
      }
      :deep(.el-checkbox__inner::after) {
        /* 恢复 Element Plus 默认对勾尺寸，不偏移 */
        border-width: 1px;
        width: 3px;
        height: 7px;
        margin: 0;
        position: static;
      }
      /* 隐藏 label 文字 */
      :deep(.el-checkbox__label) {
        display: none;
      }
    }

    /* 第一行：标题（如 主图1 / 详情图1） */
    .chip-title {
      font-size: 11px;
      font-weight: 600;
      color: #303133;
      padding-right: 16px; /* 给右上角勾选框留位 */
      line-height: 1.3;
    }

    /* 第二行：场景描述 */
    .chip-cn {
      font-size: 10px;
      color: #606266;
      line-height: 1.3;
      min-height: 13px;
      margin-top: 2px;
    }

    /* 第三行：尺寸 + 编辑 icon */
    .chip-size-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 2px;
    }
    .chip-size {
      font-size: 9px;
      color: $color-info;
    }
    .chip-edit-icon {
      font-size: 16px;
      color: $color-info;
      cursor: pointer;
      transition: color .15s;
      &:hover { color: $color-primary; }
    }
  }

  /* 商品原始图上传卡片 */
  .upload-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border: 1px dashed #c0c4cc;
    background: #fafafa;
    position: relative;
    overflow: hidden;
    &:hover {
      border-color: $color-primary;
      background: #f0f7ff;
    }
    .upload-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      width: 100%;
      .upload-text {
        font-size: 11px;
        color: #303133;
        font-weight: 600;
      }
      .upload-hint {
        font-size: 9px;
        color: $color-info;
      }
    }
    .upload-thumb-wrap {
      position: relative;
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      .upload-thumb {
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: $border-radius-sm;
      }
      .upload-overlay {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity .2s;
      }
      &:hover .upload-overlay {
        opacity: 1;
      }
    }
  }

  /* 详情模板卡片更紧凑 */
  .tpl-picker.detail .tpl-chip {
    padding: 2px 4px;
    .chip-title { font-size: 10px; }
    .chip-cn {
      font-size: 9px;
      line-height: 1.2;
      min-height: 11px;
    }
    .chip-size { font-size: 8px; }
  }

  @media (max-width: $breakpoint-mobile) {
    .row-2col { grid-template-columns: 1fr; }
    .tpl-picker.main, .tpl-picker.detail {
      grid-template-columns: repeat(2, 1fr);
    }
  }


  .en-edit-row {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    .el-button { flex-shrink: 0; }
  }

  .form-hint {
    font-size: 12px;
    color: $color-info;
    margin-left: 8px;
  }

  /* 弹窗 footer：左右分栏 */
  .dialog-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .footer-left {
      display: flex;
      gap: 8px;
    }
    .footer-right {
      display: flex;
      gap: 8px;
    }
  }
}
</style>
