<template>
  <div class="dashboard-container">
    <h1 class="dashboard-title">{{ t('dashboard.title') }}</h1>
    <p class="dashboard-subtitle">{{ t('dashboard.welcome', { name: userName }) }}</p>

    <div class="dashboard-sections">
      <section class="dashboard-section">
        <h2 class="section-title">{{ t('dashboard.section.main') }}</h2>
        <div class="menu-grid">
          <RouterLink v-if="canShowResource('orders')" to="/orders/menu" class="menu-card">
            <div class="menu-icon">📋</div>
            <div class="menu-label">{{ t('dashboard.menu.orders') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('production')" to="/production/menu" class="menu-card">
            <div class="menu-icon">🏭</div>
            <div class="menu-label">{{ t('dashboard.menu.production') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('purchase')" to="/purchase/menu" class="menu-card">
            <div class="menu-icon">🛒</div>
            <div class="menu-label">{{ t('dashboard.menu.purchase') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('shipping')" to="/shipping/menu" class="menu-card">
            <div class="menu-icon">🚚</div>
            <div class="menu-label">{{ t('dashboard.menu.shipping') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('inventory')" to="/inventory" class="menu-card">
            <div class="menu-icon">📦</div>
            <div class="menu-label">{{ t('dashboard.menu.inventory') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('quality')" to="/quality" class="menu-card">
            <div class="menu-icon">✅</div>
            <div class="menu-label">{{ t('dashboard.menu.quality') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('masters')" to="/masters" class="menu-card">
            <div class="menu-icon">⚙️</div>
            <div class="menu-label">{{ t('dashboard.menu.masters') }}</div>
          </RouterLink>
          <RouterLink v-if="canShowResource('notifications')" to="/notifications/sources" class="menu-card">
            <div class="menu-icon">🔔</div>
            <div class="menu-label">{{ t('dashboard.menu.notifications') }}</div>
          </RouterLink>
          <RouterLink to="/overtime/menu" class="menu-card">
            <div class="menu-icon">⏰</div>
            <div class="menu-label">{{ t('dashboard.menu.overtime') }}</div>
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { authState, ensureAuth } from '@/auth'
import { hasPermission } from '@/router'
import { t } from '@/i18n'

const user = authState.user
const canShowResource = (resource) => {
  if (hasPermission(user, resource)) return true
  const permissions = Array.isArray(user?.effective_permissions) ? user.effective_permissions : []
  const prefix = `${resource}.`
  return permissions.some((item) => {
    if (!item || typeof item.resource !== 'string') return false
    if (!item.resource.startsWith(prefix)) return false
    return Boolean(item.can_view || item.can_edit)
  })
}

const userName = computed(() => {
  const current = authState.user
  if (!current) return t('nav.guest')
  const fullName = `${current.last_name || ''} ${current.first_name || ''}`.trim()
  return fullName || current.username || current.email || t('nav.user')
})

onMounted(() => {
  ensureAuth()
})
</script>

<style scoped>
.dashboard-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-title {
  font-size: 28px;
  font-weight: 700;
  color: #1a2e44;
  margin: 0 0 32px;
  text-align: center;
}

.dashboard-sections {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.dashboard-section {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #344054;
  margin: 0 0 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #52b788;
}

.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.menu-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  background: #f8f9fa;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  text-decoration: none;
  color: #344054;
  transition: all 0.2s;
  cursor: pointer;
  min-height: 120px;
}

.menu-card:hover {
  background: #e8f5f0;
  border-color: #52b788;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(82, 183, 136, 0.15);
}

.menu-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.menu-label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }

  .dashboard-title {
    font-size: 24px;
    margin-bottom: 24px;
  }

  .dashboard-section {
    padding: 16px;
  }

  .section-title {
    font-size: 16px;
  }

  .menu-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
  }

  .menu-card {
    padding: 16px 12px;
    min-height: 100px;
  }

  .menu-icon {
    font-size: 28px;
    margin-bottom: 8px;
  }

  .menu-label {
    font-size: 12px;
  }
}
</style>

