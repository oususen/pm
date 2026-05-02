<template>
  <div class="page-container" v-if="canViewReview">
    <div class="page-header">
      <div>
        <h1 class="page-title">製品チェックシート品質確認一覧</h1>
        <p class="helper-text">入力済みチェックシートを出荷日・台目・ロット単位で確認し、承認PDFを生成します。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn-secondary" to="/quality/product-checksheet/templates">台紙登録へ</RouterLink>
      </div>
    </div>

    <section class="panel">
      <div class="filters">
        <input v-model="filters.q" type="text" placeholder="品番・ロット・入力者・確認者" />
        <input v-model="filters.planned_ship_date" type="date" />
        <input v-model="filters.shipment_unit_no" type="number" min="1" placeholder="台目" />
        <select v-model="filters.status">
          <option value="">すべて</option>
          <option value="COMPLETED">入力完了</option>
          <option value="APPROVED">承認済み</option>
          <option value="PENDING">未入力</option>
        </select>
        <button class="btn-primary" type="button" @click="loadRecords">検索</button>
      </div>
    </section>

    <section class="panel">
      <table class="data-table">
        <thead>
          <tr>
            <th>状態</th>
            <th>製品</th>
            <th>ロット</th>
            <th>番号</th>
            <th>出荷日</th>
            <th>台目</th>
            <th>出荷分内</th>
            <th>入力者</th>
            <th>確認者</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in records" :key="record.id">
            <td>{{ statusLabel(record.status) }}</td>
            <td>{{ record.product_code }}</td>
            <td>{{ record.lot_no || '-' }}</td>
            <td>{{ record.sequence_no }}/{{ record.quantity }}</td>
            <td>{{ record.planned_ship_date || '-' }}</td>
            <td>{{ record.shipment_unit_no || '-' }}</td>
            <td>{{ record.shipment_sequence_no || '-' }}</td>
            <td>{{ record.completed_by_name || '-' }}</td>
            <td>{{ record.supervisor_name || '-' }}</td>
            <td>
              <div class="actions">
                <RouterLink class="btn-small" :to="`/quality/product-checksheet/input/${record.batch}`">開く</RouterLink>
                <a v-if="record.generated_pdf_url" class="btn-small" :href="record.generated_pdf_url" target="_blank">PDF</a>
                <button
                  v-if="record.status === 'COMPLETED'"
                  class="btn-small"
                  type="button"
                  :disabled="!canEditReview"
                  @click="approve(record)"
                >
                  承認PDF
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!records.length">
            <td colspan="10" class="empty-cell">対象データがありません。</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>

  <div class="page-container" v-else>
    <h1 class="page-title">製品チェックシート品質確認一覧</h1>
    <p class="helper-text">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const records = ref([])
const filters = ref({
  q: '',
  planned_ship_date: '',
  shipment_unit_no: '',
  status: 'COMPLETED',
})
const canAccessQuality = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) return hasPermission(user, resource, level)
  return hasPermission(user, 'quality', level)
}
const canViewReview = computed(() => canAccessQuality('quality.product_checksheet_review', 'view'))
const canEditReview = computed(() => canAccessQuality('quality.product_checksheet_review', 'edit'))

const loadRecords = async () => {
  const params = {}
  Object.entries(filters.value).forEach(([key, value]) => {
    if (value !== '') params[key] = value
  })
  const res = await api.productChecksheets.listRecords({ ...params, page_size: 200 })
  records.value = res.data?.results || res.data || []
}

const approve = async (record) => {
  if (!canEditReview.value) return
  const supervisorName = window.prompt('確認者名を入力してください。')
  if (!supervisorName) return
  try {
    await api.productChecksheets.approveRecord(record.id, { supervisor_name: supervisorName })
    await loadRecords()
  } catch (error) {
    console.error(error)
    alert(`承認に失敗しました: ${error.response?.data?.detail || error.message}`)
  }
}

const statusLabel = (status) => {
  if (status === 'APPROVED') return '承認済み'
  if (status === 'COMPLETED') return '入力完了'
  return '未入力'
}

onMounted(() => {
  if (!canViewReview.value) return
  loadRecords()
})
</script>

<style scoped>
.helper-text { margin: 0; color: #5f6b76; }
.panel { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; margin-bottom: 14px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.filters input, .filters select { border: 1px solid #cfd6df; border-radius: 6px; padding: 8px; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 8px; border-bottom: 1px solid #edf1f5; text-align: left; }
.data-table th { background: #f7f9fb; font-size: 13px; }
.actions { display: flex; gap: 6px; flex-wrap: wrap; }
.empty-cell { color: #6b7280; text-align: center; }
.btn-primary, .btn-secondary, .btn-small { border-radius: 6px; border: 1px solid #2563eb; padding: 8px 12px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; background: #fff; color: #2563eb; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-small { padding: 5px 8px; font-size: 12px; }
</style>
