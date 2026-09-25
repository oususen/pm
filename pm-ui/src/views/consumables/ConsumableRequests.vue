<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">消耗品 発注準備 <DataSourceDialog title="消耗品 発注準備" :sources="dsSources" /></h1>
      <button class="btn-primary" :disabled="loading" @click="fetchAll">更新</button>
    </div>

    <!-- 注文書作成（発注準備・購入先別） -->
    <section v-if="canEdit" class="section">
      <div class="section-title">注文書作成（発注準備の依頼を購入先ごとにまとめます）</div>
      <p v-if="!routeStatus.route_configured" class="warn-text">
        承認設定に「消耗品注文書」が未登録のため、注文書を作成できません（設定 &gt; 承認設定で登録してください）。
      </p>
      <p v-else-if="!routeStatus.can_create" class="warn-text">注文書の作成権限がありません（承認設定の作成者を確認してください）。</p>
      <div v-if="!preparingGroups.length" class="empty">発注準備の依頼はありません。</div>
      <div v-for="g in preparingGroups" :key="g.key" class="supplier-group">
        <div class="group-head">
          <label><input type="checkbox" :checked="isGroupAllSelected(g)" @change="toggleGroup(g, $event.target.checked)" />
            購入先: <b>{{ g.supplier_name || '（購入先未設定）' }}</b></label>
          <span>| 件数: {{ g.rows.length }} | 選択金額: {{ formatPrice(selectedAmount(g)) }}円</span>
          <template v-if="g.supplier_id">
            <input v-model="notes[g.key]" class="note-input" placeholder="注文書の備考" />
            <button
              class="btn-success"
              :disabled="!routeStatus.can_create || !selectedIds(g).length || creating"
              @click="createOrder(g)"
            >注文書作成（{{ selectedIds(g).length }}件）</button>
          </template>
          <span v-else class="warn-text">消耗品マスタで購入先を設定してください</span>
        </div>
        <table class="data-table">
          <tbody>
            <tr v-for="r in g.rows" :key="r.id">
              <td class="chk"><input v-model="selected" type="checkbox" :value="r.id" :disabled="!g.supplier_id" /></td>
              <td class="mono">{{ r.consumable_code }}</td>
              <td>{{ r.consumable_name }}</td>
              <td class="num">
                <template v-if="preparingEditingId === r.id">
                  <input v-model.number="preparingEditQuantity" type="number" min="1" class="qty-input" /> {{ r.unit }}
                </template>
                <template v-else>{{ r.quantity }} {{ r.unit }}</template>
              </td>
              <td class="num">{{ formatPrice(r.total_amount) }}円</td>
              <td>
                <template v-if="preparingEditingId === r.id">
                  <select v-if="preparingDeadlineType === 'preset'" v-model="preparingEditDeadline">
                    <option value="最短">最短</option><option value="通常">通常</option><option value="余裕あり">余裕あり</option>
                  </select>
                  <input v-else v-model="preparingEditDeadline" type="date" />
                  <select v-model="preparingDeadlineType" @change="switchPreparingDeadlineType">
                    <option value="preset">区分</option><option value="date">日付</option>
                  </select>
                </template>
                <template v-else>納期: {{ r.deadline }}</template>
              </td>
              <td>依頼者: {{ r.requester_name || '-' }}</td>
              <td>{{ r.note }}</td>
              <td class="action-cell">
                <template v-if="preparingEditingId === r.id">
                  <button class="btn-sm btn-success" :disabled="savingPreparingEdit" @click="savePreparingEdit(r)">保存</button>
                  <button class="btn-sm btn-secondary" :disabled="savingPreparingEdit" @click="cancelPreparingEdit">取消</button>
                </template>
                <template v-else>
                  <button class="btn-sm btn-primary" @click="startPreparingEdit(r)">数量・納期変更</button>
                  <button class="btn-sm btn-secondary" @click="setStatus(r, 'requested')">依頼中に戻す</button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 依頼一覧 -->
    <section class="section">
      <div class="section-title">依頼一覧</div>
      <div class="filter-bar">
        <label>状態:
          <select v-model="statusFilter" @change="fetchRequests">
            <option value="requested">依頼中</option>
            <option value="requested,preparing">依頼中・発注準備</option>
            <option value="ordered">発注済</option>
            <option value="received">入庫済</option>
            <option value="rejected,cancelled">却下・キャンセル</option>
            <option value="">すべて</option>
          </select>
        </label>
        <label>検索: <input v-model="search" placeholder="コード/品名/依頼者/備考" @keyup.enter="fetchRequests" /></label>
        <span class="summary">{{ requests.length }}件</span>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>依頼日時</th><th>種別</th><th>コード</th><th>品名</th><th>数量</th><th>金額</th><th>納期</th>
            <th>依頼者</th><th>班</th><th>購入先</th><th>状態</th><th>備考</th><th v-if="canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in requests" :key="r.id">
            <td class="nowrap">{{ formatDateTime(r.requested_at) }}</td>
            <td>{{ r.request_type_label }}</td>
            <td class="mono">{{ r.consumable_code }}</td>
            <td>{{ r.consumable_name }}</td>
            <td class="num">
              <input v-if="editingId === r.id" v-model.number="editQuantity" type="number" min="1" class="qty-input" />
              <template v-else>{{ r.quantity }} {{ r.unit }}</template>
            </td>
            <td class="num">{{ formatPrice(r.total_amount) }}</td>
            <td>{{ r.deadline }}</td>
            <td>{{ r.requester_name }}</td>
            <td>{{ r.team_name }}</td>
            <td>{{ r.supplier_name }}</td>
            <td><span :class="['status-chip', r.status]">{{ r.status_label }}</span></td>
            <td>{{ r.note }}</td>
            <td v-if="canEdit" class="action-cell">
              <template v-if="editingId === r.id">
                <button class="btn-sm btn-success" @click="saveQuantity(r)">保存</button>
                <button class="btn-sm btn-secondary" @click="editingId = null">取消</button>
              </template>
              <template v-else>
                <button v-if="r.status === 'requested'" class="btn-sm btn-primary" @click="setStatus(r, 'preparing')">発注準備へ</button>
                <button v-if="['requested', 'preparing'].includes(r.status)" class="btn-sm btn-secondary" @click="startEdit(r)">数量変更</button>
                <button v-if="['requested', 'preparing'].includes(r.status)" class="btn-sm btn-warn" @click="setStatus(r, 'rejected')">却下</button>
                <button v-if="['rejected', 'cancelled'].includes(r.status)" class="btn-sm btn-secondary" @click="setStatus(r, 'requested')">依頼中に戻す</button>
                <button v-if="!['ordered', 'received'].includes(r.status)" class="btn-sm btn-delete" @click="removeRequest(r)">削除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import { errorMessage, formatDateTime, formatPrice, rowsOf } from './consumableUtils'

