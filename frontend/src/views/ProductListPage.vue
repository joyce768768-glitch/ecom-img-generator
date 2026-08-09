<template>
  <div class="product-list-page">
    <!-- ============ 顶部栏 ============ -->
    <header class="site-header flex-between">
      <div class="flex-row gap-sm logo">
        <div class="logo-icon">
          <el-icon :size="28" color="#fff"><Goods /></el-icon>
        </div>
        <div class="flex-col">
          <h1 class="title">商品信息列表</h1>
          <span class="sub">每套生成记录独立管理 · 编辑 / 复制 / 删除</span>
        </div>
      </div>

      <div class="flex-row gap-sm actions">
        <el-button type="primary" :icon="Plus" @click="handleCreate">新建</el-button>
        <el-button :icon="House" @click="goToHome">返回工作台</el-button>
        <el-button :icon="Setting" @click="goToAdmin">配置中心</el-button>
      </div>
    </header>

    <!-- ============ 主区：商品卡片网格 ============ -->
    <main class="main-body">
      <div class="toolbar flex-between">
        <div class="flex-row gap-sm">
          <el-tag type="primary" effect="plain">共 {{ matStore.recordCount }} 条</el-tag>
          <el-input
            v-model="searchText"
            placeholder="搜索商品名称 / 类型"
            :prefix-icon="Search"
            clearable
            style="width: 240px"
            size="small"
          />
        </div>
        <el-button :icon="Refresh" size="small" @click="matStore.refresh()">刷新</el-button>
      </div>

      <div v-if="filteredRecords.length === 0" class="empty-state app-card">
        <el-empty :description="matStore.recordCount === 0 ? '暂无商品记录，点击「新建」开始生成' : '无匹配记录'">
          <template #image>
            <el-icon :size="56" color="#c0c4cc"><Goods /></el-icon>
          </template>
          <el-button v-if="matStore.recordCount === 0" type="primary" :icon="Plus" @click="handleCreate">新建</el-button>
        </el-empty>
      </div>

      <div v-else class="product-grid">
        <div
          v-for="rec in filteredRecords"
          :key="rec.id"
          class="product-card app-card"
        >
          <!-- 缩略图 -->
          <div class="card-thumb">
            <img
              v-if="rec.generated.length > 0"
              :src="rec.generated[0].url"
              :alt="rec.name"
              @error="onImgError"
            />
            <el-icon v-else :size="40" color="#c0c4cc"><Picture /></el-icon>
            <div class="thumb-count">
              <el-tag size="small" type="primary" effect="dark">{{ rec.generated.length }} 张</el-tag>
            </div>
          </div>

          <!-- 信息 -->
          <div class="card-body">
            <div class="card-id">{{ rec.id }}</div>
            <div class="card-name ellipsis" :title="rec.name">{{ rec.name }}</div>
            <div class="card-meta">
              <el-tag size="small" type="info" effect="plain">{{ rec.type_name || rec.type_id }}</el-tag>
              <span class="meta-time">{{ formatTime(rec.createdAt) }}</span>
            </div>
            <div class="card-product">
              <span class="ellipsis">标题：{{ rec.product.title || '—' }}</span>
              <span class="ellipsis">材质：{{ rec.product.material || '—' }}</span>
              <span class="ellipsis">规格：{{ rec.product.spec || '—' }}</span>
              <span class="ellipsis">颜色：{{ rec.product.color || '—' }}</span>
            </div>
          </div>

          <!-- 操作 -->
          <div class="card-ops">
            <el-button size="small" type="primary" plain :icon="Edit" @click="handleEdit(rec)">编辑</el-button>
            <el-button size="small" :icon="CopyDocument" @click="handleCopy(rec)">复制</el-button>
            <el-button size="small" type="danger" plain :icon="Delete" @click="handleDelete(rec)">删除</el-button>
          </div>
        </div>
      </div>
    </main>

    <!-- ============ 右下角浮动按钮 ============ -->
    <div class="nav-float-btn">
      <el-button type="primary" round @click="handleCreate">
        <el-icon><Plus /></el-icon> 新建商品
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ProductListPage.vue - 商品信息列表
 * 每套生成记录 = 一条商品数据，支持新建/编辑/复制/删除
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Goods,
  Plus,
  House,
  Setting,
  Edit,
  CopyDocument,
  Delete,
  Refresh,
  Search,
  Picture,
} from '@element-plus/icons-vue'
import { useMaterialStore } from '@/store/modules/material'
import { useGenerationStore } from '@/store/modules/generation'
import type { MaterialRecord } from '@/types'

