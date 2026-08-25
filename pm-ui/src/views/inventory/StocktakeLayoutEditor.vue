<template>
  <div class="layout-editor">
    <div class="editor-header">
      <h2 class="page-title">棚卸レイアウト編集
        <DataSourceDialog title="棚卸レイアウト" :sources="dsSources" />
      </h2>
      <div class="editor-actions">
        <select v-model="selectedAreaId" class="area-select" @change="onAreaChange">
          <option value="">エリアを選択</option>
          <option v-for="area in editableAreas" :key="area.id" :value="area.id">{{ area.name }}</option>
        </select>
        <select v-model="pdfPaperSize" class="paper-size-select">
          <option value="A4">A4</option>
          <option value="A3">A3</option>
        </select>
        <select v-model="pdfOrientation" class="paper-size-select">
          <option value="landscape">横</option>
          <option value="portrait">縦</option>
        </select>
        <button type="button" class="print-btn" @click="exportPdf" :disabled="!selectedAreaId || loading || pdfExporting || !canEditLayout">
          {{ pdfExporting ? 'PDF出力中...' : 'PDF出力' }}
        </button>
        <button type="button" class="save-btn" @click="saveConfig" :disabled="saving || !selectedAreaId || !selectedAreaEditable">{{ saving ? '保存中...' : '保存' }}</button>
      </div>
    </div>
    <div class="editor-notice">
      エリアを選択してから編集してください。エリアの作成・所属置き場の編集は
      <a href="/manual?path=在庫/棚卸現物入力.md" class="notice-link">「棚卸現物入力」画面</a>
      で行います。
      <template v-if="!canEditLayout">
        この画面は閲覧できますが、保存には「在庫: 棚卸レイアウト」の編集権限が必要です。
      </template>
    </div>

    <div class="editor-body">
      <div class="editor-sidebar">
        <div class="sidebar-section">
          <div class="sidebar-title">グリッド設定</div>
          <div class="grid-size-row">
            <label class="size-label">列数<input type="number" v-model.number="cols" min="2" max="30" class="size-input" /></label>
            <label class="size-label">行数<input type="number" v-model.number="rowCount" min="2" max="30" class="size-input" /></label>
          </div>
        </div>

        <div class="sidebar-section" v-if="selectedLocation">
          <div class="sidebar-title">配置中</div>
          <div class="placing-info">
            <strong>{{ selectedLocation }}</strong>
            <span v-if="placingType === 'equipment'" class="type-badge equip">設備</span>
            <span v-else class="type-badge loc">置き場</span>
          </div>
          <div class="span-row">
            <label class="size-label">横<input type="number" v-model.number="placingW" min="1" :max="cols" class="size-input" /></label>
            <label class="size-label">縦<input type="number" v-model.number="placingH" min="1" :max="rowCount" class="size-input" /></label>
          </div>
          <div class="placing-hint">グリッドのマスをクリックして配置</div>
          <button type="button" class="cancel-btn" @click="selectedLocation = null">取消</button>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">置き場</div>
          <div v-if="unplacedLocations.length > 0" class="palette-list">
            <button
              v-for="loc in unplacedLocations"
              :key="loc"
              type="button"
              class="palette-item"
              :class="{ selected: selectedLocation === loc && placingType === 'location' }"
              @click="selectLocation(loc)"
            >{{ loc }}</button>
          </div>
          <div v-else class="palette-empty">すべて配置済み</div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">設備</div>
          <div class="equip-add-row">
            <input v-model.trim="equipName" type="text" placeholder="設備名" class="equip-input" @keyup.enter="addEquipment" />
            <button type="button" class="equip-add-btn" @click="addEquipment" :disabled="!equipName">追加</button>
          </div>
          <div v-if="equipmentList.length > 0" class="palette-list">
            <button
              v-for="eq in equipmentList"
              :key="'eq-' + eq"
              type="button"
              class="palette-item palette-item-equip"
              :class="{ selected: selectedLocation === eq && placingType === 'equipment', placed: placedEquipSet.has(eq) }"
              @click="selectEquipment(eq)"
            >{{ eq }}</button>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-title">ズーム</div>
          <div class="zoom-row">
            <button type="button" class="zoom-btn" @click="zoomOut">−</button>
            <span class="zoom-val">{{ Math.round(zoom * 100) }}%</span>
            <button type="button" class="zoom-btn" @click="zoomIn">+</button>
          </div>
        </div>
      </div>

      <div class="editor-main">
        <div class="grid-scroll">
          <div
            class="grid-map"
            :style="{
              gridTemplateColumns: `repeat(${cols}, 48px)`,
              gridTemplateRows: `repeat(${rowCount}, 48px)`,
              transform: `scale(${zoom})`,
              transformOrigin: 'top left',
            }"
          >
            <template v-for="cellKey in cellKeys" :key="cellKey">
              <div
                v-if="!occupiedCells.has(cellKey)"
                class="grid-cell"
                :class="[gridCellClass(cellKey), { vertical: isVerticalCell(cellKey) }]"
                :style="gridCellStyle(cellKey)"
                @click="onCellClick(cellKey)"
              >
                <template v-if="cells[cellKey]">
                  <div class="cell-label" :class="{ vertical: isVerticalCell(cellKey) }" :style="getCellFontStyle(cellKey)">{{ getCellLocation(cellKey) }}</div>
                  <div class="cell-type-indicator" v-if="getCellType(cellKey) === 'equipment'">設備</div>
                  <div class="cell-edit-hint">クリックで編集</div>
                </template>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div v-if="editingCellKey" class="modal-overlay" @click.self="editingCellKey = null">
      <div class="edit-modal">
        <div class="edit-modal-header">セル編集</div>
        <div class="edit-modal-body">
          <label class="edit-field">
            <span class="edit-field-label">名前</span>
            <input type="text" v-model.trim="editCellName" class="edit-field-input" />
          </label>
          <div class="edit-field-row">
            <label class="edit-field">
              <span class="edit-field-label">横幅</span>
              <input type="number" v-model.number="editCellW" min="1" :max="cols" class="edit-field-input short" />
            </label>
            <label class="edit-field">
              <span class="edit-field-label">縦幅</span>
              <input type="number" v-model.number="editCellH" min="1" :max="rowCount" class="edit-field-input short" />
            </label>
          </div>
          <div class="edit-field">
            <span class="edit-field-label">種別</span>
            <div class="edit-type-row">
              <button type="button" class="edit-type-btn" :class="{ active: editCellType === 'location' }" @click="editCellType = 'location'">置き場</button>
              <button type="button" class="edit-type-btn equip" :class="{ active: editCellType === 'equipment' }" @click="editCellType = 'equipment'">設備</button>
            </div>
          </div>
          <div class="edit-field">
            <span class="edit-field-label">色</span>
            <div class="color-palette">
              <button
                v-for="c in colorOptions"
                :key="c.value"
                type="button"
                class="color-swatch"
                :class="{ selected: editCellColor === c.value }"
                :style="{ background: c.bg, borderColor: c.border }"
                :title="c.label"
                @click="editCellColor = c.value"
              ></button>
            </div>
          </div>
          <div class="edit-field">
            <span class="edit-field-label">文字サイズ</span>
            <div class="font-size-row">
              <button v-for="fs in fontSizeOptions" :key="fs.value" type="button" class="font-size-btn" :class="{ active: editCellFontSize === fs.value }" @click="editCellFontSize = fs.value">{{ fs.label }}</button>
            </div>
          </div>
        </div>
        <div class="edit-modal-footer">
          <button type="button" class="edit-delete-btn" @click="deleteEditingCell">削除</button>
          <div class="edit-modal-spacer"></div>
          <button type="button" class="edit-cancel-btn" @click="editingCellKey = null">キャンセル</button>
          <button type="button" class="edit-save-btn" @click="saveEditingCell">適用</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "@/api/client";
