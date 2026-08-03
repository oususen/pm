<template>
  <div class="master-menu">
    <h2 class="page-title">マスタメンテ</h2>

    <div class="menu-sections">
      <section
        v-for="(section, index) in groupedTiles"
        :key="section.key"
        class="menu-section"
        :class="{ 'has-divider': index > 0 }"
      >
        <h3 class="section-title">{{ section.label }}</h3>
        <div class="master-grid">
          <RouterLink
            v-for="tile in section.items"
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
            <div v-if="tile.description" class="description">{{ tile.description }}</div>
          </RouterLink>
        </div>
      </section>
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
const SECTION_ORDER = ['product', 'structure', 'business', 'operations', 'other']
const SECTION_LABELS = {
  product: '製品・仕様',
  structure: '工程・構成',
  business: '取引先',
  operations: '運用カレンダ',
  other: 'その他',
}

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
    { to: '/masters/product', label: '品番マスタ', icon: '📦', category: 'product', required: 'view', resource: 'masters.product' },
    { to: '/masters/product-code-mapping', label: '品番変換マスタ', icon: '🔁', description: '受注品番を社内計画品番へ変換する設定\nYD40006696→YD40006696_TATA', category: 'product', required: 'view', resource: 'masters.product' },
    { to: '/masters/product-group', label: '製品グループ', icon: '📋', category: 'product', required: 'view', resource: 'masters.product_group' },
    { to: '/masters/container-capacity', label: '容器マスタ', icon: '🗃️', category: 'product', required: 'view', resource: 'masters.container_capacity' },
    { to: '/masters/equipment', label: '設備マスタ', icon: '🛠️', category: 'structure', required: 'view', resource: 'masters.equipment' },
    { to: '/masters/bom', label: '構成マスタ', icon: '🧩', category: 'structure', required: 'view', resource: 'masters.bom' },
    { to: '/masters/routing', label: 'ルーティングマスタ', icon: '🛣️', category: 'structure', required: 'view', resource: 'masters.routing' },
    { to: '/masters/process', label: '工程マスタ', icon: '⚙️', category: 'structure', required: 'view', resource: 'masters.process' },
    { to: '/masters/line', label: 'ラインマスタ', icon: '🏗️', category: 'structure', required: 'view', resource: 'masters.line' },
    { to: '/masters/customer', label: '得意先マスタ', icon: '🏢', category: 'business', required: 'view', resource: 'masters.customer' },
    { to: '/masters/supplier', label: '仕入先マスタ', icon: '🏭', category: 'business', required: 'view', resource: 'masters.supplier' },
    { to: '/masters/contact', label: '連絡先マスタ', icon: '📞', category: 'business', required: 'view', resource: 'masters.contact' },
    { to: '/masters/calendar', label: 'カレンダマスタ', icon: '📅', category: 'operations', required: 'view', resource: 'masters.calendar' },
    { to: '/masters/work-pattern', label: '勤務パターン', icon: '⏰', category: 'operations', required: 'view', resource: 'masters.work_pattern' },
    { to: '/masters/kubota-sakai-truck', label: 'クボタ堺便マスタ', icon: '🚚', category: 'other', required: 'view', resource: 'masters.kubota_sakai_truck' },
    { to: '/masters/sourcing-bulk-change', label: '加工先一括変更', icon: '🔄', description: '外作⇔社内の切替をBOM・ルーティング一括変更', category: 'structure', required: 'edit', resource: 'masters.bom' },
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

const groupedTiles = computed(() => {
  const buckets = SECTION_ORDER.map((key) => ({
    key,
    label: SECTION_LABELS[key],
    items: [],
  }))
  const indexMap = Object.fromEntries(SECTION_ORDER.map((key, index) => [key, index]))
  for (const tile of visibleTiles.value) {
    const key = tile.category && indexMap[tile.category] !== undefined ? tile.category : 'other'
    buckets[indexMap[key]].items.push(tile)
  }
  return buckets.filter((section) => section.items.length)
})

const onTileClick = (event, tile) => {
  if (tile.disabled) {
    event.preventDefault()
  }
}
</script>

<style scoped>
.master-menu {
  padding: 16px;
}
.menu-sections {
  display: grid;
  gap: 14px;
}
.menu-section.has-divider {
  border-top: 1px solid #dbe2ea;
  padding-top: 14px;
}
.section-title {
  margin: 0 0 8px;
  font-size: 14px;
  color: #334155;
}
.master-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}
.master-tile {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  min-height: 72px;
  text-decoration: none;
  color: inherit;
  background: #fff;
  display: grid;
  gap: 6px;
  align-content: center;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}
.master-tile .icon-box {
  font-size: 22px;
}
.master-tile .label {
  font-weight: 700;
}
.master-tile .description {
  font-size: 11px;
  color: #b91c1c;
  line-height: 1.3;
  white-space: pre-line;
}
.master-tile.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
.helper-text {
  margin-top: 10px;
  color: #64748b;
}
@media (max-width: 1400px) {
  .master-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 1100px) {
  .master-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 800px) {
  .master-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 520px) {
  .master-grid {
    grid-template-columns: 1fr;
  }
}
</style>

