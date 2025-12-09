<template>
  <div class="master-menu">
    <h2 class="page-title">生産管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/production/progress" class="master-tile">
        <div class="icon-box">📈</div>
        <div class="label">進捗管理</div>
      </RouterLink>

      <RouterLink to="/production/line-demands" class="master-tile">
        <div class="icon-box">🧭</div>
        <div class="label">ライン需要一覧</div>
      </RouterLink>

      <RouterLink to="/production/inventory" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">在庫/残量一覧</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      生産管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
