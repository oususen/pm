<template>
  <div class="menu-page">
    <h2 class="page-title">消耗品メニュー</h2>
    <div class="menu-grid">
      <RouterLink v-for="tile in visibleTiles" :key="tile.to" :to="tile.to" class="menu-tile">
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label">{{ tile.label }}</div>
        <div v-if="tile.description" class="description">{{ tile.description }}</div>
      </RouterLink>
    </div>
    <p v-if="!visibleTiles.length" class="helper-text">利用できる消耗品の機能がありません。権限を確認してください。</p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { authState } from "@/auth";
import { hasPermission } from "@/router";

// 画面を追加したらここにタイルを追加する
const tiles = [
  {
    to: "/consumables/masters",
    label: "消耗品マスタ",
    icon: "🗂️",
    description: "消耗品・購入先の登録、CSV取込",
    resource: "consumables.masters",
  },
];

const visibleTiles = computed(() =>
  tiles.filter((tile) => hasPermission(authState.user, tile.resource, "view"))
);
</script>

<style scoped>
.menu-page { padding: 12px; }
.page-title { font-size: 1.2em; margin: 0 0 10px; }
.menu-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
.menu-tile { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 12px 8px; border: 1px solid #ddd; border-radius: 8px; background: #fff; color: inherit; text-decoration: none; }
.menu-tile:hover { border-color: #1565c0; background: #f0f6ff; }
.icon-box { font-size: 1.8em; }
.label { font-weight: 600; }
.description { font-size: 0.75em; color: #666; text-align: center; }
.helper-text { color: #666; font-size: 0.85em; }
</style>