import { authState } from "@/auth";
import { hasPermission } from "@/router";
import DataSourceDialog from '@/components/DataSourceDialog.vue'
import {
  buildStocktakeLayoutPdfBlob,
  createStocktakeLayoutPdfFileName,
  downloadStocktakeLayoutPdf,
} from '@/utils/stocktakeLayoutPdf'

const cols = ref(8);
const rowCount = ref(6);
const cells = ref({});
const selectedLocation = ref(null);
const placingType = ref("location");
const placingW = ref(1);
const placingH = ref(1);
const zoom = ref(1);
const equipName = ref("");
const saving = ref(false);
const loading = ref(false);
const pdfExporting = ref(false);
const allLocations = ref([]);
const equipmentList = ref([]);
const areas = ref([]);
const selectedAreaId = ref("");
const pdfPaperSize = ref("A4");
const pdfOrientation = ref("landscape");
const dsSources = [
  { op: '取得/保存', table: 'production_stocktake_layout_config', desc: 'レイアウト配置設定（エリア別グリッド・セル配置）' },
  { op: '取得', table: 'production_stocktake_area', desc: '棚卸エリア（置き場のグルーピング）' },
  { op: '取得', table: 'production_stocktake_record', desc: '棚卸現物入力記録（進捗表示用）' },
  { op: '取得', table: 'm_product_stock_location', desc: '製品別置き場マスタ（配置候補一覧）' },
]
const editingCellKey = ref(null);
const editCellName = ref("");
const editCellW = ref(1);
const editCellH = ref(1);
const editCellType = ref("location");
const editCellColor = ref("");
const editCellFontSize = ref("");
const canViewLayout = computed(() => hasPermission(authState.user, "stocktake.layout", "view"));
const canEditLayout = computed(() => hasPermission(authState.user, "stocktake.layout", "edit"));
const editableAreas = computed(() => areas.value);
const selectedAreaEditable = computed(() => canEditLayout.value);
const selectedArea = computed(() =>
  areas.value.find((area) => String(area.id) === String(selectedAreaId.value)) || null
);

