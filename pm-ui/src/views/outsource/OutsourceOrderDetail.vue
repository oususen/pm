<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">案件詳細: {{ order?.case_no }}</h2>
      <RouterLink to="/outsource/orders" class="btn-back">← 一覧へ</RouterLink>
    </div>

    <div v-if="order" class="detail-content">
      <div class="info-grid">
        <div class="info-item"><span class="info-label">品目コード</span><span>{{ order.item_code }}</span></div>
        <div class="info-item"><span class="info-label">品目名称</span><span>{{ order.item_name }}</span></div>
        <div class="info-item"><span class="info-label">受注数量</span><span>{{ order.order_qty }}</span></div>
        <div class="info-item"><span class="info-label">塗装名</span><span>{{ order.painting_name }}</span></div>
        <div class="info-item"><span class="info-label">塗装日</span><span>{{ order.painting_date }}</span></div>
        <div class="info-item"><span class="info-label">ステータス</span><span class="status-badge" :class="'st-' + order.status">{{ order.get_status_display || order.status }}</span></div>
        <div class="info-item"><span class="info-label">最早着手日</span><span>{{ order.earliest_start || '未計算' }}</span></div>
        <div class="info-item"><span class="info-label">最遅完了日</span><span>{{ order.latest_finish || '未計算' }}</span></div>
      </div>

      <div v-if="order.splits && order.splits.length" class="splits-section">
        <h3>分割計画</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>加工予定日</th>
              <th>数量</th>
              <th>材料支給</th>
              <th>加工完了</th>
              <th>出荷済</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in order.splits" :key="s.id">
              <td>{{ s.sequence }}</td>
              <td>{{ s.process_date }}</td>
              <td class="text-right">{{ s.qty }}</td>
              <td class="text-center">{{ s.material_supplied ? '✓' : '' }}</td>
              <td class="text-center">{{ s.process_completed ? '✓' : '' }}</td>
              <td class="text-center">{{ s.shipped ? '✓' : '' }}</td>
            </tr>
            <tr class="total-row">
              <td colspan="2">合計</td>
              <td class="text-right">{{ splitTotal }}</td>
              <td colspan="3"></td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="no-splits">分割計画未登録</div>
    </div>

    <div v-else-if="loading" class="loading">読み込み中...</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import api from '@/api/client'

const route = useRoute()
const order = ref(null)
const loading = ref(false)

const splitTotal = computed(() => {
  if (!order.value?.splits) return 0
  return order.value.splits.reduce((sum, s) => sum + s.qty, 0)
})

async function fetchOrder() {
  loading.value = true
  try {
    const res = await api.outsource.getOrder(route.params.id)
    order.value = res.data
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchOrder)
</script>

<style scoped>
.page-container { padding: 16px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 18px; }
.btn-back { font-size: 13px; color: #1976d2; text-decoration: none; }

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
  margin-bottom: 20px;
}
.info-item { display: flex; gap: 8px; font-size: 13px; padding: 4px 0; }
.info-label { font-weight: 600; min-width: 80px; color: #555; }

.splits-section { margin-top: 16px; }
.splits-section h3 { font-size: 14px; margin-bottom: 8px; }

.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { border: 1px solid #ddd; padding: 4px 8px; }
.data-table th { background: #f5f5f5; }
.text-right { text-align: right; }
.text-center { text-align: center; }
.total-row { font-weight: 600; background: #fafafa; }

.status-badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.st-IMPORTED { background: #e3f2fd; color: #1565c0; }
.st-SENT_TO_SUB { background: #fff3e0; color: #e65100; }
.st-SPLIT_REGISTERED { background: #e8f5e9; color: #2e7d32; }
.st-IN_PROGRESS { background: #fce4ec; color: #c62828; }
.st-COMPLETED { background: #f5f5f5; color: #616161; }

.no-splits { padding: 16px; color: #999; font-size: 13px; }
.loading { text-align: center; padding: 32px; color: #999; }
</style>
