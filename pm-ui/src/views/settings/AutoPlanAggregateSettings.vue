<template>
  <div class="settings-container">
    <h2 class="page-title">まとめ生産設定</h2>

    <div class="form-row">
      <select v-model="form.line">
        <option value="">ライン選択</option>
        <option v-for="line in lines" :key="line.id" :value="line.id">
          {{ line.line_code }} - {{ line.line_name }}
        </option>
      </select>
      <select v-model="form.product">
        <option value="">製品選択</option>
        <option v-for="product in products" :key="product.id" :value="product.id">
          {{ product.product_code }} - {{ product.product_name }}
        </option>
      </select>
      <select v-model.number="form.aggregate_weekday">
        <option v-for="d in weekdayOptions" :key="d.value" :value="d.value">{{ d.label }}</option>
      </select>
      <input v-model.number="form.aggregate_days" type="number" min="1" max="31" />
      <label class="active-label"><input v-model="form.is_active" type="checkbox" />有効</label>
      <button class="btn-primary" @click="saveSetting">{{ form.id ? '更新' : '追加' }}</button>
      <button v-if="form.id" class="btn-secondary" @click="resetForm">取消</button>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ライン</th>
            <th>製品</th>
            <th>まとめ生産日</th>
            <th>まとめ対象期間</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.line_code }} - {{ row.line_name }}</td>
            <td>{{ row.product_code }} - {{ row.product_name }}</td>
            <td>{{ weekdayLabel(row.aggregate_weekday) }}</td>
            <td>{{ row.aggregate_days }}日</td>
            <td>{{ row.is_active ? '有効' : '無効' }}</td>
            <td class="actions">
              <button class="btn-sm" @click="editRow(row)">編集</button>
              <button class="btn-sm btn-danger" @click="deleteRow(row.id)">削除</button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="6" class="no-data">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api/client'

const route = useRoute()

const lines = ref([])
const allProducts = ref([])
const products = ref([])
const rows = ref([])

const weekdayOptions = [
  { value: 0, label: '日曜' },
  { value: 1, label: '月曜' },
  { value: 2, label: '火曜' },
  { value: 3, label: '水曜' },
  { value: 4, label: '木曜' },
  { value: 5, label: '金曜' },
  { value: 6, label: '土曜' },
]

const emptyForm = () => ({
  id: null,
  line: '',
  product: '',
  aggregate_weekday: 2,
  aggregate_days: 7,
  is_active: true,
})
const form = ref(emptyForm())

const weekdayLabel = (v) => weekdayOptions.find((x) => x.value === Number(v))?.label || '-'

const loadLineProducts = async (lineId) => {
  if (!lineId) {
    products.value = allProducts.value
    return
  }
  try {
    const res = await api.lineProductDisplayOrders.getOrders({ line: lineId, page_size: 5000 })
    const orders = res?.data?.results || res?.data || []
    const productIds = new Set(orders.map((o) => o.product))
    if (productIds.size > 0) {
      products.value = allProducts.value.filter((p) => productIds.has(p.id))
    } else {
      products.value = allProducts.value
    }
  } catch {
    products.value = allProducts.value
  }
}

watch(() => form.value.line, (newLine) => {
  if (!form.value.id) form.value.product = ''
  loadLineProducts(newLine)
})

const loadMaster = async () => {
  const [lineRes, productRes] = await Promise.all([
    api.lines.getLines({ is_active: true, line_type: 'PROD', page_size: 1000 }),
    api.products.getProducts({ is_active: true, page_size: 1000 }),
  ])
  lines.value = lineRes?.data?.results || lineRes?.data || []
  allProducts.value = productRes?.data?.results || productRes?.data || []
  products.value = allProducts.value
  const queryLine = route.query.line
  if (queryLine && !form.value.line) {
    const lineId = Number(queryLine)
    if (lines.value.some((l) => l.id === lineId)) {
      form.value.line = lineId
    }
  }
}

const loadRows = async () => {
  const res = await api.autoPlanAggregateSettings.list({ page_size: 1000, ordering: 'line__line_code,product__product_code' })
  rows.value = res?.data?.results || res?.data || []
}

const resetForm = () => {
  form.value = emptyForm()
}

const editRow = (row) => {
  form.value = {
    id: row.id,
    line: row.line,
    product: row.product,
    aggregate_weekday: row.aggregate_weekday,
    aggregate_days: row.aggregate_days,
    is_active: row.is_active,
  }
}

const saveSetting = async () => {
  if (!form.value.line || !form.value.product) {
    alert('ラインと製品を選択してください。')
    return
  }
  if (!form.value.aggregate_days || Number(form.value.aggregate_days) <= 0) {
    alert('まとめ対象期間は1日以上を指定してください。')
    return
  }
  const payload = {
    line: form.value.line,
    product: form.value.product,
    aggregate_weekday: Number(form.value.aggregate_weekday),
    aggregate_days: Number(form.value.aggregate_days),
    is_active: !!form.value.is_active,
  }
  try {
    if (form.value.id) {
      await api.autoPlanAggregateSettings.update(form.value.id, payload)
    } else {
      await api.autoPlanAggregateSettings.create(payload)
    }
    await loadRows()
    resetForm()
  } catch (e) {
    const detail = e?.response?.data?.detail || '保存に失敗しました。'
    alert(detail)
  }
}

const deleteRow = async (id) => {
  if (!confirm('削除しますか？')) return
  await api.autoPlanAggregateSettings.remove(id)
  await loadRows()
  if (form.value.id === id) resetForm()
}

onMounted(async () => {
  await Promise.all([loadMaster(), loadRows()])
})
</script>

<style scoped>
.settings-container {
  padding: 12px;
  background: #eef2f6;
  min-height: 100%;
}
.page-title {
  margin: 0 0 12px;
  font-size: 18px;
}
.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}
.form-row select,
.form-row input[type='number'] {
  min-width: 160px;
  padding: 6px 8px;
}
.active-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-primary, .btn-secondary, .btn-sm, .btn-danger {
  padding: 6px 10px;
  border: 1px solid #b8c3d6;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn-primary {
  background: #1d74d8;
  border-color: #1d74d8;
  color: #fff;
}
.btn-danger {
  color: #b00;
}
.table-wrap {
  overflow-x: auto;
  background: #fff;
  border: 1px solid #d7deea;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #d7deea;
  padding: 8px;
  text-align: left;
  white-space: nowrap;
}
.actions {
  display: flex;
  gap: 6px;
}
.no-data {
  text-align: center;
  color: #666;
}
</style>

