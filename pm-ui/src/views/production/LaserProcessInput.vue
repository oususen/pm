<template>
  <div class="laser-actual-page" :class="[`mode-${activeTab}`]">

    <div class="tab-bar">
      <div class="tab-nav-actions">
        <DataSourceDialog title="レーザー実績入力" :sources="dsSources" />
        <button class="btn-inspection-nav btn-checksheet-nav" @click="openIntegratedChecksheetOperation">チェックシート実施</button>
        <button class="btn-inspection-nav" @click="openEquipmentInspection">設備点検</button>
      </div>
      <div class="tab-buttons">
        <button
          type="button"
          class="tab-item"
          :class="{ active: activeTab === 'entry' }"
          @click="activeTab = 'entry'"
        >
          実績入力
        </button>
        <button
          type="button"
          class="tab-item"
          :class="{ active: activeTab === 'list' }"
          @click="activeTab = 'list'"
        >
          一覧
        </button>
        <button
          type="button"
          class="tab-item"
          :class="{ active: activeTab === 'kadojiseki' }"
          @click="activeTab = 'kadojiseki'"
        >
          稼働記録
        </button>
      </div>
      <div v-if="activeTab === 'entry' && (form.pattern || currentProcessingMessages.length)" class="tab-operator-actions">
        <div v-if="currentProcessingMessages.length" class="current-processing-list">
          <div
            v-for="message in currentProcessingMessages"
            :key="`processing-${message.equipmentKey}`"
            class="current-processing"
            :class="{
              'current-processing--clickable': !!message.patternId,
              'current-processing--active': message.patternId && message.patternId === String(form.pattern || ''),
            }"
            @click="jumpToPattern(message)"
          >
            {{ message.label }}
          </div>
        </div>
        <div v-if="form.pattern" class="operator-action-btn-group">
          <button
            v-for="action in operatorActionOptions"
            :key="`tab-${action.value}`"
            type="button"
            class="operator-action-btn"
            :class="{ active: form.operator_action === action.value }"
            @click="form.operator_action = action.value"
          >
            {{ action.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-show="activeTab === 'entry'" class="entry-grid">
      <section class="panel form-panel">
        <div v-if="formMessage" class="message" :class="`is-${formMessageType}`">
          {{ formMessage }}
        </div>

        <div class="field">
          <label class="required">パターン番号（検索選択）</label>
          <div class="pattern-filters">
            <input
              v-model.trim="patternKeyword"
              type="text"
              placeholder="パターン番号で絞り込み"
            />
            <select v-model="patternMaterialFilter">
              <option value="">材料: すべて</option>
              <option v-for="mat in patternMaterialOptions" :key="mat" :value="mat">{{ mat }}</option>
            </select>
            <select v-model="patternEquipmentFilter">
              <option value="">設備: すべて</option>
              <option v-for="eq in laserEquipments" :key="eq.id" :value="String(eq.id)">
                {{ eq.equipment_code }} - {{ eq.equipment_name }}
              </option>
            </select>
          </div>
          <select v-model="form.pattern" class="pattern-select">
            <option value="">-- パターン選択 --</option>
            <option v-for="pattern in filteredPatterns" :key="pattern.id" :value="String(pattern.id)">
              {{ pattern.pattern_no }} / 材料:{{ pattern.material_code || '-' }} / 設備:{{ pattern.equipment_code || '-' }}
            </option>
          </select>
        </div>

        <div v-if="requiresActionReason" class="field">
          <label class="required">{{ form.operator_action === 'TEMP_END' ? '一時終了理由' : '中断理由' }}</label>
          <select v-model="form.operator_action_reason">
            <option value="">-- 選択 --</option>
            <option v-for="reason in operatorActionReasonOptions" :key="reason" :value="reason">
              {{ reason }}
            </option>
          </select>
        </div>

        <div v-if="requiresShotCount" class="field">
          <label class="required">回数</label>
          <input
            v-model.number="form.shot_count"
            type="number"
            min="1"
            step="1"
            inputmode="numeric"
            placeholder="1以上の整数"
          />
        </div>

        <div class="actions">
          <button class="btn primary" :disabled="!canSave || formSubmitting" @click="saveActual">
            {{ formSubmitting ? '処理中...' : '保存' }}
          </button>
          <button class="btn" :disabled="formSubmitting" @click="resetForm">クリア</button>
        </div>
      </section>

      <section class="panel component-panel">
        <div class="panel-head">
          <h3>構成部品詳細</h3>
        </div>

        <div v-if="selectedPattern" class="table-scroll component-table-scroll">
          <table>
            <thead>
              <tr>
                <th>品番</th>
                <th>取り数</th>
                <th>仕損</th>
                <th>仕損理由</th>
                <th>実績数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in componentRows" :key="row.product_id || row.product_code">
                <td>{{ row.product_code || '-' }}</td>
                <td class="num">{{ formatNumber(row.units_per_shot, 0) }}</td>
                <td class="num">
                  <input
                    class="table-input table-input-num"
                    type="number"
                    min="0"
                    step="1"
                    inputmode="numeric"
                    :value="row.scrap_qty_input"
                    @input="updateComponentScrapQty(row.product_id, $event.target.value)"
                  />
                </td>
                <td>
                  <select
                    class="table-input"
                    :value="row.scrap_reason"
                    @change="updateComponentScrapReason(row.product_id, $event.target.value)"
                  >
                    <option value="">-- 選択 --</option>
                    <option v-for="item in scrapReasonOptions" :key="item.value" :value="item.value">
                      {{ item.label }}
                    </option>
                  </select>
                </td>
                <td class="num">{{ formatNumber(row.total_qty, 0) }}</td>
              </tr>
              <tr v-if="!componentRows.length">
                <td colspan="5">構成部品はありません。</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="empty-pattern-message">
          パターンを選択すると構成部品を表示します。
        </div>
      </section>

      <section class="panel detail-panel">
        <div class="panel-head">
          <h3>加工情報</h3>
        </div>

        <div v-if="selectedPattern" class="detail-stack">
          <div class="summary-card">
            <div class="summary-grid">
              <div class="summary-item">
              <span class="summary-label">使用材料</span>
                <span class="summary-value">{{ selectedPattern.material_code || '-' }}</span>
              </div>
              <div class="summary-item">
              <span class="summary-label">1回あたり加工時間</span>
                <span class="summary-value">{{ formatNumber(processTimePerShot, 1) }} 分</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">使用設備（追加情報）</span>
                <span class="summary-value">{{ selectedEquipmentDisplay }}</span>
              </div>
              <div class="summary-item">
              <span class="summary-label">総加工時間</span>
                <span class="summary-value">{{ formatNumber(totalProcessTime, 1) }} 分</span>
              </div>
            </div>
          </div>

          <div class="snapshot-block">
            <h4>完成品一覧</h4>
            <div class="table-scroll finished-table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>完成品番号</th>
                    <th>完成品取り数</th>
                    <th>完成品実績換算数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in finishedRows" :key="row.product_id || row.product_code">
                    <td>{{ row.product_code || '-' }}</td>
                    <td class="num">{{ formatNumber(row.units_per_shot, 1) }}</td>
                    <td class="num">{{ formatNumber(row.total_qty, 1) }}</td>
                  </tr>
                  <tr v-if="!finishedRows.length">
                    <td colspan="3">完成品はありません。</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div v-else class="empty-pattern-message">
          パターンを選択すると詳細を表示します。
        </div>
      </section>
    </div>

    <!-- 稼働記録タブ -->
    <section v-show="activeTab === 'kadojiseki'" class="panel kadojiseki-panel">
      <div class="panel-head">
        <h3>稼働記録</h3>
      </div>

      <div v-if="kadoMessage" class="message" :class="`is-${kadoMessageType}`">
        {{ kadoMessage }}
      </div>

      <!-- 開始/終了モード切り替え -->
      <div class="kado-mode-bar">
        <button
          type="button"
          class="btn"
          :class="{ primary: kadoMode === 'start' }"
          @click="switchKadoMode('start')"
        >開始入力</button>
        <button
          type="button"
          class="btn"
          :class="{ primary: kadoMode === 'end' }"
          @click="switchKadoMode('end')"
        >終了入力</button>
      </div>

      <!-- 共通フィールド -->
      <div class="kado-form-grid">
        <div class="field">
          <label class="required">日付</label>
          <input v-model="kadoForm.work_date" type="date" @change="onKadoKeyChange" />
        </div>
        <div class="field">
          <label class="required">設備</label>
          <select v-model="kadoForm.equipment" @change="onKadoKeyChange">
            <option value="">-- 選択 --</option>
            <option v-for="eq in laserEquipments" :key="eq.id" :value="String(eq.id)">
              {{ eq.equipment_code }} - {{ eq.equipment_name }}
            </option>
          </select>
        </div>
        <div class="field">
          <label class="required">シフト</label>
          <select v-model="kadoForm.shift_no" @change="onKadoKeyChange">
            <option value="">-- 選択 --</option>
            <option value="1">1勤</option>
            <option value="2">2勤</option>
          </select>
        </div>
      </div>

      <!-- 開始モード -->
      <template v-if="kadoMode === 'start'">
        <!-- 前シフト情報バー -->
        <div v-if="kadoPrevShiftRecord" class="kado-prev-shift-bar">
          <template v-if="kadoPrevShiftRecord.end_totalizer_hour != null && !(kadoPrevShiftRecord.end_totalizer_hour === 0 && kadoPrevShiftRecord.end_totalizer_min === 0)">
            <span class="kado-existing-label">前シフト終了積算から自動セット:</span>
            <span class="kado-existing-value">
              {{ formatNumber(kadoPrevShiftRecord.end_totalizer_hour, 0) }} H
              {{ String(kadoPrevShiftRecord.end_totalizer_min).padStart(2,'0') }} M
            </span>
          </template>
          <template v-else>
            <span class="kado-existing-label">前シフト（{{ kadoPrevShiftRecord.shift_no_display }}）は未終了 →</span>
            <span class="kado-existing-value">保存時に今回の開始積算を前シフトの終了積算として自動登録します</span>
          </template>
        </div>
        <div class="kado-form-grid">
          <div class="field">
            <label class="required">開始積算 H</label>
            <input
              v-model.number="kadoForm.start_totalizer_hour"
              type="number" min="0" step="1" inputmode="numeric"
              placeholder="例: 15582"
            />
          </div>
          <div class="field">
            <label class="required">開始積算 M (0〜59)</label>
            <input
              v-model.number="kadoForm.start_totalizer_min"
              type="number" min="0" max="59" step="1" inputmode="numeric"
              placeholder="0〜59"
            />
          </div>
        </div>
        <div class="actions">
          <button class="btn primary" :disabled="!canSaveKadoStart || kadoSubmitting" @click="saveKadoStart">
            {{ kadoSubmitting ? '保存中...' : '開始を保存' }}
          </button>
          <button class="btn" :disabled="kadoSubmitting" @click="resetKadoForm">クリア</button>
        </div>
      </template>

      <!-- 終了モード -->
      <template v-if="kadoMode === 'end'">
        <!-- 既存レコードの開始積算を表示 -->
        <div v-if="kadoExistingRecord" class="kado-existing-info">
          <span class="kado-existing-label">開始積算:</span>
          <span class="kado-existing-value">
            {{ formatNumber(kadoExistingRecord.start_totalizer_hour, 0) }} H
            {{ kadoExistingRecord.start_totalizer_min }} M
          </span>
        </div>
        <div v-else-if="kadoKeyFilled && !kadoKeyLoading" class="message is-error">
          開始レコードが見つかりません。先に「開始入力」を行ってください。
        </div>
        <div v-if="kadoKeyLoading" class="message is-info">検索中...</div>

        <div v-if="kadoExistingRecord" class="kado-form-grid">
          <div class="field">
            <label class="required">終了積算 H</label>
            <input
              v-model.number="kadoForm.end_totalizer_hour"
              type="number" min="0" step="1" inputmode="numeric"
              placeholder="例: 15599"
            />
          </div>
          <div class="field">
            <label class="required">終了積算 M (0〜59)</label>
            <input
              v-model.number="kadoForm.end_totalizer_min"
              type="number" min="0" max="59" step="1" inputmode="numeric"
              placeholder="0〜59"
            />
          </div>
          <div class="field">
            <label class="required">仕事時間 (H)</label>
            <input
              v-model.number="kadoForm.work_hours"
              type="number" min="0.1" step="0.1" inputmode="decimal"
              placeholder="例: 21.0"
            />
          </div>
          <!-- 加工時間プレビュー -->
          <div v-if="kadoEndPreviewHours != null" class="field kado-preview">
            <label>加工時間（計算値）</label>
            <span class="kado-preview-value">{{ kadoEndPreviewHours }} H</span>
          </div>
          <div v-if="kadoEndPreviewRate != null" class="field kado-preview">
            <label>稼働率（計算値）</label>
            <span class="kado-preview-value">{{ kadoEndPreviewRate }} %</span>
          </div>
        </div>
        <div v-if="kadoExistingRecord" class="actions">
          <button class="btn primary" :disabled="!canSaveKadoEnd || kadoSubmitting" @click="saveKadoEnd">
            {{ kadoSubmitting ? '保存中...' : '終了を保存' }}
          </button>
          <button class="btn" :disabled="kadoSubmitting" @click="resetKadoForm">クリア</button>
        </div>
      </template>

      <!-- 検索フィルタ -->
      <div class="search-grid">
        <div class="field">
          <label>日付From</label>
          <input v-model="kadoFilters.work_date_from" type="date" />
        </div>
        <div class="field">
          <label>日付To</label>
          <input v-model="kadoFilters.work_date_to" type="date" />
        </div>
        <div class="field">
          <label>設備</label>
          <select v-model="kadoFilters.equipment">
            <option value="">すべて</option>
            <option v-for="eq in laserEquipments" :key="`kf-${eq.id}`" :value="String(eq.id)">
              {{ eq.equipment_code }} - {{ eq.equipment_name }}
            </option>
          </select>
        </div>
      </div>
      <div class="search-actions">
        <button class="btn primary" :disabled="kadoListLoading" @click="loadKadoRecords">
          {{ kadoListLoading ? '検索中...' : '検索' }}
        </button>
        <button class="btn" @click="resetKadoFilters">条件クリア</button>
        <button class="btn" :disabled="overtimeFetching" @click="fetchOvertimeWorkHoursBatch">
          {{ overtimeFetching ? '取得中...' : '取得' }}
        </button>
        <button class="btn" :disabled="Object.keys(pendingWorkHours).length === 0" @click="setOvertimeWorkHours">
          セット
        </button>
        <button class="btn primary" :disabled="!overtimeSetDone || overtimeSaving" @click="saveOvertimeWorkHours">
          {{ overtimeSaving ? '保存中...' : '保存' }}
        </button>
        <span v-if="overtimeMessage" class="kado-overtime-msg">{{ overtimeMessage }}</span>
      </div>

      <div class="result-meta">{{ kadoRecords.length }} 件</div>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>日付</th>
              <th>設備</th>
              <th>シフト</th>
              <th class="num">開始積算 H:M</th>
              <th class="num">終了積算 H:M</th>
              <th class="num">仕事時間</th>
              <th class="num">加工時間</th>
              <th class="num">稼働率</th>
              <th>状態</th>
              <th>更新日時</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="row in kadoRecords" :key="row.id">
              <!-- 通常表示行 -->
              <tr v-if="editingKadoId !== row.id">
                <td>{{ row.work_date }}</td>
                <td>{{ row.equipment_code || '-' }}{{ row.equipment_name ? ' ' + row.equipment_name : '' }}</td>
                <td>{{ row.shift_no_display || '-' }}</td>
                <td class="num">{{ formatNumber(row.start_totalizer_hour, 0) }}:{{ String(row.start_totalizer_min).padStart(2,'0') }}</td>
                <td class="num">
                  {{ row.end_totalizer_hour != null
                    ? `${formatNumber(row.end_totalizer_hour, 0)}:${String(row.end_totalizer_min).padStart(2,'0')}`
                    : '-' }}
                </td>
                <td class="num" :class="{ 'kado-pending-cell': overtimeSetDone && pendingWorkHours[row.id] != null }">
                  {{ overtimeSetDone && pendingWorkHours[row.id] != null
                    ? formatNumber(pendingWorkHours[row.id], 1)
                    : (row.work_hours != null ? formatNumber(row.work_hours, 1) : '-') }}
                </td>
                <td class="num">{{ row.process_hours != null ? formatNumber(row.process_hours, 1) : '-' }}</td>
                <td class="num">{{ row.operating_rate != null ? `${formatNumber(row.operating_rate, 1)} %` : '-' }}</td>
                <td>
                  <span class="kado-status" :class="row.is_completed ? 'completed' : 'started'">
                    {{ row.is_completed ? '終了済み' : '開始済み' }}
                  </span>
                </td>
                <td>{{ formatDateTime(row.updated_at) }}</td>
                <td class="kado-row-actions">
                  <button class="btn btn-sm" @click="startEditKado(row)">編集</button>
                  <button class="btn danger btn-sm" @click="deleteKadoRecord(row)">削除</button>
                </td>
              </tr>
              <!-- 編集行 -->
              <tr v-else class="kado-editing-row">
                <td>{{ row.work_date }}</td>
                <td>{{ row.equipment_code || '-' }}{{ row.equipment_name ? ' ' + row.equipment_name : '' }}</td>
                <td>{{ row.shift_no_display || '-' }}</td>
                <td class="num">
                  <input class="table-input table-input-num" type="number" min="0" step="1"
                    v-model.number="editKadoForm.start_totalizer_hour" style="width:70px" />
                  :
                  <input class="table-input table-input-num" type="number" min="0" max="59" step="1"
                    v-model.number="editKadoForm.start_totalizer_min" style="width:46px" />
                </td>
                <td class="num">
                  <input class="table-input table-input-num" type="number" min="0" step="1"
                    v-model.number="editKadoForm.end_totalizer_hour" placeholder="-" style="width:70px" />
                  :
                  <input class="table-input table-input-num" type="number" min="0" max="59" step="1"
                    v-model.number="editKadoForm.end_totalizer_min" placeholder="-" style="width:46px" />
                </td>
                <td class="num">
                  <input class="table-input table-input-num" type="number" min="0" step="0.1"
                    v-model.number="editKadoForm.work_hours" placeholder="-" style="width:60px" />
                </td>
                <td class="num">-</td>
                <td class="num">-</td>
                <td></td>
                <td></td>
                <td class="kado-row-actions">
                  <button class="btn primary btn-sm" :disabled="kadoEditSaving" @click="saveEditKado(row.id)">
                    {{ kadoEditSaving ? '...' : '保存' }}
                  </button>
                  <button class="btn btn-sm" @click="cancelEditKado">キャンセル</button>
                </td>
              </tr>
            </template>
            <tr v-if="!kadoRecords.length">
              <td colspan="11">データがありません。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-show="activeTab === 'list'" class="panel list-panel">
        <div class="panel-head">
          <h3>一覧 / 検索</h3>
        </div>

        <div v-if="listMessage" class="message" :class="`is-${listMessageType}`">
          {{ listMessage }}
        </div>

        <div class="search-grid">
          <div class="field">
            <label>日付From</label>
            <input v-model="filters.work_date_from" type="date" />
          </div>
          <div class="field">
            <label>日付To</label>
            <input v-model="filters.work_date_to" type="date" />
          </div>
          <div class="field">
            <label>設備</label>
            <select v-model="filters.equipment">
              <option value="">すべて</option>
              <option v-for="equipment in equipments" :key="`filter-${equipment.id}`" :value="String(equipment.id)">
                {{ equipment.equipment_code }} - {{ equipment.equipment_name }}
              </option>
            </select>
          </div>
          <div class="field">
            <label>パターン番号</label>
            <input
              v-model.trim="filters.pattern_no"
              type="text"
              placeholder="部分一致"
            />
          </div>
        </div>

        <div class="search-actions">
          <button class="btn primary" :disabled="listLoading" @click="loadActuals">
            {{ listLoading ? '検索中...' : '検索' }}
          </button>
          <button class="btn" :disabled="listLoading" @click="resetFilters">条件クリア</button>
        </div>

        <div class="result-meta">{{ actuals.length }} 件</div>

        <div class="table-scroll list-table">
          <table>
            <thead>
              <tr>
                <th>日付</th>
                <th>設備</th>
                <th>パターン番号</th>
                <th>作業時刻</th>
                <th class="num">回数</th>
                <th class="num">総加工時間</th>
                <th>登録者</th>
                <th>登録日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in actuals"
                :key="row.id"
              >
                <td>{{ row.work_date }}</td>
                <td>{{ row.equipment_code || '-' }}</td>
                <td>{{ row.pattern_no || '-' }}</td>
                <td>{{ operatorActionLabel(row.operator_action) }}</td>
                <td class="num">{{ formatNumber(row.shot_count, 0) }}</td>
                <td class="num">{{ formatNumber(row.total_process_time, 1) }}</td>
                <td>{{ row.created_by_name || '-' }}</td>
                <td>{{ formatDateTime(row.created_at) }}</td>
              </tr>
              <tr v-if="!actuals.length">
                <td colspan="8">データがありません。</td>
              </tr>
            </tbody>
          </table>
        </div>
    </section>

  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { authState } from '@/auth'
import { useRouter } from 'vue-router'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '取得/保存/削除', table: 't_laser_actual / t_laser_actual_detail', desc: 'レーザー実績・明細（ショット記録・品番別数量）' },
  { op: '取得/保存/更新/削除', table: 't_laser_shift_record', desc: 'レーザーシフト記録（勤務時間・稼働時間の管理）' },
  { op: '取得', table: 't_laser_pattern', desc: 'レーザーパターンマスタ（品番構成・1ショットあたり数量）' },
  { op: '取得', table: 'masters_equipment', desc: '設備マスタ（レーザー設備一覧）' },
]
import { getLocaleCode } from '@/i18n'

