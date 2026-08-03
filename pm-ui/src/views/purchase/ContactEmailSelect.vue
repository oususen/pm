<template>
  <div class="contact-email-select">
    <div class="selected-box" @click="openPicker">
      <template v-if="normalizedValue.length">
        <div v-if="multiple" class="selected-list">
          <div v-for="email in normalizedValue" :key="email" class="selected-item">
            {{ selectedLabel(email) }}
          </div>
        </div>
        <div v-else class="selected-single">
          {{ selectedLabel(normalizedValue[0]) }}
        </div>
      </template>
      <div v-else class="selected-placeholder">{{ placeholder }}</div>
    </div>

    <div class="action-row">
      <button type="button" class="picker-button" @click="openPicker">
        {{ resolvedPickerButtonLabel }}
      </button>
      <button
        v-if="normalizedValue.length"
        type="button"
        class="clear-button"
        @click="clearSelection"
      >
        クリア
      </button>
    </div>

    <div v-if="showPicker" class="picker-overlay" @click.self="closePicker">
      <div class="picker-modal">
        <div class="picker-header">
          <div class="picker-title">{{ resolvedPickerTitle }}</div>
          <button type="button" class="icon-button" @click="closePicker">×</button>
        </div>

        <div class="picker-toolbar">
          <input
            ref="searchInputRef"
            v-model="searchText"
            class="search-input"
            :placeholder="searchPlaceholder"
            @keyup.enter.prevent="addFirstCandidate"
          />
          <label class="filter-toggle">
            <input v-model="supplierOnly" type="checkbox" />
            仕入先候補を優先表示
          </label>
        </div>

        <div class="picker-body">
          <div class="candidate-pane">
            <div class="pane-title">候補</div>
            <div class="pane-list">
              <button
                v-for="contact in filteredCandidates"
                :key="contact.id"
                type="button"
                class="pane-item"
                @click="selectContact(contact)"
              >
                <div class="pane-name">{{ contactLabel(contact) }}</div>
                <div class="pane-email">{{ contact.email }}</div>
              </button>
              <div v-if="!filteredCandidates.length" class="empty-state">
                該当する連絡先がありません
              </div>
            </div>
          </div>

          <div class="selected-pane">
            <div class="pane-title">選択済み</div>
            <div class="pane-list selected-pane-list">
              <div v-for="email in normalizedValue" :key="email" class="selected-chip">
                <div class="selected-chip-text">{{ selectedLabel(email) }}</div>
                <button type="button" class="icon-button" @click="removeEmail(email)">×</button>
              </div>
              <div v-if="!normalizedValue.length" class="empty-state">
                まだ選択されていません
              </div>
            </div>
          </div>
        </div>

        <div class="picker-footer">
          <button type="button" class="btn-secondary" @click="closePicker">閉じる</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'

const props = defineProps({
  contacts: { type: Array, default: () => [] },
  modelValue: { type: [Array, String], default: () => [] },
  multiple: { type: Boolean, default: false },
  placeholder: { type: String, default: '連絡先を選択' },
  supplierKeywords: { type: Array, default: () => [] },
  pickerButtonLabel: { type: String, default: '' },
  pickerTitle: { type: String, default: '' },
  searchPlaceholder: { type: String, default: '会社名 / 担当者 / 部署 / 種別 / メールで検索' },
})

const emit = defineEmits(['update:modelValue'])

const showPicker = ref(false)
const searchText = ref('')
const supplierOnly = ref(true)
const searchInputRef = ref(null)

const normalizedValue = computed(() => {
  if (props.multiple) return Array.isArray(props.modelValue) ? props.modelValue : []
  return props.modelValue ? [props.modelValue] : []
})

const resolvedPickerButtonLabel = computed(() => {
  if (props.pickerButtonLabel) return props.pickerButtonLabel
  return props.multiple ? 'CC選択' : '返信先選択'
})

const resolvedPickerTitle = computed(() => {
  if (props.pickerTitle) return props.pickerTitle
  return props.multiple ? 'CC送信先選択' : '返信先選択'
})

