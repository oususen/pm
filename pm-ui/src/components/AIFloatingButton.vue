<template>
  <div v-if="!aiDrawerOpen && !requestDialogOpen && !requestHistoryOpen" ref="root" class="qa-floating">
    <div v-if="menuOpen" class="qa-menu" role="menu">
      <button v-if="canUseAI" type="button" role="menuitem" @click="chooseAI">1 AI</button>
      <button type="button" role="menuitem" @click="chooseRequest">{{ canUseAI ? '2' : '1' }} リクエスト</button>
      <button type="button" role="menuitem" @click="chooseHistory">{{ canUseAI ? '3' : '2' }} リクエスト履歴</button>
    </div>
    <button
      class="ai-floating-button"
      type="button"
      title="Q&Aメニューを開く"
      aria-label="Q&Aメニューを開く"
      :aria-expanded="menuOpen"
      @click="menuOpen = !menuOpen"
    >
      <svg aria-hidden="true" viewBox="0 0 24 24">
        <path d="M5.5 5.5h13v9.2a3 3 0 0 1-3 3H11l-4.3 3v-3H5.5a3 3 0 0 1-3-3v-6.2a3 3 0 0 1 3-3Z" />
        <path d="M8 10.5h8M8 13.5h5" />
      </svg>
      <span>Q&amp;A</span>
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { aiDrawerOpen, openAIDrawer } from '@/composables/aiDrawer'
import { requestDialogOpen, openRequestDialog, requestHistoryOpen, openRequestHistory } from '@/composables/requestDialog'

const route = useRoute()
const root = ref(null)
const menuOpen = ref(false)
const canUseAI = computed(() => hasPermission(authState.user, 'ai.chat', 'view'))

const chooseAI = () => {
  menuOpen.value = false
  openAIDrawer(route.fullPath)
}
const chooseRequest = () => {
  menuOpen.value = false
  openRequestDialog()
}
const chooseHistory = () => {
  menuOpen.value = false
  openRequestHistory()
}

const onOutside = (event) => {
  if (menuOpen.value && root.value && !root.value.contains(event.target)) menuOpen.value = false
}
onMounted(() => document.addEventListener('click', onOutside))
onBeforeUnmount(() => document.removeEventListener('click', onOutside))
</script>

<style scoped>
.qa-floating{position:fixed;right:18px;bottom:18px;z-index:890;display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.qa-menu{display:flex;flex-direction:column;background:#fff;border:1px solid #c8ccd0;border-radius:8px;box-shadow:0 5px 16px rgba(0,0,0,.2);overflow:hidden}
.qa-menu button{border:0;background:none;padding:8px 18px;text-align:left;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
.qa-menu button:hover{background:#e6f4f1}
.ai-floating-button{position:relative;width:52px;height:52px;border:0;border-radius:50%;display:grid;place-items:center;gap:0;background:#087b6e;color:#fff;box-shadow:0 5px 16px rgba(8,123,110,.32);cursor:pointer}.ai-floating-button:hover{background:#05695f;transform:translateY(-1px)}.ai-floating-button:focus-visible{outline:3px solid #9adfd3;outline-offset:3px}.ai-floating-button svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.ai-floating-button span{position:absolute;bottom:5px;font-size:9px;font-weight:800;letter-spacing:.03em}@media(max-width:768px){.qa-floating{right:14px;bottom:14px;z-index:1090}.ai-floating-button{width:48px;height:48px}}
</style>