const fontSizeOptions = [
  { value: "", label: "標準" },
  { value: "8", label: "8" },
  { value: "10", label: "10" },
  { value: "12", label: "12" },
  { value: "14", label: "14" },
  { value: "16", label: "16" },
  { value: "20", label: "20" },
];

const colorOptions = [
  { value: "", label: "デフォルト", bg: "#e5e7eb", border: "#d1d5db" },
  { value: "red", label: "赤", bg: "#fecaca", border: "#f87171" },
  { value: "orange", label: "オレンジ", bg: "#fed7aa", border: "#fb923c" },
  { value: "yellow", label: "黄", bg: "#fef08a", border: "#facc15" },
  { value: "green", label: "緑", bg: "#bbf7d0", border: "#4ade80" },
  { value: "blue", label: "青", bg: "#bfdbfe", border: "#60a5fa" },
  { value: "purple", label: "紫", bg: "#ddd6fe", border: "#a78bfa" },
  { value: "pink", label: "ピンク", bg: "#fbcfe8", border: "#f472b6" },
  { value: "brown", label: "茶", bg: "#d7ccc8", border: "#a1887f" },
];

const zoomIn = () => { zoom.value = Math.min(2, +(zoom.value + 0.2).toFixed(1)); };
const zoomOut = () => { zoom.value = Math.max(0.3, +(zoom.value - 0.2).toFixed(1)); };

const cellKeys = computed(() => {
  const keys = [];
  for (let r = 0; r < rowCount.value; r++) {
    for (let c = 0; c < cols.value; c++) {
      keys.push(`${r}-${c}`);
    }
  }
  return keys;
});

const getCellLocation = (cellKey) => {
  const cell = cells.value[cellKey];
  if (!cell) return null;
  return typeof cell === "string" ? cell : cell.location;
};

const getCellType = (cellKey) => {
  const cell = cells.value[cellKey];
  if (!cell) return null;
  if (typeof cell === "string") return "location";
  return cell.type || "location";
};

const occupiedCells = computed(() => {
  const set = new Set();
  for (const [key, cell] of Object.entries(cells.value)) {
    if (!cell) continue;
    const [r, c] = key.split("-").map(Number);
    const w = typeof cell === "string" ? 1 : (cell.w || 1);
    const h = typeof cell === "string" ? 1 : (cell.h || 1);
    for (let dr = 0; dr < h; dr++) {
      for (let dc = 0; dc < w; dc++) {
        if (dr === 0 && dc === 0) continue;
        set.add(`${r + dr}-${c + dc}`);
      }
    }
  }
  return set;
});

const placedLocationSet = computed(() => {
  const set = new Set();
  for (const cell of Object.values(cells.value)) {
    if (!cell) continue;
    const type = typeof cell === "string" ? "location" : (cell.type || "location");
    if (type === "location") set.add(typeof cell === "string" ? cell : cell.location);
  }
  return set;
});

