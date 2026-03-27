<template>
  <div class="master-menu">
    <h2 class="page-title">マスタメンテ</h2>

    <div class="master-grid">
      <RouterLink
        v-for="tile in visibleTiles"
        :key="tile.to"
        :to="tile.to"
        class="master-tile"
        :class="{ 'is-disabled': tile.disabled }"
        :aria-disabled="tile.disabled ? 'true' : 'false'"
        :tabindex="tile.disabled ? -1 : 0"
        @click="(event) => onTileClick(event, tile)"
      >
        <div class="icon-box">{{ tile.icon }}</div>
        <div class="label">{{ tile.label }}</div>
      </RouterLink>
    </div>

    <p class="helper-text">
      ※タイルをクリックすると各マスタ画面へ遷移します。
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const PERMISSION_MODE = 'hide'

const findPermission = (user, resource) => {
  if (!user) return null
  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  return permissions.find((item) => item.resource === resource) || null
}

const hasMenuPermission = (resource, level) => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true

  const entry = findPermission(user, resource)
  if (entry) {
    return level === 'edit'
      ? Boolean(entry.can_edit)
      : Boolean(entry.can_view || entry.can_edit)
  }

  return hasPermission(user, 'masters', level)
}

const tiles = computed(() => {
  const list = [
    { to: '/masters/product', label: '品番マスタ', icon: '📦', required: 'view', resource: 'masters.product' },
    { to: '/masters/product-group', label: '製品グループ', icon: '📋', required: 'view', resource: 'masters.product_group' },
    { to: '/masters/container-capacity', label: '容器マスタ', icon: '🗃️', required: 'view', resource: 'masters.container_capacity' },
    { to: '/masters/equipment', label: '設備マスタ', icon: '🛠️', required: 'view', resource: 'masters.equipment' },
    { to: '/masters/bom', label: '構成マスタ', icon: '🧩', required: 'view', resource: 'masters.bom' },
    { to: '/masters/routing', label: 'ルーティングマスタ', icon: '🛣️', required: 'view', resource: 'masters.routing' },
    { to: '/masters/customer', label: '得意先マスタ', icon: '🏢', required: 'view', resource: 'masters.customer' },
    { to: '/masters/supplier', label: '仕入先マスタ', icon: '🏭', required: 'view', resource: 'masters.supplier' },
    { to: '/masters/process', label: '工程マスタ', icon: '⚙️', required: 'view', resource: 'masters.process' },
    { to: '/masters/line', label: 'ラインマスタ', icon: '🏗️', required: 'view', resource: 'masters.line' },
    { to: '/masters/calendar', label: 'カレンダマスタ', icon: '📅', required: 'view', resource: 'masters.calendar' },
    { to: '/masters/work-pattern', label: '勤務パターン', icon: '⏰', required: 'view', resource: 'masters.work_pattern' },
    { to: '/masters/contact', label: '連絡先マスタ', icon: '📞', required: 'view', resource: 'masters.contact' },
  ]

  return list.map((tile) => ({
    ...tile,
    disabled: !hasMenuPermission(tile.resource, tile.required),
  }))
})

const visibleTiles = computed(() => {
  if (PERMISSION_MODE === 'hide') {
    return tiles.value.filter((tile) => !tile.disabled)
  }
  return tiles.value
})

const onTileClick = (event, tile) => {
  if (tile.disabled) {
    event.preventDefault()
  }
}
</script>
