<template>
  <div class="user-chip-select">
    <input
      v-model="searchText"
      class="search-input"
      placeholder="社員コード/氏名/ユーザー名で検索して追加"
      @keyup.enter.prevent="addFirstCandidate"
    />
    <div v-if="candidates.length" class="candidate-list">
      <div v-for="u in candidates" :key="u.id" class="candidate-item" @click="addUser(u)">
        <span class="candidate-code">{{ codeLabel(u) }}</span>
        <span class="candidate-name">{{ nameLabel(u) }}</span>
      </div>
    </div>
    <div class="chip-list">
      <span v-for="uid in modelValue" :key="uid" class="chip">
        <span class="chip-label">{{ userLabel(uid) }}</span>
        <button class="chip-remove" @click="removeUser(uid)">&times;</button>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  userList: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const searchText = ref('')

const normalizeUserId = (value) => Number(value)

const codeLabel = (u) => u?.profile?.employee_code || u?.username || u?.email || ''
const nameLabel = (u) => {
  const last = u?.last_name || ''
  const first = u?.first_name || ''
  return `${last}${first}`.trim() || u?.username || u?.email || ''
}

const candidates = computed(() => {
  const kw = (searchText.value || '').trim().toLowerCase()
  if (!kw) return []
  return props.userList
    .filter((u) => {
      const userId = normalizeUserId(u.id)
      if (props.modelValue.some((id) => normalizeUserId(id) === userId)) return false
      const code = codeLabel(u).toLowerCase()
      const name = nameLabel(u).toLowerCase()
      const uname = (u?.username || '').toLowerCase()
      const email = (u?.email || '').toLowerCase()
      return code.includes(kw) || name.includes(kw) || uname.includes(kw) || email.includes(kw)
    })
    .slice(0, 8)
})

const addUser = (u) => {
  const userId = normalizeUserId(u.id)
  if (!props.modelValue.some((id) => normalizeUserId(id) === userId)) {
    emit('update:modelValue', [...props.modelValue, userId])
  }
  searchText.value = ''
}

const addFirstCandidate = () => {
  if (candidates.value.length) addUser(candidates.value[0])
}

const removeUser = (uid) => {
  const targetId = normalizeUserId(uid)
  emit('update:modelValue', props.modelValue.filter((id) => normalizeUserId(id) !== targetId))
}

const userLabel = (uid) => {
  const targetId = normalizeUserId(uid)
  const u = props.userList.find((x) => normalizeUserId(x.id) === targetId)
  if (!u) return `ID:${uid}`
  return `${codeLabel(u)} ${nameLabel(u)}`.trim()
}
</script>

<style scoped>
.user-chip-select { position: relative; }
.search-input { width: 100%; padding: 4px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px; }
.candidate-list { position: absolute; z-index: 10; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; max-height: 200px; overflow-y: auto; width: 100%; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.candidate-item { padding: 6px 8px; cursor: pointer; font-size: 13px; display: flex; gap: 8px; }
.candidate-item:hover { background: #eff6ff; }
.candidate-code { font-weight: 600; color: #2563eb; min-width: 60px; }
.candidate-name { color: #1e293b; }
.chip-list { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
.chip { display: inline-flex; align-items: center; gap: 4px; background: #eef2f6; border: 1px solid #cfd6e1; border-radius: 14px; padding: 2px 8px; font-size: 12px; }
.chip-remove { border: none; background: none; cursor: pointer; color: #64748b; font-size: 14px; padding: 0; line-height: 1; }
.chip-remove:hover { color: #dc2626; }
</style>