const placedEquipSet = computed(() => {
  const set = new Set();
  for (const cell of Object.values(cells.value)) {
    if (!cell || typeof cell === "string") continue;
    if (cell.type === "equipment") set.add(cell.location);
  }
  return set;
});

const unplacedLocations = computed(() =>
  allLocations.value.filter((loc) => !placedLocationSet.value.has(loc))
);

const colorMap = {
  red: { bg: "#fecaca", border: "#f87171" },
  orange: { bg: "#fed7aa", border: "#fb923c" },
  yellow: { bg: "#fef08a", border: "#facc15" },
  green: { bg: "#bbf7d0", border: "#4ade80" },
  blue: { bg: "#bfdbfe", border: "#60a5fa" },
  purple: { bg: "#ddd6fe", border: "#a78bfa" },
  pink: { bg: "#fbcfe8", border: "#f472b6" },
  brown: { bg: "#d7ccc8", border: "#a1887f" },
};

const gridCellStyle = (cellKey) => {
  const cell = cells.value[cellKey];
  const [r, c] = cellKey.split("-").map(Number);
  const style = { gridRow: `${r + 1}`, gridColumn: `${c + 1}` };
  if (cell) {
    const w = typeof cell === "string" ? 1 : (cell.w || 1);
    const h = typeof cell === "string" ? 1 : (cell.h || 1);
    if (w > 1) style.gridColumn = `${c + 1} / span ${w}`;
    if (h > 1) style.gridRow = `${r + 1} / span ${h}`;
    const clr = typeof cell === "string" ? "" : (cell.color || "");
    if (clr && colorMap[clr]) {
      style.background = colorMap[clr].bg;
      style.borderColor = colorMap[clr].border;
    }
  }
  return style;
};

const gridCellClass = (cellKey) => {
  const loc = getCellLocation(cellKey);
  if (!loc) return "cell-empty";
  if (getCellType(cellKey) === "equipment") return "cell-equipment";
  return "cell-location";
};

const isVerticalCell = (cellKey) => {
  const cell = cells.value[cellKey];
  if (!cell || typeof cell === "string") return false;
  return (cell.h || 1) > (cell.w || 1);
};

const getCellFontStyle = (cellKey) => {
  const cell = cells.value[cellKey];
  if (!cell || typeof cell === "string") return {};
  const fs = cell.fontSize;
  if (!fs) return {};
  return { fontSize: `${fs}px` };
};

const canPlace = (r, c, w, h) => {
  for (let dr = 0; dr < h; dr++) {
    for (let dc = 0; dc < w; dc++) {
      const k = `${r + dr}-${c + dc}`;
      if (r + dr >= rowCount.value || c + dc >= cols.value) return false;
      if (cells.value[k] || occupiedCells.value.has(k)) return false;
    }
  }
  return true;
};

const selectLocation = (loc) => {
  selectedLocation.value = loc;
  placingType.value = "location";
  placingW.value = 1;
  placingH.value = 1;
};

const selectEquipment = (eq) => {
  selectedLocation.value = eq;
  placingType.value = "equipment";
  placingW.value = 1;
  placingH.value = 1;
};

const addEquipment = () => {
  if (!equipName.value) return;
  if (!equipmentList.value.includes(equipName.value)) {
    equipmentList.value.push(equipName.value);
  }
  selectedLocation.value = equipName.value;
  placingType.value = "equipment";
  placingW.value = 1;
  placingH.value = 1;
  equipName.value = "";
};

const openCellEditor = (cellKey) => {
  const cell = cells.value[cellKey];
  if (!cell) return;
  editingCellKey.value = cellKey;
  editCellName.value = typeof cell === "string" ? cell : cell.location;
  editCellW.value = typeof cell === "string" ? 1 : (cell.w || 1);
  editCellH.value = typeof cell === "string" ? 1 : (cell.h || 1);
  editCellType.value = typeof cell === "string" ? "location" : (cell.type || "location");
  editCellColor.value = typeof cell === "string" ? "" : (cell.color || "");
  editCellFontSize.value = typeof cell === "string" ? "" : (cell.fontSize || "");
};

