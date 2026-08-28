<template>
  <div class="stocktake-mobile" v-if="viewMode === 'list'">
    <header class="top-tabs">
      <span class="active">
        <select v-model="filters.area_id" class="area-select">
          <option value="">全エリア</option>
          <option v-for="area in areas" :key="area.id" :value="area.id">{{ area.name }}</option>
        </select>
        <button type="button" class="recorder-icon-btn" @click="showRecorderModal = true">&#x1F464;</button>
        <DataSourceDialog title="棚卸入力" :sources="dsSources" />
      </span>
      <input type="date" class="top-date" v-model="filters.stocktake_date" />
        <span style="display:flex;gap:4px;justify-content:flex-end;align-items:center">
        <span v-if="canManageAreasView" class="tab-link" @click="showAreaModal = true">&#x1F3E2;</span>
        <span class="tab-link" @click="printSlips" v-if="selectedArea">&#x1F5A8;</span>
        <span v-if="canViewLayout" class="tab-link" @click="openLayout">レイアウト</span>
      </span>
    </header>

    <section class="search-strip">
      <div class="search-grid">
        <label class="search-block">
          <span class="search-label">ライン検索 <button type="button" class="field-reset-btn" @click="clearLineFilter" aria-label="ラインクリア">クリア</button></span>
          <div class="search-input-wrap">
            <select v-model="filters.line_id">
              <option value="">すべて</option>
              <option v-for="line in lineOptions" :key="line.id" :value="line.id">
                {{ line.line_name || line.line_code }}
              </option>
            </select>
          </div>
        </label>
        <label class="search-block">
          <span class="search-label">置き場検索 <button type="button" class="field-reset-btn" @click="clearLocationFilter" aria-label="置き場クリア">クリア</button></span>
          <div class="search-input-wrap">
            <select v-model="filters.stock_location">
              <option value="">すべて</option>
              <option v-for="location in filteredLocations" :key="location" :value="location">
                {{ location }}
              </option>
            </select>
          </div>
        </label>
        <label class="search-block wide">
          <span class="search-label">品番検索 <button type="button" class="field-reset-btn" @click="clearProductCodeFilter" aria-label="品番クリア">クリア</button></span>
          <div class="search-input-wrap">
            <input v-model.trim="filters.product_code" type="text" placeholder="品番の一部入力して" />
          </div>
        </label>
      </div>
    </section>

    <section class="candidate-list">
      <div v-if="loading" class="empty-state">読込中...</div>
      <div v-else-if="!hasFilter" class="empty-state">エリア・置き場・品番のいずれかを選択してください</div>
      <div v-else-if="filteredRows.length === 0" class="empty-state">対象がありません</div>
      <div v-else class="list-stack">
        <article
          v-for="row in filteredRows"
          :key="row.product_id"
          class="stock-list-item"
          :class="{
            active: selectedProductId === row.product_id,
            dirty: isDirty(row),
            diff: hasDiff(row),
          }"
          @click="selectedProductId = row.product_id"
        >
          <div class="cell code-cell">
            <div class="cell-label">品番:</div>
            <div class="cell-value code">{{ row.product_code }}</div>
            <div class="cell-sub">{{ row.product_name || "-" }}</div>
          </div>
          <div class="cell process-cell">
            <div class="cell-label">加工先</div>
            <div class="cell-value">{{ row.process_name || row.process_code || "-" }}</div>
          </div>
          <div class="cell location-cell" :class="{ 'other-area': isOtherArea(row) }">
            <div class="cell-label">置き場:</div>
            <div class="cell-value">{{ formatRowLocations(row) }}</div>
            <div v-if="isOtherArea(row)" class="other-area-badge">他エリア品</div>
          </div>
          <div class="cell photo-cell">
            <img v-if="row.image_url" :src="row.image_url" :alt="row.product_name" />
            <div v-else class="photo-placeholder">NO IMAGE</div>
          </div>
          <div class="list-arrow">
            <button v-if="row.record_count > 0" type="button" class="history-btn" @click.stop="openHistory(row.product_id)">
              <span class="history-icon">&#x1F4CB;</span>
              <span class="history-badge">{{ row.record_count }}</span>
            </button>
            <button type="button" class="arrow-btn" @click.stop="openDetail(row.product_id)">›</button>
          </div>
        </article>
      </div>
    </section>

    <section class="confirm-area" v-if="selectedRow">
      <div class="confirm-main preview">
        <div class="confirm-head">
          <span class="confirm-title">品番</span>
          <div class="confirm-value-box">{{ selectedRow.product_code }}</div>
          <span class="confirm-title">加工先</span>
          <div class="confirm-value-box">{{ selectedRow.process_name || selectedRow.process_code || "-" }}</div>
        </div>
        <div class="confirm-photo">
          <img v-if="selectedRow.image_url" :src="selectedRow.image_url" :alt="selectedRow.product_name" />
          <div v-else class="photo-placeholder large">NO IMAGE</div>
          <span class="position-badge">{{ selectedIndexLabel }}</span>
        </div>
      </div>
    </section>
  </div>

  <div v-else-if="viewMode === 'detail'" class="stocktake-detail-mobile">
    <header class="detail-header">
      <button class="detail-back" type="button" @click="closeDetail">‹</button>
      <div class="detail-title">{{ selectedArea ? selectedArea.name : '棚卸' }}入力</div>
      <button class="detail-save" type="button" @click="saveCurrent" :disabled="saving || !canEdit || !selectedRow || normalizeNumber(editValues[selectedRow.product_id]) === null || !selectedRecorder">
        保存
      </button>
    </header>

    <section v-if="selectedRow" class="detail-body">
      <div class="detail-grid two">
        <label class="detail-field">
          <span>品番</span>
          <input :value="selectedRow.product_code" type="text" readonly />
        </label>
        <label class="detail-field">
          <span>品名</span>
          <input :value="selectedRow.product_name || '-'" type="text" readonly />
        </label>
      </div>

      <div class="detail-grid two">
        <label class="detail-field">
          <span>加工先</span>
          <input :value="selectedRow.process_name || selectedRow.process_code || '-'" type="text" readonly />
        </label>
        <label class="detail-field">
          <span>置き場</span>
          <input :value="formatRowLocations(selectedRow)" type="text" readonly />
        </label>
      </div>

      <div class="detail-grid two">
        <label class="detail-field">
          <span>机上在庫</span>
          <input :value="selectedRow.system_stock_qty" type="text" readonly />
        </label>
        <label class="detail-field">
          <span>差異</span>
          <input :value="formatSigned(calcDiff(selectedRow))" type="text" readonly />
        </label>
      </div>

      <div class="detail-grid two">
        <label class="detail-field">
          <span>入力者</span>
          <select v-model="selectedRecorder" class="recorder-select" :disabled="!canEdit">
            <option value="">選択</option>
            <option v-for="r in recorders" :key="r.id" :value="r.name">{{ r.name }}</option>
          </select>
        </label>
        <label class="detail-field">
          <span>カウンター</span>
          <select v-model="selectedCounter" class="recorder-select" :disabled="!canEdit">
            <option value="">選択</option>
            <option v-for="c in counters" :key="'c'+c.id" :value="c.name">{{ c.name }}</option>
          </select>
        </label>
      </div>
      <div class="detail-grid two">
        <label class="detail-field">
          <span>数量</span>
          <input
            :value="editValues[selectedRow.product_id]"
            type="number"
            step="1"
            inputmode="numeric"
            :readonly="!canEdit"
            @input="onActualInput(selectedRow.product_id, $event)"
          />
        </label>
        <label class="detail-field">
          <span>備考</span>
          <input
            :value="noteValues[selectedRow.product_id]"
            type="text"
            placeholder="備考"
            :readonly="!canEdit"
            @input="onNoteInput(selectedRow.product_id, $event)"
          />
        </label>
      </div>

      <div class="detail-photo-label">写真</div>
      <div class="detail-photo">
        <img v-if="selectedRow.image_url" :src="selectedRow.image_url" :alt="selectedRow.product_name" />
        <div v-else class="photo-placeholder large">NO IMAGE</div>
      </div>
    </section>
  </div>

  <div v-else-if="viewMode === 'history'" class="stocktake-detail-mobile">
    <header class="detail-header">
      <button class="detail-back" type="button" @click="closeHistory">‹</button>
      <div class="detail-title">入力履歴</div>
      <span></span>
    </header>
    <section class="detail-body" v-if="historyRow">
      <div class="history-product-info">
        <span class="history-product-code">{{ historyRow.product_code }}</span>
        <span class="history-product-name">{{ historyRow.product_name || '-' }}</span>
      </div>
      <div v-if="historyLoading" class="empty-state">読込中...</div>
      <div v-else-if="historyItems.length === 0" class="empty-state">履歴がありません</div>
      <div v-else class="history-list">
        <div v-for="item in historyItems" :key="item.id" class="history-item">
          <div class="history-qty">{{ item.actual_stock_qty }}</div>
          <div class="history-meta">
            <div>入力: {{ item.recorder_name || item.updated_by_name || '-' }}</div>
            <div v-if="item.counter_name">カウンター: {{ item.counter_name }}</div>
            <div class="history-time">{{ formatDateTime(item.updated_at) }}</div>
            <div v-if="item.note" class="history-note">{{ item.note }}</div>
          </div>
          <button v-if="canDeleteHistory" type="button" class="history-delete-btn" @click="deleteHistoryRecord(item.id)">✕</button>
        </div>
      </div>
    </section>
  </div>

  <div v-else-if="viewMode === 'layout'" class="stocktake-mobile">
    <header class="top-tabs">
      <span class="tab-link" @click="viewMode = 'list'">&#9664; 一覧</span>
      <input type="date" class="top-date" v-model="filters.stocktake_date" />
      <span class="active">レイアウト</span>
    </header>

    <section class="layout-body">
      <div class="layout-toolbar">
        <div class="zoom-controls">
          <button type="button" class="zoom-btn" @click="zoomOut">−</button>
          <span class="zoom-label">{{ Math.round(layoutZoom * 100) }}%</span>
          <button type="button" class="zoom-btn" @click="zoomIn">+</button>
        </div>
      </div>

      <div v-if="Object.keys(layoutCells).length === 0" class="layout-empty-msg">
        まだレイアウトが設定されていません。<br />PCの在庫メニューから「棚卸レイアウト編集」で作成してください。
      </div>

      <div class="layout-map-scroll">
      <div class="layout-map" :style="{ gridTemplateColumns: `repeat(${layoutCols}, 40px)`, gridTemplateRows: `repeat(${layoutRows}, 40px)`, transform: `scale(${layoutZoom})`, transformOrigin: 'top left' }">
        <template v-for="cellKey in layoutCellKeys" :key="cellKey">
          <div
            v-if="!occupiedCells.has(cellKey)"
            class="map-cell"
            :class="mapCellClass(cellKey)"
            :style="cellStyle(cellKey)"
            @click="onMapCellClick(cellKey)"
          >
            <template v-if="layoutCells[cellKey]">
              <div class="map-cell-name" :class="{ vertical: cellH(cellKey) > cellW(cellKey) }" :style="cellFontStyle(cellKey)">{{ cellLocation(cellKey) }}</div>
              <template v-if="cellType(cellKey) === 'location'">
                <div class="map-cell-progress" v-if="locationProgressMap[cellLocation(cellKey)]">
                  <div class="map-cell-bar">
                    <div class="map-cell-bar-fill" :style="{ width: locationProgressMap[cellLocation(cellKey)].pct + '%' }"></div>
                  </div>
                  <div class="map-cell-count">{{ locationProgressMap[cellLocation(cellKey)].done }}/{{ locationProgressMap[cellLocation(cellKey)].total }}</div>
                </div>
              </template>
              <div class="map-cell-comment-mark" v-if="cellComment(cellKey)" @click.stop="toggleComment(cellKey)">コ</div>
              <div class="map-cell-comment-tip" v-if="cellComment(cellKey) && showingCommentKey === cellKey" @click.stop="showingCommentKey = null">{{ cellComment(cellKey) }}</div>
            </template>
          </div>
        </template>
      </div>
      </div>
    </section>
  </div>

  <div v-if="showRecorderModal" class="modal-overlay" @click.self="showRecorderModal = false">
    <div class="modal-box people-modal">
      <div class="modal-header">入力者・カウンター管理</div>
      <div class="modal-body">
        <div class="people-manage-tabs">
          <button type="button" class="people-manage-tab" :class="{ active: peopleManageTab === 'recorder' }" @click="peopleManageTab = 'recorder'">入力者</button>
          <button type="button" class="people-manage-tab" :class="{ active: peopleManageTab === 'counter' }" @click="peopleManageTab = 'counter'">カウンター</button>
        </div>
        <div v-if="peopleManageTab === 'recorder'" class="people-manage-panel">
          <div class="people-manage-title">入力者</div>
          <div class="recorder-add-row">
            <input v-model.trim="newRecorderName" type="text" placeholder="名前を入力" :disabled="!canEdit" @keyup.enter="addRecorder" />
            <button type="button" @click="addRecorder" :disabled="!newRecorderName || !canEdit">追加</button>
          </div>
          <div v-if="recorders.length === 0" class="empty-state compact">入力者がいません</div>
          <div v-else class="recorder-list">
            <div v-for="r in recorders" :key="r.id" class="recorder-item">
              <span>{{ r.name }}</span>
              <button v-if="canEdit" type="button" class="history-delete-btn" @click="removeRecorder(r.id)">✕</button>
            </div>
          </div>
        </div>
        <div v-else class="people-manage-panel">
          <div class="people-manage-title">カウンター</div>
          <div class="recorder-add-row">
            <input v-model.trim="newCounterName" type="text" placeholder="名前を入力" :disabled="!canEdit" @keyup.enter="addCounter" />
            <button type="button" @click="addCounter" :disabled="!newCounterName || !canEdit">追加</button>
          </div>
          <div v-if="counters.length === 0" class="empty-state compact">カウンターがいません</div>
          <div v-else class="recorder-list">
            <div v-for="c in counters" :key="c.id" class="recorder-item">
              <span>{{ c.name }}</span>
              <button v-if="canEdit" type="button" class="history-delete-btn" @click="removeCounter(c.id)">✕</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" @click="showRecorderModal = false">閉じる</button>
      </div>
    </div>
  </div>

  <div v-if="showAreaModal" class="modal-overlay" @click.self="showAreaModal = false">
    <div class="modal-box area-modal">
      <div class="modal-header">エリア管理</div>
      <div class="modal-body">
        <div class="area-edit-section" v-if="canManageAreasEdit && editingArea">
          <div class="area-edit-name-row">
            <input v-model.trim="editingArea.name" placeholder="エリア名" :disabled="!canManageAreasEdit" />
            <button type="button" class="btn-save" @click="saveEditArea" :disabled="!editingArea.name || !canManageAreasEdit">保存</button>
            <button type="button" class="btn-cancel" @click="editingArea = null">戻る</button>
          </div>
          <div class="area-loc-title">所属置き場 (タップで追加/解除)</div>
          <div class="area-loc-chips">
            <span
              v-for="loc in allKnownLocations"
              :key="loc"
              class="area-loc-chip"
              :class="{ selected: editingArea.locations.includes(loc), disabled: !canManageAreasEdit }"
              @click="toggleAreaLocation(loc)"
            >{{ loc }}</span>
          </div>
          <div v-if="allKnownLocations.length === 0" class="empty-state">置き場データがありません。先に製品マスタで保管場所を設定してください。</div>
        </div>
        <div v-else>
          <div v-if="canManageAreasEdit" class="area-create-box">
            <div class="area-create-row">
              <select v-model="newAreaType" class="area-create-select" :disabled="!canManageAreasEdit">
                <option value="team">班</option>
                <option value="unit">グループ</option>
                <option value="other">その他</option>
              </select>
              <select
                v-if="newAreaType === 'team'"
                v-model="selectedTeamAreaId"
                class="area-create-select wide"
                :disabled="!canManageAreasEdit"
                @keyup.enter="createArea"
              >
                <option value="">班を選択</option>
                <option v-for="team in teamAreaOptions" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
              </select>
              <select
                v-else-if="newAreaType === 'unit'"
                v-model="selectedUnitAreaId"
                class="area-create-select wide"
                :disabled="!canManageAreasEdit"
                @keyup.enter="createArea"
              >
                <option value="">グループを選択</option>
                <option v-for="unit in unitAreaOptions" :key="unit.id" :value="String(unit.id)">{{ unit.name }}</option>
              </select>
              <input
                v-else
                v-model.trim="newAreaName"
                class="area-create-input"
                :disabled="!canManageAreasEdit"
                placeholder="その他エリア名"
                @keyup.enter="createArea"
              />
              <button type="button" @click="createArea" :disabled="!canCreateArea || !canManageAreasEdit">追加</button>
            </div>
            <div class="area-create-help">エリア作成は既存の班・グループから選択するか、「その他」で任意名を登録します。</div>
          </div>
          <div v-if="areas.length === 0" class="empty-state">エリアがありません</div>
          <div v-else class="recorder-list">
            <div v-for="area in areas" :key="area.id" class="recorder-item">
              <span v-if="canManageAreasEdit" @click="startEditArea(area)" style="cursor:pointer;flex:1">{{ area.name }} <small style="color:#6b7280">({{ area.locations.length }}置き場)</small></span>
              <span v-else style="flex:1">{{ area.name }} <small style="color:#6b7280">({{ area.locations.length }}置き場)</small></span>
              <button v-if="canManageAreasEdit" type="button" class="history-delete-btn" @click="deleteArea(area.id)">✕</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" @click="showAreaModal = false; editingArea = null">閉じる</button>
      </div>
    </div>
  </div>

