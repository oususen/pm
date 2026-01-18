<template>
  <div class="dashboard-container">
    <h1 class="dashboard-title">DAISO 管理システム</h1>
    <p class="dashboard-subtitle">ようこそ、{{ userName }}さん</p>

    <div class="dashboard-sections">
      <section class="dashboard-section">
        <h2 class="section-title">主要機能</h2>
        <div class="menu-grid">
          <RouterLink v-if="hasPermission(user, 'orders')" to="/orders/menu" class="menu-card">
            <div class="menu-icon">📋</div>
            <div class="menu-label">受注管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'production')" to="/production/menu" class="menu-card">
            <div class="menu-icon">🏭</div>
            <div class="menu-label">生産管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'purchase')" to="/purchase/menu" class="menu-card">
            <div class="menu-icon">🛒</div>
            <div class="menu-label">仕入管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'shipping')" to="/shipping/menu" class="menu-card">
            <div class="menu-icon">🚚</div>
            <div class="menu-label">出荷管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'inventory')" to="/inventory" class="menu-card">
            <div class="menu-icon">📦</div>
            <div class="menu-label">在庫管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'quality')" to="/quality" class="menu-card">
            <div class="menu-icon">✅</div>
            <div class="menu-label">品質管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'masters')" to="/masters" class="menu-card">
            <div class="menu-icon">⚙️</div>
            <div class="menu-label">マスタ管理</div>
          </RouterLink>
          <RouterLink v-if="hasPermission(user, 'notifications')" to="/notifications/sources" class="menu-card">
            <div class="menu-icon">🔔</div>
            <div class="menu-label">通知作成</div>
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { RouterLink } from 'vue-router'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const user = authState.user
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
