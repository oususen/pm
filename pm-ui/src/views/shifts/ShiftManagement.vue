<template>
  <div class="shift-management">
    <div class="top">
      <h1>シフト管理</h1>
      <div class="tabs">
        <button :class="{ on: activeTab === 'chart' }" @click="activeTab = 'chart'">シフトチャート</button>
        <button :class="{ on: activeTab === 'week' }" @click="activeTab = 'week'">週間作成</button>
        <button :class="{ on: activeTab === 'master' }" @click="activeTab = 'master'">基本設定</button>
      </div>
      <div class="top-actions">
        <button class="btn" @click="printCurrent">印刷</button>
        <button class="btn primary" @click="focusEntry">＋配置</button>
      </div>
    </div>

    <!-- シフトチャートタブ -->
    <div v-show="activeTab === 'chart'">
      <section class="toolbar prepare-form card">
        <label><span class="field-label">ライン</span>
          <select v-model="currentLineId" @change="onLineChange">
            <option v-for="l in lines" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
        </label>
        <label><span class="field-label">日付</span><input v-model="selectedDate" type="date" @change="loadAssignments" /></label>
        <label><span class="field-label">開始</span><input v-model="rangeStart" type="time" @change="renderNeeded++" /></label>
        <label><span class="field-label">終了</span><input v-model="rangeEnd" type="time" @change="renderNeeded++" /></label>
        <label><span class="field-label">単位</span>
          <select v-model.number="step" @change="renderNeeded++">
            <option :value="15">15分</option><option :value="30">30分</option><option :value="60">1時間</option>
          </select>
        </label>
        <button class="btn reset" @click="resetShift">リセット</button>
      </section>

      <section ref="entryBox" :class="['prepare-form', 'entry', 'card', { editing: !!editingId }]">
        <b class="entry-title">{{ editingId ? '編集' : '配置' }}</b>
        <select v-model="entryWorkerId" @change="syncStartFromChart">
          <option v-for="w in currentWorkers" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
        <select v-model="entryLineProcessId">
          <option v-for="p in currentLineProcesses" :key="p.id" :value="p.id">{{ p.process_name }}</option>
        </select>
        <label><span class="field-label">開始</span><input v-model="entryStart" type="time" @change="updateEndPreview" /></label>
        <label><span class="field-label">実働</span>
          <select v-model.number="entryWorkHours" @change="updateEndPreview">
            <option v-for="opt in workHoursOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
          </select>
        </label>
        <span class="end-preview">{{ endPreviewText }}</span>
        <input v-model.number="entryUnits" type="number" min="0" style="width:65px" /><span>台</span>
        <input v-model="entryComment" class="comment" placeholder="コメント" />
        <button class="btn primary" @click="submitAssignment">{{ editingId ? '保存' : '追加' }}</button>
        <button v-if="editingId" class="btn" @click="cancelEdit">やめる</button>
      </section>

      <div class="chart-workspace">
        <section class="card chart-card">
          <div class="head">
            <div>
              <h2>{{ selectedDate.replaceAll('-', '/') }} シフト <span class="line-badge">{{ currentLineName }}</span></h2>
              <p>バーをクリックすると編集できます／黄色は自動休憩です</p>
            </div>
            <div class="legend">
              <span v-for="p in currentLineProcesses" :key="p.id">
                <i :style="{ background: p.color }"></i>{{ p.process_name }}
              </span>
              <span><i style="background:#ffd21f"></i>自動休憩</span>
            </div>
          </div>
          <div class="scroll">
            <div class="chart" v-html="chartHtml"></div>
          </div>
        </section>
        <aside class="stats side-stats" v-html="statsHtml"></aside>
      </div>
    </div>

    <!-- 週間作成タブ -->
    <div v-show="activeTab === 'week'">
      <section class="week-toolbar card">
        <label>ライン
          <select v-model="currentLineId" @change="onLineChange">
            <option v-for="l in lines" :key="l.id" :value="l.id">{{ l.name }}</option>
          </select>
        </label>
        <label>週の月曜日<input v-model="weekStartDate" type="date" @change="loadWeekData" /></label>
        <button class="btn" @click="printCurrent">週間シフトを印刷</button>
      </section>

      <section class="week-copy card">
        <h2>シフトをほかの日へコピー</h2>
        <p>同じ週の曜日、指定日、または次の週へコピーできます。</p>
        <div class="copy-row">
          <b>元の日</b>
          <select v-model.number="copySourceIdx">
            <option v-for="(d, i) in weekDates" :key="i" :value="i">{{ dayNames[i] }}曜日（{{ d.slice(5).replace('-', '/') }}）</option>
          </select>
          <b>同じ週のコピー先</b>
          <div class="targets">
            <label v-for="(d, i) in weekDates" :key="i" v-show="i !== copySourceIdx">
              <input type="checkbox" v-model="copyTargets" :value="i" /> {{ dayNames[i] }}曜日
            </label>
          </div>
          <button class="btn primary" @click="copyWeekShift">選択した日にコピー</button>
        </div>
        <div class="copy-row copy-extra">
          <b>指定日へ</b>
          <input v-model="copyToDateValue" type="date" />
          <button class="btn" @click="copyToSingleDate">この日へコピー</button>
          <b>1週間一括</b>
          <label>コピー先の月曜日 <input v-model="bulkWeekStart" type="date" /></label>
          <button class="btn primary" @click="copyWholeWeek">1週間を一括コピー</button>
        </div>
      </section>

      <section class="week-grid">
        <article v-for="(d, i) in weekDates" :key="d" class="card day-card" :class="{ today: d === todayStr }">
          <h3>{{ dayNames[i] }}曜日</h3>
          <div class="date">{{ d.replaceAll('-', '/') }}</div>
          <div class="summary">
            配置：<b>{{ weekSummary[d]?.count || 0 }}件</b><br/>
            作業時間：<b>{{ fmtHours(weekSummary[d]?.hours || 0) }}</b><br/>
            予定台数：<b>{{ weekSummary[d]?.units || 0 }}台</b>
          </div>
          <button class="btn" @click="goDay(d)">この日を編集</button>
        </article>
      </section>

      <section class="week-print card" v-html="weekPrintHtml"></section>
    </div>

    <!-- 基本設定タブ -->
    <div v-show="activeTab === 'master'" class="master">
      <section class="card panel line-panel">
        <div class="panelhead">
          <h2>ライン登録</h2>
          <button class="btn" @click="addLine">＋追加</button>
        </div>
        <div v-for="l in lines" :key="l.id" :class="['mrow', 'line', { active: l.id === currentLineId }]">
          <input :value="l.name" @change="updateLineName(l.id, $event.target.value)" />
          <button class="switch" @click="switchLine(l.id)">{{ l.id === currentLineId ? '選択中' : '切替' }}</button>
          <button class="del" @click="deleteLine(l.id)">削除</button>
        </div>
      </section>

      <section class="card panel">
        <div class="panelhead">
          <h2>作業者（{{ currentLineName }}）</h2>
          <button class="btn" @click="showWorkerPicker = true">＋追加</button>
        </div>
        <div v-for="(w, i) in currentWorkers" :key="w.id" class="mrow worker-row">
          <span class="worker-name-cell">{{ w.name }}<small v-if="w.user_display_name" class="user-tag">{{ w.user_display_name }}</small></span>
          <select :value="w.shift_type" @change="updateWorkerField(w.id, 'shift_type', $event.target.value)">
            <option value="朝">朝</option>
            <option value="昼">昼</option>
            <option value="夜">夜</option>
          </select>
          <label class="worktime"><span>出勤</span>
            <input type="time" :value="w.work_start" @change="updateWorkerField(w.id, 'work_start', $event.target.value)" />
          </label>
          <label class="worktime"><span>退勤</span>
            <input type="time" :value="w.work_end" @change="updateWorkerField(w.id, 'work_end', $event.target.value)" />
          </label>
          <div class="order-buttons">
            <button :disabled="i === 0" @click="moveWorker(w.id, -1)">↑</button>
            <button :disabled="i === currentWorkers.length - 1" @click="moveWorker(w.id, 1)">↓</button>
          </div>
          <button class="del" @click="deleteWorker(w.id)">削除</button>
        </div>
      </section>

      <section class="card panel">
        <div class="panelhead">
          <h2>工程・活動設定（{{ currentLineName }}）</h2>
          <div class="panelhead-actions">
            <button class="btn" @click="showProcessPicker = true">＋工程</button>
            <button class="btn activity-btn" @click="addActivity">＋活動</button>
          </div>
        </div>
        <div v-for="lp in currentLineProcesses" :key="lp.id" class="mrow proc">
          <input type="color" class="color-pick" :value="lp.color" @change="updateLineProcess(lp.id, 'color', $event.target.value)" />
          <span v-if="!lp.is_activity"><i class="color-dot" :style="{ background: lp.color }"></i>{{ lp.process_name }}（{{ lp.process_code }}）</span>
          <span v-else class="activity-name-row">
            <i class="color-dot" :style="{ background: lp.color }"></i>
            <input class="activity-name-input" :value="lp.process_name" placeholder="活動名を入力" @change="updateLineProcess(lp.id, 'custom_name', $event.target.value)" />
            <small class="activity-tag">活動</small>
          </span>
          <button class="del" @click="deleteLineProcess(lp.id)">削除</button>
        </div>
      </section>

      <!-- 工程選択ダイアログ -->
      <div v-if="showProcessPicker" class="modal-overlay" @click.self="showProcessPicker = false">
        <div class="modal card">
          <h3>工程を追加</h3>
          <input v-model="processSearch" placeholder="工程名・コードで検索" style="width:100%;margin-bottom:10px" />
          <div class="process-list">
            <div v-for="p in filteredMasterProcesses" :key="p.id" class="process-item" @click="addLineProcess(p)">
              {{ p.process_code }} — {{ p.process_name }}
            </div>
          </div>
          <button class="btn" @click="showProcessPicker = false" style="margin-top:10px">閉じる</button>
        </div>
      </div>

      <!-- ユーザー選択ダイアログ -->
      <div v-if="showWorkerPicker" class="modal-overlay" @click.self="showWorkerPicker = false">
        <div class="modal card">
          <h3>作業者を追加（ユーザーから選択）</h3>
          <input v-model="userSearch" placeholder="名前・ユーザー名で検索" style="width:100%;margin-bottom:10px" />
          <div class="process-list">
            <div v-for="u in filteredUsers" :key="u.id" class="process-item" @click="addWorkerFromUser(u)">
              {{ u.last_name }} {{ u.first_name }}<small style="color:#667085;margin-left:8px">{{ u.username }}</small>
            </div>
            <div v-if="!filteredUsers.length" style="padding:12px;color:#667085">該当するユーザーがいません</div>
          </div>
          <button class="btn" @click="showWorkerPicker = false" style="margin-top:10px">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import api from '@/api/client'

