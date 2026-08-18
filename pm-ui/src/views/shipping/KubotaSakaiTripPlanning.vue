<template>
  <div class="trip-planning-page">
    <div v-if="lockedClickNotice" class="locked-click-toast">
      {{ lockedClickNotice }}
    </div>
    <div class="toolbar">
      <div class="field">
        <label>出荷開始日</label>
        <input v-model="targetDate" type="date" />
      </div>
      <div class="field">
        <label>期間</label>
        <select v-model.number="horizonDays">
          <option :value="5">5日</option>
          <option :value="14">14日</option>
          <option :value="31">31日</option>
          <option :value="60">60日</option>
          <option :value="90">90日</option>
        </select>
      </div>
      <div class="field search-field">
        <label>検索</label>
        <input v-model.trim="keyword" type="text" placeholder="品番" @keydown.enter="loadGrid" />
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
      <button class="btn import-btn" :disabled="importing || loading" @click="importOrders">
        {{ importing ? '取込中...' : '取込' }}
      </button>
      <button class="btn save-btn" :disabled="loading || saving" @click="save">保存</button>
      <button class="btn" :disabled="loading" @click="loadGrid">表示</button>
      <button class="btn" :disabled="loading || !mergedRows.length" @click="openDisplaySettingDialog">表示順</button>
      <button class="btn" :disabled="loading || exportingCsv" @click="exportLoadDetailCsv">
        {{ exportingCsv ? '出力中...' : '占有CSV' }}
      </button>
      <button class="btn pickup-btn" :disabled="loading || exportingPickupPdf" @click="openPickupPdfDialog">
        {{ exportingPickupPdf ? '出力中...' : '集荷明細PDF' }}
      </button>
      <button class="btn detail-btn" :disabled="loading" @click="showTruckDetail = !showTruckDetail">
        便詳細
      </button>
      <DataSourceDialog title="" :sources="dsSources" />
      <button class="btn pseudo-product-btn" :disabled="loading" @click="togglePseudoProductPanel">
        AM/PM対象品
      </button>
      <button class="btn auto-assign-btn" :disabled="loading || saving || autoAssigning" @click="openAutoAssignDialog">
        自動便振分
      </button>
      <label class="toolbar-checkbox">
        <input type="checkbox" v-model="hideWeekends" />
        休日非表示
      </label>
      <button class="btn" :class="{ 'active-toggle': showProgressAdjust }" @click="showProgressAdjust = !showProgressAdjust">
        進捗調整
      </button>
      <button v-if="showProgressAdjust" class="btn save-btn" :disabled="savingProgressAdjust" @click="saveProgressAdjust">
        {{ savingProgressAdjust ? '保存中...' : '調整保存' }}
      </button>
      <span v-if="lastAdjustedAt" class="adj-badge">最新納期調整日: {{ formatAdjDate(lastAdjustedAt) }}</span>
    </div>

    <div v-if="showAutoAssignDialog" class="modal-overlay" @click.self="closeAutoAssignDialog">
      <div class="modal-card">
        <h3 class="modal-title">自動便振分</h3>
        <div class="modal-fields">
          <label class="modal-field">
            <span>適用カレンダ</span>
            <select v-model.number="autoAssignCalendarId">
              <option v-for="cal in calendarList" :key="cal.id" :value="cal.id">{{ cal.calendar_name }}</option>
            </select>
          </label>
          <label class="modal-field">
            <span>振分開始日</span>
            <input v-model="autoAssignStartDate" type="date" />
          </label>
          <label class="modal-field">
            <span>振分終了日</span>
            <input v-model="autoAssignEndDate" type="date" />
          </label>
        </div>
        <label class="modal-check">
          <input v-model="autoAssignResetExisting" type="checkbox" />
          <span>期間内の既存割付をリセットしてから振分</span>
        </label>
        <div class="modal-actions">
          <button class="btn" :disabled="autoAssigning" @click="closeAutoAssignDialog">閉じる</button>
          <button class="btn auto-assign-btn" :disabled="autoAssigning" @click="autoAssignTrips">
            {{ autoAssigning ? '振分中...' : '実行' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showPickupPdfDialog" class="modal-overlay" @click.self="closePickupPdfDialog">
      <div class="modal-card">
        <h3 class="modal-title">集荷明細表（PDF）</h3>
        <div class="modal-fields">
          <label class="modal-field">
            <span>開始日</span>
            <input v-model="pickupPdfStartDate" type="date" />
          </label>
          <label class="modal-field">
            <span>終了日</span>
            <input v-model="pickupPdfEndDate" type="date" />
          </label>
        </div>
        <div class="modal-actions">
          <button class="btn" :disabled="exportingPickupPdf" @click="closePickupPdfDialog">閉じる</button>
          <button class="btn pickup-btn" :disabled="exportingPickupPdf" @click="exportPickupDetailPdf">
            {{ exportingPickupPdf ? '出力中...' : 'PDF出力' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showSaveConfirmDialog" class="modal-overlay" @click.self="closeSaveConfirmDialog">
      <div class="modal-card save-confirm-modal">
        <h3 class="modal-title">保存前チェック</h3>
        <div class="save-confirm-message">保存前チェックで注意点があります。</div>
        <div class="save-confirm-scroll">
          <div v-if="saveValidationState.missingTruckCount" class="save-confirm-section">
            <div class="save-confirm-line">・便未選択: {{ saveValidationState.missingTruckCount }}件</div>
            <div v-for="item in saveValidationState.missingTruckDetails" :key="`missing-${item}`" class="save-confirm-detail">
              {{ item }}
            </div>
            <div class="save-confirm-detail save-confirm-detail-danger">※ このまま保存すると、前工程３班はその便未割り振り分の計画を立てられなくなります</div>
          </div>
          <div v-if="saveValidationState.unassignedQtyCount" class="save-confirm-section">
            <div class="save-confirm-line save-confirm-line-danger">・未割付残あり: {{ saveValidationState.unassignedQtyCount }}件</div>
            <div v-for="item in saveValidationState.unassignedQtyDetails" :key="`unassigned-${item}`" class="save-confirm-detail save-confirm-detail-danger">
              {{ item }}
            </div>
            <div class="save-confirm-detail save-confirm-detail-danger">※ このまま保存すると、前工程３班はその未割付残分の計画を立てられなくなります</div>
          </div>
          <div v-if="saveValidationState.overAssigned.length" class="save-confirm-section">
            <div v-for="item in saveValidationState.overAssigned" :key="`over-${item}`" class="save-confirm-line">
              ・割付数量超過: {{ item }}
            </div>
            <div class="save-confirm-detail save-confirm-detail-danger">※ このまま保存すると、前工程３班は超過分も含めた計画を立てることになります</div>
          </div>
          <div v-if="saveValidationState.overloaded.length" class="save-confirm-line">
            ・便占有率100%超: {{ saveValidationState.overloaded.join(' / ') }}
          </div>
        </div>
        <div class="save-confirm-question">このまま保存しますか？</div>
        <div class="modal-actions">
          <button class="btn" :disabled="saving" @click="closeSaveConfirmDialog">キャンセル</button>
          <button class="btn save-btn" :disabled="saving" @click="proceedSave">OK</button>
        </div>
      </div>
    </div>

    <div v-if="showDisplaySettingDialog" class="modal-overlay" @click.self="showDisplaySettingDialog = false">
      <div class="display-setting-modal">
        <h3 class="modal-title">便計画表示順設定</h3>
        <div class="display-setting-body">
          <div class="display-setting-table-wrap">
            <table class="display-setting-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>品番</th>
                  <th>品名</th>
                  <th>納入地</th>
                  <th>行色(RGB)</th>
                  <th>+色(RGB)</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, idx) in displaySettingItems"
                  :key="item.key"
                  :style="{ background: displaySettingActiveKey === item.key ? '#dbeafe' : idx % 2 ? '#fafafa' : '#fff' }"
                >
                  <td>{{ idx + 1 }}</td>
                  <td>{{ item.product_code }}</td>
                  <td>{{ item.product_name || '' }}</td>
                  <td>{{ item.ship_to_code || '-' }}</td>
                  <td>
                    <div class="rgb-editor">
                      <input type="text" inputmode="numeric" :value="hexToR(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'r', $event.target.value)" />
                      <input type="text" inputmode="numeric" :value="hexToG(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'g', $event.target.value)" />
                      <input type="text" inputmode="numeric" :value="hexToB(item.bg_color)" @input="item.bg_color = setRgbChannel(item.bg_color, 'b', $event.target.value)" />
                    </div>
                  </td>
                  <td>
                    <div class="rgb-editor">
                      <input type="text" inputmode="numeric" :value="hexToR(item.plus_bg_color)" @input="item.plus_bg_color = setRgbChannel(item.plus_bg_color, 'r', $event.target.value)" />
                      <input type="text" inputmode="numeric" :value="hexToG(item.plus_bg_color)" @input="item.plus_bg_color = setRgbChannel(item.plus_bg_color, 'g', $event.target.value)" />
                      <input type="text" inputmode="numeric" :value="hexToB(item.plus_bg_color)" @input="item.plus_bg_color = setRgbChannel(item.plus_bg_color, 'b', $event.target.value)" />
                    </div>
                  </td>
                  <td class="display-setting-actions">
                    <button class="mini" @click="moveDisplaySettingItem(idx, -1)" :disabled="idx === 0">&uarr;</button>
                    <button class="mini" @click="moveDisplaySettingItem(idx, 1)" :disabled="idx === displaySettingItems.length - 1">&darr;</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="display-setting-samples">
            <div class="display-setting-sample-title">色サンプル</div>
            <div class="display-setting-sample-group">
              <div class="display-setting-sample-label">行背景色</div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#bfdbfe;"></span><span>191 219 254</span></div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#bbf7d0;"></span><span>187 247 208</span></div>
            </div>
            <div class="display-setting-sample-group">
              <div class="display-setting-sample-label">+ボタン色</div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#d4a574;"></span><span>212 165 116</span></div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#bbbbbb;"></span><span>187 187 187</span></div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#444444;"></span><span>68 68 68</span></div>
              <div class="display-setting-sample-item"><span class="sample-chip" style="background:#fbbf24;"></span><span>251 191 36</span></div>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showDisplaySettingDialog = false">キャンセル</button>
          <button class="btn save-btn" :disabled="savingDisplaySettings" @click="saveDisplaySettings">
            {{ savingDisplaySettings ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showTruckDetail" class="truck-detail-wrap">
      <table class="truck-detail-table">
        <thead>
          <tr>
            <th>便名</th>
            <th>俗称</th>
            <th>出発時刻</th>
            <th>着時刻</th>
            <th>長さ(mm)</th>
            <th>奥行き(mm)</th>
            <th>Gap(mm)</th>
            <th>日ずれ</th>
            <th>通常便</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="truck in detailTrucks" :key="`detail-${truck.id}`">
            <td>{{ truck.name || '-' }}</td>
            <td>{{ truckDisplayName(truck) }}</td>
            <td>{{ truck.departure_time || '-' }}</td>
            <td>{{ truck.arrival_time || '-' }}</td>
            <td class="num-cell">{{ formatNumber(truck.width) }}</td>
            <td class="num-cell">{{ formatNumber(truck.depth) }}</td>
            <td class="num-cell">{{ truck.container_gap || 0 }}</td>
            <td class="num-cell">{{ formatNumber(truck.arrival_day_offset) }}</td>
            <td>{{ truck.default_use ? '通常' : '-' }}</td>
          </tr>
          <tr v-if="!detailTrucks.length">
            <td colspan="9" class="detail-empty">便マスタがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showPseudoProductPanel" class="pseudo-product-wrap">
      <div class="pseudo-product-toolbar">
        <span class="pseudo-product-title">AM/PMグループ対象製品</span>
        <button class="btn save-btn" :disabled="savingPseudo" @click="savePseudoProducts">
          {{ savingPseudo ? '保存中...' : '保存' }}
        </button>
      </div>
      <table class="pseudo-product-table">
        <thead>
          <tr>
            <th class="pseudo-label-col">便</th>
            <th v-for="row in pseudoProductRows" :key="`pth-${row.key}`" class="pseudo-product-col">
              <div class="pseudo-col-code">{{ row.product_code }}</div>
              <div class="pseudo-col-name">{{ productNameMap.get(row.product_code) || '' }}</div>
              <div class="pseudo-col-shipto">{{ row.ship_to_code || '-' }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pt in pseudoTrucks" :key="`ptr-${pt.id}`">
            <td class="pseudo-label-col">{{ pt.alias_name || pt.name }}</td>
            <td v-for="row in pseudoProductRows" :key="`pp-${row.key}-${pt.id}`" class="pseudo-check-cell">
              <input
                type="checkbox"
                :checked="row.truckIds.has(pt.id)"
                @change="togglePseudoTruck(row, pt.id)"
              />
            </td>
          </tr>
          <tr v-if="!pseudoProductRows.length">
            <td colspan="1" class="detail-empty">データがありません</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="main-layout">
      <div class="table-wrap" ref="tableWrapRef">
      <table class="grid">
        <thead ref="theadRef">
          <tr>
            <th rowspan="4" class="left-head code-col">品番</th>
            <th rowspan="4" class="left-head shipto-col">納入場</th>
            <th
              v-for="dateKey in dateKeys"
              :key="`day-${dateKey}`"
              :colspan="SLOT_COUNT"
              class="date-head"
              :class="{
                'holiday-head': isHoliday(dateKey),
                'overdue-head': hasOverdueDate(dateKey),
                'day-split-left': isDaySplitStart(dateKey),
              }"
            >
              <div class="date-head-content">
                <span class="pseudo-occ pseudo-occ-left" :class="{ 'pseudo-occ-over': pseudoTruckOccupancyPercent(dateKey, 'AM') > 95 }">AM:{{ pseudoTruckOccupancyPercent(dateKey, 'AM') }}%</span>
                <div class="date-head-center">
                  <span class="date-head-label">{{ formatHeaderDate(dateKey) }}</span>
                  <button
                    class="date-head-note-btn"
                    :class="{ 'has-note': hasDateHeaderNote(dateKey) }"
                    :title="dateHeaderNoteButtonTitle(dateKey)"
                    @click="openDateHeaderNoticeDialog(dateKey)"
                  >{{ hasDateHeaderNote(dateKey) ? 'メモ' : '📝' }}</button>
                </div>
                <span class="pseudo-occ pseudo-occ-right" :class="{ 'pseudo-occ-over': pseudoTruckOccupancyPercent(dateKey, 'PM') > 95 }">PM:{{ pseudoTruckOccupancyPercent(dateKey, 'PM') }}%</span>
              </div>
            </th>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`truck-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`truck-${dateKey}-${slotIdx}`"
                :class="[
                  'truck-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                {{ truckNameAt(dateKey, slotIdx - 1) }}
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`occ-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`occ-${dateKey}-${slotIdx}`"
                :class="[
                  'occ-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                <div class="occ-head-content">
                  <span>{{ truckOccupancyLabel(dateKey, slotIdx - 1) }}</span>
                  <span
                    v-if="showTruck60Diff(dateKey, slotIdx - 1)"
                    class="truck-60-diff"
                    :class="{ negative: truckDiffFrom60(dateKey, slotIdx - 1) < 0 }"
                  >
                    {{ formatSignedNumber(truckDiffFrom60(dateKey, slotIdx - 1)) }}
                  </span>
                </div>
              </th>
            </template>
          </tr>
          <tr>
            <template v-for="dateKey in dateKeys" :key="`item-${dateKey}`">
              <th
                v-for="slotIdx in SLOT_COUNT"
                :key="`item-${dateKey}-${slotIdx}`"
                :class="[
                  'item-head',
                  slotWidthClass(slotIdx - 1),
                  {
                    'holiday-head': isHoliday(dateKey),
                    'day-split-left': slotIdx === 1 && isDaySplitStart(dateKey),
                  },
                ]"
              >
                <template v-if="slotIdx - 1 === 3">
                  <div class="select-head-grid">
                    <span>便</span>
                    <span>容数</span>
                    <span>容器</span>
                    <span>個数</span>
                    <span>＋－</span>
                  </div>
                </template>
                <template v-else>
                  {{ slotLabels[slotIdx - 1] }}
                </template>
              </th>
            </template>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in mergedRows" :key="row.rowKey" :class="{ 'trip-colored-row': hasRowCustomColor(row) }" :style="getRowColorStyle(row)">
            <td class="code-col">
              <div>{{ row.product_code }}</div>
              <div class="product-name">{{ productNameMap.get(row.product_code) || '' }}</div>
            </td>
            <td class="shipto-col">
              <div>{{ row.ship_to_code || '-' }}</div>
              <div v-if="row.ship_to_name" class="shipto-name">{{ row.ship_to_name }}</div>
            </td>
            <template v-for="dateKey in dateKeys" :key="`${row.rowKey}-${dateKey}`">
              <td class="cell-center cell-stacked col-order" :class="{ 'day-split-left': isDaySplitStart(dateKey) }">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-order-${slotIdx}`"
                  class="sub-cell entry-text-subcell"
                  :style="slotBlockStyle(slotEntryAt(row, dateKey, slotIdx - 1))"
                >
                  <div class="entry-order-wrap">
                    <span>{{ sourceOrderLabel(slotEntryAt(row, dateKey, slotIdx - 1)) }}</span>
                  </div>
                  <button
                    v-if="slotEntryAt(row, dateKey, slotIdx - 1)?.coordination_note"
                    class="entry-note-badge"
                    type="button"
                    @mouseenter="showCoordinationNoteBubble(slotEntryAt(row, dateKey, slotIdx - 1), $event)"
                    @mouseleave="hideCursorBubble"
                    @focus="showCoordinationNoteBubble(slotEntryAt(row, dateKey, slotIdx - 1), $event)"
                    @blur="hideCursorBubble"
                  >連絡</button>
                </div>
              </td>
              <td class="cell-right cell-stacked col-demand">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-demand-${slotIdx}`"
                  class="sub-cell entry-text-subcell"
                  :style="slotBlockStyle(slotEntryAt(row, dateKey, slotIdx - 1))"
                >
                  {{ formatNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.delivery_qty) }}
                </div>
              </td>
              <td class="cell-right cell-stacked col-assigned">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-assigned-${slotIdx}`"
                  class="sub-cell entry-text-subcell"
                  :style="slotBlockStyle(slotEntryAt(row, dateKey, slotIdx - 1))"
                >
                  {{ formatNumber(assignedQty(slotEntryAt(row, dateKey, slotIdx - 1))) }}
                </div>
              </td>
              <td class="cell-select cell-stacked col-select">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-select-${slotIdx}`"
                  class="sub-cell select-subcell"
                  :style="slotBlockStyle(slotEntryAt(row, dateKey, slotIdx - 1))"
                >
                  <div v-if="slotEntryAt(row, dateKey, slotIdx - 1)" class="allocation-stack">
                    <div
                      v-for="(al, idx) in slotEntryAt(row, dateKey, slotIdx - 1).allocations"
                      :key="`${row.rowKey}-${dateKey}-${slotIdx}-al-${idx}`"
                      class="allocation-row"
                      :class="{ 'allocation-row-locked': isAllocationLocked(al) }"
                      :title="isAllocationLocked(al) ? al.lock_reason : ''"
                      @click="handleLockedAllocationClick(al)"
                    >
                      <select class="truck-select" v-model.number="al.truck_id" :disabled="isAllocationLocked(al)" @change="handleAllocationTruckSelect(slotEntryAt(row, dateKey, slotIdx - 1), dateKey, al.truck_id)">
                        <option :value="null">便</option>
                        <option
                          v-for="truck in displayTrucksForDate(dateKey)"
                          :key="truck.id"
                          :value="truck.id"
                          :disabled="isLockedTruck(dateKey, truck.id)"
                        >
                          {{ truckDisplayName(truck) }}
                        </option>
                      </select>
                      <input
                        v-model="al.container_count"
                        type="text"
                        inputmode="numeric"
                        :disabled="isAllocationLocked(al)"
                        @input="handleContainerCountInput(slotEntryAt(row, dateKey, slotIdx - 1))"
                      />
                      <select
                        v-if="containersForProduct(row.product_code).length > 0"
                        v-model.number="al.container_id"
                        class="container-select"
                        :disabled="isAllocationLocked(al)"
                        @change="handleAllocationChange(slotEntryAt(row, dateKey, slotIdx - 1))"
                      >
                        <option :value="null">容器</option>
                        <option
                          v-for="c in containersForProduct(row.product_code)"
                          :key="c.container_id"
                          :value="c.container_id"
                        >
                          {{ c.container_name }}
                        </option>
                      </select>
                      <input
                        v-model="al.qty"
                        type="text"
                        inputmode="numeric"
                        :disabled="isAllocationLocked(al)"
                        @input="handleAllocationQtyInput(slotEntryAt(row, dateKey, slotIdx - 1))"
                        @focus="showProductBubble(row, $event)"
                        @mouseenter="showProductBubble(row, $event)"
                        @blur="handleQtyInputBlur"
                        @mouseleave="handleQtyInputMouseLeave($event)"
                      />
                      <div class="allocation-actions">
                        <button class="mini" :style="getPlusButtonStyle(row)" :disabled="isEntryFullyLocked(slotEntryAt(row, dateKey, slotIdx - 1))" @click="addAllocation(slotEntryAt(row, dateKey, slotIdx - 1), row.used_container_id)">+</button>
                        <button
                          class="mini danger"
                          :disabled="isAllocationLocked(al) || slotEntryAt(row, dateKey, slotIdx - 1).allocations.length <= 1"
                          @click="removeAllocation(slotEntryAt(row, dateKey, slotIdx - 1), idx)"
                        >
                          -
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </td>
              <td class="cell-right cell-stacked col-remain">
                <div
                  v-for="slotIdx in row.maxSlots"
                  :key="`${row.rowKey}-${dateKey}-remain-${slotIdx}`"
                  class="sub-cell entry-text-subcell"
                  :style="slotBlockStyle(slotEntryAt(row, dateKey, slotIdx - 1))"
                  :class="{ 'remain-negative': parseNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.unassigned_qty_preview) < 0 }"
                >
                  {{ formatNumber(slotEntryAt(row, dateKey, slotIdx - 1)?.unassigned_qty_preview) }}
                </div>
              </td>
              <td class="cell-right cell-stacked col-progress" :class="{ 'progress-negative': parseNumber(progressAt(row, dateKey)) < 0 }">
                <div class="sub-cell">{{ formatNumber(progressAt(row, dateKey)) }}</div>
                <div v-if="showProgressAdjust" class="sub-cell progress-adjust-cell">
                  <input
                    :value="progressAdjustAt(row, dateKey)"
                    type="text"
                    inputmode="numeric"
                    class="progress-adjust-input"
                    @input="setProgressAdjust(row, dateKey, $event.target.value)"
                  />
                </div>
              </td>
            </template>
          </tr>
          <tr v-if="!mergedRows.length">
            <td :colspan="2 + dateKeys.length * SLOT_COUNT" class="empty">データがありません</td>
          </tr>
          <tr v-else class="daily-load-row">
              <td class="code-col daily-load-label">積み荷明細</td>
              <td class="shipto-col daily-load-label daily-load-note">宵積みの便は前日列へ表示</td>
            <template v-for="dateKey in dateKeys" :key="`daily-load-${dateKey}`">
              <td class="daily-load-cell" :colspan="SLOT_COUNT" :class="{ 'day-split-left': isDaySplitStart(dateKey) }">
                <div v-if="(loadBlocksByDate[dateKey] || []).length" class="daily-load-blocks">
                  <table class="daily-load-table">
                    <tbody>
                      <template v-for="(block, blockIdx) in loadBlocksByDate[dateKey]" :key="`${dateKey}-block-${blockIdx}`">
                        <tr
                          v-for="(line, lineIdx) in block.lines"
                          :key="`${dateKey}-line-${blockIdx}-${lineIdx}`"
                          :class="{ 'daily-load-block-start': blockIdx > 0 && lineIdx === 0 }"
                        >
                          <td v-if="lineIdx === 0" class="daily-load-truck" :rowspan="block.lines.length">
                            <div class="daily-load-truck-line">
                              <span>{{ block.truckLabel }}</span>
                              <span class="daily-load-truck-occ">{{ truckDepartureOccupancyLabelById(block.occupancyDateKey, block.truckId) }}</span>
                            </div>
                          </td>
                          <td class="daily-load-product">
                            <div v-if="line[0]" class="daily-load-product-line">
                              <span>{{ loadDetailProductBaseLabel(line[0]) }}</span>
                              <span class="daily-load-shipto">{{ formatLoadDetailShipTo(line[0]) }}</span>
                            </div>
                          </td>
                          <td class="daily-load-product">
                            <div v-if="line[1]" class="daily-load-product-line">
                              <span>{{ loadDetailProductBaseLabel(line[1]) }}</span>
                              <span class="daily-load-shipto">{{ formatLoadDetailShipTo(line[1]) }}</span>
                            </div>
                          </td>
                        </tr>
                      </template>
                    </tbody>
                  </table>
                </div>
                <div v-else class="daily-load-empty">-</div>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
      </div>

      <aside class="plan-sidebar">
        <div class="plan-sidebar-header">
          <span class="plan-sidebar-title">積載平面図（出発日）</span>
          <div class="plan-sidebar-date-control">
            <button class="plan-date-btn" :disabled="!planPrevDate" @click="planDate = planPrevDate">‹</button>
            <input v-model="planDate" type="date" class="plan-sidebar-date-input" />
            <button class="plan-date-btn" :disabled="!planNextDate" @click="planDate = planNextDate">›</button>
          </div>
        </div>
        <div ref="planSidebarBodyRef" class="plan-sidebar-body">
          <div
            v-for="truck in planTruckModels"
            :key="`plan-${truck.truckId}`"
            class="plan-truck-card"
            :class="{ 'plan-truck-card-active': activePlanTruckId === truck.truckId }"
            :data-plan-truck-id="truck.truckId"
          >
            <div class="plan-truck-header">
              <div class="plan-truck-header-main">
                <span class="plan-truck-name">{{ truck.label }}</span>
                <button
                  type="button"
                  class="plan-note-btn"
                  :class="{ 'has-note': truck.hasNotice }"
                  title="事務所連絡を入力"
                  @click="openTripNoticeDialog(truck)"
                >📝</button>
              </div>
              <div class="plan-truck-header-right">
                <span
                  v-for="n in truck.notices"
                  :key="n.notice_type"
                  class="plan-note-badge"
                  :class="{ urgent: n.notice_type === 'URGENT', vendor: n.notice_type === 'VENDOR' }"
                >{{ n.notice_type === 'URGENT' ? '緊急連絡' : n.notice_type === 'VENDOR' ? '業者連絡' : '出荷担当連絡' }}</span>
                <span v-if="truck.overloaded" class="plan-overload-badge">積載超過</span>
              </div>
            </div>
            <div v-for="n in truck.notices" :key="`preview-${n.notice_type}`" class="plan-note-preview">{{ noticeTypeLabel(n.notice_type) }}: {{ n.notice_text }}</div>
            <div class="plan-svg-wrap">
              <svg :viewBox="truck.viewBox" class="plan-svg" preserveAspectRatio="xMidYMid meet">
                <rect :x="0" :y="0" :width="truck.viewW" :height="truck.viewH" class="plan-bed" />
                <template v-for="(item, idx) in truck.placed" :key="`${truck.truckId}-pl-${idx}`">
                  <g>
                    <rect
                      :x="item.x" :y="item.y"
                      :width="item.w" :height="item.d"
                      :fill="item.color"
                      class="plan-container"
                    >
                      <title>{{ item.label }}（{{ item.layers }}段）</title>
                    </rect>
                    <text
                      :x="item.x + item.w / 2"
                      :y="item.y + item.d / 2"
                      :font-size="item.fontSize"
                      text-anchor="middle"
                      dominant-baseline="central"
                      class="plan-layer-text"
                    >{{ item.layers }}</text>
                  </g>
                </template>
              </svg>
            </div>
            <div class="plan-legend">
              <div v-for="(item, idx) in truck.items" :key="`${truck.truckId}-lg-${idx}`" class="plan-legend-row">
                <span class="plan-swatch" :style="{ background: item.color }"></span>
                <div class="plan-legend-text">
                  <div class="plan-legend-code">{{ item.productCode }}×{{ formatNumber(item.qty) }}（{{ item.containerCount }}容器）</div>
                </div>
              </div>
            </div>
            <div class="plan-remaining">
              <div v-if="truck.remaining.length">
                <span class="plan-remaining-label">残りスペース</span>
                <div v-for="(r, idx) in truck.remaining" :key="`${truck.truckId}-rm-${idx}`" class="plan-remaining-row">
                  <span class="plan-remaining-code">{{ r.label }}</span>
                  <span class="plan-remaining-count">あと{{ r.count }}箱</span>
                </div>
              </div>
              <div v-else class="plan-remaining-empty">残りスペースなし</div>
            </div>
          </div>
          <div v-if="!planTruckModels.length" class="plan-sidebar-empty">
            {{ planDateLoaded ? '便マスタがありません' : '指定日のデータがありません' }}
          </div>
        </div>
      </aside>
    </div>

    <div v-if="showTripNoticeDialog" class="modal-overlay" @click.self="closeTripNoticeDialog">
      <div class="modal-card trip-note-modal">
        <h3 class="modal-title">メモ</h3>
        <div class="trip-note-target">{{ activeTripNoticeLabel }}</div>
        <div v-if="tripNoticeTabs.length > 1" class="trip-note-tabs">
          <button
            v-for="t in tripNoticeTabs"
            :key="t"
            class="trip-note-tab"
            :class="{ active: tripNoticeTypeDraft === t, 'has-text': !!tripNoticeDrafts[t] }"
            @click="tripNoticeTypeDraft = t"
          >{{ noticeTypeLabel(t) }}<span v-if="tripNoticeDrafts[t]" class="tab-dot"></span></button>
        </div>
        <div class="modal-fields">
          <label class="modal-field">
            <textarea
              v-model.trim="tripNoticeDrafts[tripNoticeTypeDraft]"
              class="trip-note-textarea"
              maxlength="200"
              :placeholder="activeTripNotice?.noticeScope === 'date_header' ? 'メモを入力' : `${noticeTypeLabel(tripNoticeTypeDraft)}への連絡を入力`"
            ></textarea>
          </label>
        </div>
        <div class="trip-note-count">{{ (tripNoticeDrafts[tripNoticeTypeDraft] || '').length }}/200</div>
        <template v-for="t in tripNoticeTabs" :key="`ref-${t}`">
          <div v-if="t !== tripNoticeTypeDraft && tripNoticeDrafts[t]" class="trip-note-ref">
            <span class="trip-note-ref-label">{{ noticeTypeLabel(t) }}:</span> {{ tripNoticeDrafts[t] }}
          </div>
        </template>
        <div class="modal-actions">
          <button class="btn" :disabled="savingTripNotice" @click="closeTripNoticeDialog">閉じる</button>
          <button class="btn" :disabled="savingTripNotice" @click="clearTripNotice">削除</button>
          <button class="btn save-btn" :disabled="savingTripNotice" @click="saveTripNotice">
            {{ savingTripNotice ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div class="note">未割付期限: 調整後納期の{{ assignmentDeadlineDays }}営業日前</div>
    <div
      v-if="cursorBubbleText"
      class="cursor-product-bubble"
      :style="cursorProductBubbleStyle"
    >{{ cursorBubbleText }}</div>

  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '便割付 読み書き', table: 't_kubota_sakai_trip_assignment', desc: '納期調整→便への割付データ' },
  { op: '納期調整 読み取り', table: 't_kubota_sakai_due_adjustment', desc: '出荷数(delivery_qty)の参照元' },
  { op: '便マスタ 読み取り', table: 'm_kubota_sakai_truck', desc: '便名・積載量' },
  { op: '表示順/色設定 読み書き', table: 't_kubota_sakai_trip_display_setting', desc: '便計画の品番+納入地別の表示順・色設定' },
  { op: '擬似便製品 読み書き', table: 'm_kubota_sakai_pseudo_truck_product', desc: '擬似便自動振分の製品マスタ' },
  { op: 'お気に入り 読み書き', table: 'user_favorite', desc: '画面フィルタのお気に入り保存' },
  { op: 'カレンダー 読み取り', table: 'm_calendar / m_calendar_day', desc: '営業日判定' },
  { op: '進捗 読み書き', table: 't_kubota_sakai_delivery_progress', desc: '製品×納入地別の日別進捗(需要・振分・調整)' },
]
const theadRef = ref(null)
const tableWrapRef = ref(null)

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

const SLOT_COUNT = 6
const slotLabels = ['注番', '需要', '振分', '便選択', '残', '進捗']

const formatLocalDate = (date) => {
  const yyyy = String(date.getFullYear())
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const addDays = (baseDate, days) => {
  const d = new Date(`${baseDate}T00:00:00`)
  d.setDate(d.getDate() + days)
  return formatLocalDate(d)
}

const formatHeaderDate = (dateText) => {
  const d = new Date(`${dateText}T00:00:00`)
  const w = ['日', '月', '火', '水', '木', '金', '土'][d.getDay()]
  return `${d.getMonth() + 1}/${d.getDate()}(${w})`
}

const formatAdjDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
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

const formatLoadDetailShipTo = (item) => {
  if (item?.shipToCode) return String(item.shipToCode)
  if (item?.shipToName) return String(item.shipToName)
  return ''
}

const loadDetailProductBaseLabel = (item) => `${item.productCode}×${formatNumber(item.qty)}`

const parseIntegerQty = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const normalized = String(value).replace(/[，,]/g, '').replace(/[．]/g, '.')
  const num = Number(normalized)
  return Number.isFinite(num) ? Math.max(0, Math.trunc(num)) : 0
}

const parseSignedIntegerQty = (value) => {
  if (value === null || value === undefined || value === '') return 0
  const normalized = String(value).replace(/[，,]/g, '').replace(/[．]/g, '.')
  const num = Number(normalized)
  return Number.isFinite(num) ? Math.trunc(num) : 0
}

const normalizeQtyText = (value) => {
  const qty = parseIntegerQty(value)
  return qty > 0 ? String(qty) : ''
}

const findContainerOption = (productCode, containerId) => {
  if (!productCode || !containerId) return null
  const options = productContainersMap.value[productCode] || []
  return options.find((item) => Number(item.container_id) === Number(containerId)) || null
}

const resolveAllocationCapacity = (entry, allocation) => {
  const capacity = findContainerOption(entry?.product_code, allocation?.container_id)?.capacity
  const parsed = parseIntegerQty(capacity)
  if (parsed > 0) return parsed
  const fallback = parseIntegerQty(entry?.default_capacity)
  return fallback > 0 ? fallback : 1
}

const normalizeContainerCountText = (value) => {
  const count = parseIntegerQty(value)
  return count > 0 ? String(count) : ''
}

const syncAllocationFromQty = (entry, allocation) => {
  allocation.qty = normalizeQtyText(allocation.qty)
  const qty = parseIntegerQty(allocation.qty)
  if (qty <= 0) {
    allocation.container_count = ''
    return
  }
  const capacity = resolveAllocationCapacity(entry, allocation)
  allocation.container_count = String(Math.ceil(qty / capacity))
}

const syncAllocationFromContainerCount = (entry, allocation) => {
  allocation.container_count = normalizeContainerCountText(allocation.container_count)
  const count = parseIntegerQty(allocation.container_count)
  if (count <= 0) {
    allocation.qty = ''
    return
  }
  const capacity = resolveAllocationCapacity(entry, allocation)
  allocation.qty = String(count * capacity)
}

const normalizeAllocation = (item = null, defaultContainerId = null) => ({
  id: item?.id ?? null,
  truck_id: item?.truck_id ?? null,
  container_id: item?.container_id ?? defaultContainerId,
  container_count: '',
  qty: normalizeQtyText(item?.qty ?? ''),
  is_locked: Boolean(item?.is_locked),
  lock_reason: item?.lock_reason || '',
})

const hexToRgb = (hex) => {
  if (!hex || hex.length < 7) return [255, 255, 255]
  const n = parseInt(hex.slice(1), 16)
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255]
}

const hexToR = (hex) => hexToRgb(hex)[0]
const hexToG = (hex) => hexToRgb(hex)[1]
const hexToB = (hex) => hexToRgb(hex)[2]

const setRgbChannel = (hex, ch, val) => {
  const [r, g, b] = hexToRgb(hex || '#ffffff')
  const v = Math.max(0, Math.min(255, Number(val) || 0))
  const nr = ch === 'r' ? v : r
  const ng = ch === 'g' ? v : g
  const nb = ch === 'b' ? v : b
  return `#${((1 << 24) | (nr << 16) | (ng << 8) | nb).toString(16).slice(1)}`
}

const getTripRowKey = (row) => `${row?.product_code || ''}||${row?.ship_to_code || ''}`

const sortEntries = (items = []) => {
  return [...items].sort((a, b) => {
    const aFc = a.order_type === 'FORECAST' ? 1 : 0
    const bFc = b.order_type === 'FORECAST' ? 1 : 0
    if (aFc !== bFc) return aFc - bFc
    return String(a.source_order_no || '').localeCompare(String(b.source_order_no || ''))
  })
}

const todayDate = formatLocalDate(new Date())
const defaultTargetDate = ref(todayDate)
const targetDate = ref(todayDate)
const planDate = ref(todayDate)
const horizonDays = ref(5)
const keyword = ref('')
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')
const FAVORITE_SCREEN_KEY = 'shipping.kubota_sakai_trip_planning'
const loading = ref(false)
const importing = ref(false)
const saving = ref(false)
const lastAdjustedAt = ref(null)
const exportingCsv = ref(false)
const exportingPickupPdf = ref(false)
const assignmentDeadlineDays = ref(3)
const trucksByDate = ref({})
const lockedTripsByDate = ref({})
const summaryByDate = ref({})
const departureSummaryByDate = ref({})
const previewSummaryByDate = ref({})
const previewDepartureSummaryByDate = ref({})
const mergedRows = ref([])
const productContainersMap = ref({})
const previewTimers = new Map()
let latestDeparturePreviewRequestId = 0
const showTruckDetail = ref(false)
const planSidebarBodyRef = ref(null)
const activePlanTruckId = ref(null)
const showPseudoProductPanel = ref(false)
const pseudoTrucks = ref([])
const pseudoProductRows = ref([])
const savingPseudo = ref(false)
const autoAssigning = ref(false)
const showAutoAssignDialog = ref(false)
const calendarList = ref([])
const autoAssignCalendarId = ref(null)
const autoAssignStartDate = ref('')
const autoAssignEndDate = ref('')
const autoAssignResetExisting = ref(false)
const showSaveConfirmDialog = ref(false)
const saveValidationState = ref({
  missingTruckCount: 0,
  missingTruckDetails: [],
  unassignedQtyCount: 0,
  unassignedQtyDetails: [],
  overAssigned: [],
  overloaded: [],
})
const calendarDayMap = ref({})
const productNameMap = ref(new Map())
const showPickupPdfDialog = ref(false)
const pickupPdfStartDate = ref('')
const pickupPdfEndDate = ref('')
const holidayByDate = ref({})
const progressByDate = ref({})
const showProgressAdjust = ref(false)
const savingProgressAdjust = ref(false)
const progressAdjustEdits = ref({})
const cursorBubbleText = ref('')
const cursorProductBubbleStyle = ref({})
const lockedClickNotice = ref('')
const showDisplaySettingDialog = ref(false)
const displaySettingItems = ref([])
const savingDisplaySettings = ref(false)
const displaySettingActiveKey = ref('')
const displaySettingMap = ref(new Map())
const showTripNoticeDialog = ref(false)
const savingTripNotice = ref(false)
const tripNoticeDrafts = ref({ NORMAL: '', URGENT: '', VENDOR: '' })
const tripNoticeTypeDraft = ref('NORMAL')
const activeTripNotice = ref(null)
const dateHeaderNoticesByDate = ref({})
const noticeTypeLabel = (t) => t === 'URGENT' ? '緊急' : t === 'VENDOR' ? '業者' : '出荷担当'
const DATE_HEADER_TRIP_REF = 'DATEHDR:MAIN'
const HIDE_WEEKENDS_KEY = 'kubotaSakaiTripPlanning.hideWeekends'
const hideWeekends = ref(localStorage.getItem(HIDE_WEEKENDS_KEY) === '1')

const allDateKeys = computed(() => {
  const span = Math.max(1, Number(horizonDays.value) || 1)
  return Array.from({ length: span }).map((_, idx) => addDays(targetDate.value, idx))
})

const dateKeys = computed(() => {
  if (!hideWeekends.value) return allDateKeys.value
  return allDateKeys.value.filter((dk) => isWorkingDayByCalendar(dk))
})

const detailTrucks = computed(() => {
  const firstDate = dateKeys.value[0]
  const base = (trucksByDate.value[firstDate] || []).filter((truck) => !isPseudoTruck(truck))
  if (base.length > 0) return base
  const merged = []
  const seen = new Set()
  Object.values(trucksByDate.value || {}).forEach((list) => {
    ;(list || []).forEach((truck) => {
      if (isPseudoTruck(truck)) return
      const key = Number(truck.id)
      if (seen.has(key)) return
      seen.add(key)
      merged.push(truck)
    })
  })
  return merged
})

const activeTripNoticeLabel = computed(() => {
  const truck = activeTripNotice.value
  if (!truck) return ''
  return `${truck.label || '便'} / ${truck.dateKey || ''}`
})
const tripNoticeTabs = computed(() => activeTripNotice.value?.noticeScope === 'date_header' ? ['NORMAL'] : ['NORMAL', 'URGENT', 'VENDOR'])

const isHoliday = (dateKey) => Boolean(holidayByDate.value[dateKey])
const isDaySplitStart = (dateKey) => dateKeys.value[0] !== dateKey
const pseudoTruckMarkers = {
  AM: new Set(['A', 'A便', 'Ａ', 'Ａ便', 'AM', 'AM便', 'ＡＭ', 'ＡＭ便']),
  PM: new Set(['P', 'P便', 'Ｐ', 'Ｐ便', 'PM', 'PM便', 'ＰＭ', 'ＰＭ便']),
}
const normalizeTruckMarker = (truck) => String(truck?.alias_name || truck?.name || '').trim().toUpperCase()
const isPseudoTruckType = (truck, type) => {
  const marker = normalizeTruckMarker(truck)
  const base = marker.replace(/\s+/g, '')
  if (type === 'AM' || type === 'A') return pseudoTruckMarkers.AM.has(base)
  if (type === 'PM' || type === 'P') return pseudoTruckMarkers.PM.has(base)
  return false
}
const isPseudoTruck = (truck) => isPseudoTruckType(truck, 'AM') || isPseudoTruckType(truck, 'PM')
const displayTrucksForDate = (dateKey) => (trucksByDate.value[dateKey] || []).filter((truck) => !isPseudoTruck(truck))
const slotWidthClass = (slotIdx) => {
  if (slotIdx === 0) return 'col-order'
  if (slotIdx === 1) return 'col-demand'
  if (slotIdx === 2) return 'col-assigned'
  if (slotIdx === 3) return 'col-select'
  if (slotIdx === 4) return 'col-remain'
  return 'col-progress'
}

const compareTripPlanningRows = (a, b) => {
  const keyA = getTripRowKey(a)
  const keyB = getTripRowKey(b)
  const orderA = displaySettingMap.value.get(keyA)?.display_order
  const orderB = displaySettingMap.value.get(keyB)?.display_order
  const hasA = Number.isFinite(orderA)
  const hasB = Number.isFinite(orderB)
  if (hasA || hasB) {
    const normalizedA = hasA ? orderA : 99999
    const normalizedB = hasB ? orderB : 99999
    if (normalizedA !== normalizedB) return normalizedA - normalizedB
  }
  const codeCmp = String(a?.product_code || '').localeCompare(String(b?.product_code || ''))
  if (codeCmp !== 0) return codeCmp
  return String(a?.ship_to_code || '').localeCompare(String(b?.ship_to_code || ''))
}

const sortTripPlanningRows = (rows = []) => [...rows].sort(compareTripPlanningRows)

const hasRowCustomColor = (row) => {
  const setting = displaySettingMap.value.get(getTripRowKey(row))
  return Boolean(setting?.bg_color)
}

const getRowColorStyle = (row) => {
  const setting = displaySettingMap.value.get(getTripRowKey(row))
  if (!setting?.bg_color) return {}
  return {
    '--trip-row-bg': setting.bg_color,
    '--trip-row-text': setting.text_color || '#000000',
  }
}

const getPlusButtonStyle = (row) => {
  const setting = displaySettingMap.value.get(getTripRowKey(row))
  if (!setting?.plus_bg_color) return {}
  return {
    background: setting.plus_bg_color,
    color: setting.plus_text_color || '#000000',
    borderColor: setting.plus_bg_color,
  }
}

const isLockedTruck = (dateKey, truckId) => {
  const rows = lockedTripsByDate.value[dateKey] || []
  return rows.some((item) => Number(item.truck_id) === Number(truckId))
}

const isAllocationLocked = (allocation) => Boolean(allocation?.is_locked)
const isEntryFullyLocked = (entry) => Array.isArray(entry?.allocations) && entry.allocations.length > 0
  ? entry.allocations.every((allocation) => isAllocationLocked(allocation))
  : false
let lockedClickNoticeTimer = null

const showLockedClickNotice = (message) => {
  lockedClickNotice.value = message || '出発済のため、編集できません。'
  if (lockedClickNoticeTimer) clearTimeout(lockedClickNoticeTimer)
  lockedClickNoticeTimer = setTimeout(() => {
    lockedClickNotice.value = ''
    lockedClickNoticeTimer = null
  }, 1800)
}

const handleLockedAllocationClick = (allocation) => {
  if (!isAllocationLocked(allocation)) return
  showLockedClickNotice('出発済のため、編集できません。')
}

const sourceOrderLabel = (entry) => {
  if (!entry) return ''
  return entry.source_order_no || (entry.order_type === 'FORECAST' ? '内示' : '')
}

const assignedQty = (entry) => {
  if (!entry) return 0
  return entry.allocations.reduce((sum, al) => sum + parseIntegerQty(al.qty), 0)
}

const recalcEntry = (entry) => {
  if (!entry) return
  const assigned = assignedQty(entry)
  entry.unassigned_qty_preview = Number((assigned - parseNumber(entry.delivery_qty)).toFixed(3))
}

const handleAllocationChange = (entry) => {
  if (entry?.allocations?.length) {
    entry.allocations.forEach((al) => {
      if (parseIntegerQty(al.container_count) > 0) {
        syncAllocationFromContainerCount(entry, al)
      } else {
        syncAllocationFromQty(entry, al)
      }
    })
  }
  recalcEntry(entry)
  if (entry?.due_date) schedulePreview(entry.due_date)
}

const focusPlanTruck = async (dueDateKey, truckId) => {
  const normalizedTruckId = Number(truckId)
  if (!dueDateKey || !normalizedTruckId) return
  const truck = (trucksByDate.value[dueDateKey] || []).find((item) => Number(item.id) === normalizedTruckId)
  if (!truck) return
  const departureDateKey = getLoadDetailDateKey(dueDateKey, truck) || dueDateKey
  activePlanTruckId.value = normalizedTruckId
  planDate.value = departureDateKey
  await nextTick()
  const root = planSidebarBodyRef.value
  const target = root?.querySelector?.(`[data-plan-truck-id="${normalizedTruckId}"]`)
  target?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
}

const handleAllocationTruckSelect = async (entry, dueDateKey, truckId) => {
  handleAllocationChange(entry)
  await focusPlanTruck(dueDateKey, truckId)
}

const handleAllocationQtyInput = (entry) => {
  if (entry?.allocations?.length) {
    entry.allocations.forEach((al) => {
      syncAllocationFromQty(entry, al)
    })
  }
  recalcEntry(entry)
  if (entry?.due_date) schedulePreview(entry.due_date)
}

const handleContainerCountInput = (entry) => {
  if (entry?.allocations?.length) {
    entry.allocations.forEach((al) => {
      syncAllocationFromContainerCount(entry, al)
    })
  }
  recalcEntry(entry)
  if (entry?.due_date) schedulePreview(entry.due_date)
}

const addAllocation = (entry, defaultContainerId = null) => {
  if (!entry || isEntryFullyLocked(entry)) return
  entry.allocations.push(normalizeAllocation(null, defaultContainerId))
  if (entry.due_date) schedulePreview(entry.due_date)
}

const removeAllocation = (entry, idx) => {
  const target = entry?.allocations?.[idx]
  if (!entry || isAllocationLocked(target) || entry.allocations.length <= 1) return
  entry.allocations.splice(idx, 1)
  recalcEntry(entry)
  if (entry.due_date) schedulePreview(entry.due_date)
}

const entriesAt = (row, dateKey) => row.byDate?.[dateKey] || []
const slotEntryAt = (row, dateKey, slotIdx) => entriesAt(row, dateKey)[slotIdx] || null
const isEntryOverdue = (entry) => {
  if (!entry) return false
  if (parseNumber(entry.unassigned_qty_preview) >= 0) return false
  if (entry.deadline_date) return formatLocalDate(new Date()) > entry.deadline_date
  return Boolean(entry.overdue)
}
const hasOverdueDate = (dateKey) => mergedRows.value.some((row) => entriesAt(row, dateKey).some((entry) => isEntryOverdue(entry)))
const slotBlockHeight = (entry) => {
  const allocationCount = Math.max(1, Array.isArray(entry?.allocations) ? entry.allocations.length : 0)
  return Math.max(28, allocationCount * 24 + Math.max(0, allocationCount - 1) * 3 + 4)
}
const slotBlockStyle = (entry) => ({ minHeight: `${slotBlockHeight(entry)}px` })
const progressAt = (row, dateKey) => {
  const key = `${row.product_code}||${row.ship_to_code || ''}||${dateKey}`
  return progressByDate.value[key] ?? ''
}
const progressAdjustAt = (row, dateKey) => {
  const key = `${row.product_code}||${row.ship_to_code || ''}||${dateKey}`
  if (key in progressAdjustEdits.value) return progressAdjustEdits.value[key]
  const pKey = `${row.product_code}||${row.ship_to_code || ''}||${dateKey}||adjust`
  return progressByDate.value[pKey] ?? 0
}
const setProgressAdjust = (row, dateKey, value) => {
  const key = `${row.product_code}||${row.ship_to_code || ''}||${dateKey}`
  progressAdjustEdits.value[key] = parseSignedIntegerQty(value)
}

const truckAt = (dateKey, slotIdx) => {
  const trucks = displayTrucksForDate(dateKey)
  return trucks[slotIdx] || null
}

const containersForProduct = (productCode) => productContainersMap.value[productCode] || []

const truckDisplayName = (truck) => {
  if (!truck) return ''
  return (truck.alias_name || '').trim() || truck.name || ''
}

const loadDetailTruckLabel = (truck) => {
  const base = truckDisplayName(truck) || truck?.name || ''
  if (!base) return '便'
  return base.includes('便') ? base : `便 ${base}`
}

const truckNameAt = (dateKey, slotIdx) => {
  const truck = truckAt(dateKey, slotIdx)
  return truckDisplayName(truck) || `便${slotIdx + 1}`
}

const topOccupancySummaryDateKey = (dateKey, truck) => {
  if (!dateKey || !truck) return dateKey
  const offset = Math.max(0, Number(truck.arrival_day_offset || 0))
  if (offset <= 0) return dateKey
  return addBusinessDaysByCalendar(dateKey, -offset)
}

const truckOccupancyPercent = (dateKey, slotIdx) => {
  const truck = truckAt(dateKey, slotIdx)
  if (!truck) return 0
  const summaryDateKey = topOccupancySummaryDateKey(dateKey, truck)
  const previewSummary = (previewDepartureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id))
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (departureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id))
  return parseNumber(savedSummary?.occupancy_percent)
}

