<template>
  <nav class="global-nav">
    <div class="global-nav-left">
      <RouterLink to="/" class="global-nav-logo">
        <div class="logo-content">
          <div class="logo-top">
            <span class="logo-text">DAISO</span>
            <button v-if="!isHomePage" @click.prevent="goBack" class="back-btn">
              ◀ 戻る
            </button>
            <span v-else class="logo-subtitle">管理システム</span>
          </div>
          <div class="logo-date">{{ todayText }}</div>
        </div>
      </RouterLink>
    </div>

    <div class="global-nav-center">
      <div class="nav-tabs">
        <RouterLink
          v-for="tab in displayTabs"
          :key="tab.id"
          :to="tab.link"
          class="nav-tab"
          :class="{ active: isActiveTab(tab.id) }"
        >
          {{ tab.label }}
        </RouterLink>
      </div>
    </div>

    <div class="global-nav-right">
      <div class="nav-info" v-if="!isMobile">
        <button class="lang-selector">
          <span class="globe-icon">🌐</span>
          <span>日本語</span>
          <span class="dropdown-arrow">▼</span>
        </button>
        <div class="user-info" @click="toggleUserMenu" :class="{ active: showUserMenu }">
          <span class="user-icon">👤</span>
          <span class="user-name">{{ userDisplayName }}</span>
          <span class="dropdown-arrow" :class="{ rotated: showUserMenu }">▼</span>
        </div>
        <div v-if="showUserMenu" class="user-menu">
          <RouterLink to="/settings/profile" class="user-menu-item" @click="closeUserMenu">
            <span>👤</span>
            プロフィール編集
          </RouterLink>
        </div>
      </div>
      <div class="nav-actions">
        <button class="nav-action-btn" title="お知らせ">
          <span>🔔</span>
          <span class="btn-label">お知らせ</span>
        </button>
        <button class="nav-action-btn" title="ログアウト" @click="handleLogout">
          <span>🚪</span>
          <span class="btn-label">ログアウト</span>
        </button>
        <RouterLink to="/settings" class="nav-action-btn" title="設定" v-if="!isMobile">
          <span>⚙️</span>
          <span class="btn-label">設定</span>
        </RouterLink>
      

        <button class="nav-action-btn help-btn" title="ヘルプ" @click="openHelp">
          <span>?</span>
          <span class="btn-label">ヘルプ</span>
        </button></div>
    </div>
  </nav>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { authState, logout } from '../auth'

const props = defineProps({
  isMobile: {
    type: Boolean,
    default: false,
  },
  todayText: {
    type: String,
    default: '',
  },
})

const route = useRoute()
const router = useRouter()

const isHomePage = computed(() => {
  return route.path === '/'
})

const goBack = () => {
  window.history.back()
}

const mainTabs = [
  { id: 'orders', label: '受注', link: '/orders/menu' },
  { id: 'production', label: '生産', link: '/production/menu' },
  { id: 'purchase', label: '仕入', link: '/purchase/menu' },
  { id: 'shipping', label: '出荷', link: '/shipping/menu' },
  { id: 'inventory', label: '在庫', link: '/inventory' },
  { id: 'quality', label: '品質', link: '/quality' },
  { id: 'masters', label: 'マスタ', link: '/masters' },
  { id: 'settings', label: '設定', link: '/settings' },
]

// スマホでは生産・マニュアルのみ表示
const displayTabs = computed(() => {
  if (props.isMobile) {
    return mainTabs.filter(tab => ['production', 'manual'].includes(tab.id))
  }
  return mainTabs
})

const isActiveTab = (tabId) => {
  const path = route.path
  if (tabId === 'orders' && path.startsWith('/orders')) return true
  if (tabId === 'production' && path.startsWith('/production')) return true
  if (tabId === 'purchase' && path.startsWith('/purchase')) return true
  if (tabId === 'shipping' && path.startsWith('/shipping')) return true
  if (tabId === 'inventory' && path.startsWith('/inventory')) return true
  if (tabId === 'quality' && path.startsWith('/quality')) return true
  if (tabId === 'masters' && path.startsWith('/masters')) return true
  if (tabId === 'settings' && path.startsWith('/settings')) return true
  return false
}

const manualPath = computed(() => {
  const path = route.meta?.manualPath
  if (typeof path !== 'string') return ''
  return path.trim()
})