// --- 状態 ---
const lines = ref([])
const currentLineId = ref(null)
const selectedDate = ref(new Date().toISOString().slice(0, 10))
const rangeStart = ref('08:00')
const rangeEnd = ref('22:00')
const step = ref(30)
const activeTab = ref('chart')
const renderNeeded = ref(0)
const saveStatus = ref('')

const assignments = ref([])
const weekAssignments = ref([])
const masterProcesses = ref([])

// 配置入力
const entryBox = ref(null)
const editingId = ref(null)
const entryWorkerId = ref(null)
const entryProcessId = ref(null)
const entryLineProcessId = ref(null)
const entryStart = ref('08:00')
const entryWorkHours = ref(2)
const entryUnits = ref(10)
const entryComment = ref('')
const endPreviewText = ref('')

// 週間
const dayNames = ['月', '火', '水', '木', '金', '土', '日']
const todayStr = new Date().toISOString().slice(0, 10)
const weekStartDate = ref('')
const copySourceIdx = ref(0)
const copyTargets = ref([])
const copyToDateValue = ref('')
const bulkWeekStart = ref('')

// 基本設定
const showProcessPicker = ref(false)
const processSearch = ref('')
const showWorkerPicker = ref(false)
const userSearch = ref('')
const allUsers = ref([])

// 工程別負荷時間（動的）
const processLoads = ref({})

// --- 計算プロパティ ---
const currentLine = computed(() => lines.value.find(l => l.id === currentLineId.value))
const currentLineName = computed(() => currentLine.value?.name || '')
const currentWorkers = computed(() => currentLine.value?.workers || [])
const currentLineProcesses = computed(() => currentLine.value?.line_processes || [])
const processMap = computed(() => {
  const m = {}
  for (const lp of currentLineProcesses.value) {
    if (lp.process) m[lp.process] = lp
  }
  return m
})
const lineProcessMap = computed(() => {
  const m = {}
  for (const lp of currentLineProcesses.value) m[lp.id] = lp
  return m
})

const filteredUsers = computed(() => {
  const existingUserIds = new Set(currentWorkers.value.filter(w => w.user).map(w => w.user))
  let list = allUsers.value.filter(u => u.is_active && !existingUserIds.has(u.id))
  if (userSearch.value) {
    const q = userSearch.value.toLowerCase()
    list = list.filter(u =>
      (u.last_name + u.first_name).toLowerCase().includes(q) ||
      u.username.toLowerCase().includes(q)
    )
  }
  return list
})

const filteredMasterProcesses = computed(() => {
  const existing = new Set(currentLineProcesses.value.map(lp => lp.process))
  let list = masterProcesses.value.filter(p => p.is_active && !existing.has(p.id))
  if (processSearch.value) {
    const q = processSearch.value.toLowerCase()
    list = list.filter(p => p.process_name.toLowerCase().includes(q) || p.process_code.toLowerCase().includes(q))
  }
  return list
})

const workHoursOptions = computed(() => {
  const opts = []
  for (let i = 1; i <= 48; i++) {
    const v = i / 4
    const label = v < 1 ? Math.round(v * 60) + '分' : Number.isInteger(v) ? v + '時間' : Math.floor(v) + '時間' + Math.round((v % 1) * 60) + '分'
    opts.push({ value: v, label })
  }
  return opts
})

const weekDates = computed(() => {
  if (!weekStartDate.value) return []
  const base = new Date(weekStartDate.value + 'T00:00:00')
  return dayNames.map((_, i) => {
    const d = new Date(base)
    d.setDate(base.getDate() + i)
    return isoDate(d)
  })
})

const weekSummary = computed(() => {
  const summary = {}
  for (const d of weekDates.value) {
    const dayAssigns = weekAssignments.value.filter(a => a.date === d)
    summary[d] = {
      count: dayAssigns.length,
      hours: dayAssigns.reduce((s, a) => s + netDuration(a), 0),
      units: dayAssigns.reduce((s, a) => s + (a.units || 0), 0),
    }
  }
  return summary
})

// --- 時間ユーティリティ ---
function tm(t) {
  if (!t) return 0
  const parts = t.split(':').map(Number)
  return parts[0] * 60 + parts[1]
}

function clockLabel(v) {
  let h = Math.floor(v / 60)
  const m = v % 60
  if (h > 24) h -= 24
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0')
}

function absMinute(t, anchor) {
  let v = tm(t)
  if (v < anchor) v += 1440
  return v
}

function fmtHours(n) {
  return (Math.abs(n - Math.round(n)) < 0.01 ? Math.round(n) : n.toFixed(1)) + 'h'
}

function isoDate(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
}

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}

// --- 休憩計算 ---
function breaksForSpan(start, end) {
  const clock = start % 1440
  const late = clock >= 15 * 60 || clock < 5 * 60
  const breaks = []
  if (late) {
    for (const [offset, len, label] of [[120, 10, '休憩'], [250, 45, '昼休憩'], [415, 10, '休憩'], [545, 10, '休憩']]) {
      breaks.push({ start: start + offset, end: start + offset + len, label })
    }
  } else {
    const regularEnd = start + 545
    for (const [offset, len, label] of [[120, 10, '休憩'], [240, 45, '昼休憩'], [420, 10, '休憩']]) {
      const bstart = start + offset
      if (bstart < regularEnd) breaks.push({ start: bstart, end: bstart + len, label })
    }
    if (end > regularEnd) {
      breaks.push({ start: regularEnd, end: regularEnd + 10, label: '残業前休憩' })
      for (let bstart = regularEnd + 130; bstart < end; bstart += 130) {
        breaks.push({ start: bstart, end: bstart + 10, label: '残業休憩' })
      }
    }
  }
  return breaks.filter(b => b.start < end)
}

