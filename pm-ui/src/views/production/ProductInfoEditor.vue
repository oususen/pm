<template>
  <div class="editor-mobile" v-if="viewMode === 'list'">
    <header class="top-tabs">
      <span class="active">製品情報編集</span>
      <span></span>
      <span style="text-align:right;font-size:11px">{{ filteredRows.length }} 件</span>
    </header>

    <section class="search-strip">
      <div class="search-grid">
        <label class="search-block">
          <span class="search-label">ライン <button type="button" class="field-reset-btn" @click="filters.line_id = ''">クリア</button></span>
          <div class="search-input-wrap">
            <select v-model="filters.line_id">
              <option value="">すべて</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">
                {{ line.line_name || line.line_code }}
              </option>
            </select>
          </div>
        </label>
        <label class="search-block">
          <span class="search-label">置き場 <button type="button" class="field-reset-btn" @click="filters.stock_location = ''">クリア</button></span>
          <div class="search-input-wrap">
            <select v-model="filters.stock_location">
              <option value="">すべて</option>
              <option v-for="loc in locations" :key="loc" :value="loc">{{ loc }}</option>
            </select>
          </div>
        </label>
        <label class="search-block wide">
          <span class="search-label">品番検索 <button type="button" class="field-reset-btn" @click="filters.product_code = ''">クリア</button></span>
          <div class="search-input-wrap">
            <input v-model.trim="filters.product_code" type="text" placeholder="品番の一部を入力" />
          </div>
        </label>
        <label class="search-block">
          <span class="search-label">写真 <button type="button" class="field-reset-btn" @click="filters.has_image = ''">クリア</button></span>
          <div class="search-input-wrap">
            <select v-model="filters.has_image">
              <option value="">すべて</option>
              <option value="true">あり</option>
              <option value="false">なし</option>
            </select>
          </div>
        </label>
      </div>
    </section>

    <section class="candidate-list">
      <div v-if="loading" class="empty-state">読込中...</div>
      <div v-else-if="!hasFilter" class="empty-state">ライン・置き場・品番・写真のいずれかを選択してください</div>
      <div v-else-if="filteredRows.length === 0" class="empty-state">対象がありません</div>
      <div v-else class="list-stack">
        <article
          v-for="row in filteredRows"
          :key="row.id"
          class="stock-list-item"
          :class="{ active: selectedProductId === row.id }"
          @click="openDetail(row.id)"
        >
          <div class="cell code-cell">
            <div class="cell-label">品番:</div>
            <div class="cell-value code">{{ row.product_code }}</div>
            <div class="cell-sub">{{ row.product_name || '-' }}</div>
          </div>
          <div class="cell process-cell">
            <div class="cell-label">加工先</div>
            <div class="cell-value">{{ row.processing_area_label || '-' }}</div>
          </div>
          <div class="cell location-cell">
            <div class="cell-label">置き場:</div>
            <div class="cell-value">{{ formatLocations(row) }}</div>
          </div>
          <div class="cell photo-cell">
            <img v-if="row.image_url" :src="row.image_url" :alt="row.product_name" />
            <div v-else class="photo-placeholder">NO IMAGE</div>
          </div>
          <div class="list-arrow">
            <button type="button" class="arrow-btn" @click.stop="openDetail(row.id)">›</button>
          </div>
        </article>
      </div>
    </section>

  </div>

  <div v-else-if="viewMode === 'detail'" class="detail-mobile">
    <header class="detail-header">
      <button class="detail-back" type="button" @click="closeDetail">‹</button>
      <div class="detail-title">製品情報編集</div>
      <button class="detail-save" type="button" @click="saveProduct" :disabled="saving">
        {{ saving ? '保存中...' : '保存' }}
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

      <div class="detail-section-title">置き場</div>
      <div class="location-edit-list">
        <div v-for="(loc, i) in editLocations" :key="i" class="location-edit-row">
          <input v-model.trim="editLocations[i]" type="text" :placeholder="'置き場' + (i + 1)" class="location-input" />
          <button type="button" class="location-remove-btn" @click="removeLocation(i)">✕</button>
        </div>
        <button v-if="editLocations.length < 4" type="button" class="location-add-btn" @click="addLocation">+ 置き場追加</button>
      </div>

      <div class="detail-section-title">写真</div>
      <div class="photo-edit-area">
        <div class="current-photo">
          <img v-if="selectedRow.image_url" :src="selectedRow.image_url" :alt="selectedRow.product_name" />
          <div v-else class="photo-placeholder large">NO IMAGE</div>
        </div>
        <div class="photo-actions">
          <label class="photo-upload-btn">
            <input type="file" accept="image/*" capture="environment" @change="onPhotoSelected" hidden />
            撮影 / 選択
          </label>
          <span v-if="photoFile" class="photo-filename">{{ photoFile.name }}</span>
        </div>
        <div v-if="photoPreview" class="photo-preview">
          <div class="preview-label">新しい写真:</div>
          <img :src="photoPreview" alt="プレビュー" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import api from '@/api/client'