const router = useRouter()
const localeCode = computed(() => getLocaleCode())

function openEquipmentInspection() {
  router.push({ path: '/quality/equipment-inspection/operation' })
}

const resolveLaserLineId = async () => {
  const laserEquipment = (Array.isArray(equipments.value) ? equipments.value : []).find(
    (eq) => String(eq.line_name || '').includes('レーザ'),
  )
  const equipmentLineId = laserEquipment?.line_id || laserEquipment?.line || laserEquipment?.production_line || laserEquipment?.production_line_id
  if (equipmentLineId) return String(equipmentLineId)

  try {
    const res = await api.lines.getProductionLines({ page_size: 500 })
    const lines = normalizeList(res.data)
    const laserLine = (Array.isArray(lines) ? lines : []).find((line) => {
      const code = String(line.line_code || '')
      const name = String(line.line_name || '')
      return code.includes('LASER') || name.includes('レーザ')
    })
    if (laserLine?.id) return String(laserLine.id)
  } catch (error) {
    console.warn('レーザラインID解決に失敗:', error)
  }
  return ''
}

async function openIntegratedChecksheetOperation() {
  const lineId = await resolveLaserLineId()
  router.push({
    path: '/quality/product-checksheet/integrated/operation',
    query: {
      source: 'laser_process_input',
      ...(lineId ? { line_id: lineId } : {}),
    },
  })
}

