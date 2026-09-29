<template>
  <button
    v-if="canUseAI && !aiDrawerOpen"
    class="ai-floating-button"
    type="button"
    title="社内AIを開く"
    aria-label="社内AIを開く"
    @click="openAIDrawer(route.fullPath)"
  >
    <svg aria-hidden="true" viewBox="0 0 24 24">
      <path d="M5.5 5.5h13v9.2a3 3 0 0 1-3 3H11l-4.3 3v-3H5.5a3 3 0 0 1-3-3v-6.2a3 3 0 0 1 3-3Z" />
      <path d="M8 10.5h8M8 13.5h5" />
    </svg>
    <span>AI</span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { aiDrawerOpen, openAIDrawer } from '@/composables/aiDrawer'

const route = useRoute()
const canUseAI = computed(() => hasPermission(authState.user, 'ai.chat', 'view'))
</script>

<style scoped>
.ai-floating-button{position:fixed;right:18px;bottom:18px;z-index:890;width:52px;height:52px;border:0;border-radius:50%;display:grid;place-items:center;gap:0;background:#087b6e;color:#fff;box-shadow:0 5px 16px rgba(8,123,110,.32);cursor:pointer}.ai-floating-button:hover{background:#05695f;transform:translateY(-1px)}.ai-floating-button:focus-visible{outline:3px solid #9adfd3;outline-offset:3px}.ai-floating-button svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.ai-floating-button span{position:absolute;bottom:5px;font-size:9px;font-weight:800;letter-spacing:.03em}@media(max-width:768px){.ai-floating-button{right:14px;bottom:14px;width:48px;height:48px;z-index:1090}}
</style>