const saveEditingCell = () => {
  const key = editingCellKey.value;
  if (!key || !editCellName.value) return;
  const oldCell = cells.value[key];
  const oldW = typeof oldCell === "string" ? 1 : (oldCell.w || 1);
  const oldH = typeof oldCell === "string" ? 1 : (oldCell.h || 1);
  const newW = editCellW.value;
  const newH = editCellH.value;
  if (newW !== oldW || newH !== oldH) {
    const [r, c] = key.split("-").map(Number);
    const tempCells = { ...cells.value };
    delete tempCells[key];
    const tempOccupied = new Set();
    for (const [k, v] of Object.entries(tempCells)) {
      if (!v) continue;
      const [kr, kc] = k.split("-").map(Number);
      const tw = typeof v === "string" ? 1 : (v.w || 1);
      const th = typeof v === "string" ? 1 : (v.h || 1);
      for (let dr = 0; dr < th; dr++) {
        for (let dc = 0; dc < tw; dc++) {
          if (dr === 0 && dc === 0) continue;
          tempOccupied.add(`${kr + dr}-${kc + dc}`);
        }
      }
    }
    for (let dr = 0; dr < newH; dr++) {
      for (let dc = 0; dc < newW; dc++) {
        if (dr === 0 && dc === 0) continue;
        const ck = `${r + dr}-${c + dc}`;
        if (r + dr >= rowCount.value || c + dc >= cols.value || tempCells[ck] || tempOccupied.has(ck)) {
          alert("このサイズでは他のセルと重なります");
          return;
        }
      }
    }
  }
  cells.value = {
    ...cells.value,
    [key]: { location: editCellName.value, w: newW, h: newH, type: editCellType.value, color: editCellColor.value, fontSize: editCellFontSize.value },
  };
  editingCellKey.value = null;
};

const deleteEditingCell = () => {
  if (editingCellKey.value) {
    removeCell(editingCellKey.value);
    editingCellKey.value = null;
  }
};

const onCellClick = (cellKey) => {
  if (cells.value[cellKey]) {
    openCellEditor(cellKey);
    return;
  }
  if (!selectedLocation.value) return;
  if (occupiedCells.value.has(cellKey)) return;
  const [r, c] = cellKey.split("-").map(Number);
  const w = placingW.value;
  const h = placingH.value;
  if (!canPlace(r, c, w, h)) {
    alert("この位置にはこのサイズで配置できません");
    return;
  }
  cells.value = {
    ...cells.value,
    [cellKey]: { location: selectedLocation.value, w, h, type: placingType.value },
  };
  selectedLocation.value = null;
};

const removeCell = (cellKey) => {
  const cell = cells.value[cellKey];
  if (cell && typeof cell !== "string" && cell.type === "equipment") {
    const loc = cell.location;
    const stillUsed = Object.entries(cells.value).some(
      ([k, v]) => k !== cellKey && v && typeof v !== "string" && v.type === "equipment" && v.location === loc
    );
    if (!stillUsed) {
      equipmentList.value = equipmentList.value.filter((e) => e !== loc);
    }
  }
  const newCells = { ...cells.value };
  delete newCells[cellKey];
  cells.value = newCells;
};

const loadConfig = async () => {
  if (!selectedAreaId.value || !canViewLayout.value) {
    cols.value = 8;
    rowCount.value = 6;
    cells.value = {};
    equipmentList.value = [];
    selectedLocation.value = null;
    return;
  }
  loading.value = true;
  try {
    const params = { area_id: selectedAreaId.value };
    const res = await api.stocktakeRecords.getLayoutConfig(params);
    cols.value = res.data.cols || 8;
    rowCount.value = res.data.rows || 6;
    const raw = res.data.cells || {};
    const converted = {};
    const eqSet = new Set();
    for (const [key, val] of Object.entries(raw)) {
      const cell = typeof val === "string" ? { location: val, w: 1, h: 1, type: "location" } : val;
      converted[key] = cell;
      if (cell.type === "equipment") eqSet.add(cell.location);
    }
    cells.value = converted;
    equipmentList.value = [...eqSet].sort();
  } catch (e) {
    console.error("レイアウト設定取得エラー:", e);
  }
  loading.value = false;
};

const loadLocations = async () => {
  if (!selectedAreaId.value || !canViewLayout.value) {
    allLocations.value = [];
    return;
  }
  const area = areas.value.find((item) => String(item.id) === String(selectedAreaId.value));
  allLocations.value = Array.isArray(area?.locations) ? [...area.locations].sort((a, b) => a.localeCompare(b, 'ja')) : [];
};

