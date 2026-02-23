<template>
  <div class="adjustment-menu">
    <h2 class="page-title">在庫調整メニュー</h2>
    <div class="tile-grid">
      <RouterLink to="/inventory/adjustments/progress" class="tile">
        <div class="tile-title">進度調整</div>
        <div class="tile-desc">進度の補正値を登録します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments/stock" class="tile">
        <div class="tile-title">在庫調整</div>
        <div class="tile-desc">在庫の補正値を登録します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments/planned-stock" class="tile">
        <div class="tile-title">計画在庫調整</div>
        <div class="tile-desc">計画在庫の補正値を登録します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments/planned-progress" class="tile">
        <div class="tile-title">計画進度調整</div>
        <div class="tile-desc">計画進度の補正値を登録します。</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.adjustment-menu {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}
.tile {
  display: block;
  text-decoration: none;
  color: #1f2a44;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 14px;
}
.tile:hover {
  border-color: #6f89bf;
  background: #f8fbff;
}
.tile-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 6px;
}
.tile-desc {
  font-size: 12px;
  color: #4b5563;
}
</style>