</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import api from "@/api/client";
import { formatISODate } from "@/utils/dateUtil";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const filters = reactive({
  stocktake_date: formatISODate(new Date()),
  line_id: "",
  stock_location: "",
  product_code: "",
  product_name: "",
  has_image: false,
  diff_only: false,
  area_id: "",
});

const loading = ref(false);
const saving = ref(false);
const rows = ref([]);
const locations = ref([]);
const lineOptions = ref([]);
const editValues = ref({});
const noteValues = ref({});
const historyItems = ref([]);
const historyLoading = ref(false);
const historyProductId = ref(null);
const canDeleteHistory = computed(() => hasPermission(authState.user, "stocktake.delete", "edit"));
const canEdit = computed(() => hasPermission(authState.user, "stocktake", "edit"));
const canViewLayout = computed(() => hasPermission(authState.user, "stocktake.layout", "view"));
const isAreaAdminUser = computed(() => {
  const user = authState.user;
  return Boolean(user?.is_superuser || user?.username === 'admin');
});
const canManageAreasView = computed(() =>
  isAreaAdminUser.value || hasPermission(authState.user, "stocktake.area", "view")
);
const canManageAreasEdit = computed(() =>
  isAreaAdminUser.value || hasPermission(authState.user, "stocktake.area", "edit")
);
const recorders = ref([]);
const counters = ref([]);
const layoutCols = ref(4);
const layoutRows = ref(4);
const layoutCells = ref({});
const showingCommentKey = ref(null);
const layoutEditing = ref(false);
const layoutSelectedLocation = ref(null);
const placingType = ref('location');
const placingW = ref(1);
const placingH = ref(1);
const layoutZoom = ref(1);
const equipmentName = ref('');
const showRecorderModal = ref(false);
const showAreaModal = ref(false);
const dsSources = [
  { op: '取得/保存', table: 'production_stocktake_record', desc: '棚卸現物入力記録（数量・備考・入力者・カウンター）' },
  { op: '取得/保存', table: 'production_stocktake_recorder', desc: '棚卸入力者（日ごと）' },
  { op: '取得/保存', table: 'production_stocktake_counter', desc: '棚卸カウンター（日ごと）' },
  { op: '取得/保存', table: 'production_stocktake_area', desc: '棚卸エリア（置き場のグルーピング）' },
  { op: '取得', table: 'production_stocktake_layout_config', desc: 'レイアウト配置設定（エリア別）' },
  { op: '取得', table: 'm_product', desc: '製品マスタ（品番・品名・画像）' },
  { op: '取得', table: 'm_product_stock_location', desc: '製品別置き場マスタ' },
  { op: '取得', table: 'line_backlog', desc: '在庫（机上在庫数の算出元）' },
]
const areas = ref([]);
const newAreaName = ref('');
const newAreaType = ref('team');
const selectedTeamAreaId = ref('');
const selectedUnitAreaId = ref('');
const teamAreaOptions = ref([]);
const unitAreaOptions = ref([]);
const editingArea = ref(null);
const allKnownLocations = ref([]);

