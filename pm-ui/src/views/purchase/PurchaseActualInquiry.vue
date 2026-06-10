<template>
  <div class="page">
    <h2 class="page-title">納入実績照会</h2>

    <div class="tab-bar">
      <button class="tab-item" :class="{ active: activeTab === 'inquiry' }" @click="activeTab = 'inquiry'">照会</button>
      <button class="tab-item" :class="{ active: activeTab === 'mapping' }" @click="activeTab = 'mapping'">マッピング設定</button>
    </div>

    <!-- ====== 照会タブ ====== -->
    <div v-show="activeTab === 'inquiry'">
      <div class="filters">
        <label>開始日 <input v-model="startDate" type="date" /></label>
        <label>終了日 <input v-model="endDate" type="date" /></label>
        <label>品番 <input v-model.trim="productCode" type="text" /></label>
        <label>仕入先
          <select v-model="filterSupplierId">
            <option value="">-- すべて --</option>
            <option v-for="s in suppliers" :key="s.id" :value="String(s.id)">
              {{ s.supplier_code }} {{ s.supplier_name }}
            </option>
          </select>
        </label>
        <button class="btn" :disabled="loading" @click="load">検索</button>
        <button
          class="btn btn-secondary"
          :disabled="loading || !rows.length"
          @click="onExportKikan"
        >基幹システム入力用Excel</button>
      </div>

      <div class="table-wrap">
        <table class="list-table">
          <thead>
            <tr>
              <th>納入日</th>
              <th>品番</th>
              <th>品名</th>
              <th>購入先</th>
              <th class="num">数量</th>
              <th>入力者</th>
              <th class="num">ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>{{ formatDate(row.delivery_date) }}</td>
              <td>{{ row.product_code }}</td>
              <td>{{ row.product_name }}</td>
              <td>{{ row.supplier }}</td>
              <td class="num">{{ formatNum(row.qty) }}</td>
              <td>{{ row.operator_name }}</td>
              <td class="num">{{ row.id }}</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="7" class="no-data">データがありません</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ====== マッピング設定タブ ====== -->
    <div v-show="activeTab === 'mapping'" class="settings-panel">
      <h3 class="settings-title">マッピング設定</h3>
      <div class="settings-note">
        <strong>注意ポイント</strong>
        <ul>
          <li>仕入先を選択したあと、各アプリ品番ごとに基幹品番・品目区分(G/K)・仕入先コード・品番後Tab回数を設定してください。</li>
          <li>品目区分は G=外作、K=購入品です。（外作、購入品は基幹システム上のがいねんである）自動入力処理では G は工程テーブル待ち、K は通常画面遷移待ちになります。</li>
          <li>品番後Tab回数は「品番入力後、仕入先コードまでに押すTabの合計回数」です。HCE0040実装では G　1か所=1、G　2か所=3、K=1 です。</li>
          <li>仕入先コードは６桁入力、例　ゼンツーの場合　000095と入力してください。入荷数後のTab回数は自動設定される。</li>
          <li>画面からマッピング設定してもいいし、テンプレを出力してEXCELで作りしてから導入することもできる。</li>
        </ul>
      </div>

      <div class="settings-selector">
        <label>仕入先</label>
        <select v-model="mappingSupplier" @change="onMappingSupplierChange">
          <option value="">-- 選択 --</option>
          <option v-for="s in suppliers" :key="s.id" :value="String(s.id)">
            {{ s.supplier_code }} {{ s.supplier_name }}
          </option>
        </select>
      </div>

      <div v-if="mappingLoading" class="settings-info">読込中...</div>
      <div v-else-if="mappingError" class="settings-error">{{ mappingError }}</div>

      <div class="settings-actions">
        <button class="btn" :disabled="!mappingSupplier || mappingLoading" @click="saveMappings">保存</button>
        <button class="btn btn-secondary" :disabled="!mappingSupplier || mappingLoading" @click="downloadMappingTemplate">テンプレ出力</button>
        <label class="btn btn-secondary" :class="{ disabled: !mappingSupplier || mappingLoading }">
          Excelから導入
          <input ref="importFileRef" type="file" accept=".xlsx,.xls" style="display:none" @change="onImportExcel" />
        </label>
      </div>
      <div v-if="mappingSaveMsg" class="settings-message">{{ mappingSaveMsg }}</div>

      <div v-if="mappingSupplier" class="table-wrap settings-table-wrap">
        <table class="list-table mapping-table">
          <thead>
            <tr>
              <th>アプリ品番</th>
              <th>品名</th>
              <th>品目区分</th>
              <th>基幹品番</th>
              <th>仕入先コード<br><small>加工先CD(G) / 仕入先コード(K)</small></th>
              <th>品番後Tab回数<br><small>G1か所=1、G2か所=3、K=1</small></th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in mappingRows" :key="idx">
              <td>{{ item.appProductCode }}</td>
              <td>{{ item.productName }}</td>
              <td>
                <select v-model="item.itemType" class="map-select">
                  <option value="">-- 未設定 --</option>
                  <option value="G">G（外作）</option>
                  <option value="K">K（購入）</option>
                </select>
              </td>
              <td>
                <input v-model="item.coreProductCode" type="text" class="map-input" placeholder="基幹品番" />
              </td>
              <td>
                <input v-model="item.supplierCode" type="text" class="map-input" placeholder="例: 000095" />
              </td>
              <td>
                <input v-model.number="item.tabsAfterHinban" type="number" class="map-input map-input-narrow" min="1" max="10" />
              </td>
              <td>
                <button class="btn btn-secondary btn-sm" @click="copyCode(item)">コピー</button>
              </td>
            </tr>
            <tr v-if="!mappingRows.length">
              <td colspan="7" class="no-data">品番がありません（先に仕入先を選択してください）</td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, ref } from 'vue'
