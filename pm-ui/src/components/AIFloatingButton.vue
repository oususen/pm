<template>
  <div v-if="visible" ref="root" class="qa-floating" :class="{ 'is-collapsed': collapsed }" :style="floatingStyle">
    <button v-if="collapsed" type="button" class="qa-restore" title="Q&Aボタンを戻す" aria-label="Q&Aボタンを戻す" @click="restore">Q&amp;A</button>
    <template v-else>
      <div v-if="menuOpen" ref="menu" class="qa-menu" role="menu" :style="menuStyle">
        <button v-if="canUseAI" type="button" role="menuitem" @click="chooseAI">1 AI</button>
        <button type="button" role="menuitem" @click="chooseRequest">{{ canUseAI ? '2' : '1' }} リクエスト</button>
        <button type="button" role="menuitem" @click="chooseHistory">{{ canUseAI ? '3' : '2' }} リクエスト履歴</button>
      </div>
      <button class="ai-floating-button" type="button" title="クリックでQ&Aメニュー・ドラッグで移動" aria-label="Q&Aメニューを開く（ドラッグで移動）" :aria-expanded="menuOpen"
        @pointerdown="startDrag" @click="toggleMenu" @dragstart.prevent>
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="M5.5 5.5h13v9.2a3 3 0 0 1-3 3H11l-4.3 3v-3H5.5a3 3 0 0 1-3-3v-6.2a3 3 0 0 1 3-3Z" />
          <path d="M8 10.5h8M8 13.5h5" />
        </svg>
        <span>Q&amp;A</span>
      </button>
      <button type="button" class="qa-collapse" title="Q&Aボタンを折りたたむ" aria-label="Q&Aボタンを折りたたむ" @click="collapse">×</button>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import { aiDrawerOpen, openAIDrawer } from '@/composables/aiDrawer'
import { requestDialogOpen, openRequestDialog, requestHistoryOpen, openRequestHistory } from '@/composables/requestDialog'

const STORAGE_KEY = 'pm.qa-floating.preferences.v1'
const route = useRoute()
const root = ref(null)
const menu = ref(null)
const menuOpen = ref(false)
const collapsed = ref(false)
const position = ref(null)
const viewport = ref({ width: window.innerWidth, height: window.innerHeight })
const menuStyle = ref({})
const visible = computed(() => !aiDrawerOpen.value && !requestDialogOpen.value && !requestHistoryOpen.value)
const canUseAI = computed(() => hasPermission(authState.user, 'ai.chat', 'view'))
const size = computed(() => viewport.value.width <= 768 ? 68 : 72)
const height = computed(() => size.value + 8)
const clamp = (value, extent, length) => Math.max(0, Math.min(value, Math.max(0, extent - length)))
const boundedPosition = (point) => ({ x: clamp(point.x, viewport.value.width, size.value), y: clamp(point.y, viewport.value.height, height.value) })
const floatingStyle = computed(() => {
  if (!position.value) return {}
  return {
    left: `${collapsed.value ? Math.max(0, viewport.value.width - 48) : position.value.x}px`,
    top: `${collapsed.value ? clamp(position.value.y, viewport.value.height, 32) : position.value.y}px`,
    right: 'auto', bottom: 'auto',
  }
})
let drag = null
let suppressClick = false