const dsSources = [
  { op: '読み書き', table: 't_consumable_request', desc: '注文依頼（状態: 依頼中→発注準備→発注済→入庫済）' },
  { op: '書き', table: 't_consumable_dispatch_order', desc: '注文書（購入先単位）' },
  { op: '書き', table: 'accounts_approvalrequest', desc: '注文書の承認申請' },
]

const router = useRouter()
const canEdit = computed(() => hasPermission(authState.user, 'consumables.dispatch', 'edit'))

const loading = ref(false)
const requests = ref([])
const preparing = ref([])
const statusFilter = ref('requested')
const search = ref('')
const routeStatus = ref({ route_configured: true, can_create: false })
const selected = ref([])
const notes = ref({})
const creating = ref(false)
const editingId = ref(null)
const editQuantity = ref(1)
const preparingEditingId = ref(null)
const preparingEditQuantity = ref(1)
const preparingEditDeadline = ref('最短')
const preparingDeadlineType = ref('preset')
const savingPreparingEdit = ref(false)

const preparingGroups = computed(() => {
  const map = new Map()
  preparing.value.forEach((r) => {
    const key = r.supplier_id ? String(r.supplier_id) : 'none'
    if (!map.has(key)) map.set(key, { key, supplier_id: r.supplier_id, supplier_name: r.supplier_name, rows: [] })
    map.get(key).rows.push(r)
  })
  return [...map.values()]
})

const selectedIds = (g) => g.rows.filter((r) => selected.value.includes(r.id)).map((r) => r.id)
const selectedAmount = (g) => g.rows.filter((r) => selected.value.includes(r.id)).reduce((sum, r) => sum + Number(r.total_amount), 0)
const isGroupAllSelected = (g) => g.rows.length > 0 && g.rows.every((r) => selected.value.includes(r.id))

function toggleGroup(g, checked) {
  if (!g.supplier_id) return
  const ids = g.rows.map((r) => r.id)
  selected.value = checked
    ? [...new Set([...selected.value, ...ids])]
    : selected.value.filter((id) => !ids.includes(id))
}

async function fetchRequests() {
  const params = { page_size: 0, search: search.value || undefined }
  if (statusFilter.value) params.statuses = statusFilter.value
  requests.value = rowsOf(await api.consumables.listRequests(params))
}

async function fetchPreparing() {
  preparing.value = rowsOf(await api.consumables.listRequests({ page_size: 0, status: 'preparing', undispatched: 1 }))
  const ids = preparing.value.map((r) => r.id)
  selected.value = selected.value.filter((id) => ids.includes(id))
}

async function fetchAll() {
  loading.value = true
  try {
    const tasks = [fetchRequests()]
    if (canEdit.value) {
      tasks.push(fetchPreparing())
      tasks.push(api.consumables.getDispatchRouteStatus().then((res) => { routeStatus.value = res.data }))
    }
    await Promise.all(tasks)
  } finally {
    loading.value = false
  }
}

