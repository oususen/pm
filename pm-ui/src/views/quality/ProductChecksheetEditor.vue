<template>
  <div class="page-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">製品チェックシート配置編集</h1>
        <p class="helper-text" v-if="templateObj">
          {{ templateObj.line_code }} / {{ templateObj.process_code }} / {{ templateObj.product_code }} - {{ templateObj.name }}
        </p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn-secondary" to="/quality/product-checksheet/templates">一覧へ</RouterLink>
        <button class="btn-primary" type="button" @click="saveFields" :disabled="saving || !canEditTemplate">フィールド保存</button>
      </div>
    </div>

    <div v-if="templateObj" class="editor-grid">
      <section class="panel controls">
        <h2>テンプレート情報</h2>
        <div class="form-grid">
          <label>帳票タイトル<input :value="templateObj.document_title || templateObj.name" type="text" disabled /></label>
          <label>版<input :value="`v${templateObj.version}`" type="text" disabled /></label>
          <label>状態<input :value="templateObj.status" type="text" disabled /></label>
        </div>

        <h2>項目追加</h2>
        <div class="form-grid">
          <label>種類
            <select v-model="newField.field_type">
              <option value="checkbox">チェック</option>
              <option value="text">テキスト</option>
              <option value="aggregate_okng">OK/NG</option>
              <option value="date">日付</option>
              <option value="photo">写真</option>
              <option value="pen">手書き</option>
              <option value="worker_name">作業者名</option>
              <option value="supervisor_stamp">承認印</option>
            </select>
          </label>
          <label>表示名<input v-model="newField.label" type="text" /></label>
          <label>内部キー<input v-model="newField.key" type="text" /></label>
          <label>必須
            <select v-model="newField.required">
              <option :value="false">任意</option>
              <option :value="true">必須</option>
            </select>
          </label>
          <p class="helper-text full-row">台紙上の追加したい位置をクリックしてください。</p>
        </div>

        <h2>配置項目</h2>
        <div class="field-list">
          <button
            v-for="(field, index) in fields"
            :key="field.key"
            class="field-row"
            :class="{ active: selectedIndex === index }"
            type="button"
            @click="selectedIndex = index"
          >
            <span>{{ field.label }}</span>
            <small>{{ field.field_type }} / {{ Math.round(field.x) }},{{ Math.round(field.y) }}</small>
          </button>
        </div>

        <div v-if="selectedField" class="field-detail">
          <h2>選択中</h2>
          <div class="form-grid">
            <label>表示名<input v-model="selectedField.label" type="text" /></label>
            <label>内部キー<input v-model="selectedField.key" type="text" /></label>
            <label>種類
              <select v-model="selectedField.field_type">
                <option value="checkbox">チェック</option>
                <option value="text">テキスト</option>
                <option value="aggregate_okng">OK/NG</option>
                <option value="date">日付</option>
                <option value="photo">写真</option>
                <option value="pen">手書き</option>
                <option value="worker_name">作業者名</option>
                <option value="supervisor_stamp">承認印</option>
              </select>
            </label>
            <label>必須
              <select v-model="selectedField.required">
                <option :value="false">任意</option>
                <option :value="true">必須</option>
              </select>
            </label>
            <label>X<input v-model.number="selectedField.x" type="number" /></label>
            <label>Y<input v-model.number="selectedField.y" type="number" /></label>
            <label>幅<input v-model.number="selectedField.width" type="number" min="6" /></label>
            <label>高さ<input v-model.number="selectedField.height" type="number" min="6" /></label>
            <label class="full-row">説明<input v-model="selectedField.description" type="text" /></label>
            <button class="btn-danger full-row" type="button" @click="removeSelected" :disabled="!canEditTemplate">削除</button>
          </div>
        </div>
      </section>

      <section class="sheet-panel">
        <div class="sheet-toolbar">
          <span>v{{ templateObj.version }} / {{ templateObj.status }}</span>
          <button class="btn-secondary" type="button" @click="zoom = Math.max(0.4, zoom - 0.1)">縮小</button>
          <button class="btn-secondary" type="button" @click="zoom += 0.1">拡大</button>
        </div>
        <div class="sheet-scroll">
          <div class="sheet-stage" :class="{ editable: canEditTemplate }" :style="stageStyle" @click="handleStageClick">
            <img class="sheet-image" :src="templateObj.background_image_url" alt="台紙" />
            <div
              v-for="(field, index) in fields"
              :key="field.key"
              class="field-box"
              :class="{ selected: selectedIndex === index }"
              :style="boxStyle(field)"
              @click.stop="selectedIndex = index"
              @pointerdown.stop="startDrag($event, field)"
            >
              <span v-if="field.show_label !== false" class="field-label">{{ field.label }}</span>
              <strong>{{ previewText(field) }}</strong>
              <span
                v-if="selectedIndex === index && canEditTemplate"
                class="resize-handle"
                @pointerdown.stop.prevent="startResize($event, field)"
              ></span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const route = useRoute()