const roundTo = (value, scale) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return 0
  const factor = Math.pow(10, scale)
  return Math.round(num * factor) / factor
}

const formatNumber = (value, fractionDigits = 1) => {
  const num = Number(value || 0)
  if (!Number.isFinite(num)) return '0'
  return num.toLocaleString(localeCode.value, {
    minimumFractionDigits: 0,
    maximumFractionDigits: fractionDigits,
  })
}

const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '-'
  return `${d.toLocaleDateString(localeCode.value)} ${d.toLocaleTimeString(localeCode.value, { hour: '2-digit', minute: '2-digit' })}`
}

const toYmd = (date) => {
  const d = new Date(date)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const todayYmd = () => {
  const d = new Date()
  return toYmd(d)
}

const businessDateYmd = () => {
  // 日替わりは8:00基準
  const d = new Date()
  if (d.getHours() < 8) {
    d.setDate(d.getDate() - 1)
  }
  return toYmd(d)
}

const shiftDateYmd = (offsetDays) => {
  const d = new Date()
  d.setDate(d.getDate() + offsetDays)
  return toYmd(d)
}

const operatorActionLabels = {
  START: '開始',
  END: '終了',
  PAUSE: '中断',
  TEMP_END: '一時終了',
  RESUME: '再開',
}

const notStartedOperatorActions = ['START']
const startedOperatorActions = ['END', 'PAUSE']
const pausedOperatorActions = ['RESUME', 'TEMP_END']
const tempEndedOperatorActions = ['RESUME']

const pauseReasonOptions = [
  '設備トラブル',
  '治具トラブル',
  '品質トラブル',
  'ティーチング',
  'ワイヤ交換',
  '部品ショート',
  '班長/対応者待ち',
  '工程指導',
  '3S活動',
  '改善活動',
  'パターン違い',
  'その他',
]

const tempEndReasonOptions = [
  '本日設備復旧不可',
  '本日治具使用不可',
  '他へ製品切り替え',
  'その他',
]

const scrapReasonOptions = [
  { value: '未切断', label: '1 未切断' },
  { value: 'ドロス', label: '2 ドロス' },
  { value: '欠肉', label: '3 欠肉' },
  { value: 'ズレ', label: '4 ズレ' },
  { value: 'キズ', label: '5 キズ' },
  { value: '錆', label: '6 錆' },
  { value: '変形', label: '7 変形' },
  { value: '穴無し', label: '8 穴無し' },
  { value: 'その他', label: '9 その他' },
]

const createEmptyForm = () => ({
  id: null,
  work_date: businessDateYmd(),
  equipment: '',
  pattern: '',
  operator_action: '',
  operator_action_reason: '',
  shot_count: null,
  remarks: '',
})

const createDefaultFilters = () => ({
  work_date_from: shiftDateYmd(-14),
  work_date_to: todayYmd(),
  equipment: '',
  pattern_no: '',
})

const normalizeList = (payload) => {
  if (Array.isArray(payload)) return payload
  if (Array.isArray(payload?.results)) return payload.results
  return []
}

// --- 稼働記録フォーム ---
const createEmptyKadoForm = () => ({
  work_date: businessDateYmd(),
  equipment: '',
  shift_no: '',
  start_totalizer_hour: '',
  start_totalizer_min: '',
  end_totalizer_hour: '',
  end_totalizer_min: '',
  work_hours: '',
})

const createDefaultKadoFilters = () => ({
  work_date_from: shiftDateYmd(-14),
  work_date_to: todayYmd(),
  equipment: '',
})

const kadoMode = ref('start')       // 'start' | 'end'
const kadoForm = ref(createEmptyKadoForm())
const kadoFilters = ref(createDefaultKadoFilters())
const kadoRecords = ref([])
const kadoExistingRecord = ref(null)  // 終了モード時に取得した既存レコード
const kadoKeyLoading = ref(false)
const kadoSubmitting = ref(false)
const kadoListLoading = ref(false)
const kadoMessage = ref('')
const kadoMessageType = ref('info')

const setKadoMessage = (message, type = 'info') => {
  kadoMessage.value = message
  kadoMessageType.value = type
}

// 日付・設備・シフトが揃っているか
const kadoKeyFilled = computed(() => (
  !!kadoForm.value.work_date &&
  !!kadoForm.value.equipment &&
  !!kadoForm.value.shift_no
))

// 開始保存バリデーション
const canSaveKadoStart = computed(() => {
  if (!kadoKeyFilled.value) return false
  const h = Number(kadoForm.value.start_totalizer_hour)
  if (!Number.isInteger(h) || h < 0) return false
  const m = Number(kadoForm.value.start_totalizer_min)
  if (!Number.isInteger(m) || m < 0 || m > 59) return false
  return true
})

// 終了保存バリデーション
const canSaveKadoEnd = computed(() => {
  if (!kadoExistingRecord.value) return false
  const h = Number(kadoForm.value.end_totalizer_hour)
  if (!Number.isInteger(h) || h < 0) return false
  const m = Number(kadoForm.value.end_totalizer_min)
  if (!Number.isInteger(m) || m < 0 || m > 59) return false
  const wh = Number(kadoForm.value.work_hours)
  if (!Number.isFinite(wh) || wh <= 0) return false
  return true
})

// 終了入力時のリアルタイム計算プレビュー
const kadoEndPreviewHours = computed(() => {
  if (!kadoExistingRecord.value) return null
  const endH = Number(kadoForm.value.end_totalizer_hour)
  const endM = Number(kadoForm.value.end_totalizer_min)
  if (!Number.isInteger(endH) || endH < 0) return null
  if (!Number.isInteger(endM) || endM < 0 || endM > 59) return null
  const rec = kadoExistingRecord.value
  const startMin = rec.start_totalizer_hour * 60 + rec.start_totalizer_min
  const endMin = endH * 60 + endM
  const diff = endMin - startMin
  if (diff < 0) return null
  return round(diff / 60, 1)
})

const kadoEndPreviewRate = computed(() => {
  const ph = kadoEndPreviewHours.value
  if (ph === null) return null
  const wh = Number(kadoForm.value.work_hours)
  if (!Number.isFinite(wh) || wh <= 0) return null
  return round(ph / wh * 100, 1)
})

const round = (v, d) => {
  const f = Math.pow(10, d)
  return Math.round(v * f) / f
}

// 前シフトの終了積算（開始入力モードで引き継ぎ用）
const kadoPrevShiftRecord = ref(null)

const switchKadoMode = (mode) => {
  kadoMode.value = mode
  kadoExistingRecord.value = null
  kadoPrevShiftRecord.value = null
  setKadoMessage('', 'info')
  if (kadoKeyFilled.value) {
    if (mode === 'end') fetchKadoExistingRecord()
    if (mode === 'start') fetchKadoPrevShiftRecord()
  }
}

// 終了モード・開始モード: 日付・設備・シフトが変わったら検索
const onKadoKeyChange = () => {
  kadoExistingRecord.value = null
  kadoPrevShiftRecord.value = null
  if (!kadoKeyFilled.value) return
  if (kadoMode.value === 'end') fetchKadoExistingRecord()
  if (kadoMode.value === 'start') fetchKadoPrevShiftRecord()
}

const fetchKadoExistingRecord = async () => {
  kadoKeyLoading.value = true
  try {
    const params = {
      work_date__gte: kadoForm.value.work_date,
      work_date__lte: kadoForm.value.work_date,
      equipment: kadoForm.value.equipment,
      shift_no: kadoForm.value.shift_no,
    }
    const res = await api.laserShiftRecords.getLaserShiftRecords(params)
    const rows = normalizeList(res.data)
    kadoExistingRecord.value = rows[0] || null
  } catch {
    kadoExistingRecord.value = null
  } finally {
    kadoKeyLoading.value = false
  }
}

// 開始入力モード: 直前シフト（終了済み）を取得して開始積算に自動セット
const fetchKadoPrevShiftRecord = async () => {
  if (!kadoForm.value.equipment || !kadoForm.value.work_date || !kadoForm.value.shift_no) return
  try {
    const res = await api.laserShiftRecords.getLaserShiftRecords({
      equipment: kadoForm.value.equipment,
      work_date__lte: kadoForm.value.work_date,
      ordering: '-work_date,-shift_no',
      page_size: 5,
    })
    const rows = normalizeList(res.data)
    const currentDate = kadoForm.value.work_date
    const currentShift = Number(kadoForm.value.shift_no)
    // 終了済み・未終了問わず直前シフトを探す
    const prev = rows.find((r) => {
      if (r.work_date < currentDate) return true
      if (r.work_date === currentDate && r.shift_no < currentShift) return true
      return false
    })
    kadoPrevShiftRecord.value = prev || null
    // 直前シフトが終了済み（0:00以外）なら開始積算に自動セット
    if (prev && prev.end_totalizer_hour != null && !(prev.end_totalizer_hour === 0 && prev.end_totalizer_min === 0)) {
      kadoForm.value.start_totalizer_hour = prev.end_totalizer_hour
      kadoForm.value.start_totalizer_min = prev.end_totalizer_min
    }
  } catch {
    kadoPrevShiftRecord.value = null
  }
}

const resetKadoForm = () => {
  kadoForm.value = createEmptyKadoForm()
  kadoExistingRecord.value = null
  setKadoMessage('', 'info')
}

const resetKadoFilters = async () => {
  kadoFilters.value = createDefaultKadoFilters()
  await loadKadoRecords()
}

const loadKadoRecords = async () => {
  kadoListLoading.value = true
  try {
    const params = {}
    if (kadoFilters.value.work_date_from) params.work_date__gte = kadoFilters.value.work_date_from
    if (kadoFilters.value.work_date_to) params.work_date__lte = kadoFilters.value.work_date_to
    if (kadoFilters.value.equipment) params.equipment = kadoFilters.value.equipment
    const res = await api.laserShiftRecords.getLaserShiftRecords(params)
    kadoRecords.value = normalizeList(res.data)
  } catch (error) {
    kadoRecords.value = []
    setKadoMessage(extractErrorMessage(error, '稼働記録の取得に失敗しました。'), 'error')
  } finally {
    kadoListLoading.value = false
  }
}

const saveKadoStart = async () => {
  if (!canSaveKadoStart.value || kadoSubmitting.value) return
  kadoSubmitting.value = true
  setKadoMessage('', 'info')
  try {
    const startH = Number(kadoForm.value.start_totalizer_hour)
    const startM = Number(kadoForm.value.start_totalizer_min)

    // 前シフトが終了未記録 or 0:00（仮置き）なら、今回の開始積算を前シフトの終了積算として自動セット
    const prev = kadoPrevShiftRecord.value
    if (prev && (prev.end_totalizer_hour == null || (prev.end_totalizer_hour === 0 && prev.end_totalizer_min === 0))) {
      await api.laserShiftRecords.patchLaserShiftRecord(prev.id, {
        end_totalizer_hour: startH,
        end_totalizer_min: startM,
      })
    }

    await api.laserShiftRecords.createLaserShiftRecord({
      work_date: kadoForm.value.work_date,
      equipment: Number(kadoForm.value.equipment),
      shift_no: Number(kadoForm.value.shift_no),
      start_totalizer_hour: startH,
      start_totalizer_min: startM,
    })
    setKadoMessage('開始を保存しました。', 'success')
    resetKadoForm()
    await loadKadoRecords()
  } catch (error) {
    setKadoMessage(extractErrorMessage(error, '保存に失敗しました。入力内容を確認してください。'), 'error')
  } finally {
    kadoSubmitting.value = false
  }
}

// --- 残業申請から仕事時間を一括取得・セット・保存 ---
const overtimeFetching = ref(false)
const overtimeSaving = ref(false)
const overtimeSetDone = ref(false)
const overtimeMessage = ref('')
const pendingWorkHours = ref({})  // { record_id: calculated_hours }

const calcWorkHoursFromApp = (app) => {
  const h = parseFloat(app.hours ?? 0)
  if (app.application_type === 'overtime') return Math.round((8 + h) * 10) / 10
  if (app.application_type === 'half_day_am') return Math.round((4 + h) * 10) / 10
  return h
}

// ① 取得: 残業申請を取得してpendingWorkHoursに格納（DBは変更しない）
const fetchOvertimeWorkHoursBatch = async () => {
  const from = kadoFilters.value.work_date_from
  const to = kadoFilters.value.work_date_to
  if (!from || !to) {
    overtimeMessage.value = '日付Fromと日付Toを指定してください'
    return
  }
  const targets = kadoRecords.value.filter(r => r.work_hours == null)
  if (targets.length === 0) {
    overtimeMessage.value = '対象レコードがありません（仕事時間未設定）'
    return
  }
  overtimeFetching.value = true
  overtimeMessage.value = ''
  pendingWorkHours.value = {}
  overtimeSetDone.value = false
  try {
    const userIds = [...new Set(targets.map(r => r.created_by).filter(Boolean))]
    const appMap = {}
    for (const userId of userIds) {
      const res = await api.overtime.getApplications({
        work_date__gte: from,
        work_date__lte: to,
        applicant: userId,
        page_size: 200,
      })
      for (const app of normalizeList(res.data)) {
        const key = `${app.applicant}_${app.work_date}`
        if (!appMap[key]) appMap[key] = app
      }
    }
    const pending = {}
    for (const record of targets) {
      const key = `${record.created_by}_${record.work_date}`
      const app = appMap[key]
      if (!app) continue
      pending[record.id] = calcWorkHoursFromApp(app)
    }
    pendingWorkHours.value = pending
    const count = Object.keys(pending).length
    overtimeMessage.value = count > 0
      ? `${count}件 取得しました。内容を確認してセットしてください。`
      : '対象日の残業申請が見つかりませんでした'
  } catch {
    overtimeMessage.value = '取得に失敗しました'
  } finally {
    overtimeFetching.value = false
  }
}

// ② セット: pendingWorkHoursを一覧上に反映（黄色表示、DBは変更しない）
const setOvertimeWorkHours = () => {
  overtimeSetDone.value = true
  const count = Object.keys(pendingWorkHours.value).length
  overtimeMessage.value = `${count}件 セットしました。内容を確認して保存してください。`
}

// ③ 保存: pendingWorkHoursをDBにパッチ保存
const saveOvertimeWorkHours = async () => {
  const entries = Object.entries(pendingWorkHours.value)
  if (entries.length === 0) return
  overtimeSaving.value = true
  overtimeMessage.value = ''
  try {
    for (const [recordId, hours] of entries) {
      await api.laserShiftRecords.patchLaserShiftRecord(Number(recordId), { work_hours: hours })
    }
    overtimeMessage.value = `${entries.length}件 保存しました`
    pendingWorkHours.value = {}
    overtimeSetDone.value = false
    await loadKadoRecords()
  } catch {
    overtimeMessage.value = '保存に失敗しました'
  } finally {
    overtimeSaving.value = false
  }
}

// --- 稼働記録 インライン編集 ---
const editingKadoId = ref(null)
const editKadoForm = ref({})
const kadoEditSaving = ref(false)

const startEditKado = (row) => {
  editingKadoId.value = row.id
  editKadoForm.value = {
    start_totalizer_hour: row.start_totalizer_hour,
    start_totalizer_min: row.start_totalizer_min,
    end_totalizer_hour: row.end_totalizer_hour ?? '',
    end_totalizer_min: row.end_totalizer_min ?? '',
    work_hours: row.work_hours ?? '',
  }
}

const cancelEditKado = () => {
  editingKadoId.value = null
  editKadoForm.value = {}
}

const saveEditKado = async (id) => {
  kadoEditSaving.value = true
  try {
    const f = editKadoForm.value
    const payload = {
      start_totalizer_hour: Number(f.start_totalizer_hour),
      start_totalizer_min: Number(f.start_totalizer_min),
      end_totalizer_hour: f.end_totalizer_hour !== '' ? Number(f.end_totalizer_hour) : null,
      end_totalizer_min: f.end_totalizer_min !== '' ? Number(f.end_totalizer_min) : null,
      work_hours: f.work_hours !== '' ? Number(f.work_hours) : null,
    }
    await api.laserShiftRecords.patchLaserShiftRecord(id, payload)
    cancelEditKado()
    await loadKadoRecords()
  } catch (error) {
    setKadoMessage(extractErrorMessage(error, '更新に失敗しました。'), 'error')
  } finally {
    kadoEditSaving.value = false
  }
}

const deleteKadoRecord = async (row) => {
  if (!confirm(`${row.work_date} ${row.equipment_code} ${row.shift_no_display} の記録を削除しますか？`)) return
  try {
    await api.laserShiftRecords.deleteLaserShiftRecord(row.id)
    await loadKadoRecords()
  } catch (error) {
    setKadoMessage(extractErrorMessage(error, '削除に失敗しました。'), 'error')
  }
}

const saveKadoEnd = async () => {
  if (!canSaveKadoEnd.value || kadoSubmitting.value) return
  kadoSubmitting.value = true
  setKadoMessage('', 'info')
  try {
    await api.laserShiftRecords.patchLaserShiftRecord(kadoExistingRecord.value.id, {
      end_totalizer_hour: Number(kadoForm.value.end_totalizer_hour),
      end_totalizer_min: Number(kadoForm.value.end_totalizer_min),
      work_hours: Number(kadoForm.value.work_hours),
    })
    setKadoMessage('終了を保存しました。', 'success')
    resetKadoForm()
    await loadKadoRecords()
  } catch (error) {
    setKadoMessage(extractErrorMessage(error, '保存に失敗しました。入力内容を確認してください。'), 'error')
  } finally {
    kadoSubmitting.value = false
  }
}

const form = ref(createEmptyForm())
const filters = ref(createDefaultFilters())
const equipments = ref([])
const patterns = ref([])
const actuals = ref([])
const latestActionByPattern = ref({})
const patternKeyword = ref('')
const patternMaterialFilter = ref('')
const patternEquipmentFilter = ref('')
const activeTab = ref('entry')
const currentProcessingByEquipment = ref({})
const componentScrapInputs = ref({})

const formSubmitting = ref(false)
const listLoading = ref(false)

const formMessage = ref('')
const formMessageType = ref('info')
const listMessage = ref('')
const listMessageType = ref('info')

const setFormMessage = (message, type = 'info') => {
  formMessage.value = message
  formMessageType.value = type
}

const setListMessage = (message, type = 'info') => {
  listMessage.value = message
  listMessageType.value = type
}

const clearMessages = () => {
  formMessage.value = ''
  listMessage.value = ''
}

// レーザーライン（line_name に「レーザ」を含む）の設備のみ（稼働記録タブ用）
const laserEquipments = computed(() => {
  return (Array.isArray(equipments.value) ? equipments.value : []).filter(
    (eq) => String(eq.line_name || '').includes('レーザ')
  )
})

const patternMaterialOptions = computed(() => {
  const source = Array.isArray(patterns.value) ? patterns.value : []
  const codes = [...new Set(source.map((p) => String(p.material_code || '')).filter(Boolean))]
  return codes.sort()
})

const filteredPatterns = computed(() => {
  const source = Array.isArray(patterns.value) ? patterns.value : []
  const keyword = String(patternKeyword.value || '').trim().toLowerCase()
  const matFilter = String(patternMaterialFilter.value || '').trim()
  const eqFilter = String(patternEquipmentFilter.value || '').trim()
  return source.filter((pattern) => {
    if (keyword && !String(pattern.pattern_no || '').toLowerCase().includes(keyword)) return false
    if (matFilter && String(pattern.material_code || '') !== matFilter) return false
    if (eqFilter && String(pattern.equipment || '') !== eqFilter) return false
    return true
  })
})

const selectedPattern = computed(() => {
  if (!form.value.pattern) return null
  return (
    (Array.isArray(patterns.value) ? patterns.value : []).find(
      (pattern) => String(pattern.id) === String(form.value.pattern)
    ) || null
  )
})

const resolvedEquipmentId = computed(() => {
  if (selectedPattern.value?.equipment) return String(selectedPattern.value.equipment)
  return String(form.value.equipment || '')
})

const latestActionByPatternFromList = computed(() => {
  const map = {}
  const rows = Array.isArray(actuals.value) ? actuals.value : []
  for (const row of rows) {
    const patternId = String(row?.pattern || '')
    if (!patternId || map[patternId]) continue
    const action = String(row?.operator_action || '').toUpperCase()
    if (!action) continue
    map[patternId] = action
  }
  return map
})

const selectedPatternLatestOperatorAction = computed(() => {
  const patternId = String(form.value.pattern || '')
  if (!patternId) return ''
  const cached = String(latestActionByPattern.value[patternId] || '').toUpperCase()
  if (cached) return cached
  return String(latestActionByPatternFromList.value[patternId] || '').toUpperCase()
})

const selectedPatternWorkState = computed(() => {
  const latestAction = selectedPatternLatestOperatorAction.value
  if (latestAction === 'PAUSE') return 'PAUSED'
  if (latestAction === 'TEMP_END') return 'TEMP_ENDED'
  if (latestAction === 'START' || latestAction === 'RESUME') return 'STARTED'
  return 'NOT_STARTED'
})

const buildEquipmentKey = (equipmentId, equipmentCode, equipmentName) => {
  const idKey = String(equipmentId || '').trim()
  if (idKey) return `id:${idKey}`
  const codeKey = String(equipmentCode || '').trim()
  if (codeKey) return `code:${codeKey}`
  const nameKey = String(equipmentName || '').trim()
  if (nameKey) return `name:${nameKey}`
  return ''
}

const buildEquipmentLabel = (equipmentName, equipmentId = '') => {
  const name = String(equipmentName || '').trim()
  if (name) return name

  const idKey = String(equipmentId || '').trim()
  if (!idKey) return ''
  const equipment = (Array.isArray(equipments.value) ? equipments.value : []).find(
    (row) => String(row.id) === idKey
  )
  return String(equipment?.equipment_name || '').trim()
}

const currentProcessingMessages = computed(() => {
  const rows = Object.entries(currentProcessingByEquipment.value || {})
    .map(([equipmentKey, item]) => ({
      equipmentKey,
      equipmentLabel: String(item?.equipmentLabel || '').trim(),
      patternNo: String(item?.patternNo || '').trim(),
      patternId: String(item?.patternId || '').trim(),
    }))
    .filter((item) => !!item.equipmentLabel)
    .sort((a, b) => a.equipmentLabel.localeCompare(b.equipmentLabel))

  return rows.map((item) => ({
    equipmentKey: item.equipmentKey,
    patternId: item.patternId,
    patternNo: item.patternNo,
    label: item.patternNo
      ? `現在${item.equipmentLabel}はパターン${item.patternNo}加工中`
      : `現在${item.equipmentLabel}は加工中`,
  }))
})

const updateCurrentProcessingState = (actionValue, equipmentId, equipmentCode, equipmentName, patternNo, patternId) => {
  const action = String(actionValue || '').toUpperCase()
  const equipmentKey = buildEquipmentKey(equipmentId, equipmentCode, equipmentName)
  if (!action || !equipmentKey) return
  const label = buildEquipmentLabel(equipmentName, equipmentId)
  const pno = String(patternNo || '').trim()
  const pid = String(patternId || '').trim()

  if (action === 'START' || action === 'RESUME') {
    currentProcessingByEquipment.value = {
      ...currentProcessingByEquipment.value,
      [equipmentKey]: {
        equipmentLabel: label,
        patternNo: pno,
        patternId: pid,
      },
    }
    return
  }

  if (action === 'END' || action === 'PAUSE' || action === 'TEMP_END') {
    const next = { ...currentProcessingByEquipment.value }
    delete next[equipmentKey]
    currentProcessingByEquipment.value = next
  }
}

const operatorActionOptions = computed(() => {
  const toOptions = (actions) =>
    actions.map((value) => ({
      value,
      label: operatorActionLabels[value],
    }))

  if (!form.value.pattern) return []
  if (selectedPatternWorkState.value === 'STARTED') return toOptions(startedOperatorActions)
  if (selectedPatternWorkState.value === 'PAUSED') return toOptions(pausedOperatorActions)
  if (selectedPatternWorkState.value === 'TEMP_ENDED') return toOptions(tempEndedOperatorActions)
  return toOptions(notStartedOperatorActions)
})

const requiresShotCount = computed(() => {
  const action = String(form.value.operator_action || '').toUpperCase()
  return action === 'END' || action === 'PAUSE'
})

const requiresActionReason = computed(() => {
  const action = String(form.value.operator_action || '').toUpperCase()
  return action === 'PAUSE' || action === 'TEMP_END'
})

const operatorActionReasonOptions = computed(() => {
  const action = String(form.value.operator_action || '').toUpperCase()
  if (action === 'TEMP_END') return tempEndReasonOptions
  return pauseReasonOptions
})

const effectiveShotCount = computed(() => {
  const shots = Number(form.value.shot_count)
  if (!Number.isInteger(shots) || shots < 0) return 0
  return shots
})

const isValidShotCount = computed(() => {
  const shots = Number(form.value.shot_count)
  if (!Number.isInteger(shots)) return false
  if (!requiresShotCount.value) return shots === 0
  const action = String(form.value.operator_action || '').toUpperCase()
  if (action === 'PAUSE') return shots >= 0
  return shots >= 1
})

const processTimePerShot = computed(() => {
  if (!selectedPattern.value) return 0
  return roundTo(selectedPattern.value.process_time_min, 1)
})

const totalProcessTime = computed(() => {
  if (!selectedPattern.value) return 0
  return roundTo(processTimePerShot.value * effectiveShotCount.value, 1)
})

const selectedEquipmentDisplay = computed(() => {
  const pattern = selectedPattern.value
  if (!pattern) return '-'

  const code = String(pattern.equipment_code || '').trim()
  const name = String(pattern.equipment_name || '').trim()
  if (code && name) return `${code} - ${name}`
  if (code) return code
  if (name) return name

  const equipmentId = String(pattern.equipment || resolvedEquipmentId.value || '').trim()
  if (!equipmentId) return '-'
  const equipment = (Array.isArray(equipments.value) ? equipments.value : []).find(
    (row) => String(row.id) === equipmentId
  )
  if (!equipment) return '-'
  const eqCode = String(equipment.equipment_code || '').trim()
  const eqName = String(equipment.equipment_name || '').trim()
  if (eqCode && eqName) return `${eqCode} - ${eqName}`
  if (eqCode) return eqCode
  if (eqName) return eqName
  return '-'
})

const buildScrapInputKey = (productId) => {
  const patternId = String(form.value.pattern || '')
  const pid = String(productId || '')
  return `${patternId}:${pid}`
}

const normalizeScrapQtyInput = (value, grossQty) => {
  const text = String(value ?? '').trim()
  if (!text) {
    return { qty: 0, input: '' }
  }
  const raw = Number(text)
  if (!Number.isFinite(raw) || raw <= 0) {
    return { qty: 0, input: '' }
  }
  const max = Number(grossQty || 0)
  if (!Number.isFinite(max) || max <= 0) {
    return { qty: 0, input: '' }
  }
  const qty = Math.min(Math.floor(raw), Math.floor(max))
  return { qty, input: String(qty) }
}

const getComponentScrapState = (productId) => {
  const key = buildScrapInputKey(productId)
  return componentScrapInputs.value[key] || { qtyInput: '', reason: '' }
}

const updateComponentScrapQty = (productId, value) => {
  const target = componentRows.value.find((row) => String(row.product_id) === String(productId))
  if (!target) return
  const key = buildScrapInputKey(productId)
  const current = getComponentScrapState(productId)
  const normalized = normalizeScrapQtyInput(value, target.gross_qty)
  componentScrapInputs.value = {
    ...componentScrapInputs.value,
    [key]: {
      qtyInput: normalized.input,
      reason: current.reason || '',
    },
  }
}

const updateComponentScrapReason = (productId, value) => {
  const key = buildScrapInputKey(productId)
  const current = getComponentScrapState(productId)
  componentScrapInputs.value = {
    ...componentScrapInputs.value,
    [key]: {
      qtyInput: current.qtyInput || '',
      reason: String(value || ''),
    },
  }
}

const componentRows = computed(() => {
  if (!selectedPattern.value) return []
  const shots = effectiveShotCount.value
  const rows = Array.isArray(selectedPattern.value.component_items)
    ? selectedPattern.value.component_items
    : []
  return rows.map((row) => {
    const units = Number(row.take_qty || 0)
    const grossQty = roundTo(units * shots, 0)
    const scrapState = getComponentScrapState(row.component_product)
    const normalizedScrap = normalizeScrapQtyInput(scrapState.qtyInput, grossQty)
    const scrapQty = normalizedScrap.qty
    return {
      product_id: row.component_product,
      product_code: row.component_product_code || '',
      units_per_shot: units,
      gross_qty: grossQty,
      scrap_qty_input: normalizedScrap.input,
      scrap_qty: scrapQty,
      scrap_reason: String(scrapState.reason || ''),
      total_qty: roundTo(grossQty - scrapQty, 0),
    }
  })
})

const hasInvalidComponentScrap = computed(() => componentRows.value.some((row) => (
  Number(row.scrap_qty || 0) > 0 && !String(row.scrap_reason || '').trim()
)))

const finishedRows = computed(() => {
  if (!selectedPattern.value) return []
  const shots = effectiveShotCount.value
  const rows = Array.isArray(selectedPattern.value.finished_items)
    ? selectedPattern.value.finished_items
    : []
  return rows.map((row) => {
    const units = Number(row.units_per_shot || 0)
    return {
      product_id: row.finished_product,
      product_code: row.finished_product_code || '',
      units_per_shot: roundTo(units, 1),
      total_qty: roundTo(units * shots, 1),
    }
  })
})

const canSave = computed(() => {
  if (!form.value.work_date) return false
  if (!resolvedEquipmentId.value) return false
  if (!form.value.pattern) return false
  if (!form.value.operator_action) return false
  if (!operatorActionOptions.value.some((item) => item.value === form.value.operator_action)) return false
  if (requiresActionReason.value && !String(form.value.operator_action_reason || '').trim()) return false
  if (!isValidShotCount.value) return false
  if (hasInvalidComponentScrap.value) return false
  return true
})

const operatorActionLabel = (value) => {
  const key = String(value || '').toUpperCase()
  return operatorActionLabels[key] || '-'
}

const extractErrorMessage = (error, fallback) => {
  const payload = error?.response?.data
  if (typeof payload === 'string' && payload.trim()) return payload.trim()
  if (payload?.detail) return String(payload.detail)
  if (payload && typeof payload === 'object') {
    const firstKey = Object.keys(payload)[0]
    if (firstKey) {
      const val = payload[firstKey]
      if (Array.isArray(val) && val.length) {
        return `${firstKey}: ${val.join(', ')}`
      }
      if (typeof val === 'string' && val) {
        return `${firstKey}: ${val}`
      }
    }
  }
  return fallback
}

const loadEquipments = async () => {
  try {
    const res = await api.equipments.getEquipments({ is_active: true, page_size: 500 })
    equipments.value = normalizeList(res.data)
  } catch (error) {
    equipments.value = []
    setListMessage(extractErrorMessage(error, '設備一覧の取得に失敗しました。'), 'error')
  }
}

const loadPatterns = async () => {
  try {
    const res = await api.laserPatterns.getLaserPatterns({ page_size: 500 })
    patterns.value = normalizeList(res.data)
  } catch (error) {
    patterns.value = []
    setListMessage(extractErrorMessage(error, 'パターン一覧の取得に失敗しました。'), 'error')
  }
}

const buildSearchParams = () => {
  const params = {}
  if (filters.value.work_date_from) params.work_date__gte = filters.value.work_date_from
  if (filters.value.work_date_to) params.work_date__lte = filters.value.work_date_to
  if (filters.value.equipment) params.equipment = filters.value.equipment
  if (filters.value.pattern_no) params.pattern_no = filters.value.pattern_no
  return params
}

const loadActuals = async () => {
  listLoading.value = true
  setListMessage('', 'info')
  try {
    const res = await api.laserActuals.getLaserActuals(buildSearchParams())
    actuals.value = normalizeList(res.data)
  } catch (error) {
    actuals.value = []
    setListMessage(extractErrorMessage(error, '一覧の取得に失敗しました。'), 'error')
  } finally {
    listLoading.value = false
  }
}

const loadLatestActionForPattern = async (patternId) => {
  const pid = String(patternId || '').trim()
  if (!pid) return
  try {
    const params = {
      pattern: pid,
      ordering: '-created_at',
      page_size: 1,
    }
    if (resolvedEquipmentId.value) {
      params.equipment = resolvedEquipmentId.value
    }
    const res = await api.laserActuals.getLaserActuals(params)
    const rows = normalizeList(res.data)
    const action = String(rows[0]?.operator_action || '').toUpperCase()
    latestActionByPattern.value = {
      ...latestActionByPattern.value,
      [pid]: action,
    }
  } catch (error) {
    // 最新アクション取得失敗時は一覧データからの推定にフォールバック
  }
}

const loadCurrentProcessingState = async () => {
  try {
    const res = await api.laserActuals.getCurrentProcessing({
      scan_limit: 2000,
    })
    const rows = normalizeList(res.data)

    const nextState = {}
    rows.forEach((row) => {
      const key = buildEquipmentKey(row?.equipment, row?.equipment_code, row?.equipment_name)
      if (!key) return
      nextState[key] = {
        equipmentLabel: buildEquipmentLabel(row?.equipment_name, row?.equipment),
        patternNo: String(row?.pattern_no || '').trim(),
        patternId: String(row?.pattern || '').trim(),
      }
    })
    currentProcessingByEquipment.value = nextState
  } catch (error) {
    // 軽量API失敗時は従来の一覧取得ロジックでフォールバック
    try {
      const res = await api.laserActuals.getLaserActuals({
        ordering: '-created_at',
        page_size: 500,
      })
      const rows = normalizeList(res.data)

      const latestByEquipment = {}
      for (const row of rows) {
        const key = buildEquipmentKey(row?.equipment, row?.equipment_code, row?.equipment_name)
        if (!key || latestByEquipment[key]) continue
        latestByEquipment[key] = row
      }

      const nextState = {}
      Object.values(latestByEquipment).forEach((row) => {
        const action = String(row?.operator_action || '').toUpperCase()
        if (!(action === 'START' || action === 'RESUME')) return
        const key = buildEquipmentKey(row?.equipment, row?.equipment_code, row?.equipment_name)
        if (!key) return
        nextState[key] = {
          equipmentLabel: buildEquipmentLabel(row?.equipment_name, row?.equipment),
          patternNo: String(row?.pattern_no || '').trim(),
          patternId: String(row?.pattern || '').trim(),
        }
      })
      currentProcessingByEquipment.value = nextState
    } catch {
      // 表示復元失敗時はそのまま入力を継続可能にする
    }
  }
}

const jumpToPattern = (message) => {
  if (!message.patternId) return
  form.value.pattern = message.patternId
  patternKeyword.value = message.patternNo
}

const resetForm = () => {
  form.value = createEmptyForm()
  componentScrapInputs.value = {}
  patternKeyword.value = ''
  setFormMessage('', 'info')
}

const resetFilters = async () => {
  filters.value = createDefaultFilters()
  await loadActuals()
}

const saveActual = async () => {
  if (!canSave.value || formSubmitting.value) return
  formSubmitting.value = true
  setFormMessage('', 'info')

  const payload = {
    work_date: form.value.work_date,
    equipment: Number(resolvedEquipmentId.value),
    pattern: Number(form.value.pattern),
    operator_action: String(form.value.operator_action || 'END').toUpperCase(),
    operator_action_reason: String(form.value.operator_action_reason || '').trim(),
    shot_count: Number(form.value.shot_count),
    component_scraps: componentRows.value
      .map((row) => ({
        product: Number(row.product_id),
        scrap_qty: Number(row.scrap_qty || 0),
        scrap_reason: String(row.scrap_reason || '').trim(),
      }))
      .filter((row) => row.product > 0 && row.scrap_qty > 0),
    remarks: form.value.remarks || '',
  }

  try {
    const res = await api.laserActuals.createLaserActual(payload)
    const saved = res?.data || null
    const savedAction = String(saved?.operator_action || payload.operator_action || '').toUpperCase()
    const savedPatternNo = String(saved?.pattern_no || selectedPattern.value?.pattern_no || '').trim()
    setFormMessage('保存しました。', 'success')
    if (saved?.pattern && saved?.operator_action) {
      latestActionByPattern.value = {
        ...latestActionByPattern.value,
        [String(saved.pattern)]: String(saved.operator_action).toUpperCase(),
      }
    }
    updateCurrentProcessingState(
      savedAction,
      saved?.equipment || payload.equipment,
      saved?.equipment_code || selectedPattern.value?.equipment_code || '',
      saved?.equipment_name || selectedPattern.value?.equipment_name || '',
      savedPatternNo,
      saved?.pattern || payload.pattern,
    )
    resetForm()
    await loadActuals()
  } catch (error) {
    setFormMessage(extractErrorMessage(error, '保存に失敗しました。入力内容を確認してください。'), 'error')
  } finally {
    formSubmitting.value = false
  }
}

watch(
  () => form.value.pattern,
  async (patternId) => {
    // パターン変更時は前回の警告をクリア
    if (formMessageType.value === 'warning') setFormMessage('', 'info')
    if (!patternId) {
      form.value.operator_action = ''
      form.value.operator_action_reason = ''
      form.value.shot_count = null
      return
    }
    const selected = patterns.value.find((pattern) => String(pattern.id) === String(patternId))
    if (selected) {
      patternKeyword.value = selected.pattern_no || ''
      form.value.equipment = selected.equipment ? String(selected.equipment) : ''
    }
    await loadLatestActionForPattern(patternId)
    // 当日同一パターンの重複チェック
    await checkDuplicatePatternToday(patternId)
  }
)

const checkDuplicatePatternToday = async (patternId) => {
  const pid = String(patternId || '').trim()
  if (!pid) return
  try {
    const today = businessDateYmd()
    const res = await api.laserActuals.getLaserActuals({
      pattern: pid,
      work_date__gte: today,
      work_date__lte: today,
      operator_action: 'END',
      page_size: 1,
    })
    const rows = normalizeList(res.data)
    if (rows.length > 0) {
      const patternNo = selectedPattern.value?.pattern_no || pid
      setFormMessage(`⚠ パターン ${patternNo} は本日すでに実績が登録されています。`, 'warning')
    }
  } catch {
    // チェック失敗時は警告なしで続行
  }
}

watch(
  () => operatorActionOptions.value.map((item) => item.value).join('|'),
  () => {
    const options = operatorActionOptions.value
    if (!options.length) {
      form.value.operator_action = ''
      return
    }
    if (!options.some((item) => item.value === form.value.operator_action)) {
      form.value.operator_action = options[0].value
    }
  },
  { immediate: true }
)

watch(
  () => form.value.operator_action,
  (action) => {
    const key = String(action || '').toUpperCase()
    if (!(key === 'PAUSE' || key === 'TEMP_END')) {
      form.value.operator_action_reason = ''
    }
    if (!(key === 'END' || key === 'PAUSE')) {
      form.value.shot_count = null
    }
  },
  { immediate: true }
)

onMounted(async () => {
  clearMessages()
  const processingStatePromise = loadCurrentProcessingState()
  await Promise.all([loadEquipments(), loadPatterns()])
  await Promise.all([loadActuals(), loadKadoRecords()])
  await processingStatePromise
})
</script>

<style scoped>
.laser-actual-page {
  padding: 14px;
  display: grid;
  gap: 12px;
}

.laser-actual-page.mode-entry {
  grid-template-columns: minmax(340px, 0.95fr) minmax(560px, 1.45fr);
  grid-template-areas:
    "tab component"
    "form component"
    "detail component";
  align-items: start;
}

.laser-actual-page.mode-list {
  grid-template-columns: 1fr;
  grid-template-areas:
    "tab"
    "list";
  align-items: start;
}

.laser-actual-page.mode-kadojiseki {
  grid-template-columns: 1fr;
  grid-template-areas:
    "tab"
    "kadojiseki";
  align-items: start;
}

.tab-bar {
  grid-area: tab;
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  justify-self: stretch;
  width: 100%;
}

.btn-inspection-nav {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #0e7490;
  background: #fff;
  color: #0e7490;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  flex-shrink: 0;
}
.tab-nav-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.btn-checksheet-nav {
  border-color: #2563eb;
  color: #2563eb;
}
.tab-buttons {
  display: flex;
  gap: 8px;
}

.tab-operator-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: flex-end;
}

