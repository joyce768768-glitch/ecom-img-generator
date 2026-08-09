/**
 * router/index.ts - Vue Router 配置（单页面仅一个主页路由）
 */
import { createRouter, createWebHashHistory, type RouteLocationNormalized, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue'),
    meta: { title: '工作台' },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminPage.vue'),
    meta: { title: '配置中心' },
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('@/views/ProductListPage.vue'),
    meta: { title: '商品信息列表' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to: RouteLocationNormalized) => {
  const appTitle = (import.meta.env.VITE_APP_TITLE as string) || '电商主图详情图生成工具'
  if (to.meta && typeof to.meta.title === 'string') {
    document.title = `${to.meta.title} - ${appTitle}`
  } else {
    document.title = appTitle
  }
})

export default router
