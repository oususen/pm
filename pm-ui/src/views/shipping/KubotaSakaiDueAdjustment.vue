<template>
  <div class="due-adjustment-page">
    <div class="toolbar">
      <div class="field">
        <label>開始日</label>
        <input v-model="startDate" type="date" />
      </div>
      <div class="field">
        <label>期間</label>
        <select v-model.number="horizonDays">
          <option :value="7">7日</option>
          <option :value="14">14日</option>
          <option :value="30">30日</option>
          <option :value="60">60日</option>
        </select>
      </div>
      <div class="field search-field">
        <label>品番 OR検索</label>
        <div class="search-inputs">
          <input v-model.trim="keyword" type="text" placeholder="キーワード1" @keydown.enter="handleDisplayClick" />
          <input v-model.trim="keyword2" type="text" placeholder="キーワード2" @keydown.enter="handleDisplayClick" />
        </div>
      </div>
      <div class="field">
        <label>一括入力開始日</label>
        <input v-model="bulkStartDate" :min="startDate" :max="bulkStartDateMax" type="date" />
      </div>
      <div class="field">
        <label>お気に入り</label>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">
            {{ fav.name }}
          </option>
        </select>
      </div>
      <div class="field">
        <label>登録名</label>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
      </div>
      <button class="btn favorite-btn" title="お気に入り登録" :disabled="loading || saving || importing" @click="saveFavorite">★</button>
      <span v-if="lastAdjustedAt" class="lock-badge adj-badge">最新調整日: {{ formatAdjDate(lastAdjustedAt) }}</span>
      <span v-if="lockDate" class="lock-badge">{{ formatShortDate(lockDate) }} ～締め</span>
      <span v-if="duePlanLockDate" class="lock-badge plan-lock">{{ formatShortDate(duePlanLockDate) }} ～計画lock</span>
      <button class="btn import-btn" :disabled="importing || loading" @click="importOrders">{{ importing ? '取込中...' : '取込' }}</button>
      <button class="btn" :disabled="importing || loading || saving" @click="openChangeReasonDialog">計画変更</button>
      <button class="btn save-btn" :disabled="saving || loading" @click="saveDeliveries">{{ saving ? '保存中...' : '保存' }}</button>
      <button class="btn" :disabled="loading || !matrixColumns.length" @click="exportExcel">EXCEL出力</button>
      <button class="btn" :disabled="loading || importing" @click="handleDisplayClick">表示</button>
      <button class="btn" @click="openNotifyConfigDialog">通知設定</button>
      <span class="fixed-help">計画欄の「固」で注番固定</span>
      <DataSourceDialog title="" :sources="dsSources" />
    </div>

    <div class="table-wrap">
      <table class="grid">
        <colgroup>
          <col style="width: 60px" />
          <col v-if="!matrixColumns.length" style="width: auto" />
          <template v-for="col in matrixColumns" :key="`col-${col.colKey}`">
            <col style="width: 70px" />
            <col style="width: 40px" />
            <col style="width: 45px" />
            <col style="width: 40px" />
          </template>
        </colgroup>
        <thead ref="theadRef">
          <tr class="head1">
            <th rowspan="2" class="sticky-left date-separator">日付</th>
            <th v-if="!matrixColumns.length" rowspan="2" class="empty-grid-spacer"></th>
            <th
              v-for="(col, colIdx) in matrixColumns"
              :key="col.colKey"
              colspan="4"
              :class="{ 'product-start': colIdx > 0 }"
            >
              <div class="head-group">
                <span class="head-code">{{ col.productCode }}</span>
                <span class="head-ship">{{ col.shipToCode }}</span>
                <button
                  class="copy-btn del-btn"
                  :disabled="loading || saving || importing"
                  title="計画一括削除"
                  @click.stop="openClearPlanDialog(col)"
                >×</button>
                <button
                  class="copy-btn"
                  :disabled="loading || saving || importing || linking"
                  title="前倒し計画をFIRM注番に紐づけ"
                  @click.stop="linkForwardPlans(col)"
                >⇔</button>
                <button
                  class="copy-btn"
                  :disabled="loading || saving || importing"
                  @click.stop="applyDemandToPlan(col.group)"
                >→</button>
              </div>
              <div class="head-ship-name">{{ col.group.shipToName || ' ' }}</div>
            </th>
          </tr>
          <tr class="head2">
            <template v-for="(col, colIdx) in matrixColumns" :key="`sub-${col.colKey}`">
              <th :class="{ 'product-start': colIdx > 0 }">注番</th>
              <th>受注</th>
              <th>計画</th>
              <th class="product-end">注残</th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in displayRows"
            :key="row.rowKey"
            :class="{ 'carry-tr': row.isCarry, 'day-row': !row.isCarry, 'locked-row': !row.isCarry && isDateLocked(row.dateKey) }"
          >
            <td class="sticky-left date-col date-separator" :class="row.dayClass">{{ row.label }}</td>
            <td v-if="!matrixColumns.length" class="empty-grid-spacer" :class="row.dayClass"></td>
            <template v-if="row.isCarry">
              <template v-for="(col, colIdx) in matrixColumns" :key="`${row.rowKey}-${col.colKey}`">
                <td :class="{ 'product-start': colIdx > 0 }"></td>
                <td></td>
                <td></td>
                <td class="readonly-cell product-end carry-value">{{ formatNumber(row.cells[col.colKey]) }}</td>
              </template>
            </template>
            <template v-else>
              <template v-for="(col, colIdx) in matrixColumns" :key="`${row.rowKey}-${col.colKey}`">
                <td class="orderno-subcol" :class="{ 'product-start': colIdx > 0 }">
                  <div
                    v-for="slotIdx in row.maxSlots"
                    :key="`${row.rowKey}-${col.colKey}-label-${slotIdx}`"
                    class="sub-cell"
                    :class="{ forecast: slotLineAt(row, col.colKey, slotIdx - 1)?.orderType === 'FORECAST' }"
                  >
                    <div class="order-label-wrap">
                      <span>{{ slotLabel(row, col.colKey, slotIdx - 1) }}</span>
                      <button
                        v-if="slotLineAt(row, col.colKey, slotIdx - 1)"
                        class="line-note-btn"
                        :class="{ 'has-note': hasCoordinationNote(row, col.colKey, slotIdx - 1) }"
                        :disabled="loading || saving || importing"
                        title="業務連絡メモ"
                        @click.stop="openCoordinationNoteDialog(row, col.colKey, slotIdx - 1)"
                      >連</button>
                    </div>
                  </div>
                </td>
                <td class="readonly-cell demand" :class="row.dayClass">
                  <div
                    v-for="slotIdx in row.maxSlots"
                    :key="`${row.rowKey}-${col.colKey}-demand-${slotIdx}`"
                    class="sub-cell"
                  >{{ slotDemand(row, col.colKey, slotIdx - 1) }}</div>
                </td>
                <td :class="row.dayClass">
                  <div
                    v-for="slotIdx in row.maxSlots"
                    :key="`${row.rowKey}-${col.colKey}-delivery-${slotIdx}`"
                    class="sub-cell"
                    :class="{ 'fixed-plan-cell': isFixedCell(editableLineAt(row, col, slotIdx - 1), row.dateKey) }"
                  >
                    <template v-if="editableLineAt(row, col, slotIdx - 1)">
                      <input
                        :ref="(el) => { if (el) inputRefs[`${row.dateKey}-${col.colKey}-${slotIdx - 1}`] = el }"
                        :data-row="row.dateKey"
                        :data-col="col.colKey"
                        :data-slot="slotIdx - 1"
                        :value="displayInputValue(editableLineAt(row, col, slotIdx - 1).deliveryByDate[row.dateKey])"
                        :disabled="isDateLocked(row.dateKey)"
                        :class="{ 'locked-cell': isDateLocked(row.dateKey), 'fixed-input': isFixedCell(editableLineAt(row, col, slotIdx - 1), row.dateKey) }"
                        type="text"
                        inputmode="decimal"
                        @input="onDeliveryInput(editableLineAt(row, col, slotIdx - 1), row.dateKey, $event.target.value)"
                        @blur="onDeliveryBlur(editableLineAt(row, col, slotIdx - 1), row.dateKey)"
                        @keydown.enter.prevent="focusNextRow($event, row.dateKey, col.colKey, slotIdx - 1)"
                      />
                      <button
                        class="fixed-toggle-btn"
                        :class="{ active: isFixedCell(editableLineAt(row, col, slotIdx - 1), row.dateKey) }"
                        :disabled="isDateLocked(row.dateKey)"
                        title="この注番へ計画数を固定"
                        @click.stop="toggleFixedCell(editableLineAt(row, col, slotIdx - 1), row.dateKey)"
                      >固</button>
                    </template>
                  </div>
                </td>
                <td class="readonly-cell product-end" :class="row.dayClass">
                  <div
                    v-for="slotIdx in row.maxSlots"
                    :key="`${row.rowKey}-${col.colKey}-remaining-${slotIdx}`"
                    class="sub-cell"
                  >{{ slotRemaining(row, col.colKey, slotIdx - 1) }}</div>
                </td>
              </template>
            </template>
          </tr>
          <tr v-if="!displayRows.length">
            <td :colspan="matrixColumns.length * 4 + 1" class="empty">データがありません</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <th class="sticky-left total-label date-separator">最終残</th>
            <td v-if="!matrixColumns.length" class="total-blank empty-grid-spacer"></td>
            <template v-for="(col, colIdx) in matrixColumns" :key="`total-${col.colKey}`">
              <td class="total-blank" :class="{ 'product-start': colIdx > 0 }"></td>
              <td class="total-blank"></td>
              <td class="total-blank"></td>
              <td class="total-value product-end" :class="{ error: groupTotalRemaining(col.group) !== 0 }">
                {{ formatNumber(groupTotalRemaining(col.group)) }}
              </td>
            </template>
          </tr>
        </tfoot>
      </table>
    </div>

    <div v-if="showClearPlanDialog" class="modal-overlay" @click.self="closeClearPlanDialog">
      <div class="modal-content">
        <h2>{{ clearPlanTarget?.productCode }} {{ clearPlanTarget?.shipToCode }} 計画削除</h2>
        <div style="margin-bottom: 8px;">
          <label style="font-weight: 600;">開始日</label>
          <input v-model="clearPlanStartDate" type="date" style="margin-left: 8px;" />
        </div>
        <p style="margin: 8px 0; font-size: 13px;">この日以降の計画数を0にします。削除しますか？</p>
        <div class="modal-actions">
          <button class="btn" @click="closeClearPlanDialog">キャンセル</button>
          <button class="btn save-btn" style="background: #dc2626;" @click="executeClearPlan">削除</button>
        </div>
      </div>
    </div>

    <div v-if="showChangeReasonDialog" class="modal-overlay" @click.self="closeChangeReasonDialog">
      <div class="modal-content">
        <h2>変更理由入力</h2>
        <textarea
          v-model="changeReasonDraft"
          rows="4"
          placeholder="変更理由を入力してください"
        ></textarea>
        <div class="modal-actions">
          <button class="btn" @click="closeChangeReasonDialog">キャンセル</button>
          <button class="btn save-btn" @click="confirmChangeReason">確定</button>
        </div>
      </div>
    </div>

    <div v-if="showCoordinationNoteDialog" class="modal-overlay" @click.self="closeCoordinationNoteDialog">
      <div class="modal-content">
        <h2>業務連絡メモ</h2>
        <div class="note-target">{{ coordinationNoteTargetLabel }}</div>
        <label for="shared-coordination-note">共通連絡（同日・同品番・同納入場所の全注番共通）</label>
        <textarea
          id="shared-coordination-note"
          v-model.trim="sharedCoordinationNoteDraft"
          rows="3"
          maxlength="200"
          placeholder="内示から確定に変わっても引き継ぐ連絡"
        ></textarea>
        <div class="note-count">{{ sharedCoordinationNoteDraft.length }}/200</div>
        <template v-if="activeCoordinationNote?.orderType === 'FIRM'">
          <label for="order-coordination-note">注番別連絡（この注番のみ）</label>
          <textarea id="order-coordination-note" v-model.trim="coordinationNoteDraft" rows="3" maxlength="200"></textarea>
          <div class="note-count">{{ coordinationNoteDraft.length }}/200</div>
        </template>
        <div class="modal-actions">
          <button class="btn" :disabled="savingCoordinationNote" @click="closeCoordinationNoteDialog">キャンセル</button>
          <button
            class="btn"
            :disabled="savingCoordinationNote || (!coordinationNoteDraft && !sharedCoordinationNoteDraft)"
            @click="clearCoordinationNote"
          >両方削除</button>
          <button class="btn save-btn" :disabled="savingCoordinationNote" @click="saveCoordinationNote">
            {{ savingCoordinationNote ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showNotifyConfigDialog" class="modal-overlay" @click.self="closeNotifyConfigDialog">
      <div class="modal-content notify-config-modal">
        <h2>納期調整 通知設定</h2>
        <p class="notify-description">
          納期調整で計画数を変更して保存した際に、以下のユーザーにアプリ内通知を送信します。
          メール通知を有効にすると、同じ宛先にメールも送信します。
        </p>
        <div v-if="notifyConfigLoading" class="email-loading">読み込み中...</div>
        <template v-else>
          <div class="email-field">
            <label>通知先</label>
            <UserChipSelect
              :userList="notifyAllUsers"
              v-model="notifyUserIds"
            />
            <p class="notify-helper">社員を検索して通知先に追加します。</p>
          </div>
          <div class="email-field">
            <label>通知対象期間</label>
            <div class="notify-horizon-row">
              <input
                v-model.number="notifyHorizonDays"
                type="number"
                min="0"
                class="notify-horizon-input"
              />
              <span>営業日後まで（ダイソウカレンダー基準、0=制限なし）</span>
            </div>
            <p class="notify-helper">設定した営業日数を超える将来の変更は通知しません。</p>
          </div>
          <div class="email-field">
            <label>メール通知</label>
            <div class="notify-toggle-row">
              <label class="notify-toggle-label">
                <input type="checkbox" v-model="notifyEmailEnabled" />
                <span>差分検知時にメールも送信する</span>
              </label>
            </div>
            <p class="notify-helper">有効にすると、上記通知先ユーザーのメールアドレス宛にメールを送信します。</p>
          </div>
          <div class="modal-actions">
            <button class="btn save-btn" :disabled="notifyConfigSaving" @click="saveNotifyConfig">
              {{ notifyConfigSaving ? '保存中...' : '保存' }}
            </button>
            <button class="btn" @click="closeNotifyConfigDialog">キャンセル</button>
          </div>
          <div v-if="notifyConfigMessage" class="notify-message" :class="notifyConfigError ? 'error' : 'success'">
            {{ notifyConfigMessage }}
          </div>
        </template>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import ExcelJS from 'exceljs'
import api from '@/api/client'
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import UserChipSelect from '@/views/purchase/UserChipSelect.vue'

const dsSources = [
  { op: '納期調整 読み書き', table: 't_kubota_sakai_due_adjustment', desc: '品番×日付の納期調整データ（需要・出荷数）' },
  { op: '固定設定 読み書き', table: 't_kubota_sakai_due_allocation_override', desc: '注番へ強制紐づけする固定数量' },
  { op: '受注明細 読み取り', table: 't_order_line', desc: '取込元の受注明細（demand_qty）' },
  { op: 'カレンダー 読み取り', table: 'm_calendar / m_calendar_day', desc: '営業日判定・計画ロック日' },
  { op: 'お気に入り 読み書き', table: 'user_favorite', desc: '画面フィルタのお気に入り保存' },
  { op: '連絡先 読み取り', table: 'm_contacts', desc: 'メール送信先' },
]
const inputRefs = reactive({})
const theadRef = ref(null)

const setStickyTopValues = () => {
  if (!theadRef.value) return
  const rows = theadRef.value.querySelectorAll('tr')
  let cumTop = 0
  rows.forEach((tr) => {
    const cells = tr.querySelectorAll('th')
    cells.forEach((th) => {
      if (!th.hasAttribute('rowspan')) {
        th.style.top = `${cumTop}px`
      }
    })
    cumTop += tr.offsetHeight
  })
  const rowspanCells = theadRef.value.querySelectorAll('th[rowspan]')
  rowspanCells.forEach((th) => { th.style.top = '0px' })
}

const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const formatAdjDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

const formatShortDate = (dateStr) => {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`
}

const parseNumber = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const num = Number(String(value).replace(/,/g, ''))
  return Number.isFinite(num) ? num : 0
}

const formatNumber = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const displayInputValue = (value) => {
  const num = parseNumber(value)
  if (Math.abs(num) < 0.000001) return ''
  return Number.isInteger(num) ? String(num) : num.toFixed(3).replace(/\.?0+$/, '')
}

const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const linking = ref(false)
const keyword = ref('V0')
const keyword2 = ref('6E')
const startDate = ref(formatLocalDate(new Date()))
const bulkStartDate = ref(startDate.value)
const horizonDays = ref(60)
const groups = ref([])
const lockDate = ref(null)
const duePlanLockDate = ref(null)
const lastAdjustedAt = ref(null)
const calendarDayMap = ref({})
const kubotaSakaiCalendarId = ref(null)
const isEditUnlocked = ref(false)
const changeReason = ref('')
const changeReasonDraft = ref('')
const showChangeReasonDialog = ref(false)
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')
const FAVORITE_SCREEN_KEY = 'shipping.kubota_sakai_due_adjustment'
const hasDisplayedOnce = ref(false)
const showCoordinationNoteDialog = ref(false)
const savingCoordinationNote = ref(false)
const coordinationNoteDraft = ref('')
const sharedCoordinationNoteDraft = ref('')
const activeCoordinationNote = ref(null)

const dateColumns = computed(() => {
  const base = new Date(`${startDate.value}T00:00:00`)
  return Array.from({ length: horizonDays.value }).map((_, idx) => {
    const d = new Date(base)
    d.setDate(base.getDate() + idx)
    const mm = d.getMonth() + 1
    const dd = d.getDate()
    const w = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
    const key = formatLocalDate(d)
    return { key, label: `${mm}/${dd}${w}`, dayClass: isHolidayDate(key, d.getDay()) ? 'holiday' : '' }
  })
})

const bulkStartDateMax = computed(() => {
  if (!dateColumns.value.length) return startDate.value
  return dateColumns.value[dateColumns.value.length - 1].key
})

const normalizeBulkStartDate = () => {
  const keys = dateColumns.value.map((col) => col.key)
  if (!keys.length) return
  const minKey = keys[0]
  const maxKey = keys[keys.length - 1]
  if (!bulkStartDate.value || bulkStartDate.value < minKey) {
    bulkStartDate.value = minKey
    return
  }
  if (bulkStartDate.value > maxKey) {
    bulkStartDate.value = maxKey
  }
}

const filteredGroups = computed(() => {
  const kw1 = keyword.value.trim().toLowerCase()
  const kw2 = keyword2.value.trim().toLowerCase()
  if (!kw1 && !kw2) return groups.value
  return groups.value.filter((group) => {
    const searchTarget = `${group.productCode}`.toLowerCase()
    const match1 = kw1 && searchTarget.includes(kw1)
    const match2 = kw2 && searchTarget.includes(kw2)
    return match1 || match2
  })
})

const matrixColumns = computed(() => {
  return [...filteredGroups.value]
    .sort((a, b) => {
      const codeCmp = String(a.productCode).localeCompare(String(b.productCode))
      if (codeCmp !== 0) return codeCmp
      return String(a.shipToCode || '').localeCompare(String(b.shipToCode || ''))
    })
    .map((group) => ({
      colKey: group.groupKey,
      productCode: group.productCode,
      shipToCode: group.shipToCode || '-',
      group,
    }))
})

const lineSortCompare = (a, b) => {
  const aFc = a.orderType === 'FORECAST' ? 1 : 0
  const bFc = b.orderType === 'FORECAST' ? 1 : 0
  if (aFc !== bFc) return aFc - bFc
  return String(a.sourceOrderNo || '').localeCompare(String(b.sourceOrderNo || ''))
}

const lineHasAnyValueInHorizon = (line) => {
  return dateColumns.value.some((dateCol) => {
    const demand = parseNumber(line.demandByDate[dateCol.key])
    const delivery = parseNumber(line.deliveryByDate[dateCol.key])
    return demand > 0 || delivery > 0
  })
}

const displayRows = computed(() => {
  // 繰越行
  const hasCarry = matrixColumns.value.some((col) => parseNumber(col.group.carryRemaining) !== 0)
  const carryRow = {
    rowKey: '_carry',
    dateKey: '_carry',
    label: '繰越',
    dayClass: 'carry-row',
    isCarry: true,
    maxSlots: 1,
    cells: {},
  }
  if (hasCarry) {
    matrixColumns.value.forEach((col) => {
      carryRow.cells[col.colKey] = parseNumber(col.group.carryRemaining)
    })
  }

  const dateRows = dateColumns.value.map((dateCol) => {
    const cells = {}
    let maxSlots = 0
    matrixColumns.value.forEach((col) => {
      const visibleLines = col.group.lines
        .filter((line) => {
          const demand = parseNumber(line.demandByDate[dateCol.key])
          const delivery = parseNumber(line.deliveryByDate[dateCol.key])
          return demand > 0 || delivery > 0
        })
        .sort(lineSortCompare)
      cells[col.colKey] = visibleLines
      if (visibleLines.length > maxSlots) maxSlots = visibleLines.length
    })
    return {
      rowKey: dateCol.key,
      dateKey: dateCol.key,
      label: dateCol.label,
      dayClass: dateCol.dayClass,
      isCarry: false,
      maxSlots: maxSlots || 1,
      cells,
    }
  })

  return hasCarry ? [carryRow, ...dateRows] : dateRows
})

const isDateLocked = (dateKey) => {
  if (lockDate.value && dateKey <= lockDate.value) return true
  if (duePlanLockDate.value && dateKey <= duePlanLockDate.value && !isEditUnlocked.value) return true
  return false
}

const isHolidayDate = (dateKey, weekDay) => {
  const day = calendarDayMap.value[dateKey]
  if (day && typeof day.is_working_day === 'boolean') return !day.is_working_day
  return weekDay === 0 || weekDay === 6
}

const resolveKubotaSakaiCalendarId = async () => {
  if (kubotaSakaiCalendarId.value) return kubotaSakaiCalendarId.value
  const normalize = (value) => String(value || '').trim().toLowerCase()
  const pick = (list = []) => {
    const exact = list.find((row) => {
      const code = normalize(row.calendar_code)
      return code === 'kubota_sakai' || code === 'kobota_sakai' || code === 'kubota-muke' || code === 'kubota_muke'
    })
    if (exact) return exact
    const nameHit = list.find((row) => {
      const code = normalize(row.calendar_code)
      const name = normalize(row.calendar_name)
      return (name.includes('クボタ') && name.includes('堺')) || (code.includes('kubota') && code.includes('sakai'))
    })
    if (nameHit) return nameHit
    return list.find((row) => normalize(row.calendar_code).includes('kubota') || normalize(row.calendar_code).includes('kobota')) || null
  }
  for (const kw of ['kubota', 'kobota', 'クボタ']) {
    try {
      const res = await api.calendars.getCalendars({ search: kw, page_size: 500 })
      const list = res.data?.results || res.data || []
      const found = pick(list)
      if (found?.id) {
        kubotaSakaiCalendarId.value = found.id
        return found.id
      }
    } catch (error) { /* ignore */ }
  }
  return null
}

const loadKubotaSakaiCalendarDays = async () => {
  try {
    const calendarId = await resolveKubotaSakaiCalendarId()
    if (!calendarId) { calendarDayMap.value = {}; return }
    const rangeStart = startDate.value
    const baseDate = new Date(`${startDate.value}T00:00:00`)
    const rangeEndDate = new Date(baseDate)
    rangeEndDate.setDate(baseDate.getDate() + 89)
    const rangeEnd = formatLocalDate(rangeEndDate)
    const daysRes = await api.calendars.getCalendarDays(calendarId, {
      target_date__gte: rangeStart,
      target_date__lte: rangeEnd,
    })
    const days = daysRes.data?.results || daysRes.data || []
    const map = {}
    days.forEach((day) => { if (day?.target_date) map[day.target_date] = day })
    calendarDayMap.value = map
  } catch (error) {
    calendarDayMap.value = {}
  }
}

const recalcGroupRemaining = (group) => {
  // 品番+納入場所の全注番を合算して累積注残を計算
  // carry_remaining: 表示期間より前の繰越注残
  const dates = dateColumns.value.map((c) => c.key).sort()
  let running = parseNumber(group.carryRemaining)
  const remainingAtDate = {}
  for (const d of dates) {
    let dayDemand = 0
    let dayDelivery = 0
    for (const line of group.lines) {
      dayDemand += parseNumber(line.demandByDate[d])
      dayDelivery += parseNumber(line.deliveryByDate[d])
    }
    running += dayDelivery - dayDemand
    remainingAtDate[d] = running
  }
  // まず全ラインの注残をクリア
  for (const line of group.lines) {
    for (const d of dates) {
      line.remainingByDate[d] = 0
    }
  }
  // 各日付で、その日にデータがあるラインのうち最後のものに注残をセット
  for (const d of dates) {
    const activeLines = group.lines.filter((line) => {
      return parseNumber(line.demandByDate[d]) > 0 || parseNumber(line.deliveryByDate[d]) > 0
    })
    if (activeLines.length > 0) {
      activeLines[activeLines.length - 1].remainingByDate[d] = remainingAtDate[d]
    }
  }
  group.finalRemaining = running
}

const buildLine = (li) => {
  const demandByDate = {}
  const deliveryByDate = {}
  const fixedByDate = {}
  const remainingByDate = {}
  dateColumns.value.forEach((col) => {
    demandByDate[col.key] = 0
    deliveryByDate[col.key] = 0
    fixedByDate[col.key] = ''
    remainingByDate[col.key] = 0
  })
  Object.entries(li.demand_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(demandByDate, d)) demandByDate[d] = parseNumber(q)
  })
  Object.entries(li.delivery_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(deliveryByDate, d)) deliveryByDate[d] = parseNumber(q)
  })
  Object.entries(li.fixed_by_date || {}).forEach(([d, q]) => {
    if (Object.prototype.hasOwnProperty.call(fixedByDate, d)) fixedByDate[d] = q === '' ? '' : parseNumber(q)
  })
  return {
    lineKey: li.line_key,
    sourceOrderNo: li.source_order_no,
    orderType: li.order_type,
    demandByDate,
    deliveryByDate,
    fixedByDate,
    dueAdjustmentIdByDate: li.due_adjustment_id_by_date || {},
    coordinationNoteByDate: li.coordination_note_by_date || {},
    sharedCoordinationNoteByDate: li.shared_coordination_note_by_date || {},
    remainingByDate,
    _dirty: false,
  }
}

const buildGroupFromGridItem = (item) => {
  const group = {
    groupKey: item.group_key,
    productCode: item.product_code,
    shipToCode: item.ship_to_code || '-',
    shipToName: item.ship_to_name || '',
    carryRemaining: parseNumber(item.carry_remaining),
    lines: (item.lines || []).map(buildLine),
  }
  recalcGroupRemaining(group)
  return group
}

const slotLineAt = (row, colKey, slotIdx) => {
  const arr = row.cells[colKey]
  return arr && arr[slotIdx] ? arr[slotIdx] : null
}

const getPrimaryEditableLine = (group) => {
  if (!group?.lines?.length) return null
  const candidates = group.lines.filter(lineHasAnyValueInHorizon).sort(lineSortCompare)
  if (candidates.length > 0) return candidates[0]
  return [...group.lines].sort(lineSortCompare)[0] || null
}

const editableLineAt = (row, col, slotIdx) => {
  const line = slotLineAt(row, col.colKey, slotIdx)
  if (line) return line
  if (slotIdx !== 0) return null
  return getPrimaryEditableLine(col.group)
}

const slotLabel = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  if (!line) return ''
  return line.sourceOrderNo || (line.orderType === 'FORECAST' ? '内示' : '-')
}

const slotDemand = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  return line ? formatNumber(line.demandByDate[row.dateKey]) : ''
}

const slotDueAdjustmentId = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  if (!line) return null
  return Number(line.dueAdjustmentIdByDate?.[row.dateKey] || 0) || null
}

const slotCoordinationNote = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  if (!line) return ''
  return String(line.coordinationNoteByDate?.[row.dateKey] || '').trim()
}

const hasCoordinationNote = (row, colKey, slotIdx) => Boolean(
  slotCoordinationNote(row, colKey, slotIdx) || slotLineAt(row, colKey, slotIdx)?.sharedCoordinationNoteByDate?.[row.dateKey],
)

const slotRemaining = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  return line ? formatNumber(line.remainingByDate[row.dateKey]) : ''
}

const groupTotalRemaining = (group) => {
  return group.finalRemaining ?? 0
}

const showClearPlanDialog = ref(false)
const clearPlanTarget = ref(null)
const clearPlanStartDate = ref('')

const openClearPlanDialog = (col) => {
  clearPlanTarget.value = col
  clearPlanStartDate.value = bulkStartDate.value || startDate.value
  showClearPlanDialog.value = true
}
const closeClearPlanDialog = () => {
  showClearPlanDialog.value = false
  clearPlanTarget.value = null
}
const executeClearPlan = () => {
  const col = clearPlanTarget.value
  if (!col?.group) return
  const from = clearPlanStartDate.value
  let changed = false
  for (const line of col.group.lines) {
    for (const dc of dateColumns.value) {
      if (from && dc.key < from) continue
      if (isDateLocked(dc.key)) continue
      const current = parseNumber(line.deliveryByDate[dc.key])
      if (current !== 0) {
        line.deliveryByDate[dc.key] = 0
        changed = true
      }
    }
    if (changed) line._dirty = true
  }
  if (changed) recalcGroupRemaining(col.group)
  closeClearPlanDialog()
}

const linkForwardPlans = async (col) => {
  if (!col.group) return
  if (!confirm(`${col.productCode} / ${col.shipToCode || '(なし)'}\n前倒し計画をFIRM注番に紐づけますか？`)) return
  linking.value = true
  try {
    const shipTo = col.shipToCode === '-' ? '' : (col.shipToCode || '')
    const res = await api.kubotaSakaiDueAdjustments.linkForwardPlans({
      product_code: col.productCode,
      ship_to_code: shipTo,
    })
    const d = res.data
    if (d.linked > 0) {
      alert(`${d.linked}件の前倒し計画を紐づけました。`)
      await loadGrid()
    } else {
      alert(d.detail || '紐づけ対象がありませんでした。')
    }
  } catch (error) {
    alert(error?.response?.data?.detail || '紐づけに失敗しました。')
  } finally {
    linking.value = false
  }
}

const applyDemandToPlan = (group) => {
  if (!group) return
  let changed = false
  const applyFrom = bulkStartDate.value
  for (const line of group.lines) {
    for (const col of dateColumns.value) {
      if (applyFrom && col.key < applyFrom) continue
      if (isDateLocked(col.key)) continue
      const demandQty = parseNumber(line.demandByDate[col.key])
      const currentQty = parseNumber(line.deliveryByDate[col.key])
      if (currentQty !== demandQty) {
        line.deliveryByDate[col.key] = demandQty
        changed = true
      }
    }
    if (changed) line._dirty = true
  }
  if (changed) recalcGroupRemaining(group)
}

watch([startDate, horizonDays], () => {
  normalizeBulkStartDate()
})

const toFavoritePayload = () => ({
  horizonDays: Number(horizonDays.value || 60),
  keyword: String(keyword.value || ''),
  keyword2: String(keyword2.value || ''),
})

const applyFavoritePayload = (payload) => {
  const nextHorizon = Number(payload?.horizonDays || 60)
  horizonDays.value = [7, 14, 30, 60].includes(nextHorizon) ? nextHorizon : 60
  keyword.value = String(payload?.keyword || '')
  keyword2.value = String(payload?.keyword2 || '')
  normalizeBulkStartDate()
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得失敗:', e)
  }
}

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  applyFavoritePayload(target.payload || {})
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) {
      await api.accounts.updateFavorite(id, payload)
    } else {
      await api.accounts.createFavorite(payload)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存に失敗しました。'
    alert(`お気に入り保存エラー: ${detail}`)
  }
}

const loadGrid = async () => {
  loading.value = true
  try {
    const [res] = await Promise.all([
      api.kubotaSakaiDueAdjustments.grid({
        start_date: startDate.value,
        horizon_days: horizonDays.value,
      }),
      loadKubotaSakaiCalendarDays(),
    ])
    lockDate.value = res.data?.lock_date || null
    duePlanLockDate.value = res.data?.due_plan_lock_date || null
    lastAdjustedAt.value = res.data?.last_adjusted_at || null
    const items = res.data?.rows || []
    groups.value = items.map(buildGroupFromGridItem)
    nextTick(setStickyTopValues)
  } catch (error) {
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const importCautionMessage = [
  '計算が中途半端になるため、取込または初回表示の実行中は他の画面へ遷移したり、この画面を閉じたりしないでください。',
  '処理完了メッセージが出るまでお待ちください。',
].join('\n')

const formatDeletedTripAssignmentsMessage = (items) => {
  if (!Array.isArray(items) || !items.length) return ''
  const lines = items.map((item) => {
    const qty = item?.qty ?? '0'
    return `${item?.due_date || '-'} ${item?.product_code || '-'} ${qty}`
  })
  return `\n\n削除された内示便割付:\n${lines.join('\n')}`
}

const importOrders = async () => {
  if (importing.value || loading.value) return
  alert(importCautionMessage)
  importing.value = true
  try {
    const res = await api.kubotaSakaiDueAdjustments.importOrders({
      start_date: startDate.value,
      horizon_days: horizonDays.value,
    })
    const d = res.data
    hasDisplayedOnce.value = true
    alert(
      `取込完了: 新規${d.created}件, 更新${d.updated}件, 内示→確定削除${d.deleted_forecast}件`
      + formatDeletedTripAssignmentsMessage(d.deleted_trip_assignments)
    )
    await loadGrid()
  } catch (error) {
    const message = error?.response?.data?.detail || '取込に失敗しました。'
    alert(message)
  } finally {
    importing.value = false
  }
}

const importOrdersForInitialDisplay = async () => {
  importing.value = true
  try {
    await api.kubotaSakaiDueAdjustments.importOrders({
      start_date: startDate.value,
      horizon_days: horizonDays.value,
    })
  } finally {
    importing.value = false
  }
}

const handleDisplayClick = async () => {
  if (loading.value || importing.value) return
  if (!hasDisplayedOnce.value) {
    alert(importCautionMessage)
    try {
      await importOrdersForInitialDisplay()
    } catch (error) {
      const message = error?.response?.data?.detail || '取込に失敗しました。'
      alert(message)
      return
    }
    hasDisplayedOnce.value = true
  }
  await loadGrid()
}

const findGroupForLine = (line) => {
  return groups.value.find((g) => g.lines.includes(line))
}

const isFixedCell = (line, dateKey) => {
  if (!line) return false
  const value = line.fixedByDate?.[dateKey]
  return value !== '' && value !== null && value !== undefined
}

const toggleFixedCell = (line, dateKey) => {
  if (!line) return
  if (isFixedCell(line, dateKey)) {
    line.fixedByDate[dateKey] = ''
  } else {
    const qty = parseNumber(line.deliveryByDate[dateKey])
    if (qty <= 0) {
      alert('固定する前に計画数を入力してください。')
      return
    }
    line.fixedByDate[dateKey] = qty
  }
  line._dirty = true
}

const onDeliveryInput = (line, dateKey, rawValue) => {
  const normalized = rawValue.replace(/[^\d.-]/g, '')
  line.deliveryByDate[dateKey] = normalized === '' ? 0 : parseNumber(normalized)
  if (isFixedCell(line, dateKey)) {
    const fixedQty = parseNumber(line.deliveryByDate[dateKey])
    line.fixedByDate[dateKey] = fixedQty > 0 ? fixedQty : ''
  }
  line._dirty = true
  const group = findGroupForLine(line)
  if (group) recalcGroupRemaining(group)
}

const onDeliveryBlur = (line, dateKey) => {
  const qty = parseNumber(line.deliveryByDate[dateKey])
  if (qty < 0) line.deliveryByDate[dateKey] = 0
}

const focusNextRow = (event, currentDateKey, colKey, slotIdx) => {
  const dates = dateColumns.value.map((c) => c.key)
  const currentIdx = dates.indexOf(currentDateKey)
  if (currentIdx < 0) return
  // 次の日付行で同じ列・同じスロットのinputを探す
  for (let i = currentIdx + 1; i < dates.length; i++) {
    const key = `${dates[i]}-${colKey}-${slotIdx}`
    const el = inputRefs[key]
    if (el) {
      el.focus()
      el.select()
      return
    }
  }
}

const buildPayloadRows = (targetGroups = [], dirtyOnly = true) => {
  const payloadRows = []
  for (const group of targetGroups) {
    const includeWholeGroup = !dirtyOnly || group.lines.some((line) => line._dirty)
    for (const line of group.lines) {
      if (!includeWholeGroup) continue
      const deliveryByDate = {}
      const fixedByDate = {}
      for (const col of dateColumns.value) {
        deliveryByDate[col.key] = parseNumber(line.deliveryByDate[col.key])
        fixedByDate[col.key] = isFixedCell(line, col.key) ? parseNumber(line.fixedByDate[col.key]) : ''
      }
      payloadRows.push({
        line_key: line.lineKey,
        delivery_by_date: deliveryByDate,
        fixed_by_date: fixedByDate,
      })
    }
  }
  return payloadRows
}

const formatDateCompact = (value) => String(value || '').replace(/-/g, '')

const buildMultilineCell = (values = []) => {
  const lines = values.map((value) => String(value ?? '')).filter((value) => value !== '')
  return lines.join('\n')
}

const buildExcelCellValue = (values = []) => {
  const normalized = values
    .map((value) => parseNumber(value))
    .filter((value) => Math.abs(value) >= 0.000001)
  if (!normalized.length) return 0
  if (normalized.length === 1) return normalized[0]
  return normalized.reduce((a, b) => a + b, 0)
}

const toExcelArgb = (hex) => `FF${String(hex || '#ffffff').replace('#', '').toUpperCase()}`

const makeExcelBorder = (thick = false, color = '#7f8c9a') => ({
  style: thick ? 'medium' : 'thin',
  color: { argb: toExcelArgb(color) },
})

const applyExcelCellStyle = (cell, {
  align = 'center',
  bold = false,
  bg = '#ffffff',
  thickLeft = false,
  thickRight = false,
  thickTop = false,
  thickBottom = false,
  wrapText = false,
  hideZero = false,
} = {}) => {
  cell.font = { bold, name: 'Meiryo', size: 11 }
  cell.alignment = {
    horizontal: align,
    vertical: 'middle',
    wrapText,
  }
  if (hideZero) cell.numFmt = '0;-0;'
  cell.fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: toExcelArgb(bg) },
  }
  cell.border = {
    top: makeExcelBorder(thickTop, thickTop ? '#44556f' : '#7f8c9a'),
    left: makeExcelBorder(thickLeft, thickLeft ? '#44556f' : '#7f8c9a'),
    bottom: makeExcelBorder(thickBottom, thickBottom ? '#44556f' : '#7f8c9a'),
    right: makeExcelBorder(thickRight, thickRight ? '#44556f' : '#7f8c9a'),
  }
}

const exportExcel = async () => {
  if (!matrixColumns.value.length) {
    alert('出力対象のデータがありません。')
    return
  }

  const filterText = [keyword.value, keyword2.value].filter(Boolean).join(' OR ') || '（なし）'
  const workbook = new ExcelJS.Workbook()
  const sheet = workbook.addWorksheet('納期調整')
  const totalColumns = 1 + matrixColumns.value.length * 3
  const columnWidths = [{ width: 12 }]
  matrixColumns.value.forEach(() => {
    columnWidths.push({ width: 12 }, { width: 10 }, { width: 10 })
  })
  sheet.columns = columnWidths

  sheet.addRow(['開始日', startDate.value, '期間', `${horizonDays.value}日`, '品番OR検索', filterText])
  for (let col = 1; col <= totalColumns; col++) {
    const cell = sheet.getRow(1).getCell(col)
    const isLabel = [1, 3, 5].includes(col)
    applyExcelCellStyle(cell, {
      align: isLabel ? 'center' : 'left',
      bold: isLabel,
      bg: isLabel ? '#eef3f8' : '#ffffff',
    })
  }

  sheet.addRow([])

  const headerRow1 = sheet.addRow([])
  const headerRow2 = sheet.addRow([])
  const headerRow3 = sheet.addRow([])
  const hRow1 = headerRow1.number
  sheet.mergeCells(hRow1, 1, hRow1 + 2, 1)
  headerRow1.getCell(1).value = '日付'
  applyExcelCellStyle(headerRow1.getCell(1), { bold: true, bg: '#cfd8ec', thickRight: true })
  applyExcelCellStyle(headerRow2.getCell(1), { bold: true, bg: '#cfd8ec', thickRight: true })
  applyExcelCellStyle(headerRow3.getCell(1), { bold: true, bg: '#e7edf7', thickRight: true })

  matrixColumns.value.forEach((col, index) => {
    const startCol = 2 + index * 3
    const endCol = startCol + 2
    sheet.mergeCells(hRow1, startCol, hRow1, endCol)
    const mergedCell = headerRow1.getCell(startCol)
    mergedCell.value = `${col.productCode} ${col.shipToCode}`
    applyExcelCellStyle(mergedCell, {
      bold: true,
      bg: '#cfd8ec',
      thickLeft: index > 0,
      thickRight: true,
    })

    sheet.mergeCells(hRow1 + 1, startCol, hRow1 + 1, endCol)
    const shipCell = headerRow2.getCell(startCol)
    shipCell.value = col.group.shipToName || ''
    applyExcelCellStyle(shipCell, {
      bg: '#cfd8ec',
      thickLeft: index > 0,
      thickRight: true,
    })

    const labels = ['受注', '計画', '注残']
    labels.forEach((label, offset) => {
      const cell = headerRow3.getCell(startCol + offset)
      cell.value = label
      applyExcelCellStyle(cell, {
        bold: true,
        bg: '#e7edf7',
        thickLeft: offset === 0 && index > 0,
        thickRight: offset === 2,
      })
    })
  })

  displayRows.value.forEach((row) => {
    const rowBg = row.isCarry
      ? '#f0f4ff'
      : row.dayClass === 'holiday'
        ? '#ffe3e3'
        : '#ffffff'
    const excelRow = sheet.addRow([])
    excelRow.getCell(1).value = row.label
    applyExcelCellStyle(excelRow.getCell(1), {
      align: 'right',
      bg: rowBg,
      bold: row.isCarry,
      thickRight: true,
      thickBottom: !row.isCarry,
    })

    matrixColumns.value.forEach((col, index) => {
      const startCol = 2 + index * 3
      const lines = row.isCarry ? [] : (row.cells[col.colKey] || [])
      const totalPlan = lines.reduce((sum, line) => sum + parseNumber(line.deliveryByDate[row.dateKey]), 0)
      const values = row.isCarry
        ? [0, 0, parseNumber(row.cells[col.colKey])]
        : [
            buildExcelCellValue(lines.map((line) => line.demandByDate[row.dateKey])),
            Math.abs(totalPlan) < 0.000001 ? 0 : totalPlan,
            buildExcelCellValue(lines.map((line) => line.remainingByDate[row.dateKey])),
          ]

      values.forEach((value, offset) => {
        const cell = excelRow.getCell(startCol + offset)
        cell.value = value
        applyExcelCellStyle(cell, {
          align: offset === 1 || offset === 2 || offset === 0 ? 'right' : 'center',
          bg: rowBg,
          bold: row.isCarry,
          thickLeft: offset === 0 && index > 0,
          thickRight: offset === 2,
          thickBottom: !row.isCarry,
          wrapText: !row.isCarry && (offset === 0 || offset === 2),
          hideZero: true,
        })
      })
    })
  })

  const totalRow = sheet.addRow([])
  totalRow.getCell(1).value = '総残'
  applyExcelCellStyle(totalRow.getCell(1), {
    bold: true,
    bg: '#dbe6f7',
    thickTop: true,
    thickRight: true,
  })
  matrixColumns.value.forEach((col, index) => {
    const startCol = 2 + index * 3
    totalRow.getCell(startCol).value = 0
    totalRow.getCell(startCol + 1).value = 0
    totalRow.getCell(startCol + 2).value = groupTotalRemaining(col.group) || 0
    applyExcelCellStyle(totalRow.getCell(startCol), {
      bg: '#dbe6f7',
      thickTop: true,
      thickLeft: index > 0,
      hideZero: true,
    })
    applyExcelCellStyle(totalRow.getCell(startCol + 1), {
      bg: '#dbe6f7',
      thickTop: true,
      hideZero: true,
    })
    applyExcelCellStyle(totalRow.getCell(startCol + 2), {
      align: 'right',
      bold: true,
      bg: '#dbe6f7',
      thickTop: true,
      thickRight: true,
      hideZero: true,
    })
  })

  const suffix = [keyword.value, keyword2.value].filter(Boolean).join('_') || 'all'
  const filename = `クボタ堺納期調整_${formatDateCompact(startDate.value)}_${horizonDays.value}日_${suffix}.xlsx`
  const buffer = await workbook.xlsx.writeBuffer()
  const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

const saveDeliveries = async () => {
  if (saving.value || loading.value) return
  if (isEditUnlocked.value && !changeReason.value) {
    alert('変更理由を入力してください。')
    return
  }

  let payloadRows = buildPayloadRows(groups.value, true)
  const noChangeSave = payloadRows.length === 0
  if (noChangeSave) {
    payloadRows = buildPayloadRows(filteredGroups.value, false)
  }

  if (payloadRows.length === 0) {
    alert('保存対象がありません。')
    return
  }

  saving.value = true
  try {
    await api.kubotaSakaiDueAdjustments.bulkSave(payloadRows, {
      change_reason: isEditUnlocked.value ? changeReason.value : '',
    })
    isEditUnlocked.value = false
    changeReason.value = ''
    changeReasonDraft.value = ''
    await loadGrid()
    if (noChangeSave) {
      alert('再保存して再配分を反映しました。')
    } else {
      alert('保存しました。')
    }
  } catch (error) {
    const data = error?.response?.data
    alert(data?.detail || '保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const openChangeReasonDialog = () => {
  changeReasonDraft.value = changeReason.value
  showChangeReasonDialog.value = true
}

const closeChangeReasonDialog = () => {
  showChangeReasonDialog.value = false
}

const confirmChangeReason = () => {
  const reason = (changeReasonDraft.value || '').trim()
  if (!reason) {
    alert('変更理由を入力してください。')
    return
  }
  changeReason.value = reason
  isEditUnlocked.value = true
  showChangeReasonDialog.value = false
}

const coordinationNoteTargetLabel = computed(() => {
  const active = activeCoordinationNote.value
  if (!active) return ''
  const orderLabel = active.sourceOrderNo || (active.orderType === 'FORECAST' ? '内示' : '-')
  const shipToCode = active.shipToCode || '-'
  return `${active.dateLabel} / ${active.productCode} / ${shipToCode} / ${orderLabel}`
})

const openCoordinationNoteDialog = (row, colKey, slotIdx) => {
  const line = slotLineAt(row, colKey, slotIdx)
  const dueAdjustmentId = slotDueAdjustmentId(row, colKey, slotIdx)
  if (!line || !dueAdjustmentId) return
  const col = matrixColumns.value.find((item) => item.colKey === colKey)
  activeCoordinationNote.value = {
    dueAdjustmentId,
    rowDateKey: row.dateKey,
    line,
    productCode: col?.productCode || '',
    shipToCode: col?.shipToCode === '-' ? '' : (col?.shipToCode || ''),
    sourceOrderNo: line.sourceOrderNo || '',
    orderType: line.orderType || '',
    dateLabel: row.label,
  }
  coordinationNoteDraft.value = slotCoordinationNote(row, colKey, slotIdx)
  sharedCoordinationNoteDraft.value = String(line.sharedCoordinationNoteByDate?.[row.dateKey] || '')
  showCoordinationNoteDialog.value = true
}

const closeCoordinationNoteDialog = () => {
  showCoordinationNoteDialog.value = false
  activeCoordinationNote.value = null
  coordinationNoteDraft.value = ''
  sharedCoordinationNoteDraft.value = ''
}

const saveCoordinationNote = async () => {
  const active = activeCoordinationNote.value
  if (!active?.dueAdjustmentId) return
  savingCoordinationNote.value = true
  try {
    const res = await api.kubotaSakaiDueAdjustments.saveCoordinationNote(
      active.dueAdjustmentId,
      coordinationNoteDraft.value,
      sharedCoordinationNoteDraft.value,
    )
    active.line.coordinationNoteByDate[active.rowDateKey] = String(res.data?.coordination_note || '')
    // 同じ日付・品番・納入場所に並ぶ全注番へ、共通連絡の変更を反映する。
    const group = groups.value.find((item) => item.productCode === active.productCode &&
      (item.shipToCode === '-' ? '' : item.shipToCode) === active.shipToCode)
    group?.lines.forEach((line) => {
      line.sharedCoordinationNoteByDate[active.rowDateKey] = String(res.data?.shared_coordination_note || '')
    })
    closeCoordinationNoteDialog()
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '業務連絡メモの保存に失敗しました。'
    alert(detail)
  } finally {
    savingCoordinationNote.value = false
  }
}

const clearCoordinationNote = async () => {
  coordinationNoteDraft.value = ''
  sharedCoordinationNoteDraft.value = ''
  await saveCoordinationNote()
}

// ========== 通知設定 ==========
const showNotifyConfigDialog = ref(false)
const notifyConfigLoading = ref(false)
const notifyConfigSaving = ref(false)
const notifyAllUsers = ref([])
const notifyUserIds = ref([])
const notifyEmailEnabled = ref(false)
const notifyHorizonDays = ref(0)
const notifyConfigMessage = ref('')
const notifyConfigError = ref(false)

const openNotifyConfigDialog = async () => {
  showNotifyConfigDialog.value = true
  notifyConfigLoading.value = true
  notifyConfigMessage.value = ''
  try {
    const res = await api.kubotaSakaiDueAdjustments.getNotifyConfig()
    notifyAllUsers.value = res.data.all_users || []
    notifyUserIds.value = res.data.notify_user_ids || []
    notifyEmailEnabled.value = !!res.data.email_enabled
    notifyHorizonDays.value = res.data.notify_horizon_days || 0
  } catch {
    notifyAllUsers.value = []
    notifyUserIds.value = []
  } finally {
    notifyConfigLoading.value = false
  }
}

const closeNotifyConfigDialog = () => {
  showNotifyConfigDialog.value = false
}

const saveNotifyConfig = async () => {
  notifyConfigSaving.value = true
  notifyConfigMessage.value = ''
  try {
    const res = await api.kubotaSakaiDueAdjustments.saveNotifyConfig({
      notify_user_ids: notifyUserIds.value,
      email_enabled: notifyEmailEnabled.value,
      notify_horizon_days: notifyHorizonDays.value || 0,
    })
    notifyUserIds.value = res.data.notify_user_ids || notifyUserIds.value
    notifyEmailEnabled.value = !!res.data.email_enabled
    notifyHorizonDays.value = res.data.notify_horizon_days || 0
    notifyConfigMessage.value = '保存しました'
    notifyConfigError.value = false
  } catch {
    notifyConfigMessage.value = '保存に失敗しました'
    notifyConfigError.value = true
  } finally {
    notifyConfigSaving.value = false
  }
}

let theadResizeObserver = null

onMounted(async () => {
  await loadFavorites()
  normalizeBulkStartDate()
  await nextTick()
  setStickyTopValues()
  if (theadRef.value) {
    theadResizeObserver = new ResizeObserver(() => setStickyTopValues())
    theadResizeObserver.observe(theadRef.value)
  }
})

onBeforeUnmount(() => {
  if (theadResizeObserver) { theadResizeObserver.disconnect(); theadResizeObserver = null }
})
</script>

<style scoped>
.due-adjustment-page {
  padding: 8px;
  background: #eef2f6;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.toolbar {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #e1e8f4;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 8px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.field label {
  font-size: 12px;
  color: #374151;
}
.field input,
.field select {
  min-width: 60px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-inputs {
  display: flex;
  gap: 4px;
}
.search-field input {
  min-width: 80px;
  width: 120px;
}
.btn {
  padding: 6px 12px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.save-btn {
  background: #dff3e6;
  border-color: #8fc8a1;
}
.lock-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #92400e;
  white-space: nowrap;
}
.import-btn {
  background: #dbe8ff;
  border-color: #8daed6;
}
.favorite-btn {
  background: #facc15;
  border-color: #eab308;
  color: #78350f;
  font-weight: 700;
  min-width: 34px;
}
.lock-badge.adj-badge {
  background: #e0f2fe;
  border-color: #38bdf8;
  color: #0369a1;
}
.lock-badge.plan-lock {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #1e3a8a;
}
.fixed-help {
  font-size: 12px;
  color: #4b5563;
}
.table-wrap {
  flex: 1;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
}
.grid {
  width: max-content;
  min-width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}
.grid th,
.grid td {
  border-right: 1px solid #d7dfe8;
  border-bottom: 1px solid #d7dfe8;
  padding: 3px 6px;
  white-space: nowrap;
  font-size: 14px;
  height: 28px;
  box-sizing: border-box;
  vertical-align: top;
}
.grid thead tr:first-child th {
  border-top: 1px solid #d7dfe8;
}
.grid th:first-child,
.grid td:first-child {
  border-left: 1px solid #d7dfe8;
}
.grid th {
  position: sticky;
  z-index: 2;
}
.grid tbody td {
  padding: 0;
}
.grid thead .head1 th {
  background: #cfd8ec;
}
.grid thead .head2 th {
  background: #e7edf7;
}
.grid th.product-start,
.grid td.product-start {
  border-left: 2px solid #7b8aa7;
}
.grid th.product-end,
.grid td.product-end {
  border-right: 2px solid #7b8aa7;
}
.empty-grid-spacer {
  width: auto;
  min-width: 0;
  background: #fff;
}
.head-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.head-code {
  font-weight: 700;
}
.head-ship {
  color: #374151;
  font-weight: 500;
}
.head-ship-name {
  font-size: 11px;
  color: #6b7280;
  font-weight: 400;
}
.copy-btn {
  height: 22px;
  min-width: 22px;
  padding: 0 6px;
  border: 1px solid #9fb2d1;
  border-radius: 3px;
  background: #f8fbff;
  color: #1f3b69;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}
.copy-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.del-btn {
  color: #dc2626;
  border-color: #f0a0a0;
  background: #fff5f5;
}
.grid th.holiday,
.grid td.holiday {
  background: #ffe3e3;
}
.sticky-left {
  position: sticky;
  left: 0;
  z-index: 4;
  background: #fff;
}
.head1 .sticky-left,
.head2 .sticky-left {
  z-index: 6;
}
.date-col {
  text-align: right;
  padding: 3px 8px !important;
}
.date-separator {
  border-right: 3px solid #5f6f8f !important;
}
.sub-cell {
  height: 26px;
  line-height: 26px;
  padding: 0 6px;
  border-bottom: 1px dashed #e5e7eb;
  box-sizing: border-box;
  text-align: right;
  font-size: 14px;
}
.sub-cell:last-child {
  border-bottom: none;
}
.fixed-plan-cell {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 1px;
  background: #fff7d6;
}
.sub-cell.forecast {
  background: #fafcff;
  color: #64748b;
}
.orderno-subcol .sub-cell {
  text-align: center;
  font-size: 11px;
  color: #374151;
  background: #f1f5f9;
}
.order-label-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 100%;
}
.line-note-btn {
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border: 1px solid #94a3b8;
  border-radius: 999px;
  background: #fff;
  color: #475569;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
}
.line-note-btn.has-note {
  background: #fff7ed;
  border-color: #f97316;
  color: #c2410c;
  font-weight: 700;
}
.readonly-cell {
  color: #4b5563;
}
.readonly-cell.demand .sub-cell {
  background: #f4f7fb;
}
.readonly-cell.demand .sub-cell.forecast {
  background: #eef4fb;
}
.sub-cell input {
  width: 100%;
  height: 22px;
  text-align: right;
  border: 1px solid #d1d5db;
  border-radius: 2px;
  padding: 0 4px;
  box-sizing: border-box;
  background: #fff;
}
.fixed-input {
  font-weight: 700;
  color: #92400e;
}
.fixed-toggle-btn {
  flex: 0 0 auto;
  width: 18px;
  height: 18px;
  border: 1px solid #d1d5db;
  border-radius: 3px;
  background: #f8fafc;
  color: #000;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}
.fixed-toggle-btn.active {
  border-color: #d97706;
  background: #f59e0b;
  color: #000;
}
.total-row th,
.total-row td {
  position: sticky;
  bottom: 0;
  z-index: 5;
  background: #dbe6f7;
  border-top: 2px solid #9ab1d6;
  border-bottom: 1px solid #d7dfe8;
}
.total-row .total-label {
  text-align: center;
  font-weight: 700;
}
.total-row .total-value {
  text-align: right;
  font-weight: 700;
}
.total-row .total-blank {
  background: #e5edf9;
}
.total-row .error {
  color: #b91c1c;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 16px 0;
}
.carry-tr td {
  background: #f0f4ff;
  border-bottom: 2px solid #9ab1d6;
  font-weight: 700;
}
.carry-tr .sticky-left {
  background: #f0f4ff;
}
.carry-value {
  text-align: right;
  padding: 3px 6px !important;
  color: #1e40af;
}
.day-row td {
  border-bottom: 2px solid #94a3b8;
}
.locked-row td {
  background: #f3f4f6 !important;
}
.locked-row .sticky-left {
  background: #f3f4f6 !important;
}
.locked-cell {
  background: #e5e7eb !important;
  color: #9ca3af !important;
  cursor: not-allowed;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal-content {
  width: 420px;
  max-width: calc(100vw - 24px);
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.25);
  padding: 16px;
}
.modal-content h2 {
  margin: 0 0 10px;
  font-size: 16px;
}
.modal-content textarea {
  width: 100%;
  resize: vertical;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 8px;
  font-size: 13px;
  box-sizing: border-box;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.note-target {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}
.note-count {
  margin-top: 6px;
  text-align: right;
  font-size: 11px;
  color: #64748b;
}
.email-modal {
  width: 720px;
  max-height: 90vh;
  overflow-y: auto;
}
.email-field {
  margin-bottom: 14px;
}
.email-field > label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.email-field input[type="text"],
.email-field textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 8px;
  font-size: 14px;
  box-sizing: border-box;
}
.email-field textarea {
  resize: vertical;
}
.email-select {
  width: 100%;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 14px;
}
.email-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}
.email-loading {
  text-align: center;
  padding: 12px;
  color: #6b7280;
}
.email-warning {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  border-radius: 4px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #92400e;
}
.email-send-btn {
  background: #2563eb;
  color: #fff;
  border-color: #1d4ed8;
  font-weight: 600;
}
.email-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.notify-config-modal {
  max-width: 620px;
}
.notify-description {
  color: #555;
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.6;
}
.notify-helper {
  margin: 2px 0 0;
  font-size: 12px;
  color: #666;
}
.notify-horizon-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}
.notify-horizon-input {
  width: 60px;
  padding: 4px 6px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  font-size: 13px;
  text-align: right;
}
.notify-toggle-row {
  display: flex;
  align-items: center;
}
.notify-toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
}
.notify-toggle-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.notify-message {
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
  font-size: 13px;
}
.notify-message.success {
  background: #d4edda;
  color: #155724;
}
.notify-message.error {
  background: #fee;
  color: #c00;
}
</style>
