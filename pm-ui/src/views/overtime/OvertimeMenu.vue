<template>
  <div class="overtime-menu">
    <h1 class="page-title">勤務管理</h1>
    <div class="menu-grid">
      <RouterLink to="/overtime/apply" class="menu-card">
        <div class="menu-icon">📝</div>
        <div class="menu-label">残業申請</div>
        <div class="menu-desc">時間外・休日出勤を申請する</div>
      </RouterLink>
      <RouterLink to="/overtime/list" class="menu-card">
        <div class="menu-icon">📋</div>
        <div class="menu-label">申請一覧</div>
        <div class="menu-desc">自分の申請履歴を確認する</div>
      </RouterLink>
      <RouterLink v-if="isApprover" to="/overtime/approvals" class="menu-card approver-card">
        <div class="menu-icon">✅</div>
        <div class="menu-label">承認待ち一覧</div>
        <div class="menu-desc">承認が必要な申請を確認する</div>
        <span v-if="pendingCount" class="badge">{{ pendingCount }}</span>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { authState } from '@/auth'
import api from '@/api/client'

const pendingCount = ref(0)

const isApprover = computed(() => {
  const role = authState.user?.profile?.role
  return ['supervisor', 'chief', 'manager'].includes(role)
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
