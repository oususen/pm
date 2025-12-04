<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">工程マスタ</h1>
      <div class="page-actions">
        <button @click="fetchProcesses" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>工程コード</th>
            <th>工程名</th>
            <th>外注工程</th>
            <th>有効</th>
            <th>使用ライン</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="process in processes" :key="process.id">
            <td>{{ process.process_code }}</td>
            <td>{{ process.process_name }}</td>
            <td>{{ process.is_outsource ? '外注' : '社内' }}</td>
            <td>{{ process.is_active ? '有効' : '無効' }}</td>
            <td>
              <div class="tag-list" v-if="getProcessLines(process.id).length">
                <span
                  v-for="line in getProcessLines(process.id)"
                  :key="line.line_id"
                  class="tag"
                >
                  {{ line.line_code }} ({{ line.count }}件)
                </span>
              </div>
              <span v-else>-</span>
            </td>
            <td>
              <button @click="editProcess(process)" class="btn-sm">編集</button>
              <button @click="deleteProcess(process.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="processes.length === 0" class="no-data">
        データがありません
      </div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ isEdit ? '工程編集' : '工程新規作成' }}</h2>
        <form @submit.prevent="saveProcess">
          <div class="form-group">
            <label>工程コード *</label>
            <input v-model="formData.process_code" required :disabled="isEdit" />
          </div>
          <div class="form-group">
            <label>工程名 *</label>
            <input v-model="formData.process_name" required />
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_outsource" />
              外注工程
            </label>
          </div>
          <div class="form-group">
            <label>
              <input type="checkbox" v-model="formData.is_active" />
              有効
            </label>
          </div>
          <div v-if="isEdit" class="form-group">
            <label>この工程を使うライン</label>
            <div class="tag-list" v-if="getProcessLines(formData.id).length">
              <span
                v-for="line in getProcessLines(formData.id)"
                :key="line.line_id"
                class="tag"
              >
                {{ line.line_code }} ({{ line.count }}件)
              </span>
            </div>
            <div v-else class="inline-empty">現在この工程を使用するラインはありません</div>
          </div>
          <div v-if="isEdit" class="form-group">
            <label>ライン一括割当（この工程を使う全ルートを選択ラインに変更）</label>
            <select v-model="lineBulkSelection" class="select-line">
              <option :value="null">変更しない</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_code }} - {{ line.line_name }}
              </option>
            </select>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary">保存</button>
            <button type="button" @click="closeDialog" class="btn-secondary">キャンセル</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const processes = ref([])
const routingSteps = ref([])
const lines = ref([])
const lineBulkSelection = ref(null)
const showDialog = ref(false)
const isEdit = ref(false)
const formData = ref({
  process_code: '',
  process_name: '',
  is_outsource: false,
  is_active: true
})

const fetchProcesses = async () => {
  try {
    const response = await api.processes.getProcesses()
    processes.value = response.data.results || response.data
  } catch (error) {
    console.error('工程取得エラー:', error)
    alert('工程データの取得に失敗しました')
  }
}

const fetchRoutingSteps = async () => {
  try {
    const response = await api.routings.getRoutings()
    const data = response.data.results || response.data
    const steps = []
    data.forEach((routing) => {
      (routing.steps || []).forEach((step) => {
        steps.push({
          ...step,
          routing_code: routing.routing_code,
          product_name: routing.product_name,
        })
      })
    })
    routingSteps.value = steps
  } catch (error) {
    console.error('ルーティング工程取得エラー:', error)
  }
}

const fetchLines = async () => {
  try {
    const response = await api.lines.getLines()
    lines.value = response.data.results || response.data
  } catch (error) {
    console.error('ライン取得エラー:', error)
  }
}

const showNewDialog = () => {
  isEdit.value = false
  formData.value = {
    process_code: '',
    process_name: '',
    is_outsource: false,
    is_active: true
  }
  lineBulkSelection.value = null
  showDialog.value = true
}

const editProcess = (process) => {
  isEdit.value = true
  formData.value = { ...process }
  lineBulkSelection.value = null
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const saveProcess = async () => {
  try {
    if (isEdit.value) {
      await api.processes.updateProcess(formData.value.id, formData.value)
      alert('更新しました')
    } else {
      await api.processes.createProcess(formData.value)
      alert('作成しました')
    }
    await fetchProcesses()
    if (isEdit.value && lineBulkSelection.value !== null) {
      await saveLineAssignments(lineBulkSelection.value)
      await fetchRoutingSteps()
    }
    closeDialog()
  } catch (error) {
    console.error('保存エラー:', error)
    alert('保存に失敗しました')
  }
}

const deleteProcess = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.processes.deleteProcess(id)
    await fetchProcesses()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchProcesses()
  fetchRoutingSteps()
  fetchLines()
})

const getProcessLines = (processId) => {
  const filtered = routingSteps.value.filter((s) => s.process === processId)
  const map = {}
  filtered.forEach((s) => {
    if (!s.line) return
    if (!map[s.line]) {
      map[s.line] = { line_id: s.line, line_name: s.line_name, line_code: s.line_name || `Line#${s.line}`, count: 0 }
    }
    map[s.line].count += 1
  })
  return Object.values(map)
}

const saveLineAssignments = async (lineId) => {
  const targets = routingSteps.value.filter((s) => s.process === formData.value.id)
  for (const step of targets) {
    const payload = {
      routing: step.routing,
      step_no: step.step_no,
      process: step.process,
      line: lineId,
      time_unit: step.time_unit,
      lead_time_days: step.lead_time_days,
      start_offset_min: step.start_offset_min,
      duration_min: step.duration_min,
      remark: step.remark,
    }
    try {
      await api.routings.updateRoutingStep(step.id, payload)
    } catch (e) {
      console.error('ライン割当更新エラー:', e)
      alert('ライン割当の更新に失敗しました')
      throw e
    }
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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #eef5ff;
  border: 1px solid #cbd9ff;
  border-radius: 12px;
  font-size: 12px;
  color: #1f3b7a;
}

.inline-table {
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  overflow: hidden;
}

.inline-header,
.inline-row {
  display: grid;
  grid-template-columns: 1fr 220px;
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
}

.select-line {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
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
</style>
