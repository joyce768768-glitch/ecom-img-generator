<template>
  <div class="admin-page">
    <!-- ============ 顶部栏 ============ -->
    <header class="site-header flex-between">
      <div class="flex-row gap-sm logo">
        <div class="logo-icon">
          <el-icon :size="28" color="#fff"><Setting /></el-icon>
        </div>
        <div class="flex-col">
          <h1 class="title">类型配置中心</h1>
          <span class="sub">多类目白名单 + 15图场景Prompt + System段</span>
        </div>
      </div>

      <div class="flex-row gap-sm actions">
        <el-button type="success" :icon="House" @click="goToHome">
          返回工作台
        </el-button>
        <el-upload
          :show-file-list="false"
          accept="application/json"
          :before-upload="handleBeforeImport"
          style="display: inline-block"
        >
          <el-button :icon="Upload">导入JSON</el-button>
        </el-upload>
        <el-button :icon="Download" @click="typesStore.exportFile">导出JSON</el-button>
        <el-button :icon="Refresh" @click="refreshAll" :loading="typesStore.loadingList">刷新</el-button>
      </div>
    </header>

    <!-- ============ 主区：两栏布局 ============ -->
    <main class="main-body">
      <!-- 左栏：类型卡片列表 -->
      <aside class="type-list-col">
        <div class="col-header">
          <h3>类型列表</h3>
          <el-badge
            :value="typesStore.slimList.length"
            class="count-badge"
            type="primary"
            effect="light"
          />
        </div>
        <div class="slim-scroll" v-loading="typesStore.loadingList">
          <div
            v-for="t in typesStore.slimList"
            :key="t.type_id"
            :class="['type-card', { 'is-selected': t.type_id === currentDraftId }]"
            @click="selectCardType(t.type_id)"
          >
            <div class="card-type-id">{{ t.type_id }}</div>
            <div class="flex-between card-head">
              <span class="card-title">{{ t.type_name }}</span>
              <div class="flex-row gap-xs">
                <el-tag size="small" type="primary" effect="plain">主{{ t.main_count }}</el-tag>
                <el-tag size="small" type="success" effect="plain">详{{ t.detail_count }}</el-tag>
              </div>
            </div>
            <div class="wl-summary">
              <span class="wl-chip">标题:{{ t.titles_count }}</span>
              <span class="wl-chip">材质:{{ t.materials_count }}</span>
              <span class="wl-chip">规格:{{ t.specs_count }}</span>
              <span class="wl-chip">颜色:{{ t.colors_count }}</span>
              <span class="wl-chip">卖点:{{ t.features_count }}</span>
            </div>
            <div class="card-ops" @click.stop>
              <el-button size="small" type="primary" plain :icon="Edit" @click="openRenameDialog(t)">编辑</el-button>
              <el-button size="small" :icon="CopyDocument" @click="openDuplicateDialog(t)">复制</el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :icon="Delete"
                :disabled="typesStore.slimList.length <= 1"
                @click="handleDeleteCard(t.type_id)"
              >删除</el-button>
            </div>
          </div>
          <!-- 新增类型按钮 -->
          <div class="add-type-card" @click="openCreateDialog">
            <el-icon :size="24"><Plus /></el-icon>
            <span>新增类型</span>
          </div>
          <el-empty
            v-if="typesStore.slimList.length === 0"
            description="暂无类型，点击下方「新增类型」创建"
            :image-size="80"
          />
        </div>
      </aside>

      <!-- 右栏：详情编辑 -->
      <section class="detail-col" v-loading="typesStore.loadingDetail">
        <template v-if="draft">
          <!-- 4 个 Tabs -->
          <div class="app-card tabs-card">
            <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
              <!-- ============ Tab1 白名单配置 ============ -->
              <el-tab-pane label="白名单配置" name="whitelist">
                <div class="wl-groups">
                  <template v-for="(g, key) in wlGroups" :key="key">
                    <div class="wl-group">
                      <div class="flex-between wl-head">
                        <div class="flex-row gap-xs">
                          <el-tag type="info" effect="dark">{{ g.label }}</el-tag>
                          <span class="wl-count">{{ draft[key].length }} 项</span>
                        </div>
                        <div class="flex-row gap-xs">
                          <el-button size="small" :icon="Plus" @click="addChipInput(key)">新增1项</el-button>
                          <el-button
                            size="small"
                            type="primary"
                            plain
                            :icon="DocumentCopy"
                            @click="openBulkDialog(key as WhitelistKey)"
                          >📋 粘贴批量添加</el-button>
                        </div>
                      </div>
                      <div class="chip-box" :class="{ 'is-empty': draft[key].length === 0 }">
                        <template v-for="(v, idx) in draft[key]" :key="`${key}-${idx}-${v}`">
                          <el-tag
                            class="wl-tag"
                            closable
                            type="primary"
                            effect="light"
                            @close="removeChip(key, idx)"
                          >
                            <span class="chip-val">{{ v }}</span>
                          </el-tag>
                        </template>
                        <el-input
                          v-if="addChipMap[key] === true"
                          v-model="chipInputValMap[key]"
                          size="small"
                          class="new-chip-input"
                          placeholder="按回车添加"
                          @keyup.enter="confirmAddChip(key)"
                          @blur="confirmAddChip(key)"
                          :ref="(el: any) => setChipRef(key as WhitelistKey, el)"
                        />
                        <el-empty
                          v-if="draft[key].length === 0 && addChipMap[key] !== true"
                          description="暂无项，点击右侧按钮添加"
                          :image-size="60"
                        />
                      </div>
                    </div>
                  </template>

                  <!-- 默认勾选卖点 -->
                  <div class="wl-group">
                    <div class="flex-between wl-head">
                      <div class="flex-row gap-xs">
                        <el-tag type="warning" effect="dark">默认勾选卖点</el-tag>
                        <span class="wl-count">{{ draft.default_selected_features.length }} 项</span>
                        <span class="hint">从「核心卖点」白名单中勾选</span>
                      </div>
                      <el-button
                        size="small"
                        type="warning"
                        plain
                        @click="selectAllDefaultFeatures"
                        :disabled="draft.features.length === 0"
                      >全选白名单卖点</el-button>
                    </div>
                    <div class="feature-check">
                      <el-checkbox
                        v-if="draft.features.length === 0"
                        disabled
                        label="请先在「核心卖点」白名单中添加值"
                      />
                      <el-checkbox
                        v-for="fv in draft.features"
                        :key="`df-${fv}`"
                        :model-value="draft.default_selected_features.includes(fv)"
                        :label="fv"
                        @change="toggleDefaultFeature(fv, $event)"
                      >{{ fv }}</el-checkbox>
                    </div>
                  </div>
                </div>
              </el-tab-pane>

              <!-- ============ Tab2 主图场景 5张 ============ -->
              <el-tab-pane label="主图场景（5张）" name="main">
                <SceneTable
                  :rows="draft.main_scenes"
                  default-size="main"
                  @update="onSceneUpdate('main', $event)"
                />
              </el-tab-pane>

              <!-- ============ Tab3 详情场景 10张 ============ -->
              <el-tab-pane label="详情场景（10张）" name="detail">
                <SceneTable
                  :rows="draft.detail_scenes"
                  default-size="detail"
                  @update="onSceneUpdate('detail', $event)"
                />
              </el-tab-pane>

              <!-- ============ Tab4 System段 & 重置 ============ -->
              <el-tab-pane label="System段 & 重置" name="system">
                <div class="system-card">
                  <div class="flex-between sys-head">
                    <div>
                      <h4>类目专属 System Prompt 追加段</h4>
                      <p class="hint">当 model 生成的 Prompt 中 System Block 会自动拼接该段内容。可填写类目专属风格要求，如"衣架产品需展示旋转多角度展示其承重与防滑功能"等。</p>
                    </div>
                    <el-tag type="info" effect="plain">建议英文</el-tag>
                  </div>
                  <el-input
                    v-model="draft.system_extra_prompt"
                    type="textarea"
                    :rows="12"
                    placeholder="例如：Product e-commerce hero shot for hanger category. Always show functional hanger angles (close-up of hooks, non-slip pads, load bearing). Pure white seamless background. High-key studio lighting. Clean white seamless e-commerce style background for all shots."
                    @input="markDirty"
                  />
                </div>
                <div class="danger-zone app-card">
                  <h4 class="danger-title">危险操作</h4>
                  <div class="flex-row gap-md">
                    <el-button
                      type="warning"
                      plain
                      :icon="RefreshLeft"
                      :disabled="!origId"
                      @click="resetToDefault"
                    >重置该类型为衣架默认值</el-button>
                    <el-button
                      type="danger"
                      :icon="Delete"
                      :disabled="!origId || typesStore.slimList.length <= 1"
                      @click="handleDeleteCurrent"
                    >删除该类型</el-button>
                    <el-tag
                      v-if="typesStore.slimList.length <= 1"
                      type="warning"
                      effect="plain"
                    >至少保留 1 个类型，不可删除最后一个</el-tag>
                  </div>
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- ============ 底部操作栏 sticky ============ -->
          <div class="save-bar app-card">
            <div class="flex-between">
              <div class="flex-row gap-sm left">
                <span v-if="dirty" class="dirty-dot"></span>
                <span class="save-status" :class="{ warn: dirty }">
                  {{ dirty ? '有未保存的改动' : (lastSaved ? `最近保存 ${lastSaved}` : '尚未保存') }}
                </span>
              </div>
              <div class="flex-row gap-sm right">
                <el-button
                  :icon="RefreshLeft"
                  :disabled="!dirty"
                  @click="cancelRestore"
                >取消还原</el-button>
                <el-button
                  type="primary"
                  :icon="Check"
                  :disabled="!dirty || !canSave"
                  :loading="typesStore.saving"
                  @click="handleSave"
                >保存类型</el-button>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="app-card no-select">
          <el-empty description="请在左侧选择类型，或右上角新建类型" :image-size="120">
            <el-button type="primary" :icon="Plus" @click="openCreateDialog">立即新建</el-button>
          </el-empty>
        </div>
      </section>
    </main>

    <!-- ============ 新增类型 Dialog ============ -->
    <el-dialog
      v-model="createDialogVisible"
      title="新增类型"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form label-width="110px">
        <el-form-item label="type_id" required>
          <el-input
            v-model="createForm.type_id"
            placeholder="例如：hanger_abs"
            :disabled="typesStore.saving"
          />
          <div class="form-hint">仅创建时可编辑，由 字母/数字/_ 组成</div>
        </el-form-item>
        <el-form-item label="类型名称" required>
          <el-input
            v-model="createForm.type_name"
            placeholder="例如：衣架-ABS塑料成人款"
            :disabled="typesStore.saving"
          />
        </el-form-item>
        <el-form-item label="基于复制">
          <el-select
            v-model="createForm.copy_from_id"
            placeholder="空 = 创建空模板（只有空字段）"
            clearable
            style="width: 100%"
            :disabled="typesStore.saving"
          >
            <el-option
              v-for="t in typesStore.slimList"
              :key="t.type_id"
              :label="`${t.type_name}（主${t.main_count}/详${t.detail_count}）`"
              :value="t.type_id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false" :disabled="typesStore.saving">取消</el-button>
        <el-button type="primary" :loading="typesStore.saving" @click="submitCreate">确认创建</el-button>
      </template>
    </el-dialog>

    <!-- ============ 重命名类型 Dialog ============ -->
    <el-dialog
      v-model="renameDialogVisible"
      title="编辑类型名称"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item label="type_id">
          <el-tag type="info" effect="plain">{{ renameSrc?.type_id }}</el-tag>
          <div class="form-hint">类型ID不可修改</div>
        </el-form-item>
        <el-form-item label="类型名称" required>
          <el-input
            v-model="renameForm.type_name"
            placeholder="例如：衣架-ABS塑料成人款"
            :disabled="typesStore.saving"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameDialogVisible = false" :disabled="typesStore.saving">取消</el-button>
        <el-button type="primary" :loading="typesStore.saving" @click="submitRename">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 复制类型 Dialog ============ -->
    <el-dialog
      v-model="dupDialogVisible"
      title="复制类型"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-width="110px">
        <el-form-item label="源类型">
          <el-tag type="primary" effect="plain">{{ dupSrc?.type_name }}</el-tag>
        </el-form-item>
        <el-form-item label="新 type_id" required>
          <el-input v-model="dupForm.new_type_id" placeholder="例如：hanger_metal" />
        </el-form-item>
        <el-form-item label="新名称" required>
          <el-input v-model="dupForm.new_name" placeholder="例如：衣架-金属款" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dupDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="typesStore.saving" @click="submitDuplicate">确认复制</el-button>
      </template>
    </el-dialog>

    <!-- ============ 批量粘贴 Dialog ============ -->
    <el-dialog
      v-model="bulkDialogVisible"
      :title="`批量粘贴添加：${wlGroups[bulkKey]?.label ?? ''}`"
      width="560px"
      :close-on-click-modal="false"
    >
      <div class="bulk-hint">支持 逗号 / 换行 / 顿号 / 分号 / 竖线 多种分隔符，自动去重后合并</div>
      <el-input
        v-model="bulkText"
        type="textarea"
        :rows="10"
        :placeholder="bulkPlaceholder"
      />
      <div class="bulk-preview" v-if="parsedBulk.length > 0">
        <el-tag type="success" effect="plain">共解析 {{ parsedBulk.length }} 项</el-tag>
        <div class="flex-row gap-xs flex-wrap chips-preview">
          <el-tag v-for="(p, i) in parsedBulk.slice(0, 30)" :key="i" size="small" type="info" effect="plain">{{ p }}</el-tag>
          <span v-if="parsedBulk.length > 30" class="hint">... 还有 {{ parsedBulk.length - 30 }} 项</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="bulkDialogVisible = false">取消</el-button>
        <el-button type="primary" :disabled="parsedBulk.length === 0" @click="submitBulk">确认追加</el-button>
      </template>
    </el-dialog>

    <!-- ============ 导入 Dialog ============ -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入类型配置"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form label-width="100px">
        <el-form-item label="文件">
          <el-tag type="info" effect="plain">{{ importFile?.name }}</el-tag>
        </el-form-item>
        <el-form-item label="导入模式" required>
          <el-radio-group v-model="importMode">
            <el-radio value="merge">合并（type_id 相同覆盖，不同追加）</el-radio>
            <el-radio value="replace">替换（清空当前所有后导入）</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="typesStore.saving" @click="submitImport">确认导入</el-button>
      </template>
    </el-dialog>

    <!-- 右下角：回到顶部 -->
    <el-backtop :right="24" :bottom="96" />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Check,
  CopyDocument,
  Delete,
  DocumentCopy,
  Download,
  Edit,
  House,
  Plus,
  Refresh,
  RefreshLeft,
  Setting,
  Upload,
} from '@element-plus/icons-vue'
import { useTypesStore } from '@/store/modules/types'
import type {
  SceneItem,
  TypeFull,
  TypePayload,
  TypeSlim,
} from '@/types'
import SceneTable from '@/components/SceneTable.vue'

