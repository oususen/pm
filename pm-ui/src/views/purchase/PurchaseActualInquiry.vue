<template>
  <div class="page">
    <h2 class="page-title">納入実績照会 <button v-if="authState.user?.is_superuser" class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button></h2>
    <div class="filters">
      <label>開始日 <input v-model="startDate" type="date" /></label>
      <label>終了日 <input v-model="endDate" type="date" /></label>
      <label>品番 <input v-model.trim="productCode" type="text" /></label>
      <button class="btn" :disabled="loading" @click="load">検索</button>
    </div>

    <div class="table-wrap">
      <table class="list-table">
        <thead>
          <tr>
            <th>納入日</th>
            <th>品番</th>
            <th>品名</th>
            <th>購入先</th>
            <th class="num">数量</th>
            <th>入力者</th>
            <th class="num">ID</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ formatDate(row.delivery_date) }}</td>
            <td>{{ row.product_code }}</td>
            <td>{{ row.product_name }}</td>
            <td>{{ row.supplier }}</td>
            <td class="num">{{ formatNum(row.qty) }}</td>
            <td>{{ row.operator_name }}</td>
            <td class="num">{{ row.id }}</td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="7" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- データソースモーダル -->
    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header"><h3>データソース</h3><button class="ds-close" @click="showDataSource = false">&times;</button></div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr><td>実績 読み取り</td><td>process_realtime_record</td><td>納入実績（source: PURCHASE_ACTUAL_INPUT / PURCHASE_RECEIVING）</td></tr>
            <tr><td>仕入先 読み取り</td><td>m_supplier</td><td>仕入先マスタ（購入先名表示）</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'

const showDataSource = ref(false)
const loading = ref(false)
const rows = ref([])
const today = formatISODate(new Date())
const startDate = ref(today)
const endDate = ref(today)
const productCode = ref('')

const formatDate = (value) => String(value || '').replace(/-/g, '/')
const formatNum = (value) => Number(value || 0).toLocaleString()

const load = async () => {
  loading.value = true
  try {
    const res = await api.purchaseActuals.getInquiry({
      start_date: startDate.value,
      end_date: endDate.value,
      product_code: productCode.value || undefined,
    })
    rows.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    rows.value = []
    alert('納入実績の取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 16px; }
.page-title { margin: 0 0 12px; font-size: 22px; }
.filters { display: flex; gap: 10px; align-items: end; margin-bottom: 10px; flex-wrap: wrap; }
.filters label { display: grid; gap: 4px; font-size: 13px; font-weight: 700; }
.filters input { border: 1px solid #9ca3af; padding: 6px; min-width: 140px; }
.btn { border: 1px solid #6d7478; background: #e5e5e5; padding: 6px 12px; font-weight: 700; }
.table-wrap { border: 1px solid #8d9498; overflow: auto; background: #fff; }
.list-table { width: 100%; border-collapse: collapse; min-width: 900px; }
.list-table th, .list-table td { border: 1px solid #ccd2d8; padding: 6px 8px; font-size: 13px; }
.list-table th { background: #4f6f82; color: #fff; text-align: left; position: sticky; top: 0; }
.num { text-align: right; }
.no-data { text-align: center; color: #64748b; }
.ds-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
</style>




