<template>
  <div class="config-page">
    <div class="toolbar">
      <h2>AI検索設定</h2>
      <span class="subtitle">AIチャットが検索できるDBテーブルを管理します</span>
      <button class="btn-add" @click="openForm(null)">＋ 追加</button>
    </div>

    <table class="config-table">
      <thead>
        <tr>
          <th style="width:40px">順</th>
          <th style="width:90px">ラベル</th>
          <th>モデル</th>
          <th>検索フィールド</th>
          <th>表示テンプレート</th>
          <th style="width:50px">有効</th>
          <th style="width:100px">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in configs" :key="row.id" :class="{ inactive: !row.is_active }">
          <td>{{ row.display_order }}</td>
          <td><strong>{{ row.label }}</strong></td>
          <td class="mono">{{ row.model_path }}</td>
          <td class="mono">{{ row.search_fields.join(', ') }}</td>
          <td class="mono tmpl">{{ row.display_template }}</td>
          <td style="text-align:center">{{ row.is_active ? '✓' : '—' }}</td>
          <td>
            <button class="btn-sm" @click="openForm(row)">編集</button>
            <button class="btn-sm btn-del" @click="remove(row)">削除</button>
          </td>
        </tr>
        <tr v-if="!configs.length">
          <td colspan="7" style="text-align:center;color:#999;padding:20px">設定がありません。「＋ 追加」で検索対象を登録してください。</td>
        </tr>
      </tbody>
    </table>

    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal">
        <h3>{{ editing ? '設定編集' : '設定追加' }}</h3>
        <div class="form-grid">
          <label>モデルパス
            <div class="input-with-picker">
              <input v-model="form.model_path" placeholder="例: masters.Supplier" />
              <select @change="onModelSelect">
                <option value="">モデル一覧から選択…</option>
                <option v-for="m in availableModels" :key="m.model_path" :value="m.model_path">{{ m.model_path }}（{{ m.verbose_name }}）</option>
              </select>
            </div>
          </label>
          <label>表示ラベル <input v-model="form.label" placeholder="例: 仕入先" /></label>
          <label>検索フィールド
            <div class="field-tags">
              <span v-for="(f, i) in form.search_fields" :key="'s'+i" class="tag">{{ f }} <button @click="form.search_fields.splice(i,1)">×</button></span>
              <select v-if="selectedModelFields.length" @change="addField('search_fields', $event)">
                <option value="">追加…</option>
                <option v-for="f in selectedModelFields" :key="f.name" :value="f.name">{{ f.name }}（{{ f.verbose_name }}）</option>
              </select>
              <input v-else v-model="fieldInput.search" placeholder="フィールド名を入力" @keydown.enter.prevent="addFieldManual('search_fields')" />
            </div>
          </label>
          <label>表示フィールド
            <div class="field-tags">
              <span v-for="(f, i) in form.display_fields" :key="'d'+i" class="tag">{{ f }} <button @click="form.display_fields.splice(i,1)">×</button></span>
              <select v-if="selectedModelFields.length" @change="addField('display_fields', $event)">
                <option value="">追加…</option>
                <option v-for="f in selectedModelFields" :key="f.name" :value="f.name">{{ f.name }}（{{ f.verbose_name }}）</option>
              </select>
              <input v-else v-model="fieldInput.display" placeholder="フィールド名を入力" @keydown.enter.prevent="addFieldManual('display_fields')" />
            </div>
          </label>
          <label>表示テンプレート <input v-model="form.display_template" placeholder="例: {supplier_name}（コード: {supplier_code}）" /></label>
          <label>フィルタ条件（JSON） <input v-model="filterText" placeholder='例: {"is_active": true}' /></label>
          <div class="form-row">
            <label class="inline">表示順 <input v-model.number="form.display_order" type="number" style="width:60px" /></label>
            <label class="inline"><input v-model="form.is_active" type="checkbox" /> 有効</label>
          </div>
        </div>
        <div v-if="formError" class="form-error">{{ formError }}</div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="showForm = false">キャンセル</button>
          <button class="btn-save" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'

const configs = ref([])
const availableModels = ref([])
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const formError = ref('')
const filterText = ref('{}')
const fieldInput = ref({ search: '', display: '' })

const form = ref({
  model_path: '', label: '', search_fields: [], display_fields: [],
  display_template: '', filter_json: {}, is_active: true, display_order: 0,
})

const selectedModelFields = computed(() => {
  const m = availableModels.value.find(x => x.model_path === form.value.model_path)
  return m ? m.fields : []
})

watch(() => form.value.display_fields, (fields) => {
  if (!form.value.display_template && fields.length) {
    form.value.display_template = `{${fields[0]}}（コード: {${fields.length > 1 ? fields[1] : fields[0]}}）`
  }
}, { deep: true })

const load = async () => {
  const { data } = await api.aiSearchConfigs.list()
  configs.value = data
}

const loadModels = async () => {
  try {
    const { data } = await api.aiSearchConfigs.models()
    availableModels.value = data
  } catch { /* ignore */ }
}