const viewMode = ref('list')
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const lines = ref([])
const locations = ref([])
const selectedProductId = ref(null)

const filters = ref({
  line_id: '',
  stock_location: '',
  product_code: '',
  has_image: '',
})

const editLocations = ref([])
const photoFile = ref(null)
const photoPreview = ref('')

const hasFilter = computed(() =>
  !!(filters.value.line_id || filters.value.stock_location || filters.value.product_code || filters.value.has_image)
)

const filteredRows = computed(() => {
  if (!hasFilter.value) return []
  let result = rows.value
  if (filters.value.product_code) {
    const kw = filters.value.product_code.toLowerCase()
    result = result.filter(r =>
      r.product_code.toLowerCase().includes(kw) || (r.product_name || '').toLowerCase().includes(kw)
    )
  }
  return result
})

const selectedRow = computed(() =>
  rows.value.find(r => r.id === selectedProductId.value) || null
)

const PROCESSING_AREA_LABELS = {
  LASER: 'レーザ', BRAKE: 'ブレーキ', NUT: 'ナット',
  WELD: '溶接', SPOT: 'スポット', ASSY: '組立', OTHER: 'その他',
}

const formatLocations = (row) => {
  const locs = row.stock_locations || []
  if (locs.length) return locs.map(l => typeof l === 'string' ? l : l.location_name).join(', ')
  return row.stock_location || '-'
}

const loadMasters = async () => {
  try {
    const [lineRes, locRes] = await Promise.all([
      api.lines.getLines({ page_size: 500 }),
      api.stocktakeRecords.list({ stocktake_date: new Date().toISOString().slice(0, 10), masters_only: 'true' }),
    ])
    lines.value = lineRes.data?.results || lineRes.data || []
    locations.value = locRes.data?.locations || []
  } catch (e) {
    console.error('マスタ取得エラー:', e)
  }
}

const loadProducts = async () => {
  loading.value = true
  try {
    const params = { is_active: true, page_size: 5000 }
    if (filters.value.line_id) params.line = filters.value.line_id
    if (filters.value.stock_location) params.stock_location = filters.value.stock_location
    if (filters.value.has_image !== '') params.has_image = filters.value.has_image === 'true'
    if (filters.value.product_code && !filters.value.line_id && !filters.value.stock_location) {
      params.search = filters.value.product_code
    }
    const res = await api.products.getProducts(params)
    const list = res.data?.results || res.data || []
    rows.value = list.map(p => ({
      ...p,
      stock_locations: p.stock_locations_list || [],
      processing_area_label: PROCESSING_AREA_LABELS[p.processing_area] || '',
    }))
  } catch (e) {
    console.error('製品取得エラー:', e)
    rows.value = []
  } finally {
    loading.value = false
  }
}