.current-processing-list {
  display: grid;
  gap: 4px;
}

.current-processing {
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 16px;
  font-weight: 700;
}

.current-processing--clickable {
  cursor: pointer;
}

.current-processing--clickable:hover {
  background: #dbeafe;
  border-color: #3b82f6;
}

.current-processing--active {
  background: #dcfce7;
  border-color: #16a34a;
  color: #15803d;
}

.current-processing--active:hover {
  background: #bbf7d0;
  border-color: #15803d;
}

.tab-item {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  padding: 9px 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.tab-item.active {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
}

.entry-grid {
  display: contents;
}

.form-panel {
  grid-area: form;
}

.detail-panel {
  grid-area: detail;
}

.component-panel {
  grid-area: component;
  min-height: 0;
}

.list-panel {
  grid-area: list;
}

.kadojiseki-panel {
  grid-area: kadojiseki;
}

.kado-mode-bar {
  display: flex;
  gap: 8px;
}

.kado-form-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.kado-preview {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 8px 10px;
}

.kado-preview-value {
  font-size: 16px;
  font-weight: 700;
  color: #166534;
}

.kado-prev-shift-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  font-size: 14px;
  flex-wrap: wrap;
}


.kado-existing-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 14px;
}

.kado-pending-cell {
  background: #fef9c3;
  font-weight: 700;
  color: #92400e;
}