const helpUrl = computed(() => {
  const base = '/manual'
  if (!manualPath.value) return base
  const encoded = manualPath.value
    .split('/')
    .filter(Boolean)
    .map(encodeURIComponent)
    .join('/')
  return `${base}?path=${encoded}`
})

const openHelp = () => {
  window.open(helpUrl.value, '_blank', 'noopener')
}

const userDisplayName = computed(() => {
  const user = authState.user
  if (!user) return 'ゲスト'
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim()
  return fullName || user.username || user.email || 'ユーザー'
})

const showUserMenu = ref(false)

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const handleClickOutside = (event) => {
  const userInfo = event.target.closest('.user-info')
  const userMenu = event.target.closest('.user-menu')
  if (!userInfo && !userMenu) {
    closeUserMenu()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const handleLogout = async () => {
  await logout()
  router.replace('/login')
}
</script>

<style scoped>
.global-nav {
  height: 50px;
  min-height: 50px;
  background: linear-gradient(135deg, #52b788 0%, #40916c 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 100;
  flex-shrink: 0;
}

.global-nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 200px;
}

.global-nav-logo {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: white;
}

.logo-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.logo-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.logo-subtitle {
  font-size: 13px;
  font-weight: 500;
  opacity: 0.95;
}

.back-btn {
  font-size: 12px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.logo-date {
  font-size: 11px;
  font-weight: 400;
  opacity: 0.85;
  white-space: nowrap;
}

.global-nav-center {
  flex: 1;
  display: flex;
  justify-content: center;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 16px;
  min-width: 0;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
}

.global-nav-center::-webkit-scrollbar {
  height: 4px;
}

.global-nav-center::-webkit-scrollbar-track {
  background: transparent;
}

.global-nav-center::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 2px;
}

.global-nav-center::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}

.nav-tabs {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: nowrap;
  min-width: min-content;
}

.nav-tab {
  padding: 6px 16px;
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  border-radius: 4px;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-tab:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.nav-tab.active {
  background: rgba(255, 255, 255, 0.25);
  color: white;
  font-weight: 600;
}

.global-nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 200px;
  justify-content: flex-end;
}

.nav-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.lang-selector {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: white;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.lang-selector:hover {
  background: rgba(255, 255, 255, 0.25);
}

.globe-icon {
  font-size: 14px;
}

.dropdown-arrow {
  font-size: 10px;
  opacity: 0.7;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  color: white;
  font-size: 13px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}

.user-info:hover,
.user-info.active {
  background: rgba(255, 255, 255, 0.25);
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 160px;
  z-index: 1000;
  margin-top: 4px;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  color: #333;
  text-decoration: none;
  font-size: 14px;
  transition: background 0.2s;
}

.user-menu-item:hover {
  background: #f5f5f5;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
}

.user-icon {
  font-size: 16px;
}

.user-name {
  font-weight: 500;
}

.nav-actions {
  display: flex;
  gap: 6px;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  color: white;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.nav-action-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.btn-label {
  font-size: 12px;
}

.help-btn .btn-label {
  display: none;
}

/* Mobile styles */
@media (max-width: 1024px) {
  .nav-tabs {
    gap: 2px;
  }

  .nav-tab {
    padding: 6px 12px;
    font-size: 12px;
  }

  .nav-actions .btn-label {
    display: none;
  }

  .lang-selector span:not(.globe-icon) {
    display: none;
  }
}

@media (max-width: 768px) {
  .global-nav {
    padding: 0 12px;
    height: 48px;
    min-height: 48px;
  }

  .global-nav-left {
    min-width: auto;
    flex-shrink: 0;
  }

  .logo-top {
    gap: 6px;
  }

  .logo-text {
    font-size: 18px;
  }

  .logo-subtitle {
    font-size: 11px;
  }

  .back-btn {
    font-size: 11px;
    padding: 2px 6px;
  }

  .logo-date {
    font-size: 10px;
  }

  .global-nav-center {
    flex: 1;
    justify-content: center;
    padding: 0 12px;
  }

  .nav-tabs {
    justify-content: center;
  }

  .nav-tab {
    padding: 6px 20px;
    font-size: 14px;
    font-weight: 600;
  }

  .global-nav-right {
    min-width: auto;
    gap: 8px;
    flex-shrink: 0;
  }

  .nav-actions {
    gap: 8px;
  }

  .nav-action-btn {
    padding: 6px 6px;
    background: rgba(255, 255, 255, 0.2);
  }

  .nav-action-btn .btn-label {
    display: none;
  }

  .nav-action-btn span {
    font-size: 20px;
  }
}
</style>
