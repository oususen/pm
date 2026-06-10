<template>
  <div class="settings-container">
    <h2 class="page-title">締め日管理 <DataSourceDialog title="締め日管理" :sources="dsSources" /></h2>
    <div v-if="!canView" class="card no-permission">この画面を開く権限がありません。</div>
    <div v-else class="card">
      <p class="desc">締め日以前のデータは計算・取込・編集の対象外になります。</p>
      <table class="lock-table">
        <thead>
          <tr>
            <th>カテゴリ</th>
            <th>モード</th>
            <th>設定値</th>
            <th>状態</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in categories" :key="item.key">
            <td class="cat-label">{{ item.label }}</td>
            <td>
              <select v-model="item.mode" :disabled="!canEdit" class="mode-select">
                <option value="fixed">固定日付</option>
                <option value="days">N日前（自動）</option>
              </select>
            </td>
            <td>
              <input
                v-if="item.mode === 'fixed'"
                type="date"
                v-model="item.fixedDate"
                :disabled="!canEdit"
                class="date-input"
              />
              <div v-else class="days-input-row">
                <span>今日の</span>
                <input
                  type="number"
                  min="0"
                  v-model.number="item.daysAgo"
                  :disabled="!canEdit"
                  class="days-input"
                />
                <span>日前</span>
              </div>
            </td>
            <td>
              <span v-if="resolvedDate(item)" class="badge locked">{{ resolvedDate(item) }} まで締め</span>
              <span v-else class="badge unlocked">未設定</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!canEdit" class="helper warning">この設定を変更する権限がありません。</p>
      <div class="actions">
        <button class="btn primary" @click="saveAll" :disabled="saving || !canEdit">
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="btn" @click="clearAll" :disabled="saving || !canEdit">全解除</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 'system_setting', desc: '締め日設定（カテゴリ別ロック日付）' },
]

const saving = ref(false)

const categories = reactive([
  { key: 'lock_date.kubota_sakai_due', label: 'クボタ堺納期調整', mode: 'fixed', fixedDate: '', daysAgo: 0 },
  { key: 'lock_date.inventory', label: '在庫計算', mode: 'fixed', fixedDate: '', daysAgo: 0 },
  { key: 'lock_date.progress', label: '進度計算', mode: 'fixed', fixedDate: '', daysAgo: 0 },
])

const formatLocalDate = (d) => {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const resolvedDate = (item) => {
  if (item.mode === 'fixed') return item.fixedDate || null
  if (item.mode === 'days' && item.daysAgo > 0) {
    const d = new Date()
    d.setDate(d.getDate() - item.daysAgo)
    return formatLocalDate(d)
  }
  return null
}

const parseStoredValue = (raw) => {
  if (!raw) return { mode: 'fixed', fixedDate: '', daysAgo: 0 }
  if (raw.startsWith('days:')) {
    const n = parseInt(raw.substring(5), 10)
    return { mode: 'days', fixedDate: '', daysAgo: Number.isFinite(n) ? n : 0 }
  }
  return { mode: 'fixed', fixedDate: raw, daysAgo: 0 }
}

const toStoredValue = (item) => {
  if (item.mode === 'days' && item.daysAgo > 0) return `days:${item.daysAgo}`
  if (item.mode === 'fixed' && item.fixedDate) return item.fixedDate
  return ''
}

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canView = computed(() => canAccessByResource('settings.lock_date', 'view'))
const canEdit = computed(() => canAccessByResource('settings.lock_date', 'edit'))

const loadSettings = async () => {
  try {
    const res = await api.systemSettings.getAll()
    for (const cat of categories) {
      const entry = res.data[cat.key]
      const parsed = parseStoredValue(entry?.value || '')
      cat.mode = parsed.mode
      cat.fixedDate = parsed.fixedDate
      cat.daysAgo = parsed.daysAgo
    }
  } catch (e) {
    console.error('締め日設定の取得に失敗しました', e)
  }
}

const saveAll = async () => {
  saving.value = true
  try {
    const payload = {}
    for (const cat of categories) {
      payload[cat.key] = toStoredValue(cat)
    }
    await api.systemSettings.updateByKey(payload)
    alert('保存しました。')
  } catch (e) {
    console.error('締め日設定の保存に失敗しました', e)
    alert('保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const clearAll = () => {
  for (const cat of categories) {
    cat.mode = 'fixed'
    cat.fixedDate = ''
    cat.daysAgo = 0
  }
}

onMounted(() => {
  if (canView.value) loadSettings()
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
  max-width: 780px;
}
.no-permission {
  color: #b91c1c;
  font-weight: 600;
}
.desc {
  margin: 0 0 10px;
  font-size: 12px;
  color: #666;
}
.lock-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.lock-table th {
  text-align: left;
  padding: 6px 8px;
  background: #f3f5f8;
  border-bottom: 1px solid #d1d9e6;
  font-size: 11px;
  color: #555;
}
.lock-table td {
  padding: 8px;
  border-bottom: 1px solid #e8ecf1;
}
.cat-label {
  font-weight: 600;
  white-space: nowrap;
}
.mode-select {
  padding: 4px 6px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  font-size: 12px;
}
.date-input {
  padding: 4px 6px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  font-size: 13px;
}
.days-input-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}
.days-input {
  width: 60px;
  padding: 4px 6px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
  font-size: 13px;
  text-align: right;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}
.badge.locked {
  background: #fef3c7;
  color: #92400e;
}
.badge.unlocked {
  background: #e8ecf1;
  color: #888;
}
.helper.warning {
  margin: 8px 0 0;
  font-size: 12px;
  color: #b45309;
}
.actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
</style>

