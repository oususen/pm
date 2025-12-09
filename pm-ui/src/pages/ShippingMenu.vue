<template>
  <div class="master-menu">
    <h2 class="page-title">出荷管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/shipping/instruction" class="master-tile">
        <div class="icon-box">🚚</div>
        <div class="label">出荷指示</div>
      </RouterLink>

      <RouterLink to="/shipping/actual" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">出荷実績</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      出荷管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
