<template>
  <div class="inventory-menu">
    <h2 class="page-title">在庫管理メニュー</h2>
    <div class="tile-grid">
      <RouterLink v-if="canViewStocktakeInput" to="/inventory/stocktake-input" class="tile">
        <div class="tile-icon">🗂️</div>
        <div class="tile-title">棚卸現物入力</div>
        <div class="tile-desc">場所・工程・写真を見ながら現物数を入力します。</div>
      </RouterLink>
      <RouterLink v-if="canViewStocktakeInput" to="/inventory/stocktake-results" class="tile">
        <div class="tile-icon">📊</div>
        <div class="tile-title">棚卸結果確認</div>
        <div class="tile-desc">棚卸入力結果を一覧表で確認します。</div>
      </RouterLink>
      <RouterLink v-if="canViewStocktakeLayout" to="/inventory/stocktake-layout" class="tile">
        <div class="tile-icon">🗺️</div>
        <div class="tile-title">棚卸レイアウト編集</div>
        <div class="tile-desc">倉庫の棚・設備の配置をグリッドで編集します。</div>
      </RouterLink>
      <RouterLink to="/inventory/adjustments" class="tile">
        <div class="tile-icon">🛠️</div>
        <div class="tile-title">調整</div>
        <div class="tile-desc">進度/在庫/計画在庫/計画進度の調整画面へ遷移します。</div>
      </RouterLink>
      <RouterLink to="/inventory/actual-progress" class="tile">
        <div class="tile-icon">🧮</div>
        <div class="tile-title">実進度求め</div>
        <div class="tile-desc">在庫合計と親別需要窓から実進度を算出します。</div>
      </RouterLink>
    </div>
    <p class="helper-text">在庫管理メニューから機能に遷移します。</p>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
import { computed } from "vue";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

const canViewStocktakeInput = computed(() =>
  hasPermission(authState.user, "stocktake", "view")
);
const canViewStocktakeLayout = computed(() =>
  hasPermission(authState.user, "stocktake.layout", "view")
);
</script>

<style scoped>
.inventory-menu {
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