const templateObj = ref(null)
const fields = ref([])
const selectedIndex = ref(-1)
const saving = ref(false)
const zoom = ref(1)
const dragState = ref(null)
const resizeState = ref(null)
const newField = ref({
  field_type: 'checkbox',
  label: 'チェック',
  key: '',
  required: false,
})
const canAccessQuality = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) return hasPermission(user, resource, level)
  return hasPermission(user, 'quality', level)
}
const canEditTemplate = computed(() => canAccessQuality('quality.product_checksheet_template', 'edit'))

const selectedField = computed(() => (selectedIndex.value >= 0 ? fields.value[selectedIndex.value] : null))
const stageStyle = computed(() => ({
  width: `${templateObj.value?.background_width || 1200}px`,
  height: `${templateObj.value?.background_height || 1600}px`,
  transform: `scale(${zoom.value})`,
  transformOrigin: 'top left',
}))

const loadTemplate = async () => {
  const res = await api.productChecksheets.getTemplate(route.params.id)
  templateObj.value = res.data
  fields.value = (res.data.fields_data || []).map((item) => ({ ...item }))
}

const defaultSize = (type) => {
  if (type === 'checkbox') return { width: 28, height: 28 }
  if (type === 'photo') return { width: 180, height: 120 }
  if (type === 'pen') return { width: 220, height: 120 }
  if (type === 'supervisor_stamp') return { width: 120, height: 120 }
  return { width: 150, height: 34 }
}

const uniqueKey = (base) => {
  const stem = String(base || `field_${fields.value.length + 1}`).trim().toLowerCase().replace(/[^a-z0-9_]+/g, '_') || `field_${fields.value.length + 1}`
  const taken = new Set(fields.value.map((item) => item.key))
  let key = stem
  let index = 1
  while (taken.has(key)) {
    key = `${stem}_${index}`
    index += 1
  }
  return key
}

const clamp = (value, minValue, maxValue) => Math.min(Math.max(value, minValue), maxValue)

const addField = (position = null) => {
  if (!canEditTemplate.value) return
  const size = defaultSize(newField.value.field_type)
  const maxX = Math.max((templateObj.value?.background_width || 0) - size.width, 0)
  const maxY = Math.max((templateObj.value?.background_height || 0) - size.height, 0)
  const x = position ? clamp(Math.round(position.x), 0, maxX) : Math.round(maxX / 2)
  const y = position ? clamp(Math.round(position.y), 0, maxY) : Math.round(maxY / 2)
  const field = {
    key: uniqueKey(newField.value.key || newField.value.label),
    label: newField.value.label || '項目',
    field_type: newField.value.field_type,
    description: '',
    x,
    y,
    width: size.width,
    height: size.height,
    required: Boolean(newField.value.required),
    placeholder: '',
    show_label: true,
    text_direction: 'horizontal',
    counter_step: 1,
  }
  fields.value.push(field)
  selectedIndex.value = fields.value.length - 1
}

const handleStageClick = (event) => {
  if (!canEditTemplate.value) {
    clearSelection()
    return
  }
  const rect = event.currentTarget.getBoundingClientRect()
  addField({
    x: (event.clientX - rect.left) / zoom.value,
    y: (event.clientY - rect.top) / zoom.value,
  })
}

const removeSelected = () => {
  if (!canEditTemplate.value) return
  if (selectedIndex.value < 0) return
  fields.value.splice(selectedIndex.value, 1)
  selectedIndex.value = -1
}

const clearSelection = () => {
  selectedIndex.value = -1
}

const boxStyle = (field) => ({
  left: `${field.x}px`,
  top: `${field.y}px`,
  width: `${field.width}px`,
  height: `${field.height}px`,
})

const previewText = (field) => {
  if (field.field_type === 'checkbox') return '□'
  if (field.field_type === 'photo') return '写真'
  if (field.field_type === 'pen') return '手書き'
  if (field.field_type === 'supervisor_stamp') return '承認'
  if (field.field_type === 'aggregate_okng') return 'OK/NG'
  if (field.field_type === 'date') return '日付'
  return '入力'
}

