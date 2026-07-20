<template>
  <div class="settings-container">
    <h2 class="page-title">受注お久しぶり製品通知設定</h2>
    <div v-if="!canView" class="card no-permission">この画面を開く権限がありません。</div>
    <div v-else class="card">
      <div class="tab-bar">
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'settings' }]"
          @click="activeTab = 'settings'"
        >
          設定
        </button>
        <button
          type="button"
          :class="['tab-btn', { active: activeTab === 'logs' }]"
          @click="activeTab = 'logs'"
        >
          履歴
        </button>
      </div>

      <div v-if="activeTab === 'settings'">
        <div class="field">
          <label>お久しぶり判定日数</label>
          <div class="input-row">
            <input v-model.number="days" type="number" min="1" :disabled="loading || !canEdit" />
            <span class="suffix">日</span>
          </div>
          <p class="helper">受注取込後、各明細の納期から指定日数さかのぼって同一品番の受注がなければ通知対象にします。</p>
        </div>

        <div class="field">
          <label>送信宛先</label>
          <UserChipSelect
            :userList="userList"
            v-model="recipientUserIds"
          />
          <p class="helper">社員を検索して送信先に追加します。</p>
          <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>
        </div>

        <div class="actions">
          <button class="btn primary" @click="saveSetting" :disabled="loading || saving || !canEdit">保存</button>
        </div>
      </div>

      <div v-else class="log-section">
        <div class="section-title">通知履歴</div>
        <p class="helper">直近100件の送信済み履歴です。</p>
        <div class="log-filters">
          <div class="filter-item customer-filter">
            <label>顧客</label>
            <input v-model.trim="logCustomerFilter" type="text" placeholder="コード/名称で絞り込み" />
          </div>
          <div class="filter-item">
            <label>納期From</label>
            <input v-model="logDueDateFrom" type="date" />
          </div>
          <div class="filter-item">
            <label>納期To</label>
            <input v-model="logDueDateTo" type="date" />
          </div>
        </div>
        <div class="log-table-wrap">
          <table class="log-table">
            <thead>
              <tr>
                <th>通知日時</th>
                <th>得意先</th>
                <th>品番</th>
                <th>納期</th>
                <th class="num">数量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!filteredNoticeLogs.length">
                <td colspan="5" class="empty">履歴はありません。</td>
              </tr>
              <tr v-for="row in filteredNoticeLogs" :key="row.id">
                <td>{{ row.notified_at || '-' }}</td>
                <td>{{ formatCustomer(row) }}</td>
                <td>{{ row.product_code || '-' }}</td>
                <td>{{ row.due_date || '-' }}</td>
                <td class="num">{{ formatQuantity(row.quantity) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { formatISODate, getBusinessDate } from '@/utils/dateUtil'
import UserChipSelect from '@/views/purchase/UserChipSelect.vue'

const today = formatISODate(getBusinessDate())
const days = ref(90)
const recipientUserIds = ref([])
const userList = ref([])
const noticeLogs = ref([])
const activeTab = ref('settings')
const logCustomerFilter = ref('')
const logDueDateFrom = ref(today)
const logDueDateTo = ref('')
const loading = ref(false)
const saving = ref(false)

const canAccessOrders = (level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  if (hasPermission(user, 'orders.first_article', level)) return true
  return hasPermission(user, 'orders', level)
}

const canView = computed(() => canAccessOrders('view'))
const canEdit = computed(() => canAccessOrders('edit'))
const filteredNoticeLogs = computed(() => {
  const keyword = String(logCustomerFilter.value || '').trim().toLowerCase()
  const from = logDueDateFrom.value || ''
  const to = logDueDateTo.value || ''

  return noticeLogs.value
    .filter((row) => {
      const customerCode = String(row?.customer_code || '').toLowerCase()
      const customerName = String(row?.customer_name || '').toLowerCase()
      const dueDate = String(row?.due_date || '')

      if (keyword && !customerCode.includes(keyword) && !customerName.includes(keyword)) {
        return false
      }
      if (from && dueDate && dueDate < from) {
        return false
      }
      if (to && dueDate && dueDate > to) {
        return false
      }
      if ((from || to) && !dueDate) {
        return false
      }
      return true
    })
    .slice()
    .sort((a, b) => {
      const dueA = String(a?.due_date || '')
      const dueB = String(b?.due_date || '')
      if (dueA !== dueB) return dueA.localeCompare(dueB)
      return String(b?.notified_at || '').localeCompare(String(a?.notified_at || ''))
    })
})

const loadSetting = async () => {
  if (!canView.value) return
  loading.value = true
  try {
    const res = await api.orders.getFirstArticleSetting()
    days.value = Number(res.data?.days ?? 90)
    recipientUserIds.value = Array.isArray(res.data?.recipient_user_ids) ? res.data.recipient_user_ids : []
    userList.value = Array.isArray(res.data?.all_users) ? res.data.all_users : []
    noticeLogs.value = Array.isArray(res.data?.notice_logs) ? res.data.notice_logs : []
  } catch (error) {
    console.error('受注お久しぶり製品通知設定の取得に失敗しました', error)
    alert('設定の取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

const saveSetting = async () => {
  if (!canEdit.value) return
  if (!Number.isInteger(days.value) || days.value < 1) {
    alert('判定日数は1以上の整数で入力してください。')
    return
  }

  saving.value = true
  try {
    const res = await api.orders.saveFirstArticleSetting({
      days: days.value,
      recipient_user_ids: recipientUserIds.value,
    })
    days.value = Number(res.data?.days ?? days.value)
    recipientUserIds.value = Array.isArray(res.data?.recipient_user_ids) ? res.data.recipient_user_ids : []
    alert('保存しました。')
  } catch (error) {
    console.error('受注お久しぶり製品通知設定の保存に失敗しました', error)
    alert(error?.response?.data?.detail || '保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const formatCustomer = (row) => {
  const code = row?.customer_code || ''
  const name = row?.customer_name || ''
  if (code && name) return `${code} ${name}`
  return code || name || '-'
}

const formatQuantity = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return value || '-'
  return String(Math.trunc(num))
}

onMounted(() => {
  loadSetting()
})
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: 'Segoe UI', 'Hiragino Kaku Gothic ProN', Meiryo, sans-serif;
}
.page-title {
  margin: 0 0 10px;
  font-size: 16px;
  font-weight: 700;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 12px;
  max-width: 720px;
}
.tab-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #d8deea;
}
.tab-btn {
  min-width: 84px;
  padding: 7px 12px;
  border: 1px solid #b9c6da;
  border-radius: 4px;
  background: #f7f9fc;
  color: #41526f;
  cursor: pointer;
}
.tab-btn.active {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.no-permission {
  color: #b91c1c;
  font-weight: 600;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}
.field label {
  font-size: 12px;
  color: #444;
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.input-row input {
  width: 120px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.suffix {
  font-size: 12px;
  color: #333;
}
.helper {
  margin: 0;
  font-size: 12px;
  color: #666;
}
.helper.warning {
  color: #b45309;
}
.actions {
  margin-top: 12px;
}
.log-section {
  margin-top: 2px;
}
.log-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 10px 0 12px;
  align-items: end;
}
.filter-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.filter-item label {
  font-size: 12px;
  color: #444;
}
.filter-item input {
  height: 32px;
  padding: 6px 8px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}
.customer-filter {
  min-width: 260px;
  flex: 1 1 260px;
}
.section-title {
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #24324b;
}
.log-table-wrap {
  overflow-x: auto;
  border: 1px solid #d8deea;
  border-radius: 4px;
}
.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.log-table th,
.log-table td {
  padding: 7px 8px;
  border-bottom: 1px solid #e3e8f1;
  text-align: left;
  white-space: nowrap;
}
.log-table th {
  background: #f2f5fb;
  color: #31415f;
}
.log-table .num {
  text-align: right;
}
.log-table .empty {
  text-align: center;
  color: #667085;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
</style>
