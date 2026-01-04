<template>
  <div class="master-menu">
    <h2 class="page-title">生産管理メニュー</h2>

    <div class="master-grid">
      <RouterLink to="/production/mobile-process-input" class="master-tile">
        <div class="icon-box">📱</div>
        <div class="label">工程作業入力</div>
      </RouterLink>

      <RouterLink to="/production/scrap-record" class="master-tile">
        <div class="icon-box">🛠️</div>
        <div class="label">仕損品記録</div>
      </RouterLink>

      <RouterLink to="/production/plan-input" class="master-tile">
        <div class="icon-box" aria-label="計画">📝</div>
        <div class="label">生産計画入力</div>
      </RouterLink>

      <RouterLink to="/production/inventory" class="master-tile">
        <div class="icon-box" aria-label="在庫">📦</div>
        <div class="label">在庫/残量一覧</div>
      </RouterLink>

      <RouterLink to="/production/scrap-history" class="master-tile">
        <div class="icon-box">📜</div>
        <div class="label">仕損履歴</div>
      </RouterLink>

      <RouterLink to="/production/progress" class="master-tile">
        <div class="icon-box" aria-label="進捗">📊</div>
        <div class="label">進捗管理</div>
      </RouterLink>

      <RouterLink to="/production/line-demands" class="master-tile">
        <div class="icon-box" aria-label="需要">📈</div>
        <div class="label">ライン需要一覧</div>
      </RouterLink>

      <RouterLink to="/production/line-calendars" class="master-tile">
        <div class="icon-box" aria-label="勤">⏱</div>
        <div class="label">ライン勤務カレンダ</div>
      </RouterLink>

      <RouterLink to="/production/stock-allocations" class="master-tile">
        <div class="icon-box" aria-label="引当">🎯</div>
        <div class="label">在庫引当</div>
      </RouterLink>

      <RouterLink to="/production/orders" class="master-tile">
        <div class="icon-box" aria-label="指示">🛠️</div>
        <div class="label">製造指示</div>
      </RouterLink>

      <RouterLink to="/production/sequence-board" class="master-tile accent">
        <div class="icon-box">🎛</div>
        <div class="label">ミックス順序ボード</div>
      </RouterLink>

      <RouterLink to="/production/line-monitor" class="master-tile accent">
        <div class="icon-box">📺</div>
        <div class="label">ライン稼働監視</div>
      </RouterLink>

      <RouterLink to="/production/mobile-input" class="master-tile">
        <div class="icon-box">📱</div>
        <div class="label">モバイル作業入力（ライン）</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      生産管理メニューから各機能に遷移します。
    </p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.master-menu {
  padding: 16px;
}
.master-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.master-tile .icon-box {
  font-size: 22px;
}
.master-tile .label {
  font-weight: 700;
}
.master-tile.accent {
  border: 1px solid #4f46e5;
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.18);
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
</style>
