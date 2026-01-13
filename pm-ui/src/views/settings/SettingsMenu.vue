<template>
  <div class="master-menu">
    <h2 class="page-title">設定</h2>

    <div class="master-grid">
      <RouterLink to="/settings/users" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">ユーザー管理</div>
      </RouterLink>
      <RouterLink to="/settings/permission-templates" class="master-tile">
        <div class="icon-box">👤</div>
        <div class="label">権限テンプレート</div>
      </RouterLink>
      <RouterLink to="/settings/smtp" class="master-tile">
        <div class="icon-box">📧</div>
        <div class="label">SMTP設定</div>
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