const saveConfig = async () => {
  if (!selectedAreaId.value) {
    alert("先にエリアを選択してください");
    return;
  }
  if (!canEditLayout.value) {
    alert("このエリアは変更できません");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      cols: cols.value,
      rows: rowCount.value,
      cells: cells.value,
      area_id: selectedAreaId.value,
    };
    await api.stocktakeRecords.saveLayoutConfig(payload);

    const layoutLocs = [];
    for (const cell of Object.values(cells.value)) {
      if (!cell) continue;
      const type = typeof cell === "string" ? "location" : (cell.type || "location");
      if (type === "location") {
        const name = typeof cell === "string" ? cell : cell.location;
        if (name && !layoutLocs.includes(name)) layoutLocs.push(name);
      }
    }
    const area = areas.value.find(a => a.id === Number(selectedAreaId.value));
    if (area) {
      const merged = [...new Set([...area.locations, ...layoutLocs])];
      await api.stocktakeRecords.saveArea({ id: area.id, name: area.name, locations: merged });
      await loadAreas();
      await loadLocations();
    }

    alert("保存しました");
  } catch (e) {
    console.error("保存エラー:", e);
    alert("保存に失敗しました");
  }
  saving.value = false;
};

const loadAreas = async () => {
  try {
    const res = await api.stocktakeRecords.listAreas();
    areas.value = Array.isArray(res.data?.areas) ? res.data.areas : [];
    if (selectedAreaId.value && !areas.value.some((area) => String(area.id) === String(selectedAreaId.value))) {
      selectedAreaId.value = "";
    }
  } catch (e) {
    console.error("エリア取得エラー:", e);
  }
};

const onAreaChange = () => {
  selectedLocation.value = null;
  loadLocations();
  loadConfig();
};

const exportPdf = async () => {
  if (!selectedAreaId.value) {
    alert("先にエリアを選択してください");
    return;
  }
  if (!canEditLayout.value) {
    alert("PDF出力する権限がありません");
    return;
  }
  if (loading.value || pdfExporting.value) return;
  editingCellKey.value = null;
  selectedLocation.value = null;
  pdfExporting.value = true;
  try {
    const blob = await buildStocktakeLayoutPdfBlob({
      areaName: selectedArea.value?.name || '',
      paperSize: pdfPaperSize.value,
      orientation: pdfOrientation.value,
      cols: cols.value,
      rows: rowCount.value,
      cells: cells.value,
    });
    const fileName = createStocktakeLayoutPdfFileName({
      areaName: selectedArea.value?.name || '',
      paperSize: `${pdfPaperSize.value}_${pdfOrientation.value === 'portrait' ? '縦' : '横'}`,
    });
    downloadStocktakeLayoutPdf({ blob, fileName });
  } catch (e) {
    console.error("棚卸レイアウトPDF出力エラー:", e);
    alert("PDF出力に失敗しました");
  } finally {
    pdfExporting.value = false;
  }
};

onMounted(async () => {
  await loadAreas();
  await loadLocations();
  await loadConfig();
});
</script>

<style scoped>
.layout-editor {
  padding: 12px 16px;
  min-height: 100%;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.editor-notice {
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
  border-radius: 8px;
  font-size: 13px;
}

.notice-link {
  color: #1d4ed8;
  font-weight: 700;
  text-decoration: underline;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.area-select {
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
}

.paper-size-select {
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
}

.save-btn {
  padding: 6px 20px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.print-btn {
  padding: 6px 16px;
  background: #fff;
  color: #1f2937;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.print-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.editor-body {
  display: flex;
  gap: 16px;
}

.editor-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
}

.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: #374151;
  margin-bottom: 6px;
}

.grid-size-row, .span-row {
  display: flex;
  gap: 8px;
}

.size-label {
  font-size: 12px;
  color: #4b5563;
  display: flex;
  align-items: center;
  gap: 4px;
}

.size-input {
  width: 50px;
  padding: 3px 6px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 12px;
}

.placing-info {
  font-size: 13px;
  margin-bottom: 6px;
}

.type-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  margin-left: 4px;
}

.type-badge.loc {
  background: #dbeafe;
  color: #1e40af;
}

.type-badge.equip {
  background: #6366f1;
  color: #fff;
}

.placing-hint {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 6px;
}