import * as XLSX from 'xlsx'
import api from '@/api/client'
import { exportPurchaseKikanExcel } from '@/utils/purchaseActualKikanExport'

const activeTab = ref('inquiry')
const loading = ref(false)
const rows = ref([])
const suppliers = ref([])
const today = formatISODate(new Date())
const startDate = ref(today)
const endDate = ref(today)
const productCode = ref('')
const filterSupplierId = ref('')

// マッピング設定
const mappingSupplier = ref('')
const mappingLoading = ref(false)
const mappingError = ref('')
const mappingRows = ref([])
const mappingSaveMsg = ref('')

const formatDate = (value) => String(value || '').replace(/-/g, '/')
const formatNum = (value) => Number(value || 0).toLocaleString()

const loadSuppliers = async () => {
  try {
    const res = await api.suppliers.getSuppliers()
    suppliers.value = (res.data?.results || res.data || []).sort((a, b) =>
      (a.supplier_code || '').localeCompare(b.supplier_code || '')
    )
  } catch (_e) {
    suppliers.value = []
  }
}

const load = async () => {
  loading.value = true
  try {
    const res = await api.purchaseActuals.getInquiry({
      start_date: startDate.value,
      end_date: endDate.value,
      product_code: productCode.value || undefined,
    })
    let data = Array.isArray(res.data) ? res.data : []
    if (filterSupplierId.value) {
      const sup = suppliers.value.find((s) => String(s.id) === filterSupplierId.value)
      if (sup) {
        data = data.filter((r) => {
          const s = r.supplier || ''
          return s === sup.supplier_name || s === sup.supplier_code || s.includes(sup.supplier_name) || s.includes(sup.supplier_code)
        })
      }
    }
    rows.value = data
  } catch (_e) {
    rows.value = []
    alert('納入実績の取得に失敗しました。')
  } finally {
    loading.value = false
  }
}

// ====== 基幹システム入力用Excel ======
const onExportKikan = async () => {
  // 照会中の仕入先を特定（仕入先フィルタがあればそれを使う）
  let supplierId = filterSupplierId.value
  if (!supplierId) {
    // 照会結果から仕入先を推定（複数混在の場合は全品番のマッピングを使用）
    supplierId = ''
  }

  let mappings = []
  if (supplierId) {
    try {
      const res = await api.purchaseActualKikanMapping.getMapping(supplierId)
      mappings = Array.isArray(res.data?.mappings) ? res.data.mappings : []
    } catch (_e) {
      alert('マッピング設定の取得に失敗しました。')
      return
    }
  } else {
    // 仕入先フィルタなし: 全仕入先のマッピングを結合
    try {
      const uniqueSupplierNames = [...new Set(rows.value.map((r) => r.supplier).filter(Boolean))]
      const matched = suppliers.value.filter((s) => uniqueSupplierNames.includes(s.supplier_name))
      const results = await Promise.all(
        matched.map((s) => api.purchaseActualKikanMapping.getMapping(s.id).catch(() => null))
      )
      for (const res of results) {
        if (res?.data?.mappings) mappings.push(...res.data.mappings)
      }
    } catch (_e) {
      alert('マッピング設定の取得に失敗しました。')
      return
    }
  }

  const sup = suppliers.value.find((s) => String(s.id) === supplierId)
  exportPurchaseKikanExcel(rows.value, mappings, startDate.value, endDate.value, sup?.supplier_code || '')
}