const zoomIn = () => { layoutZoom.value = Math.min(2, +(layoutZoom.value + 0.2).toFixed(1)); };
const zoomOut = () => { layoutZoom.value = Math.max(0.4, +(layoutZoom.value - 0.2).toFixed(1)); };
const newRecorderName = ref("");
const newCounterName = ref("");
const peopleManageTab = ref("recorder");
const selectedRecorder = ref("");
const selectedCounter = ref("");
const selectedProductId = ref(null);
const viewMode = ref("list");

const normalizeNumber = (value) => {
  if (value === "" || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const hydrateEditors = (items) => {
  const actualMap = {};
  const noteMap = {};
  items.forEach((row) => {
    actualMap[row.product_id] = row.actual_stock_qty ?? "";
    noteMap[row.product_id] = row.note || "";
  });
  editValues.value = actualMap;
  noteValues.value = noteMap;
};

const syncSelectedRow = (items) => {
  if (!items.length) {
    selectedProductId.value = null;
    return;
  }
  const hasSelected = items.some((row) => row.product_id === selectedProductId.value);
  if (!hasSelected) {
    selectedProductId.value = items[0].product_id;
  }
};

const hasFilter = computed(() =>
  !!(filters.area_id || filters.line_id || filters.stock_location || filters.product_code)
);

const loadMasters = async () => {
  try {
    const response = await api.stocktakeRecords.list({
      stocktake_date: filters.stocktake_date,
      masters_only: 'true',
    });
    lineOptions.value = Array.isArray(response.data?.lines) ? response.data.lines : [];
    locations.value = Array.isArray(response.data?.locations) ? response.data.locations : [];
  } catch (_) {}
};

const reload = async () => {
  if (!hasFilter.value) {
    rows.value = [];
    selectedProductId.value = null;
    return;
  }
  loading.value = true;
  try {
    const response = await api.stocktakeRecords.list({
      stocktake_date: filters.stocktake_date,
      line_id: filters.line_id || undefined,
      stock_location: filters.stock_location || undefined,
      product_code: filters.product_code || undefined,
      product_name: filters.product_name || undefined,
      has_image: filters.has_image ? "true" : undefined,
      diff_only: filters.diff_only ? "true" : undefined,
    });
    rows.value = Array.isArray(response.data?.rows) ? response.data.rows : [];
    hydrateEditors(rows.value);
    syncSelectedRow(rows.value);
  } catch (error) {
    console.error("棚卸一覧取得エラー:", error);
    alert(error?.response?.data?.detail || "棚卸一覧の取得に失敗しました。");
  } finally {
    loading.value = false;
  }
};

const calcDiff = (row) => {
  const actual = normalizeNumber(editValues.value[row.product_id]);
  if (actual === null) return row.diff_qty ?? 0;
  return actual - Number(row.system_stock_qty || 0);
};

const isDirty = (row) => {
  const actual = normalizeNumber(editValues.value[row.product_id]);
  const originalActual = normalizeNumber(row.actual_stock_qty);
  const note = String(noteValues.value[row.product_id] || "");
  const originalNote = String(row.note || "");
  return actual !== originalActual || note !== originalNote;
};

const hasDiff = (row) => calcDiff(row) !== 0;
const selectedArea = computed(() => {
  if (!filters.area_id) return null;
  return areas.value.find(a => a.id === Number(filters.area_id)) || null;
});
const filteredLocations = computed(() => {
  if (!selectedArea.value) return locations.value;
  return locations.value.filter(l => selectedArea.value.locations.includes(l));
});
const isInSelectedArea = (row) => {
  if (!selectedArea.value) return true;
  const locs = new Set(selectedArea.value.locations);
  const rowLocs = getRowLocations(row);
  if (!rowLocs.length) return false;
  return rowLocs.some(l => locs.has(l));
};
const isOtherArea = (row) => {
  if (!selectedArea.value) return false;
  return !isInSelectedArea(row);
};
const areaFilteredRows = computed(() => {
  if (!selectedArea.value) return rows.value;
  if (filters.product_code) {
    const code = filters.product_code.toLowerCase();
    const matched = rows.value.filter(row =>
      row.product_code.toLowerCase().includes(code)
    );
    matched.sort((a, b) => {
      const aIn = isInSelectedArea(a) ? 0 : 1;
      const bIn = isInSelectedArea(b) ? 0 : 1;
      return aIn - bIn;
    });
    return matched;
  }
  return rows.value.filter(row => isInSelectedArea(row));
});
const diffCount = computed(() => filteredRows.value.filter((row) => hasDiff(row)).length);
const filteredRows = computed(() => areaFilteredRows.value);
const selectedRow = computed(() => filteredRows.value.find((row) => row.product_id === selectedProductId.value) || null);
const selectedRowIndex = computed(() => filteredRows.value.findIndex((row) => row.product_id === selectedProductId.value));
const selectedIndexLabel = computed(() => {
  if (selectedRowIndex.value < 0) return "-";
  return `${selectedRowIndex.value + 1} / ${filteredRows.value.length}`;
});
const canMovePrev = computed(() => selectedRowIndex.value > 0);
const canMoveNext = computed(() => selectedRowIndex.value >= 0 && selectedRowIndex.value < filteredRows.value.length - 1);
const newAreaResolvedName = computed(() => {
  if (newAreaType.value === 'team') {
    return teamAreaOptions.value.find((team) => String(team.id) === String(selectedTeamAreaId.value))?.name || '';
  }
  if (newAreaType.value === 'unit') {
    return unitAreaOptions.value.find((unit) => String(unit.id) === String(selectedUnitAreaId.value))?.name || '';
  }
  return newAreaName.value.trim();
});
const areaNameExists = computed(() =>
  areas.value.some((area) => area.name === newAreaResolvedName.value)
);
const canCreateArea = computed(() => !!newAreaResolvedName.value && !areaNameExists.value);

const getRowLocations = (row) => {
  if (row.stock_locations && row.stock_locations.length) return row.stock_locations;
  if (row.stock_location) return [row.stock_location];
  return [];
};
const formatRowLocations = (row) => {
  const locs = getRowLocations(row);
  return locs.length ? locs.join(', ') : '-';
};

const locationTiles = computed(() => {
  const map = {};
  for (const row of rows.value) {
    const locs = getRowLocations(row);
    const keys = locs.length ? locs : ['(未設定)'];
    for (const loc of keys) {
      if (!map[loc]) map[loc] = { location: loc, total: 0, done: 0, productIds: new Set() };
      if (!map[loc].productIds.has(row.product_id)) {
        map[loc].productIds.add(row.product_id);
        map[loc].total++;
        if (row.record_count > 0) map[loc].done++;
      }
    }
  }
  return Object.values(map)
    .map((t) => {
      delete t.productIds;
      t.remaining = t.total - t.done;
      t.progressPct = t.total > 0 ? Math.round((t.done / t.total) * 100) : 0;
      t.statusClass = t.done === 0 ? 'tile-none' : t.remaining === 0 ? 'tile-complete' : 'tile-partial';
      return t;
    })
    .sort((a, b) => a.location.localeCompare(b.location, 'ja'));
});

const openLayout = async () => {
  if (!canViewLayout.value) return;
  filters.line_id = '';
  filters.stock_location = '';
  filters.product_code = '';
  viewMode.value = 'layout';
  await loadLayoutConfig();
};

const goToLocationList = (location) => {
  filters.stock_location = location === '(未設定)' ? '' : location;
  viewMode.value = 'list';
};

const layoutCellKeys = computed(() => {
  const keys = [];
  for (let r = 0; r < layoutRows.value; r++) {
    for (let c = 0; c < layoutCols.value; c++) {
      keys.push(`${r}-${c}`);
    }
  }
  return keys;
});

const allLocations = computed(() => {
  const set = new Set();
  for (const row of rows.value) {
    for (const loc of getRowLocations(row)) set.add(loc);
  }
  return [...set].sort((a, b) => a.localeCompare(b, 'ja'));
});

const cellLocation = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell) return null;
  return typeof cell === 'string' ? cell : cell.location;
};

