<template>
  <div class="lookup-select-input">
    <input
      :value="inputText"
      :placeholder="placeholder"
      :disabled="disabled"
      @focus="onFocus"
      @input="onInput(($event.target?.value || '').toString())"
      @keydown="onKeydown"
      @blur="onBlur"
    />
    <div v-if="isOpen" class="dropdown">
      <div class="dropdown-head" :class="{ 'code-only': codeOnly }">
        <span class="col-code">品番</span>
        <span v-if="!codeOnly" class="col-name">品名</span>
      </div>
      <div class="dropdown-body">
        <button
          v-for="(option, idx) in filteredOptions"
          :key="`lookup-option-${option.value}`"
          type="button"
          class="option-row"
          :class="{ active: idx === activeIndex, 'code-only': codeOnly }"
          @mousedown.prevent="selectOption(option)"
          @mousemove="activeIndex = idx"
        >
          <span class="col-code">{{ option.code || option.label }}</span>
          <span v-if="!codeOnly" class="col-name">{{ option.name || option.label }}</span>
        </button>
        <div v-if="!filteredOptions.length" class="empty-row">候補がありません</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, null],
    default: null,
  },
  options: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  maxOptions: {
    type: Number,
    default: 200,
  },
  codeOnly: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])

const inputText = ref('')
const searchText = ref('')
const isOpen = ref(false)
const activeIndex = ref(-1)

const toHalfWidth = (value) =>
  String(value ?? '')
    .replace(/[！-～]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0))
    .replace(/　/g, ' ')

const normalize = (value) => toHalfWidth(value).trim().toLowerCase()

const scoreOption = (option, query) => {
  const code = normalize(option?.code)
  const label = normalize(option?.label)
  const name = normalize(option?.name)
  if (!query) return 999
  if (code === query) return 0
  if (code.startsWith(query)) return 1
  if (code.endsWith(query)) return 2
  if (code.includes(query)) return 3
  if (label.startsWith(query)) return 4
  if (label.includes(query)) return 5
  if (name.startsWith(query)) return 6
  if (name.includes(query)) return 7
  return 999
}

const selectedOption = computed(() =>
  (props.options || []).find((option) => `${option.value}` === `${props.modelValue}`),
)

const displayText = (option) => {
  if (!option) return ''
  return props.codeOnly ? (option.code || option.label || '') : (option.label || '')
}

const filteredOptions = computed(() => {
  const source = Array.isArray(props.options) ? props.options : []
  const query = normalize(searchText.value)
  if (!query) return source.slice(0, props.maxOptions)
  return source
    .map((option) => ({ option, score: scoreOption(option, query) }))
    .filter((row) => row.score < 999)
    .sort((a, b) => {
      if (a.score !== b.score) return a.score - b.score
      return normalize(a.option?.code).localeCompare(normalize(b.option?.code))
    })
    .map((row) => row.option)
    .slice(0, props.maxOptions)
})

const syncInputByModelValue = () => {
  inputText.value = displayText(selectedOption.value)
  searchText.value = ''
}

watch(() => props.modelValue, syncInputByModelValue, { immediate: true })
watch(() => props.options, syncInputByModelValue, { deep: true })

const findMatch = (text, allowPartial = false) => {
  const query = normalize(text)
  if (!query) return null

  const options = Array.isArray(props.options) ? props.options : []
  const exact = options.find((option) => {
    const label = normalize(option?.label)
    const code = normalize(option?.code)
    const name = normalize(option?.name)
    return label === query || code === query || name === query || `${option.value}` === query
  })
  if (exact) return exact
  if (!allowPartial) return null

  const partial = options.filter((option) => {
    const label = normalize(option?.label)
    const code = normalize(option?.code)
    const name = normalize(option?.name)
    return (
      code.startsWith(query) ||
      code.endsWith(query) ||
      code.includes(query) ||
      label.includes(query) ||
      name.includes(query)
    )
  })
  partial.sort((a, b) => scoreOption(a, query) - scoreOption(b, query))
  if (partial.length === 1) return partial[0]
  return null
}

const onInput = (value) => {
  inputText.value = value
  searchText.value = value
  isOpen.value = true
  activeIndex.value = filteredOptions.value.length ? 0 : -1
  if (!String(value || '').trim()) {
    emit('update:modelValue', null)
    return
  }
  const matched = findMatch(value, false)
  if (matched) {
    emit('update:modelValue', matched.value)
  }
}

const selectOption = (option) => {
  emit('update:modelValue', option.value)
  inputText.value = displayText(option)
  searchText.value = ''
  isOpen.value = false
  activeIndex.value = -1
}

const onFocus = () => {
  searchText.value = ''
  isOpen.value = true
  activeIndex.value = filteredOptions.value.length ? 0 : -1
}

const finalizeInput = () => {
  const value = String(inputText.value || '')
  if (!value.trim()) {
    emit('update:modelValue', null)
    inputText.value = ''
    return
  }

  const matched = findMatch(value, true)
  if (matched) {
    emit('update:modelValue', matched.value)
    inputText.value = displayText(matched)
    return
  }

  if (selectedOption.value) {
    inputText.value = displayText(selectedOption.value)
    return
  }

  emit('update:modelValue', null)
  inputText.value = ''
}

const onKeydown = (event) => {
  if (!isOpen.value && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
    isOpen.value = true
  }
  if (!isOpen.value) return

  const maxIndex = filteredOptions.value.length - 1
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = Math.min(activeIndex.value + 1, maxIndex)
    return
  }
  if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value = Math.max(activeIndex.value - 1, 0)
    return
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    if (activeIndex.value >= 0 && filteredOptions.value[activeIndex.value]) {
      selectOption(filteredOptions.value[activeIndex.value])
      return
    }
    finalizeInput()
    isOpen.value = false
    return
  }
  if (event.key === 'Escape') {
    isOpen.value = false
  }
}

const onBlur = () => {
  window.setTimeout(() => {
    finalizeInput()
    searchText.value = ''
    isOpen.value = false
    activeIndex.value = -1
  }, 120)
}
</script>

<style scoped>
.lookup-select-input {
  position: relative;
  width: 100%;
}
.lookup-select-input input {
  width: 100%;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.dropdown {
  position: absolute;
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  border: 1px solid #9ca3af;
  border-radius: 6px;
  background: #fff;
  z-index: 30;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}
.dropdown-head {
  display: grid;
  grid-template-columns: 42% 58%;
  gap: 8px;
  padding: 5px 8px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 12px;
  font-weight: 700;
  background: #f3f4f6;
}
.dropdown-head.code-only {
  grid-template-columns: 1fr;
}
.dropdown-body {
  max-height: 240px;
  overflow-y: auto;
}
.option-row {
  width: 100%;
  display: grid;
  grid-template-columns: 42% 58%;
  gap: 8px;
  border: none;
  border-bottom: 1px solid #f1f5f9;
  background: #fff;
  text-align: left;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 12px;
}
.option-row.code-only {
  grid-template-columns: 1fr;
}
.option-row.active {
  background: #e0f2fe;
}
.col-code {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.col-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.empty-row {
  padding: 8px;
  color: #6b7280;
  font-size: 12px;
}
</style>
