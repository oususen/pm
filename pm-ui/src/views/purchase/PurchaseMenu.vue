<template>
  <div class="master-menu">
    <h2 class="page-title">仕入れ管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/purchase/plan-input" class="master-tile">
        <div class="icon-box">📦</div>
        <div class="label">仕入れ計画</div>
      </RouterLink>
      <RouterLink to="/purchase/inventory" class="master-tile">
        <div class="icon-box">📊</div>
        <div class="label">在庫/残量</div>
      </RouterLink>
      <RouterLink to="/purchase/progress-only" class="master-tile">
        <div class="icon-box">📈</div>
        <div class="label">仕入れ進度のみ</div>
      </RouterLink>
      <RouterLink to="/purchase/actual-input" class="master-tile">
        <div class="icon-box">🧾</div>
        <div class="label">仕入れ実績入力</div>
      </RouterLink>
      <RouterLink to="/purchase/actual-inquiry" class="master-tile">
        <div class="icon-box">📋</div>
        <div class="label">納入実績照会</div>
      </RouterLink>
      <RouterLink to="/purchase/supplier-calendar" class="master-tile">
        <div class="icon-box">🗓️</div>
        <div class="label">仕入れ先カレンダ</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      仕入れ管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>
