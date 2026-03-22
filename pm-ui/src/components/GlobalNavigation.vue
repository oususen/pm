<template>
  <nav class="global-nav">
    <div class="global-nav-left">
      <RouterLink to="/" class="global-nav-logo">
        <div class="logo-content">
          <div class="logo-top">
            <span class="logo-text">DAISO</span>
            <button v-if="!isHomePage" @click.prevent="goBack" class="back-btn">
              ◀ {{ t('nav.back') }}
            </button>
            <span v-else class="logo-subtitle">{{ t('nav.subtitle') }}</span>
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
      <div class="nav-info">
        <div class="user-info" @click="toggleUserMenu" :class="{ active: showUserMenu }">
          <span class="user-name">{{ userDisplayName }}</span>
          <span class="dropdown-arrow" :class="{ rotated: showUserMenu }">▼</span>
        </div>
        <div v-if="showUserMenu" class="user-menu">
          <div class="user-menu-header">
            <div class="user-menu-name">{{ userDisplayName }}</div>
            <div class="user-menu-account">{{ userAccountName }}</div>
          </div>
          <div class="user-menu-divider"></div>
          <RouterLink to="/settings/profile" class="user-menu-item" @click="closeUserMenu">
            <span>👤</span>
            {{ t('nav.profile') }}
          </RouterLink>
          <div class="user-menu-item language-item">
            <span>🌐</span>
            <div class="language-select">
              <div class="language-label">{{ t('nav.language') }}</div>
              <select v-model="selectedLocale" class="language-dropdown">
                <option v-for="opt in localeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>
          </div>
          <div class="user-menu-divider"></div>
          <button class="user-menu-item logout-item" type="button" @click="handleLogout">
            <span>🚪</span>
            {{ t('nav.logout') }}
          </button>
        </div>
      </div>
      <div class="nav-actions">
        <div v-if="showNotificationBell" class="notification-wrapper" @click.stop>
          <button
            class="nav-action-btn notification-btn"
            :title="t('nav.notifications')"
            type="button"
            @mousedown.stop
            @mouseup.stop
            @click.stop.prevent="toggleNotificationMenu"
          >
            <span>🔔</span>
            <span class="btn-label">{{ t('nav.notifications') }}</span>
            <span v-if="notificationCount" class="notification-badge">{{ notificationCount }}</span>
          </button>
          <div v-if="showNotificationMenu" class="notification-menu" @click.stop @mousedown.stop>
            <div class="notification-menu-header">{{ t('nav.unreadTitle') }}</div>
            <div v-if="unreadNotifications.length" class="notification-list">
              <div v-for="item in unreadNotifications" :key="item.id" class="notification-item">
                <div class="notification-title">{{ item.title }}</div>
              </div>
            </div>
            <div v-else class="notification-empty">{{ t('nav.unreadEmpty') }}</div>
            <RouterLink
              to="/notifications"
              class="notification-link"
              @click="closeNotificationMenu"
            >
              {{ t('nav.list') }}
            </RouterLink>
          </div>
        </div>
        <RouterLink
          v-if="showTaskButton"
          to="/tasks"
          class="nav-action-btn task-btn"
          :class="{ active: isTaskPage }"
          title="タスク"
        >
          <span>📌</span>
          <span class="btn-label">タスク</span>
          <span v-if="pendingTaskCount" class="task-badge">{{ pendingTaskCount }}</span>
        </RouterLink>
        <RouterLink to="/settings" class="nav-action-btn" :title="t('nav.settings')" v-if="!isMobile">
          <span>⚙️</span>
          <span class="btn-label">{{ t('nav.settings') }}</span>
        </RouterLink>
        <button class="nav-action-btn help-btn" :title="t('nav.help')" @click="openHelp">
          <span>?</span>
          <span class="btn-label">{{ t('nav.help') }}</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { authState, logout } from '../auth'
import { hasPermission } from '../router'
import api from '@/api/client'
import { locale, t, setLocale, getLocaleOptions } from '@/i18n'

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

const mainTabs = computed(() => [
  { id: 'orders', label: t('nav.tabs.orders'), link: '/orders/menu', resource: 'orders' },
  { id: 'production', label: t('nav.tabs.production'), link: '/production/menu', resource: 'production' },
  { id: 'purchase', label: t('nav.tabs.purchase'), link: '/purchase/menu', resource: 'purchase' },
  { id: 'shipping', label: t('nav.tabs.shipping'), link: '/shipping/menu', resource: 'shipping' },
  { id: 'inventory', label: t('nav.tabs.inventory'), link: '/inventory', resource: 'inventory' },
  { id: 'quality', label: t('nav.tabs.quality'), link: '/quality', resource: 'quality' },
  { id: 'notifications', label: t('nav.tabs.notifications'), link: '/notifications/sources', resource: 'notifications' },
  { id: 'engineeringChange', label: t('nav.tabs.engineeringChange'), link: '/engineering-change/menu', resource: 'engineering_change' },
  { id: 'overtime', label: t('nav.tabs.overtime'), link: '/overtime/menu', resource: null },
  { id: 'masters', label: t('nav.tabs.masters'), link: '/masters', resource: 'masters' },
  { id: 'settings', label: t('nav.tabs.settings'), link: '/settings', resource: 'settings' },
])

