<template>
  <div class="plan-deviation-report">
    <div class="report-header">
      <h2>計画乖離レポート <button v-if="authState.user?.is_superuser" class="ds-btn" @click="showDataSource = true" title="データソース"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></svg></button></h2>
      <div class="header-controls">
        <label>対象日:</label>
        <input type="date" v-model="targetDate" @change="loadReport" />
        <select v-model="lineTypeFilter" @change="onLineTypeChange">
          <option value="PROD">社内</option>
          <option value="PURCHASE">購入先</option>
          <option value="OUTSOURCE">外作</option>
          <option value="">全て</option>
        </select>
        <select v-model="selectedLineId" @change="onLineChange">
          <option value="">全ライン</option>
          <option v-for="line in filteredLines" :key="line.id" :value="line.id">
            {{ line.line_code }} - {{ line.line_name }}
          </option>
        </select>
        <select v-model="selectedProcessId" @change="loadReport">
          <option value="">全工程</option>
          <option v-for="p in processes" :key="p.id" :value="p.id">
            {{ p.process_code }} - {{ p.process_name }}
          </option>
        </select>
        <select v-model="statusFilter">
          <option value="">全て</option>
          <option value="over">超過のみ</option>
          <option value="short">不足のみ</option>
          <option value="unplanned">計画外のみ</option>
          <option value="exclude_unplanned">計画外除外</option>
        </select>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">お気に入り選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
        <input
          type="text"
          v-model.trim="favoriteName"
          placeholder="お気に入り名"
        />
        <button class="btn-favorite" title="お気に入り登録" @click="saveFavorite" :disabled="loading">★</button>
        <button class="btn-gantt-config" @click="showGanttConfig = true" title="ガント計画適用ライン設定">⚙</button>
        <button class="btn-reload" @click="loadReport" :disabled="loading">更新</button>
        <button
          class="btn-confirm"
          :class="{ confirmed: !!confirmation }"
          :disabled="!canConfirm || confirming"
          @click="confirmRecord"
        >
          {{ confirmation ? '確認済み' : (confirming ? '処理中...' : '確認済み') }}
        </button>
      </div>
    </div>

    <div v-if="confirmation" class="confirmation-bar">
      確認済み: {{ confirmation.confirmed_by_name }} ({{ formatDateTime(confirmation.confirmed_at) }})
    </div>

    <div class="note">
      各製品計画数（sequence_no&gt;0）と実績数（sequence_no=0）を比較して表示します。計画数が0で実績数がある場合は「計画外」として表示されます。
    </div>

    <!-- レーザ重複実績セクション -->
    <div v-if="laserDuplicates.length" class="laser-duplicates-section">
      <h3>レーザ重複実績 ({{ laserDuplicates.length }} 件)</h3>
      <p class="laser-dup-note">同じ品番・同じ数量で複数レコードが登録されています。二重入力の可能性があります。</p>
      <table class="deviation-table dup-table">
        <thead>
          <tr>
            <th>品番</th>
            <th class="num">実績数</th>
            <th class="num">件数</th>
            <th>詳細</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dup in laserDuplicates" :key="`${dup.product_code}-${dup.total_qty}`" class="dup-row">
            <td>{{ dup.product_code }}</td>
            <td class="num">{{ dup.total_qty }}</td>
            <td class="num">{{ dup.count }}</td>
            <td class="dup-details">
              <span v-for="(rec, i) in dup.records" :key="rec.actual_id" class="dup-record">
                {{ rec.pattern_no }} x{{ rec.shot_count }} ({{ rec.equipment_code }}){{ i < dup.records.length - 1 ? '、' : '' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="summary" class="summary-bar">
      <span class="summary-item">合計: <strong>{{ summary.total }}</strong> 件</span>
      <span class="summary-item over">超過: <strong>{{ summary.over_count }}</strong> 件</span>
      <span class="summary-item short">不足: <strong>{{ summary.short_count }}</strong> 件</span>
      <span class="summary-item unplanned">計画外: <strong>{{ summary.unplanned_count }}</strong> 件</span>
    </div>

    <div v-if="loading" class="loading">読み込み中...</div>

    <table v-else-if="filteredItems.length" class="deviation-table">
      <thead>
        <tr>
          <th>ライン</th>
          <th>工程</th>
          <th>製品コード</th>
          <th>品名</th>
          <th class="num">計画数</th>
          <th class="num">実績数</th>
          <th class="num">乖離数</th>
          <th class="num">乖離率</th>
          <th>状態</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in filteredItems" :key="`${item.line_id}-${item.process_id}-${item.product_id}`"
            :class="item.status">
          <td>{{ item.line_code }}</td>
          <td>{{ item.process_name }}</td>
          <td>{{ item.product_code }}</td>
          <td>{{ item.product_name }}</td>
          <td class="num">{{ item.plan_qty }}<span v-if="ganttLineIds.has(item.line_id)" class="gantt-badge" title="ガント計画">G</span></td>
          <td class="num">{{ item.actual_qty }}</td>
          <td class="num" :class="item.status">
            {{ item.deviation > 0 ? '+' : '' }}{{ item.deviation }}
          </td>
          <td class="num" :class="item.status">
            {{ item.deviation_rate != null ? (item.deviation_rate > 0 ? '+' : '') + item.deviation_rate + '%' : '-' }}
          </td>
          <td>
            <span class="status-badge" :class="item.status">
              {{ statusLabel(item.status) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-else class="no-data">乖離データはありません</div>

    <!-- ガント計画適用ライン設定モーダル -->
    <div v-if="showGanttConfig" class="ds-overlay" @click.self="showGanttConfig = false">
      <div class="ds-modal" style="max-width: 500px;">
        <div class="ds-header">
          <h3>計画データソース設定</h3>
          <button class="ds-close" @click="showGanttConfig = false">×</button>
        </div>
        <div style="padding: 12px 18px 6px; font-size: 13px; color: #555;">
          ON: LineGanttPlanから計画数取得 / OFF: LineBacklogから取得（デフォルト）
        </div>
        <div style="padding: 4px 18px 6px; font-size: 12px; color: #c62828; background: #ffebee; margin: 6px 18px; border-radius: 4px; padding: 8px 12px; line-height: 1.6;">
          ⚠ ONにする前に、対象ラインの全製品の<strong>ガントチャート表示品マップ</strong>を設定してください。マップ未登録の製品は乖離レポートに表示されません。
        </div>
        <div style="padding: 8px 18px 16px; max-height: 400px; overflow-y: auto;">
          <table class="ds-table">
            <thead>
              <tr>
                <th>コード</th>
                <th>ライン名</th>
                <th style="text-align: center;">ガント計画</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in configLines" :key="line.id">
                <td style="font-family: monospace;">{{ line.line_code }}</td>
                <td>{{ line.line_name }}</td>
                <td style="text-align: center;">
                  <label class="toggle-switch">
                    <input
                      type="checkbox"
                      :checked="ganttLineIds.has(line.id)"
                      @change="toggleGanttLine(line.id, $event.target.checked)"
                    />
                    <span class="toggle-slider"></span>
                  </label>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showDataSource" class="ds-overlay" @click.self="showDataSource = false">
      <div class="ds-modal">
        <div class="ds-header">
          <h3>データソース — 計画乖離レポート</h3>
          <button class="ds-close" @click="showDataSource = false">×</button>
        </div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <tr><td>取得</td><td>line_backlog (sequence_no > 0)</td><td>計画数（plan_qty）の取得</td></tr>
            <tr><td>取得</td><td>line_backlog (sequence_no = 0)</td><td>実績数（actual_qty）の取得</td></tr>
            <tr><td>取得</td><td>t_laser_actual_detail</td><td>レーザー重複実績の検出</td></tr>
            <tr><td>取得</td><td>t_production_record_confirmation</td><td>確認済みフラグの取得</td></tr>
            <tr><td>保存</td><td>t_production_record_confirmation</td><td>確認ボタン押下時に確認者・日時を記録</td></tr>
            <tr><td>取得/保存</td><td>user_favorite</td><td>お気に入りフィルタ条件</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
const showDataSource = ref(false)
import api from '@/api/client'
import { authState } from '@/auth'

const targetDate = ref('')
const lineTypeFilter = ref('PROD')
const selectedLineId = ref('')
const selectedProcessId = ref('')
const statusFilter = ref('')
const loading = ref(false)
const items = ref([])
const summary = ref(null)
const lines = ref([])
const processes = ref([])
const laserDuplicates = ref([])
const confirmation = ref(null)
const confirming = ref(false)
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')

const showGanttConfig = ref(false)
const ganttLineIds = ref(new Set())

const configLines = computed(() => {
  if (!lineTypeFilter.value) return lines.value
  return lines.value.filter(l => l.line_type === lineTypeFilter.value)
})

async function toggleGanttLine(lineId, enabled) {
  try {
    const res = await api.planDeviationLineConfig.toggle(lineId, enabled)
    ganttLineIds.value = new Set(res.data.gantt_line_ids || [])
    loadReport()
  } catch (e) {
    console.error('ガント設定エラー:', e)
    alert('設定の保存に失敗しました。')
  }
}

const FAVORITE_SCREEN_KEY = 'production.plan_deviation_report'

const filteredLines = computed(() => {
  if (!lineTypeFilter.value) return lines.value
  return lines.value.filter(l => l.line_type === lineTypeFilter.value)
})

// 確認済みボタンはライン＋工程（全工程以外）を選択した時のみ有効
const canConfirm = computed(() => {
  return !!selectedLineId.value && !!selectedProcessId.value && !confirmation.value
})

const STATUS_LABELS = {
  over: '超過',
  short: '不足',
  unplanned: '計画外',
}

function statusLabel(status) {
  return STATUS_LABELS[status] || status
}

function formatDateTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.toLocaleDateString('ja-JP')} ${d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' })}`
}

const filteredItems = computed(() => {
  if (!statusFilter.value) return items.value
  if (statusFilter.value === 'exclude_unplanned') {
    return items.value.filter(item => item.status !== 'unplanned')
  }
  return items.value.filter(item => item.status === statusFilter.value)
})

async function loadLines() {
  try {
    const res = await api.lines.getLines()
    lines.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('ライン取得エラー:', e)
  }
}

async function loadProcesses(lineId) {
  if (!lineId) {
    processes.value = []
    return
  }
  try {
    const res = await api.processes.getProcesses({ line: lineId })
    processes.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('工程取得エラー:', e)
    processes.value = []
  }
}

const toFavoritePayload = () => ({
  targetDate: String(targetDate.value || ''),
  lineTypeFilter: String(lineTypeFilter.value || ''),
  selectedLineId: String(selectedLineId.value || ''),
  selectedProcessId: String(selectedProcessId.value || ''),
  statusFilter: String(statusFilter.value || ''),
})

async function applyFavorite() {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  const payload = target.payload || {}
  targetDate.value = String(payload.targetDate || targetDate.value || '')
  lineTypeFilter.value = String(payload.lineTypeFilter || 'PROD')
  selectedLineId.value = String(payload.selectedLineId || '')
  await loadProcesses(selectedLineId.value)
  selectedProcessId.value = String(payload.selectedProcessId || '')
  statusFilter.value = String(payload.statusFilter || '')
}

async function loadFavorites() {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得エラー:', e)
  }
}

async function saveFavorite() {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) {
      await api.accounts.updateFavorite(id, payload)
    } else {
      await api.accounts.createFavorite(payload)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存に失敗しました。'
    alert(`お気に入り保存エラー: ${detail}`)
  }
}

function onLineTypeChange() {
  selectedLineId.value = ''
  selectedProcessId.value = ''
  processes.value = []
  loadReport()
}

function onLineChange() {
  selectedProcessId.value = ''
  loadProcesses(selectedLineId.value)
  loadReport()
}

async function loadReport() {
  loading.value = true
  try {
    const params = {}
    if (targetDate.value) {
      params.date = targetDate.value
    }
    if (lineTypeFilter.value) {
      params.line_type = lineTypeFilter.value
    }
    if (selectedLineId.value) {
      params.line_id = selectedLineId.value
    }
    if (selectedProcessId.value) {
      params.process_id = selectedProcessId.value
    }
    const res = await api.planDeviationReport.get(params)
    items.value = res.data.items || []
    summary.value = res.data.summary || null
    laserDuplicates.value = res.data.laser_duplicates || []
    confirmation.value = res.data.confirmation || null
    if (res.data.gantt_line_ids) {
      ganttLineIds.value = new Set(res.data.gantt_line_ids)
    }
    // 初回ロード時、サーバーが返した日付（前営業日）をセット
    if (!targetDate.value && res.data.date) {
      targetDate.value = res.data.date
    }
  } catch (e) {
    console.error('レポート取得エラー:', e)
    items.value = []
    summary.value = null
    laserDuplicates.value = []
    confirmation.value = null
  } finally {
    loading.value = false
  }
}

async function confirmRecord() {
  if (!canConfirm.value || confirming.value) return
  confirming.value = true
  try {
    await api.recordConfirmations.confirm({
      work_date: targetDate.value,
      line_id: selectedLineId.value,
      process_id: selectedProcessId.value,
    })
    // レポート再読み込みで確認状態を更新
    await loadReport()
  } catch (e) {
    console.error('確認済み登録エラー:', e)
    alert('確認済みの登録に失敗しました。')
  } finally {
    confirming.value = false
  }
}

onMounted(() => {
  loadLines()
  loadFavorites()
  loadReport()
})
</script>

<style scoped>
.plan-deviation-report {
  padding: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.report-header h2 {
  margin: 0;
  font-size: 1.3em;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.header-controls input,
.header-controls select {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

.btn-reload {
  padding: 6px 16px;
  background: #4a90d9;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.btn-favorite {
  padding: 6px 10px;
  background: #facc15;
  color: #78350f;
  border: 1px solid #eab308;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  min-width: 34px;
}

.btn-favorite:hover {
  background: #eab308;
}

.btn-favorite:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reload:hover {
  background: #357abd;
}

.btn-reload:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-confirm {
  padding: 6px 16px;
  background: #e65100;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
}

.btn-confirm:hover:not(:disabled) {
  background: #bf360c;
}

.btn-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-confirm.confirmed {
  background: #2e7d32;
  cursor: default;
}

.confirmation-bar {
  padding: 8px 12px;
  margin-bottom: 10px;
  background: #e8f5e9;
  border-left: 3px solid #2e7d32;
  color: #1b5e20;
  font-size: 14px;
  font-weight: bold;
}

.note {
  padding: 8px 12px;
  margin-bottom: 10px;
  background: #fff5f5;
  border-left: 3px solid #d32f2f;
  color: #d32f2f;
  font-size: 14px;
  line-height: 1.5;
}

/* レーザ重複実績 */
.laser-duplicates-section {
  padding: 12px;
  margin-bottom: 16px;
  background: #fff3e0;
  border: 2px solid #e65100;
  border-radius: 8px;
}

.laser-duplicates-section h3 {
  margin: 0 0 4px;
  color: #e65100;
  font-size: 16px;
}

.laser-dup-note {
  margin: 0 0 8px;
  color: #bf360c;
  font-size: 13px;
}

.dup-table {
  font-size: 13px;
}

.dup-row td {
  background: #fff8e1;
}

.dup-details {
  font-size: 12px;
  color: #555;
}

.dup-record {
  white-space: nowrap;
}

.summary-bar {
  display: flex;
  gap: 20px;
  padding: 10px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 16px;
  font-size: 14px;
}

.summary-item.over {
  color: #d32f2f;
}

.summary-item.short {
  color: #1565c0;
}

.summary-item.unplanned {
  color: #e65100;
}

.loading,
.no-data {
  text-align: center;
  padding: 40px;
  color: #888;
  font-size: 14px;
}

.deviation-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.deviation-table th {
  background: #f0f0f0;
  padding: 8px 10px;
  text-align: left;
  border-bottom: 2px solid #ddd;
  white-space: nowrap;
}

.deviation-table td {
  padding: 7px 10px;
  border-bottom: 1px solid #eee;
}

.deviation-table th.num,
.deviation-table td.num {
  text-align: right;
}

.deviation-table tr.over td {
  background: #fff5f5;
}

.deviation-table tr.short td {
  background: #f5f8ff;
}

.deviation-table tr.unplanned td {
  background: #fff8e1;
}

td.over {
  color: #d32f2f;
  font-weight: bold;
}

td.short {
  color: #1565c0;
  font-weight: bold;
}

td.unplanned {
  color: #e65100;
  font-weight: bold;
}

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: bold;
}

.status-badge.over {
  background: #ffebee;
  color: #d32f2f;
}

.status-badge.short {
  background: #e3f2fd;
  color: #1565c0;
}

.status-badge.unplanned {
  background: #fff3e0;
  color: #e65100;
}
.btn-gantt-config {
  padding: 6px 10px;
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #86efac;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
.btn-gantt-config:hover { background: #dcfce7; }

.gantt-badge {
  display: inline-block;
  margin-left: 4px;
  padding: 0 4px;
  background: #dcfce7;
  color: #166534;
  border-radius: 3px;
  font-size: 10px;
  font-weight: bold;
  vertical-align: middle;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #cbd5e1;
  border-radius: 20px;
  transition: .2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background: #fff;
  border-radius: 50%;
  transition: .2s;
}
.toggle-switch input:checked + .toggle-slider { background: #22c55e; }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(16px); }

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