const truckOccupancyLabel = (dateKey, slotIdx) => `${truckOccupancyPercent(dateKey, slotIdx)}%`
const truckAssignedQtyById = (dateKey, truckId) => {
  const normalizedTruckId = Number(truckId)
  if (!dateKey || !normalizedTruckId) return 0
  let sum = 0
  mergedRows.value.forEach((row) => {
    entriesAt(row, dateKey).forEach((entry) => {
      ;(entry.allocations || []).forEach((allocation) => {
        if (Number(allocation.truck_id) === normalizedTruckId) {
          sum += parseIntegerQty(allocation.qty)
        }
      })
    })
  })
  return sum
}
const isTruck2 = (truck) => {
  const name = String(truckDisplayName(truck) || '').trim()
  return name === '2' || name === '2便' || name === '２' || name === '２便'
}
const showTruck60Diff = (dateKey, slotIdx) => isTruck2(truckAt(dateKey, slotIdx))
const truckDiffFrom60 = (dateKey, slotIdx) => {
  const truck = truckAt(dateKey, slotIdx)
  if (!truck) return 0
  return truckAssignedQtyById(dateKey, truck.id) - 60
}
const formatSignedNumber = (value) => {
  const num = parseNumber(value)
  if (num > 0) return `+${formatNumber(num)}`
  if (num < 0) return `-${formatNumber(Math.abs(num))}`
  return '0'
}
const truckOccupancyPercentById = (dateKey, truckId) => {
  const normalizedTruckId = Number(truckId)
  if (!dateKey || !normalizedTruckId) return 0
  const truck = (trucksByDate.value[dateKey] || []).find((item) => Number(item.id) === normalizedTruckId)
  const summaryDateKey = topOccupancySummaryDateKey(dateKey, truck)
  const previewSummary = (previewDepartureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === normalizedTruckId)
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (departureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === normalizedTruckId)
  return parseNumber(savedSummary?.occupancy_percent)
}
const truckOccupancyLabelById = (dateKey, truckId) => `${truckOccupancyPercentById(dateKey, truckId)}`
const truckDepartureOccupancyPercentById = (dateKey, truckId) => {
  const normalizedTruckId = Number(truckId)
  if (!dateKey || !normalizedTruckId) return 0
  const previewSummary = (previewDepartureSummaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === normalizedTruckId)
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (departureSummaryByDate.value[dateKey] || []).find((s) => Number(s.truck_id) === normalizedTruckId)
  return parseNumber(savedSummary?.occupancy_percent)
}
const truckDepartureOccupancyLabelById = (dateKey, truckId) => `${truckDepartureOccupancyPercentById(dateKey, truckId)}`
const pseudoTruckOccupancyPercent = (dateKey, type) => {
  const pseudoTruck = (trucksByDate.value[dateKey] || []).find((truck) => isPseudoTruckType(truck, type))
  if (!pseudoTruck) return 0
  const summaryDateKey = topOccupancySummaryDateKey(dateKey, pseudoTruck)
  const previewSummary = (previewDepartureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(pseudoTruck.id))
  if (previewSummary) return parseNumber(previewSummary.occupancy_percent)
  const savedSummary = (departureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(pseudoTruck.id))
  return parseNumber(savedSummary?.occupancy_percent)
}

