import { ref, computed } from 'vue'
import { authState } from './auth'
import api from '@/api/client'

// グローバル状態
const notifications = ref([])
const departments = ref([])
const previousNotificationIds = ref(new Set())
let pollingInterval = null
const POLLING_INTERVAL_MS = 30000 // 30秒

// ヘルパー関数
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

// アクティブな通知（有効期間内 & 対象者）
const activeNotifications = computed(() => {
  const user = authState.user
  if (!user) return []

  const userId = user.id
  const userDivisionId = user?.profile?.division_id ?? user?.profile?.division ?? null
  const userGroupId = user?.profile?.group_id ?? user?.profile?.group ?? null
  const userTeamId = user?.profile?.team_id ?? user?.profile?.team ?? null
  const userPosition = user?.profile?.position || ''

  const parseLocalDate = (val) => {
    if (!val) return null
    // 'YYYY-MM-DD' をローカル日付として解釈（UTC扱いによる9時間ズレを防ぐ）
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(val))
    if (m) {
      return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
    }
    const d = new Date(val)
    return Number.isNaN(d.getTime()) ? null : d
  }

  const today = new Date()
  const todayYmd = new Date(today.getFullYear(), today.getMonth(), today.getDate())

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
      division: userDivisionId,
      group: userGroupId,
      team: userTeamId,
    })) return false
    if (!matchesPositionTarget(targetPositions, userPosition)) return false
    return true
  })
})

// 未読の通知のみ
const unreadNotifications = computed(() => {
  return activeNotifications.value.filter((item) => !item.is_read)
})

// 通知数
const notificationCount = computed(() => unreadNotifications.value.length)

// チャイム音を鳴らす
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

// 新着通知をチェック
const checkForNewNotifications = (currentIds) => {
  if (previousNotificationIds.value.size === 0) {
    previousNotificationIds.value = currentIds
    return
  }

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

// 通知を取得
const loadNotifications = async () => {
  try {
    const res = await api.notifications.list({ ordering: 'display_order,id' })
    const data = res.data?.results || res.data || []
    notifications.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('通知取得エラー:', error)
  }
}

// 部署を取得
const loadDepartments = async () => {
  try {
    const res = await api.accounts.getDepartments({ ordering: 'display_id,name' })
    const data = res.data?.results || res.data || []
    departments.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('部署一覧の取得に失敗しました:', error)
    departments.value = []
  }
}

// ポーリング実行
const pollNotifications = async () => {
  if (!authState.user) return

  try {
    await loadDepartments()
    await loadNotifications()

    const currentIds = new Set(unreadNotifications.value.map((n) => n.id))
    checkForNewNotifications(currentIds)
  } catch (error) {
    console.error('通知ポーリングエラー:', error)
  }
}

// ポーリング開始
const startPolling = () => {
  if (pollingInterval) return

  pollNotifications()
  pollingInterval = setInterval(pollNotifications, POLLING_INTERVAL_MS)
}

// ポーリング停止
const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// リセット
const resetNotificationState = () => {
  stopPolling()
  notifications.value = []
  departments.value = []
  previousNotificationIds.value = new Set()
}

// 通知を再読み込み（確認ボタン押下後など）
const refreshNotifications = async () => {
  await loadNotifications()
}

export {
  notifications,
  departments,
  activeNotifications,
  unreadNotifications,
  notificationCount,
  startPolling,
  stopPolling,
  resetNotificationState,
  refreshNotifications,
  loadNotifications,
  loadDepartments,
}
