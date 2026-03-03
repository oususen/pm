<template>
  <div class="master-menu">
    <h2 class="page-title">品質管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/quality/equipment-inspection" class="master-tile">
        <div class="icon-box">🧰</div>
        <div class="label">設備点検表</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      品質管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