const normalizeTruckAlias = (value) => String(value || '').trim().replace(/\s+/g, '').replace(/便$/u, '').toUpperCase()

const isTruckAlias = (truck, alias) => {
  const target = normalizeTruckAlias(alias)
  if (!target) return false
  const candidates = [
    truck?.alias_name,
    truck?.name,
    truckDisplayName(truck),
  ]
  return candidates.some((item) => normalizeTruckAlias(item) === target)
}

const autoAssignTruckCandidatesForDate = (dateKey) => {
  const trucks = trucksByDate.value[dateKey] || []
  return trucks.filter((truck) => Boolean(truck?.auto_assign_target) && !isPseudoTruck(truck))
}

const autoAssignTruckSummary = (dateKey, truck) => {
  if (!dateKey || !truck) return null
  const summaryDateKey = topOccupancySummaryDateKey(dateKey, truck)
  const previewSummary = (previewDepartureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id))
  if (previewSummary) return previewSummary
  return (departureSummaryByDate.value[summaryDateKey] || []).find((s) => Number(s.truck_id) === Number(truck.id)) || null
}

const getLoadDetailDateKey = (dateKey, truck) => {
  const offset = Math.max(0, Number(truck?.arrival_day_offset || 0))
  if (offset <= 0) return dateKey
  const departureDateKey = addBusinessDaysByCalendar(dateKey, -offset)
  return allDateKeys.value.includes(departureDateKey) ? departureDateKey : null
}

