<template>
  <div class="master-menu">
    <h2 class="page-title">設備点検表</h2>

    <div class="master-grid">
      <RouterLink to="/quality/equipment-inspection/master" class="master-tile">
        <div class="icon-box">📝</div>
        <div class="label">点検項目作成</div>
      </RouterLink>
      <RouterLink to="/quality/equipment-inspection/operation" class="master-tile">
        <div class="icon-box">🛠</div>
        <div class="label">点検実施</div>
      </RouterLink>
      <RouterLink to="/quality/equipment-inspection/monthly-review" class="master-tile">
        <div class="icon-box">📅</div>
        <div class="label">月間確認</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      点検項目作成・日次実施・週次/月次確認を同じ設備点検表メニューで運用します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
