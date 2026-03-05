<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">組織管理</h1>
      <div class="page-actions">
        <button @click="loadAll" class="btn-primary" :disabled="loading || !canView">更新</button>
        <button @click="showCreate(null, 'division')" class="btn-success" :disabled="!canEdit">事業部を追加</button>
      </div>
    </div>

    <div v-if="errorMessage" class="error-msg">{{ errorMessage }}</div>

    <div v-if="!canView" class="page-content">
      <div class="no-data">この画面を開く権限がありません。</div>
    </div>
    <div v-else class="page-content">
      <div v-if="loading" class="no-data">読み込み中...</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>階層</th>
            <th>名前</th>
            <th>表示順</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="div in tree" :key="div.id">
            <!-- 事業部 -->
            <tr class="row-division">
              <td><span class="level-badge level-division">事業部</span></td>
              <td>{{ div.name }}</td>
              <td>{{ div.display_id }}</td>
              <td class="actions">
                <button class="btn-sm" @click="showEdit(div)" :disabled="!canEdit">編集</button>
                <button class="btn-sm btn-success" @click="showCreate(div.id, 'group')" :disabled="!canEdit">係を追加</button>
                <button class="btn-sm btn-danger" @click="confirmDelete(div)" :disabled="!canEdit">削除</button>
              </td>
            </tr>
            <!-- 係 -->
            <template v-for="grp in div.children" :key="grp.id">
              <tr class="row-group">
                <td><span class="level-badge level-group">係</span></td>
                <td class="indent-1">{{ grp.name }}</td>
                <td>{{ grp.display_id }}</td>
                <td class="actions">
                  <button class="btn-sm" @click="showEdit(grp)" :disabled="!canEdit">編集</button>
                  <button class="btn-sm btn-success" @click="showCreate(grp.id, 'team')" :disabled="!canEdit">班を追加</button>
                  <button class="btn-sm btn-danger" @click="confirmDelete(grp)" :disabled="!canEdit">削除</button>
                </td>
              </tr>
              <!-- 班 -->
              <template v-for="team in grp.children" :key="team.id">
                <tr class="row-team">
                  <td><span class="level-badge level-team">班</span></td>
                  <td class="indent-2">{{ team.name }}</td>
                  <td>{{ team.display_id }}</td>
                  <td class="actions">
                    <button class="btn-sm" @click="showEdit(team)" :disabled="!canEdit">編集</button>
                    <button class="btn-sm btn-success" @click="showCreate(team.id, 'unit')" :disabled="!canEdit">グループを追加</button>
                    <button class="btn-sm btn-danger" @click="confirmDelete(team)" :disabled="!canEdit">削除</button>
                  </td>
                </tr>
                <!-- グループ -->
                <tr v-for="unit in team.children" :key="unit.id" class="row-unit">
                  <td><span class="level-badge level-unit">グループ</span></td>
                  <td class="indent-3">{{ unit.name }}</td>
                  <td>{{ unit.display_id }}</td>
                  <td class="actions">
                    <button class="btn-sm" @click="showEdit(unit)" :disabled="!canEdit">編集</button>
                    <button class="btn-sm btn-danger" @click="confirmDelete(unit)" :disabled="!canEdit">削除</button>
                  </td>
                </tr>
              </template>
            </template>
          </template>
        </tbody>
      </table>
      <div v-if="!loading && tree.length === 0" class="no-data">データがありません</div>
    </div>

    <!-- 新規/編集ダイアログ -->
    <div v-if="showDialog" class="modal-overlay" @click.self="closeDialog">
      <div class="modal-content">
        <h2>{{ editTarget ? '編集' : levelLabels[dialogLevel] + ' 新規作成' }}</h2>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>名前 <span class="required">*</span></label>
            <input v-model="form.name" required autofocus :disabled="!canEdit" />
          </div>
          <div class="form-group">
            <label>表示順</label>
            <input v-model.number="form.display_id" type="number" :disabled="!canEdit" />
          </div>
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="saving || !canEdit">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeDialog">キャンセル</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 削除確認ダイアログ -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal-content">
        <h2>削除確認</h2>
        <p>「{{ deleteTarget.name }}」を削除しますか？<br>配下の組織も削除されます。</p>
        <div class="form-actions">
          <button class="btn-danger" @click="doDelete" :disabled="saving || !canEdit">削除</button>
          <button class="btn-secondary" @click="deleteTarget = null">キャンセル</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const tree = ref([])
const allDepts = ref([])

const showDialog = ref(false)
const editTarget = ref(null)
const dialogLevel = ref('division')
const dialogParentId = ref(null)
const deleteTarget = ref(null)