const loadBlocksByDate = computed(() => {
  const result = Object.fromEntries(dateKeys.value.map((dateKey) => [dateKey, []]))
  const bucketMap = new Map()
  const getBucket = (displayDateKey, truck) => {
    const truckId = Number(truck?.id || 0)
    if (!displayDateKey || !truckId) return null
    const key = `${displayDateKey}||${truckId}`
    if (!bucketMap.has(key)) {
      bucketMap.set(key, {
        dateKey: displayDateKey,
        occupancyDateKey: null,
        truckId,
        truckLabel: loadDetailTruckLabel(truck),
        products: new Map(),
      })
    }
    return bucketMap.get(key)
  }

  dateKeys.value.forEach((dateKey) => {
    const truckMap = new Map((trucksByDate.value[dateKey] || []).map((truck) => [Number(truck.id), truck]))
    mergedRows.value.forEach((row) => {
      const entries = entriesAt(row, dateKey)
      entries.forEach((entry) => {
        ;(entry.allocations || []).forEach((allocation) => {
          const truckId = Number(allocation.truck_id)
          const qty = parseIntegerQty(allocation.qty)
          if (!truckId || qty <= 0) return
          const truck = truckMap.get(truckId)
          if (!truck) return
          const displayDateKey = getLoadDetailDateKey(dateKey, truck)
          const bucket = getBucket(displayDateKey, truck)
          if (!bucket) return
          if (!bucket.occupancyDateKey) bucket.occupancyDateKey = displayDateKey
          const productKey = `${row.product_code}||${row.ship_to_code || ''}`
          const existing = bucket.products.get(productKey)
          if (existing) {
            existing.qty += qty
            return
          }
          bucket.products.set(productKey, {
            productCode: row.product_code,
            shipToCode: row.ship_to_code || '',
            shipToName: row.ship_to_name || '',
            qty,
          })
        })
      })
    })
  })

  bucketMap.forEach((bucket) => {
    const items = [...bucket.products.values()]
      .map((item) => ({
        truckId: bucket.truckId,
        truckLabel: bucket.truckLabel,
        productCode: item.productCode,
        shipToCode: item.shipToCode,
        shipToName: item.shipToName,
        qty: item.qty,
      }))
      .sort((a, b) => {
        const codeCompare = String(a.productCode).localeCompare(String(b.productCode))
        if (codeCompare !== 0) return codeCompare
        return String(a.shipToCode || '').localeCompare(String(b.shipToCode || ''))
      })
    const blocks = items.length ? [{
      truckId: bucket.truckId,
      truckLabel: bucket.truckLabel,
      products: items.map((item) => ({
        productCode: item.productCode,
        shipToCode: item.shipToCode,
        shipToName: item.shipToName,
        qty: item.qty,
      })),
    }] : []
    const normalizedBlocks = blocks.map((block) => {
      const lines = []
      for (let idx = 0; idx < block.products.length; idx += 2) {
        lines.push(block.products.slice(idx, idx + 2))
      }
      return {
        dateKey: bucket.dateKey,
        occupancyDateKey: bucket.occupancyDateKey || bucket.dateKey,
        truckId: block.truckId,
        truckLabel: block.truckLabel,
        lines: lines.length ? lines : [[]],
      }
    })
    result[bucket.dateKey].push(...normalizedBlocks)
  })
  Object.keys(result).forEach((dateKey) => {
    result[dateKey].sort((a, b) => a.truckId - b.truckId)
  })
  return result
})

const planColorPalette = [
  '#fca5a5', '#fbbf24', '#86efac', '#7dd3fc', '#c4b5fd',
  '#f9a8d4', '#fdba74', '#a7f3d0', '#93c5fd', '#fcd34d',
  '#d9f99d', '#f5d0fe', '#a5b4fc', '#fda4af', '#bef264',
]

const planColorForProduct = (productCode) => {
  const display = displaySettingItems.value.find((item) => item.product_code === productCode)
  if (display && display.bg_color && display.bg_color !== '#ffffff') return display.bg_color
  let hash = 0
  const str = String(productCode || '')
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) >>> 0
  }
  return planColorPalette[hash % planColorPalette.length]
}

const collectTruckPlanItems = (departureDateKey, truckId) => {
  const grouped = new Map()
  allDateKeys.value.forEach((dueDateKey) => {
    const truckMap = new Map((trucksByDate.value[dueDateKey] || []).map((t) => [Number(t.id), t]))
    const dueTruck = truckMap.get(Number(truckId))
    if (!dueTruck) return
    if (getLoadDetailDateKey(dueDateKey, dueTruck) !== departureDateKey) return
    mergedRows.value.forEach((row) => {
      entriesAt(row, dueDateKey).forEach((entry) => {
        ;(entry.allocations || []).forEach((allocation) => {
          if (Number(allocation.truck_id) !== Number(truckId)) return
          const qty = parseIntegerQty(allocation.qty)
          if (qty <= 0) return
          const container = findContainerOption(entry.product_code, allocation.container_id)
          const capacity = resolveAllocationCapacity(entry, allocation)
          const containerCount = Math.max(1, Math.ceil(qty / Math.max(1, capacity)))
          const key = `${entry.product_code}||${allocation.container_id || 'default'}`
          const existing = grouped.get(key)
          if (existing) {
            existing.qty += qty
            existing.containerCount += containerCount
            return
          }
          grouped.set(key, {
            key,
            productCode: entry.product_code,
            containerName: container?.container_name || '',
            qty,
            containerCount,
          })
        })
      })
    })
  })
  return [...grouped.values()].sort((a, b) => String(a.productCode).localeCompare(String(b.productCode)))
}

const buildTruckPlanColorMap = (items = []) => {
  const usedColors = new Set()
  const truckColorMap = new Map()
  items.forEach((item) => {
    const code = item.productCode
    const display = displaySettingItems.value.find((row) => row.product_code === code)
    let color = display && display.bg_color && display.bg_color !== '#ffffff' ? display.bg_color : ''
    if (!color || usedColors.has(color)) {
      const fallback = planColorForProduct(code)
      color = usedColors.has(fallback)
        ? (planColorPalette.find((c) => !usedColors.has(c)) || fallback)
        : fallback
    }
    usedColors.add(color)
    truckColorMap.set(code, color)
  })
  return truckColorMap
}