const hasChildResourcePermission = (user, parentResource) => {
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  const prefix = `${parentResource}.`
  return permissions.some((item) => {
    if (!item || typeof item.resource !== 'string') return false
    if (!item.resource.startsWith(prefix)) return false
    return Boolean(item.can_view || item.can_edit)
  })
}

const canShowTabByPermission = (user, resource) => {
  if (hasPermission(user, resource, 'view')) return true
  return hasChildResourcePermission(user, resource)
}

// ユーザーの権限に基づいてタブをフィルタリング
const displayTabs = computed(() => {
  const user = authState.user
  // 権限がないタブを非表示
  let tabs = mainTabs.value.filter((tab) => canShowTabByPermission(user, tab.resource))
  // スマホでは生産・マニュアルのみ表示（権限がある場合）
  if (props.isMobile) {
    tabs = tabs.filter(tab => ['production', 'manual'].includes(tab.id))
  }
  return tabs
})

const isActiveTab = (tabId) => {
  const path = route.path
  if (tabId === 'orders' && path.startsWith('/orders')) return true
  if (tabId === 'production' && path.startsWith('/production')) return true
  if (tabId === 'purchase' && path.startsWith('/purchase')) return true
  if (tabId === 'shipping' && path.startsWith('/shipping')) return true
  if (tabId === 'inventory' && path.startsWith('/inventory')) return true
  if (tabId === 'quality' && path.startsWith('/quality')) return true
  if (tabId === 'notifications' && path.startsWith('/notifications')) return true
  if (tabId === 'engineeringChange' && path.startsWith('/engineering-change')) return true
  if (tabId === 'overtime' && path.startsWith('/overtime')) return true
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
  if (!user) return t('nav.guest')
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim()
  return fullName || user.username || user.email || t('nav.user')
})

const userAccountName = computed(() => {
  const user = authState.user
  if (!user) return ''
  return user.username || user.email || ''
})

const showUserMenu = ref(false)
const showNotificationMenu = ref(false)
const notifications = ref([])
const pendingTaskCount = ref(0)
const previousNotificationIds = ref(new Set())
const pollingInterval = ref(null)
const POLLING_INTERVAL_MS = 30000 // 30秒ごとにポーリング
const localeOptions = getLocaleOptions()
const selectedLocale = computed({
  get: () => locale.value,
  set: (value) => setLocale(value),
})

const userDepartmentId = computed(() => authState.user?.profile?.department_id ?? authState.user?.profile?.department ?? null)
const userDivisionId = computed(() => authState.user?.profile?.division_id ?? authState.user?.profile?.division ?? null)
const userGroupId = computed(() => authState.user?.profile?.group_id ?? authState.user?.profile?.group ?? null)
const userTeamId = computed(() => authState.user?.profile?.team_id ?? authState.user?.profile?.team ?? null)
const userPosition = computed(() => authState.user?.profile?.role || '')
const showTaskButton = computed(() => Boolean(authState.user))
const isTaskPage = computed(() => route.path.startsWith('/tasks'))
const canAccessNotifications = computed(() => {
  return Boolean(authState.user)
})
const showNotificationBell = computed(() => Boolean(authState.user) && canAccessNotifications.value)
const departments = ref([])

const toId = (value) => (value === null || value === undefined ? '' : String(value))

const departmentLevelMap = computed(() => {
  const map = new Map()
  departments.value.forEach((dept) => {
    map.set(toId(dept.id), dept.level)
  })
  return map
})

const getTargetLevelSets = (targetDepartments) => {
  const team = new Set()
  const group = new Set()
  const division = new Set()
  targetDepartments.forEach((deptId) => {
    const id = toId(deptId)
    const level = departmentLevelMap.value.get(id)
    if (level === 'team') team.add(id)
    if (level === 'group') group.add(id)
    if (level === 'division') division.add(id)
  })
  return { team, group, division }
}

const matchesDepartmentTarget = (targetDepartments, userLevels) => {
  if (!targetDepartments.length) return true
  const { team, group, division } = getTargetLevelSets(targetDepartments)
  const userTeam = toId(userLevels.team)
  const userGroup = toId(userLevels.group)
  const userDivision = toId(userLevels.division)
  if (team.size) return team.has(userTeam)
  if (group.size) return group.has(userGroup)
  if (division.size) return division.has(userDivision)
  return false
}

