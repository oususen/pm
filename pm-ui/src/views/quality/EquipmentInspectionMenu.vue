<template>
  <div class="master-menu">
    <h2 class="page-title">設備点検表</h2>

    <div class="master-grid">
      <RouterLink to="/quality/equipment-inspection/master" class="master-tile">
        <div class="icon-box">📝</div>
        <div class="label">点検項目作成</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      将来的に作業標準書も同じ品質メニュー配下に追加予定です。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