.kado-overtime-msg {
  font-size: 13px;
  color: #1e40af;
}

.kado-existing-label {
  color: #64748b;
  font-weight: 600;
}

.kado-existing-value {
  font-weight: 700;
  color: #1e40af;
}

.btn-sm {
  padding: 3px 8px;
  font-size: 12px;
}

.kado-row-actions {
  display: flex;
  gap: 4px;
  white-space: nowrap;
}

.kado-editing-row {
  background: #fffbeb;
}

.kado-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.kado-status.completed {
  background: #dcfce7;
  color: #166534;
}

.kado-status.started {
  background: #fef9c3;
  color: #854d0e;
}

@media (max-width: 900px) {
  .kado-form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .kado-form-grid {
    grid-template-columns: 1fr;
  }
}

.panel {
  border: 1px solid #d9e2ec;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
  display: grid;
  gap: 10px;
  align-content: start;
}

.panel-head h3 {
  margin: 0;
  font-size: 18px;
}

.message {
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
}

.message.is-success {
  background: #dcfce7;
  color: #166534;
}

.message.is-error {
  background: #fee2e2;
  color: #991b1b;
}

.message.is-warning {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
  font-weight: 700;
}

.message.is-info {
  background: #e2e8f0;
  color: #334155;
}

.form-grid {
  display: grid;
  gap: 10px;
}