const matchesPositionTarget = (targetPositions, position) => {
  if (!targetPositions.length) return true
  if (!position) return false
  return targetPositions.some((pos) => String(pos) === String(position))
}

const matchesUserTarget = (targetUsers, userId) => {
  if (!targetUsers.length) return false
  return targetUsers.some((id) => String(id) === String(userId))
}

const activeNotifications = computed(() => {
  const parseLocalDate = (value) => {
    if (!value) return null
    const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value))
    if (matched) {
      return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]))
    }
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return null
    return parsed
  }

  const now = new Date()
  const todayYmd = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const userId = authState.user?.id
  return notifications.value.filter((item) => {
    if (!item) return false
    const from = parseLocalDate(item.valid_from)
    const to = parseLocalDate(item.valid_to)
    if (from && todayYmd < from) return false
    if (to && todayYmd > to) return false
    const targetDepartments = Array.isArray(item.target_departments) ? item.target_departments : []
    const targetPositions = Array.isArray(item.target_positions) ? item.target_positions : []
    const targetUsers = Array.isArray(item.target_users) ? item.target_users : []

    const hasTargetUsers = targetUsers.length > 0
    if (hasTargetUsers && !matchesUserTarget(targetUsers, userId)) return false

    // 部署・役職・ユーザーが未指定の場合は全員対象
    if (!targetDepartments.length && !targetPositions.length && !targetUsers.length) return true

    // 部署・役職でのマッチ判定
    if (!matchesDepartmentTarget(targetDepartments, {
      division: userDivisionId.value,
      group: userGroupId.value,
      team: userTeamId.value,
    })) return false
    if (!matchesPositionTarget(targetPositions, userPosition.value)) return false
    return true
  })
})

// 未読の通知のみ
const unreadNotifications = computed(() => {
  return activeNotifications.value.filter((item) => !item.is_read)
})

const notificationCount = computed(() => unreadNotifications.value.length)

const loadNotifications = async () => {
  if (!canAccessNotifications.value) {
    notifications.value = []
    return
  }
  try {
    const res = await api.notifications.list({ ordering: 'display_order,id' })
    const data = res.data?.results || res.data || []
    notifications.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('通知取得エラー:', error)
  }
}

const loadPendingTaskCount = async () => {
  if (!authState.user) {
    pendingTaskCount.value = 0
    return
  }
  try {
    const [purchaseResponse, qualityResponse] = await Promise.all([
      api.purchaseOrderProposals.listTasks({
        assigned_to_me: true,
        status: 'PENDING',
      }),
      api.qualityEquipmentInspections.listTasks({
        assigned_to_me: true,
        status: 'PENDING',
      }),
    ])
    const purchaseRows = Array.isArray(purchaseResponse.data) ? purchaseResponse.data : []
    const qualityRows = Array.isArray(qualityResponse.data) ? qualityResponse.data : []
    pendingTaskCount.value = purchaseRows.length + qualityRows.length
  } catch (error) {
    console.error('タスク件数の取得に失敗しました:', error)
    pendingTaskCount.value = 0
  }
}

const loadDepartments = async () => {
  if (!canAccessNotifications.value) {
    departments.value = []
    return
  }
  try {
    const res = await api.accounts.getDepartments({ ordering: 'display_id,name' })
    const data = res.data?.results || res.data || []
    departments.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('部署一覧の取得に失敗しました:', error)
    departments.value = []
  }
}

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
  if (showUserMenu.value) {
    showNotificationMenu.value = false
  }
}

const closeUserMenu = () => {
  showUserMenu.value = false
}

const toggleNotificationMenu = async () => {
  showNotificationMenu.value = !showNotificationMenu.value
  if (showNotificationMenu.value) {
    showUserMenu.value = false
    await loadDepartments()
    await loadNotifications()
  }
}

const closeNotificationMenu = () => {
  showNotificationMenu.value = false
}

// チャイム音を鳴らす（Web Audio API使用）
const playChimeSound = () => {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const frequencies = [523.25, 659.25, 783.99] // ド・ミ・ソ

    frequencies.forEach((freq, index) => {
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()

      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)

      oscillator.frequency.value = freq
      oscillator.type = 'sine'

      const startTime = audioContext.currentTime + index * 0.15
      const duration = 0.3

      gainNode.gain.setValueAtTime(0, startTime)
      gainNode.gain.linearRampToValueAtTime(0.3, startTime + 0.05)
      gainNode.gain.linearRampToValueAtTime(0, startTime + duration)

      oscillator.start(startTime)
      oscillator.stop(startTime + duration)
    })
  } catch (error) {
    console.error('チャイム音の再生に失敗しました:', error)
  }
}