const planTruckModels = computed(() => {
  const dateKey = planDate.value
  const models = []

  // 実出発日ベースの積載データを取得
  const departureSummaries = previewDepartureSummaryByDate.value[dateKey] || departureSummaryByDate.value[dateKey] || []

  // 全納期日を走査し、getLoadDetailDateKeyで実出発日がdateKeyと一致する便を収集
  const allTruckMap = new Map()
  Object.values(trucksByDate.value).forEach((list) => {
    list.forEach((t) => allTruckMap.set(Number(t.id), t))
  })
  const truckIds = new Set(
    departureSummaries.filter((s) => Array.isArray(s.placed) && s.placed.length > 0).map((s) => Number(s.truck_id)),
  )
  const truckDueDateMap = new Map()
  allDateKeys.value.forEach((dk) => {
    const truckMap = new Map((trucksByDate.value[dk] || []).map((t) => [Number(t.id), t]))
    mergedRows.value.forEach((row) => {
      entriesAt(row, dk).forEach((entry) => {
        ;(entry.allocations || []).forEach((allocation) => {
          const truckId = Number(allocation.truck_id)
          if (!truckId || parseIntegerQty(allocation.qty) <= 0) return
          const truck = truckMap.get(truckId)
          if (!truck) return
          if (getLoadDetailDateKey(dk, truck) === dateKey) {
            truckIds.add(truckId)
            if (!truckDueDateMap.has(truckId)) truckDueDateMap.set(truckId, dk)
          }
        })
      })
    })
  })

  const planTrucks = [...truckIds]
    .map((id) => allTruckMap.get(id))
    .filter(Boolean)
    .sort((a, b) => Number(a.trip_number || 0) - Number(b.trip_number || 0))

  planTrucks.forEach((truck) => {
    const truckId = Number(truck.id)
    const bedW = parseNumber(truck.width)
    const bedD = parseNumber(truck.depth)
    const bedH = parseNumber(truck.height)
    const gap = parseNumber(truck.container_gap)

    // ---- 実出発日ベースの積載判定結果を優先 → 納期日(occupancyDateKey)ベース → 保存済みgrid ----
    const departureSummary = departureSummaries.find((s) => Number(s.truck_id) === truckId)
    const dueDateKey = truckDueDateMap.get(truckId) || dateKey
    const previewSummary = (previewSummaryByDate.value[dueDateKey] || []).find((s) => Number(s.truck_id) === truckId)
    const gridSummary = (summaryByDate.value[dueDateKey] || []).find((s) => Number(s.truck_id) === truckId)
    const backendSummary = (departureSummary && Array.isArray(departureSummary.placed))
      ? departureSummary
      : (previewSummary && Array.isArray(previewSummary.placed))
        ? previewSummary
        : ((gridSummary && Array.isArray(gridSummary.placed)) ? gridSummary : null)
    const aggregatedItems = collectTruckPlanItems(dateKey, truckId)
    if (aggregatedItems.length === 0) return
    const truckColorMap = buildTruckPlanColorMap(aggregatedItems)

    if (backendSummary) {
      const placed = backendSummary.placed.map((p) => {
        const pw = parseNumber(p.w)
        const pd = parseNumber(p.d)
        const layers = parseIntegerQty(p.layers) || 1
        return {
          x: parseNumber(p.x),
          y: parseNumber(p.y),
          w: pw,
          d: pd,
          layers,
          fontSize: Math.max(60, Math.min(pw, pd) * 0.4),
          rotated: Boolean(p.rotated),
          color: truckColorMap.get(p.product_code) || planColorForProduct(p.product_code),
          label: `${p.product_code}×${formatNumber(p.qty)}`,
        }
      })
      const items = aggregatedItems.map((item) => ({
        ...item,
        color: truckColorMap.get(item.productCode) || planColorForProduct(item.productCode),
      }))
      const viewW = bedD || 1
      const viewH = bedW || 1
      models.push({
        truckId,
        label: truckDisplayName(truck) || truck.name || '便',
        viewW,
        viewH,
        viewBox: `0 0 ${viewW} ${viewH}`,
        items,
        placed,
        remaining: (backendSummary.remaining || []).map((r) => ({ label: r.label, count: parseIntegerQty(r.count) })),
        overloaded: backendSummary.can_fit === false,
        notices: (backendSummary.contact_notices || []).filter((n) => n.notice_text),
        hasNotice: Boolean(backendSummary.has_contact_notice || (backendSummary.contact_notices || []).some((n) => n.notice_text)),
        dateKey,
      })
      return
    }

    // ---- フォールバック: フロント側のパッキング（実出発日ベースで全納期日を走査） ----
    const grouped = new Map()

    allDateKeys.value.forEach((dk) => {
      const truckMap = new Map((trucksByDate.value[dk] || []).map((t) => [Number(t.id), t]))
      const dkTruck = truckMap.get(truckId)
      if (!dkTruck) return
      const displayDk = getLoadDetailDateKey(dk, dkTruck)
      if (displayDk !== dateKey) return
      mergedRows.value.forEach((row) => {
        entriesAt(row, dk).forEach((entry) => {
          ;(entry.allocations || []).forEach((allocation) => {
            if (Number(allocation.truck_id) !== truckId) return
            const qty = parseIntegerQty(allocation.qty)
            if (qty <= 0) return
            const container = findContainerOption(entry.product_code, allocation.container_id)
            const capacity = resolveAllocationCapacity(entry, allocation)
            const containerCount = Math.max(1, Math.ceil(qty / Math.max(1, capacity)))
            const containerKey = allocation.container_id || 'default'
            const key = `${entry.product_code}||${containerKey}`
            const existing = grouped.get(key)
            if (existing) {
              existing.qty += qty
              existing.count += containerCount
              return
            }
            grouped.set(key, {
              key,
              productCode: entry.product_code,
              containerName: container?.container_name || '',
              cw: parseNumber(container?.width),
              cd: parseNumber(container?.depth),
              ch: parseNumber(container?.height),
              stackable: container?.stackable == null ? true : Boolean(container.stackable),
              maxStack: parseIntegerQty(container?.max_stack),
              orientation: container?.orientation || 'free',
              capacity: Math.max(1, capacity),
              count: containerCount,
              qty,
              color: truckColorMap.get(entry.product_code) || planColorForProduct(entry.product_code),
            })
          })
        })
      })
    })

    const items = [...grouped.values()].sort((a, b) => (b.cw * b.cd) - (a.cw * a.cd))

    // 段数と実効床面積（バックエンド計算式と同一）
    items.forEach((item) => {
      let layers = 1
      if (item.cw > 0 && item.cd > 0 && item.ch > 0 && item.stackable) {
        const truckLayers = Math.floor(bedH / item.ch)
        const maxStack = item.maxStack > 0 ? item.maxStack : truckLayers
        layers = Math.max(1, Math.min(truckLayers || 1, maxStack || 1))
      }
      item.layers = layers
      item.effectiveFloor = (item.cw * item.cd) / layers
    })

    // 同じ容器なら製品が違っても合算して段積み効率化
    const containerMerged = new Map()
    items.forEach((item) => {
      if (item.cw <= 0 || item.cd <= 0) return
      const mergeKey = item.key.split('||')[1] || 'default'
      const existing = containerMerged.get(mergeKey)
      if (existing) {
        existing.count += item.count
      } else {
        containerMerged.set(mergeKey, { ...item })
      }
    })
    const mergedItems = [...containerMerged.values()]

    // パッカー: スロットを荷台内に敷き詰める（縁gap分縮小したエリアで判定）
    const packBedD = bedD - gap
    const packBedW = bedW - gap
    const packSlots = (slotList) => {
      const result = []
      let rowX = 0
      let rowY = 0
      let rowH = 0
      let allFit = true
      let maxX = 0
      let maxY = 0
      slotList.forEach((slot) => {
        const len = slot.len
        const wid = slot.wid
        if (rowX + len > packBedD) {
          rowX = 0
          rowY += rowH
          rowH = 0
        }
        if (rowY + wid > packBedW) {
          allFit = false
        }
        result.push({
          x: rowX,
          y: rowY,
          w: len,
          d: wid,
          layers: slot.layers,
          fontSize: Math.max(60, Math.min(len, wid) * 0.4),
          rotated: slot.rotated,
          color: slot.color,
          label: slot.label,
        })
        rowX += len
        rowH = Math.max(rowH, wid)
        maxX = Math.max(maxX, rowX)
        maxY = Math.max(maxY, rowY + wid)
      })
      return { placed: result, allFit, maxX, maxY }
    }

    // 各品目のフロアスロット（同じ容器は合算済み。段積みは1フットプリント）
    const allSlots = []
    const typeSlots = []
    mergedItems.forEach((item) => {
      const layers = Math.max(1, item.layers || 1)
      const totalCount = item.count
      const floorSlots = Math.ceil(totalCount / layers)
      const capNormal = Math.floor(bedW / item.cw) * Math.floor(bedD / item.cd)
      const capRotated = Math.floor(bedW / item.cd) * Math.floor(bedD / item.cw)
      const orientation = String(item.orientation || 'free')
      let rotated
      if (orientation === 'long') {
        rotated = item.cw > item.cd
      } else if (orientation === 'short') {
        rotated = item.cd > item.cw
      } else {
        rotated = capRotated > capNormal
      }
      const len = rotated ? item.cw : item.cd
      const wid = rotated ? item.cd : item.cw

      // フットプリントごとの段数を計算（最後のスロットは残り容器数分）
      // 容器間隔: パッキング用にgap加算、表示時は実寸
      const packLen = len + gap
      const packWid = wid + gap
      let remainingCount = totalCount
      const typeSlot = { item, len: packLen, wid: packWid, rotated }
      typeSlots.push(typeSlot)
      for (let i = 0; i < floorSlots; i++) {
        const slotLayers = Math.min(layers, remainingCount)
        remainingCount -= slotLayers
        allSlots.push({
          len: packLen,
          wid: packWid,
          rotated,
          layers: slotLayers,
          color: item.color,
          label: `${item.containerName || item.productCode}`,
        })
      }
    })

    const mainPack = packSlots(allSlots)
    const placed = mainPack.placed.map((p) => ({ ...p, x: p.x + gap, y: p.y + gap, w: p.w - gap, d: p.d - gap }))
    // 実際に荷台へ収まっているか（積載可否の判定。収まらなければ積載超過）
    const overloaded = !mainPack.allFit

    // 残りスペース: 現在の積載が荷台に収まる場合のみ、各品目の容器を実際にあと何箱
    // 置けるかをパッキングで幾何学的に判定する（面積ベースではなく、見た目と一致させる）
    const remainingMap = new Map()
    if (bedW > 0 && bedD > 0 && mainPack.allFit) {
      typeSlots.forEach((typeSlot) => {
        const { item } = typeSlot
        const extraSlot = {
          len: typeSlot.len,
          wid: typeSlot.wid,
          rotated: typeSlot.rotated,
          layers: item.layers || 1,
          color: item.color,
          label: item.containerName || item.productCode,
        }
        let extra = 0
        let canAdd = true
        while (canAdd && extra < 500) {
          const testSlots = allSlots.slice()
          for (let i = 0; i <= extra; i++) {
            testSlots.push(extraSlot)
          }
          if (packSlots(testSlots).allFit) {
            extra++
          } else {
            canAdd = false
          }
        }
        if (extra > 0) {
          const label = item.containerName || item.productCode
          remainingMap.set(label, Math.max(remainingMap.get(label) || 0, extra))
        }
      })
    }
    const remaining = [...remainingMap.entries()].map(([label, count]) => ({ label, count }))

    const bedW2 = bedW || 1
    const bedD2 = bedD || 1
    const viewW = bedD2 // 表示上の幅（長手=奥行 を横に）
    const viewH = bedW2 // 表示上の高さ（幅 を縦に）
    models.push({
      truckId,
      label: truckDisplayName(truck) || truck.name || '便',
      viewW,
      viewH,
      viewBox: `0 0 ${viewW} ${viewH}`,
      items: aggregatedItems.map((item) => ({
        ...item,
        color: truckColorMap.get(item.productCode) || planColorForProduct(item.productCode),
      })),
      placed,
      remaining,
      overloaded,
      notices: [],
      hasNotice: false,
      dateKey,
    })
  })
  return models
})

const patchTripNoticeSummaries = (dateKey, truckId, notices) => {
  const patchMap = (source = {}) => {
    const list = Array.isArray(source[dateKey]) ? source[dateKey] : []
    return {
      ...source,
      [dateKey]: list.map((item) => (
        Number(item?.truck_id) === Number(truckId)
          ? {
              ...item,
              contact_notices: notices,
              has_contact_notice: notices.length > 0,
            }
          : item
      )),
    }
  }
  departureSummaryByDate.value = patchMap(departureSummaryByDate.value)
  previewDepartureSummaryByDate.value = patchMap(previewDepartureSummaryByDate.value)
}

const _applyNoticesResponse = (notices) => {
  const drafts = { NORMAL: '', URGENT: '', VENDOR: '' }
  for (const n of notices || []) {
    const t = String(n.notice_type || 'NORMAL').trim().toUpperCase()
    if (t in drafts) drafts[t] = String(n.notice_text || '').trim()
  }
  tripNoticeDrafts.value = drafts
}

const hasDateHeaderNote = (dateKey) => Boolean((dateHeaderNoticesByDate.value[dateKey] || []).length)
const dateHeaderNoteButtonTitle = (dateKey) => hasDateHeaderNote(dateKey) ? '日付メモあり' : '日付メモを入力'
const patchDateHeaderNotice = (dateKey, notices) => {
  dateHeaderNoticesByDate.value = {
    ...dateHeaderNoticesByDate.value,
    [dateKey]: Array.isArray(notices) ? notices.filter((n) => String(n?.notice_text || '').trim()) : [],
  }
}

const openTripNoticeDialog = async (truck) => {
  activeTripNotice.value = {
    truckId: Number(truck?.truckId || 0),
    label: truck?.label || '便',
    dateKey: truck?.dateKey || planDate.value,
    noticeScope: 'truck',
  }
  _applyNoticesResponse(truck?.notices || [])
  tripNoticeTypeDraft.value = 'NORMAL'
  showTripNoticeDialog.value = true
  if (!activeTripNotice.value.truckId || !activeTripNotice.value.dateKey) return
  try {
    const res = await api.kubotaSakaiTripAssignments.getTripNotices(
      activeTripNotice.value.dateKey,
      activeTripNotice.value.truckId,
    )
    _applyNoticesResponse(res.data?.notices || [])
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '連絡メモの取得に失敗しました。'
    alert(detail)
  }
}

const openDateHeaderNoticeDialog = async (dateKey) => {
  activeTripNotice.value = {
    truckId: 0,
    tripRef: DATE_HEADER_TRIP_REF,
    label: '日付メモ',
    dateKey,
    noticeScope: 'date_header',
  }
  _applyNoticesResponse(dateHeaderNoticesByDate.value[dateKey] || [])
  tripNoticeTypeDraft.value = 'NORMAL'
  showTripNoticeDialog.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.getTripNotices(dateKey, null, DATE_HEADER_TRIP_REF)
    const notices = res.data?.notices || []
    _applyNoticesResponse(notices)
    patchDateHeaderNotice(dateKey, notices)
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '日付メモの取得に失敗しました。'
    alert(detail)
  }
}

const closeTripNoticeDialog = () => {
  if (savingTripNotice.value) return
  showTripNoticeDialog.value = false
  activeTripNotice.value = null
  tripNoticeDrafts.value = { NORMAL: '', URGENT: '', VENDOR: '' }
  tripNoticeTypeDraft.value = 'NORMAL'
}

const saveTripNotice = async () => {
  const truck = activeTripNotice.value
  if (!truck?.dateKey || (!truck?.truckId && !truck?.tripRef)) return
  savingTripNotice.value = true
  try {
    const currentType = tripNoticeTypeDraft.value
    const currentText = tripNoticeDrafts.value[currentType] || ''
    const res = await api.kubotaSakaiTripAssignments.saveTripNotice(
      truck.dateKey,
      truck.truckId || null,
      currentText,
      currentType,
      truck.tripRef || '',
    )
    const notices = res.data?.notices || []
    _applyNoticesResponse(notices)
    if (truck.noticeScope === 'date_header') {
      patchDateHeaderNotice(truck.dateKey, notices)
    } else {
      patchTripNoticeSummaries(truck.dateKey, truck.truckId, notices)
    }
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || `${truck.noticeScope === 'date_header' ? '日付' : '連絡'}メモの保存に失敗しました。`
    alert(detail)
  } finally {
    savingTripNotice.value = false
  }
}

const clearTripNotice = async () => {
  tripNoticeDrafts.value[tripNoticeTypeDraft.value] = ''
  await saveTripNotice()
}

// 平面図の日付ナビゲーション（納期日＋実出発日を含む全日付で前後移動）
const planAvailableDates = computed(() => {
  const dateSet = new Set(allDateKeys.value)
  Object.keys(departureSummaryByDate.value).forEach((k) => dateSet.add(k))
  Object.keys(previewDepartureSummaryByDate.value).forEach((k) => dateSet.add(k))
  return [...dateSet].sort()
})
const planPrevDate = computed(() => {
  const keys = planAvailableDates.value
  const idx = keys.indexOf(planDate.value)
  return idx > 0 ? keys[idx - 1] : ''
})
const planNextDate = computed(() => {
  const keys = planAvailableDates.value
  const idx = keys.indexOf(planDate.value)
  return idx >= 0 && idx < keys.length - 1 ? keys[idx + 1] : ''
})
const planDateLoaded = computed(() => planAvailableDates.value.includes(planDate.value))