const router = useRouter()
const typesStore = useTypesStore()

type WhitelistKey = 'titles' | 'materials' | 'specs' | 'colors' | 'features'
type SceneKey = 'main' | 'detail'

const wlGroups: Record<WhitelistKey, { label: string }> = {
  titles: { label: '标题白名单' },
  materials: { label: '材质白名单' },
  specs: { label: '规格白名单' },
  colors: { label: '颜色白名单' },
  features: { label: '核心卖点白名单' },
}

// ---------------- state ----------------
const activeTab = ref<'whitelist' | 'main' | 'detail' | 'system'>('whitelist')
const dirty = ref(false)
const lastSaved = ref('')
const origId = ref<string>('')
const draft = ref<TypeFull | null>(null)

const createDialogVisible = ref(false)
const dupDialogVisible = ref(false)
const renameDialogVisible = ref(false)
const bulkDialogVisible = ref(false)
const importDialogVisible = ref(false)

const createForm = reactive({
  type_id: '',
  type_name: '',
  copy_from_id: '',
})
const dupSrc = ref<TypeSlim | null>(null)
const dupForm = reactive({ new_type_id: '', new_name: '' })
const renameSrc = ref<TypeSlim | null>(null)
const renameForm = reactive({ type_name: '' })
const bulkKey = ref<WhitelistKey>('titles')
const bulkText = ref('')

