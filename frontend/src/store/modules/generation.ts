/**
 * store/modules/generation.ts - 核心生成流程 Pinia Store（类型可配置版）
 * 依赖：types store（必须先选类型，才有白名单/模板/默认商品参数）
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import JSZip from 'jszip'
import { saveAs } from 'file-saver'
import { ElMessage } from 'element-plus'

import type {
  AppConfigResp,
  GeneratedImage,
  GenerateReqBody,
  ImageTemplate,
  ModelOption,
  ProductForm,
  SceneItem,
  TaskLogEntry,
  TaskStatus,
  WhitelistConfig,
} from '@/types'
import {
  fetchAppConfig,
  fetchTaskResults,
  pollTaskStatus,
  saveApiKeys,
  startGeneration,
} from '@/api'
import { loadModelPreference, saveModelPreference, appendMaterial } from '@/utils/storage'
import { useTypesStore } from './types'

export const useGenerationStore = defineStore('generation', () => {
  // ---------------- state ----------------
  const configReady = ref(false)
  const modelOptions = ref<ModelOption[]>([])
  const sizeMap = ref<Record<string, [number, number]>>({ main: [800, 800], detail: [750, 1000] })
  const negativeBase = ref('')

  const templates = ref<ImageTemplate[]>([])
  const whitelist = ref<WhitelistConfig>({
    titles: [], materials: [], specs: [], colors: [], features: [],
  })

  const currentModel = ref('')
  const product = ref<ProductForm>({
    title: '', material: '', spec: '', color: '', features: [],
  })
  const dryRun = ref(false)
  const extraNegative = ref('')  // 用户自定义负面词（来自模型配置弹窗）
  // 参考图影响强度（0-1，仅当 originalImage 存在时生效；越大越接近参考图）
  const refStrength = ref<number>(0.5)

  const apiKeyStatus = ref({
    dashscope_configured: false,
    openai_configured: false,
    ollama_configured: true,
  })

  const taskId = ref<string | null>(null)
  const taskTypeId = ref('')
  const taskTypeName = ref('')
  const taskStatus = ref<TaskStatus>('pending')
  const taskTotal = ref(0)
  const taskDone = ref(0)
  const taskFailed = ref(0)
  const currentKey = ref<string | null>(null)
  const logs = ref<TaskLogEntry[]>([])
  const logsCursor = ref(0)
  const generated = ref<GeneratedImage[]>([])
  const elapsedSec = ref(0)
  const pollingTimer = ref<number | null>(null)

  // 商品列表记录ID（新建/编辑时预生成，用于生成后保存到商品列表）
  const currentProductId = ref<string>('')

  // 商品原始图（用户上传，作为后续15张图的设计参考）
  const originalImage = ref<string>('')  // base64 data URL

  // ---------------- getters ----------------
  const selectedTemplateKeys = computed<string[]>(() =>
    templates.value.filter((t) => t.selected).map((t) => t.key),
  )
  const selectedCount = computed<number>(() => selectedTemplateKeys.value.length)
  const mainTemplates = computed<ImageTemplate[]>(() =>
    templates.value.filter((t) => t.group === 'main'),
  )
  const detailTemplates = computed<ImageTemplate[]>(() =>
    templates.value.filter((t) => t.group === 'detail'),
  )
  const progressPercent = computed<number>(() => {
    if (taskTotal.value === 0) return 0
    return Math.round(((taskDone.value + taskFailed.value) / taskTotal.value) * 100)
  })
  const visibleGenerated = computed<GeneratedImage[]>(() =>
    generated.value.filter((g) => !g.deleted),
  )
  const isRunning = computed<boolean>(() => taskStatus.value === 'running')

  // ---------------- 依赖 store ----------------
  const typesStore = useTypesStore()

  // ---------------- 初始化：基础配置（无类型） ----------------
  async function initConfig(): Promise<void> {
    if (configReady.value) return
    const resp: AppConfigResp = await fetchAppConfig()
    modelOptions.value = resp.models
    sizeMap.value = resp.sizes || sizeMap.value
    negativeBase.value = resp.negative_base || ''
    if (resp.api_keys) {
      apiKeyStatus.value = { ...apiKeyStatus.value, ...resp.api_keys }
    }
    const pref = loadModelPreference()
    currentModel.value = pref && resp.models.some((m) => m.value === pref)
      ? pref
      : resp.default_model

    // 加载类型列表 + 自动选中第一个
    await typesStore.loadList()
    if (typesStore.slimList.length > 0) {
      await applyTypeToWorkbench(typesStore.slimList[0].type_id)
    }

    configReady.value = true
    if (resp.message) {
      console.info('[config]', resp.message)
    }
  }

  // ---------------- 应用类型到工作台（用户切换类型或初始化） ----------------
  async function applyTypeToWorkbench(typeId: string): Promise<void> {
    const detail = await typesStore.selectType(typeId)
    if (!detail) {
      templates.value = []
      whitelist.value = { titles: [], materials: [], specs: [], colors: [], features: [] }
      return
    }
    // 1. 白名单
    whitelist.value = {
      titles: [...detail.titles],
      materials: [...detail.materials],
      specs: [...detail.specs],
      colors: [...detail.colors],
      features: [...detail.features],
    }
    // 2. 模板 = 场景（默认全选）
    const buildFromScene = (s: SceneItem, g: 'main' | 'detail'): ImageTemplate => ({
      key: s.key,
      group: g,
      size: sizeMap.value[s.size] || sizeMap.value[g] || [800, 800],
      scene_cn: s.scene_cn,
      scene_en: s.scene_en,
      selected: true,
    })
    templates.value = [
      ...detail.main_scenes.map((s) => buildFromScene(s, 'main')),
      ...detail.detail_scenes.map((s) => buildFromScene(s, 'detail')),
    ]
    // 3. 默认商品参数 = 类型配置里的默认值
    product.value = {
      title: detail.default_title || detail.titles[0] || '',
      material: detail.materials[0] || '',
      spec: detail.specs[0] || '',
      color: detail.colors[0] || '',
      features: [...(detail.default_selected_features || [])],
    }
  }

  // ---------------- 模板勾选 ----------------
  function toggleTemplate(key: string): void {
    const t = templates.value.find((x) => x.key === key)
    if (t) t.selected = !t.selected
  }
  function selectAllMain(): void {
    templates.value.forEach((t) => { if (t.group === 'main') t.selected = true })
  }
  function selectAllDetail(): void {
    templates.value.forEach((t) => { if (t.group === 'detail') t.selected = true })
  }
  function clearAllTemplates(): void {
    templates.value.forEach((t) => (t.selected = false))
  }
  function resetProductToTypeDefault(): void {
    if (typesStore.currentTypeDetail) {
      const d = typesStore.currentTypeDetail
      product.value = {
        title: d.default_title || d.titles[0] || '',
        material: d.materials[0] || '',
        spec: d.specs[0] || '',
        color: d.colors[0] || '',
        features: [...(d.default_selected_features || [])],
      }
    }
  }

  // ---------------- 表单校验 ----------------
  function validateForm(): string | null {
    if (!typesStore.hasSelected) return '请先在顶部选择类型（没有合适的去「配置中心」新增）'
    if (selectedCount.value === 0) return '请至少勾选1张图片模板'
    // 以下字段均为可选（允许"不设置"），空值跳过白名单校验
    if (product.value.title && whitelist.value.titles.length > 0 && !whitelist.value.titles.includes(product.value.title)) {
      return `商品标题「${product.value.title}」不在白名单内`
    }
    if (product.value.material && whitelist.value.materials.length > 0 && !whitelist.value.materials.includes(product.value.material)) {
      return `材质「${product.value.material}」不在白名单内`
    }
    if (product.value.spec && whitelist.value.specs.length > 0 && !whitelist.value.specs.includes(product.value.spec)) {
      return `规格「${product.value.spec}」不在白名单内`
    }
    if (product.value.color && whitelist.value.colors.length > 0 && !whitelist.value.colors.includes(product.value.color)) {
      return `颜色「${product.value.color}」不在白名单内`
    }
    return null
  }

  // ---------------- 生成 + 轮询 ----------------
  async function startGenerate(): Promise<void> {
    const errMsg = validateForm()
    if (errMsg) {
      ElMessage.warning(errMsg)
      return
    }
    if (isRunning.value) {
      ElMessage.info('当前有正在运行的任务，请等待结束')
      return
    }
    saveModelPreference(currentModel.value)
    resetTaskState(false)
    taskStatus.value = 'pending'

    const body: GenerateReqBody = {
      type_id: typesStore.currentTypeId,
      model: currentModel.value,
      only_keys: selectedTemplateKeys.value,
      dry_run: dryRun.value,
      extra_negative: extraNegative.value,
      product: product.value,
      original_image: originalImage.value || undefined,
      ref_strength: originalImage.value ? refStrength.value : undefined,
    }
    const resp = await startGeneration(body)
    taskId.value = resp.task_id
    taskTypeId.value = resp.type_id
    taskTypeName.value = resp.type_name
    taskStatus.value = 'running'
    ElMessage.success(
      `任务已启动 (${resp.task_id.slice(0, 8)}…) · 类型「${resp.type_name}」，正在轮询进度...`,
    )
    startPolling()
  }

  function startPolling(): void {
    if (pollingTimer.value) window.clearInterval(pollingTimer.value)
    logsCursor.value = 0
    pollingTimer.value = window.setInterval(async () => {
      if (!taskId.value) return
      try {
        const s = await pollTaskStatus(taskId.value, logsCursor.value)
        taskStatus.value = s.status
        taskTotal.value = s.total
        taskDone.value = s.done
        taskFailed.value = s.failed
        currentKey.value = s.current_key
        elapsedSec.value = s.elapsed
        if (s.logs.length > 0) logs.value.push(...s.logs)
        logsCursor.value = s.logs_since_next

        if (s.status === 'done') {
          stopPolling()
          await loadResults()
          await saveToMaterial()
          ElMessage.success(
            `生成完成：成功 ${taskDone.value}，失败 ${taskFailed.value}，耗时 ${s.elapsed.toFixed(1)}s`,
          )
        }
      } catch (e) {
        console.warn('[poll] 单次轮询失败', e)
      }
    }, 1500)
  }

  function stopPolling(): void {
    if (pollingTimer.value) {
      window.clearInterval(pollingTimer.value)
      pollingTimer.value = null
    }
  }

  async function loadResults(): Promise<void> {
    if (!taskId.value) return
    const r = await fetchTaskResults(taskId.value)
    generated.value = r.generated
    taskTypeId.value = r.type_id
    taskTypeName.value = r.type_name
  }

  function resetTaskState(keepImages: boolean): void {
    stopPolling()
    taskId.value = null
    taskTypeId.value = ''
    taskTypeName.value = ''
    taskStatus.value = 'pending'
    taskTotal.value = 0
    taskDone.value = 0
    taskFailed.value = 0
    currentKey.value = null
    logs.value = []
    logsCursor.value = 0
    elapsedSec.value = 0
    if (!keepImages) generated.value = []
  }

  // ---------------- 素材库持久化 ----------------
  async function saveToMaterial(): Promise<void> {
    if (generated.value.length === 0) return
    const id = currentProductId.value || `mat_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    appendMaterial({
      id,
      name: `${product.value.title.slice(0, 18)} · ${new Date().toLocaleTimeString()}`,
      createdAt: Date.now(),
      type_id: taskTypeId.value || typesStore.currentTypeId,
      type_name: taskTypeName.value || typesStore.currentTypeDetail?.type_name || '',
      product: { ...product.value, features: [...product.value.features] },
      model: currentModel.value,
      dry_run: dryRun.value,
      generated: JSON.parse(JSON.stringify(generated.value)),
      used_keys: [...selectedTemplateKeys.value],
    })
  }

  /** 设置当前商品记录ID（新建/编辑时调用） */
  function setProductId(id: string): void {
    currentProductId.value = id
  }

  /** 设置商品原始图（base64 data URL） */
  function setOriginalImage(dataUrl: string): void {
    originalImage.value = dataUrl
  }

  /** 清除商品原始图 */
  function clearOriginalImage(): void {
    originalImage.value = ''
  }

  /** 生成新商品ID */
  function genProductId(): string {
    return `prod_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
  }

  /** 素材库回填（需切换到对应的类型后再填表单+勾选模板） */
  async function applyMaterialProduct(
    p: ProductForm,
    usedKeys: string[],
    matTypeId?: string,
  ): Promise<void> {
    // 如果类型不一样，先切换类型（确保白名单/模板与素材记录一致）
    if (matTypeId && matTypeId !== typesStore.currentTypeId) {
      await applyTypeToWorkbench(matTypeId)
    }
    product.value = { ...p, features: [...p.features] }
    templates.value.forEach((t) => {
      t.selected = usedKeys.includes(t.key)
    })
    ElMessage.info(
      `已回填素材：切换到类型「${typesStore.currentTypeDetail?.type_name || matTypeId}」 + ${p.title.slice(0, 20)}`,
    )
  }

  // ---------------- 图片操作 ----------------
  function deleteImage(key: string): void {
    const item = generated.value.find((g) => g.key === key)
    if (item) item.deleted = true
  }
  function restoreImage(key: string): void {
    const item = generated.value.find((g) => g.key === key)
    if (item) item.deleted = false
  }
  async function downloadAllZip(): Promise<void> {
    const list = visibleGenerated.value
    if (list.length === 0) {
      ElMessage.warning('暂无可下载的图片')
      return
    }
    const zip = new JSZip()
    ElMessage.info(`开始打包 ${list.length} 张图片...`)
    try {
      const tasks = list.map(async (img) => {
        const resp = await fetch(img.url)
        if (!resp.ok) throw new Error(`下载 ${img.file} 失败`)
        const blob = await resp.blob()
        zip.file(img.file, blob)
      })
      await Promise.all(tasks)
      const zipBlob = await zip.generateAsync({ type: 'blob' })
      const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      saveAs(zipBlob, `1688主图详情图_${stamp}.zip`)
      ElMessage.success(`打包完成，共 ${list.length} 张`)
    } catch (e) {
      console.error(e)
      ElMessage.error(`打包失败：${e instanceof Error ? e.message : String(e)}`)
    }
  }

  async function saveApiKeysToBackend(params: { dashscope_api_key?: string; openai_api_key?: string }): Promise<boolean> {
    try {
      const resp = await saveApiKeys(params)
      if (resp.ok && resp.api_keys) {
        apiKeyStatus.value = { ...apiKeyStatus.value, ...resp.api_keys }
        return true
      }
    } catch (e) {
      console.error('[config] saveApiKeys failed', e)
    }
    return false
  }

  return {
    // state
    configReady,
    modelOptions,
    sizeMap,
    negativeBase,
    templates,
    whitelist,
    currentModel,
    product,
    dryRun,
    extraNegative,
    refStrength,
    apiKeyStatus,
    taskId,
    taskTypeId,
    taskTypeName,
    taskStatus,
    taskTotal,
    taskDone,
    taskFailed,
    currentKey,
    logs,
    generated,
    elapsedSec,
    currentProductId,
    originalImage,
    // getters
    selectedTemplateKeys,
    selectedCount,
    mainTemplates,
    detailTemplates,
    progressPercent,
    visibleGenerated,
    isRunning,
    // actions
    initConfig,
    applyTypeToWorkbench,
    toggleTemplate,
    selectAllMain,
    selectAllDetail,
    clearAllTemplates,
    resetProductToTypeDefault,
    validateForm,
    startGenerate,
    stopPolling,
    loadResults,
    resetTaskState,
    applyMaterialProduct,
    deleteImage,
    restoreImage,
    downloadAllZip,
    saveApiKeysToBackend,
    setProductId,
    setOriginalImage,
    clearOriginalImage,
    genProductId,
  }
})