const buildPayloadRowsForDate = (dateKey) => {
  return mergedRows.value
    .flatMap((row) => entriesAt(row, dateKey))
    .map((entry) => ({
      due_adjustment_id: entry.due_adjustment_id,
      default_container_id: entry.used_container_id || null,
      allocations: entry.allocations
        .map((item) => ({
          id: item.id,
          truck_id: item.truck_id,
          container_id: item.container_id || null,
          qty: parseIntegerQty(item.qty),
        }))
        .filter((item) => item.truck_id && item.qty > 0),
    }))
}

const buildPreviewRowsByDate = () => Object.fromEntries(
  allDateKeys.value.map((dateKey) => [dateKey, buildPayloadRowsForDate(dateKey)]),
)

const previewLoadForDate = async (dateKey) => {
  const payloadRows = buildPayloadRowsForDate(dateKey)
  const previewRowsByDate = buildPreviewRowsByDate()
  const requestId = ++latestDeparturePreviewRequestId
  try {
    const res = await api.kubotaSakaiTripAssignments.previewLoad(dateKey, payloadRows, previewRowsByDate)
    const summaries = Array.isArray(res.data?.truck_summaries) ? res.data.truck_summaries : []
    const departureSummariesByDate = res.data?.departure_truck_summaries_by_date || {}
    previewSummaryByDate.value = {
      ...previewSummaryByDate.value,
      [dateKey]: summaries,
    }
    if (requestId !== latestDeparturePreviewRequestId) return
    previewDepartureSummaryByDate.value = {
      ...previewDepartureSummaryByDate.value,
      ...departureSummariesByDate,
    }
  } catch (error) {
    console.warn('便占有率プレビュー取得失敗', error)
  }
}

const schedulePreview = (dateKey) => {
  if (!dateKey) return
  const prev = previewTimers.get(dateKey)
  if (prev) clearTimeout(prev)
  const timer = setTimeout(() => {
    previewLoadForDate(dateKey)
    previewTimers.delete(dateKey)
  }, 250)
  previewTimers.set(dateKey, timer)
}

const showCursorBubble = (text, event) => {
  cursorBubbleText.value = String(text || '')
  const rect = event?.target?.getBoundingClientRect?.()
  if (!rect) return
  const left = Math.round(rect.left + rect.width / 2)
  const top = Math.round(rect.top - 8)
  cursorProductBubbleStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    transform: 'translate(-50%, -100%)',
  }
}

const showProductBubble = (row, event) => {
  showCursorBubble(row?.product_code || '', event)
}

const showCoordinationNoteBubble = (entry, event) => {
  showCursorBubble(entry?.coordination_note || '', event)
}

const hideCursorBubble = () => {
  cursorBubbleText.value = ''
  cursorProductBubbleStyle.value = {}
}

const handleQtyInputBlur = () => {
  window.setTimeout(() => {
    const root = tableWrapRef.value
    const active = document.activeElement
    if (!root || !active || !root.contains(active)) {
      hideCursorBubble()
    }
  }, 0)
}

const handleQtyInputMouseLeave = (event) => {
  if (document.activeElement !== event?.target) {
    hideCursorBubble()
  }
}

const mapSeries = async (items, mapper) => {
  const results = []
  for (let idx = 0; idx < items.length; idx += 1) {
    results.push(await mapper(items[idx], idx))
  }
  return results
}

const refreshAllPreview = async () => {
  await mapSeries(dateKeys.value, async (dateKey) => {
    await previewLoadForDate(dateKey)
  })
}

const loadDisplaySettings = async () => {
  try {
    const res = await api.kubotaSakaiTripAssignments.getDisplaySettings()
    const rows = Array.isArray(res.data?.rows) ? res.data.rows : []
    const map = new Map()
    rows.forEach((row, idx) => {
      map.set(`${row.product_code || ''}||${row.ship_to_code || ''}`, {
        display_order: Number(row.display_order ?? idx),
        bg_color: row.bg_color || '',
        text_color: row.text_color || '',
        plus_bg_color: row.plus_bg_color || '',
        plus_text_color: row.plus_text_color || '',
      })
    })
    displaySettingMap.value = map
  } catch (error) {
    console.warn('便計画表示設定の取得失敗', error)
    displaySettingMap.value = new Map()
  }
}

const openDisplaySettingDialog = async () => {
  await loadDisplaySettings()
  displaySettingItems.value = sortTripPlanningRows(mergedRows.value).map((row) => {
    const setting = displaySettingMap.value.get(getTripRowKey(row))
    return {
      key: getTripRowKey(row),
      product_code: row.product_code,
      product_name: productNameMap.value.get(row.product_code) || '',
      ship_to_code: row.ship_to_code || '',
      bg_color: setting?.bg_color || '#ffffff',
      text_color: setting?.text_color || '#000000',
      plus_bg_color: setting?.plus_bg_color || '#ffffff',
      plus_text_color: setting?.plus_text_color || '#000000',
    }
  })
  displaySettingActiveKey.value = ''
  showDisplaySettingDialog.value = true
}

const moveDisplaySettingItem = (idx, direction) => {
  const nextIdx = idx + direction
  if (nextIdx < 0 || nextIdx >= displaySettingItems.value.length) return
  const arr = [...displaySettingItems.value]
  displaySettingActiveKey.value = arr[idx].key
  ;[arr[idx], arr[nextIdx]] = [arr[nextIdx], arr[idx]]
  displaySettingItems.value = arr
}

const saveDisplaySettings = async () => {
  savingDisplaySettings.value = true
  try {
    const rows = displaySettingItems.value.map((item, idx) => ({
      product_code: item.product_code,
      ship_to_code: item.ship_to_code || '',
      display_order: idx,
      bg_color: item.bg_color && item.bg_color !== '#ffffff' ? item.bg_color : '',
      text_color: item.text_color && item.text_color !== '#000000' ? item.text_color : '',
      plus_bg_color: item.plus_bg_color && item.plus_bg_color !== '#ffffff' ? item.plus_bg_color : '',
      plus_text_color: item.plus_text_color && item.plus_text_color !== '#000000' ? item.plus_text_color : '',
    }))
    await api.kubotaSakaiTripAssignments.saveDisplaySettings(rows)
    await loadDisplaySettings()
    mergedRows.value = sortTripPlanningRows(mergedRows.value)
    if (pseudoProductRows.value.length) {
      pseudoProductRows.value = sortTripPlanningRows(pseudoProductRows.value)
    }
    showDisplaySettingDialog.value = false
  } catch (error) {
    alert('表示順設定の保存に失敗しました。')
  } finally {
    savingDisplaySettings.value = false
  }
}

const loadGrid = async () => {
  loading.value = true
  try {
    await loadDisplaySettings()
    const responses = await mapSeries(
      allDateKeys.value,
      async (dateKey) => api.kubotaSakaiTripAssignments.grid({
        target_date: dateKey,
        keyword: keyword.value,
      }),
    )
    const nextTrucksByDate = {}
    const nextLockedTripsByDate = {}
    const nextSummaryByDate = {}
    const nextDepartureSummaryByDate = {}
    const nextHolidayByDate = {}
    const nextProgressByDate = {}
    const nextProductContainers = {}
    const nextDateHeaderNoticesByDate = {}
    const map = new Map()
    let maxDeadline = 3

    responses.forEach((res, idx) => {
      const dateKey = allDateKeys.value[idx]
      const trucks = Array.isArray(res.data?.trucks) ? res.data.trucks : []
      const summaries = Array.isArray(res.data?.truck_summaries) ? res.data.truck_summaries : []
      const departureSummaries = Array.isArray(res.data?.departure_truck_summaries) ? res.data.departure_truck_summaries : []
      const lockedTrips = Array.isArray(res.data?.locked_trips) ? res.data.locked_trips : []
      const payloadRows = Array.isArray(res.data?.rows) ? res.data.rows : []
      nextTrucksByDate[dateKey] = trucks
      nextLockedTripsByDate[dateKey] = lockedTrips
      nextSummaryByDate[dateKey] = summaries
      nextDepartureSummaryByDate[dateKey] = departureSummaries
      nextHolidayByDate[dateKey] = Boolean(res.data?.is_holiday)
      nextDateHeaderNoticesByDate[dateKey] = Array.isArray(res.data?.date_header_notices) ? res.data.date_header_notices : []
      maxDeadline = Math.max(maxDeadline, Number(res.data?.assignment_deadline_days || 3))
      if (res.data?.last_adjusted_at) lastAdjustedAt.value = res.data.last_adjusted_at
      const pcMap = res.data?.product_containers
      if (pcMap && typeof pcMap === 'object') {
        Object.entries(pcMap).forEach(([code, containers]) => {
          if (!nextProductContainers[code]) nextProductContainers[code] = containers
        })
      }

      payloadRows.forEach((raw) => {
        if (raw.product_code && raw.product_name) {
          productNameMap.value.set(raw.product_code, raw.product_name)
        }
        const progressKey = `${raw.product_code}||${raw.ship_to_code || ''}||${dateKey}`
        if (!(progressKey in nextProgressByDate)) {
          nextProgressByDate[progressKey] = raw.progress_qty ?? 0
          nextProgressByDate[`${progressKey}||adjust`] = raw.progress_adjust_qty ?? 0
        }
        const key = `${raw.product_code}||${raw.ship_to_code || ''}`
        if (!map.has(key)) {
          map.set(key, {
            rowKey: key,
            product_code: raw.product_code,
            ship_to_code: raw.ship_to_code || '',
            ship_to_name: raw.ship_to_name || '',
            used_container_id: raw.used_container_id || null,
            byDate: {},
            maxSlots: 1,
          })
        }
        const defaultContainerId = raw.used_container_id || null
        const allocations = Array.isArray(raw.allocations) && raw.allocations.length
          ? raw.allocations.map((a) => normalizeAllocation(a, defaultContainerId))
          : [normalizeAllocation(null, defaultContainerId)]
        const entry = {
          due_adjustment_id: raw.due_adjustment_id,
          product_code: raw.product_code,
          used_container_id: raw.used_container_id || null,
          source_order_no: raw.source_order_no || '',
          order_type: raw.order_type || '',
          coordination_note: String(raw.coordination_note || '').trim(),
          delivery_qty: parseNumber(raw.delivery_qty),
          overdue: Boolean(raw.overdue),
          deadline_date: raw.deadline_date || '',
          default_capacity: raw.capacity,
          allocations,
          unassigned_qty_preview: parseNumber(raw.unassigned_qty),
          due_date: dateKey,
          is_locked: Boolean(raw.is_locked),
          lock_reason: raw.lock_reason || '',
        }
        entry.allocations.forEach((al) => {
          syncAllocationFromQty(entry, al)
        })
        recalcEntry(entry)
        if (!map.get(key).byDate[dateKey]) {
          map.get(key).byDate[dateKey] = []
        }
        map.get(key).byDate[dateKey].push(entry)
      })
    })

    const rows = [...map.values()]
    rows.forEach((row) => {
      let maxSlots = 1
      allDateKeys.value.forEach((dateKey) => {
        row.byDate[dateKey] = sortEntries(row.byDate[dateKey] || [])
        maxSlots = Math.max(maxSlots, row.byDate[dateKey].length || 0)
      })
      row.maxSlots = maxSlots || 1
    })

    trucksByDate.value = nextTrucksByDate
    lockedTripsByDate.value = nextLockedTripsByDate
    summaryByDate.value = nextSummaryByDate
    departureSummaryByDate.value = nextDepartureSummaryByDate
    productContainersMap.value = nextProductContainers
    holidayByDate.value = nextHolidayByDate
    dateHeaderNoticesByDate.value = nextDateHeaderNoticesByDate
    progressByDate.value = nextProgressByDate
    progressAdjustEdits.value = {}
    previewSummaryByDate.value = {}
    previewDepartureSummaryByDate.value = {}
    assignmentDeadlineDays.value = maxDeadline
    mergedRows.value = sortTripPlanningRows(rows)
    nextTick(setStickyTopValues)
  } catch (error) {
    console.error('loadGrid error:', error)
    const message = error?.response?.data?.detail || 'データ取得に失敗しました。'
    alert(message)
  } finally {
    loading.value = false
  }
}

const importOrders = async () => {
  if (importing.value || loading.value) return
  importing.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.importOrders({
      start_date: targetDate.value,
      horizon_days: horizonDays.value,
    })
    const d = res.data || {}
    alert(`取込完了: 対象${d.total_rows || 0}件を読取りました。`)
    await loadGrid()
  } catch (error) {
    const message = error?.response?.data?.detail || '取込に失敗しました。'
    alert(message)
  } finally {
    importing.value = false
  }
}

const csvEscape = (value) => {
  const text = value == null ? '' : String(value)
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`
  }
  return text
}

const exportLoadDetailCsv = async () => {
  exportingCsv.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.loadDetail(targetDate.value)
    const rows = Array.isArray(res.data?.rows) ? res.data.rows : []
    if (!rows.length) {
      alert('対象日の便割付データがありません。')
      return
    }

    const header = ['便', '便面積', '製品', '数量', '容器名', '容器', '使用容器数', '使用容器面積', '占有']
    const lines = [header.join(',')]
    rows.forEach((row) => {
      const truckLabel = row.truck_alias_name
        ? `${row.truck_alias_name} (${row.truck_name})`
        : row.truck_name
      const record = [
        truckLabel,
        row.truck_area,
        row.product_code,
        row.qty,
        row.container_name || '-',
        row.container_size || '-',
        row.container_count,
        row.used_container_area,
        `${row.occupancy_percent}%`,
      ]
      lines.push(record.map(csvEscape).join(','))
    })

    const csv = `\uFEFF${lines.join('\r\n')}`
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `便占有明細_${targetDate.value}.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    const message = error?.response?.data?.detail || 'CSV出力に失敗しました。'
    alert(message)
  } finally {
    exportingCsv.value = false
  }
}

const openPickupPdfDialog = () => {
  showPickupPdfDialog.value = true
  pickupPdfStartDate.value = targetDate.value
  pickupPdfEndDate.value = addDays(targetDate.value, Math.max(0, Number(horizonDays.value || 1) - 1))
}

const closePickupPdfDialog = () => {
  if (exportingPickupPdf.value) return
  showPickupPdfDialog.value = false
}