async function setStatus(r, status) {
  const labels = { preparing: '発注準備', requested: '依頼中', rejected: '却下', cancelled: 'キャンセル' }
  if (status === 'rejected' && !confirm(`「${r.consumable_name}」の依頼を却下しますか？`)) return
  try {
    await api.consumables.setRequestStatus(r.id, status)
    fetchAll()
  } catch (err) {
    alert(`${labels[status]}にできませんでした: ${errorMessage(err)}`)
  }
}

function startEdit(r) {
  editingId.value = r.id
  editQuantity.value = r.quantity
}

async function saveQuantity(r) {
  try {
    await api.consumables.updateRequest(r.id, { quantity: editQuantity.value })
    editingId.value = null
    fetchAll()
  } catch (err) {
    alert(errorMessage(err))
  }
}

function startPreparingEdit(r) {
  preparingEditingId.value = r.id
  preparingEditQuantity.value = r.quantity
  preparingDeadlineType.value = /^\d{4}-\d{2}-\d{2}$/.test(r.deadline) ? 'date' : 'preset'
  preparingEditDeadline.value = r.deadline || '最短'
}

function switchPreparingDeadlineType() {
  preparingEditDeadline.value = preparingDeadlineType.value === 'preset' ? '最短' : ''
}

function cancelPreparingEdit() {
  preparingEditingId.value = null
}

async function savePreparingEdit(r) {
  if (!Number.isInteger(preparingEditQuantity.value) || preparingEditQuantity.value < 1) {
    alert('数量は1以上の整数を入力してください')
    return
  }
  const deadline = preparingDeadlineType.value === 'date'
    ? (preparingEditDeadline.value || '最短')
    : preparingEditDeadline.value
  savingPreparingEdit.value = true
  try {
    await api.consumables.updateRequest(r.id, { quantity: preparingEditQuantity.value, deadline })
    preparingEditingId.value = null
    await fetchAll()
  } catch (err) {
    alert(`依頼を更新できませんでした: ${errorMessage(err)}`)
  } finally {
    savingPreparingEdit.value = false
  }
}

async function removeRequest(r) {
  if (!confirm(`「${r.consumable_name}」の依頼を削除しますか？`)) return
  try {
    await api.consumables.deleteRequest(r.id)
    fetchAll()
  } catch (err) {
    alert(errorMessage(err))
  }
}

async function createOrder(g) {
  const ids = selectedIds(g)
  if (!confirm(`${g.supplier_name} の注文書を作成しますか？（${ids.length}件 / ${formatPrice(selectedAmount(g))}円）`)) return
  creating.value = true
  try {
    const order = (await api.consumables.createDispatchOrder({
      supplier: g.supplier_id,
      request_ids: ids,
      note: notes.value[g.key] || '',
    })).data
    notes.value[g.key] = ''
    router.push({ path: '/consumables/dispatch-orders', query: { id: order.id } })
  } catch (err) {
    alert(errorMessage(err))
    fetchAll()
  } finally {
    creating.value = false
  }
}

onMounted(fetchAll)
</script>

<style scoped>
.page-container { padding: 12px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.page-title { font-size: 1.2em; margin: 0; }
.section { margin-bottom: 14px; }
.section-title { font-weight: 700; margin: 4px 0; border-left: 4px solid #1565c0; padding-left: 6px; }
.filter-bar { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 6px; font-size: 0.85em; }
.summary { color: #555; }
.empty { color: #777; font-size: 0.85em; }
.warn-text { color: #e65100; font-size: 0.85em; margin: 2px 0; }
.supplier-group { border: 1px solid #ddd; border-radius: 6px; padding: 6px; margin-bottom: 6px; }
.group-head { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; font-size: 0.85em; margin-bottom: 4px; }
.note-input { flex: 1; min-width: 160px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85em; }
.data-table th, .data-table td { padding: 3px 6px; border: 1px solid #ddd; text-align: left; }
.data-table th { background: #f5f5f5; white-space: nowrap; }
.data-table .num { text-align: right; white-space: nowrap; }
.data-table .mono { font-family: monospace; }
.data-table .nowrap { white-space: nowrap; }
.chk { width: 24px; text-align: center; }
.qty-input { width: 70px; }
.action-cell { white-space: nowrap; }
.action-cell button { margin-right: 3px; }
.status-chip { padding: 0 6px; border-radius: 8px; background: #eee; white-space: nowrap; }
.status-chip.requested { background: #fff3e0; color: #e65100; }
.status-chip.preparing { background: #e3f2fd; color: #1565c0; }
.status-chip.ordered { background: #e8f5e9; color: #2e7d32; }
.status-chip.received { background: #eceff1; color: #455a64; }
.status-chip.rejected, .status-chip.cancelled { background: #ffebee; color: #c62828; }
.btn-primary { background: #1565c0; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-success { background: #2e7d32; color: #fff; border: none; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-success:disabled { opacity: 0.5; cursor: default; }
.btn-secondary { background: #f5f5f5; border: 1px solid #ccc; padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 0.85em; }
.btn-warn { background: #ef6c00; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-delete { background: #e53935; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
.btn-sm { padding: 2px 8px; font-size: 0.8em; }
</style>