function workerEarliestStart(workerId, date, anchor, ignoreId = null) {
  const jobs = assignments.value.filter(a =>
    a.worker === workerId && a.date === date && a.id !== ignoreId
  )
  if (!jobs.length) return null
  return Math.min(...jobs.map(a => absMinute(a.start_time, anchor)))
}

function workerDay(workerId, date, anchor, ignoreId = null) {
  const jobs = assignments.value.filter(a =>
    a.worker === workerId && a.date === date && a.id !== ignoreId
  )
  if (!jobs.length) return null
  const startMin = Math.min(...jobs.map(a => absMinute(a.start_time, anchor)))
  let endMax = startMin
  for (const a of jobs) {
    const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, anchor, a.id)
    endMax = Math.max(endMax, e)
  }
  return { start: startMin, end: endMax }
}

function autoBreaks(workerId, date, anchor) {
  const day = workerDay(workerId, date, anchor)
  return day ? breaksForSpan(day.start, day.end) : []
}

function shiftFromStart(start) {
  const c = start % 1440
  if (c >= 5 * 60 && c < 12 * 60) return { name: '朝', css: 'morning' }
  if (c >= 12 * 60 && c < 17 * 60 + 5) return { name: '昼', css: 'day' }
  return { name: '夜', css: 'night' }
}

function endFromWorkHoursCalc(startText, hours, workerId, date, anchor, ignoreId = null) {
  const earliest = workerId && date ? workerEarliestStart(workerId, date, anchor, ignoreId) : null
  let start = absMinute(startText, anchor)
  const shiftStart = earliest !== null ? Math.min(earliest, start) : start
  while (start < shiftStart) start += 1440
  const target = Math.round(hours * 60)
  const horizon = start + target + 720
  const breaks = breaksForSpan(shiftStart, horizon)
  let worked = 0, t = start
  while (worked < target && t < start + 2880) {
    if (!breaks.some(b => t >= b.start && t < b.end)) worked++
    t++
  }
  return t
}

function netDuration(a) {
  const anchor = tm(rangeStart.value)
  const day = workerDay(a.worker, a.date, anchor)
  let s = absMinute(a.start_time, anchor)
  if (day) while (s < day.start) s += 1440
  let e = tm(a.end_time || clockLabel(endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, anchor, a.id)))
  while (e <= s) e += 1440
  let mins = e - s
  autoBreaks(a.worker, a.date, anchor).forEach(b => {
    mins -= Math.max(0, Math.min(e, b.end) - Math.max(s, b.start))
  })
  return Math.max(0, mins) / 60
}

function resolveLP(a) {
  if (a.line_process) return lineProcessMap.value[a.line_process]
  if (a.process) return processMap.value[a.process]
  return null
}

// --- チャート描画 ---
const chartHtml = computed(() => {
  void renderNeeded.value
  const sm = tm(rangeStart.value)
  let em = tm(rangeEnd.value)
  if (em <= sm) em += 1440
  const total = em - sm
  const ticks = []
  for (let t = sm; t <= em; t += step.value) ticks.push(t)

  const active = assignments.value.filter(a => a.shift_line === currentLineId.value && a.date === selectedDate.value)
  let h = '<div class="nh">作業者</div><div class="axis">' +
    ticks.map((t, i) => `<span style="left:${(t - sm) / total * 100}%">${i % Math.max(1, 60 / step.value) === 0 ? Math.floor((t % 1440) / 60) + ':' + String(t % 60).padStart(2, '0') : ''}</span>`).join('') + '</div>'

  for (const w of currentWorkers.value) {
    const day = workerDay(w.id, selectedDate.value, sm)
    const actualStart = day ? clockLabel(day.start) : w.work_start
    const actualShift = day ? shiftFromStart(day.start) : { name: w.shift_type, css: w.shift_type === '夜' ? 'night' : w.shift_type === '昼' ? 'day' : 'morning' }
    const dayJobs = assignments.value.filter(a => a.worker === w.id && a.date === selectedDate.value)
    const totalWork = dayJobs.reduce((sum, a) => sum + netDuration(a), 0)
    const breaks = autoBreaks(w.id, selectedDate.value, sm).filter(b => b.end > sm && b.start < em)

    h += `<div class="row"><div class="worker shift-${actualShift.css}"><b>${esc(w.name)}</b><small class="shift-info">${actualShift.name}勤 · ${actualStart}出勤</small><small class="worker-total">実働合計 ${fmtHours(totalWork)}</small></div><div class="track">`
    h += ticks.map(t => `<i class="gridline" style="left:${(t - sm) / total * 100}%"></i>`).join('')

    for (const a of active.filter(x => x.worker === w.id)) {
      const p = resolveLP(a)
      if (!p) continue
      const s = absMinute(a.start_time, sm)
      let e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
      const color = p.color || '#64748b'
      h += `<div class="bar" data-id="${a.id}" style="left:${(s - sm) / total * 100}%;width:${(e - s) / total * 100}%;background:${color}" title="${esc(a.comment || 'クリックで編集')}"><button class="bar-delete" data-delete="${a.id}" title="削除">×</button><b>${esc(p.process_name)} <em>${a.units || 0}台</em></b><span>${a.start_time}–${clockLabel(e)} · 実働${fmtHours(netDuration(a))}${a.comment ? ' · ' + esc(a.comment) : ''}</span></div>`
    }

    for (const b of breaks) {
      const bs = Math.max(sm, b.start), be = Math.min(em, b.end)
      h += `<div class="break-bar ${b.label === '昼休憩' ? 'meal' : 'short'}" style="left:${(bs - sm) / total * 100}%;width:${(be - bs) / total * 100}%" title="${b.label} ${clockLabel(b.start)}～${clockLabel(b.end)}"><b>${b.label}</b><span>${clockLabel(b.start)}～${clockLabel(b.end)}</span></div>`
    }
    if (breaks.length) {
      h += `<div class="break-summary"><strong>自動休憩</strong>${breaks.map(b => `<span class="${b.label === '昼休憩' ? 'meal-text' : ''}">${b.label} ${clockLabel(b.start)}～${clockLabel(b.end)}</span>`).join('')}</div>`
    }
    h += '</div></div>'
  }
  return h
})

const statsHtml = computed(() => {
  void renderNeeded.value
  const sm = tm(rangeStart.value)
  const active = assignments.value.filter(a => a.shift_line === currentLineId.value && a.date === selectedDate.value)
  let finalEnd = 0
  for (const a of active) {
    const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
    finalEnd = Math.max(finalEnd, e)
  }
  const finalText = finalEnd ? (finalEnd >= 1440 ? '翌日 ' : '') + clockLabel(finalEnd) : '未設定'
  let h = `<article class="card final-summary"><small>このラインの最終終了時刻</small><strong>${finalText}</strong><span>${active.length ? active.length + '件の配置から自動計算' : '配置を追加すると表示されます'}</span></article>`

  for (const p of currentLineProcesses.value) {
    const placed = active.filter(a => {
      if (a.line_process) return a.line_process === p.id
      return a.process && a.process === p.process
    }).reduce((s, a) => s + netDuration(a), 0)
    const loadData = p.process ? processLoads.value[String(p.process)] : null
    const req = loadData ? +loadData.load_hours : 0
    const d = placed - req
    const achieved = req <= 0 ? true : d >= -0.01
    const rate = req > 0 ? Math.round(placed / req * 100) : (placed > 0 ? 100 : 0)
    const reqLabel = req > 0 ? fmtHours(req) : '負荷なし'
    h += `<article class="card stat"><header><span><i style="background:${p.color}"></i>${esc(p.process_name)}</span><b class="${achieved ? 'good' : 'bad'}">${req <= 0 ? '負荷なし' : achieved ? (Math.abs(d) < 0.01 ? '達成' : fmtHours(d) + '余裕') : fmtHours(-d) + '不足'}</b></header><div class="meter"><span class="${achieved ? 'achievement-good' : 'achievement-bad'}" style="width:${Math.min(100, rate)}%"></span></div><p>達成度 <b>${rate}%</b><span>必要 ${reqLabel}／配置 ${fmtHours(placed)}</span></p></article>`
  }
  return h
})

