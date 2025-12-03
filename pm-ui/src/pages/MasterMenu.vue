<template>
  <div class="master-menu">
    <h2 class="page-title">マスタメンテ</h2>

    <div class="master-grid">
      <RouterLink to="/masters/product" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">品番マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/bom" class="master-tile">
        <div class="icon-box">🧩</div>
        <div class="label">構成マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/customer" class="master-tile">
        <div class="icon-box">🏢</div>
        <div class="label">取引先マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/calendar" class="master-tile">
        <div class="icon-box">📅</div>
        <div class="label">カレンダマスタ</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      ※タイルをクリックすると各マスタ画面へ遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