// 新着通知をチェックしてチャイム音を鳴らす
const checkForNewNotifications = (currentIds) => {
  if (previousNotificationIds.value.size === 0) {
    // 初回読み込み時は音を鳴らさない
    previousNotificationIds.value = currentIds
    return
  }

  // 新しい通知があるかチェック
  let hasNew = false
  currentIds.forEach((id) => {
    if (!previousNotificationIds.value.has(id)) {
      hasNew = true
    }
  })

  if (hasNew) {
    playChimeSound()
  }

  previousNotificationIds.value = currentIds
}

// ポーリングで通知を取得
const pollNotifications = async () => {
  if (!authState.user) return

  try {
    if (canAccessNotifications.value) {
      await loadDepartments()
      await loadNotifications()
    } else {
      notifications.value = []
    }
    await loadPendingTaskCount()

    // 未読通知のIDセットを作成（未読ベースで新着検出）
    const currentIds = new Set(unreadNotifications.value.map((n) => n.id))
    checkForNewNotifications(currentIds)
  } catch (error) {
    console.error('通知ポーリングエラー:', error)
  }
}

// ポーリング開始
const startPolling = () => {
  if (!authState.user) return
  if (pollingInterval.value) return

  // 初回実行
  pollNotifications()

  // 定期実行
  pollingInterval.value = setInterval(pollNotifications, POLLING_INTERVAL_MS)
}

// ポーリング停止
const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

const handleClickOutside = (event) => {
  const userInfo = event.target.closest('.user-info')
  const userMenu = event.target.closest('.user-menu')
  const notificationWrapper = event.target.closest('.notification-wrapper')
  const notificationMenu = event.target.closest('.notification-menu')
  if (!userInfo && !userMenu) {
    closeUserMenu()
  }
  if (!notificationWrapper && !notificationMenu) {
    closeNotificationMenu()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  // ログイン済みならポーリング開始
  if (authState.user) {
    startPolling()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  stopPolling()
})

// ユーザーのログイン状態を監視してポーリングを制御
watch(
  () => authState.user,
  (newUser) => {
    if (newUser) {
      startPolling()
    } else {
      stopPolling()
      notifications.value = []
      pendingTaskCount.value = 0
      previousNotificationIds.value = new Set()
    }
  }
)

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
  padding: 6px 10px;
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
  padding: 4px 6px;
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
  padding: 6px 0;
}

.user-menu-header {
  padding: 10px 12px 6px 12px;
}

.user-menu-name {
  font-size: 14px;
  font-weight: 700;
  color: #1f2a44;
}

.user-menu-account {
  font-size: 12px;
  color: #64748b;
}

.user-menu-divider {
  height: 1px;
  background: #e5e7eb;
  margin: 6px 0;
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
  width: 100%;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.language-item {
  align-items: flex-start;
}

.language-select {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.language-label {
  font-size: 12px;
  color: #64748b;
}

.language-dropdown {
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 4px 6px;
  font-size: 12px;
  background: #fff;
  width: 100%;
}

.user-menu-item:hover {
  background: #f5f5f5;
}

.dropdown-arrow.rotated {
  transform: rotate(180deg);
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
  padding: 4px 4px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}
.help-btn {
  padding: 4px 6px;
}

.notification-wrapper {
  position: relative;
}

.notification-badge {
  background: #ef4444;
  color: #fff;
  border-radius: 999px;
  padding: 0 6px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 700;
}

.task-badge {
  background: #ef4444;
  color: #fff;
  border-radius: 999px;
  padding: 0 6px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 700;
}

.notification-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  background: #fff;
  border-radius: 6px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
  min-width: 260px;
  z-index: 1000;
  padding: 8px 0;
}

.notification-menu-header {
  font-size: 13px;
  font-weight: 700;
  color: #1f2a44;
  padding: 6px 12px;
}

.notification-list {
  max-height: 280px;
  overflow-y: auto;
}

.notification-item {
  padding: 8px 12px;
  border-top: 1px solid #f1f5f9;
}

.notification-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f2a44;
}

.notification-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

.notification-range {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

.notification-empty {
  padding: 12px;
  font-size: 12px;
  color: #94a3b8;
}

.notification-link {
  display: block;
  padding: 8px 12px;
  font-size: 12px;
  color: #2563eb;
  text-decoration: none;
}

.nav-action-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.nav-action-btn.active {
  background: rgba(255, 255, 255, 0.35);
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
    padding: 6px 8px;
    font-size: 12px;
  }

  .nav-actions .btn-label {
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
    padding: 6px 12px;
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
    padding: 6px 4px;
    background: rgba(255, 255, 255, 0.2);
  }

  .help-btn {
    padding: 6px 6px;
  }

  .nav-action-btn .btn-label {
    display: none;
  }

  .nav-action-btn span {
    font-size: 20px;
  }

  .user-name {
    max-width: 120px;
  }
}
</style>
