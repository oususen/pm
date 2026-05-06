<template>
  <div class="page">
    <h2 class="page-title">納入実績照会</h2>
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
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, ref } from 'vue'
import api from '@/api/client'

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
</style>




