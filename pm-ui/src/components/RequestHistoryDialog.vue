<template>
  <div v-if="requestHistoryOpen" class="rh-overlay" @click.self="close">
    <div class="rh-dialog" role="dialog" aria-label="リクエスト履歴">
      <header>
        <strong>リクエスト履歴</strong>
        <div class="hdr-actions">
          <button type="button" title="閉じる" @click="close">×</button>
          <button type="button" title="マニュアルを開く" aria-label="マニュアルを開く" @click="openManual(MANUAL_PATH)">?</button>
        </div>
      </header>
      <p class="note">全員のリクエストが表示されます。同じ内容を送る前に確認してください。</p>
      <form class="filters" @submit.prevent="load">
        <label>依頼者
          <select v-model="requesterId">
            <option value="">すべて</option>
            <option v-for="item in requesters" :key="item.id" :value="String(item.id)">{{ item.name }}</option>
          </select>
        </label>
        <label>状態
          <select v-model="status">
            <option value="">すべて</option>
            <option v-for="option in STATUS_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="grow">キーワード
          <input v-model="keyword" type="text" placeholder="件名・内容" />
        </label>
        <button type="submit" class="primary" :disabled="loading">検索</button>
        <button type="button" :disabled="loading" @click="reset">リセット</button>
      </form>
      <p v-if="errorMessage" class="msg error">{{ errorMessage }}</p>
      <div class="list">
        <table>
          <thead>
            <tr><th>送信日時</th><th>種類</th><th>件名</th><th>依頼者</th><th>状況</th></tr>
          </thead>
          <tbody>
            <template v-for="row in rows" :key="row.id">
              <tr class="row" :class="{ open: openId === row.id }" @click="toggle(row.id)">
                <td>{{ formatDateTime(row.created_at) }}</td>
                <td>{{ row.request_type_label }}</td>
                <td class="subject">{{ row.subject }}</td>
                <td>{{ row.requester_name || '-' }}</td>
                <td><span class="status" :class="row.status">{{ row.status_label }}</span></td>
              </tr>
              <tr v-if="openId === row.id" class="detail">
                <td colspan="5"><div class="body">{{ row.body }}</div></td>
              </tr>
            </template>
          </tbody>
        </table>
        <p v-if="!rows.length && !loading" class="empty">該当するリクエストはありません</p>
        <p v-if="rows.length >= LIMIT" class="empty">最新{{ LIMIT }}件まで表示しています。絞り込みで探してください。</p>
      </div>
      <footer>
        <button type="button" @click="close">閉じる</button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '@/api/client'
import { requestHistoryOpen, closeRequestHistory } from '@/composables/requestDialog'
import { openManual } from '@/composables/manualLink'

const MANUAL_PATH = '共通/リクエスト.md'

const LIMIT = 200
const STATUS_OPTIONS = [
  { value: 'PENDING', label: '未対応' },
  { value: 'IN_PROGRESS', label: '対応中' },
  { value: 'DONE', label: '完了' },
  { value: 'REJECTED', label: '却下' },
]

const rows = ref([])
const requesters = ref([])
const requesterId = ref('')
const status = ref('')
const keyword = ref('')
const loading = ref(false)
const errorMessage = ref('')
const openId = ref(null)

const formatDateTime = (value) => {
  if (!value) return '-'
  const dt = new Date(value)
  return Number.isNaN(dt.getTime()) ? value : dt.toLocaleString('ja-JP')
}

const load = async () => {
  loading.value = true
  errorMessage.value = ''
  openId.value = null
  try {
    const params = {}
    if (requesterId.value) params.requester = requesterId.value
    if (status.value) params.status = status.value
    if (keyword.value.trim()) params.q = keyword.value.trim()
    const { data } = await api.userRequests.history(params)
    rows.value = data?.results || []
    requesters.value = data?.requesters || []
  } catch (error) {
    rows.value = []
    errorMessage.value = error?.response?.data?.detail || 'リクエスト履歴の取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const reset = () => {
  requesterId.value = ''
  status.value = ''
  keyword.value = ''
  void load()
}

const toggle = (id) => {
  openId.value = openId.value === id ? null : id
}

const close = () => closeRequestHistory()

// 開くたびに最新の状態を取得する（絞り込みはリセットする）
watch(requestHistoryOpen, (open) => {
  if (!open) return
  requesterId.value = ''
  status.value = ''
  keyword.value = ''
  void load()
})
</script>

<style scoped>
.rh-overlay{position:fixed;inset:0;z-index:1200;background:rgba(0,0,0,.35);display:grid;place-items:center;padding:12px}
.rh-dialog{width:min(860px,100%);max-height:100%;display:flex;flex-direction:column;gap:6px;background:#fff;border-radius:8px;box-shadow:0 10px 30px rgba(0,0,0,.25);padding:10px 12px;font-size:13px}
header,footer{display:flex;align-items:center;gap:8px}
header{justify-content:space-between}
header button{border:0;background:none;font-size:18px;cursor:pointer}
.hdr-actions{display:flex;align-items:center;gap:4px}
.hdr-actions button+button{width:22px;height:22px;border:1px solid #c8ccd0;border-radius:50%;font-size:13px;line-height:1;padding:0}
.note{margin:0;color:#666;font-size:12px}
.filters{display:flex;flex-wrap:wrap;align-items:flex-end;gap:6px 10px}
.filters label{display:flex;flex-direction:column;gap:2px;font-weight:600;font-size:12px}
.filters label.grow{flex:1;min-width:140px}
.filters select,.filters input{padding:4px 6px;border:1px solid #c8ccd0;border-radius:4px;font:inherit;font-weight:400}
.filters button,footer button{padding:4px 12px;border:1px solid #c8ccd0;border-radius:4px;background:#f5f6f7;cursor:pointer}
.filters .primary{background:#087b6e;color:#fff;border-color:#087b6e}
.filters button:disabled{opacity:.5;cursor:default}
.list{flex:1;min-height:120px;overflow:auto;border:1px solid #e1e4e8;border-radius:4px}
table{width:100%;border-collapse:collapse}
th,td{padding:4px 8px;border-bottom:1px solid #eceff1;text-align:left;vertical-align:top}
th{position:sticky;top:0;background:#f0f3f6;font-size:12px;white-space:nowrap}
tr.row{cursor:pointer}
tr.row:hover,tr.row.open{background:#f5fbf9}
td.subject{word-break:break-word}
tr.detail td{background:#fafbfc}
.body{white-space:pre-wrap;word-break:break-word;max-height:200px;overflow:auto}
.status{display:inline-block;padding:0 8px;border-radius:10px;font-size:12px;white-space:nowrap;background:#eceff1}
.status.PENDING{background:#fdecea;color:#b03a2e}
.status.IN_PROGRESS{background:#fff3e0;color:#b9770e}
.status.DONE{background:#e6f4ea;color:#2e7d32}
.status.REJECTED{background:#eceff1;color:#555}
.empty{margin:0;padding:10px;text-align:center;color:#666}
.msg{margin:0;font-weight:600}
.msg.error{color:#c0392b}
footer{justify-content:flex-end}
</style>