// --- 週間印刷 ---
const weekPrintHtml = computed(() => {
  if (!weekDates.value.length) return ''
  const dates = weekDates.value.slice(0, 5)
  const sm = tm(rangeStart.value)
  let em = tm(rangeEnd.value)
  if (em <= sm) em += 1440
  const total = em - sm
  const tickValues = [sm, sm + 360, sm + 720, sm + 1080, em].filter((v, i, a) => v <= em && a.indexOf(v) === i)
  const axis = tickValues.map(v => clockLabel(v).replace(':00', '時')).join('・')

  let h = `<h2>週間シフトチャート　${esc(currentLineName.value)}</h2><div class="sub">${dates[0].replaceAll('-', '/')} ～ ${dates[4].replaceAll('-', '/')}（月～金）</div>`
  h += `<table class="week-table"><thead><tr><th>作業者</th>${dates.map((d, i) => `<th>${dayNames[i]}曜日<br>${d.slice(5).replace('-', '/')}<small class="week-axis">${axis}</small></th>`).join('')}</tr></thead><tbody>`

  for (const w of currentWorkers.value) {
    h += `<tr><th>${esc(w.name)}<br><small>${w.shift_type}勤</small></th>`
    for (const d of dates) {
      const jobs = weekAssignments.value.filter(a => a.shift_line === currentLineId.value && a.date === d && a.worker === w.id).sort((a, b) => absMinute(a.start_time, sm) - absMinute(b.start_time, sm))
      if (!jobs.length) { h += '<td>－</td>'; continue }
      const bars = jobs.map(a => {
        const p = resolveLP(a) || { process_name: '不明', color: '#64748b' }
        const s = absMinute(a.start_time, sm)
        const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
        const cs = Math.max(sm, s), ce = Math.min(em, e)
        return ce <= cs ? '' : `<div class="week-mini-bar" style="--bar-color:${p.color};background:${p.color};left:${(cs - sm) / total * 100}%;width:${Math.max(1, (ce - cs) / total * 100)}%">${esc(p.process_name)}</div>`
      }).join('')
      const details = jobs.map(a => {
        const p = resolveLP(a) || { process_name: '不明' }
        return `<div class="week-detail">${a.start_time}～${clockLabel(endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id))}　${esc(p.process_name)}　${a.units || 0}台</div>`
      }).join('')
      h += `<td><div class="week-mini-row">${bars}</div>${details}</td>`
    }
    h += '</tr>'
  }
  h += '</tbody></table>'
  return h
})

// --- API操作 ---
async function loadLines() {
  const { data } = await api.shifts.getLines()
  lines.value = data
  if (data.length && !currentLineId.value) {
    currentLineId.value = data[0].id
  }
  if (data.length && !data.find(l => l.id === currentLineId.value)) {
    currentLineId.value = data[0].id
  }
}

async function loadAssignments() {
  if (!currentLineId.value) return
  const { data } = await api.shifts.getAssignments({
    shift_line: currentLineId.value,
    date: selectedDate.value,
  })
  assignments.value = data
  renderNeeded.value++
  await loadProcessLoads()
}

async function loadProcessLoads() {
  if (!currentLineId.value || !selectedDate.value) return
  try {
    const { data } = await api.shifts.getProcessLoads(currentLineId.value, selectedDate.value)
    processLoads.value = data.loads || {}
  } catch (e) {
    processLoads.value = {}
  }
}

async function loadWeekData() {
  if (!currentLineId.value || !weekStartDate.value) return
  const dates = weekDates.value
  if (!dates.length) return
  const { data } = await api.shifts.getAssignmentsByRange({
    shift_line: currentLineId.value,
    date_from: dates[0],
    date_to: dates[6],
  })
  weekAssignments.value = data
}

async function loadMasterProcesses() {
  const { data } = await api.processes.getProcesses()
  masterProcesses.value = data
}

async function loadUsers() {
  const { data } = await api.accounts.getUsers({ is_active: true, page_size: 500 })
  allUsers.value = Array.isArray(data) ? data : (data.results || [])
}

async function onLineChange() {
  await loadAssignments()
  await loadWeekData()
  syncStartFromChart()
}