// ====== マッピング設定 ======
const onMappingSupplierChange = async () => {
  if (!mappingSupplier.value) {
    mappingRows.value = []
    return
  }
  mappingLoading.value = true
  mappingError.value = ''
  mappingSaveMsg.value = ''
  try {
    // 品番候補（BOMItem + RoutingStep）と保存済みマッピングを並列取得
    const [candidatesRes, savedRes] = await Promise.all([
      api.purchaseActualKikanMapping.getCandidates(mappingSupplier.value),
      api.purchaseActualKikanMapping.getMapping(mappingSupplier.value),
    ])

    const templateItems = Array.isArray(candidatesRes.data) ? candidatesRes.data : []
    const savedMappings = Array.isArray(savedRes.data?.mappings) ? savedRes.data.mappings : []
    const savedMap = new Map(
      savedMappings.map((m) => [String(m.appProductCode || '').trim().toUpperCase(), m])
    )

    mappingRows.value = templateItems.map((item) => {
      const code = String(item.product_code || '').trim().toUpperCase()
      const saved = savedMap.get(code)
      return {
        appProductCode: item.product_code || '',
        productName: item.product_name || '',
        itemType: saved?.itemType || '',
        coreProductCode: saved?.coreProductCode || '',
        supplierCode: saved?.supplierCode || '',
        tabsAfterHinban: saved?.tabsAfterHinban ?? '',
      }
    })
  } catch (_e) {
    mappingError.value = '品番一覧またはマッピング設定の取得に失敗しました。'
    mappingRows.value = []
  } finally {
    mappingLoading.value = false
  }
}

const copyCode = (item) => {
  item.coreProductCode = item.appProductCode
}

// ====== テンプレ出力 ======
const MAPPING_HEADERS = ['アプリ品番', '品名', '品目区分(G/K)', '基幹品番', '仕入先コード', '品番後Tabキー回数']

const downloadMappingTemplate = () => {
  const rows = mappingRows.value.map((item) => [
    item.appProductCode,
    item.productName,
    item.itemType || '',
    item.coreProductCode || '',
    item.supplierCode || '',
    item.tabsAfterHinban !== '' && item.tabsAfterHinban != null ? item.tabsAfterHinban : '',
  ])
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet([MAPPING_HEADERS, ...rows])
  // 列幅設定
  ws['!cols'] = [{ wch: 20 }, { wch: 24 }, { wch: 14 }, { wch: 20 }, { wch: 14 }, { wch: 16 }]
  XLSX.utils.book_append_sheet(wb, ws, 'マッピング')
  const sup = suppliers.value.find((s) => String(s.id) === mappingSupplier.value)
  const code = sup?.supplier_code || 'supplier'
  const data = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  const blob = new Blob([data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `マッピングテンプレ_${code}.xlsx`
  a.click()
  URL.revokeObjectURL(url)
}

// ====== Excelから導入 ======
const importFileRef = ref(null)

const onImportExcel = (event) => {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const wb = XLSX.read(e.target.result, { type: 'array' })
      const ws = wb.Sheets[wb.SheetNames[0]]
      const raw = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' })
      if (raw.length < 2) {
        alert('データがありません。')
        return
      }
      const headers = raw[0].map((h) => String(h || '').trim())
      const idxApp    = headers.indexOf('アプリ品番')
      const idxName   = headers.indexOf('品名')
      const idxType   = headers.indexOf('品目区分(G/K)')
      const idxCore   = headers.indexOf('基幹品番')
      const idxSup    = headers.indexOf('仕入先コード')
      const idxTabs   = headers.indexOf('品番後Tabキー回数')
      if (idxApp < 0 || idxCore < 0) {
        alert('「アプリ品番」「基幹品番」列が見つかりません。テンプレ出力したExcelを使用してください。')
        return
      }
      // 既存のmappingRowsをアプリ品番で引く（品名を保持するため）
      const existingMap = new Map(mappingRows.value.map((r) => [r.appProductCode.trim().toUpperCase(), r]))

      const importedCodes = new Set()
      const updated = []
      for (const row of raw.slice(1)) {
        const appCode = String(row[idxApp] || '').trim()
        if (!appCode) continue
        importedCodes.add(appCode.toUpperCase())
        const existing = existingMap.get(appCode.toUpperCase())
        const itemType = String(row[idxType] || '').trim().toUpperCase()
        const tabs = parseInt(row[idxTabs], 10)
        updated.push({
          appProductCode: appCode,
          productName: existing?.productName || String(row[idxName] || ''),
          itemType: itemType === 'K' ? 'K' : itemType === 'G' ? 'G' : (existing?.itemType || ''),
          coreProductCode: String(row[idxCore] || '').trim(),
          supplierCode: idxSup >= 0 ? String(row[idxSup] || '').trim() : (existing?.supplierCode || ''),
          tabsAfterHinban: Number.isFinite(tabs) && tabs >= 1 ? tabs : (existing?.tabsAfterHinban ?? ''),
        })
      }
      // Excel未記載だった品番は既存のまま残す
      for (const row of mappingRows.value) {
        if (!importedCodes.has(row.appProductCode.trim().toUpperCase())) {
          updated.push(row)
        }
      }
      mappingRows.value = updated
      mappingSaveMsg.value = `${updated.length} 件を読み込みました。内容を確認して「保存」を押してください。`
    } catch (err) {
      alert(`Excel読み込みエラー: ${err.message || err}`)
    } finally {
      // 同じファイルを再選択できるようリセット
      if (importFileRef.value) importFileRef.value.value = ''
    }
  }
  reader.readAsArrayBuffer(file)
}

