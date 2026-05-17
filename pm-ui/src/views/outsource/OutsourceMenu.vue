<template>
  <div class="master-menu">
    <h2 class="page-title">FB外作管理</h2>

    <div class="master-grid">
      <RouterLink
        v-for="tile in tiles"
        :key="tile.key"
        :to="tile.to"
        class="master-tile"
      >
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label">{{ tile.label }}</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";

const tiles = [
  { key: 'import', icon: '📥', label: '受注取込', to: '/outsource/orders/import' },
  { key: 'orders', icon: '📋', label: '受注一覧', to: '/outsource/orders' },
  { key: 'export', icon: '📤', label: 'Excel出力', to: '/outsource/excel-export' },
  { key: 'splits', icon: '📊', label: '分割計画取込', to: '/outsource/splits/import' },
  { key: 'materials', icon: '🔩', label: '材料所要量', to: '/outsource/materials' },
  { key: 'procurement', icon: '🚚', label: '材料手配', to: '/outsource/procurement' },
  { key: 'delivery', icon: '📦', label: '納入・出荷', to: '/outsource/delivery' },
  { key: 'progress', icon: '📈', label: '進捗管理', to: '/outsource/progress' },
  { key: 'masters', icon: '⚙️', label: 'マスタ管理', to: '/outsource/masters' },
];
</script>

<style scoped>
.master-menu { padding: 16px; }
.page-title { margin-bottom: 16px; font-size: 18px; }
.master-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.master-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 8px;
  border: 1px solid #ddd;
  border-radius: 8px;
  text-decoration: none;
  color: #333;
  transition: box-shadow 0.15s;
}
.master-tile:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.icon-box { font-size: 28px; margin-bottom: 8px; }
.label { font-size: 13px; text-align: center; }
</style>
