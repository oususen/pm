<template>
  <div class="task-menu">
    <h2 class="page-title">タスク設定</h2>
    <div class="tile-grid">
      <RouterLink v-for="tile in tiles" :key="tile.title" :to="tile.to" class="tile">
        <div class="tile-title">{{ tile.title }}</div>
        <div class="tile-desc">{{ tile.desc }}</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from "vue-router";
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const canAccess = (resource) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const hasSpecific = permissions.some((item) => item.resource === resource)
  if (hasSpecific) {
    return hasPermission(user, resource, 'view')
  }
  return hasPermission(user, 'settings', 'view')
}

const allTiles = [
  {
    to: '/settings/auto-plan',
    title: '自動計画',
    desc: 'ライン別/順序の自動計画設定を管理します。',
    resource: 'settings.scheduled_tasks',
  },
  {
    to: { path: '/settings/inventory-task-settings', query: { mode: 'inventory' } },
    title: '取り込み・在庫計算・進度計算（定時タスク）',
    desc: '需要取り込みと在庫関連の定時計算を設定します。',
    resource: 'settings.scheduled_tasks',
  },
  {
    to: { path: '/settings/scheduled-tasks', query: { mode: 'order-expansion' } },
    title: '自動受注展開',
    desc: 'OPEN受注をLineDemandへ展開する定時実行を設定します。',
    resource: 'settings.scheduled_tasks',
  },
  {
    to: { path: '/settings/scheduled-tasks', query: { mode: 'safety-stock' } },
    title: '自動安全在庫',
    desc: '社内品・購入品ごとの自動安全在庫タスクを設定します。',
    resource: 'settings.scheduled_tasks',
  },
  {
    to: '/settings/purchase-order-approval',
    title: '承認者設定',
    desc: '発注提案書の承認レベル別ユーザーを設定します。',
    resource: 'settings.purchase_order_approval',
  },
]

const tiles = computed(() => allTiles.filter((tile) => canAccess(tile.resource)))
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

