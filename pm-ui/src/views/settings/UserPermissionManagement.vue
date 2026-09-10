<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">ユーザー権限編集</h2>
      <div class="page-actions">
        <input
          v-model="searchKeyword"
          class="search-input"
          type="text"
          placeholder="ユーザー名/氏名/メールで検索"
          @keyup.enter="loadUsers"
        />
        <select v-model="filterDepartmentId" class="search-select">
          <option :value="''">事業部: すべて</option>
          <option value="__unset__">事業部: 未設定</option>
          <option v-for="dept in filterDepartmentOptions" :key="dept.value" :value="String(dept.value)">
            {{ dept.label }}
          </option>
        </select>
        <select v-model="filterGroupId" class="search-select">
          <option value="">係: すべて</option>
          <option value="__unset__">係: 未設定</option>
          <option v-for="grp in filterGroupOptions" :key="grp.value" :value="String(grp.value)">
            {{ grp.label }}
          </option>
        </select>
        <select v-model="filterTeamId" class="search-select">
          <option value="">班: すべて</option>
          <option value="__unset__">班: 未設定</option>
          <option v-for="tm in filterTeamOptions" :key="tm.value" :value="String(tm.value)">
            {{ tm.label }}
          </option>
        </select>
        <select v-model="filterUnitId" class="search-select">
          <option value="">グループ: すべて</option>
          <option value="__unset__">グループ: 未設定</option>
          <option v-for="ut in filterUnitOptions" :key="ut.value" :value="String(ut.value)">
            {{ ut.label }}
          </option>
        </select>
        <select v-model="filterPosition" class="search-select">
          <option value="">役割: すべて</option>
          <option v-for="option in roleOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
        <label class="filter-check">
          <input v-model="filterActiveOnly" type="checkbox" />
          有効のみ
        </label>
        <label class="filter-check">
          <input v-model="filterInactiveOnly" type="checkbox" />
          無効のみ
        </label>
        <button class="btn" @click="loadUsers" :disabled="loading">
          更新
        </button>
        <button class="btn primary" @click="startCreate" :disabled="!canManageBasic">
          新規ユーザー
        </button>
      </div>
    </div>

    <div class="page-content">
      <div v-if="!isAdminUser" class="helper-text">
        この画面を開く権限がありません。
      </div>
      <div v-else class="user-grid">
        <section class="user-list">
          <h3 class="section-title">
            ユーザー一覧
            <span class="count-text">（{{ filteredUsers.length }} / {{ users.length }}件）</span>
          </h3>
          <div v-if="loading" class="helper-text">読み込み中...</div>
          <div v-else-if="filteredUsers.length === 0" class="helper-text">該当ユーザーがありません。</div>
          <table v-else class="data-table">
            <thead>
              <tr>
                <th>ユーザー名</th>
                <th>氏名</th>
                <th>事業部</th>
                <th>役割</th>
                <th>状態</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="user in filteredUsers"
                :key="user.id"
                :class="{ active: user.id === selectedUserId }"
                @click="selectUser(user)"
              >
                <td>{{ user.username }}</td>
                <td>{{ getUserDisplayName(user) }}</td>
                <td>{{ user.profile?.division_name || user.profile?.department_name || '-' }}</td>
                <td>{{ roleLabels[user.profile?.role] || '-' }}</td>
                <td>
                  <span :class="user.is_active ? 'status active' : 'status inactive'">
                    {{ user.is_active ? '有効' : '無効' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="user-editor">
          <div class="editor-header">
            <h3 class="section-title" :class="{ 'creating-mode': isCreating, 'editing-mode': !isCreating && selectedUserId }">
              <span v-if="isCreating" class="mode-badge create">新規作成</span>
              <span v-else-if="selectedUserId" class="mode-badge edit">編集中</span>
              <span v-else class="mode-badge empty">未選択</span>
              {{ isCreating ? '新規ユーザー作成' : selectedUserId ? `ユーザー詳細 - ${form.username}` : 'ユーザーを選択してください' }}
            </h3>
          </div>

          <div v-if="errorMessage" class="alert alert-danger">
            {{ errorMessage }}
          </div>
          <div v-if="successMessage" class="alert alert-success">
            {{ successMessage }}
          </div>

          <div v-if="!isCreating && !selectedUserId" class="empty-state">
            <p>左側のリストからユーザーを選択して編集するか、「新規ユーザー」ボタンをクリックして新しいユーザーを作成してください。</p>
          </div>

          <form v-else class="form-grid" @submit.prevent="saveUser">
            <div class="form-row">
              <label>ユーザー名</label>
              <input v-model="form.username" type="text" required />
            </div>
            <div class="form-row">
              <label>メールアドレス</label>
              <input v-model="form.email" type="email" />
            </div>
            <div class="form-row">
              <label>姓</label>
              <input v-model="form.last_name" type="text" />
            </div>
            <div class="form-row">
              <label>名</label>
              <input v-model="form.first_name" type="text" />
            </div>

            <div class="form-row">
              <label>社員コード</label>
              <input v-model="form.profile.employee_code" type="text" />
            </div>
            <div class="form-row">
              <label>役割</label>
              <select v-model="form.profile.role">
                <option v-for="option in roleOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>雇用形態</label>
              <select v-model="form.profile.employment_type">
                <option v-for="option in employmentOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>事業部</label>
              <select v-model="form.profile.division" @change="onDivisionChange">
                <option :value="null">未設定</option>
                <option v-for="div in divisionOptions" :key="div.value" :value="div.value">
                  {{ div.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>係</label>
              <select v-model="form.profile.group" @change="onGroupChange" :disabled="!form.profile.division">
                <option :value="null">未設定</option>
                <option v-for="grp in groupOptions" :key="grp.value" :value="grp.value">
                  {{ grp.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>班</label>
              <select v-model="form.profile.team" @change="onTeamChange" :disabled="!form.profile.group">
                <option :value="null">未設定</option>
                <option v-for="tm in teamOptions" :key="tm.value" :value="tm.value">
                  {{ tm.label }}
                </option>
              </select>
            </div>
            <div v-if="canAssignSupervisorTeams" class="form-row full">
              <label>担当班（複数）</label>
              <select
                v-model="form.profile.supervisor_teams"
                class="multi-select"
                multiple
                :disabled="!form.profile.group"
              >
                <option v-for="tm in teamOptions" :key="tm.value" :value="tm.value">
                  {{ tm.label }}
                </option>
              </select>
              <div class="helper-text">班長・係長・部長の兼任班を設定できます。</div>
            </div>
            <div v-if="canAssignLeaderUnits" class="form-row full">
              <label>担当グループ（複数）</label>
              <select
                v-model="form.profile.leader_units"
                class="multi-select"
                multiple
                :disabled="!form.profile.team"
              >
                <option v-for="ut in unitOptions" :key="ut.value" :value="ut.value">
                  {{ ut.label }}
                </option>
              </select>
              <div class="helper-text">リーダー・係長・部長の兼任グループを設定できます。</div>
            </div>
            <div class="form-row">
              <label>グループ</label>
              <select v-model="form.profile.unit" :disabled="!form.profile.team">
                <option :value="null">未設定</option>
                <option v-for="ut in unitOptions" :key="ut.value" :value="ut.value">
                  {{ ut.label }}
                </option>
              </select>
            </div>
            <div class="form-row">
              <label>入社日</label>
              <input v-model="form.profile.joined_on" type="date" />
            </div>

            <div class="form-row">
              <label>パスワード</label>
              <input v-model="form.password" type="password" :placeholder="passwordHint" />
            </div>
            <div class="form-row">
              <label>パスワード確認</label>
              <input v-model="passwordConfirm" type="password" :placeholder="passwordHint" />
            </div>

            <div class="form-row inline">
              <label>有効</label>
              <input v-model="form.is_active" type="checkbox" />
            </div>
            <div class="form-row inline">
              <label>backendスタッフ</label>
              <input v-model="form.is_staff" type="checkbox" />
            </div>
            <div class="form-row inline">
              <label>管理者</label>
              <input v-model="form.is_superuser" type="checkbox" />
            </div>

            <div class="form-row full permission-section">
              <div class="permission-header">
                <div>
                  <label>ユーザー個別 権限設定</label>
                  <div class="permission-helper-text">
                    状態列は最終的な有効権限、個別設定列はユーザー個別権限です。
                  </div>
                </div>
                <label class="permission-toggle">
                  <input v-model="useUserPermissions" type="checkbox" :disabled="!canManagePermissions" />
                  個別権限を使う
                </label>
              </div>
              <div v-if="detailLoading" class="helper-text">権限明細を読み込み中...</div>
              <table class="permission-table" :class="{ disabled: !useUserPermissions || !canManagePermissions }">
                <thead>
                  <tr>
                    <th>機能</th>
                    <th>状態: 閲覧</th>
                    <th>状態: 編集</th>
                    <th>個別設定: 閲覧</th>
                    <th>個別設定: 編集</th>
                    <th>獲得元</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in permissionRows" :key="row.resource">
                    <td>{{ getPermissionLabel(row.resource) }}</td>
                    <td>
                      <input type="checkbox" :checked="row.effective_can_view" disabled />
                    </td>
                    <td>
                      <input type="checkbox" :checked="row.effective_can_edit" disabled />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        v-model="row.permission.can_view"
                        @change="onPermissionChange(row.permission, 'can_view')"
                        :disabled="!useUserPermissions || !canManagePermissions"
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        v-model="row.permission.can_edit"
                        @change="onPermissionChange(row.permission, 'can_edit')"
                        :disabled="!useUserPermissions || !canManagePermissions"
                      />
                    </td>
                    <td class="permission-source-cell">
                      <div v-if="row.sources.length" class="permission-source-list">
                        <span
                          v-for="(source, index) in row.sources"
                          :key="`${row.resource}-${source.source_type}-${index}`"
                          class="permission-source-tag"
                          :class="{ edit: source.can_edit, view: source.can_view && !source.can_edit }"
                        >
                          {{ source.source_label }}: {{ describePermissionLevel(source.can_view, source.can_edit) }}
                        </span>
                      </div>
                      <span v-else class="permission-source-empty">-</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="form-actions">
              <button type="submit" class="btn primary" :disabled="saving || !canManageBasic">
                {{ saving ? '保存中...' : '保存' }}
              </button>
              <button type="button" class="btn" @click="resetForm" :disabled="!canManageBasic">
                リセット
              </button>
              <button
                v-if="!isCreating && selectedUserId"
                type="button"
                class="btn danger"
                @click="deleteUser"
                :disabled="saving || !canManageBasic"
              >
                削除
              </button>
            </div>
          </form>
        </section>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const users = ref([])
const departments = ref([])
const divisions = ref([])
const allGroups = ref([])
const allTeams = ref([])
const allUnits = ref([])
const loading = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const searchKeyword = ref('')
const filterDepartmentId = ref('')
const filterGroupId = ref('')
const filterTeamId = ref('')
const filterUnitId = ref('')
const filterPosition = ref('')
const filterActiveOnly = ref(false)
const filterInactiveOnly = ref(false)
const selectedUserId = ref(null)
const isCreating = ref(false)
const passwordConfirm = ref('')
const useUserPermissions = ref(false)

const roleOptions = [
  { value: 'manager', label: '事業部長・課長' },
  { value: 'chief', label: '係長' },
  { value: 'supervisor', label: '班長' },
  { value: 'leader', label: 'リーダー' },
  { value: 'office_staff', label: '事務員' },
  { value: 'staff', label: '一般' },
]

const employmentOptions = [
  { value: 'regular', label: '正準社員' },
  { value: 'dispatch', label: '人材派遣' },
  { value: 'intern', label: '実習生' },
  { value: 'skilled', label: '特定技能実習生' },
  { value: 'contract', label: '嘱託社員' },
  { value: 'part', label: 'パート' },
]

const permissionResources = [
  { value: 'dashboard', label: 'ダッシュボード' },
  { value: 'orders', label: '受注' },
  { value: 'orders.list', label: '受注: 受注一覧' },
  { value: 'orders.csv_import', label: '受注: 受注取込' },
  { value: 'orders.kubota_analysis', label: '受注: クボタ内示変化推移分析' },
  { value: 'orders.naiji_analysis', label: '受注: 内示分析' },
  { value: 'orders.line_expand', label: '受注: ライン展開' },
  { value: 'orders.first_article', label: '受注: お久しぶり製品通知設定' },
  { value: 'production', label: '生産' },
  { value: 'production.process_input', label: '生産: 工程作業入力' },
  { value: 'production.process_knowledge', label: '生産: 工程別コツ・注意事項' },
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
  { value: 'shipping.progress_edit', label: '出荷: 出荷進度管理' },
  { value: 'shipping.ship_to_lead_time', label: '出荷: 納入地別出荷加算日数' },
  { value: 'inventory', label: '在庫' },
  { value: 'stocktake', label: '在庫: 棚卸入力' },
  { value: 'stocktake.layout', label: '在庫: 棚卸レイアウト' },
  { value: 'stocktake.area', label: '在庫: 棚卸エリア管理' },
  { value: 'stocktake.delete', label: '在庫: 棚卸履歴削除' },
  { value: 'quality', label: '品質' },
  { value: 'quality.equipment_inspection_master', label: '品質: 設備点検表（点検項目作成）' },
  { value: 'quality.equipment_inspection_operation', label: '品質: 設備点検表（点検実施）' },
  { value: 'quality.equipment_inspection_monthly_review', label: '品質: 設備点検表（月間確認）' },
  { value: 'quality.integrated_checksheet_template', label: '品質: 工程一体チェックシート（テンプレート管理）' },
  { value: 'quality.integrated_checksheet_operation', label: '品質: 工程一体チェックシート（チェック実施）' },
  { value: 'quality.integrated_checksheet_review', label: '品質: 工程一体チェックシート（確認）' },
  { value: 'notifications', label: '通信' },
  { value: 'notifications.create', label: '通知: 通知作成' },
  { value: 'settings.shipping_progress_horizon', label: '設定: 出荷進度再計算日数' },
  { value: 'quality.equipment_inspection', label: '品質: 設備点検実施（旧キー互換）' },
  { value: 'engineering_change', label: '設変' },
  { value: 'outsource', label: 'FB外作管理' },
  { value: 'outsource.first_article', label: 'FB外作: お久しぶり製品通知設定' },
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
  { value: 'settings.approval_routes', label: '設定: 承認設定' },
  { value: 'settings.material_order_email_config', label: '設定: 材料注文書メール設定' },
  { value: 'settings.purchase_order_approval', label: '設定: 発注承認者設定' },
  { value: 'settings.stocktake_init', label: '設定: 棚卸初期化' },
  { value: 'settings.orphan_backlog_maintenance', label: '設定: 孤立ライン実績メンテナンス' },
  { value: 'settings.lock_date', label: '設定: 締め日管理' },
  { value: 'settings.kubota_import', label: '設定: クボタ堺取り込み通知設定' },
  { value: 'settings.kubota_sakai_config', label: '設定: クボタ堺便計画設定' },
  { value: 'users', label: 'ユーザー管理' },
  { value: 'manual', label: 'マニュアル' },
]

const roleLabels = roleOptions.reduce((acc, option) => {
  acc[option.value] = option.label
  return acc
}, {})

const levelLabels = {
  division: '事業部',
  group: '係',
  team: '班',
  unit: 'グループ',
}

const emptyProfile = () => ({
  employee_code: '',
  role: 'staff',
  employment_type: 'regular',
  department: null,
  division: null,
  group: null,
  team: null,
  supervisor_teams: [],
  leader_units: [],
  unit: null,
  joined_on: '',
})

const emptyPermissions = () =>
  permissionResources.map((resource) => ({
    resource: resource.value,
    can_view: false,
    can_edit: false,
  }))

const form = reactive({
  id: null,
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  is_active: true,
  is_staff: false,
  is_superuser: false,
  password: '',
  profile: emptyProfile(),
  permissions: emptyPermissions(),
  effective_permission_details: [],
})

const passwordHint = computed(() => (isCreating.value ? '必須' : '変更時のみ入力'))
const canAssignSupervisorTeams = computed(() => form.profile.role !== 'leader')
const canAssignLeaderUnits = computed(() => ['leader', 'chief', 'manager'].includes(form.profile.role))

const canManageBasic = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings.user_permissions', 'edit')
})

const canViewUsers = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings.user_permissions', 'view')
})

const canManagePermissions = computed(() => {
  const user = authState.user
  if (!user) return false
  if (user.is_staff || user.is_superuser) return true
  return hasPermission(user, 'settings.user_permissions', 'edit')
})

const isAdminUser = computed(() => {
  return canViewUsers.value || canManagePermissions.value
})

const filterDepartmentOptions = computed(() =>
  departments.value
    .filter((dept) => dept.level === 'division')
    .map((dept) => ({
      value: dept.id,
      label: `${dept.name} (${levelLabels[dept.level] || dept.level})`,
    }))
)

const filterGroupOptions = computed(() => {
  const targetDepartment = filterDepartmentId.value
  return allGroups.value
    .filter((grp) => !targetDepartment || String(grp.parent ?? '') === targetDepartment)
    .map((grp) => ({
      value: grp.id,
      label: grp.name,
    }))
})

const filterTeamOptions = computed(() => {
  const targetDepartment = filterDepartmentId.value
  const targetGroup = filterGroupId.value
  if (targetGroup) {
    return allTeams.value
      .filter((tm) => String(tm.parent ?? '') === targetGroup)
      .map((tm) => ({
        value: tm.id,
        label: tm.name,
      }))
  }
  if (targetDepartment) {
    const groupIds = new Set(
      allGroups.value
        .filter((grp) => String(grp.parent ?? '') === targetDepartment)
        .map((grp) => String(grp.id))
    )
    return allTeams.value
      .filter((tm) => groupIds.has(String(tm.parent ?? '')))
      .map((tm) => ({
        value: tm.id,
        label: tm.name,
      }))
  }
  return allTeams.value.map((tm) => ({
    value: tm.id,
    label: tm.name,
  }))
})

const filterUnitOptions = computed(() => {
  const targetTeam = filterTeamId.value
  const targetGroup = filterGroupId.value
  const targetDepartment = filterDepartmentId.value
  if (targetTeam && targetTeam !== '__unset__') {
    return allUnits.value
      .filter((ut) => String(ut.parent ?? '') === targetTeam)
      .map((ut) => ({ value: ut.id, label: ut.name }))
  }
  if (targetGroup && targetGroup !== '__unset__') {
    const teamIds = new Set(
      allTeams.value
        .filter((tm) => String(tm.parent ?? '') === targetGroup)
        .map((tm) => String(tm.id))
    )
    return allUnits.value
      .filter((ut) => teamIds.has(String(ut.parent ?? '')))
      .map((ut) => ({ value: ut.id, label: ut.name }))
  }
  if (targetDepartment && targetDepartment !== '__unset__') {
    const groupIds = new Set(
      allGroups.value
        .filter((grp) => String(grp.parent ?? '') === targetDepartment)
        .map((grp) => String(grp.id))
    )
    const teamIds = new Set(
      allTeams.value
        .filter((tm) => groupIds.has(String(tm.parent ?? '')))
        .map((tm) => String(tm.id))
    )
    return allUnits.value
      .filter((ut) => teamIds.has(String(ut.parent ?? '')))
      .map((ut) => ({ value: ut.id, label: ut.name }))
  }
  return allUnits.value.map((ut) => ({ value: ut.id, label: ut.name }))
})

const filteredUsers = computed(() => {
  const targetDepartment = filterDepartmentId.value
  const targetGroup = filterGroupId.value
  const targetTeam = filterTeamId.value
  const targetUnit = filterUnitId.value
  const targetPosition = filterPosition.value
  return users.value.filter((user) => {
    const departmentValue = String(user.profile?.department ?? '')
    const groupValue = String(user.profile?.group ?? '')
    const teamValue = String(user.profile?.team ?? '')
    const supervisorTeamValues = Array.isArray(user.profile?.supervisor_teams)
      ? user.profile.supervisor_teams.map((value) => String(value))
      : []
    const leaderUnitValues = Array.isArray(user.profile?.leader_units)
      ? user.profile.leader_units.map((value) => String(value))
      : []
    const unitValue = String(user.profile?.unit ?? '')
    const roleValue = String(user.profile?.role ?? '')

    if (targetDepartment && targetDepartment !== '__unset__' && departmentValue !== targetDepartment) {
      return false
    }
    if (targetDepartment === '__unset__' && departmentValue) {
      return false
    }
    if (targetGroup && targetGroup !== '__unset__' && groupValue !== targetGroup) {
      return false
    }
    if (targetGroup === '__unset__' && groupValue) {
      return false
    }
    if (
      targetTeam
      && targetTeam !== '__unset__'
      && teamValue !== targetTeam
      && !supervisorTeamValues.includes(targetTeam)
    ) {
      return false
    }
    if (targetTeam === '__unset__' && (teamValue || supervisorTeamValues.length > 0)) {
      return false
    }
    if (
      targetUnit
      && targetUnit !== '__unset__'
      && unitValue !== targetUnit
      && !leaderUnitValues.includes(targetUnit)
    ) {
      return false
    }
    if (targetUnit === '__unset__' && (unitValue || leaderUnitValues.length > 0)) {
      return false
    }
    if (targetPosition && targetPosition !== '__unset__' && roleValue !== targetPosition) {
      return false
    }
    if (targetPosition === '__unset__' && roleValue) {
      return false
    }
    if (filterInactiveOnly.value && user.is_active) {
      return false
    }
    if (filterActiveOnly.value && !filterInactiveOnly.value && !user.is_active) {
      return false
    }
    return true
  })
})

const divisionOptions = computed(() =>
  divisions.value.map((div) => ({
    value: div.id,
    label: div.name,
  }))
)

const groupOptions = computed(() => {
  if (!form.profile.division) {
    return []
  }
  return allGroups.value
    .filter((grp) => grp.parent === form.profile.division)
    .map((grp) => ({
      value: grp.id,
      label: grp.name,
    }))
})

const teamOptions = computed(() => {
  if (!form.profile.group) {
    return []
  }
  return allTeams.value
    .filter((tm) => tm.parent === form.profile.group)
    .map((tm) => ({
      value: tm.id,
      label: tm.name,
    }))
})

const unitOptions = computed(() => {
  if (!form.profile.team) {
    return []
  }
  return allUnits.value
    .filter((ut) => ut.parent === form.profile.team)
    .map((ut) => ({
      value: ut.id,
      label: ut.name,
    }))
})

const effectivePermissionDetailMap = computed(() => {
  const map = new Map()
  const details = Array.isArray(form.effective_permission_details) ? form.effective_permission_details : []
  details.forEach((detail) => {
    if (detail?.resource) {
      map.set(detail.resource, detail)
    }
  })
  return map
})

const permissionRows = computed(() =>
  form.permissions.map((permission) => {
    const detail = effectivePermissionDetailMap.value.get(permission.resource)
    const templateCanView = Boolean(detail?.template_can_view)
    const templateCanEdit = Boolean(detail?.template_can_edit)
    const hasCurrentUserPermission = Boolean(permission.can_view || permission.can_edit)
    const currentUserCanView = Boolean(permission.can_view || permission.can_edit)
    const currentUserCanEdit = Boolean(permission.can_edit)
    const effectiveCanView = useUserPermissions.value
      ? (hasCurrentUserPermission ? currentUserCanView : templateCanView)
      : templateCanView
    const effectiveCanEdit = useUserPermissions.value
      ? (hasCurrentUserPermission ? currentUserCanEdit : templateCanEdit)
      : templateCanEdit
    const templateSources = Array.isArray(detail?.sources)
      ? detail.sources.filter((source) => source?.source_type !== 'user')
      : []
    const sources = [...templateSources]
    if (useUserPermissions.value && hasCurrentUserPermission) {
      sources.unshift({
        source_type: 'user',
        source_label: '個別権限',
        can_view: currentUserCanView,
        can_edit: currentUserCanEdit,
      })
    }
    return {
      resource: permission.resource,
      permission,
      template_can_view: templateCanView,
      template_can_edit: templateCanEdit,
      effective_can_view: effectiveCanView,
      effective_can_edit: effectiveCanEdit,
      sources,
    }
  })
)

const getUserDisplayName = (user) => {
  const fullName = `${user.last_name || ''} ${user.first_name || ''}`.trim()
  return fullName || user.username || user.email || '-'
}

const getPermissionLabel = (resource) => {
  const found = permissionResources.find((item) => item.value === resource)
  return found ? found.label : resource
}

const describePermissionLevel = (canView, canEdit) => {
  if (canEdit) return '閲覧・編集'
  if (canView) return '閲覧'
  return '-'
}

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

const applyUserToForm = (user) => {
  form.id = user.id
  form.username = user.username || ''
  form.email = user.email || ''
  form.first_name = user.first_name || ''
  form.last_name = user.last_name || ''
  form.is_active = Boolean(user.is_active)
  form.is_staff = Boolean(user.is_staff)
  form.is_superuser = Boolean(user.is_superuser)
  form.password = ''
  passwordConfirm.value = ''
  form.profile = {
    ...emptyProfile(),
    ...(user.profile || {}),
  }
  form.profile.supervisor_teams = Array.isArray(form.profile.supervisor_teams)
    ? form.profile.supervisor_teams
        .map((value) => Number(value))
        .filter((value) => !Number.isNaN(value))
    : []
  form.profile.leader_units = Array.isArray(form.profile.leader_units)
    ? form.profile.leader_units
        .map((value) => Number(value))
        .filter((value) => !Number.isNaN(value))
    : []
  form.permissions = buildPermissions(user.permissions)
  form.effective_permission_details = Array.isArray(user.effective_permission_details)
    ? user.effective_permission_details
    : []
  useUserPermissions.value = Array.isArray(user.permissions) && user.permissions.length > 0
}

const onPermissionChange = (perm, field) => {
  if (field === 'can_edit' && perm.can_edit) {
    perm.can_view = true
  }
  if (field === 'can_view' && !perm.can_view) {
    perm.can_edit = false
  }
}

const onDivisionChange = () => {
  // 事業部が変更されたら、係・班・グループをクリア
  form.profile.group = null
  form.profile.team = null
  form.profile.supervisor_teams = []
  form.profile.leader_units = []
  form.profile.unit = null
}

const onGroupChange = () => {
  // 係が変更されたら、班とグループをクリア
  form.profile.team = null
  form.profile.supervisor_teams = []
  form.profile.leader_units = []
  form.profile.unit = null
}

const onTeamChange = () => {
  // 班が変更されたら、グループをクリア
  form.profile.leader_units = []
  form.profile.unit = null
}

const loadDepartments = async () => {
  if (!isAdminUser.value) return
  const response = await api.accounts.getDepartments({ page_size: 20000 })
  const data = response.data
  departments.value = Array.isArray(data) ? data : data.results || []
}


const loadDivisions = async () => {
  if (!isAdminUser.value) return
  try {
    const response = await api.accounts.getDivisions()
    divisions.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    divisions.value = []
  }
}

const loadGroups = async () => {
  if (!isAdminUser.value) return
  try {
    const response = await api.accounts.getGroups()
    allGroups.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    allGroups.value = []
  }
}

const loadTeams = async () => {
  if (!isAdminUser.value) return
  try {
    const response = await api.accounts.getTeams()
    allTeams.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    allTeams.value = []
  }
}

const loadUnits = async () => {
  if (!isAdminUser.value) return
  try {
    const response = await api.accounts.getUnits()
    allUnits.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    allUnits.value = []
  }
}

const loadUsers = async () => {
  if (!isAdminUser.value) {
    errorMessage.value = 'この画面を開く権限がありません。'
    return
  }
  loading.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await api.accounts.getUsers({
      search: searchKeyword.value || undefined,
      page_size: 200,
    })
    const data = response.data
    users.value = Array.isArray(data) ? data : data.results || []
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'ユーザー一覧の取得に失敗しました。'
  } finally {
    loading.value = false
  }
}

const selectUser = async (user) => {
  if (!user?.id) return
  isCreating.value = false
  selectedUserId.value = user.id
  applyUserToForm(user)
  detailLoading.value = true
  errorMessage.value = ''
  try {
    const response = await api.accounts.getUser(user.id)
    applyUserToForm(response.data)
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || 'ユーザー権限明細の取得に失敗しました。'
  } finally {
    detailLoading.value = false
  }
}

const resetForm = async () => {
  if (isCreating.value) {
    form.id = null
    form.username = ''
    form.email = ''
    form.first_name = ''
    form.last_name = ''
    form.is_active = true
    form.is_staff = false
    form.is_superuser = false
    form.password = ''
    passwordConfirm.value = ''
    form.profile = emptyProfile()
    form.permissions = emptyPermissions()
    form.effective_permission_details = []
    useUserPermissions.value = false
    return
  }

  const current = users.value.find((item) => item.id === selectedUserId.value)
  if (current) {
    await selectUser(current)
  }
}

const startCreate = () => {
  if (!canManageBasic.value) return
  isCreating.value = true
  selectedUserId.value = null
  resetForm()
}

const buildPayload = () => {
  const supervisorTeams = Array.isArray(form.profile.supervisor_teams)
    ? form.profile.supervisor_teams.filter((value) => value !== null && value !== undefined && value !== '')
    : []
  const leaderUnits = Array.isArray(form.profile.leader_units)
    ? form.profile.leader_units.filter((value) => value !== null && value !== undefined && value !== '')
    : []

  const profile = {
    ...form.profile,
    division: form.profile.division || null,
    department: form.profile.division || null,
    group: form.profile.group || null,
    team: form.profile.team || null,
    supervisor_teams: canAssignSupervisorTeams.value ? supervisorTeams : [],
    leader_units: canAssignLeaderUnits.value ? leaderUnits : [],
    unit: form.profile.unit || null,
    joined_on: form.profile.joined_on || null,
  }

  const payload = {
    username: form.username.trim(),
    email: form.email.trim(),
    first_name: form.first_name.trim(),
    last_name: form.last_name.trim(),
    is_active: form.is_active,
    is_staff: form.is_staff,
    is_superuser: form.is_superuser,
    profile,
  }

  if (canManagePermissions.value) {
    payload.permissions = useUserPermissions.value
      ? form.permissions
          .filter((perm) => Boolean(perm.can_view) || Boolean(perm.can_edit))
          .map((perm) => ({
            resource: perm.resource,
            can_view: Boolean(perm.can_view),
            can_edit: Boolean(perm.can_edit),
          }))
      : []
  }

  if (form.password) {
    payload.password = form.password
  }

  return payload
}

const saveUser = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  if (!canManageBasic.value) {
    errorMessage.value = 'ユーザー基本情報を編集する権限がありません。'
    return
  }

  if (form.password && form.password !== passwordConfirm.value) {
    errorMessage.value = 'パスワードが一致しません。'
    return
  }

  saving.value = true
  try {
    const payload = buildPayload()
    if (isCreating.value) {
      const response = await api.accounts.createUser(payload)
      successMessage.value = 'ユーザーを作成しました。'
      isCreating.value = false
      await loadUsers()
      selectedUserId.value = response.data.id
      applyUserToForm(response.data)
    } else if (form.id) {
      const response = await api.accounts.updateUser(form.id, payload)
      successMessage.value = 'ユーザー情報を更新しました。'
      await loadUsers()
      selectedUserId.value = response.data.id
      applyUserToForm(response.data)
    }
  } catch (error) {
    const detail = error?.response?.data
    errorMessage.value = extractErrorMessage(detail) || '保存に失敗しました。'
  } finally {
    saving.value = false
  }
}

