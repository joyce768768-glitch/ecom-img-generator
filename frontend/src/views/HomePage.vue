<template>
  <div class="home-page">
    <!-- ============ 顶部栏 ============ -->
    <header class="site-header flex-between">
      <div class="flex-row gap-sm logo">
        <div class="logo-icon">
          <el-icon :size="28" color="#fff"><PictureFilled /></el-icon>
        </div>
        <div class="flex-col">
          <h1 class="title">{{ appTitle }}</h1>
          <span class="sub">1688 电商类目 · 5主图 + 10详情图 · 本地一键生成</span>
        </div>
      </div>

      <div class="flex-row gap-sm actions">
        <el-tag v-if="genStore.dryRun" type="warning" effect="dark">Dry-Run 模式</el-tag>

        <!-- 商品列表按钮 -->
        <el-button @click="goToProducts">
          <el-icon><Goods /></el-icon> 商品列表
        </el-button>

        <!-- 配置中心按钮 -->
        <el-button @click="goToAdmin">
          <el-icon><Setting /></el-icon> 配置中心
        </el-button>

        <!-- 素材库按钮 -->
        <el-badge :value="matStore.recordCount" :hidden="matStore.recordCount === 0" class="mat-badge">
          <el-button @click="matStore.openDrawer()">
            <el-icon><Collection /></el-icon> 素材库
          </el-button>
        </el-badge>

        <!-- 模型配置按钮 -->
        <el-button type="primary" plain @click="configDialogVisible = true">
          <el-icon><Tools /></el-icon> 模型配置
        </el-button>
      </div>
    </header>

    <!-- ============ 主内容：左右分栏响应式 ============ -->
    <main class="main-body" v-loading="loadingConfig" element-loading-text="加载后端配置中...">
      <section class="col-left">
        <ProductForm @submit="handleFormSubmit" @before-generate="handleBeforeGenerate" />
      </section>

      <section class="col-right flex-col" style="gap: $gap;">
        <!-- Prompt 日志/进度 -->
        <PromptPreview />

        <!-- 生成结果画廊 -->
        <div class="gallery app-card">
          <div class="flex-between gallery-head">
            <div class="flex-row gap-sm">
              <h3 class="title">
                <el-icon :size="18" color="$color-success"><Picture /></el-icon>
                &nbsp;生成结果
              </h3>
              <el-tag v-if="typesStore.currentTypeDetail" type="primary" effect="plain" size="small">
                当前：{{ typesStore.currentTypeDetail.type_name }}（默认）
              </el-tag>
              <el-tag v-else type="danger" effect="plain" size="small">未选类型</el-tag>
              <el-tag v-if="genStore.visibleGenerated.length === 0" type="info" size="small">
                暂无图片
              </el-tag>
              <el-tag
                v-else
                :type="genStore.taskStatus === 'done' ? 'success' : 'warning'"
                size="small"
              >
                {{ genStore.visibleGenerated.length }} 张
              </el-tag>
            </div>

            <div class="flex-row gap-sm gallery-ops">
              <el-tooltip content="仅展示5主图" placement="top">
                <el-button
                  size="small"
                  :type="galleryFilter === 'main' ? 'primary' : 'default'"
                  @click="galleryFilter = 'main'"
                >主图</el-button>
              </el-tooltip>
              <el-tooltip content="仅展示10详情图" placement="top">
                <el-button
                  size="small"
                  :type="galleryFilter === 'detail' ? 'primary' : 'default'"
                  @click="galleryFilter = 'detail'"
                >详情</el-button>
              </el-tooltip>
              <el-tooltip content="全部展示" placement="top">
                <el-button
                  size="small"
                  :type="galleryFilter === 'all' ? 'primary' : 'default'"
                  @click="galleryFilter = 'all'"
                >全部</el-button>
              </el-tooltip>
              <el-divider direction="vertical" />
              <el-button
                size="small"
                type="success"
                :disabled="genStore.visibleGenerated.length === 0"
                @click="handleDownloadAll"
              >
                <el-icon><Download /></el-icon> 全部打包ZIP
              </el-button>
            </div>
          </div>

          <div class="gallery-body">
            <div
              v-for="img in filteredImages"
              :key="img.file"
              class="gallery-item"
            >
              <ImageCard
                :data="img"
                @preview="openPreview"
                @delete="handleDelete"
                @restore="handleRestore"
              />
            </div>
            <div v-if="filteredImages.length === 0" class="gallery-empty">
              <el-empty
                :description="genStore.visibleGenerated.length === 0
                  ? '点击「批量生成」开始创建您的第一张电商素材图'
                  : '当前筛选下暂无图片'"
              >
                <template #image>
                  <el-icon :size="56" color="#c0c4cc"><Picture /></el-icon>
                </template>
                <el-button type="primary" size="small" @click="scrollToForm">
                  去选择参数
                </el-button>
              </el-empty>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- ============ 右下角：跳转按钮 ============ -->
    <div class="nav-float-btn">
      <el-button
        v-if="isHomeRoute"
        type="primary"
        round
        @click="goToAdmin"
      >
        <el-icon><Setting /></el-icon> 配置中心
      </el-button>
      <el-button
        v-else
        type="success"
        round
        @click="goToHome"
      >
        <el-icon><House /></el-icon> 返回工作台
      </el-button>
    </div>

    <!-- ============ 图片放大预览（原生Element Image Viewer走DOM模式避免重复下载） ============ -->
    <el-image-viewer
      v-if="viewerVisible"
      :url-list="viewerUrls"
      :initial-index="viewerInitialIdx"
      @close="viewerVisible = false"
    />

    <!-- ============ 抽屉 & 弹窗 ============ -->
    <MaterialDrawer
      v-model="drawerVisibleLocal"
    />
    <ModelConfigDialog v-model="configDialogVisible" />
  </div>