const saveMappings = async () => {
  if (!mappingSupplier.value) return
  mappingSaveMsg.value = ''
  try {
    const mappings = mappingRows.value.map((item) => ({
      appProductCode: item.appProductCode,
      coreProductCode: item.coreProductCode,
      itemType: item.itemType,
      supplierCode: item.supplierCode,
      tabsAfterHinban: item.tabsAfterHinban ?? 1,
    }))
    await api.purchaseActualKikanMapping.saveMapping(mappingSupplier.value, mappings)
    mappingSaveMsg.value = 'マッピングを保存しました。'
  } catch (_e) {
    mappingSaveMsg.value = 'マッピングの保存に失敗しました。'
  }
}

onMounted(async () => {
  await loadSuppliers()
  await load()
})
</script>

<style scoped>
.page { padding: 16px; }
.page-title { margin: 0 0 12px; font-size: 22px; }
.tab-bar { display: flex; gap: 6px; margin-bottom: 12px; border-bottom: 1px solid #cbd5e1; }
.tab-item { padding: 7px 14px; border: 1px solid #cbd5e1; border-bottom: none; border-radius: 8px 8px 0 0; background: #f8fafc; color: #334155; font-size: 13px; font-weight: 700; cursor: pointer; }
.tab-item.active { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }
.filters { display: flex; gap: 10px; align-items: end; margin-bottom: 10px; flex-wrap: wrap; }
.filters label { display: grid; gap: 4px; font-size: 13px; font-weight: 700; }
.filters input, .filters select { border: 1px solid #9ca3af; padding: 6px; min-width: 120px; }
.btn { padding: 6px 12px; border: 1px solid #1d4ed8; background: #1d4ed8; color: #fff; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 13px; }
.btn:disabled { opacity: 0.6; cursor: default; }
.btn-secondary { border-color: #64748b; background: #64748b; }
.btn-sm { padding: 3px 8px; font-size: 12px; }
.table-wrap { border: 1px solid #e2e8f0; overflow: auto; background: #fff; border-radius: 8px; }
.list-table { width: 100%; border-collapse: collapse; }
.list-table th, .list-table td { border-bottom: 1px solid #e2e8f0; padding: 6px 8px; font-size: 13px; text-align: left; }
.list-table thead th { background: #4f6f82; color: #fff; position: sticky; top: 0; }
.num { text-align: right !important; }
.no-data { text-align: center !important; color: #64748b; padding: 20px !important; }
.settings-panel { margin-top: 8px; padding: 14px; border: 1px solid #e2e8f0; border-radius: 10px; background: #fff; }
.settings-title { margin: 0; font-size: 17px; }
.settings-note { margin: 6px 0 12px; color: #64748b; font-size: 13px; }
.settings-selector { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.settings-selector label { font-size: 13px; font-weight: 700; min-width: 44px; }
.settings-selector select { min-width: 220px; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.settings-table-wrap { margin-top: 8px; }
.mapping-table { min-width: 860px; }
.map-input { width: 100%; padding: 5px 6px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.map-input-narrow { width: 60px !important; text-align: center; }
.map-select { width: 100%; padding: 5px 6px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
.settings-actions { margin-top: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.settings-actions label.btn { cursor: pointer; }
.settings-actions label.btn.disabled { opacity: 0.6; pointer-events: none; }
.settings-message { margin-top: 8px; color: #166534; font-size: 13px; font-weight: 700; }
.settings-info { margin: 8px 0; color: #1e3a8a; font-size: 13px; font-weight: 700; }
.settings-error { margin: 8px 0; color: #991b1b; font-size: 13px; font-weight: 700; }
</style>
