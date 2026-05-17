<template>
  <div class="master-menu">
    <h2 class="page-title">FB外作管理</h2>

    <div
      v-for="group in tileGroups"
      :key="group.key"
      class="menu-group"
    >
      <h3 class="group-title">{{ group.title }}</h3>
      <div class="master-grid">
        <RouterLink
          v-for="tile in group.tiles"
          :key="tile.key"
          :to="tile.to"
          class="master-tile"
        >
          <div class="icon-box">{{ tile.icon }}</div>
          <div class="label">{{ tile.label }}</div>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from "vue-router";

const tileGroups = [
  {
    key: 'orders',
    title: '受注・計画',
    tiles: [
      { key: 'import', icon: '📥', label: '受注取込', to: '/outsource/orders/import' },
      { key: 'orders', icon: '📋', label: '受注一覧', to: '/outsource/orders' },
      { key: 'export', icon: '📤', label: 'Excel出力', to: '/outsource/excel-export' },
      { key: 'splits', icon: '📊', label: '分割計画取込', to: '/outsource/splits/import' },
    ],
  },
  {
    key: 'materials',
    title: '材料',
    tiles: [
      { key: 'procurement', icon: '🚚', label: '材料手配', to: '/outsource/procurement' },
      { key: 'receiving', icon: '📥', label: '材料検収', to: '/outsource/material-receiving' },
      { key: 'materials', icon: '🔩', label: '材料支給', to: '/outsource/materials' },
    ],
  },
  {
    key: 'stock',
    title: '在庫',
    tiles: [
      { key: 'material-stock', icon: '🧱', label: '材料在庫', to: '/outsource/material-stock' },
      { key: 'product-stock', icon: '📦', label: '完成品在庫', to: '/outsource/product-stock' },
    ],
  },
  {
    key: 'execution',
    title: '実績・進捗',
    tiles: [
      { key: 'delivery', icon: '📦', label: '納入・出荷', to: '/outsource/delivery' },
      { key: 'progress', icon: '📈', label: '進捗管理', to: '/outsource/progress' },
    ],
  },
  {
    key: 'master',
    title: '設定',
    tiles: [
      { key: 'masters', icon: '⚙️', label: 'マスタ管理', to: '/outsource/masters' },
    ],
  },
];
</script>

<style scoped>
.master-menu { padding: 16px; }
.page-title { margin-bottom: 16px; font-size: 18px; }
.menu-group { margin-bottom: 12px; }
.group-title { font-size: 14px; margin: 0 0 6px; color: #374151; }
.master-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}
.master-tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 6px;
  border: 1px solid #ddd;
  border-radius: 6px;
  text-decoration: none;
  color: #333;
  transition: box-shadow 0.15s;
}
.master-tile:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.icon-box { font-size: 14px; margin-bottom: 8px; }
.label { font-size: 13px; text-align: center; }
</style>