const importFile = ref<File | null>(null)
const importMode = ref<'merge' | 'replace'>('merge')

const currentDraftId = computed(() => draft.value?.type_id ?? typesStore.currentTypeId)

const addChipMap = reactive<Record<WhitelistKey, boolean>>({
  titles: false,
  materials: false,
  specs: false,
  colors: false,
  features: false,
})
const chipInputValMap = reactive<Record<WhitelistKey, string>>({
  titles: '',
  materials: '',
  specs: '',
  colors: '',
  features: '',
})
const _chipInputRefHolder = reactive<Record<string, { focus: () => void }>>({})
function setChipRef(key: WhitelistKey, el: unknown): void {
  if (el) _chipInputRefHolder[key] = el as { focus: () => void }
}

// ---------------- getters ----------------
const canSave = computed<boolean>(() => {
  if (!draft.value) return false
  const d = draft.value
  if (!d.type_id.trim() || !d.type_name.trim()) return false
  return true
})

const bulkPlaceholder = computed(() => {
  const label = wlGroups[bulkKey.value]?.label ?? ''
  return `粘贴${label}值，例如：\nABS塑料\n不锈钢\n铝合金\n榉木\n...`
})

const parsedBulk = computed<string[]>(() => {
  if (!bulkText.value.trim()) return []
  const raw = bulkText.value
  const items = raw
    .split(/[,，、；;\|\n\r\t]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
  const set = new Set<string>()
  items.forEach((i) => set.add(i))
  return Array.from(set)
})

// ---------------- draft clone/snapshot ----------------
function _buildEmptyTypePayload(id: string, name: string): TypeFull {
  return {
    type_id: id,
    type_name: name,
    default_title: '',
    titles: [],
    materials: [],
    specs: [],
    colors: [],
    features: [],
    default_selected_features: [],
    main_scenes: [],
    detail_scenes: [],
    system_extra_prompt: '',
    created_at: Date.now(),
    updated_at: Date.now(),
  }
}

function _cloneDraft<T extends object>(o: T): T {
  return JSON.parse(JSON.stringify(o))
}

function applyDraftFromTypeFull(src: TypeFull | null, isNew = false): void {
  if (!src) {
    draft.value = null
    origId.value = ''
    dirty.value = false
    return
  }
  draft.value = _cloneDraft(src)
  origId.value = isNew ? '' : src.type_id
  dirty.value = isNew
  lastSaved.value = isNew ? '' : _formatTime()
}

function _formatTime(): string {
  const d = new Date()
  const p = (n: number) => n.toString().padStart(2, '0')
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
}

function markDirty(): void {
  dirty.value = true
}

// ---------------- 左栏 / 选择 ----------------
async function selectCardType(typeId: string): Promise<void> {
  if (dirty.value && draft.value && draft.value.type_id !== typeId) {
    try {
      await ElMessageBox.confirm(
        '当前类型有未保存的改动，切换类型后将丢失未保存内容，确认继续？',
        '未保存提示',
        { type: 'warning', confirmButtonText: '丢弃并切换', cancelButtonText: '取消' },
      )
    } catch (_e) {
      return
    }
  }
  const detail = await typesStore.selectType(typeId)
  applyDraftFromTypeFull(detail, false)
}

async function refreshAll(): Promise<void> {
  await typesStore.loadList()
  if (typesStore.currentTypeId) {
    const d = await typesStore.selectType(typesStore.currentTypeId)
    applyDraftFromTypeFull(d, false)
  }
}

// ---------------- 白名单 chip 操作 ----------------
async function addChipInput(key: WhitelistKey): Promise<void> {
  addChipMap[key] = true
  chipInputValMap[key] = ''
  await nextTick()
  _chipInputRefHolder[key]?.focus()
}

function confirmAddChip(key: WhitelistKey): void {
  if (addChipMap[key] !== true) return
  const v = chipInputValMap[key].trim()
  addChipMap[key] = false
  chipInputValMap[key] = ''
  if (!v || !draft.value) return
  if (draft.value[key].includes(v)) {
    ElMessage.warning('值已存在')
    return
  }
  draft.value[key].push(v)
  markDirty()
}

function removeChip(key: WhitelistKey, idx: number): void {
  if (!draft.value) return
  draft.value[key].splice(idx, 1)
  if (key === 'features') {
    const kept = draft.value[key]
    draft.value.default_selected_features = draft.value.default_selected_features.filter((f) =>
      kept.includes(f),
    )
  }
  markDirty()
}

function toggleDefaultFeature(val: string, checked: unknown): void {
  if (!draft.value) return
  const arr = draft.value.default_selected_features
  if (checked) {
    if (!arr.includes(val)) arr.push(val)
  } else {
    const i = arr.indexOf(val)
    if (i >= 0) arr.splice(i, 1)
  }
  markDirty()
}

function selectAllDefaultFeatures(): void {
  if (!draft.value) return
  draft.value.default_selected_features = [...draft.value.features]
  markDirty()
}

// ---------------- 批量粘贴 ----------------
function openBulkDialog(key: WhitelistKey): void {
  bulkKey.value = key
  bulkText.value = ''
  bulkDialogVisible.value = true
}

function submitBulk(): void {
  if (!draft.value) return
  const cur = draft.value[bulkKey.value]
  const set = new Set<string>(cur)
  parsedBulk.value.forEach((i) => set.add(i))
  draft.value[bulkKey.value] = Array.from(set)
  bulkDialogVisible.value = false
  markDirty()
}

// ---------------- Scene 操作 ----------------
function onSceneUpdate(which: SceneKey, next: SceneItem[]): void {
  if (!draft.value) return
  if (which === 'main') {
    draft.value.main_scenes = next
  } else {
    draft.value.detail_scenes = next
  }
  markDirty()
}

// ---------------- 新增 / 复制 / 删除 ----------------
function openCreateDialog(): void {
  const ts = Date.now().toString().slice(-6)
  createForm.type_id = `new_type_${ts}`
  createForm.type_name = ''
  createForm.copy_from_id = ''
  createDialogVisible.value = true
}

async function submitCreate(): Promise<void> {
  if (!createForm.type_id.trim() || !createForm.type_name.trim()) {
    ElMessage.warning('请填写 type_id 和 名称')
    return
  }
  const id = createForm.type_id.trim()
  const name = createForm.type_name.trim()
  let payload: TypePayload
  if (createForm.copy_from_id) {
    const src = await typesStore.selectType(createForm.copy_from_id)
    if (!src) {
      ElMessage.error('源类型不存在')
      return
    }
    const cloned: TypeFull = _cloneDraft(src)
    payload = {
      type_id: id,
      type_name: name,
      default_title: cloned.default_title,
      titles: cloned.titles,
      materials: cloned.materials,
      specs: cloned.specs,
      colors: cloned.colors,
      features: cloned.features,
      default_selected_features: cloned.default_selected_features,
      main_scenes: cloned.main_scenes,
      detail_scenes: cloned.detail_scenes,
      system_extra_prompt: cloned.system_extra_prompt,
    }
  } else {
    const empty = _buildEmptyTypePayload(id, name)
    payload = {
      type_id: empty.type_id,
      type_name: empty.type_name,
      default_title: empty.default_title,
      titles: empty.titles,
      materials: empty.materials,
      specs: empty.specs,
      colors: empty.colors,
      features: empty.features,
      default_selected_features: empty.default_selected_features,
      main_scenes: empty.main_scenes,
      detail_scenes: empty.detail_scenes,
      system_extra_prompt: empty.system_extra_prompt,
    }
  }
  const created = await typesStore.create(payload)
  if (created) {
    createDialogVisible.value = false
    applyDraftFromTypeFull(created, false)
    await typesStore.selectType(created.type_id)
  }
}

function openDuplicateDialog(t: TypeSlim): void {
  dupSrc.value = t
  dupForm.new_type_id = `${t.type_id}_copy`
  dupForm.new_name = `${t.type_name}（副本）`
  dupDialogVisible.value = true
}

function openRenameDialog(t: TypeSlim): void {
  renameSrc.value = t
  renameForm.type_name = t.type_name
  renameDialogVisible.value = true
}

async function submitRename(): Promise<void> {
  if (!renameSrc.value) return
  const name = renameForm.type_name.trim()
  if (!name) {
    ElMessage.warning('请填写类型名称')
    return
  }
  const res = await typesStore.update(renameSrc.value.type_id, { type_name: name })
  if (res) {
    renameDialogVisible.value = false
    if (draft.value && draft.value.type_id === renameSrc.value!.type_id) {
      draft.value.type_name = name
      markDirty()
    }
  }
}

async function submitDuplicate(): Promise<void> {
  if (!dupSrc.value) return
  if (!dupForm.new_type_id.trim() || !dupForm.new_name.trim()) {
    ElMessage.warning('请填写新 type_id 和名称')
    return
  }
  const res = await typesStore.duplicate(
    dupSrc.value.type_id,
    dupForm.new_name.trim(),
    dupForm.new_type_id.trim(),
  )
  if (res) {
    dupDialogVisible.value = false
  }
}

async function handleDeleteCard(typeId: string): Promise<void> {
  const ok = await typesStore.remove(typeId)
  if (ok && typeId === currentDraftId.value) {
    applyDraftFromTypeFull(typesStore.currentTypeDetail, false)
  }
}

async function handleDeleteCurrent(): Promise<void> {
  if (!origId.value) return
  const ok = await typesStore.remove(origId.value)
  if (ok) {
    applyDraftFromTypeFull(typesStore.currentTypeDetail, false)
  }
}

function resetToDefault(): void {
  // 清空为 空模板（不去后端做 reset，保留现有默认衣架的内容通过复制方式重建）
  ElMessageBox.confirm(
    '确认重置当前类型所有字段为空模板？（白名单、场景、System段全部清空）',
    '重置类型',
    { type: 'warning', confirmButtonText: '确认重置', cancelButtonText: '取消' },
  )
    .then(() => {
      if (!draft.value) return
      const id = draft.value.type_id
      const name = draft.value.type_name
      const empty = _buildEmptyTypePayload(id, name)
      applyDraftFromTypeFull(empty, true)
    })
    .catch(() => {})
}

// ---------------- 保存 / 取消还原 ----------------
function cancelRestore(): void {
  if (!origId.value) {
    // 新建未保存，直接清空 draft
    applyDraftFromTypeFull(null, false)
    return
  }
  // 从 store 里重新拉详情覆盖
  typesStore
    .selectType(origId.value)
    .then((d) => applyDraftFromTypeFull(d, false))
    .catch(() => {})
}

async function handleSave(): Promise<void> {
  if (!draft.value || !canSave.value) return
  const d = draft.value
  const payload: TypePayload = {
    type_id: d.type_id,
    type_name: d.type_name,
    default_title: d.default_title,
    titles: [...d.titles],
    materials: [...d.materials],
    specs: [...d.specs],
    colors: [...d.colors],
    features: [...d.features],
    default_selected_features: [...d.default_selected_features],
    main_scenes: d.main_scenes.map((s) => ({ ...s })),
    detail_scenes: d.detail_scenes.map((s) => ({ ...s })),
    system_extra_prompt: d.system_extra_prompt,
  }
  const id = origId.value
  let saved: TypeFull | null
  if (!id) {
    saved = await typesStore.create(payload)
  } else {
    saved = await typesStore.update(id, payload)
  }
  if (saved) {
    applyDraftFromTypeFull(saved, false)
    lastSaved.value = _formatTime()
  }
}

// ---------------- 导入 ----------------
function handleBeforeImport(file: File): boolean {
  importFile.value = file
  importMode.value = 'merge'
  importDialogVisible.value = true
  return false // 阻止自动上传，手动 submitImport
}

async function submitImport(): Promise<void> {
  if (!importFile.value) return
  const ok = await typesStore.importFile(importFile.value, importMode.value)
  if (ok) {
    importDialogVisible.value = false
    importFile.value = null
    // 导入后选中第一个
    const first = typesStore.slimList[0]
    if (first) {
      const d = await typesStore.selectType(first.type_id)
      applyDraftFromTypeFull(d, false)
    }
  }
}

// ---------------- 路由跳转 ----------------
function goToHome(): void {
  if (dirty.value) {
    ElMessageBox.confirm(
      '当前有未保存的改动，离开后将丢失，确认继续？',
      '未保存提示',
      { type: 'warning', confirmButtonText: '丢弃并离开', cancelButtonText: '取消' },
    )
      .then(() => router.push('/'))
      .catch(() => {})
    return
  }
  router.push('/')
}

function handleTabChange(_tab: string): void {
  // 预留
}

// ---------------- 生命周期 ----------------
onMounted(async () => {
  await typesStore.loadList()
  const first = typesStore.slimList[0]
  if (first) {
    const d = await typesStore.selectType(first.type_id)
    applyDraftFromTypeFull(d, false)
  }
  window.addEventListener('beforeunload', _blockIfDirty)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', _blockIfDirty)
})

function _blockIfDirty(e: BeforeUnloadEvent): void {
  if (dirty.value) {
    e.preventDefault()
    e.returnValue = '有未保存的改动，确认离开？'
  }
}
</script>

<style lang="scss" scoped>
.admin-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: $bg-main;
  color: $text-primary;
  position: relative;
}