const openForm = (row) => {
  formError.value = ''
  if (row) {
    editing.value = row.id
    form.value = {
      model_path: row.model_path, label: row.label,
      search_fields: [...row.search_fields], display_fields: [...row.display_fields],
      display_template: row.display_template, filter_json: row.filter_json || {},
      is_active: row.is_active, display_order: row.display_order,
    }
    filterText.value = JSON.stringify(row.filter_json || {})
  } else {
    editing.value = null
    form.value = {
      model_path: '', label: '', search_fields: [], display_fields: [],
      display_template: '', filter_json: {}, is_active: true,
      display_order: configs.value.length ? Math.max(...configs.value.map(c => c.display_order)) + 1 : 0,
    }
    filterText.value = '{}'
  }
  showForm.value = true
}

const onModelSelect = (e) => {
  if (e.target.value) {
    form.value.model_path = e.target.value
    const m = availableModels.value.find(x => x.model_path === e.target.value)
    if (m && !form.value.label) form.value.label = m.verbose_name
  }
  e.target.value = ''
}

const addField = (target, e) => {
  const v = e.target.value
  if (v && !form.value[target].includes(v)) form.value[target].push(v)
  e.target.value = ''
}

const addFieldManual = (target) => {
  const key = target === 'search_fields' ? 'search' : 'display'
  const v = fieldInput.value[key].trim()
  if (v && !form.value[target].includes(v)) form.value[target].push(v)
  fieldInput.value[key] = ''
}

const save = async () => {
  formError.value = ''
  try {
    form.value.filter_json = filterText.value.trim() ? JSON.parse(filterText.value) : {}
  } catch {
    formError.value = 'フィルタ条件のJSON形式が不正です。'
    return
  }
  if (!form.value.model_path || !form.value.label || !form.value.search_fields.length || !form.value.display_fields.length || !form.value.display_template) {
    formError.value = 'すべての必須項目を入力してください。'
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await api.aiSearchConfigs.update(editing.value, form.value)
    } else {
      await api.aiSearchConfigs.create(form.value)
    }
    showForm.value = false
    await load()
  } catch (e) {
    formError.value = e.response?.data?.model_path?.[0] || e.response?.data?.detail || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const remove = async (row) => {
  if (!confirm(`「${row.label}」を削除しますか？`)) return
  await api.aiSearchConfigs.delete(row.id)
  await load()
}

onMounted(() => { load(); loadModels() })
</script>

<style scoped>
.config-page { max-width: 1100px; margin: 0 auto; padding: 12px 16px; font-family: "Yu Gothic UI", Meiryo, sans-serif; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.toolbar h2 { font-size: 15px; margin: 0; }
.subtitle { font-size: 11px; color: #888; }
.btn-add { margin-left: auto; background: #0e786d; color: #fff; border: none; border-radius: 5px; padding: 5px 12px; font-size: 12px; cursor: pointer; }
.config-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.config-table th { background: #f5f7f7; text-align: left; padding: 6px 8px; border-bottom: 2px solid #e0e5e5; font-weight: 600; font-size: 11px; color: #556; }
.config-table td { padding: 6px 8px; border-bottom: 1px solid #eee; }
.config-table tr.inactive { opacity: 0.45; }
.mono { font-family: Consolas, monospace; font-size: 11px; color: #446; }
.tmpl { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.btn-sm { background: #fff; border: 1px solid #ddd; border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer; margin-right: 4px; }
.btn-sm:hover { border-color: #0e786d; color: #0e786d; }
.btn-del { color: #c55; }
.btn-del:hover { border-color: #c55; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.3); display: grid; place-items: center; z-index: 1000; }
.modal { background: #fff; border-radius: 10px; padding: 20px 24px; width: min(560px, 92vw); max-height: 90vh; overflow-y: auto; box-shadow: 0 10px 40px rgba(0,0,0,.15); }
.modal h3 { font-size: 14px; margin: 0 0 14px; }
.form-grid { display: grid; gap: 10px; }
.form-grid label { display: grid; gap: 3px; font-size: 11px; font-weight: 600; color: #556; }
.form-grid input, .form-grid select { font-size: 12px; padding: 5px 8px; border: 1px solid #ddd; border-radius: 5px; }
.input-with-picker { display: flex; gap: 6px; }
.input-with-picker input { flex: 1; }
.input-with-picker select { font-size: 11px; max-width: 220px; }
.field-tags { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.tag { background: #e7f7f2; color: #168c7e; padding: 2px 6px; border-radius: 4px; font-size: 11px; display: flex; align-items: center; gap: 3px; }
.tag button { background: none; border: none; color: #888; cursor: pointer; font-size: 12px; padding: 0 2px; }
.field-tags select, .field-tags input { font-size: 11px; padding: 3px 6px; border: 1px solid #ddd; border-radius: 4px; }
.form-row { display: flex; gap: 16px; align-items: center; }
.inline { display: flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 600; color: #556; }
.form-error { color: #c55; font-size: 11px; margin-top: 6px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.btn-cancel { background: #fff; border: 1px solid #ddd; border-radius: 5px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-save { background: #0e786d; color: #fff; border: none; border-radius: 5px; padding: 6px 14px; font-size: 12px; cursor: pointer; }
.btn-save:disabled { opacity: .5; cursor: default; }
</style>
