<template>
  <div class="inventory-menu">
    <h2 class="page-title">在庫管理メニュー</h2>
    <div class="tile-grid">
      <RouterLink to="/inventory/adjustments" class="tile">
        <div class="tile-title">調整</div>
        <div class="tile-desc">進度/在庫/計画在庫/計画進度の調整画面へ遷移します。</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.inventory-menu {
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
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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
  font-size: 14px;
  color: #4b5563;
}
</style>