const cellType = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell) return null;
  if (typeof cell === 'string') return 'location';
  return cell.type || 'location';
};

const cellW = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell || typeof cell === 'string') return 1;
  return cell.w || 1;
};

const cellH = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell || typeof cell === 'string') return 1;
  return cell.h || 1;
};

const cellComment = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell || typeof cell === 'string') return '';
  return cell.comment || '';
};

const toggleComment = (cellKey) => {
  showingCommentKey.value = showingCommentKey.value === cellKey ? null : cellKey;
};

const occupiedCells = computed(() => {
  const set = new Set();
  for (const [key, cell] of Object.entries(layoutCells.value)) {
    if (!cell) continue;
    const [r, c] = key.split('-').map(Number);
    const w = typeof cell === 'string' ? 1 : (cell.w || 1);
    const h = typeof cell === 'string' ? 1 : (cell.h || 1);
    for (let dr = 0; dr < h; dr++) {
      for (let dc = 0; dc < w; dc++) {
        if (dr === 0 && dc === 0) continue;
        set.add(`${r + dr}-${c + dc}`);
      }
    }
  }
  return set;
});

const placedLocations = computed(() => {
  const set = new Set();
  for (const cell of Object.values(layoutCells.value)) {
    if (!cell) continue;
    const type = typeof cell === 'string' ? 'location' : (cell.type || 'location');
    if (type === 'location') set.add(typeof cell === 'string' ? cell : cell.location);
  }
  return set;
});

const placedEquipments = computed(() => {
  const list = [];
  for (const cell of Object.values(layoutCells.value)) {
    if (!cell || typeof cell === 'string') continue;
    if (cell.type === 'equipment') list.push(cell.location);
  }
  return list;
});

const unplacedEquipments = computed(() => {
  const placed = new Set(placedEquipments.value);
  const all = new Set();
  for (const cell of Object.values(layoutCells.value)) {
    if (!cell || typeof cell === 'string') continue;
    if (cell.type === 'equipment') all.add(cell.location);
  }
  return [...all].filter((eq) => !placed.has(eq));
});

const unplacedLocations = computed(() =>
  allLocations.value.filter((loc) => !placedLocations.value.has(loc))
);

const locationProgressMap = computed(() => {
  const map = {};
  for (const t of locationTiles.value) {
    map[t.location] = { total: t.total, done: t.done, pct: t.progressPct };
  }
  return map;
});

const cellColorMap = {
  red: { bg: "#fecaca", border: "#f87171" },
  orange: { bg: "#fed7aa", border: "#fb923c" },
  yellow: { bg: "#fef08a", border: "#facc15" },
  green: { bg: "#bbf7d0", border: "#4ade80" },
  blue: { bg: "#bfdbfe", border: "#60a5fa" },
  purple: { bg: "#ddd6fe", border: "#a78bfa" },
  pink: { bg: "#fbcfe8", border: "#f472b6" },
  brown: { bg: "#d7ccc8", border: "#a1887f" },
};

