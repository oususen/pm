<template>
  <div class="task-menu">
    <h2 class="page-title">タスク設定</h2>
    <div class="tile-grid">
      <RouterLink to="/settings/auto-plan" class="tile">
        <div class="tile-title">自動計画</div>
        <div class="tile-desc">ライン別/順序の自動計画設定を管理します。</div>
      </RouterLink>
      <RouterLink :to="{ path: '/settings/inventory-task-settings', query: { mode: 'inventory' } }" class="tile">
        <div class="tile-title">取り込み・在庫計算・進度計算（定時タスク）</div>
        <div class="tile-desc">需要取り込みと在庫関連の定時計算を設定します。</div>
      </RouterLink>
      <RouterLink :to="{ path: '/settings/scheduled-tasks', query: { mode: 'order-expansion' } }" class="tile">
        <div class="tile-title">自動受注展開</div>
        <div class="tile-desc">OPEN受注をLineDemandへ展開する定時実行を設定します。</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.task-menu {
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
  font-size: 12px;
  color: #4b5563;
}
</style>