watch(() => [filters.value.line_id, filters.value.stock_location, filters.value.has_image], () => {
  if (filters.value.line_id || filters.value.stock_location || filters.value.has_image) loadProducts()
})

let searchTimer = null
watch(() => filters.value.product_code, (val) => {
  clearTimeout(searchTimer)
  if (val && val.length >= 2 && !filters.value.line_id && !filters.value.stock_location) {
    searchTimer = setTimeout(() => loadProducts(), 400)
  }
})

const openDetail = (productId) => {
  selectedProductId.value = productId
  const row = selectedRow.value
  if (row) {
    const locs = row.stock_locations || []
    editLocations.value = locs.length
      ? locs.map(l => typeof l === 'string' ? l : l.location_name)
      : (row.stock_location ? [row.stock_location] : [''])
  } else {
    editLocations.value = ['']
  }
  photoFile.value = null
  photoPreview.value = ''
  viewMode.value = 'detail'
}

const closeDetail = () => {
  viewMode.value = 'list'
}

const addLocation = () => {
  if (editLocations.value.length < 4) editLocations.value.push('')
}

const removeLocation = (i) => {
  const name = editLocations.value[i] || ''
  if (name && !confirm(`置き場「${name}」を削除しますか？`)) return
  editLocations.value.splice(i, 1)
  if (editLocations.value.length === 0) editLocations.value.push('')
}

const onPhotoSelected = (e) => {
  const file = e.target.files?.[0]
  if (!file) return
  photoFile.value = file
  const reader = new FileReader()
  reader.onload = (ev) => { photoPreview.value = ev.target.result }
  reader.readAsDataURL(file)
}