const exportPickupDetailPdf = async () => {
  const startDate = pickupPdfStartDate.value
  const endDate = pickupPdfEndDate.value
  if (!startDate || !endDate) {
    alert('開始日と終了日を指定してください。')
    return
  }
  if (startDate > endDate) {
    alert('開始日は終了日以前を指定してください。')
    return
  }
  exportingPickupPdf.value = true
  try {
    const res = await api.kubotaSakaiTripAssignments.pickupDetailPdf(startDate, endDate)
    const blob = new Blob([res.data], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `クボタ堺_集荷明細表_${startDate}_${endDate}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    showPickupPdfDialog.value = false
  } catch (error) {
    const data = error?.response?.data
    if (data instanceof Blob) {
      alert('PDF出力に失敗しました。')
      return
    }
    const message = data?.detail || data?.error || 'PDF出力に失敗しました。'
    alert(message)
  } finally {
    exportingPickupPdf.value = false
  }
}

const closeSaveConfirmDialog = () => {
  if (saving.value) return
  showSaveConfirmDialog.value = false
}

const performSave = async () => {
  saving.value = true
  try {
    for (const dateKey of allDateKeys.value) {
      const payloadRows = mergedRows.value
        .flatMap((row) => entriesAt(row, dateKey))
        .map((entry) => ({
          due_adjustment_id: entry.due_adjustment_id,
          allocations: entry.allocations
            .map((item) => ({
              truck_id: item.truck_id,
              container_id: item.container_id || null,
              qty: parseIntegerQty(item.qty),
            }))
            .filter((item) => item.truck_id && item.qty > 0),
        }))
      await api.kubotaSakaiTripAssignments.bulkSave(dateKey, payloadRows)
    }
    await loadGrid()
    alert('保存しました。')
  } catch (error) {
    const detail = error?.response?.data?.detail || '保存に失敗しました。'
    const errors = error?.response?.data?.errors
    if (Array.isArray(errors) && errors.length > 0) {
      const lines = errors.map((item) => {
        if (item.truck_name) return `${item.truck_name}: ${(item.errors || []).join(', ')}`
        if (item.due_adjustment_id) return `${item.detail || '入力エラー'}`
        return JSON.stringify(item)
      })
      alert([detail, ...lines].join('\n'))
    } else {
      alert(detail)
    }
  } finally {
    saving.value = false
  }
}

const proceedSave = async () => {
  showSaveConfirmDialog.value = false
  await performSave()
}

const save = async () => {
  const validation = validateBeforeSave()
  if (!validation.ok) {
    saveValidationState.value = validation
    showSaveConfirmDialog.value = true
    return
  }
  await performSave()
}

const saveProgressAdjust = async () => {
  savingProgressAdjust.value = true
  try {
    const rows = []
    for (const [key, adjustQty] of Object.entries(progressAdjustEdits.value)) {
      const [productCode, shipToCode, planDate] = key.split('||')
      rows.push({
        plan_date: planDate,
        product_code: productCode,
        ship_to_code: shipToCode || '',
        adjust_qty: adjustQty,
      })
    }
    if (rows.length) {
      await api.kubotaSakaiTripAssignments.saveDeliveryProgressAdjust(rows)
    }
    await loadGrid()
    showProgressAdjust.value = false
    alert('進捗調整を保存しました。')
  } catch (error) {
    alert(error?.response?.data?.detail || '進捗調整の保存に失敗しました。')
  } finally {
    savingProgressAdjust.value = false
  }
}

const validateBeforeSave = () => {
  let missingTruckCount = 0
  let unassignedQtyCount = 0
  const overAssigned = []
  const overloaded = []
  const overloadedSet = new Set()
  const missingTruckDetails = []
  const unassignedQtyDetails = []

  for (const dateKey of allDateKeys.value) {
    const previewList = previewDepartureSummaryByDate.value[dateKey] || departureSummaryByDate.value[dateKey] || []
    for (const row of mergedRows.value) {
      for (const entry of entriesAt(row, dateKey)) {
        const deliveryQty = parseIntegerQty(entry?.delivery_qty)
        if (deliveryQty <= 0) continue
        const validAllocations = (entry.allocations || []).filter(
          (item) => item?.truck_id && parseIntegerQty(item?.qty) > 0,
        )
        const unassigned = parseNumber(entry?.unassigned_qty_preview)
        if (!validAllocations.length) {
          missingTruckCount += 1
          missingTruckDetails.push(`${dateKey} ${row.product_code} ${formatNumber(deliveryQty)}`)
        } else if (unassigned < 0) {
          unassignedQtyCount += 1
          unassignedQtyDetails.push(`${dateKey} ${row.product_code} ${formatNumber(Math.abs(unassigned))}`)
        }
        if (unassigned > 0) overAssigned.push(`${dateKey} ${row.product_code} (需要${deliveryQty} 割付${deliveryQty + unassigned})`)
      }
    }

    for (const item of previewList) {
      const occ = parseNumber(item?.occupancy_percent)
      if (occ > 100) {
        const key = `${dateKey}-${item?.truck_id}`
        if (overloadedSet.has(key)) continue
        overloadedSet.add(key)
        overloaded.push(`${dateKey} ${item?.truck_name || '便'} ${formatNumber(occ)}%`)
      }
    }
  }

  if (!missingTruckCount && !unassignedQtyCount && !overAssigned.length && !overloaded.length) {
    return { ok: true }
  }

  return {
    ok: false,
    missingTruckCount,
    missingTruckDetails,
    unassignedQtyCount,
    unassignedQtyDetails,
    overAssigned,
    overloaded,
  }
}

// ---- 擬似便対象製品 ----

const togglePseudoProductPanel = async () => {
  showPseudoProductPanel.value = !showPseudoProductPanel.value
  if (showPseudoProductPanel.value) {
    await loadPseudoProducts()
  }
}

const loadPseudoProducts = async () => {
  try {
    const res = await api.kubotaSakaiTripAssignments.getPseudoTruckProducts()
    pseudoTrucks.value = res.data?.pseudo_trucks || []
    const mappings = res.data?.mappings || []
    const mappingMap = new Map()
    mappings.forEach((m) => {
      const key = `${m.product_code}||${m.ship_to_code || ''}`
      mappingMap.set(key, new Set((m.trucks || []).map((t) => Number(t.truck_id))))
    })
    const gridKeys = new Set()
    mergedRows.value.forEach((row) => {
      gridKeys.add(`${row.product_code}||${row.ship_to_code || ''}`)
    })
    pseudoProductRows.value = sortTripPlanningRows([...gridKeys].map((key) => {
      const [productCode, shipToCode] = key.split('||', 2)
      return {
        key,
        product_code: productCode,
        ship_to_code: shipToCode,
        truckIds: mappingMap.get(key) || new Set(),
      }
    }))
  } catch (error) {
    alert('AM/PMグループ対象製品の取得に失敗しました。')
  }
}

const togglePseudoTruck = (row, truckId) => {
  if (row.truckIds.has(truckId)) {
    row.truckIds.delete(truckId)
  } else {
    row.truckIds.add(truckId)
  }
}

const savePseudoProducts = async () => {
  savingPseudo.value = true
  try {
    const rows = pseudoProductRows.value.map((row) => ({
      product_code: row.product_code,
      ship_to_code: row.ship_to_code || '',
      truck_ids: [...row.truckIds],
    }))
    await api.kubotaSakaiTripAssignments.savePseudoTruckProducts(rows)
    alert('AM/PMグループ対象製品を保存しました。')
  } catch (error) {
    alert('保存に失敗しました。')
  } finally {
    savingPseudo.value = false
  }
}

// ---- 自動便振分 ----

const isWorkingDayByCalendar = (dateKey) => {
  if (dateKey in calendarDayMap.value) return calendarDayMap.value[dateKey]
  const d = new Date(`${dateKey}T00:00:00`)
  return d.getDay() !== 0 && d.getDay() !== 6
}

const addBusinessDaysByCalendar = (baseDateStr, days) => {
  let current = new Date(`${baseDateStr}T00:00:00`)
  let remaining = Math.abs(days)
  const direction = days >= 0 ? 1 : -1
  while (remaining > 0) {
    current.setDate(current.getDate() + direction)
    if (isWorkingDayByCalendar(formatLocalDate(current))) remaining--
  }
  return formatLocalDate(current)
}

const loadDefaultCalendar = async () => {
  if (!calendarList.value.length) {
    const res = await api.calendars.getCalendars()
    calendarList.value = (res.data?.results || res.data || []).sort((a, b) =>
      String(a.calendar_name).localeCompare(String(b.calendar_name)),
    )
  }
  if (!autoAssignCalendarId.value && calendarList.value.length) {
    const kubota = calendarList.value.find(
      (c) => /kubota|kobota|クボタ/.test(`${c.calendar_code}${c.calendar_name}`),
    )
    autoAssignCalendarId.value = kubota ? kubota.id : calendarList.value[0].id
  }
  await loadCalendarDays()
}

const initializeDefaultTargetDate = async () => {
  try {
    await loadDefaultCalendar()
    const previousBusinessDate = addBusinessDaysByCalendar(todayDate, -1)
    defaultTargetDate.value = previousBusinessDate
    if (!targetDate.value || targetDate.value === todayDate) {
      targetDate.value = previousBusinessDate
    }
  } catch (error) {
    const fallbackDate = addBusinessDaysByCalendar(todayDate, -1)
    defaultTargetDate.value = fallbackDate
    if (!targetDate.value || targetDate.value === todayDate) {
      targetDate.value = fallbackDate
    }
  }
}

const openAutoAssignDialog = async () => {
  try {
    await loadDefaultCalendar()
    autoAssignStartDate.value = addBusinessDaysByCalendar(todayDate, 4)
    autoAssignEndDate.value = dateKeys.value.at(-1) || autoAssignStartDate.value
    autoAssignResetExisting.value = false
    showAutoAssignDialog.value = true
  } catch (error) {
    alert('カレンダー情報の取得に失敗しました。')
  }
}

const closeAutoAssignDialog = () => {
  if (autoAssigning.value) return
  showAutoAssignDialog.value = false
}

const loadCalendarDays = async () => {
  if (!autoAssignCalendarId.value) return
  const res = await api.calendars.getCalendarDays(autoAssignCalendarId.value, { page_size: 9999 })
  const days = res.data?.results || res.data || []
  const map = {}
  days.forEach((d) => { map[d.target_date] = Boolean(d.is_working_day) })
  calendarDayMap.value = map
}

watch(hideWeekends, (v) => {
  localStorage.setItem(HIDE_WEEKENDS_KEY, v ? '1' : '0')
})

watch(targetDate, (v) => {
  planDate.value = v
})

watch(autoAssignCalendarId, async (newVal) => {
  if (newVal && showAutoAssignDialog.value) {
    await loadCalendarDays()
    autoAssignStartDate.value = addBusinessDaysByCalendar(todayDate, 4)
    autoAssignEndDate.value = dateKeys.value.at(-1) || autoAssignStartDate.value
  }
})

const ensureAutoAssignRangeVisible = async (startDate, endDate) => {
  const visibleStart = allDateKeys.value[0]
  const visibleEnd = allDateKeys.value.at(-1)
  if (visibleStart && visibleEnd && startDate >= visibleStart && endDate <= visibleEnd) {
    return
  }

  const spanDays = Math.max(1, Math.floor((new Date(`${endDate}T00:00:00`) - new Date(`${startDate}T00:00:00`)) / 86400000) + 1)
  const allowedHorizons = [5, 14, 31, 60, 90]
  const nextHorizon = allowedHorizons.find((value) => value >= spanDays)
  if (!nextHorizon) {
    throw new Error('自動振分の指定範囲は90日以内で指定してください。')
  }

  targetDate.value = startDate
  horizonDays.value = nextHorizon
  await loadGrid()
}

const autoAssignTrips = async () => {
  autoAssigning.value = true
  try {
    const thresholdDate = autoAssignStartDate.value || formatLocalDate(new Date())
    const endDate = autoAssignEndDate.value || dateKeys.value.at(-1) || thresholdDate
    if (thresholdDate > endDate) {
      alert('振分開始日は振分終了日以前にしてください。')
      return
    }
    const targetDateKeys = dateKeys.value.filter((dk) => dk >= thresholdDate && dk <= endDate)
    if (!targetDateKeys.length) {
      await ensureAutoAssignRangeVisible(thresholdDate, endDate)
    }
    const effectiveTargetDateKeys = dateKeys.value.filter((dk) => dk >= thresholdDate && dk <= endDate)
    if (!effectiveTargetDateKeys.length) {
      alert('指定範囲に表示中の日付がありません。')
      return
    }
    const hasAllCandidates = effectiveTargetDateKeys.every((dateKey) => autoAssignTruckCandidatesForDate(dateKey).length > 0)
    if (!hasAllCandidates) {
      alert('自動振分対象の実便が便マスタに設定されていない日があります。')
      return
    }
    const res = await api.kubotaSakaiTripAssignments.autoAssign(
      thresholdDate,
      endDate,
      autoAssignResetExisting.value,
    )
    const resultRowsByDate = res.data?.rows_by_date || {}
    Object.entries(resultRowsByDate).forEach(([dateKey, rows]) => {
      if (!Array.isArray(rows)) return
      const rowMap = new Map(rows.map((item) => [Number(item.due_adjustment_id), item]))
      mergedRows.value.forEach((row) => {
        entriesAt(row, dateKey).forEach((entry) => {
          const payload = rowMap.get(Number(entry.due_adjustment_id))
          if (!payload) return
          const defaultContainerId = entry.used_container_id || null
          const allocations = Array.isArray(payload.allocations) && payload.allocations.length
            ? payload.allocations.map((item) => normalizeAllocation(item, defaultContainerId))
            : [normalizeAllocation(null, defaultContainerId)]
          entry.allocations = allocations
          entry.allocations.forEach((al) => syncAllocationFromQty(entry, al))
          recalcEntry(entry)
        })
      })
    })

    if (effectiveTargetDateKeys.length > 0) {
      await previewLoadForDate(effectiveTargetDateKeys[0])
    }

    const skippedEntries = Array.isArray(res.data?.skipped) ? res.data.skipped : []
    let message = `自動振分完了: ${Number(res.data?.assigned_count || 0)}件割当`
    if (skippedEntries.length > 0) {
      const lines = skippedEntries.map((item) => {
        const remainingQty = parseNumber(item.remaining_qty)
        const headBase = `${item.date} ${item.product_code} ${item.ship_to_code || '-'} ${item.source_order_no || '内示'}`
        const head = remainingQty > 0 ? `${headBase} 残:${formatNumber(remainingQty)}` : headBase
        const reasons = Array.isArray(item.reasons) ? item.reasons
          .map((reason) => {
            const errors = Array.isArray(reason.errors) && reason.errors.length ? reason.errors.join(' / ') : '平面図に配置できません。'
            return `${reason.truck_name || reason.truck_id || '便'}: ${errors}`
          })
          .join(' | ') : ''
        return reasons ? `${head}\n  ${reasons}` : head
      })
      message += `\n\n積載不可のため未割当:\n${lines.join('\n')}`
    }
    showAutoAssignDialog.value = false
    alert(message)
  } catch (error) {
    alert('自動振分に失敗しました。')
  } finally {
    autoAssigning.value = false
  }
}

const toFavoritePayload = () => ({
  horizonDays: Number(horizonDays.value || 5),
  keyword: String(keyword.value || ''),
})

const applyFavoritePayload = (payload) => {
  const nextHorizon = Number(payload?.horizonDays || 5)
  horizonDays.value = [5, 14, 31, 60, 90].includes(nextHorizon) ? nextHorizon : 5
  keyword.value = String(payload?.keyword || '')
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

onMounted(async () => {
  await loadFavorites()
  await initializeDefaultTargetDate()
  await loadGrid()
  await nextTick()
  setStickyTopValues()
})

onUnmounted(() => {
  if (lockedClickNoticeTimer) {
    clearTimeout(lockedClickNoticeTimer)
    lockedClickNoticeTimer = null
  }
})

onUnmounted(() => {
  previewTimers.forEach((timerId) => clearTimeout(timerId))
  previewTimers.clear()
  hideCursorBubble()
})
</script>

<style scoped>
.trip-planning-page {
  padding: 8px;
  background: #eef2f6;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.locked-click-toast {
  position: fixed;
  top: 14px;
  right: 14px;
  z-index: 1600;
  padding: 8px 12px;
  border: 1px solid #dc2626;
  border-radius: 6px;
  background: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
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
.field input {
  min-width: 140px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.field select {
  min-width: 90px;
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.search-field input {
  min-width: 220px;
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
.import-btn {
  background: #dbe8ff;
  border-color: #8daed6;
}
.detail-btn {
  background: #f7f7f7;
}
.pseudo-product-btn {
  background: #fef9c3;
  border-color: #d4a017;
}
.auto-assign-btn {
  background: #e0e7ff;
  border-color: #6366f1;
}
.favorite-btn {
  background: #facc15;
  border-color: #eab308;
  color: #78350f;
  font-weight: 700;
  min-width: 34px;
}
.adj-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  background: #e0f2fe;
  border: 1px solid #38bdf8;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #0369a1;
  white-space: nowrap;
}
.pickup-btn {
  background: #eefcf5;
  border-color: #80c79c;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.35);
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-card {
  width: min(420px, calc(100vw - 32px));
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.18);
}
.save-confirm-modal {
  width: min(680px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
}
.save-confirm-scroll {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.save-confirm-message,
.save-confirm-question {
  font-size: 13px;
  line-height: 1.6;
  color: #111827;
}
.save-confirm-question {
  margin-top: 16px;
}
.save-confirm-section,
.save-confirm-line {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #111827;
  white-space: pre-wrap;
}
.save-confirm-detail {
  padding-left: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #111827;
  white-space: pre-wrap;
}
.save-confirm-line-danger,
.save-confirm-detail-danger {
  color: #b91c1c;
  font-weight: 600;
}
.display-setting-modal {
  width: min(980px, calc(100vw - 32px));
  max-height: calc(100vh - 32px);
  overflow: auto;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 14px;
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.18);
}
.modal-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 700;
  color: #111827;
}
.display-setting-body {
  display: flex;
  gap: 12px;
}
.display-setting-table-wrap {
  flex: 1;
  overflow: auto;
  border: 1px solid #d7dfe8;
}
.display-setting-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.display-setting-table th,
.display-setting-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 4px 6px;
  text-align: center;
  white-space: nowrap;
}
.display-setting-table th {
  position: sticky;
  top: 0;
  background: #eef2f7;
  z-index: 1;
}
.display-setting-actions {
  display: flex;
  justify-content: center;
  gap: 4px;
}
.display-setting-samples {
  width: 180px;
  flex-shrink: 0;
  border-left: 1px solid #d7dfe8;
  padding-left: 12px;
  font-size: 11px;
}
.display-setting-sample-title {
  font-weight: 600;
  margin-bottom: 6px;
}
.display-setting-sample-group {
  margin-bottom: 10px;
}
.display-setting-sample-label {
  font-size: 10px;
  color: #666;
  margin-bottom: 4px;
}
.display-setting-sample-item {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}
.sample-chip {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 1px solid #aaa;
  border-radius: 2px;
}
.rgb-editor {
  display: flex;
  justify-content: center;
  gap: 2px;
}
.rgb-editor input {
  width: 30px;
  font-size: 10px;
  padding: 0;
  border: 1px solid #ccc;
  border-radius: 2px;
  text-align: center;
}
.modal-fields {
  display: flex;
  gap: 8px;
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  font-size: 12px;
  color: #374151;
}
.modal-field input {
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.modal-field select {
  padding: 6px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
}
.modal-check {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
}
.modal-check input {
  width: 16px;
  height: 16px;
}
.modal-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.trip-note-modal {
  width: min(520px, calc(100vw - 32px));
}
.trip-note-target {
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}
.trip-note-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
}
.trip-note-tab {
  position: relative;
  padding: 4px 14px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #cbd5e1;
  border-radius: 4px 4px 0 0;
  background: #f1f5f9;
  color: #64748b;
  cursor: pointer;
}
.trip-note-tab.active {
  background: #fff;
  color: #1e293b;
  border-bottom-color: #fff;
}
.trip-note-ref {
  margin-top: 6px;
  padding: 5px 8px;
  font-size: 11px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  line-height: 1.4;
}
.trip-note-ref-label {
  font-weight: 700;
  color: #334155;
}
.trip-note-tab .tab-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-left: 4px;
  border-radius: 50%;
  background: #3b82f6;
  vertical-align: middle;
}
.trip-note-textarea {
  min-height: 120px;
  resize: vertical;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.5;
}
.trip-note-count {
  margin-top: 6px;
  text-align: right;
  font-size: 11px;
  color: #64748b;
}
.truck-detail-wrap {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 6px;
}
.truck-detail-table {
  width: 100%;
  border-collapse: collapse;
}
.truck-detail-table th,
.truck-detail-table td {
  border: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 6px;
}
.truck-detail-table th {
  background: #e8edf3;
  text-align: center;
}
.num-cell {
  text-align: center;
}
.detail-empty {
  text-align: center;
  color: #6b7280;
}
.pseudo-product-wrap {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  padding: 6px;
  max-height: 300px;
  overflow: auto;
}
.pseudo-product-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.pseudo-product-title {
  font-weight: 700;
  font-size: 13px;
  color: #111827;
}
.pseudo-product-table {
  width: auto;
  border-collapse: collapse;
}
.pseudo-product-table th,
.pseudo-product-table td {
  border: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 8px;
}
.pseudo-product-table th {
  background: #e8edf3;
  text-align: center;
}
.pseudo-check-cell {
  text-align: center;
}
.pseudo-label-col {
  white-space: nowrap;
  font-weight: 600;
  text-align: center;
  min-width: 30px;
}
.pseudo-product-col {
  text-align: center;
  white-space: nowrap;
  padding: 2px 6px !important;
}
.pseudo-col-code {
  font-size: 11px;
  font-weight: 600;
}
.pseudo-col-name {
  font-size: 10px;
  color: #374151;
}
.pseudo-col-shipto {
  font-size: 10px;
  color: #6b7280;
}
.day-split-left {
  border-left: 2px solid #111827 !important;
}
.main-layout {
  flex: 1;
  display: flex;
  gap: 8px;
  min-height: 0;
  min-width: 0;
}
.table-wrap {
  flex: 5;
  overflow: auto;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  min-width: 0;
}
.plan-sidebar {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 4px;
  overflow: hidden;
}
.plan-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 8px;
  background: #e8edf3;
  border-bottom: 1px solid #c5cfde;
  flex-shrink: 0;
}
.plan-sidebar-title {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}
.plan-sidebar-date-control {
  display: flex;
  align-items: center;
  gap: 3px;
}
.plan-sidebar-date-input {
  width: 118px;
  padding: 3px 4px;
  font-size: 11px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
}
.plan-date-btn {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  padding: 0;
  font-size: 14px;
  line-height: 1;
  border: 1px solid #b5c1d2;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  text-align: center;
}
.plan-date-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.plan-sidebar-body {
  flex: 1;
  overflow: auto;
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.plan-sidebar-empty {
  color: #6b7280;
  font-size: 12px;
  text-align: center;
  padding: 12px 0;
}
.plan-truck-card {
  border: 1px solid #c5cfde;
  border-radius: 4px;
  background: #f8fafc;
  padding: 6px;
}
.plan-truck-card-active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.18);
}
.plan-truck-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 4px;
}
.plan-truck-header-main,
.plan-truck-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.plan-truck-name {
  font-size: 12px;
  font-weight: 700;
  color: #111827;
}
.plan-note-btn {
  width: 24px;
  height: 24px;
  padding: 0;
  font-size: 13px;
  line-height: 1;
  border: 1px solid #94a3b8;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
}
.plan-note-btn.has-note {
  background: #fef3c7;
  border-color: #d97706;
}
.plan-note-badge {
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  color: #9a3412;
  background: #ffedd5;
  border: 1px solid #fb923c;
  border-radius: 999px;
  white-space: nowrap;
}
.plan-note-badge.urgent {
  color: #991b1b;
  background: #fee2e2;
  border-color: #ef4444;
}
.plan-note-badge.vendor {
  color: #1e3a5f;
  background: #dbeafe;
  border-color: #3b82f6;
}
.plan-overload-badge {
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: #dc2626;
  border-radius: 8px;
  white-space: nowrap;
}
.plan-note-preview {
  margin-bottom: 4px;
  padding: 4px 6px;
  font-size: 11px;
  line-height: 1.4;
  color: #7c2d12;
  background: #fff7ed;
  border: 1px solid #fdba74;
  border-radius: 4px;
  white-space: pre-wrap;
}
.plan-svg-wrap {
  width: 100%;
  background: #fff;
  border: 1px solid #d7dfe8;
  border-radius: 4px;
}
.plan-svg {
  display: block;
  width: 100%;
  height: auto;
}
.plan-bed {
  fill: #eef2f6;
  stroke: #1f2937;
  stroke-width: 6;
}
.plan-container {
  stroke: #111827;
  stroke-width: 2;
}
.plan-legend {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 6px;
}
.plan-legend-row {
  display: flex;
  align-items: flex-start;
  gap: 5px;
  font-size: 11px;
  line-height: 1.3;
  min-width: 0;
}
.plan-swatch {
  flex-shrink: 0;
  width: 10px;
  height: 10px;
  border: 1px solid #6b7280;
  border-radius: 2px;
  margin-top: 1px;
}
.plan-legend-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.plan-legend-code {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.plan-legend-count {
  font-size: 10px;
  color: #0369a1;
  font-weight: 600;
  white-space: nowrap;
}
.plan-layer-text {
  fill: #111827;
  font-weight: 700;
  user-select: none;
  pointer-events: none;
}
.plan-remaining {
  margin-top: 6px;
  border-top: 1px dashed #c5cfde;
  padding-top: 4px;
}
.plan-remaining-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 2px;
}
.plan-remaining-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  font-size: 11px;
  line-height: 1.4;
}
.plan-remaining-code {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.plan-remaining-count {
  white-space: nowrap;
  color: #0369a1;
  font-weight: 600;
}
.plan-remaining-empty {
  font-size: 11px;
  color: #6b7280;
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
  border-right: 1px solid #2d3748;
  border-bottom: 1px solid #2d3748;
  font-size: 12px;
  padding: 4px 0;
  background: #f8fafc;
  vertical-align: top;
}
.grid thead tr:first-child th {
  border-top: 1px solid #2d3748;
}
.grid th:first-child,
.grid td:first-child {
  border-left: 1px solid #2d3748;
}
.grid th {
  text-align: center;
  white-space: nowrap;
  position: sticky;
  z-index: 2;
}
.grid tbody td {
  padding: 0;
}
.grid tbody tr.trip-colored-row td {
  background: var(--trip-row-bg) !important;
  color: var(--trip-row-text) !important;
}
.left-head {
  background: #e5e7eb !important;
  position: sticky;
  z-index: 3 !important;
  left: 0;
}
.left-head.shipto-col {
  left: 136px;
}
.date-head {
  background: #eceff3 !important;
  padding: 0 6px !important;
}
.date-head.overdue-head {
  background: #fee2e2 !important;
  color: #991b1b !important;
}
.date-head-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.date-head-center {
  display: flex;
  align-items: center;
  gap: 8px;
}
.date-head-label {
  font-size: 24px;
  line-height: 1.2;
}
.date-head-note-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #94a3b8;
  border-radius: 999px;
  background: #fff;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}
.date-head-note-btn.has-note {
  background: #fef3c7;
  border-color: #d97706;
  width: auto;
  min-width: 44px;
  padding: 0 8px;
  color: #9a3412;
  font-weight: 700;
  animation: date-head-note-blink 1s step-end infinite;
}
@keyframes date-head-note-blink {
  0%, 50% {
    opacity: 1;
  }
  50.01%, 100% {
    opacity: 0.35;
  }
}
.pseudo-occ {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  font-size: 20px;
  font-weight: 500;
  color: #111827;
}
.pseudo-occ-left {
  left: 8px;
}
.pseudo-occ-right {
  right: 8px;
}
.pseudo-occ-over {
  color: #dc2626 !important;
  font-weight: 700;
}
.holiday-head {
  color: #b91c1c !important;
}
.truck-head,
.occ-head,
.item-head {
  min-width: 96px;
}
.col-order {
  width: 70px;
  min-width: 70px !important;
  max-width: 70px;
}
.col-demand,
.col-assigned,
.col-remain,
.col-progress {
  width: 50px;
  min-width: 50px !important;
  max-width: 50px;
}
.progress-negative {
  color: #dc2626;
  font-weight: 600;
}
.progress-adjust-cell {
  padding: 0 !important;
}
.progress-adjust-input {
  width: 100%;
  height: 20px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  text-align: right;
  font-size: 11px;
  padding: 0 3px;
  box-sizing: border-box;
}
.toolbar-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.toolbar-checkbox input { margin: 0; }
.active-toggle {
  background: #3b82f6 !important;
  color: #fff !important;
}
.col-select {
  width: 196px;
  min-width: 196px !important;
  max-width: 196px;
}
.truck-head {
  background: #f1f5f9 !important;
  border-bottom: 1px solid #2d3748 !important;
}
.occ-head {
  background: #f8fafc !important;
  border-bottom: 1px solid #2d3748 !important;
}
.occ-head-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.truck-60-diff {
  font-size: 11px;
  font-weight: 600;
  color: #1f2937;
}
.truck-60-diff.negative {
  color: #b91c1c;
}
.item-head {
  background: #eef2f7 !important;
  font-weight: 500;
  border-bottom: 1px solid #2d3748 !important;
}
.select-head-grid {
  display: grid;
  grid-template-columns: 35px 30px 45px 30px 34px;
  gap: 4px;
  align-items: center;
  justify-content: center;
  width: 190px;
  margin: 0 auto;
  font-size: 10px;
  line-height: 1.1;
}
.select-head-grid span {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
}
.code-col {
  min-width: 135px;
  background: #fff;
  position: sticky;
  left: 0;
  z-index: 1;
}
.product-name {
  font-size: 10px;
  color: #6b7280;
  line-height: 1.2;
}
.shipto-col {
  min-width: 72px;
  text-align: center;
  background: #fff;
  position: sticky;
  left: 136px;
  z-index: 1;
}
.shipto-name {
  font-size: 10px;
  color: #6b7280;
  line-height: 1.2;
}
.grid tbody td.code-col,
.grid tbody td.shipto-col {
  padding: 6px;
}
.cell-center {
  text-align: center;
  background: #fff;
}
.cell-right {
  text-align: center;
  background: #fff;
}
.cell-select {
  min-width: 230px;
  background: #fff;
}
.cell-stacked .sub-cell {
  min-height: 28px;
  line-height: 28px;
  padding: 0;
  border-bottom: 1px dashed #e2e8f0;
  box-sizing: border-box;
}
.cell-stacked .sub-cell:last-child {
  border-bottom: none;
}
.entry-text-subcell {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 2px 4px !important;
  line-height: 1.2 !important;
  white-space: normal;
}
.entry-order-wrap {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
}
.entry-note-badge {
  margin-top: 2px;
  padding: 1px 5px;
  border-radius: 999px;
  border: 1px solid #f97316;
  background: #fff7ed;
  color: #c2410c;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}
.select-subcell {
  padding: 2px 0 !important;
  line-height: normal !important;
}
.allocation-stack {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.allocation-row {
  display: grid;
  grid-template-columns: 35px 30px 45px 30px 34px;
  gap: 4px;
  align-items: center;
  justify-content: center;
  width: 190px;
  margin: 0 auto;
}
.allocation-row-locked {
  opacity: 0.75;
}
.allocation-row select,
.allocation-row input {
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  height: 24px;
  padding: 2px 4px;
  font-size: 12px;
}
.allocation-row select {
  width: 35px;
}
.allocation-row select.truck-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: none;
  padding-right: 2px;
}
.allocation-row select.container-select {
  width: 45px;
}
.allocation-row input {
  width: 100%;
  text-align: right;
  box-sizing: border-box;
}
.allocation-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 34px;
}
.mini {
  width: 15px;
  height: 15px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;
  font-size: 10px;
  line-height: 1;
  padding: 0;
}
.mini.danger {
  color: #b91c1c;
}
.remain-negative {
  color: #b91c1c;
  font-weight: 700;
}
.empty {
  text-align: center;
  color: #6b7280;
  padding: 20px 0 !important;
}
.note {
  font-size: 12px;
  color: #6b7280;
}
.cursor-product-bubble {
  position: fixed;
  z-index: 1200;
  pointer-events: none;
  padding: 2px 8px;
  border-radius: 999px;
  background: #fde68a;
  border: 1px solid #d97706;
  color: #7c2d12;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
}
.daily-load-row td {
  background: #f9fbff;
  border-top: 2px solid #94a3b8;
}
.daily-load-label {
  font-weight: 700;
  text-align: center;
  background: #eef2f7 !important;
}

.daily-load-note {
  font-size: 11px;
  line-height: 1.3;
  white-space: normal;
}
.daily-load-cell {
  padding: 0 !important;
  background: #fdfefe !important;
}
.daily-load-blocks {
  width: 100%;
}
.daily-load-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
.daily-load-table td {
  border-right: 2px solid #94a3b8;
  border-bottom: 1px solid #cbd5e1;
  padding: 2px 4px;
  font-size: 12px;
  line-height: 1.2;
  white-space: nowrap;
}
.daily-load-table td:nth-child(1),
.daily-load-table td:nth-child(2) {
  border-right-width: 3px;
}
.daily-load-block-start td {
  border-top: 3px solid #000 !important;
}
.daily-load-table tr:last-child td {
  border-bottom: none;
}
.daily-load-table td:last-child {
  border-right: none;
}
.daily-load-truck {
  width: 54px;
  text-align: left;
  vertical-align: top;
  background: #fafafa;
  font-weight: 500;
}
.daily-load-truck-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.daily-load-truck-occ {
  margin-left: auto;
  text-align: right;
}
.daily-load-product {
  text-align: left;
  vertical-align: middle;
  color: #111827;
}
.daily-load-product-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.daily-load-shipto {
  margin-left: auto;
  text-align: right;
}
.daily-load-empty {
  min-height: 28px;
  line-height: 28px;
  padding: 0 6px;
  color: #94a3b8;
}
</style>