</template>

<script setup lang="ts">
/**
 * HomePage.vue - 主页，左右分栏响应式布局串起所有组件
 * 核心：必须先选类型才能用
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  PictureFilled,
  Collection,
  Setting,
  Tools,
  Picture,
  Download,
  House,
  Goods,
} from '@element-plus/icons-vue'

import ProductForm from '@/components/ProductForm.vue'
import PromptPreview from '@/components/PromptPreview.vue'
import ImageCard from '@/components/ImageCard.vue'
import MaterialDrawer from '@/components/MaterialDrawer.vue'
import ModelConfigDialog from '@/components/ModelConfigDialog.vue'

import { useGenerationStore } from '@/store/modules/generation'
import { useTypesStore } from '@/store/modules/types'
import { useMaterialStore } from '@/store/modules/material'
import type { GeneratedImage } from '@/types'

const route = useRoute()
const router = useRouter()
const genStore = useGenerationStore()
const typesStore = useTypesStore()
const matStore = useMaterialStore()

const appTitle = import.meta.env.VITE_APP_TITLE || '1688 电商主图 & 详情图生成工具'

const loadingConfig = ref(false)
const galleryFilter = ref<'all' | 'main' | 'detail'>('all')

const viewerVisible = ref(false)
const viewerUrls = ref<string[]>([])
const viewerInitialIdx = ref(0)

const configDialogVisible = ref(false)
const drawerVisibleLocal = computed<boolean>({
  get: () => matStore.drawerVisible,
  set: (v: boolean) => { if (!v) matStore.closeDrawer() },
})

const isHomeRoute = computed<boolean>(() => route.path === '/' || route.name === 'Home')

const filteredImages = computed<GeneratedImage[]>(() => {
  const list = genStore.visibleGenerated
  if (galleryFilter.value === 'all') return list
  if (galleryFilter.value === 'main') return list.filter((g: GeneratedImage) => g.key.startsWith('main'))
  return list.filter((g: GeneratedImage) => g.key.startsWith('detail'))
})

function handleBeforeGenerate(): boolean {
  if (!typesStore.hasSelected) {
    ElMessage.error('请先在顶部选择类型')
    return false
  }
  return true
}

function handleFormSubmit(): void {
  const right = document.querySelector('.col-right')
  if (right) right.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function openPreview(img: GeneratedImage): void {
  const urls: string[] = filteredImages.value.map((g: GeneratedImage) => g.url)
  const idx = urls.indexOf(img.url)
  viewerUrls.value = urls
  viewerInitialIdx.value = idx >= 0 ? idx : 0
  viewerVisible.value = true
}

function handleDelete(key: string): void {
  genStore.deleteImage(key)
  ElMessage.info(`已标记删除：${key}，可在素材库恢复`)
}
function handleRestore(key: string): void {
  genStore.restoreImage(key)
  ElMessage.success(`已恢复：${key}`)
}

async function handleDownloadAll(): Promise<void> {
  await genStore.downloadAllZip()
}

function scrollToForm(): void {
  const left = document.querySelector('.col-left')
  if (left) left.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function goToAdmin(): void {
  router.push('/admin')
}
function goToHome(): void {
  router.push('/')
}
function goToProducts(): void {
  router.push('/products')
}

onMounted(async () => {
  loadingConfig.value = true
  // 从路由 query 获取商品 ID（新建/编辑时预生成）
  const queryId = route.query.product_id as string | undefined
  if (queryId) {
    genStore.setProductId(queryId)
  }
  try {
    await genStore.initConfig()
  } catch (e) {
    ElMessage.error(
      '后端连接失败！请确认 Python server.py 已启动（默认 http://127.0.0.1:8765）。错误详情：'
      + (e instanceof Error ? e.message : String(e)),
    )
  } finally {
    loadingConfig.value = false
  }
})
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
}

/* ===== 顶部栏 ===== */
.site-header {
  height: $header-height;
  padding: 0 24px;
  background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(30, 58, 138, .2);
  flex-shrink: 0;
  z-index: 10;

  .logo {
    .logo-icon {
      width: 40px; height: 40px;
      border-radius: 10px;
      background: rgba(255, 255, 255, .18);
      display: flex; align-items: center; justify-content: center;
    }
    .title {
      margin: 0; font-size: 17px; font-weight: 700;
      letter-spacing: .5px;
    }
    .sub {
      font-size: 12px;
      color: rgba(255,255,255,.78);
    }
  }
  .actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .actions :deep(.el-button),
  .actions :deep(.el-tag) {
    border: none !important;
  }
  .actions :deep(.el-select .el-input__wrapper) {
    box-shadow: none;
  }
  .actions :deep(.select-warning .el-input__wrapper) {
    box-shadow: 0 0 0 2px $color-danger inset !important;
  }
  .actions :deep(.el-select.select-warning .el-input__inner) {
    color: $color-danger;
  }
}