const cellStyle = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  const [r, c] = cellKey.split('-').map(Number);
  const style = { gridRow: `${r + 1}`, gridColumn: `${c + 1}` };
  if (cell) {
    const w = typeof cell === 'string' ? 1 : (cell.w || 1);
    const h = typeof cell === 'string' ? 1 : (cell.h || 1);
    if (w > 1) style.gridColumn = `${c + 1} / span ${w}`;
    if (h > 1) style.gridRow = `${r + 1} / span ${h}`;
    const clr = typeof cell === 'string' ? '' : (cell.color || '');
    if (clr && cellColorMap[clr]) {
      style.background = cellColorMap[clr].bg;
      style.borderColor = cellColorMap[clr].border;
    }
  }
  return style;
};

const cellFontStyle = (cellKey) => {
  const cell = layoutCells.value[cellKey];
  if (!cell || typeof cell === 'string') return {};
  const fs = cell.fontSize;
  if (!fs) return {};
  return { fontSize: `${fs}px` };
};

const mapCellClass = (cellKey) => {
  const loc = cellLocation(cellKey);
  if (!loc) return layoutEditing.value ? 'map-cell-empty-edit' : 'map-cell-empty';
  if (cellType(cellKey) === 'equipment') return 'tile-equipment';
  if (cellType(cellKey) === 'aisle') return 'tile-aisle';
  const prog = locationProgressMap.value[loc];
  if (!prog || prog.done === 0) return 'tile-none';
  if (prog.done >= prog.total) return 'tile-complete';
  return 'tile-partial';
};

const selectLocationToPlace = (loc) => {
  layoutSelectedLocation.value = loc;
  placingType.value = 'location';
  placingW.value = 1;
  placingH.value = 1;
};

const selectEquipmentToPlace = (eq) => {
  layoutSelectedLocation.value = eq;
  placingType.value = 'equipment';
  placingW.value = 1;
  placingH.value = 1;
};

const addEquipment = () => {
  if (!equipmentName.value) return;
  layoutSelectedLocation.value = equipmentName.value;
  placingType.value = 'equipment';
  placingW.value = 1;
  placingH.value = 1;
  equipmentName.value = '';
};

const canPlace = (r, c, w, h) => {
  for (let dr = 0; dr < h; dr++) {
    for (let dc = 0; dc < w; dc++) {
      const k = `${r + dr}-${c + dc}`;
      if (r + dr >= layoutRows.value || c + dc >= layoutCols.value) return false;
      if (layoutCells.value[k] || occupiedCells.value.has(k)) return false;
    }
  }
  return true;
};

const onMapCellClick = (cellKey) => {
  if (layoutEditing.value) {
    if (layoutSelectedLocation.value && !layoutCells.value[cellKey] && !occupiedCells.value.has(cellKey)) {
      const [r, c] = cellKey.split('-').map(Number);
      const w = placingW.value;
      const h = placingH.value;
      if (!canPlace(r, c, w, h)) {
        alert('この位置にはこのサイズで配置できません');
        return;
      }
      layoutCells.value = {
        ...layoutCells.value,
        [cellKey]: { location: layoutSelectedLocation.value, w, h, type: placingType.value },
      };
      layoutSelectedLocation.value = null;
    }
  } else {
    if (cellType(cellKey) === 'equipment') return;
    const loc = cellLocation(cellKey);
    if (loc) goToLocationList(loc);
  }
};

const removeLayoutCell = (cellKey) => {
  const newCells = { ...layoutCells.value };
  delete newCells[cellKey];
  layoutCells.value = newCells;
};

const loadLayoutConfig = async () => {
  try {
    const params = filters.area_id ? { area_id: filters.area_id } : {};
    const res = await api.stocktakeRecords.getLayoutConfig(params);
    layoutCols.value = res.data.cols || 4;
    layoutRows.value = res.data.rows || 4;
    const raw = res.data.cells || {};
    const converted = {};
    for (const [key, val] of Object.entries(raw)) {
      converted[key] = typeof val === 'string' ? { location: val, w: 1, h: 1 } : val;
    }
    layoutCells.value = converted;
    if (Object.keys(layoutCells.value).length === 0) {
      layoutEditing.value = true;
    }
  } catch (e) {
    console.error("レイアウト設定取得エラー:", e);
    layoutEditing.value = true;
  }
};

const saveLayoutConfig = async () => {
  try {
    await api.stocktakeRecords.saveLayoutConfig({
      cols: layoutCols.value,
      rows: layoutRows.value,
      cells: layoutCells.value,
    });
  } catch (e) {
    console.error("レイアウト設定保存エラー:", e);
    alert("レイアウト保存に失敗しました。");
  }
};

const toggleLayoutEdit = async () => {
  if (layoutEditing.value) {
    await saveLayoutConfig();
    layoutEditing.value = false;
    layoutSelectedLocation.value = null;
  } else {
    layoutEditing.value = true;
  }
};

const onActualInput = (productId, event) => {
  editValues.value = {
    ...editValues.value,
    [productId]: event.target.value,
  };
};

const onNoteInput = (productId, event) => {
  noteValues.value = {
    ...noteValues.value,
    [productId]: event.target.value,
  };
};

const moveSelection = (direction) => {
  const nextIndex = selectedRowIndex.value + direction;
  if (nextIndex < 0 || nextIndex >= filteredRows.value.length) return;
  selectedProductId.value = filteredRows.value[nextIndex].product_id;
};

const openDetail = (productId) => {
  selectedProductId.value = productId;
  editValues.value = { ...editValues.value, [productId]: "" };
  noteValues.value = { ...noteValues.value, [productId]: "" };
  viewMode.value = "detail";
};

const closeDetail = () => {
  viewMode.value = "list";
};

const historyRow = computed(() => rows.value.find((r) => r.product_id === historyProductId.value) || null);

const openHistory = async (productId) => {
  historyProductId.value = productId;
  viewMode.value = "history";
  historyLoading.value = true;
  try {
    const res = await api.stocktakeRecords.history(productId, { stocktake_date: filters.stocktake_date });
    historyItems.value = Array.isArray(res.data?.items) ? res.data.items : [];
  } catch (e) {
    console.error("履歴取得エラー:", e);
    historyItems.value = [];
  } finally {
    historyLoading.value = false;
  }
};

const closeHistory = () => {
  viewMode.value = "list";
};

const deleteHistoryRecord = async (recordId) => {
  if (!confirm("この入力を削除しますか？")) return;
  try {
    await api.stocktakeRecords.deleteRecord(historyProductId.value, recordId);
    historyItems.value = historyItems.value.filter((i) => i.id !== recordId);
    await reload();
  } catch (e) {
    console.error("削除エラー:", e);
    alert("削除に失敗しました。");
  }
};

const loadRecorders = async () => {
  try {
    const res = await api.stocktakeRecords.listRecorders({ stocktake_date: filters.stocktake_date });
    recorders.value = Array.isArray(res.data?.recorders) ? res.data.recorders : [];
  } catch (e) {
    console.error("記入者取得エラー:", e);
    recorders.value = [];
  }
};

const loadCounters = async () => {
  try {
    const res = await api.stocktakeRecords.listCounters({ stocktake_date: filters.stocktake_date });
    counters.value = Array.isArray(res.data?.counters) ? res.data.counters : [];
  } catch (e) {
    console.error("カウンター取得エラー:", e);
    counters.value = [];
  }
};

const addRecorder = async () => {
  if (!canEdit.value) return;
  if (!newRecorderName.value) return;
  try {
    await api.stocktakeRecords.addRecorder({ stocktake_date: filters.stocktake_date, name: newRecorderName.value });
    newRecorderName.value = "";
    await loadRecorders();
  } catch (e) {
    console.error("記入者追加エラー:", e);
    alert("追加に失敗しました。");
  }
};

const addCounter = async () => {
  if (!canEdit.value) return;
  if (!newCounterName.value) return;
  try {
    await api.stocktakeRecords.addCounter({ stocktake_date: filters.stocktake_date, name: newCounterName.value });
    newCounterName.value = "";
    await loadCounters();
  } catch (e) {
    console.error("カウンター追加エラー:", e);
    alert("追加に失敗しました。");
  }
};

const removeRecorder = async (id) => {
  if (!canEdit.value) return;
  try {
    await api.stocktakeRecords.removeRecorder({ id });
    await loadRecorders();
  } catch (e) {
    console.error("記入者削除エラー:", e);
  }
};