const router = useRouter()
const matStore = useMaterialStore()
const genStore = useGenerationStore()

const searchText = ref('')

const filteredRecords = computed<MaterialRecord[]>(() => {
  const list = matStore.records
  const q = searchText.value.trim().toLowerCase()
  if (!q) return list
  return list.filter(
    (r) =>
      r.name.toLowerCase().includes(q) ||
      r.type_name.toLowerCase().includes(q) ||
      r.type_id.toLowerCase().includes(q) ||
      r.product.title.toLowerCase().includes(q),
  )
})

function formatTime(ts: number): string {
  const d = new Date(ts)
  const p = (n: number) => n.toString().padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 新建：预生成 id，跳转到工作台 */
function handleCreate(): void {
  const id = genStore.genProductId()
  genStore.setProductId(id)
  router.push({ path: '/', query: { product_id: id } })
}

/** 编辑：回填数据到工作台 */
async function handleEdit(rec: MaterialRecord): Promise<void> {
  genStore.setProductId(rec.id)
  router.push({ path: '/', query: { product_id: rec.id } })
  // 等待工作台挂载后再回填
  setTimeout(() => {
    matStore.reuseRecord(rec)
  }, 300)
}

/** 复制 */
function handleCopy(rec: MaterialRecord): void {
  matStore.duplicateRecord(rec.id)
}

/** 删除 */
async function handleDelete(rec: MaterialRecord): Promise<void> {
  await matStore.deleteRecord(rec.id)
}

function onImgError(e: Event): void {
  const img = e.target as HTMLImageElement
  img.style.display = 'none'
}

function goToHome(): void {
  router.push('/')
}
function goToAdmin(): void {
  router.push('/admin')
}

onMounted(() => {
  matStore.refresh()
})
</script>

<style lang="scss" scoped>
.product-list-page {
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
}

/* ===== 主区 ===== */
.main-body {
  flex: 1;
  padding: $gap;
  overflow-y: auto;
}

.toolbar {
  margin-bottom: $gap;
}

.empty-state {
  padding: 60px 0;
  text-align: center;
}

/* ===== 商品卡片网格 ===== */
.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: $gap;
}

.product-card {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
  transition: all 0.2s;

  &:hover {
    box-shadow: $shadow-hover;
    transform: translateY(-2px);
  }

  .card-thumb {
    position: relative;
    width: 100%;
    height: 180px;
    background: #f5f7fa;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .thumb-count {
      position: absolute;
      top: 8px;
      right: 8px;
    }
  }

  .card-body {
    padding: 12px 14px;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .card-id {
    font-size: 11px;
    color: $color-info;
    font-family: monospace;
  }

  .card-name {
    font-size: 14px;
    font-weight: 600;
    color: #303133;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: 8px;

    .meta-time {
      font-size: 12px;
      color: $color-info;
    }
  }

  .card-product {
    display: flex;
    flex-direction: column;
    gap: 2px;
    font-size: 12px;
    color: #606266;
    line-height: 1.5;

    span {
      max-width: 100%;
    }
  }

  .card-ops {
    display: flex;
    gap: 6px;
    padding: 10px 14px;
    border-top: 1px solid #f0f0f0;
    background: #fafafa;
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

/* ===== 响应式 ===== */
@media (max-width: $breakpoint-mobile) {
  .site-header { padding: 0 $gap-sm; }
  .main-body { padding: $gap-sm; }
  .product-grid { grid-template-columns: 1fr; }
  .nav-float-btn { right: $gap-sm; bottom: $gap-sm; }
}
</style>
