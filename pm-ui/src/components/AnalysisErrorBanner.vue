<template>
  <div v-if="notices.length" ref="banner" class="analysis-error-banner">
    <div v-for="notice in notices" :key="notice.id" class="analysis-error-item" role="alert">
      <div><strong class="analysis-error-heading">エラー</strong><p>{{ notice.message }}</p></div>
      <button type="button" class="analysis-error-close" aria-label="エラーを閉じる" @click="notice.dismiss">×</button>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({ notices: { type: Array, default: () => [] } })
const banner = ref(null)
let generation = 0, disposed = false
onBeforeUnmount(() => { disposed = true; generation++ })
watch(() => props.notices.map(({ id, message }) => ({ id, message })), async (current, previous = []) => {
  const request = ++generation
  if (!current.some(notice => !previous.some(old => old.id === notice.id && old.message === notice.message))) return
  await nextTick()
  const element = banner.value
  // 非表示タブや破棄後はスクロールしない。視界内なら位置・フォーカスを保つ。
  if (disposed || request !== generation || !element || !element.getClientRects().length) return
  const rect = element.getBoundingClientRect()
  if (rect.top >= 0 && rect.bottom <= window.innerHeight && rect.left >= 0 && rect.right <= window.innerWidth) return
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  element.scrollIntoView({ block: 'start', behavior: reduced ? 'auto' : 'smooth' })
}, { immediate: true, flush: 'post' })
</script>

<style scoped>
.analysis-error-banner { position: sticky; top: 32px; z-index: 10000; border: 2px solid #a22; background: #fff0ee; color: #a22; padding: 8px; margin: 8px 0; max-height: calc(100dvh - 56px); overflow: auto; scroll-margin-top: 32px; box-shadow: 0 2px 6px #0002; }
.analysis-error-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.analysis-error-item + .analysis-error-item { border-top: 1px solid #a22; margin-top: 8px; padding-top: 8px; }
.analysis-error-heading, p { font-weight: 700; } p { margin: 4px 0 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.analysis-error-item > div { min-width: 0; }
.analysis-error-close { flex: none; padding: 2px 10px; border: 1px solid #a22; background: #fff0ee; color: #a22; font: inherit; font-weight: 700; cursor: pointer; }
</style>