const saveProduct = async () => {
  if (!selectedRow.value) return
  saving.value = true
  try {
    const productId = selectedRow.value.id
    const locs = editLocations.value.filter(l => l.trim())
    await api.products.setStockLocations(productId, locs.map((name, i) => ({
      location_name: name.trim(),
      sort_order: i,
    })))

    if (photoFile.value) {
      const formData = new FormData()
      formData.append('file', photoFile.value)
      await api.products.uploadProductImage(productId, formData)
    }

    await loadProducts()
    photoFile.value = null
    photoPreview.value = ''
    const row = selectedRow.value
    if (row) {
      const locs2 = row.stock_locations || []
      editLocations.value = locs2.length
        ? locs2.map(l => typeof l === 'string' ? l : l.location_name)
        : (row.stock_location ? [row.stock_location] : [''])
    }
    alert('保存しました')
  } catch (e) {
    console.error('保存エラー:', e)
    alert('保存に失敗しました: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadMasters()
})
</script>

<style scoped>
.editor-mobile {
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
.top-tabs .active { text-align: left; color: #fff9cc; }
.search-strip { padding: 0; background: #9ccf39; }
.search-grid { display: grid; grid-template-columns: 1fr 1fr 1.35fr 0.8fr; gap: 0; }
.search-block { font-size: 9px; color: #23360a; min-width: 0; overflow: hidden; }
.search-label { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1px; }
.field-reset-btn { border: none; background: transparent; padding: 0; font-size: 10px; cursor: pointer; color: inherit; }
.search-input-wrap select,
.search-input-wrap input {
  width: 100%; box-sizing: border-box; border: 1px solid #8a9aa9; border-radius: 0;
  background: #fff; padding: 0 2px; font-size: 12px; height: 28px;
}
.candidate-list { padding: 0 3px; }
.list-stack { display: grid; gap: 4px; max-height: 60vh; overflow-y: auto; }
.stock-list-item {
  display: grid; grid-template-columns: 1.3fr 0.7fr 0.7fr 0.95fr 36px;
  gap: 0; padding: 0; background: transparent; border: 2px solid #f0f0f0; cursor: pointer;
}
.stock-list-item.active { border-color: #ffef9c; }
.cell {
  min-height: 38px; padding: 3px; display: flex; flex-direction: column;
  justify-content: center; border-right: 1px solid rgba(0,0,0,0.18);
}
.code-cell { background: #a7c9e5; }
.process-cell { background: #f7a614; }
.location-cell { background: #a7c9e5; }
.photo-cell { background: #f7a614; height: 38px; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.photo-cell img { max-width: 100%; max-height: 38px; object-fit: cover; }
.list-arrow { display: flex; align-items: center; justify-content: center; background: #f0f4f8; }
.arrow-btn { border: none; background: transparent; font-size: 26px; font-weight: 700; color: #6b7280; cursor: pointer; }
.cell-label, .cell-sub { font-size: 9px; }
.cell-label { color: rgba(0,0,0,0.72); margin-bottom: 1px; }
.cell-value { font-size: 12px; line-height: 1.1; font-weight: 700; }
.cell-value.code { font-size: 13px; }
.cell-sub { margin-top: 3px; color: #334155; }
.empty-state { padding: 24px 10px; text-align: center; color: #64748b; }
.photo-placeholder { font-size: 11px; letter-spacing: 0.12em; color: #94a3b8; font-weight: 700; }
.photo-placeholder.large { font-size: 16px; }

/* Detail mode */
.detail-mobile {
  max-width: 600px; margin: 0 auto; min-height: 100vh; background: #f5f5f0;
  font-family: "Noto Sans JP", "Segoe UI", sans-serif;
}
.detail-header {
  display: grid; grid-template-columns: 48px 1fr 72px; align-items: center;
  background: #87bf23; color: #fff; padding: 0; height: 44px;
}
.detail-back { border: none; background: transparent; color: #fff; font-size: 28px; cursor: pointer; text-align: center; }
.detail-title { font-size: 14px; font-weight: 700; text-align: center; }
.detail-save {
  border: none; background: #166534; color: #fff; font-size: 13px; font-weight: 700;
  padding: 6px 8px; border-radius: 4px; cursor: pointer; margin-right: 6px;
}
.detail-save:disabled { opacity: 0.5; cursor: not-allowed; }
.detail-body { padding: 10px; }
.detail-grid.two { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
.detail-field { display: flex; flex-direction: column; gap: 2px; }
.detail-field span { font-size: 11px; font-weight: 700; color: #374151; }
.detail-field input, .detail-field select {
  padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px;
  background: #fff;
}
.detail-field input[readonly] { background: #f3f4f6; color: #6b7280; }
.detail-section-title {
  font-size: 12px; font-weight: 700; color: #1f2937; margin: 12px 0 6px;
  padding-bottom: 3px; border-bottom: 2px solid #87bf23;
}
.location-edit-list { display: flex; flex-direction: column; gap: 6px; }
.location-edit-row { display: flex; gap: 6px; align-items: center; }
.location-input {
  flex: 1; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 13px;
}
.location-remove-btn {
  border: none; background: #fee2e2; color: #dc2626; width: 28px; height: 28px;
  border-radius: 4px; font-size: 14px; cursor: pointer;
}
.location-add-btn {
  border: 1px dashed #9ca3af; background: transparent; padding: 6px; border-radius: 4px;
  font-size: 12px; color: #4b5563; cursor: pointer; margin-top: 2px;
}
.photo-edit-area { margin-top: 6px; }
.current-photo {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; min-height: 200px;
  display: flex; align-items: center; justify-content: center; overflow: hidden;
}
.current-photo img { max-width: 100%; max-height: 350px; object-fit: contain; }
.photo-actions { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.photo-upload-btn {
  display: inline-block; padding: 8px 16px; background: #2563eb; color: #fff;
  border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer;
}
.photo-filename { font-size: 12px; color: #6b7280; }
.photo-preview { margin-top: 8px; }
.preview-label { font-size: 11px; font-weight: 700; color: #374151; margin-bottom: 4px; }
.photo-preview img {
  max-width: 100%; max-height: 250px; object-fit: contain; border: 2px solid #87bf23; border-radius: 6px;
}
</style>