const form = ref({ name: '', display_id: 0 })

const levelLabels = { division: '事業部', group: '係', team: '班', unit: 'グループ' }

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canView = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.departments', 'view')
})

const canEdit = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return canAccessByResource('settings.departments', 'edit')
})

const buildTree = (depts) => {
  const map = {}
  depts.forEach(d => { map[d.id] = { ...d, children: [] } })
  const roots = []
  depts.forEach(d => {
    if (d.level === 'division') {
      roots.push(map[d.id])
    } else if (d.parent && map[d.parent]) {
      map[d.parent].children.push(map[d.id])
    }
  })
  const sortById = (arr) => {
    arr.sort((a, b) => (a.display_id - b.display_id) || (a.id - b.id))
    arr.forEach(n => sortById(n.children))
    return arr
  }
  return sortById(roots)
}

const loadAll = async () => {
  if (!canView.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await api.accounts.getDepartments({ page_size: 20000 })
    allDepts.value = Array.isArray(res.data) ? res.data : (res.data.results || [])
    tree.value = buildTree(allDepts.value)
  } catch {
    errorMessage.value = '読み込みに失敗しました。'
  } finally {
    loading.value = false
  }
}

const showCreate = (parentId, level) => {
  if (!canEdit.value) return
  editTarget.value = null
  dialogLevel.value = level
  dialogParentId.value = parentId
  form.value = { name: '', display_id: 0 }
  showDialog.value = true
}

const showEdit = (dept) => {
  if (!canEdit.value) return
  editTarget.value = dept
  dialogLevel.value = dept.level
  dialogParentId.value = dept.parent
  form.value = { name: dept.name, display_id: dept.display_id }
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
  editTarget.value = null
}

const save = async () => {
  if (!canEdit.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    if (editTarget.value) {
      await api.accounts.updateDepartment(editTarget.value.id, {
        name: form.value.name,
        display_id: form.value.display_id,
      })
    } else {
      await api.accounts.createDepartment({
        name: form.value.name,
        level: dialogLevel.value,
        parent: dialogParentId.value,
        display_id: form.value.display_id,
      })
    }
    closeDialog()
    await loadAll()
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const confirmDelete = (dept) => {
  if (!canEdit.value) return
  deleteTarget.value = dept
}

const doDelete = async () => {
  if (!canEdit.value) return
  if (!deleteTarget.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    await api.accounts.deleteDepartment(deleteTarget.value.id)
    deleteTarget.value = null
    await loadAll()
  } catch (e) {
    errorMessage.value = e?.response?.data?.detail || '削除に失敗しました。'
    deleteTarget.value = null
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>

<style scoped>
.page-container {
  padding: 16px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: bold;
}
.page-actions {
  display: flex;
  gap: 8px;
}
.error-msg {
  color: #c00;
  margin-bottom: 8px;
  font-size: 13px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th, .data-table td {
  border: 1px solid #ddd;
  padding: 6px 10px;
  text-align: left;
}
.data-table th {
  background: #f4f6fb;
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.indent-1 { padding-left: 24px !important; }
.indent-2 { padding-left: 48px !important; }
.indent-3 { padding-left: 72px !important; }

.level-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: bold;
}
.level-division { background: #dbeafe; color: #1d4ed8; }
.level-group    { background: #d1fae5; color: #065f46; }
.level-team     { background: #fef9c3; color: #92400e; }
.level-unit     { background: #ede9fe; color: #5b21b6; }

.row-division td { background: #f8faff; }
.row-group td    { background: #f8fff8; }
.row-team td     { background: #fffef0; }
.row-unit td     { background: #fdf8ff; }

.btn-primary   { background: #2563eb; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-success   { background: #16a34a; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-secondary { background: #6b7280; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn-sm        { padding: 3px 8px; border: none; border-radius: 3px; cursor: pointer; font-size: 12px; background: #e5e7eb; color: #111; }
.btn-sm.btn-success { background: #bbf7d0; color: #065f46; }
.btn-sm.btn-danger  { background: #fee2e2; color: #991b1b; }
.btn-danger    { background: #dc2626; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 13px; }

.no-data { color: #888; padding: 16px; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
  min-width: 320px;
  max-width: 480px;
  width: 100%;
}
.modal-content h2 {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 16px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 13px;
  margin-bottom: 4px;
  font-weight: 500;
}
.form-group input {
  width: 100%;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 13px;
  box-sizing: border-box;
}
.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 16px;
}
.required { color: #c00; }
</style>
