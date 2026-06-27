<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">権限テンプレート</h2>
      <div class="page-actions">
        <button class="btn" @click="refreshAll" :disabled="loading || !canViewPage">
          更新
        </button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="!canViewPage" class="helper-text">
        この画面を開く権限がありません。
      </div>
      <template v-else>
      <div class="template-tabs" role="tablist" aria-label="権限テンプレート種別">
        <button
          type="button"
          class="template-tab"
          :class="{ active: activeTab === 'departmentPosition' }"
          @click="activeTab = 'departmentPosition'"
        >
          部署・役職
        </button>
        <button
          type="button"
          class="template-tab"
          :class="{ active: activeTab === 'department' }"
          @click="activeTab = 'department'"
        >
          部署
        </button>
        <button
          type="button"
          class="template-tab"
          :class="{ active: activeTab === 'position' }"
          @click="activeTab = 'position'"
        >
          役職
        </button>
        <button
          type="button"
          class="template-tab"
          :class="{ active: activeTab === 'userOverrides' }"
          @click="openUserOverridesTab"
        >
          個別権限ユーザー一覧
        </button>
        <button
          type="button"
          class="template-tab"
          :class="{ active: activeTab === 'configuredTemplates' }"
          @click="openConfiguredTemplatesTab"
        >
          設定済みテンプレ一覧
        </button>
      </div>

      <div v-show="activeTab === 'departmentPosition'" class="template-card">
        <div class="template-sticky-header">
          <div class="template-header">
            <h3 class="section-title">部署・役職 権限テンプレート</h3>
            <div class="template-header-actions">
              <div v-if="templateSuccess" class="save-message success">
                {{ templateSuccess }}
              </div>
              <button
                type="button"
                class="btn"
                @click="clearTemplatePermissions"
                :disabled="templateSaving || !selectedPositionName || !canEditPage"
              >
                一括外す
              </button>
              <button type="button" class="btn primary" @click="saveTemplate" :disabled="templateSaving || !canEditPage">
                {{ templateSaving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>

          <div class="template-controls">
            <div class="template-select">
              <label>部署選択</label>
              <select v-model="selectedDepartmentId" @change="onDepartmentChange">
                <option :value="null">選択してください</option>
                <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                  {{ dept.label }}
                </option>
              </select>
            </div>
            <div class="template-select">
              <label>役割選択</label>
              <select
                v-model="selectedPositionName"
                :disabled="!selectedDepartmentId"
                @change="loadTemplate"
              >
                <option value="">選択してください</option>
                <option v-for="r in ROLE_CHOICES" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="templateError" class="alert alert-danger">
          {{ templateError }}
        </div>

        <div v-if="templateLoading" class="helper-text">読み込み中...</div>

        <div v-else class="permission-table-wrap">
          <table class="permission-table">
            <thead>
              <tr>
                <th>機能</th>
                <th>閲覧</th>
                <th>編集</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="perm in templatePermissions" :key="perm.resource">
                <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_view"
                    @change="onPermissionChange(perm, 'can_view')"
                    :disabled="!selectedPositionName || !canEditPage"
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_edit"
                    @change="onPermissionChange(perm, 'can_edit')"
                    :disabled="!selectedPositionName || !canEditPage"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <div v-show="activeTab === 'department'" class="template-card">
        <div class="template-sticky-header">
          <div class="template-header">
            <h3 class="section-title">部署 権限テンプレート</h3>
            <div class="template-header-actions">
              <div v-if="departmentTemplateSuccess" class="save-message success">
                {{ departmentTemplateSuccess }}
              </div>
              <button
                type="button"
                class="btn"
                @click="clearDepartmentTemplatePermissions"
                :disabled="departmentTemplateSaving || !selectedDepartmentOnlyId || !canEditPage"
              >
                一括外す
              </button>
              <button type="button" class="btn primary" @click="saveDepartmentTemplate" :disabled="departmentTemplateSaving || !canEditPage">
                {{ departmentTemplateSaving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>

          <div class="template-controls">
            <div class="template-select">
              <label>部署選択</label>
              <select v-model="selectedDepartmentOnlyId" @change="loadDepartmentTemplate">
                <option :value="null">選択してください</option>
                <option v-for="dept in departmentOptions" :key="dept.value" :value="dept.value">
                  {{ dept.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="departmentTemplateError" class="alert alert-danger">
          {{ departmentTemplateError }}
        </div>

        <div v-if="departmentTemplateLoading" class="helper-text">読み込み中...</div>

        <div v-else class="permission-table-wrap">
          <table class="permission-table">
            <thead>
              <tr>
                <th>機能</th>
                <th>閲覧</th>
                <th>編集</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="perm in departmentTemplatePermissions" :key="perm.resource">
                <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_view"
                    @change="onDepartmentPermissionChange(perm, 'can_view')"
                    :disabled="!selectedDepartmentOnlyId || !canEditPage"
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_edit"
                    @change="onDepartmentPermissionChange(perm, 'can_edit')"
                    :disabled="!selectedDepartmentOnlyId || !canEditPage"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <div v-show="activeTab === 'position'" class="template-card">
        <div class="template-sticky-header">
          <div class="template-header">
            <h3 class="section-title">役職 権限テンプレート</h3>
            <div class="template-header-actions">
              <div v-if="positionTemplateSuccess" class="save-message success">
                {{ positionTemplateSuccess }}
              </div>
              <button
                type="button"
                class="btn"
                @click="clearPositionTemplatePermissions"
                :disabled="positionTemplateSaving || !selectedPositionOnlyName || !canEditPage"
              >
                一括外す
              </button>
              <button type="button" class="btn primary" @click="savePositionTemplate" :disabled="positionTemplateSaving || !canEditPage">
                {{ positionTemplateSaving ? '保存中...' : '保存' }}
              </button>
            </div>
          </div>

          <div class="template-controls">
            <div class="template-select">
              <label>役割選択</label>
              <select v-model="selectedPositionOnlyName" @change="loadPositionTemplate">
                <option value="">選択してください</option>
                <option v-for="r in ROLE_CHOICES" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="positionTemplateError" class="alert alert-danger">
          {{ positionTemplateError }}
        </div>

        <div v-if="positionTemplateLoading" class="helper-text">読み込み中...</div>

        <div v-else class="permission-table-wrap">
          <table class="permission-table">
            <thead>
              <tr>
                <th>機能</th>
                <th>閲覧</th>
                <th>編集</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="perm in positionTemplatePermissions" :key="perm.resource">
                <td :class="getPermissionCellClass(perm)">{{ getPermissionLabel(perm.resource) }}</td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_view"
                    @change="onPositionPermissionChange(perm, 'can_view')"
                    :disabled="!selectedPositionOnlyName || !canEditPage"
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    v-model="perm.can_edit"
                    @change="onPositionPermissionChange(perm, 'can_edit')"
                    :disabled="!selectedPositionOnlyName || !canEditPage"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <div v-show="activeTab === 'userOverrides'" class="template-card">
        <div class="template-sticky-header">
          <div class="template-header">
            <h3 class="section-title">個別権限ユーザー一覧</h3>
            <div class="template-header-actions">
              <button
                type="button"
                class="btn"
                @click="loadUserOverrides"
                :disabled="userOverrideLoading || !canViewPage"
              >
                更新
              </button>
            </div>
          </div>
          <div class="helper-text">
            テンプレートではなく、ユーザー個別権限を1件以上持つユーザーのみ表示します。
          </div>
        </div>

        <div v-if="userOverrideError" class="alert alert-danger">
          {{ userOverrideError }}
        </div>

        <div v-if="userOverrideLoading" class="helper-text">読み込み中...</div>

        <div v-else-if="!userOverrideUsers.length" class="helper-text">
          個別権限ユーザーはいません。
        </div>

        <div v-else class="permission-table-wrap">
          <table class="permission-table">
            <thead>
              <tr>
                <th>ユーザー名</th>
                <th>氏名</th>
                <th>事業部</th>
                <th>役割</th>
                <th>個別権限数</th>
                <th>個別権限</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in userOverrideUsers" :key="user.id">
                <td>{{ user.username || '-' }}</td>
                <td>{{ getUserDisplayName(user) }}</td>
                <td>{{ user.profile?.division_name || user.profile?.department_name || '-' }}</td>
                <td>{{ getRoleLabel(user.profile?.role) }}</td>
                <td>{{ user.permissions.length }}</td>
                <td class="override-resources-cell">
                  {{ formatUserPermissions(user.permissions) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-show="activeTab === 'configuredTemplates'" class="template-card">
        <div class="template-sticky-header">
          <div class="template-header">
            <h3 class="section-title">設定済みテンプレ一覧</h3>
            <div class="template-header-actions">
              <button
                type="button"
                class="btn"
                @click="loadConfiguredTemplates"
                :disabled="configuredTemplateLoading || !canViewPage"
              >
                更新
              </button>
            </div>
          </div>
          <div class="helper-text">
            権限が1件以上設定されている 部署・役職 / 部署 / 役職 のみ表示します。
          </div>
        </div>

        <div v-if="configuredTemplateError" class="alert alert-danger">
          {{ configuredTemplateError }}
        </div>

        <div v-if="configuredTemplateLoading" class="helper-text">読み込み中...</div>

        <div v-else-if="!configuredTemplateRows.length" class="helper-text">
          設定済みテンプレートはありません。
        </div>

        <div v-else class="permission-table-wrap">
          <table class="permission-table">
            <thead>
              <tr>
                <th>種別</th>
                <th>部署</th>
                <th>役割</th>
                <th>設定件数</th>
                <th>設定権限</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in configuredTemplateRows" :key="row.key">
                <td>{{ row.typeLabel }}</td>
                <td>{{ row.departmentName }}</td>
                <td>{{ row.positionName }}</td>
                <td>{{ row.permissionCount }}</td>
                <td class="override-resources-cell">{{ row.permissionLabels }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const ROLE_CHOICES = [
  { value: 'manager', label: '事業部長・課長' },
  { value: 'chief', label: '係長' },
  { value: 'supervisor', label: '班長' },
  { value: 'leader', label: 'リーダー' },
  { value: 'office_staff', label: '事務員' },
  { value: 'staff', label: '一般' },
]

const loading = ref(false)
const activeTab = ref('departmentPosition')
const templateLoading = ref(false)
const templateSaving = ref(false)
const templateError = ref('')
const templateSuccess = ref('')

const departments = ref([])
const selectedDepartmentId = ref(null)
const selectedPositionName = ref('')
const templatePermissions = ref([])

const positionTemplateLoading = ref(false)
const positionTemplateSaving = ref(false)
const positionTemplateError = ref('')
const positionTemplateSuccess = ref('')
const selectedPositionOnlyName = ref('')
const positionTemplatePermissions = ref([])
const userOverrideLoading = ref(false)
const userOverrideError = ref('')
const userOverrideUsers = ref([])
const configuredTemplateLoading = ref(false)
const configuredTemplateError = ref('')
const configuredTemplateRows = ref([])

const departmentTemplateLoading = ref(false)
const departmentTemplateSaving = ref(false)
const departmentTemplateError = ref('')
const departmentTemplateSuccess = ref('')
const selectedDepartmentOnlyId = ref(null)
const departmentTemplatePermissions = ref([])

  const permissionResources = [
    { value: 'dashboard', label: 'ダッシュボード' },
    { value: 'orders', label: '受注' },
  { value: 'orders.list', label: '受注: 受注一覧' },
  { value: 'orders.csv_import', label: '受注: 受注取込' },
  { value: 'orders.kubota_analysis', label: '受注: クボタ内示変化推移分析' },
  { value: 'orders.line_expand', label: '受注: ライン展開' },
  { value: 'production', label: '生産' },
  { value: 'production.process_input', label: '生産: 工程作業入力' },
  { value: 'production.record_inquiry', label: '生産: 生産実績照会' },
  { value: 'production.record_edit', label: '生産: 実績変更' },
  { value: 'production.scrap_record', label: '生産: 仕損品記録' },
  { value: 'production.plan_input', label: '生産: 生産計画入力' },
  { value: 'production.inventory', label: '生産: 在庫/残量一覧' },
  { value: 'production.progress', label: '生産: 進度のみ' },
  { value: 'production.scrap_history', label: '生産: 仕損履歴' },
  { value: 'production.line_calendars', label: '生産: ライン勤務カレンダ' },
  { value: 'production.line_monitor', label: '生産: ライン稼働監視' },
  { value: 'purchase', label: '仕入' },
  { value: 'purchase.plan_input', label: '仕入: 仕入れ計画' },
  { value: 'purchase.inventory', label: '仕入: 在庫/残量' },
  { value: 'purchase.progress', label: '仕入: 仕入れ進度' },
  { value: 'purchase.receiving', label: '仕入: 仕入れ検収' },
  { value: 'purchase.actual_input', label: '仕入: 仕入れ実績入力' },
  { value: 'purchase.actual_edit', label: '仕入: 納入実績編集' },
  { value: 'purchase.actual_inquiry', label: '仕入: 納入実績照会' },
  { value: 'purchase.supplier_calendar', label: '仕入: 仕入れ先カレンダ' },
  { value: 'purchase.supplier_order_pattern', label: '仕入: 納入パターン設定' },
  { value: 'purchase.delivery_schedule', label: '仕入: 納入予定' },
  { value: 'purchase.order_proposals', label: '仕入: 発注業務' },
  { value: 'purchase.auto_delivery_list', label: '仕入: 自動納入リスト送信' },
  { value: 'shipping', label: '出荷' },
  { value: 'shipping.instruction', label: '出荷: 出荷指示' },
  { value: 'shipping.actual', label: '出荷: 出荷実績' },
  { value: 'shipping.progress', label: '出荷: 出荷進度照会' },
  { value: 'shipping.order_document', label: '出荷: 出荷指示書' },
  { value: 'shipping.hirakata_pickup', label: '出荷: 枚方集荷依頼書' },
  { value: 'shipping.fujishoji_document', label: '出荷: 富士商事出荷指示書' },
  { value: 'shipping.kubota_sakai_due_adjustment', label: '出荷: クボタ堺納期調整' },
  { value: 'shipping.kubota_sakai_trip_planning', label: '出荷: クボタ堺便計画' },
  { value: 'shipping.trip_execution', label: '出荷: 便確認（実行）' },
  { value: 'shipping.trip_progress', label: '出荷: 便確認（業務員）' },
  { value: 'shipping.trip_progress_summary', label: '出荷: 便進捗確認（一覧）' },
  { value: 'inventory', label: '在庫' },
  { value: 'stocktake', label: '在庫: 棚卸入力' },
  { value: 'stocktake.delete', label: '在庫: 棚卸履歴削除' },
    { value: 'quality', label: '品質' },
    { value: 'quality.equipment_inspection_master', label: '品質: 設備点検表（点検項目作成）' },
    { value: 'quality.equipment_inspection_operation', label: '品質: 設備点検表（点検実施）' },
    { value: 'quality.equipment_inspection_monthly_review', label: '品質: 設備点検表（月間確認）' },
    { value: 'quality.product_checksheet_template', label: '品質: 製品チェックシート（台紙登録/配置編集）' },
    { value: 'quality.product_checksheet_input', label: '品質: 製品チェックシート（現場入力）' },
    { value: 'quality.product_checksheet_review', label: '品質: 製品チェックシート（品質確認）' },
    { value: 'quality.integrated_checksheet_template', label: '品質: 工程一体チェックシート（テンプレート管理）' },
    { value: 'quality.integrated_checksheet_operation', label: '品質: 工程一体チェックシート（チェック実施）' },
    { value: 'quality.integrated_checksheet_review', label: '品質: 工程一体チェックシート（確認）' },
    { value: 'notifications', label: '通知作成' },
    { value: 'notifications.create', label: '通知: 通知作成' },
    { value: 'quality.equipment_inspection', label: '品質: 設備点検実施（旧キー互換）' },
    { value: 'quality.product_checksheet_batch_delete', label: '品質: チェックシートバッチ削除' },
    { value: 'engineering_change', label: '設変' },
    { value: 'outsource', label: 'FB外作管理' },
    { value: 'masters', label: 'マスタ' },
    { value: 'masters.product', label: 'マスタ: 品番マスタ' },
    { value: 'masters.product_group', label: 'マスタ: 製品グループ' },
    { value: 'masters.container_capacity', label: 'マスタ: 容器マスタ' },
    { value: 'masters.equipment', label: 'マスタ: 設備マスタ' },
    { value: 'masters.bom', label: 'マスタ: 構成マスタ' },
    { value: 'masters.routing', label: 'マスタ: ルーティングマスタ' },
    { value: 'masters.customer', label: 'マスタ: 得意先マスタ' },
    { value: 'masters.supplier', label: 'マスタ: 仕入先マスタ' },
    { value: 'masters.process', label: 'マスタ: 工程マスタ' },
    { value: 'masters.line', label: 'マスタ: ラインマスタ' },
    { value: 'masters.calendar', label: 'マスタ: カレンダマスタ' },
    { value: 'masters.work_pattern', label: 'マスタ: 勤務パターン' },
    { value: 'masters.contact', label: 'マスタ: 連絡先マスタ' },
    { value: 'masters.kubota_sakai_truck', label: 'マスタ: クボタ堺便マスタ' },
    { value: 'settings', label: '設定' },
  { value: 'settings.profile', label: '設定: プロフィール編集' },
  { value: 'settings.users', label: '設定: ユーザー管理' },
  { value: 'settings.departments', label: '設定: 組織管理' },
  { value: 'settings.user_permissions', label: '設定: ユーザー権限編集' },
  { value: 'settings.permission_templates', label: '設定: 権限テンプレート' },
  { value: 'settings.smtp', label: '設定: SMTP設定' },
  { value: 'settings.purchase_plan_lock', label: '設定: 仕入計画ロック設定' },
  { value: 'settings.production_plan_lock', label: '設定: 生産計画ロック設定' },
  { value: 'settings.scheduled_tasks', label: '設定: 定時タスク設定' },
  { value: 'settings.purchase_order_approval', label: '設定: 発注承認者設定' },
  { value: 'settings.stocktake_init', label: '設定: 棚卸初期化' },
  { value: 'settings.lock_date', label: '設定: 締め日管理' },
  { value: 'settings.kubota_sakai_config', label: '設定: クボタ堺便計画設定' },
  { value: 'users', label: 'ユーザー管理' },
  { value: 'manual', label: 'マニュアル' },
]

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
  unit: 'グループ',
}

const levelIndent = {
  division: '',
  group: '　',
  team: '　　',
  unit: '　　　',
}

const roleLabelMap = Object.fromEntries(
  ROLE_CHOICES.map((item) => [item.value, item.label])
)

const canAccessByResource = (resource, level = 'view') => {
  const user = authState.user
  if (!user || !resource) return false
  if (user.is_staff || user.is_superuser) return true

  const permissions = Array.isArray(user.effective_permissions)
    ? user.effective_permissions
    : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, 'settings', level)
}

const canViewPage = computed(() => canAccessByResource('settings.permission_templates', 'view'))
const canEditPage = computed(() => canAccessByResource('settings.permission_templates', 'edit'))

const buildDepartmentTree = (depts) => {
  const levelOrder = ['division', 'group', 'team', 'unit']
  const byParent = {}
  for (const dept of depts) {
    const pid = dept.parent || null
    if (!byParent[pid]) byParent[pid] = []
    byParent[pid].push(dept)
  }
  for (const key of Object.keys(byParent)) {
    byParent[key].sort((a, b) => {
      const li = levelOrder.indexOf(a.level) - levelOrder.indexOf(b.level)
      if (li !== 0) return li
      return (a.name || '').localeCompare(b.name || '')
    })
  }
  const result = []
  const walk = (parentId) => {
    for (const dept of (byParent[parentId] || [])) {
      const indent = levelIndent[dept.level] || ''
      result.push({
        value: dept.id,
        label: `${indent}${dept.name} (${levelLabels[dept.level] || dept.level})`,
      })
      walk(dept.id)
    }
  }
  walk(null)
  return result
}

const departmentOptions = computed(() => buildDepartmentTree(departments.value))

const getPermissionLabel = (resource) => {
  const found = permissionResources.find((item) => item.value === resource)
  return found ? found.label : resource
}

const getRoleLabel = (role) => {
  if (!role) return '-'
  return roleLabelMap[role] || role
}

const getUserDisplayName = (user) => {
  const fullName = `${user?.last_name || ''} ${user?.first_name || ''}`.trim()
  return fullName || user?.username || '-'
}

const formatUserPermissions = (permissions) => {
  if (!Array.isArray(permissions) || !permissions.length) return '-'
  return permissions
    .map((perm) => getPermissionLabel(perm.resource))
    .join(' / ')
}

const normalizeList = (payload) => {
  return Array.isArray(payload) ? payload : payload?.results || []
}

const getDepartmentNameById = (departmentId) => {
  if (!departmentId) return '-'
  const dept = departments.value.find((item) => String(item.id) === String(departmentId))
  if (!dept) return String(departmentId)
  return `${dept.name} (${levelLabels[dept.level] || dept.level})`
}

const formatPermissionLabels = (permissions) => {
  if (!Array.isArray(permissions) || !permissions.length) return '-'
  return permissions
    .map((perm) => getPermissionLabel(perm.resource))
    .sort((a, b) => a.localeCompare(b, 'ja'))
    .join(' / ')
}

const getPermissionCellClass = (perm) => {
  if (perm.can_edit) return 'permission-cell-edit'
  if (perm.can_view) return 'permission-cell-view'
  return ''
}

const emptyPermissions = () =>
  permissionResources.map((resource) => ({
    resource: resource.value,
    can_view: false,
    can_edit: false,
  }))

const buildPermissions = (permissions) => {
  const list = Array.isArray(permissions) ? permissions : []
  return permissionResources.map((resource) => {
    const existing = list.find((perm) => perm.resource === resource.value)
    return {
      resource: resource.value,
      can_view: Boolean(existing?.can_view),
      can_edit: Boolean(existing?.can_edit),
    }
  })
}

const serializePermissions = () =>
  templatePermissions.value
    .filter((perm) => perm.can_view || perm.can_edit)
    .map((perm) => ({
      resource: perm.resource,
      can_view: Boolean(perm.can_view),
      can_edit: Boolean(perm.can_edit),
    }))

const clearPermissionList = (permissions) => {
  permissions.forEach((perm) => {
    perm.can_view = false
    perm.can_edit = false
  })
}

const clearTemplatePermissions = () => {
  if (!canEditPage.value) return
  clearPermissionList(templatePermissions.value)
}

const clearDepartmentTemplatePermissions = () => {
  if (!canEditPage.value) return
  clearPermissionList(departmentTemplatePermissions.value)
}

const clearPositionTemplatePermissions = () => {
  if (!canEditPage.value) return
  clearPermissionList(positionTemplatePermissions.value)
}

const onPermissionChange = (perm, field) => {
  if (!canEditPage.value) return
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}

const onPositionPermissionChange = (perm, field) => {
  if (!canEditPage.value) return
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}

const loadDepartments = async () => {
  if (!canViewPage.value) return
  const response = await api.accounts.getDepartments({ page_size: 20000 })
  const data = response.data
  departments.value = Array.isArray(data) ? data : data.results || []
}

const loadUserOverrides = async () => {
  if (!canViewPage.value) return
  userOverrideLoading.value = true
  userOverrideError.value = ''
  try {
    const response = await api.accounts.getUsers({ page_size: 500 })
    const users = normalizeList(response.data || [])
    userOverrideUsers.value = users
      .filter((user) => Array.isArray(user.permissions) && user.permissions.length > 0)
      .sort((a, b) => {
        const aName = getUserDisplayName(a)
        const bName = getUserDisplayName(b)
        return aName.localeCompare(bName, 'ja')
      })
  } catch (error) {
    userOverrideError.value =
      error?.response?.data?.detail || '個別権限ユーザー一覧の取得に失敗しました。'
  } finally {
    userOverrideLoading.value = false
  }
}

const loadConfiguredTemplates = async () => {
  if (!canViewPage.value) return
  configuredTemplateLoading.value = true
  configuredTemplateError.value = ''
  try {
    const [departmentResponse, positionResponse, departmentPositionResponse] = await Promise.all([
      api.accounts.getDepartmentPermissions({ page_size: 5000 }),
      api.accounts.getPositionPermissions({ page_size: 5000 }),
      api.accounts.getDepartmentPositionPermissions({ page_size: 5000 }),
    ])

    const departmentRows = normalizeList(departmentResponse.data || [])
    const positionRows = normalizeList(positionResponse.data || [])
    const departmentPositionRows = normalizeList(departmentPositionResponse.data || [])

    const grouped = []

    const departmentMap = new Map()
    departmentRows.forEach((perm) => {
      const key = `department:${perm.department}`
      if (!departmentMap.has(key)) {
        departmentMap.set(key, [])
      }
      departmentMap.get(key).push(perm)
    })
    departmentMap.forEach((permissions, key) => {
      grouped.push({
        key,
        typeLabel: '部署',
        departmentName: getDepartmentNameById(permissions[0]?.department),
        positionName: '-',
        permissionCount: permissions.length,
        permissionLabels: formatPermissionLabels(permissions),
      })
    })

    const positionMap = new Map()
    positionRows.forEach((perm) => {
      const key = `position:${perm.position_name}`
      if (!positionMap.has(key)) {
        positionMap.set(key, [])
      }
      positionMap.get(key).push(perm)
    })
    positionMap.forEach((permissions, key) => {
      grouped.push({
        key,
        typeLabel: '役職',
        departmentName: '-',
        positionName: getRoleLabel(permissions[0]?.position_name),
        permissionCount: permissions.length,
        permissionLabels: formatPermissionLabels(permissions),
      })
    })

    const departmentPositionMap = new Map()
    departmentPositionRows.forEach((perm) => {
      const key = `departmentPosition:${perm.department}:${perm.position_name}`
      if (!departmentPositionMap.has(key)) {
        departmentPositionMap.set(key, [])
      }
      departmentPositionMap.get(key).push(perm)
    })
    departmentPositionMap.forEach((permissions, key) => {
      grouped.push({
        key,
        typeLabel: '部署・役職',
        departmentName: getDepartmentNameById(permissions[0]?.department),
        positionName: getRoleLabel(permissions[0]?.position_name),
        permissionCount: permissions.length,
        permissionLabels: formatPermissionLabels(permissions),
      })
    })

    configuredTemplateRows.value = grouped.sort((a, b) => {
      const typeOrder = ['部署・役職', '部署', '役職']
      const typeDiff = typeOrder.indexOf(a.typeLabel) - typeOrder.indexOf(b.typeLabel)
      if (typeDiff !== 0) return typeDiff
      const deptDiff = (a.departmentName || '').localeCompare(b.departmentName || '', 'ja')
      if (deptDiff !== 0) return deptDiff
      return (a.positionName || '').localeCompare(b.positionName || '', 'ja')
    })
  } catch (error) {
    configuredTemplateError.value =
      error?.response?.data?.detail || '設定済みテンプレ一覧の取得に失敗しました。'
  } finally {
    configuredTemplateLoading.value = false
  }
}

const loadDepartmentTemplate = async () => {
  if (!canViewPage.value) return
  departmentTemplateError.value = ''
  departmentTemplateSuccess.value = ''
  if (!selectedDepartmentOnlyId.value) {
    departmentTemplatePermissions.value = emptyPermissions()
    return
  }

  departmentTemplateLoading.value = true
  try {
    const response = await api.accounts.getDepartmentPermissions({
      department: selectedDepartmentOnlyId.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    departmentTemplatePermissions.value = buildPermissions(list)
  } catch (error) {
    departmentTemplateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    departmentTemplateLoading.value = false
  }
}

const saveDepartmentTemplate = async () => {
  if (!canEditPage.value) return
  departmentTemplateError.value = ''
  departmentTemplateSuccess.value = ''
  if (!selectedDepartmentOnlyId.value) {
    departmentTemplateError.value = '部署を選択してください。'
    return
  }

  departmentTemplateSaving.value = true
  try {
    const permissions = departmentTemplatePermissions.value
      .filter((perm) => perm.can_view || perm.can_edit)
      .map((perm) => ({
        resource: perm.resource,
        can_view: Boolean(perm.can_view),
        can_edit: Boolean(perm.can_edit),
      }))

    const response = await api.accounts.setDepartmentPermissions({
      department: selectedDepartmentOnlyId.value,
      permissions: permissions,
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    departmentTemplatePermissions.value = buildPermissions(list)
    departmentTemplateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    departmentTemplateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    departmentTemplateSaving.value = false
  }
}

const onDepartmentPermissionChange = (perm, field) => {
  if (!canEditPage.value) return
  // 編集権限がある場合、閲覧権限も自動で付与
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  // 閲覧権限を外す場合、編集権限も自動で外す
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}
const loadPositionTemplate = async () => {
  if (!canViewPage.value) return
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  if (!selectedPositionOnlyName.value) {
    positionTemplatePermissions.value = emptyPermissions()
    return
  }

  positionTemplateLoading.value = true
  try {
    const response = await api.accounts.getPositionPermissions({
      position_name: selectedPositionOnlyName.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    positionTemplatePermissions.value = buildPermissions(list)
  } catch (error) {
    positionTemplateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    positionTemplateLoading.value = false
  }
}

const savePositionTemplate = async () => {
  if (!canEditPage.value) return
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  if (!selectedPositionOnlyName.value) {
    positionTemplateError.value = '役職を選択してください。'
    return
  }

  positionTemplateSaving.value = true
  try {
    const permissions = positionTemplatePermissions.value
      .filter((perm) => perm.can_view || perm.can_edit)
      .map((perm) => ({
        resource: perm.resource,
        can_view: Boolean(perm.can_view),
        can_edit: Boolean(perm.can_edit),
      }))

    const response = await api.accounts.setPositionPermissions({
      position_name: selectedPositionOnlyName.value,
      permissions: permissions,
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    positionTemplatePermissions.value = buildPermissions(list)
    positionTemplateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    positionTemplateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    positionTemplateSaving.value = false
  }
}


const loadTemplate = async () => {
  if (!canViewPage.value) return
  templateError.value = ''
  templateSuccess.value = ''
  if (!selectedDepartmentId.value || !selectedPositionName.value) {
    templatePermissions.value = emptyPermissions()
    return
  }

  templateLoading.value = true
  try {
    const response = await api.accounts.getDepartmentPositionPermissions({
      department: selectedDepartmentId.value,
      position_name: selectedPositionName.value,
    })
    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    templatePermissions.value = buildPermissions(list)
  } catch (error) {
    templateError.value =
      error?.response?.data?.detail || '権限テンプレートの取得に失敗しました。'
  } finally {
    templateLoading.value = false
  }
}


const saveTemplate = async () => {
  if (!canEditPage.value) return
  templateError.value = ''
  templateSuccess.value = ''
  if (!selectedDepartmentId.value || !selectedPositionName.value) {
    templateError.value = '部署と役職を選択してください。'
    return
  }

  templateSaving.value = true
  try {
    const response = await api.accounts.setDepartmentPositionPermissions({
      department: selectedDepartmentId.value,
      position_name: selectedPositionName.value,
      permissions: serializePermissions(),
    })

    const data = response.data
    const list = Array.isArray(data) ? data : data.results || []
    templatePermissions.value = buildPermissions(list)
    templateSuccess.value = '権限テンプレートを保存しました。'
  } catch (error) {
    templateError.value = extractErrorMessage(error?.response?.data) || '保存に失敗しました。'
  } finally {
    templateSaving.value = false
  }
}

const onDepartmentChange = async () => {
  selectedPositionName.value = ''
  templatePermissions.value = emptyPermissions()
}

const refreshAll = async () => {
  if (!canViewPage.value) return
  loading.value = true
  templateError.value = ''
  templateSuccess.value = ''
  positionTemplateError.value = ''
  positionTemplateSuccess.value = ''
  try {
    await loadDepartments()
    await loadTemplate()
    await loadPositionTemplate()
    if (activeTab.value === 'userOverrides') {
      await loadUserOverrides()
    }
    if (activeTab.value === 'configuredTemplates') {
      await loadConfiguredTemplates()
    }
  } finally {
    loading.value = false
  }
}

const openUserOverridesTab = async () => {
  activeTab.value = 'userOverrides'
  if (!userOverrideUsers.value.length && !userOverrideLoading.value) {
    await loadUserOverrides()
  }
}

const openConfiguredTemplatesTab = async () => {
  activeTab.value = 'configuredTemplates'
  if (!configuredTemplateRows.value.length && !configuredTemplateLoading.value) {
    await loadConfiguredTemplates()
  }
}

const extractErrorMessage = (detail) => {
  if (!detail) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.join(' ')
  if (typeof detail !== 'object') return ''

  const messages = []
  Object.entries(detail).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      messages.push(`${key}: ${value.join(' ')}`)
    } else if (typeof value === 'object' && value !== null) {
      Object.entries(value).forEach(([childKey, childValue]) => {
        if (Array.isArray(childValue)) {
          messages.push(`${key}.${childKey}: ${childValue.join(' ')}`)
        } else if (childValue) {
          messages.push(`${key}.${childKey}: ${childValue}`)
        }
      })
    } else if (value) {
      messages.push(`${key}: ${value}`)
    }
  })
  return messages.join(' / ')
}

onMounted(async () => {
  if (!canViewPage.value) return
  templatePermissions.value = emptyPermissions()
  positionTemplatePermissions.value = emptyPermissions()
  await refreshAll()
})
</script>

<style scoped>
:deep(.page-content) {
  overflow: visible;
}

.template-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.template-tab {
  border: 1px solid #9fb4da;
  background: #eef3ff;
  color: #27406f;
  padding: 6px 14px;
  border-radius: 6px 6px 0 0;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.template-tab.active {
  background: #2f6fed;
  border-color: #2f6fed;
  color: #fff;
}

.template-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 12px;
  background: #fff;
}

.template-sticky-header {
  position: sticky;
  top: 0;
  z-index: 10;
  margin: -12px -12px 12px;
  padding: 12px 12px 10px;
  background: #fff;
  border-bottom: 1px solid #dfe5ef;
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.04);
}

.permission-table-wrap {
  overflow-x: auto;
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.template-header-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
}

.template-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 12px 0;
}

.template-select {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 240px;
  font-size: 12px;
}

.template-select select,
.template-select input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.position-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.permission-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.permission-table th,
.permission-table td {
  border: 1px solid #d6d6d6;
  padding: 4px 6px;
  text-align: center;
}

.permission-table th:first-child,
.permission-table td:first-child {
  text-align: right;
}

.permission-table td.permission-cell-edit {
  background: #9ed7a5;
}

.permission-table td.permission-cell-view {
  background: #9fbcf7;
}

.permission-table th {
  background: #f4f6ff;
  font-weight: 600;
}

.save-message {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.save-message.success {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}

.btn {
  border: 1px solid #888;
  background: #f3f3f3;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
}

.btn.primary {
  background: #2f6fed;
  border-color: #2f6fed;
  color: #fff;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.helper-text {
  color: #666;
  font-size: 12px;
}

.alert {
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 8px;
  font-size: 12px;
}

.alert-danger {
  background: #ffe5e5;
  color: #b42318;
  border: 1px solid #f5b7b1;
}

.alert-success {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}
</style>
