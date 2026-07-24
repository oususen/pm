<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">出来高集計 <DataSourceDialog title="出来高集計" :sources="dsSources" /></h1>
      </div>
    </div>

    <!-- タブ切替 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'calc' }"
        @click="activeTab = 'calc'"
      >計算</button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'inquiry' }"
        @click="activeTab = 'inquiry'; loadInquiry()"
      >照会</button>
    </div>

    <!-- ===== 計算タブ ===== -->
    <div v-if="activeTab === 'calc'" class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field">
            <label>工程</label>
            <select v-model="selectedProcessId" @change="onProcessChange">
              <option :value="null">-- 選択 --</option>
              <option v-for="p in processes" :key="p.id" :value="p.id">
                {{ p.process_code }} {{ p.process_name }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="selectedLineId">
              <option :value="null">-- 自動 --</option>
              <option v-for="l in lines" :key="l.id" :value="l.id">
                {{ l.line_code }} {{ l.line_name }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>開始日</label>
            <input v-model="startDate" type="date" />
          </div>
          <div class="filter-field">
            <label>終了日</label>
            <input v-model="endDate" type="date" />
          </div>
          <div class="filter-actions">
            <button class="btn-primary" :disabled="!canCalc || calculating" @click="calcActual">
              {{ calculating ? '計算中...' : '計算' }}
            </button>
          </div>
        </div>
      </div>

      <template v-if="actualItems.length">
        <div class="section-header">
          <h2 class="section-title">実績サイクル時間（製品別）</h2>
          <div class="section-actions">
            <span class="summary-text">
              全体平均: {{ summary.avg_cycle_time_sec }}秒/個 | 合計出来高: {{ summary.total_qty }}個 | 合計稼働: {{ formatSeconds(summary.total_seconds) }}
            </span>
            <button class="btn-save" :disabled="savingActual" @click="saveActual">
              {{ savingActual ? '保存中...' : '実績CT保存' }}
            </button>
          </div>
        </div>
        <div class="table-wrapper">
          <table class="data-table compact">
            <thead>
              <tr>
                <th class="col-code">品番</th>
                <th class="col-name">品名</th>
                <th class="col-num">出来高</th>
                <th class="col-num">有効稼働時間</th>
                <th class="col-num col-ct-val">CT (秒/個)</th>
                <th class="col-num">セッション数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in actualItems" :key="item.product_id">
                <td class="col-code">{{ item.product_code }}</td>
                <td class="col-name" :title="item.product_name">{{ item.product_name }}</td>
                <td class="col-num">{{ item.total_qty }}</td>
                <td class="col-num">{{ formatSeconds(item.total_seconds) }}</td>
                <td class="col-num col-ct-val">{{ item.cycle_time_sec }}</td>
                <td class="col-num">{{ item.session_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-header" style="margin-top: 16px;">
          <h2 class="section-title">完成品サイクル時間（BOM展開）</h2>
          <div class="section-actions">
            <button class="btn-primary" :disabled="calculatingFinished || !actualSaved" @click="calcFinished">
              {{ calculatingFinished ? '計算中...' : '完成品CT計算' }}
            </button>
            <button
              v-if="finishedItems.length"
              class="btn-save"
              :disabled="savingFinished"
              @click="saveFinished"
            >
              {{ savingFinished ? '保存中...' : '完成品CT保存' }}
            </button>
          </div>
        </div>
        <div v-if="!actualSaved" class="info-msg">
          先に「実績CT保存」を実行してください
        </div>
        <div v-else-if="finishedItems.length" class="table-wrapper">
          <table class="data-table compact">
            <thead>
              <tr>
                <th class="col-code">完成品コード</th>
                <th class="col-name">完成品名</th>
                <th class="col-num col-ct-val">合計CT (秒/個)</th>
                <th class="col-detail">内訳</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in finishedItems" :key="item.finished_product_id">
                <td class="col-code">{{ item.finished_product_code }}</td>
                <td class="col-name" :title="item.finished_product_name">{{ item.finished_product_name }}</td>
                <td class="col-num col-ct-val">{{ item.total_cycle_time_sec }}</td>
                <td class="col-detail">
                  <span v-for="(c, idx) in item.components" :key="idx" class="comp-tag">
                    {{ c.component_product_code }} ×{{ c.bom_qty }} ({{ c.component_cycle_time_sec }}秒) = {{ c.finished_cycle_time_sec }}秒
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="finishedCalcDone" class="info-msg">
          該当する完成品が見つかりませんでした
        </div>
      </template>

      <div v-else-if="calcDone" class="empty-state">
        指定した条件での実績データがありません
      </div>
      <div v-else class="empty-state">
        工程・期間を指定して「計算」を押してください
      </div>
    </div>

    <!-- ===== 照会タブ ===== -->
    <div v-if="activeTab === 'inquiry'" class="page-content">
      <div class="filter-bar">
        <div class="filter-row">
          <div class="filter-field">
            <label>工程</label>
            <select v-model="inqProcessId" @change="loadInquiry">
              <option :value="null">-- 全工程 --</option>
              <option v-for="p in processes" :key="p.id" :value="p.id">
                {{ p.process_code }} {{ p.process_name }}
              </option>
            </select>
          </div>
          <div class="filter-field">
            <label>ライン</label>
            <select v-model="inqLineId" @change="loadInquiry">
              <option :value="null">-- 全ライン --</option>
              <option v-for="l in lines" :key="l.id" :value="l.id">
                {{ l.line_code }} {{ l.line_name }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <div v-if="inqLoading" class="empty-state">読み込み中...</div>
      <template v-else>
        <!-- 実績CT照会 -->
        <div class="section-header">
          <h2 class="section-title">保存済み 実績サイクル時間</h2>
          <span class="summary-text">{{ inqActualItems.length }}件</span>
        </div>
        <div v-if="inqActualItems.length" class="table-wrapper">
          <table class="data-table compact">
            <thead>
              <tr>
                <th class="col-code">工程</th>
                <th class="col-code">ライン</th>
                <th class="col-date">期間</th>
                <th class="col-code">品番</th>
                <th class="col-name">品名</th>
                <th class="col-num">出来高</th>
                <th class="col-num">稼働秒</th>
                <th class="col-num col-ct-val">CT (秒/個)</th>
                <th class="col-date">計算日時</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in inqActualItems" :key="item.id">
                <td class="col-code">{{ item.process_code }}</td>
                <td class="col-code">{{ item.line_code }}</td>
                <td class="col-date">{{ item.calc_from_date }} ~ {{ item.calc_to_date }}</td>
                <td class="col-code">{{ item.product_code }}</td>
                <td class="col-name" :title="item.product_name">{{ item.product_name }}</td>
                <td class="col-num">{{ item.total_qty }}</td>
                <td class="col-num">{{ formatSeconds(item.total_seconds) }}</td>
                <td class="col-num col-ct-val">{{ item.cycle_time_sec }}</td>
                <td class="col-date">{{ item.calculated_at }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">保存済みデータなし</div>

        <!-- 完成品CT照会 -->
        <div class="section-header" style="margin-top: 16px;">
          <h2 class="section-title">保存済み 完成品サイクル時間</h2>
          <span class="summary-text">{{ inqFinishedItems.length }}件</span>
        </div>
        <div v-if="inqFinishedItems.length" class="table-wrapper">
          <table class="data-table compact">
            <thead>
              <tr>
                <th class="col-code">工程</th>
                <th class="col-code">ライン</th>
                <th class="col-date">期間</th>
                <th class="col-code">完成品コード</th>
                <th class="col-name">完成品名</th>
                <th class="col-num col-ct-val">CT (秒/個)</th>
                <th class="col-date">計算日時</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in inqFinishedItems" :key="item.id">
                <td class="col-code">{{ item.process_code }}</td>
                <td class="col-code">{{ item.line_code }}</td>
                <td class="col-date">{{ item.calc_from_date }} ~ {{ item.calc_to_date }}</td>
                <td class="col-code">{{ item.finished_product_code }}</td>
                <td class="col-name" :title="item.finished_product_name">{{ item.finished_product_name }}</td>
                <td class="col-num col-ct-val">{{ item.cycle_time_sec }}</td>
                <td class="col-date">{{ item.calculated_at }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">保存済みデータなし</div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '実績読み取り', table: 't_process_work_session', desc: '工程作業セッション（タンク・組立等）' },
  { op: '実績読み取り', table: 'brake_line_record', desc: 'ブレーキ・スポット作業記録' },
  { op: '計算結果 保存', table: 't_actual_cycle_time', desc: '子部品の実績サイクル時間' },
  { op: '計算結果 保存', table: 't_finished_product_cycle_time', desc: '完成品サイクル時間（BOM展開後）' },
  { op: 'BOM展開', table: 'm_bom / m_bom_item', desc: '部品構成（逆展開で完成品を特定）' },
]

const activeTab = ref('calc')

// ===== 共通マスタ =====
const processes = ref([])
const lines = ref([])

// ===== 計算タブ =====
const selectedProcessId = ref(null)
const selectedLineId = ref(null)
const startDate = ref('')
const endDate = ref('')
const calculating = ref(false)
const savingActual = ref(false)
const calculatingFinished = ref(false)
const savingFinished = ref(false)
const calcDone = ref(false)
const finishedCalcDone = ref(false)
const actualSaved = ref(false)
const actualItems = ref([])
const summary = ref({ total_qty: 0, total_seconds: 0, avg_cycle_time_sec: null })
const finishedItems = ref([])
const resolvedLineId = ref(null)

const today = new Date()
const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
startDate.value = firstDay.toISOString().slice(0, 10)
endDate.value = today.toISOString().slice(0, 10)

// ===== 照会タブ =====
const inqProcessId = ref(null)
const inqLineId = ref(null)
const inqLoading = ref(false)
const inqActualItems = ref([])
const inqFinishedItems = ref([])
let inqLoaded = false

onMounted(async () => {
  const [procRes, lineRes] = await Promise.all([
    api.processes.getProcesses({ is_active: true }),
    api.lines.getLines({ is_active: true, line_type: 'PROD' }),
  ])
  processes.value = (procRes.data.results || procRes.data)
    .sort((a, b) => a.process_code.localeCompare(b.process_code))
  lines.value = (lineRes.data.results || lineRes.data)
    .sort((a, b) => a.line_code.localeCompare(b.line_code))
})

const canCalc = computed(() => selectedProcessId.value && startDate.value && endDate.value)

const onProcessChange = () => {
  const proc = processes.value.find(p => p.id === selectedProcessId.value)
  if (proc && proc.line) {
    selectedLineId.value = proc.line
  }
  actualItems.value = []
  finishedItems.value = []
  calcDone.value = false
  finishedCalcDone.value = false
  actualSaved.value = false
}

const formatSeconds = (sec) => {
  if (!sec) return '0:00:00'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const calcActual = async () => {
  calculating.value = true
  calcDone.value = false
  finishedCalcDone.value = false
  actualSaved.value = false
  actualItems.value = []
  finishedItems.value = []
  try {
    const params = {
      process_id: selectedProcessId.value,
      start_date: startDate.value,
      end_date: endDate.value,
    }
    if (selectedLineId.value) params.line_id = selectedLineId.value
    const res = await api.actualCycleTimes.calc(params)
    actualItems.value = res.data.items || []
    summary.value = res.data.summary || { total_qty: 0, total_seconds: 0, avg_cycle_time_sec: null }
    resolvedLineId.value = res.data.line_id
    calcDone.value = true
  } catch (e) {
    alert('計算エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    calculating.value = false
  }
}

const saveActual = async () => {
  if (!actualItems.value.length) return
  savingActual.value = true
  try {
    const lineId = selectedLineId.value || resolvedLineId.value
    if (!lineId) {
      alert('ラインが特定できません。ラインを選択してください。')
      return
    }
    const res = await api.actualCycleTimes.save({
      process_id: selectedProcessId.value,
      line_id: lineId,
      start_date: startDate.value,
      end_date: endDate.value,
      items: actualItems.value,
    })
    alert(`実績CT保存完了: ${res.data.saved_count}件`)
    actualSaved.value = true
  } catch (e) {
    alert('保存エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    savingActual.value = false
  }
}

const calcFinished = async () => {
  calculatingFinished.value = true
  finishedCalcDone.value = false
  finishedItems.value = []
  try {
    const lineId = selectedLineId.value || resolvedLineId.value
    const res = await api.actualCycleTimes.calcFinished({
      process_id: selectedProcessId.value,
      line_id: lineId,
      start_date: startDate.value,
      end_date: endDate.value,
    })
    finishedItems.value = res.data.items || []
    finishedCalcDone.value = true
  } catch (e) {
    alert('計算エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    calculatingFinished.value = false
  }
}

const saveFinished = async () => {
  if (!finishedItems.value.length) return
  savingFinished.value = true
  try {
    const lineId = selectedLineId.value || resolvedLineId.value
    const res = await api.actualCycleTimes.saveFinished({
      process_id: selectedProcessId.value,
      line_id: lineId,
      start_date: startDate.value,
      end_date: endDate.value,
      items: finishedItems.value,
    })
    alert(`完成品CT保存完了: ${res.data.saved_count}件`)
  } catch (e) {
    alert('保存エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    savingFinished.value = false
  }
}

// ===== 照会タブ =====
const loadInquiry = async () => {
  if (activeTab.value !== 'inquiry') return
  inqLoading.value = true
  try {
    const params = {}
    if (inqProcessId.value) params.process_id = inqProcessId.value
    if (inqLineId.value) params.line_id = inqLineId.value
    const [actRes, finRes] = await Promise.all([
      api.actualCycleTimes.list(params),
      api.actualCycleTimes.listFinished(params),
    ])
    inqActualItems.value = actRes.data || []
    inqFinishedItems.value = finRes.data || []
    inqLoaded = true
  } catch (e) {
    alert('照会エラー: ' + (e.response?.data?.error || e.message))
  } finally {
    inqLoading.value = false
  }
}
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.page-title { font-size: 18px; font-weight: 700; margin: 0; }
.page-content { display: flex; flex-direction: column; gap: 8px; }

.tab-bar { display: flex; gap: 0; margin-bottom: 8px; border-bottom: 2px solid #dee2e6; }
.tab-btn {
  padding: 6px 20px;
  font-size: 13px;
  font-weight: 600;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  color: #666;
}
.tab-btn.active { color: #3498db; border-bottom-color: #3498db; }

.filter-bar { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; padding: 10px 12px; }
.filter-row { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
.filter-field { display: flex; flex-direction: column; gap: 2px; }
.filter-field label { font-size: 11px; font-weight: 600; color: #666; }
.filter-field input, .filter-field select { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; }
.filter-actions { display: flex; gap: 6px; }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; }
.section-title { font-size: 14px; font-weight: 700; margin: 0; }
.section-actions { display: flex; gap: 8px; align-items: center; }
.summary-text { font-size: 12px; color: #555; }

.btn-primary { padding: 5px 14px; background: #3498db; color: #fff; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: default; }
.btn-save { padding: 5px 14px; background: #27ae60; color: #fff; border: none; border-radius: 4px; font-size: 13px; cursor: pointer; }
.btn-save:disabled { opacity: 0.6; cursor: default; }

.table-wrapper { overflow: auto; max-height: calc(100vh - 340px); border: 1px solid #dee2e6; border-radius: 4px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th, .data-table td { padding: 4px 8px; border: 1px solid #e0e0e0; white-space: nowrap; }
.data-table thead th { background: #f0f2f5; position: sticky; top: 0; z-index: 2; font-weight: 600; text-align: center; }
.col-code { min-width: 80px; }
.col-name { min-width: 120px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; }
.col-num { text-align: right; min-width: 70px; }
.col-ct-val { font-weight: 700; color: #2c3e50; }
.col-detail { min-width: 200px; white-space: normal; }
.col-date { min-width: 90px; white-space: nowrap; }

.comp-tag {
  display: inline-block;
  background: #eef6ff;
  border: 1px solid #b3d4fc;
  border-radius: 3px;
  padding: 1px 6px;
  margin: 1px 3px;
  font-size: 11px;
  color: #2c3e50;
}

.info-msg { font-size: 13px; color: #856404; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; padding: 8px 12px; }
.empty-state { text-align: center; color: #999; padding: 40px; font-size: 14px; }
</style>
