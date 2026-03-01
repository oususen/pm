<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">発注承認者設定</h1>
      <div class="page-actions">
        <button class="btn-primary" @click="fetchAll">更新</button>
        <button class="btn-success" @click="save">保存</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>承認レベル</th>
            <th>レベル名</th>
            <th>承認可能ユーザー</th>
            <th>通知先ユーザー</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in configs" :key="row.approval_level">
            <td>{{ row.approval_level }}</td>
            <td><input v-model="row.level_name" /></td>
            <td class="picker-cell">
              <div class="user-picker">
                <input
                  v-model="row.approver_search"
                  class="picker-search-input"
                  placeholder="社員コード/氏名/ユーザー名で検索"
                  @keyup.enter.prevent="addFirstCandidate(row, 'approver')"
                />
                <div v-if="candidateList(row, 'approver').length" class="candidate-list">
                  <div
                    v-for="user in candidateList(row, 'approver')"
                    :key="user.id"
                    class="candidate-item"
                    @click="addUser(row, 'approver', user)"
                  >
                    <span class="candidate-code">{{ codeLabel(user) }}</span>
                    <span class="candidate-name">{{ nameLabel(user) }}</span>
                  </div>
                </div>
                <div v-if="row.approver_users.length" class="selected-list">
                  <span v-for="userId in row.approver_users" :key="`approver-${row.approval_level}-${userId}`" class="chip">
                    <span class="chip-code">{{ chipCode(userId) }}</span>
                    <span class="chip-name">{{ chipName(userId) }}</span>
                    <button type="button" class="chip-remove" @click="removeUser(row, 'approver', userId)">×</button>
                  </span>
                </div>
              </div>
            </td>
            <td class="picker-cell">
              <div class="user-picker">
                <input
                  v-model="row.notify_search"
                  class="picker-search-input"
                  placeholder="社員コード/氏名/ユーザー名で検索"
                  @keyup.enter.prevent="addFirstCandidate(row, 'notify')"
                />
                <div v-if="candidateList(row, 'notify').length" class="candidate-list">
                  <div
                    v-for="user in candidateList(row, 'notify')"
                    :key="user.id"
                    class="candidate-item"
                    @click="addUser(row, 'notify', user)"
                  >
                    <span class="candidate-code">{{ codeLabel(user) }}</span>
                    <span class="candidate-name">{{ nameLabel(user) }}</span>
                  </div>
                </div>
                <div v-if="row.notify_users.length" class="selected-list">
                  <span v-for="userId in row.notify_users" :key="`notify-${row.approval_level}-${userId}`" class="chip">
                    <span class="chip-code">{{ chipCode(userId) }}</span>
                    <span class="chip-name">{{ chipName(userId) }}</span>
                    <button type="button" class="chip-remove" @click="removeUser(row, 'notify', userId)">×</button>
                  </span>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="configs.length === 0" class="no-data">データがありません</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'

const configs = ref([])
const users = ref([])
const usersById = computed(() => {
  const map = new Map()
  for (const user of users.value) {
    map.set(Number(user.id), user)
  }
  return map
})

const normalizeUserIds = (list) => {
  if (!Array.isArray(list)) return []
  const ids = list
    .map((id) => Number(id))
    .filter((id) => Number.isFinite(id))
  return [...new Set(ids)]
}

const normalizeConfig = (row) => ({
  approval_level: row.approval_level,
  level_name: row.level_name || '',
  approver_users: normalizeUserIds(row.approver_users),
  notify_users: normalizeUserIds(row.notify_users),
  approver_search: '',
  notify_search: '',
})

const fetchUsers = async () => {
  const response = await api.accounts.getUsers({ page_size: 1000, is_active: true })
  users.value = response.data.results || response.data || []
}

const fetchConfigs = async () => {
  const response = await api.purchaseOrderApprovalConfig.get()
  configs.value = (response.data || []).map((row) => normalizeConfig(row))
}

const codeLabel = (user) => user?.profile?.employee_code || user?.username || user?.email || `ID:${user?.id}`

const nameLabel = (user) => {
  const name = `${user?.last_name || ''}${user?.first_name || ''}`.trim()
  return name || user?.username || user?.email || `ID:${user?.id}`
}

const candidateList = (row, type) => {
  const targetSearch = type === 'approver' ? row.approver_search : row.notify_search
  const selected = type === 'approver' ? row.approver_users : row.notify_users
  const keyword = String(targetSearch || '').trim().toLowerCase()
  if (!keyword) return []
  const selectedSet = new Set((selected || []).map((id) => Number(id)))
  return users.value
    .filter((user) => {
      const userId = Number(user.id)
      if (selectedSet.has(userId)) return false
      const code = codeLabel(user).toLowerCase()
      const name = nameLabel(user).toLowerCase()
      const username = String(user.username || '').toLowerCase()
      return code.includes(keyword) || name.includes(keyword) || username.includes(keyword)
    })
    .slice(0, 10)
}

const addUser = (row, type, user) => {
  const userId = Number(user.id)
  const targetKey = type === 'approver' ? 'approver_users' : 'notify_users'
  const searchKey = type === 'approver' ? 'approver_search' : 'notify_search'
  if (!row[targetKey].includes(userId)) {
    row[targetKey] = [...row[targetKey], userId]
  }
  row[searchKey] = ''
}

const addFirstCandidate = (row, type) => {
  const first = candidateList(row, type)[0]
  if (first) addUser(row, type, first)
}

const removeUser = (row, type, userId) => {
  const targetKey = type === 'approver' ? 'approver_users' : 'notify_users'
  row[targetKey] = row[targetKey].filter((id) => Number(id) !== Number(userId))
}

const chipCode = (userId) => {
  const user = usersById.value.get(Number(userId))
  return user ? codeLabel(user) : `ID:${userId}`
}

const chipName = (userId) => {
  const user = usersById.value.get(Number(userId))
  return user ? nameLabel(user) : ''
}

const fetchAll = async () => {
  await Promise.all([fetchUsers(), fetchConfigs()])
}

const save = async () => {
  const payload = {
    configs: configs.value.map((row) => ({
      approval_level: row.approval_level,
      level_name: row.level_name,
      approver_users: row.approver_users || [],
      notify_users: row.notify_users || [],
    })),
  }
  await api.purchaseOrderApprovalConfig.save(payload)
  await fetchConfigs()
  alert('保存しました')
}

onMounted(async () => {
  await fetchAll()
})
</script>

<style scoped>
.picker-cell {
  min-width: 340px;
}

.user-picker {
  min-width: 320px;
}

.picker-search-input {
  width: 100%;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #cfd6e1;
  border-radius: 3px;
}

.candidate-list {
  border: 1px solid #e5e9ef;
  border-radius: 4px;
  margin-top: 6px;
  max-height: 160px;
  overflow: auto;
  background: #fff;
}

.candidate-item {
  padding: 6px 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  cursor: pointer;
}

.candidate-item:hover {
  background: #f3f6fb;
}

.candidate-code {
  font-weight: 700;
  color: #1f2a44;
  min-width: 80px;
}

.candidate-name {
  color: #444;
  font-size: 12px;
}

.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.chip {
  background: #eef2f6;
  border: 1px solid #cfd6e1;
  border-radius: 14px;
  padding: 4px 8px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chip-code {
  font-weight: 700;
}

.chip-name {
  color: #4b5563;
}

.chip-remove {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  padding: 0 2px;
  color: #6b7280;
}
</style>