/* ===== 右下角浮动按钮 ===== */
.nav-float-btn {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 50;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  border-radius: 28px;
}

/* ===== 主布局 ===== */
.main-body {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(380px, 460px) 1fr;
  gap: $gap;
  padding: $gap;
  align-items: start;
}
.col-left {
  position: sticky;
  top: $gap;
  max-height: calc(100vh - #{$header-height} - #{$gap} * 2);
  overflow-y: auto;
  padding-right: 4px;

  /* 滚动条：更细更淡，thumb 高度 60px */
  &::-webkit-scrollbar { width: 5px; height: 5px; }
  &::-webkit-scrollbar-track { background: transparent; }
  &::-webkit-scrollbar-thumb {
    background: #e4e7ed;
    border-radius: 3px;
    min-height: 60px;
    &:hover { background: #c8ccd4; }
  }
}
.col-right { min-width: 0; }

/* ===== 画廊 ===== */
.gallery-head {
  margin-bottom: 12px;
  .title { margin: 0; font-size: 16px; font-weight: 600;
    display: inline-flex; align-items: center; }
}
.gallery-body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 14px;
}
.gallery-empty { padding: 40px 0; grid-column: 1 / -1; }

/* ===== 响应式：移动端 ===== */
@media (max-width: $breakpoint-mobile) {
  .site-header { padding: 0 $gap-sm; height: auto;
    flex-direction: column; gap: $gap-sm; padding: $gap-sm;
    align-items: flex-start !important;
    .actions { width: 100%; justify-content: space-between; flex-wrap: wrap; }
    .actions :deep(.el-select) { min-width: 100% !important; width: 100% !important; }
  }
  .main-body {
    grid-template-columns: 1fr;
    padding: $gap-sm;
    gap: $gap-sm;
  }
  .col-left {
    position: static;
    max-height: none;
    overflow: visible;
  }
  .gallery-ops { flex-wrap: wrap; gap: 4px !important; }
  .gallery-body { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
  .nav-float-btn { right: $gap-sm; bottom: $gap-sm; }
}
</style>