.form-grid.two-col {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: grid;
  gap: 6px;
}

.operator-action-btn-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-self: stretch;
}

.operator-action-btn {
  flex: 1;
  min-width: 66px;
  padding: 7px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  background: #ffffff;
  color: #334155;
  font-size: 12px;
  cursor: pointer;
}

.operator-action-btn.active {
  border-color: #0ea5e9;
  background: #e0f2fe;
  color: #0c4a6e;
  font-weight: 700;
}

label {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.required::after {
  content: ' *';
  color: #dc2626;
}

input,
select {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 14px;
  box-sizing: border-box;
}

input:focus,
select:focus {
  outline: none;
  border-color: #2563eb;
}

.pattern-filters {
  display: grid;
  gap: 6px;
  grid-template-columns: 1fr 1fr 1fr;
}

.pattern-select {
  min-height: 40px;
}

.snapshot {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
  padding: 10px;
  display: grid;
  gap: 10px;
}

.snapshot-summary {
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.snapshot-summary .label {
  display: block;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 3px;
}

.snapshot-block h4 {
  margin: 0 0 6px;
  font-size: 14px;
}

.detail-stack {
  display: grid;
  gap: 10px;
  align-content: start;
}

.summary-card {
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: #f8fbff;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
}

.summary-item {
  display: grid;
  gap: 4px;
}

.summary-label {
  color: #64748b;
  font-size: 12px;
}

.summary-value {
  font-size: 16px;
  font-weight: 600;
}

.component-table-scroll {
  max-height: clamp(420px, 74vh, 920px);
}

.finished-table-scroll {
  max-height: min(44vh, 430px);
}

.empty-pattern-message {
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 20px 12px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #1e293b;
  padding: 8px 14px;
  font-size: 14px;
  cursor: pointer;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn.primary {
  background: #2563eb;
  border-color: #1d4ed8;
  color: #ffffff;
  font-weight: 700;
}

.btn.danger {
  background: #dc2626;
  border-color: #b91c1c;
  color: #ffffff;
  font-weight: 700;
}

.search-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.search-actions {
  display: flex;
  gap: 8px;
}

.result-meta {
  font-size: 12px;
  color: #475569;
}

.table-scroll {
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 7px 8px;
  text-align: left;
  white-space: nowrap;
}

.table-input {
  width: 100%;
  min-width: 120px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
}

.table-input-num {
  min-width: 72px;
  text-align: right;
}

th {
  background: #f8fafc;
  position: sticky;
  top: 0;
  z-index: 1;
}

td.num,
th.num {
  text-align: right;
}

.list-table table tbody tr {
  cursor: pointer;
}

.list-table table tbody tr:hover {
  background: #f1f5f9;
}

.list-table table tbody tr.active {
  background: #dbeafe;
}

@media (max-width: 1500px) {
  .laser-actual-page.mode-entry {
    grid-template-columns: minmax(320px, 1fr) minmax(420px, 1.25fr);
  }
}

@media (max-width: 1180px) {
  .laser-actual-page.mode-entry {
    grid-template-columns: 1fr;
    grid-template-areas:
      "tab"
      "form"
      "detail"
      "component";
  }

  .component-table-scroll,
  .finished-table-scroll {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .laser-actual-page {
    padding: 8px;
  }

  .tab-bar {
    width: 100%;
    justify-self: stretch;
    flex-direction: column;
    align-items: stretch;
  }

  .tab-buttons {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .tab-operator-actions {
    justify-content: flex-start;
  }

  .tab-item {
    width: 100%;
  }

  .form-grid.two-col,
  .search-grid {
    grid-template-columns: 1fr;
  }
}
.ds-btn { padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
</style>