.cancel-btn {
  padding: 3px 12px;
  border: 1px solid #ef4444;
  background: #fff;
  color: #ef4444;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.palette-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.palette-item {
  padding: 3px 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  font-size: 11px;
  cursor: pointer;
  border-radius: 4px;
}

.palette-item:hover {
  background: #f1f5f9;
}

.palette-item.selected {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.palette-item.placed {
  opacity: 0.4;
}

.palette-item-equip {
  background: #eef2ff;
  border-color: #a5b4fc;
}

.palette-item-equip.selected {
  background: #6366f1;
  border-color: #6366f1;
}

.palette-empty {
  font-size: 11px;
  color: #9ca3af;
}

.equip-add-row {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}

.equip-input {
  flex: 1;
  padding: 3px 6px;
  font-size: 11px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.equip-add-btn {
  padding: 3px 10px;
  font-size: 11px;
  border: none;
  background: #6366f1;
  color: #fff;
  border-radius: 4px;
  cursor: pointer;
}

.equip-add-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.zoom-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.zoom-btn {
  width: 28px;
  height: 28px;
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

.zoom-val {
  font-size: 12px;
  min-width: 36px;
  text-align: center;
}

.editor-main {
  flex: 1;
  min-width: 0;
}

.grid-scroll {
  overflow: auto;
  max-height: calc(100vh - 120px);
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
}

.grid-map {
  display: grid;
  gap: 2px;
  width: max-content;
}

.grid-cell {
  position: relative;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  min-height: 48px;
}

.cell-empty {
  background: #f0f9ff;
  border: 1px dashed #93c5fd;
}

.cell-empty:hover {
  background: #dbeafe;
}

.cell-location {
  background: #e5e7eb;
  border: 1px solid #d1d5db;
}

.cell-equipment {
  background: #c7d2fe;
  border: 1px solid #6366f1;
}

.cell-label {
  font-size: 10px;
  font-weight: 700;
  color: #1f2937;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
  padding: 0 2px;
}

.cell-label.vertical {
  writing-mode: vertical-rl;
  white-space: normal;
  width: auto;
  text-overflow: clip;
}

.cell-remove {
  position: absolute;
  top: 1px;
  right: 1px;
  border: none;
  background: #ef4444;
  color: #fff;
  width: 14px;
  height: 14px;
  font-size: 9px;
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
}

.grid-cell:hover .cell-remove {
  opacity: 1;
}

.cell-type-indicator {
  font-size: 8px;
  color: #6366f1;
  font-weight: 600;
}

.cell-edit-hint {
  font-size: 7px;
  color: #9ca3af;
  opacity: 0;
}

.grid-cell:hover .cell-edit-hint {
  opacity: 1;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.edit-modal {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
  width: 320px;
}

.edit-modal-header {
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 700;
  border-bottom: 1px solid #e5e7eb;
}

.edit-modal-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.edit-field {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.edit-field-label {
  font-size: 11px;
  font-weight: 600;
  color: #4b5563;
}

.edit-field-input {
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  font-size: 13px;
}

.edit-field-input.short {
  width: 70px;
}

.edit-field-row {
  display: flex;
  gap: 12px;
}

.edit-type-row {
  display: flex;
  gap: 6px;
}

.edit-type-btn {
  padding: 4px 14px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}

.edit-type-btn.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

.edit-type-btn.equip.active {
  background: #6366f1;
  border-color: #6366f1;
}

.edit-modal-footer {
  padding: 10px 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 8px;
}

.edit-modal-spacer {
  flex: 1;
}

.edit-delete-btn {
  padding: 5px 14px;
  border: 1px solid #ef4444;
  background: #fff;
  color: #ef4444;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}

.edit-cancel-btn {
  padding: 5px 14px;
  border: 1px solid #d1d5db;
  background: #fff;
  color: #374151;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
}

.edit-save-btn {
  padding: 5px 14px;
  border: none;
  background: #2563eb;
  color: #fff;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.color-palette {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.color-swatch {
  width: 24px;
  height: 24px;
  border: 2px solid;
  border-radius: 5px;
  cursor: pointer;
  padding: 0;
}

.color-swatch.selected {
  outline: 2px solid #2563eb;
  outline-offset: 1px;
}

.font-size-row {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.font-size-btn {
  padding: 3px 8px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  min-width: 32px;
  text-align: center;
}

.font-size-btn.active {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}

</style>
