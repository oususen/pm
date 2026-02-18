<template>
  <div class="master-menu">
    <h2 class="page-title">マスタメンテ</h2>

    <div class="master-grid">
      <RouterLink to="/masters/product" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">品番マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/product-group" class="master-tile">
        <div class="icon-box">📋</div>
        <div class="label">製品グループ</div>
      </RouterLink>

      <RouterLink to="/masters/container-capacity" class="master-tile">
        <div class="icon-box">🗃️</div>
        <div class="label">容器マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/bom" class="master-tile">
        <div class="icon-box">🧩</div>
        <div class="label">構成マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/routing" class="master-tile">
        <div class="icon-box">🛣️</div>
        <div class="label">ルーティングマスタ</div>
      </RouterLink>

      <RouterLink to="/masters/customer" class="master-tile">
        <div class="icon-box">🏢</div>
        <div class="label">得意先マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/supplier" class="master-tile">
        <div class="icon-box">🏭</div>
        <div class="label">仕入先マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/process" class="master-tile">
        <div class="icon-box">⚙️</div>
        <div class="label">工程マスタ</div>
      </RouterLink>

      <RouterLink to="/masters/line" class="master-tile">
        <div class="icon-box">🏗️</div>
        <div class="label">ラインマスタ</div>
      </RouterLink>

      <RouterLink to="/masters/calendar" class="master-tile">
        <div class="icon-box">📅</div>
        <div class="label">カレンダマスタ</div>
      </RouterLink>

      <RouterLink to="/masters/work-pattern" class="master-tile">
        <div class="icon-box">⏰</div>
        <div class="label">勤務パターン</div>
      </RouterLink>

      <RouterLink to="/masters/contact" class="master-tile">
        <div class="icon-box">📞</div>
        <div class="label">連絡先マスタ</div>
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