// 配置操作
async function submitAssignment() {
  if (!entryWorkerId.value || !entryLineProcessId.value || !entryWorkHours.value) {
    alert('作業者・工程/活動・実働時間を入力してください')
    return
  }
  try {
    const lp = lineProcessMap.value[entryLineProcessId.value]
    const payload = {
      shift_line: currentLineId.value,
      date: selectedDate.value,
      worker: entryWorkerId.value,
      process: lp?.process || null,
      line_process: entryLineProcessId.value,
      start_time: entryStart.value,
      work_hours: entryWorkHours.value,
      units: entryUnits.value || 0,
      comment: entryComment.value.trim(),
    }
    if (editingId.value) {
      await api.shifts.updateAssignment(editingId.value, payload)
    } else {
      await api.shifts.createAssignment(payload)
    }
    entryComment.value = ''
    cancelEdit()
    await loadAssignments()
    syncStartFromChart()
  } catch (e) {
    console.error('配置保存エラー:', e)
    alert('配置の保存に失敗しました: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteAssignmentById(id) {
  const a = assignments.value.find(x => x.id === id)
  if (!a) return
  const p = resolveLP(a)
  if (!confirm((p ? p.process_name : 'この配置') + '（' + a.start_time + '）を削除しますか？')) return
  await api.shifts.deleteAssignment(id)
  await loadAssignments()
  syncStartFromChart()
}

function editAssignment(id) {
  const a = assignments.value.find(x => x.id === id)
  if (!a) return
  editingId.value = id
  entryWorkerId.value = a.worker
  if (a.line_process) {
    entryLineProcessId.value = a.line_process
  } else if (a.process) {
    const lp = currentLineProcesses.value.find(p => p.process === a.process)
    entryLineProcessId.value = lp ? lp.id : null
  } else {
    entryLineProcessId.value = null
  }
  entryProcessId.value = a.process
  entryStart.value = a.start_time
  entryWorkHours.value = +a.work_hours
  entryUnits.value = a.units || 0
  entryComment.value = a.comment || ''
  updateEndPreview()
  nextTick(() => entryBox.value?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
}

function cancelEdit() {
  editingId.value = null
  syncStartFromChart()
}

async function resetShift() {
  const count = assignments.value.filter(a => a.shift_line === currentLineId.value && a.date === selectedDate.value).length
  if (!count) { alert('このシフトには配置がありません。'); return }
  if (!confirm(selectedDate.value + '・' + currentLineName.value + 'の配置をすべて削除しますか？')) return
  await api.shifts.resetDay({ shift_line: currentLineId.value, date: selectedDate.value })
  await loadAssignments()
}

function syncStartFromChart() {
  if (editingId.value) { updateEndPreview(); return }
  const anchor = tm(rangeStart.value)
  const day = workerDay(entryWorkerId.value, selectedDate.value, anchor)
  if (day) {
    let next = day.end
    const breaks = breaksForSpan(day.start, day.end + 720)
    const rest = breaks.find(b => next >= b.start && next < b.end)
    if (rest) next = rest.end
    entryStart.value = clockLabel(next)
  }
  updateEndPreview()
}

function updateEndPreview() {
  if (!entryStart.value || !entryWorkHours.value) return
  const anchor = tm(rangeStart.value)
  const end = endFromWorkHoursCalc(entryStart.value, entryWorkHours.value, entryWorkerId.value, selectedDate.value, anchor, editingId.value)
  const next = end >= 1440 ? '（翌日）' : ''
  endPreviewText.value = '終了 ' + clockLabel(end) + next + '（休憩込み）'
}

function focusEntry() {
  entryBox.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// ライン操作
async function addLine() {
  await api.shifts.createLine({ name: '新しいライン', sort_order: lines.value.length })
  await loadLines()
  currentLineId.value = lines.value[lines.value.length - 1].id
  await loadAssignments()
}

async function updateLineName(id, name) {
  await api.shifts.updateLine(id, { name })
  await loadLines()
}

async function switchLine(id) {
  currentLineId.value = id
  cancelEdit()
  await loadAssignments()
  await loadWeekData()
}

async function deleteLine(id) {
  if (lines.value.length <= 1) { alert('ラインは1つ以上必要です'); return }
  if (!confirm('このラインと関連データを削除しますか？')) return
  await api.shifts.deleteLine(id)
  await loadLines()
  await loadAssignments()
}

// 作業者操作
async function addWorkerFromUser(user) {
  const displayName = (user.last_name + ' ' + user.first_name).trim() || user.username
  await api.shifts.createWorker({
    shift_line: currentLineId.value,
    user: user.id,
    name: displayName,
    shift_type: '朝',
    work_start: '08:00',
    work_end: '17:00',
    sort_order: currentWorkers.value.length,
  })
  showWorkerPicker.value = false
  userSearch.value = ''
  await loadLines()
}

async function updateWorkerField(id, field, value) {
  await api.shifts.updateWorker(id, { [field]: value })
  await loadLines()
  await loadAssignments()
}

async function moveWorker(id, dir) {
  const workers = [...currentWorkers.value]
  const i = workers.findIndex(w => w.id === id)
  const j = i + dir
  if (i < 0 || j < 0 || j >= workers.length) return
  ;[workers[i], workers[j]] = [workers[j], workers[i]]
  await api.shifts.reorderWorkers(currentLineId.value, workers.map(w => w.id))
  await loadLines()
}

async function deleteWorker(id) {
  if (!confirm('この作業者と配置を削除しますか？')) return
  await api.shifts.deleteWorker(id)
  await loadLines()
  await loadAssignments()
}

// 工程操作
async function addLineProcess(masterProcess) {
  await api.shifts.createLineProcess({
    shift_line: currentLineId.value,
    process: masterProcess.id,
    color: '#64748b',
    required_hours: 1,
    sort_order: currentLineProcesses.value.length,
  })
  showProcessPicker.value = false
  processSearch.value = ''
  await loadLines()
}

async function addActivity() {
  const name = prompt('活動名を入力してください（例: 掃除, 5S, 学習, 習熟）')
  if (!name?.trim()) return
  await api.shifts.createLineProcess({
    shift_line: currentLineId.value,
    process: null,
    custom_name: name.trim(),
    color: '#94a3b8',
    sort_order: currentLineProcesses.value.length,
  })
  await loadLines()
}

async function updateLineProcess(id, field, value) {
  try {
    await api.shifts.updateLineProcess(id, { [field]: value })
    await loadLines()
  } catch (e) {
    console.error('工程設定更新エラー:', e)
    alert('保存に失敗しました: ' + (e.response?.data ? JSON.stringify(e.response.data) : e.message))
  }
}

async function deleteLineProcess(id) {
  if (!confirm('この工程設定を削除しますか？')) return
  await api.shifts.deleteLineProcess(id)
  await loadLines()
}

// 週間コピー
async function copyWeekShift() {
  const dates = weekDates.value
  const sourceDate = dates[copySourceIdx.value]
  const targetDates = copyTargets.value.map(i => dates[i])
  if (!targetDates.length) { alert('コピー先を1日以上選択してください。'); return }
  if (!confirm(sourceDate + 'のシフトを ' + targetDates.join('、') + ' へコピーします。')) return
  await api.shifts.copyDay({ shift_line: currentLineId.value, source_date: sourceDate, target_dates: targetDates })
  copyTargets.value = []
  await loadWeekData()
  await loadAssignments()
  alert('コピーしました。')
}

async function copyToSingleDate() {
  if (!copyToDateValue.value) { alert('日付を選択してください。'); return }
  const sourceDate = weekDates.value[copySourceIdx.value]
  if (!confirm(sourceDate + ' → ' + copyToDateValue.value + ' へコピーします。')) return
  await api.shifts.copyDay({ shift_line: currentLineId.value, source_date: sourceDate, target_dates: [copyToDateValue.value] })
  await loadWeekData()
  await loadAssignments()
  alert('コピーしました。')
}

async function copyWholeWeek() {
  if (!bulkWeekStart.value) { alert('コピー先の月曜日を選択してください。'); return }
  const sourceDates = weekDates.value
  const baseDate = new Date(bulkWeekStart.value + 'T00:00:00')
  const targetDates = dayNames.map((_, i) => {
    const d = new Date(baseDate)
    d.setDate(baseDate.getDate() + i)
    return isoDate(d)
  })
  if (sourceDates[0] === targetDates[0]) { alert('元の週とコピー先が同じです。'); return }
  if (!confirm(sourceDates[0] + '～' + sourceDates[6] + ' を ' + targetDates[0] + '～' + targetDates[6] + ' へ一括コピーします。')) return

  for (let i = 0; i < 7; i++) {
    const src = weekAssignments.value.filter(a => a.date === sourceDates[i])
    if (src.length) {
      await api.shifts.copyDay({ shift_line: currentLineId.value, source_date: sourceDates[i], target_dates: [targetDates[i]] })
    }
  }
  await loadWeekData()
  alert('1週間分を一括コピーしました。')
}

function goDay(d) {
  selectedDate.value = d
  activeTab.value = 'chart'
  loadAssignments()
}

function printCurrent() {
  const isWeek = activeTab.value === 'week'
  const w = window.open('', '_blank')
  if (!w) { alert('ポップアップがブロックされました'); return }

  const title = isWeek
    ? `週間シフト ${currentLineName.value} ${weekDates.value[0]?.replaceAll('-','/')}～${weekDates.value[4]?.replaceAll('-','/')}`
    : `${selectedDate.value.replaceAll('-','/')} シフト ${currentLineName.value}`

  let body = ''
  if (isWeek) {
    body = buildWeekPrintBody()
  } else {
    body = buildChartPrintBody()
  }

  w.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8"><title>${esc(title)}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Meiryo','Hiragino Sans',sans-serif;font-size:11px;color:#17243a;padding:12mm 10mm;print-color-adjust:exact;-webkit-print-color-adjust:exact}
@page{size:A4 landscape;margin:8mm}
h1{font-size:16px;margin-bottom:2px}
.subtitle{color:#667085;font-size:10px;margin-bottom:10px}
.legend{display:flex;gap:12px;margin-bottom:8px;font-size:10px;font-weight:bold;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle;print-color-adjust:exact;-webkit-print-color-adjust:exact}

/* チャート */
.chart-grid{display:grid;grid-template-columns:120px 1fr;border:1px solid #bcc5d3;border-radius:4px;overflow:hidden}
.nh{padding:6px 8px;background:#eef3f8;font-weight:bold;font-size:10px;border-right:1px solid #bcc5d3;border-bottom:1px solid #bcc5d3}
.axis{position:relative;height:28px;background:#eef3f8;border-bottom:1px solid #bcc5d3}
.axis span{position:absolute;top:8px;font-size:8px;color:#526174;font-weight:bold;transform:translateX(-50%)}
.row{display:contents}
.worker-cell{border-right:1px solid #bcc5d3;border-bottom:1px solid #dde3ec;padding:5px 8px;font-size:9px;line-height:1.4}
.worker-cell b{display:block;font-size:10px}
.worker-cell small{display:block;color:#667085}
.track{position:relative;border-bottom:1px solid #dde3ec;height:52px}
.gridline{position:absolute;height:100%;width:1px;background:#edf0f4}
.bar{position:absolute;top:4px;height:26px;border-radius:4px;color:white;padding:2px 6px;overflow:hidden;font-size:8px;font-weight:bold;white-space:nowrap;text-overflow:ellipsis;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.bar .detail{display:block;font-size:7px;font-weight:normal;margin-top:1px}
.break-bar{position:absolute;top:3px;height:28px;background:#ffd52b;border:1px solid #c9a000;border-radius:3px;text-align:center;font-size:7px;color:#493700;padding:2px;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.break-bar b,.break-bar span{display:block;font-size:7px;line-height:1.3}
.break-info{position:absolute;left:0;right:0;bottom:2px;font-size:7px;color:#7a6200;padding:0 6px;white-space:nowrap;overflow:hidden}

/* 統計 */
.stats-row{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.stat-box{flex:1;min-width:120px;border:1px solid #dde3ec;border-radius:5px;padding:6px 8px;font-size:9px}
.stat-box header{display:flex;justify-content:space-between;font-weight:bold;font-size:10px;margin-bottom:3px}
.stat-box header i{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:4px;vertical-align:middle;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.stat-box .good{color:#168256}.stat-box .bad{color:#b42318}
.meter{height:5px;background:#e9edf2;border-radius:9px;overflow:hidden;margin:4px 0}
.meter span{display:block;height:100%;border-radius:9px;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.meter .mg{background:#16a34a}.meter .mb{background:#dc2626}
.stat-detail{color:#667085;font-size:8px}
.final-box{background:#17365d;color:#fff;border-color:#17365d;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.final-box .final-time{font-size:18px;font-weight:bold;margin:2px 0}

/* 週間 */
.week-table{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:8px}
.week-table th,.week-table td{border:1px solid #bcc5d3;padding:5px 6px;vertical-align:top;font-size:9px}
.week-table th{background:#eef3f8;font-weight:bold}
.week-table th:first-child{width:90px}
.mini-row{position:relative;height:16px;background:repeating-linear-gradient(90deg,#f4f7fb 0,#f4f7fb calc(25% - 1px),#dce4ee calc(25% - 1px),#dce4ee 25%);border:1px solid #d3dce8;border-radius:2px;margin:2px 0;overflow:hidden}
.mini-bar{position:absolute;top:1px;height:12px;border-radius:2px;color:#fff;font-size:6px;font-weight:bold;padding:0 2px;white-space:nowrap;overflow:hidden;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.mini-detail{font-size:7px;color:#526174;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.shift-morning{background:#edf5ff;border-left:4px solid #3b82f6;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.shift-day{background:#fff8e8;border-left:4px solid #f59e0b;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.shift-night{background:#f4efff;border-left:4px solid #8b5cf6;print-color-adjust:exact;-webkit-print-color-adjust:exact}
.footer{margin-top:12px;font-size:8px;color:#8896a8;text-align:right}
</style></head><body>${body}<div class="footer">印刷日時: ${new Date().toLocaleString('ja-JP')}</div></body></html>`)
  w.document.close()
  setTimeout(() => w.print(), 300)
}

function buildChartPrintBody() {
  const sm = tm(rangeStart.value)
  let em = tm(rangeEnd.value)
  if (em <= sm) em += 1440
  const total = em - sm
  const ticks = []
  for (let t = sm; t <= em; t += step.value) ticks.push(t)

  let h = `<h1>${selectedDate.value.replaceAll('-', '/')} シフト　${esc(currentLineName.value)}</h1>`
  h += `<div class="subtitle">開始 ${rangeStart.value}～終了 ${rangeEnd.value}　単位 ${step.value}分</div>`

  // 凡例
  h += '<div class="legend">'
  for (const p of currentLineProcesses.value) {
    h += `<span><i style="background:${p.color}"></i>${esc(p.process_name)}</span>`
  }
  h += '<span><i style="background:#ffd21f"></i>自動休憩</span></div>'

  // チャート
  h += '<div class="chart-grid">'
  h += '<div class="nh">作業者</div><div class="axis">'
  for (const t of ticks) {
    const pct = (t - sm) / total * 100
    const showLabel = (t - sm) % Math.max(step.value, 60) === 0
    if (showLabel) {
      h += `<span style="left:${pct}%">${Math.floor((t % 1440) / 60)}:${String(t % 60).padStart(2, '0')}</span>`
    }
  }
  h += '</div>'

  const active = assignments.value.filter(a => a.shift_line === currentLineId.value && a.date === selectedDate.value)

  for (const w of currentWorkers.value) {
    const day = workerDay(w.id, selectedDate.value, sm)
    const actualStart = day ? clockLabel(day.start) : w.work_start
    const actualShift = day ? shiftFromStart(day.start) : { name: w.shift_type, css: w.shift_type === '夜' ? 'night' : w.shift_type === '昼' ? 'day' : 'morning' }
    const dayJobs = assignments.value.filter(a => a.worker === w.id && a.date === selectedDate.value)
    const totalWork = dayJobs.reduce((sum, a) => sum + netDuration(a), 0)
    const breaks = autoBreaks(w.id, selectedDate.value, sm).filter(b => b.end > sm && b.start < em)

    h += `<div class="row"><div class="worker-cell shift-${actualShift.css}"><b>${esc(w.name)}</b><small>${actualShift.name}勤 · ${actualStart}出勤</small><small>実働${fmtHours(totalWork)}</small></div><div class="track">`
    for (const t of ticks) {
      h += `<i class="gridline" style="left:${(t - sm) / total * 100}%"></i>`
    }

    for (const a of active.filter(x => x.worker === w.id)) {
      const p = resolveLP(a)
      if (!p) continue
      const s = absMinute(a.start_time, sm)
      const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
      const color = p.color || '#64748b'
      h += `<div class="bar" style="left:${(s - sm) / total * 100}%;width:${(e - s) / total * 100}%;background:${color}">${esc(p.process_name)} ${a.units || 0}台<span class="detail">${a.start_time}–${clockLabel(e)} 実働${fmtHours(netDuration(a))}</span></div>`
    }

    for (const b of breaks) {
      const bs = Math.max(sm, b.start), be = Math.min(em, b.end)
      const bw = (be - bs) / total * 100
      if (bw > 3) {
        h += `<div class="break-bar" style="left:${(bs - sm) / total * 100}%;width:${bw}%"><b>${b.label}</b><span>${clockLabel(b.start)}～${clockLabel(b.end)}</span></div>`
      } else {
        h += `<div class="break-bar" style="left:${(bs - sm) / total * 100}%;width:${bw}%" title="${b.label}"></div>`
      }
    }
    h += '</div></div>'
  }
  h += '</div>'

  // 統計
  let finalEnd = 0
  for (const a of active) {
    const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
    finalEnd = Math.max(finalEnd, e)
  }
  const finalText = finalEnd ? (finalEnd >= 1440 ? '翌日 ' : '') + clockLabel(finalEnd) : '未設定'

  h += '<div class="stats-row">'
  h += `<div class="stat-box final-box"><div style="font-size:8px;opacity:.8">最終終了時刻</div><div class="final-time">${finalText}</div><div style="font-size:7px;opacity:.8">${active.length}件の配置</div></div>`

  for (const p of currentLineProcesses.value) {
    const placed = active.filter(a => {
      if (a.line_process) return a.line_process === p.id
      return a.process && a.process === p.process
    }).reduce((s, a) => s + netDuration(a), 0)
    const loadData = p.process ? processLoads.value[String(p.process)] : null
    const req = loadData ? +loadData.load_hours : 0
    const d = placed - req
    const achieved = req <= 0 ? true : d >= -0.01
    const rate = req > 0 ? Math.round(placed / req * 100) : (placed > 0 ? 100 : 0)
    const reqLabel = req > 0 ? fmtHours(req) : '負荷なし'
    const statusText = req <= 0 ? '負荷なし' : achieved ? (Math.abs(d) < 0.01 ? '達成' : fmtHours(d) + '余裕') : fmtHours(-d) + '不足'
    h += `<div class="stat-box"><header><span><i style="background:${p.color}"></i>${esc(p.process_name)}</span><b class="${achieved ? 'good' : 'bad'}">${statusText}</b></header><div class="meter"><span class="${achieved ? 'mg' : 'mb'}" style="width:${Math.min(100, rate)}%"></span></div><div class="stat-detail">達成度 ${rate}%　必要 ${reqLabel}／配置 ${fmtHours(placed)}</div></div>`
  }
  h += '</div>'

  return h
}

function buildWeekPrintBody() {
  const sm = tm(rangeStart.value)
  let em = tm(rangeEnd.value)
  if (em <= sm) em += 1440
  const total = em - sm
  const dates = weekDates.value.slice(0, 5)

  let h = `<h1>週間シフト　${esc(currentLineName.value)}</h1>`
  h += `<div class="subtitle">${dates[0]?.replaceAll('-','/')} ～ ${dates[4]?.replaceAll('-','/')}（月～金）</div>`

  // 凡例
  h += '<div class="legend">'
  for (const p of currentLineProcesses.value) {
    h += `<span><i style="background:${p.color}"></i>${esc(p.process_name)}</span>`
  }
  h += '</div>'

  h += '<table class="week-table"><thead><tr><th>作業者</th>'
  for (let i = 0; i < dates.length; i++) {
    h += `<th>${dayNames[i]}曜日<br>${dates[i].slice(5).replace('-', '/')}</th>`
  }
  h += '</tr></thead><tbody>'

  for (const w of currentWorkers.value) {
    h += `<tr><th>${esc(w.name)}<br><small style="font-weight:normal;color:#667085">${w.shift_type}勤</small></th>`
    for (const d of dates) {
      const jobs = weekAssignments.value.filter(a => a.shift_line === currentLineId.value && a.date === d && a.worker === w.id).sort((a, b) => absMinute(a.start_time, sm) - absMinute(b.start_time, sm))
      if (!jobs.length) { h += '<td style="color:#bcc5d3;text-align:center">－</td>'; continue }
      const bars = jobs.map(a => {
        const p = resolveLP(a) || { process_name: '不明', color: '#64748b' }
        const s = absMinute(a.start_time, sm)
        const e = endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id)
        const cs = Math.max(sm, s), ce = Math.min(em, e)
        if (ce <= cs) return ''
        return `<div class="mini-bar" style="background:${p.color};left:${(cs - sm) / total * 100}%;width:${Math.max(1, (ce - cs) / total * 100)}%">${esc(p.process_name)}</div>`
      }).join('')
      const details = jobs.map(a => {
        const p = resolveLP(a) || { process_name: '不明' }
        return `<div class="mini-detail">${a.start_time}～${clockLabel(endFromWorkHoursCalc(a.start_time, +a.work_hours, a.worker, a.date, sm, a.id))} ${esc(p.process_name)} ${a.units || 0}台</div>`
      }).join('')
      h += `<td><div class="mini-row">${bars}</div>${details}</td>`
    }
    h += '</tr>'
  }
  h += '</tbody></table>'

  return h
}

// --- チャートクリックイベント ---
function onChartClick(e) {
  const deleteBtn = e.target.closest('[data-delete]')
  if (deleteBtn) {
    e.stopPropagation()
    deleteAssignmentById(+deleteBtn.dataset.delete)
    return
  }
  const bar = e.target.closest('[data-id]')
  if (bar) {
    editAssignment(+bar.dataset.id)
  }
}

// --- 初期化 ---
onMounted(async () => {
  const today = new Date()
  const monday = new Date(today)
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7))
  weekStartDate.value = isoDate(monday)

  await Promise.all([loadLines(), loadMasterProcesses(), loadUsers()])
  await loadAssignments()
  await loadWeekData()

  if (currentWorkers.value.length) {
    entryWorkerId.value = currentWorkers.value[0].id
  }
  if (currentLineProcesses.value.length) {
    entryLineProcessId.value = currentLineProcesses.value[0].id
    entryProcessId.value = currentLineProcesses.value[0].process
  }
  updateEndPreview()

  document.addEventListener('click', onChartClick)
})

watch(activeTab, (tab) => {
  if (tab === 'week') loadWeekData()
})

watch([currentLineId, selectedDate], () => {
  loadProcessLoads()
}, { immediate: true })
</script>

<style scoped>
:root{--ink:#17243a;--muted:#667085;--line:#dfe5ec;--navy:#17365d;--bg:#f3f6f9}
*{box-sizing:border-box}
.shift-management{max-width:1540px;margin:auto;padding:10px 20px 40px}
button,input,select{font:inherit}
button{cursor:pointer}
.top{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.top h1{margin:0;font-size:18px;white-space:nowrap}
.tabs{display:flex;gap:0;border-bottom:none}
.tabs button{border:0;background:none;padding:6px 10px;color:#64748b;font-size:13px;font-weight:bold;border-bottom:2px solid transparent}
.tabs button.on{color:#17365d;border-bottom-color:#17365d}
.top-actions{margin-left:auto;display:flex;gap:6px}
.btn{border:1px solid #17365d;border-radius:5px;padding:5px 12px;font-size:12px;font-weight:bold;background:white;color:#17365d}
.btn.primary{background:#17365d;color:white}
.card{background:white;border:1px solid #dfe5ec;border-radius:8px;box-shadow:0 1px 4px #1c34520a}
.prepare-form{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.prepare-form label{display:inline-flex;align-items:center;gap:5px;margin:0;flex:0 0 auto}
.field-label{white-space:nowrap;font-size:11px;font-weight:bold;color:#667085}
.prepare-form select,.prepare-form input{padding:5px 7px;border:1px solid #cbd5e1;border-radius:4px;font-size:13px}
.toolbar,.entry{padding:8px 12px;margin-bottom:6px}
.entry-title{font-size:12px;color:#17365d}
input,select{border:1px solid #cbd5e1;border-radius:5px;padding:5px 7px;font-size:13px;background:white}
.comment{min-width:120px;flex:1}
.legend{display:flex;gap:10px;align-items:center;font-size:12px;font-weight:bold;flex-wrap:wrap}
.head{padding:15px 18px;border-bottom:1px solid #dfe5ec;display:flex;justify-content:space-between;gap:15px}
.head h2{margin:0 0 3px;font-size:18px}
.head p{margin:0;color:#667085;font-size:12px}
.legend{font-size:12px;font-weight:bold;flex-wrap:wrap}
.legend i,.stat i{width:9px;height:9px;border-radius:2px;display:inline-block;margin-right:5px}
.scroll{overflow-x:auto}
:deep(.chart){display:grid;grid-template-columns:140px 1fr;min-width:900px}
:deep(.nh),:deep(.axis){height:49px;background:#f7f9fb}
:deep(.nh){padding:16px;border-right:1px solid #dfe5ec;font-size:12px;font-weight:bold}
:deep(.axis),:deep(.track){position:relative}
:deep(.axis span){position:absolute;top:16px;font-size:10px;color:#627083;font-weight:bold}
:deep(.row){display:contents}
:deep(.worker){height:94px;border-top:1px solid #dfe5ec;border-right:1px solid #dfe5ec;padding:12px 16px}
:deep(.worker b),:deep(.worker small){display:block}
:deep(.worker small){color:#7a8798;margin-top:3px}
:deep(.track){height:94px;border-top:1px solid #dfe5ec}
:deep(.gridline){position:absolute;height:100%;width:1px;background:#edf0f4}
:deep(.bar){position:absolute;top:7px;height:48px;border:0;border-radius:6px;color:white;text-align:left;padding:6px 9px;overflow:hidden;box-shadow:0 2px 4px #1d29394d;cursor:pointer}
:deep(.bar b),:deep(.bar span){display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
:deep(.bar b){font-size:12px}
:deep(.bar span){font-size:9px;margin-top:2px}
:deep(.bar em){font-style:normal;background:#ffffff35;padding:1px 4px;border-radius:4px}
:deep(.bar-delete){position:absolute;right:4px;top:4px;width:20px;height:20px;padding:0;border:1px solid #fff8;border-radius:50%;background:#8b1d25;color:#fff;text-align:center;font-weight:bold;line-height:17px;z-index:7}
:deep(.break-bar){position:absolute;top:5px;height:52px;z-index:5;pointer-events:none;background:#ffd52b;border:2px solid #8d6800;color:#332700;border-radius:4px;overflow:visible;box-shadow:0 1px 3px #0004;text-align:center}
:deep(.break-bar.short){min-width:5px}
:deep(.break-bar.short b),:deep(.break-bar.short span){display:none}
:deep(.break-bar.meal){background:repeating-linear-gradient(135deg,#ffe67a,#ffe67a 8px,#ffc928 8px,#ffc928 16px);padding:5px 3px}
:deep(.break-bar.meal b),:deep(.break-bar.meal span){display:block;white-space:nowrap;font-size:9px;line-height:1.25}
:deep(.break-summary){position:absolute;left:0;right:0;bottom:5px;height:27px;display:flex;align-items:center;gap:12px;padding:4px 8px;background:#fff9d8;border-top:1px solid #e2c75d;color:#624b00;font-size:10px;font-weight:bold;white-space:nowrap;overflow:hidden}
:deep(.break-summary strong){background:#ffd52b;color:#493700;border-radius:4px;padding:2px 6px}
:deep(.break-summary .meal-text){background:#ffed9b;padding:2px 5px;border-radius:4px}
.chart-workspace{display:grid;grid-template-columns:minmax(0,1fr) 290px;gap:12px;align-items:start}
.chart-card{min-width:0}
.side-stats{display:grid;grid-template-columns:1fr;gap:9px}
:deep(.stat){padding:12px}
:deep(.stat header){display:flex;justify-content:space-between;font-size:13px;font-weight:bold}
:deep(.stat .bad){color:#b42318}
:deep(.stat .good){color:#168256}
:deep(.meter){height:7px;background:#e9edf2;border-radius:9px;margin:9px 0 7px;overflow:hidden}
:deep(.meter span){height:100%;display:block}
:deep(.meter span.achievement-bad){background:#dc2626!important}
:deep(.meter span.achievement-good){background:#16a34a!important}
:deep(.stat p){margin:0;color:#667085;font-size:11px}
:deep(.stat p span){float:right}
:deep(.final-summary){padding:14px;background:linear-gradient(135deg,#17365d,#285ea8);color:#fff;border-color:#17365d}
:deep(.final-summary small){display:block;font-size:10px;opacity:.8;font-weight:bold}
:deep(.final-summary strong){display:block;margin-top:4px;font-size:25px;letter-spacing:.03em}
:deep(.final-summary span){display:block;margin-top:2px;font-size:10px;opacity:.85}
.end-preview{padding:5px 8px;background:#eef6ff;border:1px solid #b8d3f2;border-radius:4px;color:#174d83;font-size:11px;font-weight:bold;white-space:nowrap}
.entry.editing{border:2px solid #f59e0b;background:#fffbf0}
:deep(.worker-total){color:#14734d!important;font-weight:bold}
:deep(.worker.shift-morning){background:#edf5ff;border-left:5px solid #3b82f6}
:deep(.worker.shift-day){background:#fff8e8;border-left:5px solid #f59e0b}
:deep(.worker.shift-night){background:#f4efff;border-left:5px solid #8b5cf6}
:deep(.worker .shift-info){font-weight:bold}
:deep(.worker.shift-morning .shift-info){color:#2563a9}
:deep(.worker.shift-day .shift-info){color:#a15c00}
:deep(.worker.shift-night .shift-info){color:#6d42b5}
.btn.reset{border-color:#c8342f;color:#b42318;background:#fff5f5;font-size:11px;padding:4px 8px}
.line-badge{display:inline-block;background:#e9f0fb;color:#17365d;border-radius:5px;padding:3px 8px;margin-left:7px;font-size:12px}

/* 週間 */
.week-toolbar{padding:12px 15px;margin-bottom:12px;display:flex;gap:12px;align-items:end}
.week-toolbar label{display:flex;flex-direction:column;gap:4px;color:#667085;font-size:11px;font-weight:bold}
.week-copy{padding:18px;margin-bottom:12px}
.week-copy h2{margin:0 0 5px}
.week-copy p{margin:0 0 16px;color:#667085;font-size:12px}
.copy-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.targets{display:flex;gap:6px;flex-wrap:wrap}
.targets label{padding:8px 10px;background:#f4f7fb;border:1px solid #d5dde8;border-radius:6px}
.copy-extra{margin-top:14px;padding-top:14px;border-top:1px solid #dde5ef}
.week-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:10px}
.day-card{padding:14px;min-height:145px}
.day-card.today{border-color:#285ea8}
.day-card h3{margin:0 0 4px;font-size:15px}
.day-card .date{color:#667085;font-size:11px}
.day-card .summary{margin:18px 0;color:#334155;font-size:12px;line-height:1.7}
.day-card .btn{width:100%;padding:7px}

/* 週間印刷 */
:deep(.week-print){margin-top:14px;padding:16px;overflow-x:auto}
:deep(.week-print h2){margin:0 0 3px}
:deep(.week-print .sub){color:#667085;font-size:11px;margin-bottom:12px}
:deep(.week-table){width:100%;border-collapse:collapse;table-layout:fixed}
:deep(.week-table th),:deep(.week-table td){border:1px solid #cfd8e5;padding:7px;vertical-align:top;font-size:10px}
:deep(.week-table th){background:#eef3f8}
:deep(.week-table th:first-child){width:105px}
:deep(.week-axis){display:block;color:#607086;font-size:7px;font-weight:normal;margin-top:2px}
:deep(.week-mini-row){position:relative;height:18px;margin:3px 0;background:repeating-linear-gradient(90deg,#f4f7fb 0,#f4f7fb calc(25% - 1px),#dce4ee calc(25% - 1px),#dce4ee 25%);border:1px solid #d3dce8;border-radius:3px;overflow:hidden}
:deep(.week-mini-bar){position:absolute;top:1px;height:14px;border-radius:2px;color:#fff;padding:1px 3px;font-size:7px;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
:deep(.week-detail){font-size:7px;color:#526174;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* 基本設定 */
.master{display:grid;grid-template-columns:1fr 1.2fr;gap:14px}
.panel{padding:18px}
.panelhead{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #dfe5ec;padding-bottom:12px}
.panelhead h2{margin:0;font-size:18px}
.mrow{display:grid;grid-template-columns:1fr 85px 55px;gap:7px;padding:8px 0;border-bottom:1px solid #eef1f5}
.mrow.proc{grid-template-columns:36px 1fr 55px;align-items:center}
.color-pick{width:32px;height:32px;padding:2px;border:1px solid #cbd5e1;border-radius:6px;cursor:pointer;background:none}
.color-dot{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:middle}
.panelhead-actions{display:flex;gap:6px}
.activity-btn{border-color:#6366f1;color:#4f46e5;background:#f5f3ff}
.activity-name-row{display:flex;align-items:center;gap:4px;flex:1}
.activity-name-input{border:1px dashed #a5b4fc;border-radius:4px;padding:4px 7px;font-size:13px;background:#fafafe;flex:1;min-width:80px}
.activity-tag{background:#e0e7ff;color:#4338ca;border-radius:4px;padding:1px 6px;font-size:9px;font-weight:bold;white-space:nowrap}
.del{border:0;border-radius:6px;background:#fff1f1;color:#b42318;font-weight:bold;font-size:11px;padding:6px 10px}
.mrow.line{grid-template-columns:1fr 75px 70px;border:1px solid transparent;border-radius:7px;padding:7px}
.mrow.line.active{background:#eaf2ff;border-color:#285ea8}
.switch{border:0;border-radius:6px;background:#e9f0fb;color:#17365d;font-weight:bold;padding:6px 10px}
.mrow.line.active .switch{background:#17365d;color:white}
.line-panel{grid-column:1/-1}
.mrow.worker-row{grid-template-columns:minmax(120px,1fr) 65px 108px 108px 76px 55px;min-width:650px}
.order-buttons{display:grid;grid-template-columns:1fr 1fr;gap:4px}
.order-buttons button{border:1px solid #b8c6d8;background:#f3f7fc;color:#17365d;border-radius:5px;font-weight:bold}
.order-buttons button:disabled{opacity:.3;cursor:default}
.worktime{display:flex;align-items:center;gap:4px;font-size:9px;color:#667085}
.worktime input{width:82px;padding:7px 4px}
.worker-name-cell{display:flex;flex-direction:column;gap:2px;padding:4px 0}
.worker-name-cell small.user-tag{color:#667085;font-size:10px}

/* 工程選択モーダル */
.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,.4);display:flex;align-items:center;justify-content:center;z-index:1000}
.modal{padding:24px;max-width:500px;width:90%;max-height:70vh;overflow-y:auto}
.modal h3{margin:0 0 12px}
.process-list{max-height:300px;overflow-y:auto}
.process-item{padding:10px;border-bottom:1px solid #eef1f5;cursor:pointer}
.process-item:hover{background:#eaf2ff}

/* 印刷 */
@media print{
  .actions,.tabs,.toolbar,.entry,.stats,.week-toolbar,.week-copy,.week-grid{display:none!important}
  .shift-management{padding:0!important}
  .card{box-shadow:none!important}
}
@media(max-width:1200px){.chart-workspace{grid-template-columns:1fr}}
@media(max-width:1000px){.week-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){.master{grid-template-columns:1fr}}
</style>