const deleteUser = async () => {
  if (!canManageBasic.value || !form.id) return
  if (!confirm(`ユーザー「${form.username}」を削除します。よろしいですか？`)) return

  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await api.accounts.deleteUser(form.id)
    successMessage.value = 'ユーザーを削除しました。'
    selectedUserId.value = null
    isCreating.value = false
    form.id = null
    form.username = ''
    form.email = ''
    form.first_name = ''
    form.last_name = ''
    form.is_active = true
    form.is_staff = false
    form.is_superuser = false
    form.password = ''
    passwordConfirm.value = ''
    form.profile = emptyProfile()
    form.permissions = emptyPermissions()
    form.effective_permission_details = []
    useUserPermissions.value = false
    await loadUsers()
  } catch (error) {
    const detail = error?.response?.data
    errorMessage.value = extractErrorMessage(detail) || '削除に失敗しました。'
  } finally {
    saving.value = false
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
  if (!isAdminUser.value) {
    errorMessage.value = 'この画面を開く権限がありません。'
    return
  }
  await Promise.all([
    loadDepartments(),
    loadDivisions(),
    loadGroups(),
    loadTeams(),
    loadUnits(),
    loadUsers(),
  ])
})

watch(filterDepartmentId, () => {
  filterGroupId.value = ''
  filterTeamId.value = ''
})