const removeCounter = async (id) => {
  if (!canEdit.value) return;
  try {
    await api.stocktakeRecords.removeCounter({ id });
    await loadCounters();
  } catch (e) {
    console.error("カウンター削除エラー:", e);
  }
};

const clearLineFilter = () => {
  filters.line_id = "";
};

const clearLocationFilter = () => {
  filters.stock_location = "";
};

const clearProductCodeFilter = () => {
  filters.product_code = "";
};

const loadAreas = async () => {
  try {
    const res = await api.stocktakeRecords.listAreas();
    areas.value = Array.isArray(res.data?.areas) ? res.data.areas : [];
  } catch (e) {
    console.error('エリア取得エラー:', e);
  }
};

const loadAreaMasterOptions = async () => {
  try {
    const [teamsRes, unitsRes] = await Promise.all([
      api.accounts.getTeams(),
      api.accounts.getUnits(),
    ]);
    teamAreaOptions.value = (Array.isArray(teamsRes.data) ? teamsRes.data : [])
      .map((item) => ({ id: item.id, name: item.name || item.team_name || '' }))
      .filter((item) => item.name)
      .sort((a, b) => a.name.localeCompare(b.name, 'ja'));
    unitAreaOptions.value = (Array.isArray(unitsRes.data) ? unitsRes.data : [])
      .map((item) => ({ id: item.id, name: item.name || item.unit_name || '' }))
      .filter((item) => item.name)
      .sort((a, b) => a.name.localeCompare(b.name, 'ja'));
  } catch (e) {
    console.error('班・グループ取得エラー:', e);
    teamAreaOptions.value = [];
    unitAreaOptions.value = [];
  }
};

const loadAllKnownLocations = async () => {
  try {
    const res = await api.stocktakeRecords.list({
      stocktake_date: filters.stocktake_date,
      masters_only: 'true',
    });
    const apiLocs = Array.isArray(res.data?.locations) ? res.data.locations : [];
    allKnownLocations.value = apiLocs.sort((a, b) => a.localeCompare(b, 'ja'));
  } catch (e) {
    console.error('置き場一覧取得エラー:', e);
  }
};

const createArea = async () => {
  if (!canManageAreasEdit.value) return;
  const areaName = newAreaResolvedName.value;
  if (!areaName) return;
  if (areaNameExists.value) {
    alert('同じ名前のエリアが既にあります');
    return;
  }
  try {
    await api.stocktakeRecords.saveArea({ name: areaName, locations: [] });
    newAreaName.value = '';
    selectedTeamAreaId.value = '';
    selectedUnitAreaId.value = '';
    await loadAreas();
  } catch (e) {
    alert('エリア追加に失敗しました');
  }
};

const deleteArea = async (id) => {
  if (!canManageAreasEdit.value) return;
  if (!confirm('このエリアを削除しますか？')) return;
  try {
    await api.stocktakeRecords.deleteArea(id);
    if (String(filters.area_id) === String(id)) filters.area_id = '';
    await loadAreas();
  } catch (e) {
    alert('エリア削除に失敗しました');
  }
};

const startEditArea = (area) => {
  if (!canManageAreasEdit.value) return;
  editingArea.value = { ...area, locations: [...area.locations] };
  loadAllKnownLocations();
};

const toggleAreaLocation = (loc) => {
  if (!canManageAreasEdit.value || !editingArea.value) return;
  const idx = editingArea.value.locations.indexOf(loc);
  if (idx >= 0) editingArea.value.locations.splice(idx, 1);
  else editingArea.value.locations.push(loc);
};

const saveEditArea = async () => {
  if (!canManageAreasEdit.value) return;
  if (!editingArea.value?.name) return;
  try {
    await api.stocktakeRecords.saveArea({
      id: editingArea.value.id,
      name: editingArea.value.name,
      locations: editingArea.value.locations,
    });
    editingArea.value = null;
    await loadAreas();
  } catch (e) {
    alert('エリア保存に失敗しました');
  }
};

const buildSaveItems = (targetRows) =>
  targetRows
    .map((row) => {
      let note = String(noteValues.value[row.product_id] || "").trim();
      if (isOtherArea(row) && !note.includes("他エリア")) {
        note = note ? `他エリア ${note}` : "他エリア";
      }
      return {
        product_id: row.product_id,
        system_stock_qty: Number(row.system_stock_qty || 0),
        actual_stock_qty: normalizeNumber(editValues.value[row.product_id]) ?? 0,
        note,
        recorder_name: selectedRecorder.value,
        counter_name: selectedCounter.value,
        area_name: selectedArea.value?.name || '',
      };
    });

const saveCurrent = async () => {
  if (!canEdit.value) return;
  if (!selectedRow.value) return;
  const items = buildSaveItems([selectedRow.value]);
  if (!items.length) return;

  saving.value = true;
  try {
    await api.stocktakeRecords.save({
      stocktake_date: filters.stocktake_date,
      items,
    });
    await reload();
    viewMode.value = "list";
    alert("棚卸現物数を保存しました。");
  } catch (error) {
    console.error("棚卸保存エラー:", error);
    alert(error?.response?.data?.detail || "棚卸保存に失敗しました。");
  } finally {
    saving.value = false;
  }
};

const formatSigned = (value) => {
  const num = Number(value || 0);
  if (num > 0) return `+${num}`;
  return `${num}`;
};

const formatDateTime = (value) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
};

