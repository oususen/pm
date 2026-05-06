<template>
  <div class="task-menu">
    <h2 class="page-title">自動計画</h2>
    <div class="tile-grid">
      <RouterLink to="/settings/scheduled-tasks" class="tile">
        <div class="tile-title">ライン別自動計画</div>
        <div class="tile-desc">ラインごとの設定確認と個別の今すぐ実行を行います。</div>
      </RouterLink>
      <RouterLink to="/settings/auto-plan-sequence" class="tile">
        <div class="tile-title">ライン順序自動計画</div>
        <div class="tile-desc">実行順序を決めて自動計画を順次実行します。</div>
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


