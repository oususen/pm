<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">ラインマスタ <DataSourceDialog title="ラインマスタ" :sources="dsSources" /></h1>
      <div class="page-actions">
        <button @click="fetchLines" class="btn-primary">更新</button>
        <button v-if="canEdit" @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <div class="filter-bar">
        <label for="lineTypeFilter">区分</label>
        <select id="lineTypeFilter" v-model="lineTypeFilter" @change="fetchLines">
          <option value="">すべて</option>
          <option value="PROD">社内</option>
          <option value="PURCHASE">購入先</option>
        </select>
      </div>

      <table class="data-table">
        <thead>
          <tr>
            <th>ラインコード</th>
            <th>ライン名</th>
            <th>有効</th>
            <th>工程数</th>
            <th>日LT</th>
            <th>作成日時</th>
            <th>更新日時</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="line in lines" :key="line.id">
            <td>{{ line.line_code }}</td>
            <td>{{ line.line_name }}</td>
            <td>{{ line.is_active ? '有効' : '無効' }}</td>
            <td>{{ getStepStats(line.id).count }}</td>
            <td>{{ line.lead_time_days ?? '-' }}</td>
            <td>{{ formatDateTime(line.created_at) }}</td>
            <td>{{ formatDateTime(line.updated_at) }}</td>
            <td>
              <button v-if="canEdit" @click="editLine(line)" class="btn-sm">編集</button>
              <button v-if="canEdit" @click="deleteLine(line.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="lines.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? 'ライン編集' : 'ライン新規作成' }}</h2>
        <form @submit.prevent="saveLine">
          <div class="form-group">
            <label>ラインコード *</label>
            <input v-model="formData.line_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>ライン名 *</label>
            <input v-model="formData.line_name" required :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>日LT（リードタイム）</label>
            <input v-model.number="formData.lead_time_days" type="number" min="0" :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>所属グループ</label>
            <div v-if="units.length" class="unit-list">
              <label v-for="unit in units" :key="unit.id" class="unit-item">
                <input
                  type="checkbox"
                  :value="unit.id"
                  v-model="selectedUnitIds"
                  :disabled="!canEdit"
                />
                <span>{{ unit.name }}</span>
              </label>
            </div>
            <div v-else class="inline-empty">グループがありません</div>
          </div>
          <div class="form-group">
            <label>このラインを使用する工程</label>
            <div class="inline-table" v-if="lineStepsMap[formData.id]?.length">
              <div class="inline-header">
                <span>工程</span>
              </div>
              <div
                v-for="step in lineStepsMap[formData.id]"
                :key="step.id"
                class="inline-row"
              >
                <div class="inline-main">
                  <div class="inline-title">{{ step.process_name }}</div>
                  <div class="inline-sub">#{{ step.process_code }}</div>
                </div>
              </div>
            </div>
            <div v-else class="inline-empty">紐づく工程はありません</div>
          </div>
          <div v-if="isEdit && formData.created_at" class="form-group meta">
            <label>作成日時</label>
            <div class="meta-value">{{ formatDateTime(formData.created_at) }}</div>
          </div>
          <div v-if="isEdit && formData.updated_at" class="form-group meta">
            <label>更新日時</label>
            <div class="meta-value">{{ formatDateTime(formData.updated_at) }}</div>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" :disabled="!canEdit" />
              有効
            </label>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="!canEdit">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { canAccessMasterResource } from '@/utils/masterPermissions'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'm_line', desc: 'ラインマスタ' },
  { op: '読み取り', table: 'm_process', desc: '工程（ライン紐づき）' },
  { op: '読み書き', table: 'accounts_unit', desc: 'グループ（所属）' },
]

const lines = ref([])
const lineStepsMap = ref({})
const units = ref([])
const selectedUnitIds = ref([])
const lineTypeFilter = ref('PROD')
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  line_code: '',
  line_name: '',
  is_active: true
})
const canEdit = computed(() => canAccessMasterResource('masters.line', 'edit'))

const fetchLines = async () => {
  try {
    const params = {}
    if (lineTypeFilter.value) {
      params.line_type = lineTypeFilter.value
    }
    const response = await api.lines.getLines(params)
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
    alert('ラインデータの取得に失敗しました')
  }
}