const printSlips = async () => {
  if (!selectedArea.value) return;
  if (!selectedArea.value.locations?.length) {
    alert('このエリアに置き場が登録されていません。');
    return;
  }
  const inputDate = prompt('棚卸日を入力してください（例: 2026-08-12）', filters.stocktake_date);
  if (!inputDate) return;
  try {
    const res = await api.stocktakeRecords.slipPdf({
      area_id: selectedArea.value.id,
      stocktake_date: inputDate,
    });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement('a');
    a.href = url;
    a.download = `棚卸メモ_${selectedArea.value.name}_${inputDate}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('PDF出力に失敗しました');
  }
};

onMounted(() => {
  loadMasters();
  reload();
  loadRecorders();
  loadCounters();
  loadAreas();
  loadAreaMasterOptions();
});

watch(
  () => [filters.stocktake_date, filters.area_id, filters.line_id, filters.stock_location, filters.product_code],
  () => {
    reload();
  }
);

watch(() => filters.stocktake_date, () => {
  loadRecorders();
  loadCounters();
});

watch(newAreaType, () => {
  newAreaName.value = '';
  selectedTeamAreaId.value = '';
  selectedUnitAreaId.value = '';
});
</script>

<style scoped>
.stocktake-mobile {
  max-width: 600px;
  margin: 0 auto;
  min-height: 100vh;
  padding: 10px 10px 88px;
  background: #9ccf39;
  color: #1f2937;
  font-family: "Noto Sans JP", "Segoe UI", sans-serif;
}

.top-tabs {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 6px 6px 4px;
  font-size: 13px;
  font-weight: 700;
  color: #f5f5f5;
  background: #87bf23;
}

.top-date {
  text-align: center;
  font-size: 12px;
  background: transparent;
  border: none;
  color: #fff;
  font-weight: 700;
  font-family: inherit;
}

.top-tabs .active {
  text-align: left;
  color: #fff9cc;
}

.top-tabs span:last-child {
  text-align: right;
}

.tab-link {
  cursor: pointer;
  opacity: 0.7;
}

.tab-link:active {
  opacity: 1;
}

.layout-body {
  padding: 4px;
}

.layout-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.layout-mode-btn {
  padding: 3px 12px;
  border: 1px solid #9ca3af;
  background: #f8fafc;
  font-size: 11px;
  cursor: pointer;
  border-radius: 4px;
}

.layout-mode-btn.active {
  background: #2f5eae;
  color: #fff;
  border-color: #2f5eae;
}

.layout-size-label {
  font-size: 10px;
  color: #475569;
}

.layout-size-input {
  width: 36px;
  height: 22px;
  border: 1px solid #9ca3af;
  text-align: center;
  font-size: 11px;
  margin-left: 2px;
}

.layout-step-guide {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 4px;
  padding: 6px 8px;
  margin-bottom: 6px;
}

.step-label {
  font-size: 11px;
  font-weight: 700;
  color: #166534;
}

.layout-empty-msg {
  text-align: center;
  padding: 24px 8px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
}

.layout-placing-hint {
  font-size: 11px;
  color: #1e40af;
  background: #dbeafe;
  padding: 4px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
}

.layout-cancel-btn {
  border: none;
  background: transparent;
  color: #ef4444;
  font-size: 11px;
  cursor: pointer;
  margin-left: 6px;
}

.span-label {
  margin-left: 6px;
  font-size: 11px;
}

.span-input {
  width: 32px;
  padding: 1px 2px;
  font-size: 11px;
  border: 1px solid #93c5fd;
  border-radius: 3px;
  margin-left: 2px;
}

.layout-map-scroll {
  overflow: auto;
  max-height: 70vh;
  -webkit-overflow-scrolling: touch;
}

.layout-map {
  display: grid;
  gap: 2px;
  margin-bottom: 6px;
  width: max-content;
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.zoom-btn {
  width: 26px;
  height: 26px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zoom-label {
  font-size: 11px;
  min-width: 32px;
  text-align: center;
}

.map-cell {
  position: relative;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  cursor: pointer;
  padding: 2px 2px;
  min-height: 36px;
}

.map-cell-empty {
  background: #f3f4f6;
  border: 1px dashed #d1d5db;
}

.map-cell-empty-edit {
  background: #f0f9ff;
  border: 1px dashed #93c5fd;
}

.map-cell-empty-edit:hover {
  background: #dbeafe;
}

.tile-none {
  background: #e5e7eb;
  border: 1px solid #d1d5db;
}

.tile-partial {
  background: #fff3cd;
  border: 1px solid #f59e0b;
}

.tile-complete {
  background: #d1fae5;
  border: 1px solid #10b981;
}

.tile-equipment {
  background: #c7d2fe;
  border: 1px solid #6366f1;
  cursor: default;
}

.tile-aisle {
  background: #d1d5db;
  border: 1px solid #9ca3af;
  cursor: default;
}

.map-cell-comment-mark {
  position: absolute;
  top: 0;
  right: 2px;
  font-size: 14px;
  font-weight: 700;
  color: #f59e0b;
  line-height: 1;
  cursor: pointer;
  z-index: 5;
}

.map-cell-comment-tip {
  position: absolute;
  bottom: calc(100% + 4px);
  left: 50%;
  transform: translateX(-50%);
  background: #1f2937;
  color: #fff;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 100;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.map-cell-name {
  font-size: 9px;
  font-weight: 700;
  color: #1f2937;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.map-cell-name.vertical {
  writing-mode: vertical-rl;
  white-space: normal;
  width: auto;
  text-overflow: clip;
}

.map-cell-progress {
  position: absolute;
  bottom: 1px;
  left: 2px;
  right: 2px;
}

.map-cell-bar {
  height: 3px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.map-cell-bar-fill {
  height: 100%;
  background: #10b981;
  border-radius: 2px;
}

.tile-partial .map-cell-bar-fill {
  background: #f59e0b;
}

.map-cell-count {
  font-size: 7px;
  color: #6b7280;
  text-align: center;
}

.map-cell-remove {
  position: absolute;
  top: 0;
  right: 0;
  width: 14px;
  height: 14px;
  border: none;
  background: #ef4444;
  color: #fff;
  font-size: 8px;
  line-height: 14px;
  padding: 0;
  cursor: pointer;
  border-radius: 0 4px 0 4px;
}

.layout-location-palette {
  margin-bottom: 6px;
}

.palette-title {
  font-size: 10px;
  color: #6b7280;
  margin-bottom: 4px;
}

.palette-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.palette-item {
  padding: 3px 8px;
  border: 1px solid #d1d5db;
  background: #f8fafc;
  font-size: 10px;
  cursor: pointer;
  border-radius: 4px;
}

.palette-item.selected {
  background: #2f5eae;
  color: #fff;
  border-color: #2f5eae;
}

.palette-item-equip {
  background: #e8e0ff;
  border-color: #a5b4fc;
}

.palette-item-equip.selected {
  background: #6366f1;
  border-color: #6366f1;
}

.layout-palette-section {
  margin-bottom: 6px;
}

.palette-header {
  font-size: 10px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 3px;
}

.palette-empty {
  font-size: 10px;
  color: #9ca3af;
}

.equipment-add-row {
  display: flex;
  gap: 4px;
  margin-bottom: 4px;
}

.equipment-input {
  flex: 1;
  padding: 3px 6px;
  font-size: 11px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.equipment-add-btn {
  padding: 3px 10px;
  font-size: 11px;
  border: 1px solid #6366f1;
  background: #6366f1;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
}

.equipment-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.placing-type-badge.equip {
  font-size: 9px;
  background: #6366f1;
  color: #fff;
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 4px;
}

.search-strip {
  padding: 0;
  background: #9ccf39;
}

.search-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1.35fr;
  gap: 0;
}

.search-block {
  font-size: 9px;
  color: #23360a;
  min-width: 0;
  overflow: hidden;
}

.search-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1px;
}

.field-reset-btn {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 10px;
  line-height: 1;
  cursor: pointer;
  color: inherit;
}

.search-input-wrap {
  position: relative;
}

.search-input-wrap select,
.search-input-wrap input,
.mini-field input,
.note-row input,
.qty-card input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #8a9aa9;
  border-radius: 0;
  background: #ffffff;
  padding: 0 2px;
  font-size: 12px;
  height: 28px;
}

.candidate-list {
  padding: 0 3px;
  max-height: 286px;
  overflow: hidden;
}

.list-stack {
  display: grid;
  gap: 4px;
  max-height: 286px;
  overflow-y: auto;
}

.stock-list-item {
  display: grid;
  grid-template-columns: 1.3fr 0.8fr 0.7fr 0.95fr 44px;
  grid-template-rows: auto;
  gap: 0;
  padding: 0;
  background: transparent;
  border: 2px solid #f0f0f0;
  cursor: pointer;
}

.stock-list-item.active {
  border-color: #000000;
}

.stock-list-item.diff {
  box-shadow: inset 0 0 0 2px #ef4444;
}

.stock-list-item.dirty {
  outline: 3px solid #1e40af;
}

.cell {
  min-height: 38px;
  padding: 3px 3px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  border-right: 1px solid rgba(0, 0, 0, 0.18);
}

.code-cell {
  background: #a7c9e5;
}

.process-cell {
  background: #f7a614;
}

.location-cell {
  background: #a7c9e5;
  position: relative;
}
.location-cell.other-area {
  background: #f87171;
}
.other-area-badge {
  position: absolute;
  right: 4px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  color: #fff;
  font-weight: bold;
}

.photo-cell {
  background: #f7a614;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.photo-cell img {
  max-width: 100%;
  max-height: 38px;
  object-fit: cover;
}

.list-photo img,
.confirm-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.list-arrow {
  grid-column: 5;
  grid-row: 1 / span 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  background: #f0f4f8;
}

.cell-label,
.cell-sub {
  font-size: 9px;
}

.cell-label {
  color: rgba(0, 0, 0, 0.72);
  margin-bottom: 1px;
}

.cell-value {
  font-size: 12px;
  line-height: 1.1;
  font-weight: 700;
}

.cell-value.code {
  font-size: 13px;
}

.cell-sub {
  margin-top: 3px;
  color: #334155;
}

.history-btn {
  position: relative;
  width: 20px;
  height: 20px;
  border: 1px solid #d9dfe7;
  background: #e0f2fe;
  color: #2563eb;
  font-size: 12px;
  line-height: 1;
  padding: 0;
  cursor: pointer;
}

.history-icon {
  font-size: 11px;
}

.history-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ef4444;
  color: #fff;
  font-size: 8px;
  font-weight: 700;
  min-width: 12px;
  height: 12px;
  line-height: 12px;
  border-radius: 6px;
  text-align: center;
  padding: 0 2px;
}

.arrow-btn {
  width: 20px;
  height: 24px;
  border: 1px solid #d9dfe7;
  background: #f8fafc;
  color: #f97316;
  font-size: 18px;
  line-height: 1;
}

.history-product-info {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e5e7eb;
}

.history-product-code {
  font-size: 15px;
  font-weight: 700;
  color: #15337a;
}

.history-product-name {
  font-size: 12px;
  color: #64748b;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.history-qty {
  font-size: 18px;
  font-weight: 700;
  color: #15337a;
  min-width: 60px;
  text-align: right;
}

.history-meta {
  flex: 1;
  font-size: 11px;
  color: #475569;
}

.history-time {
  font-size: 10px;
  color: #94a3b8;
}

.history-note {
  font-size: 10px;
  color: #64748b;
  margin-top: 2px;
}

.history-delete-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #ef4444;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
}

.recorder-icon-btn {
  border: none;
  background: transparent;
  color: #fff;
  font-size: 16px;
  cursor: pointer;
  padding: 0 0 0 4px;
  vertical-align: middle;
}

.recorder-select {
  flex: 1;
  min-width: 0;
  height: 30px;
  border: 1px solid #9ca3af;
  background: #fff;
  padding: 2px 4px;
  font-size: 12px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  width: 300px;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.people-modal {
  width: 380px;
}

.modal-header {
  padding: 10px 14px;
  font-size: 14px;
  font-weight: 700;
  background: #2f5eae;
  color: #fff;
}

.modal-body {
  padding: 12px 14px;
}

.modal-footer {
  padding: 8px 14px;
  text-align: right;
  border-top: 1px solid #e5e7eb;
}

.modal-footer button {
  border: 1px solid #9ca3af;
  background: #f8fafc;
  padding: 4px 16px;
  font-size: 12px;
  cursor: pointer;
}

.people-manage-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 12px;
}

.people-manage-tab {
  height: 30px;
  border: 1px solid #9ca3af;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.people-manage-tab.active {
  background: #2f5eae;
  border-color: #2f5eae;
  color: #fff;
}

.people-manage-panel {
  min-height: 180px;
}

.people-manage-title {
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 8px;
}

.recorder-add-row {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.recorder-add-row input {
  flex: 1;
  height: 28px;
  border: 1px solid #9ca3af;
  padding: 2px 6px;
  font-size: 12px;
}

.recorder-add-row button {
  height: 28px;
  border: 1px solid #2f5eae;
  background: #2f5eae;
  color: #fff;
  padding: 0 12px;
  font-size: 12px;
  cursor: pointer;
}

.recorder-add-row button:disabled {
  opacity: 0.5;
}

.recorder-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.empty-state.compact {
  padding: 12px 10px;
}

.recorder-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 13px;
}

.confirm-area {
  display: block;
  margin-top: 2px;
  padding: 0 3px;
}

.confirm-main {
  background: #a6d947;
  padding: 4px 6px 6px;
}

.confirm-main.preview {
  padding-bottom: 10px;
}

.confirm-head {
  display: grid;
  grid-template-columns: auto 1fr auto 1fr;
  gap: 4px 6px;
  align-items: end;
}

.confirm-title {
  font-size: 11px;
  font-weight: 700;
  color: #14240a;
  align-self: center;
}

.confirm-value-box {
  min-height: 28px;
  padding: 3px 5px;
  background: #ffffff;
  border: 1px solid #829299;
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
}

.confirm-photo {
  position: relative;
  min-height: 250px;
  margin-top: 6px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.position-badge {
  position: absolute;
  right: 8px;
  bottom: 6px;
  font-size: 16px;
  font-family: Georgia, serif;
  color: rgba(0, 0, 0, 0.55);
}

.empty-state {
  padding: 24px 10px;
  text-align: center;
  color: #64748b;
}

.negative,
.negative .qty-value,
.qty-box.negative .qty-value {
  color: #b42318;
}

.positive,
.qty-box.positive .qty-value {
  color: #0f766e;
}

.photo-placeholder {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: #94a3b8;
}

.photo-placeholder.large {
  min-height: 260px;
  width: 100%;
}

.detail-save:disabled,
.field-reset-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stocktake-detail-mobile {
  max-width: 600px;
  margin: 0 auto;
  min-height: 100vh;
  background: #ffffff;
  color: #1f2937;
  font-family: "Noto Sans JP", "Segoe UI", sans-serif;
  padding: 0 10px 16px;
}

.detail-header {
  display: grid;
  grid-template-columns: 36px 1fr 52px;
  align-items: center;
  min-height: 52px;
  background: #2f5eae;
  color: #ffffff;
}

.detail-back,
.detail-save {
  height: 52px;
  border: none;
  background: transparent;
  color: inherit;
  font-size: 16px;
}

.detail-back {
  font-size: 24px;
}

.detail-title {
  text-align: center;
  font-size: 15px;
  font-weight: 700;
}

.detail-body {
  padding: 8px 10px 0;
}

.detail-grid {
  display: grid;
  gap: 8px;
  margin-bottom: 6px;
}

.detail-grid.two {
  grid-template-columns: 1fr 1fr;
}

.detail-field {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #15337a;
  min-width: 0;
}

.detail-field span {
  min-width: 48px;
  white-space: nowrap;
  font-weight: 700;
}

.detail-field input {
  flex: 1;
  min-width: 0;
  height: 30px;
  border: 1px solid #9ca3af;
  background: #ffffff;
  padding: 2px 4px;
  font-size: 12px;
}

.detail-note {
  margin-top: 2px;
  margin-bottom: 8px;
}

.detail-photo-label {
  font-size: 11px;
  font-weight: 700;
  color: #15337a;
  margin-bottom: 6px;
}

.detail-photo {
  min-height: 320px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid #d1d5db;
}

.detail-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (max-width: 360px) {
  .search-grid {
    grid-template-columns: 1fr;
  }

  .confirm-head,
  .detail-grid.two {
    grid-template-columns: 1fr;
  }

  .stock-list-item {
    grid-template-columns: 1fr 42px;
    grid-template-rows: repeat(4, auto);
  }

  .code-cell,
  .process-cell,
  .location-cell,
  .photo-cell {
    grid-column: 1;
  }

  .code-cell { grid-row: 1; }
  .process-cell { grid-row: 2; }
  .location-cell { grid-row: 3; }
  .photo-cell {
    grid-row: 4;
    min-height: 120px;
  }

  .list-arrow {
    grid-column: 2;
    grid-row: 1 / span 4;
  }
}

.area-select {
  font-size: 13px;
  font-weight: 700;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.5);
  border-radius: 4px;
  color: #fff;
  padding: 2px 4px;
  max-width: 120px;
}
.area-select option { color: #1f2937; background: #fff; }

.area-modal { max-width: 440px; }
.area-create-box {
  margin-bottom: 10px;
}
.area-create-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.area-create-select,
.area-create-input {
  height: 30px;
  border: 1px solid #9ca3af;
  border-radius: 4px;
  background: #fff;
  padding: 2px 6px;
  font-size: 12px;
}
.area-create-select {
  width: 92px;
}
.area-create-select.wide,
.area-create-input {
  flex: 1;
}
.area-create-help {
  font-size: 11px;
  color: #64748b;
  line-height: 1.5;
}
.area-edit-name-row { display: flex; gap: 6px; margin-bottom: 8px; }
.area-edit-name-row input { flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
.btn-save { padding: 4px 12px; background: #16a34a; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.btn-save:disabled { opacity: 0.5; }
.btn-cancel { padding: 4px 12px; background: #6b7280; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.area-loc-title { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
.area-loc-chips { display: flex; flex-wrap: wrap; gap: 6px; max-height: 300px; overflow-y: auto; }
.area-loc-chip {
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  border-radius: 16px;
  font-size: 13px;
  cursor: pointer;
  background: #f3f4f6;
  transition: all 0.15s;
}
.area-loc-chip.selected {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

</style>
