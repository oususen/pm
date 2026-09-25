<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消耗品 在庫一覧 <DataSourceDialog title="消耗品 在庫一覧" :sources="dsSources" /></h1>
      <button class="btn-primary" :disabled="loading" @click="fetchCards">更新</button>
    </div>

    <div class="filter-bar">
      <label>検索: <input v-model="filters.search" placeholder="コード/発注コード/品名" @keyup.enter="fetchCards" /></label>
      <label>注文状態:
        <select v-model="filters.order_status" @change="fetchCards">
          <option value="">すべて</option>
          <option value="none">未発注</option>
          <option value="requested">依頼中</option>
          <option value="preparing">発注準備</option>
          <option value="ordered">発注済</option>
        </select>
      </label>
      <label>欠品:
        <select v-model="filters.shortage" @change="fetchCards">
          <option value="">すべて</option>
          <option value="1">安全在庫以下のみ</option>
        </select>
      </label>
      <label>カテゴリ:
        <select v-model="filters.category" @change="fetchCards">
          <option value="">すべて</option>
          <option v-for="c in filterOptions.categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label>保管場所:
        <select v-model="filters.storage_location" @change="fetchCards">
          <option value="">すべて</option>
          <option v-for="l in filterOptions.storage_locations" :key="l" :value="l">{{ l }}</option>
        </select>
      </label>
      <button class="btn-primary" @click="fetchCards">検索</button>
      <span class="summary">{{ cards.length }}件（欠品 {{ shortageCount }}件）</span>
    </div>

    <div v-if="loading" class="loading-message">読み込み中...</div>
    <div v-else class="card-grid">
      <div v-for="c in cards" :key="c.id" :class="['stock-card', { shortage: c.is_shortage }]">
        <div class="card-top">
          <img v-if="c.image_url" :src="c.image_url" class="card-img" alt="" />
          <div v-else class="card-img no-img">画像なし</div>
          <div class="card-main">
            <div class="card-name">{{ c.name }}</div>
            <div class="card-line">コード: {{ c.code }}</div>
            <div class="card-line">
              在庫数: <b class="stock">{{ c.stock_quantity }} {{ c.unit }}</b> | 安全在庫: {{ c.safety_stock }}
            </div>
            <div class="card-line">保管場所: {{ c.storage_location || '-' }} | 購入先: {{ c.supplier_name || '-' }}</div>
            <div class="card-line">
              注文状態: <span :class="['status-chip', c.order_status || 'none']">{{ c.order_status_label }}</span>
              <span v-if="c.is_shortage" class="shortage-chip">欠品</span>
            </div>
          </div>
        </div>
        <div v-if="c.open_requests.length" class="sub-section">
          <div class="sub-title">📝 未完了の依頼</div>
          <div v-for="r in c.open_requests" :key="r.id" class="sub-line">
            {{ r.status_label }}: {{ r.quantity }}{{ c.unit }} | 依頼日: {{ formatDateTime(r.requested_at) }}
            <span v-if="r.ordered_at">| 発注日: {{ formatDateTime(r.ordered_at) }}</span>
          </div>
        </div>
        <div v-if="c.recent_inbounds.length" class="sub-section">
          <div class="sub-title">📥 入庫履歴（直近{{ c.recent_inbounds.length }}件）</div>
          <div v-for="(m, i) in c.recent_inbounds" :key="i" class="sub-line">
            {{ formatDateTime(m.moved_at) }} | {{ m.inbound_type_label }}: {{ m.quantity }}{{ c.unit }} | 作業者: {{ m.worker_name || '-' }}
          </div>
        </div>
        <div v-if="canOperate" class="card-actions">
          <RouterLink :to="{ path: '/consumables/operations', query: { mode: 'outbound', code: c.code } }" class="act outbound">出庫</RouterLink>
          <RouterLink :to="{ path: '/consumables/operations', query: { mode: 'inbound', code: c.code } }" class="act inbound">入庫</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { formatDateTime } from './consumableUtils'

const dsSources = [
  { op: '読み', table: 't_consumable', desc: '消耗品・在庫数' },
  { op: '読み', table: 't_consumable_request', desc: '未完了の依頼（注文状態の導出）' },
  { op: '読み', table: 't_consumable_stock_movement', desc: '直近の入庫履歴' },
]

const canOperate = computed(() => hasPermission(authState.user, 'consumables.operations', 'edit'))

const cards = ref([])
const loading = ref(false)
const filterOptions = ref({ categories: [], storage_locations: [] })
const filters = ref({ search: '', order_status: '', shortage: '', category: '', storage_location: '' })

const shortageCount = computed(() => cards.value.filter((c) => c.is_shortage).length)

async function fetchCards() {
  loading.value = true
  try {
    const params = { is_active: true }
    Object.entries(filters.value).forEach(([k, v]) => {
      if (v) params[k] = v
    })
    cards.value = (await api.consumables.listCards(params)).data
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  filterOptions.value = (await api.consumables.getFilterOptions()).data
  fetchCards()
})
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.page-title { font-size: 1.2em; margin: 0; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 8px; font-size: 0.85em; }
.summary { color: #555; }
.loading-message { padding: 12px; color: #666; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 8px; }
.stock-card { border: 1px solid #ddd; border-radius: 6px; padding: 8px; background: #fff; font-size: 0.85em; }
.stock-card.shortage { border-color: #e57373; background: #fff8f8; }
.card-top { display: flex; gap: 8px; }
.card-img { width: 64px; height: 64px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.no-img { display: flex; align-items: center; justify-content: center; background: #eee; color: #999; font-size: 0.75em; }
.card-name { font-weight: 700; font-size: 1.05em; }
.card-line { color: #444; }
.stock { font-size: 1.1em; }
.stock-card.shortage .stock { color: #c62828; }
.status-chip { padding: 0 6px; border-radius: 8px; background: #eee; }
.status-chip.requested { background: #fff3e0; color: #e65100; }
.status-chip.preparing { background: #e3f2fd; color: #1565c0; }
.status-chip.ordered { background: #e8f5e9; color: #2e7d32; }
.shortage-chip { margin-left: 6px; padding: 0 6px; border-radius: 8px; background: #c62828; color: #fff; }
.sub-section { margin-top: 6px; padding-top: 4px; border-top: 1px dashed #ddd; }
.sub-title { font-weight: 600; }
.sub-line { color: #555; }
.card-actions { display: flex; gap: 6px; margin-top: 6px; }
.act { flex: 1; text-align: center; padding: 4px; border-radius: 4px; color: #fff; text-decoration: none; font-weight: 600; }
.act.outbound { background: #e65100; }
.act.inbound { background: #2e7d32; }
</style>
