<template>
  <div class="overtime-menu">
    <h1 class="page-title">勤務管理 <DataSourceDialog title="勤務管理" :sources="dsSources" /></h1>
    <div class="menu-grid">
      <RouterLink to="/overtime/apply" class="menu-card">
        <div class="menu-icon">📝</div>
        <div class="menu-label">残業申請</div>
        <div class="menu-desc">時間外・休日出勤を申請する</div>
      </RouterLink>
      <RouterLink to="/overtime/my" class="menu-card">
        <div class="menu-icon">📋</div>
        <div class="menu-label">自分の申請</div>
        <div class="menu-desc">自分の申請状況を確認する</div>
      </RouterLink>
      <RouterLink v-if="isApprover" to="/overtime/list" class="menu-card approver-card">
        <div class="menu-icon">📑</div>
        <div class="menu-label">申請一覧</div>
        <div class="menu-desc">全員の申請履歴を確認する</div>
      </RouterLink>
      <RouterLink v-if="isApprover" to="/overtime/approvals" class="menu-card approver-card">
        <div class="menu-icon">✅</div>
        <div class="menu-label">承認待ち一覧</div>
        <div class="menu-desc">承認が必要な申請を確認する</div>
        <span v-if="pendingCount" class="badge">{{ pendingCount }}</span>
      </RouterLink>
      <RouterLink v-if="isApprover" to="/overtime/stats" class="menu-card stats-card">
        <div class="menu-icon">📊</div>
        <div class="menu-label">月次統計</div>
        <div class="menu-desc">メンバーの月次労働時間を確認する</div>
      </RouterLink>
      <RouterLink v-if="isApprover" to="/overtime/productivity-stats" class="menu-card productivity-card">
        <div class="menu-icon">🏭</div>
        <div class="menu-label">加工費集計</div>
        <div class="menu-desc">日別と期間集計で加工費を確認する</div>
      </RouterLink>
      <RouterLink to="/shifts/my-line" class="menu-card shift-card">
        <div class="menu-icon">📅</div>
        <div class="menu-label">シフト確認</div>
        <div class="menu-desc">自分と同じラインのシフトを確認する</div>
      </RouterLink>
      <RouterLink v-if="isShiftManager" to="/shifts/chart" class="menu-card shift-card">
        <div class="menu-icon">🗓️</div>
        <div class="menu-label">シフトチャート管理</div>
        <div class="menu-desc">ライン別のシフト配置を管理する</div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { authState } from '@/auth'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { section: '残業・休暇申請' },
  { op: '読み書き', table: 't_overtime_application', desc: '残業・休暇申請の登録、一覧・統計表示' },
  { op: '読み書き', table: 't_overtime_approval_log', desc: '承認待ち件数・承認履歴の登録と表示' },
  { op: '読み書き', table: 'notifications', desc: '申請・承認に伴う通知の登録' },
  { section: '組織・利用者' },
  { op: '読み取り', table: 'auth_user', desc: '申請者・承認者・作業者の表示' },
  { op: '読み取り', table: 'accounts_userprofile', desc: '役割・所属・担当組織の判定' },
  { op: '読み取り', table: 'accounts_department', desc: '班・グループなど所属組織の表示と絞り込み' },
  { section: 'シフトチャート' },
  { op: '読み書き', table: 'shifts_shiftline', desc: '勤務ラインの管理' },
  { op: '読み書き', table: 'shifts_shiftworker', desc: 'ライン別作業者の管理' },
  { op: '読み書き', table: 'shifts_shiftlineprocess', desc: 'ライン別工程・活動設定の管理' },
  { op: '読み書き', table: 'shifts_shiftassignment', desc: 'シフト配置の登録・更新・削除' },
  { op: '読み取り', table: 'm_process / m_line', desc: '工程・生産ラインの表示' },
  { op: '読み取り', table: 't_line_gantt_plan', desc: '工程別負荷時間の集計表示' },
]

const pendingCount = ref(0)

const isApprover = computed(() => {
  const role = authState.user?.profile?.role
  return ['leader', 'supervisor', 'chief', 'manager'].includes(role)
})

const isShiftManager = computed(() => {
  const user = authState.user
  return Boolean(user?.is_staff || user?.is_superuser || isApprover.value)
})

onMounted(async () => {
  if (isApprover.value) {
    try {
      const res = await api.overtime.getPendingApprovals()
      pendingCount.value = (res.data || []).length
    } catch (e) {
      // ignore
    }
  }
})
</script>

<style scoped>
.overtime-menu {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1f2a44;
  margin-bottom: 24px;
}
.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
.menu-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 20px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  text-decoration: none;
  color: #1f2a44;
  transition: all 0.2s;
  cursor: pointer;
}
.menu-card:hover {
  border-color: #40916c;
  box-shadow: 0 4px 12px rgba(64, 145, 108, 0.15);
  transform: translateY(-2px);
}
.approver-card {
  border-color: #3b82f6;
}
.approver-card:hover {
  border-color: #1d4ed8;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}
.stats-card {
  border-color: #8b5cf6;
}
.stats-card:hover {
  border-color: #6d28d9;
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15);
}
.productivity-card {
  border-color: #0891b2;
}
.productivity-card:hover {
  border-color: #0e7490;
  box-shadow: 0 4px 12px rgba(8, 145, 178, 0.15);
}
.shift-card {
  border-color: #17365d;
}
.shift-card:hover {
  border-color: #0f2440;
  box-shadow: 0 4px 12px rgba(23, 54, 93, 0.15);
}
.menu-icon {
  font-size: 40px;
  margin-bottom: 12px;
}
.menu-label {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 6px;
}
.menu-desc {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
}
.badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: #ef4444;
  color: white;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 700;
}
</style>

