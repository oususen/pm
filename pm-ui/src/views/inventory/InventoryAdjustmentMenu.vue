<template>
  <div class="adjustment-menu">
    <h2 class="page-title">在庫調整メニュー</h2>
    <div class="tile-grid">
      <RouterLink to="/inventory/adjustments/progress" class="tile">
        <div class="tile-icon">📈</div>
        <div class="tile-title">進度調整</div>
        <div class="tile-desc">進度の補正値を登録します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments/stock" class="tile">
        <div class="tile-icon">📦</div>
        <div class="tile-title">在庫調整</div>
        <div class="tile-desc">在庫の補正値を登録します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments/history" class="tile">
        <div class="tile-icon">📋</div>
        <div class="tile-title">調整履歴</div>
        <div class="tile-desc">調整値の登録履歴を確認します。</div>
      </RouterLink>
    </div>
    <p class="helper-text">在庫調整メニューから各調整画面へ遷移します。</p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.adjustment-menu {
  padding: 12px 10px 18px;
  background: #efefdc;
  min-height: 100%;
}
.page-title {
  margin: 0 0 12px;
  font-size: 24px;
  font-weight: 700;
  color: #111827;
}
.tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 220px));
  gap: 12px;
}
.tile {
  display: block;
  text-decoration: none;
  color: #111827;
  background: #e5e7eb;
  border: 1px solid #c7ced9;
  border-radius: 12px;
  padding: 12px 14px;
  min-height: 92px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}
.tile:hover {
  border-color: #94a3b8;
  background: #dde1e7;
}
.tile-icon {
  font-size: 20px;
  line-height: 1;
  margin-bottom: 8px;
}
.tile-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}
.tile-desc {
  font-size: 13px;
  color: #475569;
}
.helper-text {
  margin-top: 14px;
  color: #64748b;
  font-size: 14px;
}
@media (max-width: 800px) {
  .page-title {
    font-size: 20px;
  }
  .tile-title {
    font-size: 20px;
  }
}
</style>