watch(filterGroupId, () => {
  filterTeamId.value = ''
  filterUnitId.value = ''
})

watch(filterTeamId, () => {
  filterUnitId.value = ''
})
</script>

<style scoped>
.user-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 12px;
}

.editor-header {
  margin-bottom: 12px;
}

.section-title {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-text {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.mode-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.mode-badge.create {
  background: #e7f6e9;
  color: #1a7f37;
  border: 1px solid #b7dfb9;
}

.mode-badge.edit {
  background: #e8f4ff;
  color: #0969da;
  border: 1px solid #b6d9f7;
}

.mode-badge.empty {
  background: #f6f8fa;
  color: #656d76;
  border: 1px solid #d0d7de;
}

.empty-state {
  padding: 40px 20px;
  text-align: center;
  color: #656d76;
  font-size: 13px;
  background: #f6f8fa;
  border-radius: 6px;
  border: 2px dashed #d0d7de;
}

.search-input {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  min-width: 220px;
}

.search-select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  min-width: 170px;
}

.filter-check {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #333;
  white-space: nowrap;
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

.btn.danger {
  background: #ef4444;
  border-color: #ef4444;
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

.data-table tbody tr.active {
  background: #dfe9ff;
}

.user-editor {
  border-left: 1px solid #e0e0e0;
  padding-left: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(140px, 1fr));
  gap: 10px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.form-row.full {
  grid-column: span 2;
}

.form-row.inline {
  flex-direction: row;
  align-items: center;
  gap: 6px;
}

.permission-section {
  margin-top: 6px;
}

.permission-helper-text {
  margin-top: 2px;
  font-size: 11px;
  font-weight: 400;
  color: #666;
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

.permission-table th {
  background: #f4f6ff;
  font-weight: 600;
}

.permission-source-cell {
  text-align: left !important;
  min-width: 280px;
}

.permission-source-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.permission-source-tag {
  display: inline-flex;
  align-items: center;
  border: 1px solid #d0d7de;
  border-radius: 999px;
  padding: 2px 8px;
  background: #f6f8fa;
  color: #444;
  font-size: 11px;
  line-height: 1.4;
}

.permission-source-tag.view {
  background: #eef6ff;
  border-color: #bfd9ff;
  color: #0b5cab;
}

.permission-source-tag.edit {
  background: #e7f6e9;
  border-color: #b7dfb9;
  color: #1a7f37;
}

.permission-source-empty {
  color: #888;
}

.form-row label {
  font-weight: 600;
}

.form-row input,
.form-row select {
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
}

.form-row select.multi-select {
  min-height: 88px;
  padding: 6px 8px;
}

.form-actions {
  grid-column: span 2;
  display: flex;
  gap: 8px;
  margin-top: 6px;
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

.status {
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 11px;
}

.status.active {
  background: #e7f6e9;
  color: #1a7f37;
}

.status.inactive {
  background: #ffeaea;
  color: #b42318;
}

@media (max-width: 1024px) {
  .user-grid {
    grid-template-columns: 1fr;
  }

  .user-editor {
    border-left: none;
    padding-left: 0;
    border-top: 1px solid #e0e0e0;
    padding-top: 12px;
  }
}
</style>