const startDrag = (event, field) => {
  if (!canEditTemplate.value) return
  if (resizeState.value) return
  dragState.value = {
    field,
    startX: event.clientX,
    startY: event.clientY,
    originX: Number(field.x || 0),
    originY: Number(field.y || 0),
  }
  event.currentTarget.setPointerCapture(event.pointerId)
}

const startResize = (event, field) => {
  if (!canEditTemplate.value) return
  dragState.value = null
  resizeState.value = {
    field,
    startX: event.clientX,
    startY: event.clientY,
    originWidth: Number(field.width || 0),
    originHeight: Number(field.height || 0),
  }
  event.currentTarget.setPointerCapture(event.pointerId)
}

const onPointerMove = (event) => {
  if (resizeState.value) {
    const state = resizeState.value
    const field = state.field
    const maxWidth = Math.max((templateObj.value?.background_width || 0) - Number(field.x || 0), 6)
    const maxHeight = Math.max((templateObj.value?.background_height || 0) - Number(field.y || 0), 6)
    field.width = clamp(Math.round(state.originWidth + (event.clientX - state.startX) / zoom.value), 6, maxWidth)
    field.height = clamp(Math.round(state.originHeight + (event.clientY - state.startY) / zoom.value), 6, maxHeight)
    return
  }
  if (!dragState.value) return
  const state = dragState.value
  state.field.x = Math.max(0, Math.round(state.originX + (event.clientX - state.startX) / zoom.value))
  state.field.y = Math.max(0, Math.round(state.originY + (event.clientY - state.startY) / zoom.value))
}

const stopPointerAction = () => {
  dragState.value = null
  resizeState.value = null
}

const saveFields = async () => {
  if (!canEditTemplate.value) return
  saving.value = true
  try {
    await api.productChecksheets.saveFields(templateObj.value.id, {
      fields: fields.value,
    })
    await loadTemplate()
    alert('フィールドを保存しました。')
  } catch (error) {
    console.error(error)
    alert(`保存に失敗しました: ${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', stopPointerAction)
  window.addEventListener('pointercancel', stopPointerAction)
  await loadTemplate()
})

onUnmounted(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', stopPointerAction)
  window.removeEventListener('pointercancel', stopPointerAction)
})
</script>

<style scoped>
.helper-text { margin: 0; color: #5f6b76; }
.editor-grid { display: grid; grid-template-columns: 360px 1fr; gap: 16px; align-items: start; }
.panel, .sheet-panel { background: #fff; border: 1px solid #d8dee6; border-radius: 8px; padding: 14px; }
.panel h2 { margin: 10px 0; font-size: 16px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.form-grid label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: #374151; }
.form-grid input, .form-grid select, .form-grid textarea { border: 1px solid #cfd6df; border-radius: 6px; padding: 7px; }
.full-row { grid-column: 1 / -1; }
.field-list { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow: auto; }
.field-row { display: flex; justify-content: space-between; gap: 8px; border: 1px solid #d8dee6; background: #fff; border-radius: 6px; padding: 8px; text-align: left; cursor: pointer; }
.field-row.active { border-color: #2563eb; background: #eff6ff; }
.field-row small { color: #6b7280; }
.sheet-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.sheet-scroll { overflow: auto; max-height: calc(100vh - 190px); border: 1px solid #edf1f5; background: #f8fafc; }
.sheet-stage { position: relative; }
.sheet-stage.editable { cursor: crosshair; }
.sheet-image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.field-box { position: absolute; border: 2px solid #2563eb; background: rgba(37, 99, 235, 0.12); cursor: move; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #111827; }
.field-box.selected { border-color: #dc2626; background: rgba(220, 38, 38, 0.16); }
.field-label { position: absolute; left: 0; top: -20px; background: #111827; color: #fff; padding: 2px 5px; border-radius: 4px; white-space: nowrap; }
.resize-handle { position: absolute; right: -8px; bottom: -8px; width: 16px; height: 16px; border-radius: 50%; background: #f59e0b; border: 2px solid #fff; box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.2); cursor: nwse-resize; }
.btn-primary, .btn-secondary, .btn-danger { border-radius: 6px; padding: 8px 12px; border: 1px solid #2563eb; text-decoration: none; cursor: pointer; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-secondary { background: #fff; color: #2563eb; }
.btn-danger { background: #fff; border-color: #dc2626; color: #dc2626; }
@media (max-width: 980px) { .editor-grid { grid-template-columns: 1fr; } }
</style>

