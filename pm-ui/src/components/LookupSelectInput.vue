<template>
  <div class="lookup-select-input">
    <input
      :value="inputText"
      :list="datalistId"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput(($event.target?.value || '').toString())"
      @blur="onBlur"
    />
    <datalist :id="datalistId">
      <option
        v-for="option in filteredOptions"
        :key="`lookup-option-${option.value}`"
        :value="option.label"
      />
    </datalist>
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
})

const emit = defineEmits(['update:modelValue'])

const datalistId = `lookup-select-${Math.random().toString(36).slice(2, 10)}`
const inputText = ref('')

const normalize = (value) => String(value ?? '').trim().toLowerCase()

const filteredOptions = computed(() => {
  const source = Array.isArray(props.options) ? props.options : []
  const query = normalize(inputText.value)
  if (!query) return source.slice(0, props.maxOptions)
  return source
    .filter((option) => {
      const label = normalize(option?.label)
      const code = normalize(option?.code)
      return label.includes(query) || code.includes(query)
    })
    .slice(0, props.maxOptions)
})

const selectedOption = computed(() =>
  (props.options || []).find((option) => `${option.value}` === `${props.modelValue}`),
)

const syncInputByModelValue = () => {
  inputText.value = selectedOption.value?.label || ''
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
    return label === query || code === query || `${option.value}` === query
  })
  if (exact) return exact
  if (!allowPartial) return null

  const partial = options.filter((option) => {
    const label = normalize(option?.label)
    const code = normalize(option?.code)
    return code.startsWith(query) || label.includes(query)
  })
  if (partial.length === 1) return partial[0]
  return null
}

const onInput = (value) => {
  inputText.value = value
  if (!String(value || '').trim()) {
    emit('update:modelValue', null)
    return
  }
  const matched = findMatch(value, false)
  if (matched) {
    emit('update:modelValue', matched.value)
  }
}

const onBlur = () => {
  const value = String(inputText.value || '')
  if (!value.trim()) {
    emit('update:modelValue', null)
    inputText.value = ''
    return
  }

  const matched = findMatch(value, true)
  if (matched) {
    emit('update:modelValue', matched.value)
    inputText.value = matched.label
    return
  }

  if (selectedOption.value) {
    inputText.value = selectedOption.value.label
    return
  }

  emit('update:modelValue', null)
  inputText.value = ''
}
</script>

<style scoped>
.lookup-select-input {
  width: 100%;
}
.lookup-select-input input {
  width: 100%;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
</style>
