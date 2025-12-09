<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">生産計画入力</h2>
      <div class="page-actions">
        <input type="date" v-model="planDate" />
        <select v-model="selectedLine">
          <option value="">ラインを選択</option>
          <option v-for="line in lines" :key="line.id" :value="line.id">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <button class="btn-primary" @click="addRow">行を追加</button>
        <button class="btn-secondary" @click="resetRows" :disabled="rows.length === 0">クリア</button>
        <button class="btn-primary" @click="savePlan" :disabled="rows.length === 0">保存（ダミー）</button>
      </div>
    </div>

    <div class="page-content">
      <div class="note">※ 現状は画面内で入力・確認するのみです。保存はデモアクションで、サーバー連携は未実装です。</div>
      <table class="plan-table">
        <thead>
          <tr>
            <th style="width: 50px;">行</th>
            <th style="min-width: 160px;">製品番号</th>
            <th style="min-width: 220px;">品名</th>
            <th style="min-width: 200px;">備考/仕様</th>
            <th style="width: 120px;">計画数量</th>
            <th style="min-width: 140px;">工程</th>
            <th style="min-width: 140px;">ライン</th>
            <th style="min-width: 160px;">メモ</th>
            <th style="width: 80px;">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="row.id">
            <td class="center">{{ idx + 1 }}</td>
            <td>
              <select v-model="row.product_id">
                <option value="">選択</option>
                <option v-for="p in products" :key="p.id" :value="p.id">
                  {{ p.product_code }} - {{ p.product_name }}
                </option>
              </select>
            </td>
            <td class="text">
              {{ getProductName(row.product_id) }}
            </td>
            <td>
              <input type="text" v-model="row.spec" placeholder="仕様/備考" />
            </td>
            <td>
              <input type="number" min="0" v-model.number="row.plan_qty" />
            </td>
            <td>
              <select v-model="row.process_id">
                <option value="">選択</option>
                <option v-for="proc in processes" :key="proc.id" :value="proc.id">
                  {{ proc.process_code }} - {{ proc.process_name }}
                </option>
              </select>
            </td>
            <td>
              <select v-model="row.line_id">
                <option value="">選択</option>
                <option v-for="line in lines" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </td>
            <td>
              <input type="text" v-model="row.remark" placeholder="メモ" />
            </td>
            <td class="center">
              <button class="btn-sm btn-danger" @click="removeRow(idx)">削除</button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="9" class="no-data">行を追加してください</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const planDate = ref(new Date().toISOString().slice(0, 10))
const selectedLine = ref('')
const lines = ref([])
const products = ref([])
const processes = ref([])

const rows = ref([])
let tempId = 1

const addRow = () => {
  rows.value.push({
    id: `tmp-${tempId++}`,
    product_id: '',
    process_id: '',
    line_id: selectedLine.value || '',
    plan_qty: 0,
    spec: '',
    remark: '',
  })
}

const removeRow = (idx) => {
  rows.value.splice(idx, 1)
}

const resetRows = () => {
  rows.value = []
}

const getProductName = (id) => {
  const p = products.value.find((x) => x.id === id)
  return p ? `${p.product_code} - ${p.product_name}` : ''
}

const savePlan = () => {
  alert('現状はデモのため、保存処理は未実装です。')
}

const fetchLines = async () => {
  const res = await api.lines.getLines()
  lines.value = res.data.results || res.data || []
}
const fetchProducts = async () => {
  products.value = (await api.products.getAllProducts()).sort((a, b) =>
    (a.product_code || '').localeCompare(b.product_code || '')
  )
}
const fetchProcesses = async () => {
  const res = await api.processes.getProcesses()
  processes.value = res.data.results || res.data || []
}

onMounted(async () => {
  try {
    await Promise.all([fetchLines(), fetchProducts(), fetchProcesses()])
  } catch (e) {
    console.error('初期データ取得エラー', e)
  }
})
</script>

<style scoped>
.page-container {
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.page-actions input,
.page-actions select {
  padding: 6px 8px;
  font-size: 12px;
}
.page-content {
  margin-top: 8px;
}
.note {
  margin-bottom: 8px;
  color: #666;
  font-size: 12px;
}
.plan-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.plan-table th,
.plan-table td {
  border: 1px solid #dfe4ea;
  padding: 6px 8px;
  vertical-align: middle;
}
.plan-table thead {
  background: #f6f8fb;
}
.plan-table input,
.plan-table select {
  width: 100%;
  padding: 4px 6px;
  box-sizing: border-box;
}
.center {
  text-align: center;
}
.text {
  color: #444;
}
.no-data {
  text-align: center;
  color: #888;
  padding: 12px 0;
}
.btn-primary {
  padding: 6px 10px;
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-secondary {
  padding: 6px 10px;
  background: #fff;
  color: #555;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  cursor: pointer;
}
.btn-sm {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
}
.btn-danger {
  color: #d9534f;
  border-color: #d9534f;
}
.btn-primary:hover {
  background: #2563eb;
}
.btn-secondary:hover,
.btn-sm:hover {
  background: #f3f4f6;
}
.btn-danger:hover {
  background: #fef2f2;
}
</style>