.site-header {
  height: $header-height;
  padding: 0 24px;
  background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2);
  flex-shrink: 0;
  z-index: 10;

  .logo {
    .logo-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: rgba(255, 255, 255, 0.18);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .title {
      font-size: 20px;
      font-weight: 700;
      margin: 0;
      line-height: 1.3;
    }
    .sub {
      font-size: 12px;
      color: rgba(255, 255, 255, 0.75);
    }
  }
  .actions {
    .count-badge {
      margin-left: 8px;
    }
  }
}

.main-body {
  flex: 1;
  display: flex;
  gap: $gap;
  padding: 24px;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  position: relative;
}

.type-list-col {
  width: 320px;
  border-right: 1px solid $border-color;
  padding-right: $gap-md;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .col-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $gap-sm;

    h3 {
      margin: 0;
      font-size: 15px;
      font-weight: 600;
    }
  }
  .slim-scroll {
    flex: 1;
    overflow-y: auto;
    padding-right: 4px;
    display: flex;
    flex-direction: column;
    gap: $gap-sm;
  }
}

.type-card {
  position: relative;
  border: 1px solid $border-color;
  border-radius: $radius;
  padding: $gap-md;
  background: #fff;
  cursor: pointer;
  transition: all 0.18s;

  &:hover {
    border-color: $primary-light;
    box-shadow: 0 2px 8px rgba($primary, 0.08);
  }
  &.is-selected {
    border-left: 4px solid $primary;
    background: linear-gradient(90deg, rgba($primary, 0.06) 0%, #fff 40%);
    border-color: $primary;
  }

  .card-type-id {
    font-size: 11px;
    color: $text-secondary;
    font-family: monospace;
    margin-bottom: 4px;
  }
  .card-head {
    .card-title {
      font-weight: 600;
      font-size: 14px;
    }
  }
  .wl-summary {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    .wl-chip {
      display: inline-block;
      padding: 1px 6px;
      border-radius: 4px;
      background: $bg-soft;
      font-size: 11px;
      color: $text-secondary;
    }
  }
  .card-ops {
    margin-top: 10px;
    display: flex;
    justify-content: flex-end;
    gap: 4px;
  }
}

.add-type-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 20px;
  border: 2px dashed $border-color;
  border-radius: $radius;
  background: $bg-soft;
  cursor: pointer;
  transition: all 0.18s;
  color: $text-secondary;
  font-size: 13px;

  &:hover {
    border-color: $primary;
    color: $primary;
    background: rgba($primary, 0.04);
  }
}

