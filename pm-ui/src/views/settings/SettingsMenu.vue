<template>
  <div class="master-menu">
    <h2 class="page-title">設定</h2>

    <div class="master-grid">
      <RouterLink to="/settings/users" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">ユーザー管理</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      設定メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
