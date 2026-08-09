/**
 * main.ts - Vue 应用入口
 * 注册：ElementPlus(全量，本地工具无需按需加载)+ 全部图标 + Pinia + Router
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import * as ElIcons from '@element-plus/icons-vue'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import '@/styles/global.scss'

const app = createApp(App)

// 全量注册 Element Plus 图标
for (const [name, component] of Object.entries(ElIcons)) {
  app.component(name, component as never)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
