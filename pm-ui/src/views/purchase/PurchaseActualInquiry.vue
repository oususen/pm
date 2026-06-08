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
      <p class="settings-note">仕入先を選択し、品番ごとに基幹品番・品目区分(G/K)・仕入先コード・Tab回数を設定してください。</p>

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

      <div v-if="mappingSupplier" class="table-wrap settings-table-wrap">
        <table class="list-table mapping-table">
          <thead>
            <tr>
              <th>アプリ品番</th>
              <th>品名</th>
              <th>品目区分</th>
              <th>基幹品番</th>
              <th>仕入先コード<br><small>加工先CD(G) / 仕入先コード(K)</small></th>
              <th>品番後Tab回数<br><small>G1か所=1、G2か所=2、K=1</small></th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in mappingRows" :key="idx">
              <td>{{ item.appProductCode }}</td>
              <td>{{ item.productName }}</td>
              <td>
                <select v-model="item.itemType" class="map-select">
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

      <div class="settings-actions">
        <button class="btn" :disabled="!mappingSupplier || mappingLoading" @click="saveMappings">保存</button>
      </div>
      <div v-if="mappingSaveMsg" class="settings-message">{{ mappingSaveMsg }}</div>
    </div>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { onMounted, ref } from 'vue'
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
        data = data.filter((r) => r.supplier === sup.supplier_name || r.supplier === sup.supplier_code)
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
    // 品番候補 (delivery-list-template) と保存済みマッピングを並列取得
    const [templateRes, savedRes] = await Promise.all([
      api.client.get('/purchase-receiving/delivery-list-template/', {
        params: { supplier_id: mappingSupplier.value },
      }),
      api.purchaseActualKikanMapping.getMapping(mappingSupplier.value),
    ])

    const templateItems = Array.isArray(templateRes.data) ? templateRes.data : []
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
        itemType: saved?.itemType || 'G',
        coreProductCode: saved?.coreProductCode || '',
        supplierCode: saved?.supplierCode || '',
        tabsAfterHinban: saved?.tabsAfterHinban ?? 1,
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
.settings-actions { margin-top: 12px; display: flex; gap: 8px; }
.settings-message { margin-top: 8px; color: #166534; font-size: 13px; font-weight: 700; }
.settings-info { margin: 8px 0; color: #1e3a8a; font-size: 13px; font-weight: 700; }
.settings-error { margin: 8px 0; color: #991b1b; font-size: 13px; font-weight: 700; }
</style>