const savePreferences = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ position: position.value, collapsed: collapsed.value }))
  } catch {
    console.warn('Q&Aボタンの位置・折りたたみ状態をブラウザに保存できません。')
  }
}
const placeMenu = async () => {
  await nextTick()
  if (!menuOpen.value || !menu.value || !root.value) return
  const bounds = root.value.getBoundingClientRect()
  const width = menu.value.offsetWidth
  const height = menu.value.offsetHeight
  const x = clamp(bounds.right - width, viewport.value.width, width)
  const preferredY = bounds.top - height - 8
  const y = clamp(preferredY >= 0 ? preferredY : bounds.bottom + 8, viewport.value.height, height)
  menuStyle.value = { left: `${x - bounds.left}px`, top: `${y - bounds.top}px` }
}
const removeDragListeners = () => {
  window.removeEventListener('pointermove', moveDrag)
  window.removeEventListener('pointerup', endDrag)
  window.removeEventListener('pointercancel', endDrag)
}
const endDrag = (event) => {
  if (!drag || (event && event.pointerId !== drag.id)) return
  const moved = drag.moved
  const { target, id } = drag
  drag = null
  removeDragListeners()
  if (target.hasPointerCapture(id)) target.releasePointerCapture(id)
  suppressClick = moved || event?.type === 'pointercancel'
  if (moved) savePreferences()
}
const moveDrag = (event) => {
  if (!drag || event.pointerId !== drag.id) return
  const dx = event.clientX - drag.x
  const dy = event.clientY - drag.y
  // タップ時の小さな指の揺れと、移動操作を区別する。
  if (!drag.moved && Math.hypot(dx, dy) < 6) return
  drag.moved = true
  menuOpen.value = false
  position.value = boundedPosition({ x: drag.origin.x + dx, y: drag.origin.y + dy })
  event.preventDefault()
}
const startDrag = (event) => {
  if (!event.isPrimary || event.button !== 0 || drag || !root.value) return
  suppressClick = false
  const bounds = root.value.getBoundingClientRect()
  drag = { id: event.pointerId, x: event.clientX, y: event.clientY, origin: { x: bounds.left, y: bounds.top }, moved: false, target: event.currentTarget }
  event.currentTarget.setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', moveDrag, { passive: false })
  window.addEventListener('pointerup', endDrag)
  window.addEventListener('pointercancel', endDrag)
}
const toggleMenu = (event) => {
  if (suppressClick && event.detail !== 0) {
    suppressClick = false
    return
  }
  suppressClick = false
  menuOpen.value = !menuOpen.value
}
const collapse = () => {
  endDrag()
  menuOpen.value = false
  collapsed.value = true
  savePreferences()
}
const restore = () => {
  collapsed.value = false
  position.value = boundedPosition(position.value)
  savePreferences()
}
const resize = () => {
  endDrag()
  viewport.value = { width: window.innerWidth, height: window.innerHeight }
  if (position.value) position.value = boundedPosition(position.value)
  savePreferences()
  placeMenu()
}
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
watch([menuOpen, canUseAI], placeMenu)
watch(visible, (shown) => {
  if (!shown) {
    endDrag()
    menuOpen.value = false
  }
})
onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
    if (saved && Number.isFinite(saved.position?.x) && Number.isFinite(saved.position?.y) && typeof saved.collapsed === 'boolean') {
      position.value = boundedPosition(saved.position)
      collapsed.value = saved.collapsed
    }
  } catch {
    console.warn('Q&Aボタンの保存状態を読み込めません。')
  }
  if (!position.value) {
    const margin = viewport.value.width <= 768 ? 14 : 18
    position.value = boundedPosition({ x: viewport.value.width - size.value - margin, y: viewport.value.height - height.value - margin })
  }
  document.addEventListener('click', onOutside)
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  endDrag()
  document.removeEventListener('click', onOutside)
  window.removeEventListener('resize', resize)
})
</script>

<style scoped>
.qa-floating{position:fixed;right:18px;bottom:18px;width:72px;height:80px;z-index:890}
.qa-floating.is-collapsed{width:48px;height:32px}
.qa-menu{position:absolute;display:flex;flex-direction:column;max-width:100vw;max-height:100vh;background:#fff;border:1px solid #c8ccd0;border-radius:8px;box-shadow:0 5px 16px rgba(0,0,0,.2);overflow:auto}
.qa-menu button{border:0;background:none;padding:8px 18px;text-align:left;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
.qa-menu button:hover{background:#e6f4f1}
.ai-floating-button{position:absolute;left:0;bottom:0;width:52px;height:52px;border:0;border-radius:50%;display:grid;place-items:center;gap:0;background:#087b6e;color:#fff;box-shadow:0 5px 16px rgba(8,123,110,.32);cursor:grab;touch-action:none;user-select:none}.ai-floating-button:active{cursor:grabbing}.ai-floating-button:hover{background:#05695f}.ai-floating-button:focus-visible,.qa-collapse:focus-visible,.qa-restore:focus-visible{outline:3px solid #9adfd3;outline-offset:2px}.ai-floating-button svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.ai-floating-button span{position:absolute;bottom:5px;font-size:9px;font-weight:800;letter-spacing:.03em}
.qa-collapse{position:absolute;top:0;left:14px;width:24px;height:24px;border:1px solid #c8ccd0;border-radius:50%;background:#fff;color:#43514f;cursor:pointer;font-size:18px;line-height:20px;padding:0}
.qa-restore{width:48px;height:32px;border:0;border-radius:8px 0 0 8px;background:#087b6e;color:#fff;font-size:11px;font-weight:700;cursor:pointer}
@media(max-width:768px){.qa-floating{right:14px;bottom:14px;width:68px;height:76px;z-index:1090}.ai-floating-button{width:48px;height:48px}.qa-collapse{left:12px}}
</style>