const fetchLineSteps = async () => {
  try {
    // ルーティングではなく工程マスタの line を参照して集計
    const procRes = await api.processes.getProcesses()
    const procs = procRes.data.results || procRes.data
    const map = {}
    procs.forEach((p) => {
      if (!p.line) return
      if (!map[p.line]) map[p.line] = []
      map[p.line].push({
        id: p.id,
        process_name: p.process_name,
        process_code: p.process_code,
        routing_code: '',
        product_name: '',
        time_unit: 'MINUTE',
        lead_time_days: 0,
        duration_min: 0,
      })
    })
    lineStepsMap.value = map
  } catch (error) {
    console.error('工程取得エラー:', error)
  }
}

const fetchUnits = async () => {
  try {
    const res = await api.accounts.getUnits({ page_size: 20000 })
    units.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
  } catch (error) {
    console.error('グループ取得エラー:', error)
    units.value = []
  }
}

const fetchLineUnitMappings = async (lineId) => {
  if (!lineId) {
    selectedUnitIds.value = []
    return
  }
  try {
    const res = await api.accounts.getUnitLineMappings({ line: lineId, page_size: 20000 })
    const mappings = Array.isArray(res.data) ? res.data : (res.data.results || [])
    selectedUnitIds.value = mappings.map((m) => m.unit)
  } catch (error) {
    console.error('ライン紐付グループ取得エラー:', error)
    selectedUnitIds.value = []
  }
}

const showNewDialog = () => {
  if (!canEdit.value) return
  isEdit.value = false
  formData.value = {
    line_code: '',
    line_name: '',
    is_active: true
  }
  selectedUnitIds.value = []
  showDialog.value = true
}

const editLine = async (line) => {
  if (!canEdit.value) return
  isEdit.value = true
  formData.value = { ...line }
  await fetchLineUnitMappings(line.id)
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveLine = async () => {
  if (!canEdit.value) return
  try {
    let targetLineId = formData.value.id
    if (isEdit.value) {
      await api.lines.updateLine(formData.value.id, formData.value)
      targetLineId = formData.value.id
      alert('更新しました')
    } else {
      const created = await api.lines.createLine(formData.value)
      const createdLine = created.data || {}
      targetLineId = createdLine.id
      alert('作成しました')
    }
    if (targetLineId) {
      await api.accounts.setUnitLineMappingsForLine({
        line: targetLineId,
        unit_ids: selectedUnitIds.value,
      })
    }
    await fetchLines()
    await fetchLineSteps()
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteLine = async (id) => {
  if (!canEdit.value) return
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.lines.deleteLine(id)
    await fetchLines()
    await fetchLineSteps()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchLines()
  fetchLineSteps()
  fetchUnits()
})

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${yyyy}/${mm}/${dd} ${hh}:${mi}`
}

const getStepStats = (lineId) => {
  const steps = lineStepsMap.value[lineId] || []
  return {
    count: steps.length
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  min-width: 500px;
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: #333;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group.meta {
  margin-bottom: 0.75rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #555;
}

.form-group input[type="text"] {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type="checkbox"] {
  margin-right: 0.5rem;
}

.meta-value {
  padding: 0.5rem;
  background: #f7f7f7;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  font-size: 0.95rem;
  color: #333;
}

.inline-table {
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  overflow: hidden;
}

.inline-header,
.inline-row {
  display: grid;
  grid-template-columns: 1fr;
  padding: 8px 10px;
  gap: 8px;
}

.inline-header {
  background: #f7f9ff;
  font-weight: 600;
  color: #333;
}

.inline-row:nth-child(even) {
  background: #fbfbfb;
}

.inline-main {
  display: flex;
  flex-direction: column;
}

.inline-title {
  font-weight: 600;
  color: #222;
}

.inline-sub {
  font-size: 12px;
  color: #555;
}

.inline-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-weight: 600;
  color: #333;
}

.inline-empty {
  padding: 10px 12px;
  border: 1px dashed #d0d0d0;
  border-radius: 6px;
  color: #666;
  font-size: 13px;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ddd;
  background-color: white;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary:hover {
  background-color: #f5f5f5;
}

.filter-bar {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-bar label {
  font-weight: 600;
  color: #333;
}

.filter-bar select {
  min-width: 160px;
  padding: 6px 10px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  background: #fff;
}

.unit-list {
  max-height: 180px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  background: #fff;
}

.unit-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  font-weight: 400 !important;
}

.unit-item:last-child {
  margin-bottom: 0;
}
</style>