const searchableText = (contact) => {
  return [
    contact.company_name,
    contact.department,
    contact.contact_person,
    contact.contact_type,
    contact.email,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

const supplierKeywordList = computed(() => {
  return (props.supplierKeywords || [])
    .map((value) => String(value || '').trim().toLowerCase())
    .filter(Boolean)
})

const isSupplierMatched = (contact) => {
  if (!supplierKeywordList.value.length) return false
  const text = searchableText(contact)
  return supplierKeywordList.value.some((keyword) => text.includes(keyword))
}

const orderedContacts = computed(() => {
  const matched = []
  const others = []
  for (const contact of props.contacts) {
    if (!contact.email) continue
    if (isSupplierMatched(contact)) matched.push(contact)
    else others.push(contact)
  }
  return [...matched, ...others]
})

const filteredCandidates = computed(() => {
  const keyword = searchText.value.trim().toLowerCase()
  const selectedSet = new Set(normalizedValue.value)
  return orderedContacts.value.filter((contact) => {
    if (selectedSet.has(contact.email)) return false
    if (supplierOnly.value && supplierKeywordList.value.length && !isSupplierMatched(contact)) return false
    if (!keyword) return true
    return searchableText(contact).includes(keyword)
  })
})

const emitValue = (emails) => {
  if (props.multiple) emit('update:modelValue', emails)
  else emit('update:modelValue', emails[0] || '')
}

const selectContact = (contact) => {
  if (props.multiple) {
    emitValue([...normalizedValue.value, contact.email])
  } else {
    emitValue([contact.email])
    closePicker()
  }
}

const removeEmail = (email) => {
  emitValue(normalizedValue.value.filter((value) => value !== email))
}

const clearSelection = () => {
  emitValue([])
}

const addFirstCandidate = () => {
  if (filteredCandidates.value.length) {
    selectContact(filteredCandidates.value[0])
  }
}

const contactLabel = (contact) => {
  const parts = [
    contact.company_name,
    contact.department,
    contact.contact_person,
    contact.contact_type ? `(${contact.contact_type})` : '',
  ].filter(Boolean)
  return parts.join(' ')
}

const selectedLabel = (email) => {
  const contact = props.contacts.find((item) => item.email === email)
  if (!contact) return email
  return `${contactLabel(contact)} <${email}>`
}

const openPicker = async () => {
  showPicker.value = true
  await nextTick()
  searchInputRef.value?.focus()
}

const closePicker = () => {
  showPicker.value = false
  searchText.value = ''
}
</script>

<style scoped>
.contact-email-select { display: flex; flex-direction: column; gap: 6px; }
.selected-box {
  min-height: 38px;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.selected-box:hover { border-color: #94a3b8; }
.selected-list { display: flex; flex-direction: column; gap: 4px; }
.selected-item, .selected-single { font-size: 12px; color: #0f172a; line-height: 1.4; }
.selected-placeholder { font-size: 13px; color: #94a3b8; }
.action-row { display: flex; gap: 8px; }
.picker-button, .clear-button, .btn-secondary {
  padding: 5px 12px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #fff;
  font-size: 12px;
  cursor: pointer;
}
.picker-button { border-color: #3b82f6; color: #2563eb; }
.clear-button:hover, .btn-secondary:hover, .picker-button:hover { background: #f8fafc; }
.picker-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10020;
}
.picker-modal {
  width: min(980px, calc(100vw - 32px));
  max-height: min(720px, calc(100vh - 32px));
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.22);
  overflow: hidden;
}
.picker-header, .picker-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
}
.picker-footer {
  border-top: 1px solid #e2e8f0;
  border-bottom: none;
  justify-content: flex-end;
}
.picker-title { font-size: 15px; font-weight: 700; color: #0f172a; }
.picker-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.search-input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.filter-toggle { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #334155; white-space: nowrap; }
.picker-body {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 0;
  min-height: 360px;
}
.candidate-pane, .selected-pane { min-width: 0; display: flex; flex-direction: column; }
.candidate-pane { border-right: 1px solid #e2e8f0; }
.pane-title {
  padding: 10px 16px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.pane-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.pane-item {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  margin-bottom: 8px;
}
.pane-item:hover {
  border-color: #93c5fd;
  background: #eff6ff;
}
.pane-name { font-size: 13px; color: #0f172a; line-height: 1.4; }
.pane-email { font-size: 12px; color: #475569; margin-top: 3px; }
.selected-pane-list { background: #fcfcfd; }
.selected-chip {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  background: #f8fbff;
  margin-bottom: 8px;
}
.selected-chip-text { font-size: 12px; color: #0f172a; line-height: 1.4; word-break: break-all; }
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  color: #94a3b8;
  font-size: 13px;
}
.icon-button {
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
}
.icon-button:hover { color: #dc2626; }

@media (max-width: 900px) {
  .picker-body { grid-template-columns: 1fr; }
  .candidate-pane { border-right: none; border-bottom: 1px solid #e2e8f0; }
  .picker-toolbar { flex-direction: column; align-items: stretch; }
}
</style>