.detail-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $gap-md;
  position: relative;
  padding-bottom: 88px;

  .tabs-card {
    padding: 0;
    :deep(.el-tabs__header) {
      margin: 0;
    }
    :deep(.el-tabs__content) {
      padding: $gap-md;
    }
  }

  .no-select {
    padding: $gap-md;
  }
}

// 白名单分组
.wl-groups {
  display: flex;
  flex-direction: column;
  gap: $gap-md;
}
.wl-group {
  border: 1px solid $border-color;
  border-radius: $radius;
  padding: $gap-md;
  background: $bg-soft;
}
.wl-head {
  margin-bottom: $gap-sm;
  .wl-count {
    font-size: 12px;
    color: $text-secondary;
  }
  .hint {
    font-size: 12px;
    color: $text-placeholder;
    margin-left: 8px;
  }
}
.chip-box {
  background: #fff;
  border: 1px dashed $border-color;
  border-radius: $radius-sm;
  padding: $gap-sm;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: flex-start;
  min-height: 56px;

  &.is-empty {
    min-height: 96px;
    align-items: center;
    justify-content: center;
  }

  .wl-tag {
    :deep(.el-tag__content) {
      max-width: 420px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
      vertical-align: middle;
    }
    .chip-val {
      font-size: 13px;
    }
  }
  .new-chip-input {
    width: 240px;
  }
}

