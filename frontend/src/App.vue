<template>
  <el-config-provider :locale="zhCnLocale" :size="'default'">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
/**
 * App.vue - 应用根组件
 * 仅挂载 RouterView + ElementPlus 中文语言包
 * 业务布局在 views/HomePage.vue
 */
import zhCnLocale from 'element-plus/es/locale/lang/zh-cn'
</script>

<style lang="scss" scoped>
/* 根容器样式在 global.scss 中定义 */
</style>