.feature-check {
  background: #fff;
  border: 1px dashed $border-color;
  border-radius: $radius-sm;
  padding: $gap-sm;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;

  :deep(.el-checkbox) {
    margin-right: 0;
  }
}

// System 段
.system-card {
  border: 1px solid $border-color;
  border-radius: $radius;
  padding: $gap-md;
  background: $bg-soft;

  .sys-head {
    margin-bottom: $gap-sm;
    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
    .hint {
      font-size: 12px;
      color: $text-secondary;
      margin: 4px 0 0 0;
      line-height: 1.6;
    }
  }
}

.danger-zone {
  margin-top: $gap-md;
  border: 1px solid rgba($color-danger, 0.3);
  background: rgba($color-danger, 0.03);

  .danger-title {
    margin: 0 0 $gap-sm 0;
    font-size: 14px;
    font-weight: 600;
    color: $color-danger;
  }
}

// sticky 底部保存栏
.save-bar {
  position: sticky;
  bottom: 16px;
  z-index: 5;
  padding: $gap-sm $gap-md;
  border: 1px solid $border-color;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);

  .left {
    align-items: center;
  }
  .dirty-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: $color-warning;
    box-shadow: 0 0 0 3px rgba($color-warning, 0.2);
  }
  .save-status {
    font-size: 13px;
    color: $text-secondary;
    &.warn {
      color: $color-warning;
      font-weight: 500;
    }
  }
}

.bulk-hint {
  font-size: 12px;
  color: $text-secondary;
  margin-bottom: 8px;
}
.bulk-preview {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  .chips-preview {
    margin-top: 4px;
    max-height: 180px;
    overflow: auto;
    border: 1px dashed $border-color;
    padding: $gap-sm;
    border-radius: $radius-sm;
  }
}

.form-hint {
  font-size: 12px;
  color: $text-placeholder;
  margin-top: 4px;
}
</style>
