<template>
  <div class="settings-container">
    <h2 class="page-title">ガントチャート生成表示品マップ {{ isEdit ? '編集' : '新規' }}</h2>
    <p class="helper-text">
      ライン / ライン最終品 / 工程 / 表示品を登録します。工程追加は同じライン最終品を引き継いで続けて登録できます。
    </p>

    <div class="card">
      <div class="header-actions">
        <button class="btn" @click="goList" :disabled="loading || saving">一覧へ戻る</button>
        <button
          v-if="isEdit"
          class="btn"
          @click="goAddProcessFromCurrent"
          :disabled="loading || saving || !canEdit || !form.line || !form.final_product"
        >
          同じ最終品で工程追加
        </button>
        <button class="btn danger" v-if="isEdit" @click="deleteMap" :disabled="loading || saving || deleting || !canEdit">削除</button>
        <button class="btn primary" @click="saveForm(false)" :disabled="loading || saving || !canEdit">保存</button>
        <button class="btn primary" v-if="!isEdit" @click="saveForm(true)" :disabled="loading || saving || !canEdit">
          保存して工程追加
        </button>
      </div>

      <p v-if="!canEdit" class="warn-text">閲覧モード（保存不可）</p>

      <form class="form-grid" @submit.prevent="saveForm(false)">
        <div class="form-group">
          <label>ライン *</label>
          <select v-model.number="form.line" :disabled="loading || saving || !canEdit" @change="onLineChange">
            <option :value="null">選択してください</option>
            <option v-for="line in lineOptions" :key="line.id" :value="line.id">
              {{ line.line_code }} - {{ line.line_name }}
            </option>
          </select>
        </div>

        <div class="form-group autocomplete-group">
          <label>ライン最終品 *</label>
          <div class="autocomplete">
            <input
              v-model.trim="form.final_product_query"
              type="text"
              placeholder="ライン最終品を入力して補完"
              :disabled="loading || saving || !canEdit"
              @focus="openFinalSuggestions"
              @input="onFinalProductInput"
              @blur="onFinalProductBlur"
            />
            <div v-if="form.showFinalSuggestions" class="suggestions">
              <button
                v-for="product in finalSuggestions"
                :key="product.id"
                type="button"
                class="suggestion-item"
                @mousedown.prevent="selectFinalProduct(product)"
              >
                {{ product.product_code }} - {{ product.product_name }}
              </button>
              <div v-if="!finalSuggestions.length" class="suggestion-empty">候補がありません</div>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>工程 *</label>
          <select v-model.number="form.process" :disabled="loading || saving || !canEdit">
            <option :value="null">選択してください</option>
            <option v-for="process in processOptionsForForm" :key="process.id" :value="process.id">
              {{ process.process_code }} - {{ process.process_name }}
            </option>
          </select>
        </div>

        <div class="form-group autocomplete-group">
          <label>表示品（主に連産品） *</label>
          <div class="autocomplete">
            <input
              v-model.trim="form.display_product_query"
              type="text"
              placeholder="品番コード / 品名を入力して補完"
              :disabled="loading || saving || !canEdit"
              @focus="openDisplaySuggestions"
              @input="onDisplayProductInput"
              @blur="onDisplayProductBlur"
            />
            <div v-if="form.showDisplaySuggestions" class="suggestions">
              <button
                v-for="product in displaySuggestions"
                :key="product.id"
                type="button"
                class="suggestion-item"
                @mousedown.prevent="selectDisplayProduct(product)"
              >
                {{ product.product_code }} - {{ product.product_name }}
              </button>
              <div v-if="!displaySuggestions.length" class="suggestion-empty">候補がありません</div>
            </div>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

const route = useRoute()
const router = useRouter()

const form = ref({
  line: null,
  final_product: null,
  final_product_query: '',
  showFinalSuggestions: false,
  process: null,
  display_product: null,
  display_product_query: '',
  showDisplaySuggestions: false,
})

const lineOptions = ref([])
const processOptions = ref([])
const finalProductOptions = ref([])
const finalProductOptionsByLine = ref({})
const processOptionsByFinalLine = ref({})
const routingDetailCache = ref({})
const allDisplayProductOptions = ref([])

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const initializing = ref(false)

const isEdit = computed(() => Boolean(route.params.id))
const recordId = computed(() => Number(route.params.id || 0) || null)
const canEdit = computed(() => hasPermission(authState.user, 'production.plan_input', 'edit'))

const toArray = (res) => {
  const data = res?.data
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  return []
}

const sortByCode = (a, b, codeKey, nameKey) => {
  const codeA = String(a?.[codeKey] || '')
  const codeB = String(b?.[codeKey] || '')
  if (codeA !== codeB) return codeA.localeCompare(codeB)
  return String(a?.[nameKey] || '').localeCompare(String(b?.[nameKey] || ''))
}

const uniqById = (list) => {
  const map = new Map()
  list.forEach((item) => {
    if (!item || item.id == null) return
    map.set(Number(item.id), item)
  })
  return [...map.values()]
}

const parseLineFinalCandidates = (responseData) => {
  const rows = Array.isArray(responseData) ? responseData : []
  if (!rows.length) return []
  if (Array.isArray(rows[0]?.products)) {
    return uniqById(rows.flatMap((row) => row.products || []))
  }
  return uniqById(rows)
}

const formatProductLabel = (product) => {
  if (!product) return ''
  const code = String(product.product_code || '').trim()
  const name = String(product.product_name || '').trim()
  if (code && name) return `${code} - ${name}`
  return code || name || ''
}

const productById = computed(() => {
  const map = new Map()
  allDisplayProductOptions.value.forEach((product) => {
    map.set(Number(product.id), product)
  })
  return map
})

const finalProductById = computed(() => {
  const map = new Map()
  finalProductOptions.value.forEach((product) => {
    map.set(Number(product.id), product)
  })
  Object.values(finalProductOptionsByLine.value).forEach((list) => {
    if (!Array.isArray(list)) return
    list.forEach((product) => {
      map.set(Number(product.id), product)
    })
  })
  return map
})

const findDisplayProductById = (id) => productById.value.get(Number(id)) || null
const findFinalProductById = (id) => finalProductById.value.get(Number(id)) || null

const resetForm = () => {
  form.value = {
    line: null,
    final_product: null,
    final_product_query: '',
    showFinalSuggestions: false,
    process: null,
    display_product: null,
    display_product_query: '',
    showDisplaySuggestions: false,
  }
}

const loadMasterData = async () => {
  const [lineRes, processRes, finalProductRes, displayProductRes] = await Promise.all([
    api.lines.getLines({ is_active: true, page_size: 5000 }),
    api.processes.getProcesses({ is_active: true, page_size: 5000 }),
    api.products.getProducts({ is_active: true, is_line_final_product: true, page_size: 5000 }),
    api.products.getProducts({ is_active: true, page_size: 5000 }),
  ])

  lineOptions.value = toArray(lineRes).sort((a, b) => sortByCode(a, b, 'line_code', 'line_name'))
  processOptions.value = toArray(processRes).sort((a, b) => sortByCode(a, b, 'process_code', 'process_name'))
  finalProductOptions.value = toArray(finalProductRes).sort((a, b) => sortByCode(a, b, 'product_code', 'product_name'))
  allDisplayProductOptions.value = toArray(displayProductRes).sort((a, b) => sortByCode(a, b, 'product_code', 'product_name'))
}

const ensureFinalProductsForLine = async (lineId) => {
  if (!lineId) return finalProductOptions.value
  const key = String(lineId)
  if (Object.prototype.hasOwnProperty.call(finalProductOptionsByLine.value, key)) {
    return finalProductOptionsByLine.value[key]
  }

  try {
    const res = await api.products.getLineFinalCandidates(lineId)
    const candidates = parseLineFinalCandidates(res?.data).sort((a, b) => sortByCode(a, b, 'product_code', 'product_name'))
    finalProductOptionsByLine.value = {
      ...finalProductOptionsByLine.value,
      [key]: candidates,
    }
    return candidates
  } catch (error) {
    console.error('ライン最終品候補の取得に失敗しました', error)
    finalProductOptionsByLine.value = {
      ...finalProductOptionsByLine.value,
      [key]: [],
    }
    return []
  }
}

const ensureProcessOptionsForForm = async () => {
  const finalProductId = Number(form.value.final_product || 0)
  if (!finalProductId) return []
  const lineId = Number(form.value.line || 0)
  const cacheKey = `${finalProductId}:${lineId}`
  if (Object.prototype.hasOwnProperty.call(processOptionsByFinalLine.value, cacheKey)) {
    return processOptionsByFinalLine.value[cacheKey]
  }

  try {
    const routingsRes = await api.routings.getRoutings({
      product: finalProductId,
      is_active: true,
      page_size: 200,
    })
    const routingRows = toArray(routingsRes)
    const processIdSet = new Set()

    for (const routing of routingRows) {
      if (!routing?.id) continue
      let detail = routingDetailCache.value[routing.id]
      if (!detail) {
        const routingDetailRes = await api.routings.getRouting(routing.id)
        detail = routingDetailRes?.data || {}
        routingDetailCache.value = {
          ...routingDetailCache.value,
          [routing.id]: detail,
        }
      }
      const steps = Array.isArray(detail?.steps) ? detail.steps : []
      steps.forEach((step) => {
        const processId = Number(step?.process || 0)
        if (!processId) return
        const stepLineId = Number(step?.line || 0)
        if (!lineId || stepLineId === 0 || stepLineId === lineId) {
          processIdSet.add(processId)
        }
      })
    }

    let options = processOptions.value.filter((process) => processIdSet.has(Number(process.id)))
    if (!options.length) {
      options = lineId
        ? processOptions.value.filter((process) => !process.line || Number(process.line) === lineId)
        : processOptions.value
    }
    processOptionsByFinalLine.value = {
      ...processOptionsByFinalLine.value,
      [cacheKey]: options,
    }
    return options
  } catch (error) {
    console.error('工程候補の取得に失敗しました', error)
    const fallback = lineId
      ? processOptions.value.filter((process) => !process.line || Number(process.line) === lineId)
      : processOptions.value
    processOptionsByFinalLine.value = {
      ...processOptionsByFinalLine.value,
      [cacheKey]: fallback,
    }
    return fallback
  }
}

const getFinalProductCandidates = () => {
  if (!form.value.line) return finalProductOptions.value
  const key = String(form.value.line)
  const lineCandidates = finalProductOptionsByLine.value[key] || []
  const merged = [...lineCandidates]
  const idSet = new Set(lineCandidates.map((product) => Number(product.id)))
  finalProductOptions.value.forEach((product) => {
    const id = Number(product.id)
    if (!idSet.has(id)) merged.push(product)
  })
  return merged
}

const finalSuggestions = computed(() => {
  const keyword = String(form.value.final_product_query || '').trim().toLowerCase()
  const candidates = getFinalProductCandidates()
  if (!keyword) return candidates.slice(0, 30)
  return candidates
    .filter((product) => {
      const code = String(product.product_code || '').toLowerCase()
      const name = String(product.product_name || '').toLowerCase()
      const label = formatProductLabel(product).toLowerCase()
      return code.includes(keyword) || name.includes(keyword) || label.includes(keyword)
    })
    .slice(0, 30)
})

const processOptionsForForm = computed(() => {
  const lineId = Number(form.value.line || 0)
  const finalProductId = Number(form.value.final_product || 0)
  if (finalProductId) {
    const cacheKey = `${finalProductId}:${lineId}`
    const cached = processOptionsByFinalLine.value[cacheKey]
    if (Array.isArray(cached) && cached.length) return cached
    if (!Object.prototype.hasOwnProperty.call(processOptionsByFinalLine.value, cacheKey)) {
      void ensureProcessOptionsForForm()
    }
  }
  if (!lineId) return processOptions.value
  return processOptions.value.filter((p) => !p.line || Number(p.line) === lineId)
})

const displaySuggestions = computed(() => {
  const keyword = String(form.value.display_product_query || '').trim().toLowerCase()
  if (!keyword) return allDisplayProductOptions.value.slice(0, 30)
  return allDisplayProductOptions.value
    .filter((p) => {
      const code = String(p.product_code || '').toLowerCase()
      const name = String(p.product_name || '').toLowerCase()
      const label = formatProductLabel(p).toLowerCase()
      return code.includes(keyword) || name.includes(keyword) || label.includes(keyword)
    })
    .slice(0, 30)
})

const selectFinalProduct = (product) => {
  form.value.final_product = product.id
  form.value.final_product_query = formatProductLabel(product)
  form.value.showFinalSuggestions = false
  form.value.process = null
  void ensureProcessOptionsForForm()
}

const onFinalProductInput = () => {
  form.value.showFinalSuggestions = true
  const selected = findFinalProductById(form.value.final_product)
  if (!selected) return
  if (formatProductLabel(selected) !== String(form.value.final_product_query || '').trim()) {
    form.value.final_product = null
    form.value.process = null
  }
}

const openFinalSuggestions = async () => {
  await ensureFinalProductsForLine(form.value.line)
  form.value.showFinalSuggestions = true
}

const onFinalProductBlur = () => {
  setTimeout(() => {
    const query = String(form.value.final_product_query || '').trim().toLowerCase()
    if (!form.value.final_product && query) {
      const exact = getFinalProductCandidates().find((product) => {
        const code = String(product.product_code || '').toLowerCase()
        const label = formatProductLabel(product).toLowerCase()
        return code === query || label === query
      })
      if (exact) {
        selectFinalProduct(exact)
      }
    }
    form.value.showFinalSuggestions = false
  }, 120)
}

const selectDisplayProduct = (product) => {
  form.value.display_product = product.id
  form.value.display_product_query = formatProductLabel(product)
  form.value.showDisplaySuggestions = false
}

const onDisplayProductInput = () => {
  form.value.showDisplaySuggestions = true
  const selected = findDisplayProductById(form.value.display_product)
  if (!selected) return
  if (formatProductLabel(selected) !== String(form.value.display_product_query || '').trim()) {
    form.value.display_product = null
  }
}

const openDisplaySuggestions = () => {
  form.value.showDisplaySuggestions = true
}

const onDisplayProductBlur = () => {
  setTimeout(() => {
    const query = String(form.value.display_product_query || '').trim().toLowerCase()
    if (!form.value.display_product && query) {
      const exact = allDisplayProductOptions.value.find((product) => {
        const code = String(product.product_code || '').toLowerCase()
        const label = formatProductLabel(product).toLowerCase()
        return code === query || label === query
      })
      if (exact) {
        selectDisplayProduct(exact)
      }
    }
    form.value.showDisplaySuggestions = false
  }, 120)
}

const onLineChange = async () => {
  const lineId = Number(form.value.line || 0)
  form.value.process = null
  if (!lineId) return

  await ensureFinalProductsForLine(lineId)
  if (form.value.final_product) {
    await ensureProcessOptionsForForm()
    const candidates = getFinalProductCandidates()
    if (!candidates.some((product) => Number(product.id) === Number(form.value.final_product))) {
      form.value.final_product = null
      form.value.final_product_query = ''
    }
  }
}

const validateForm = () => {
  if (!form.value.line || !form.value.final_product || !form.value.process || !form.value.display_product) {
    alert('ライン・ライン最終品・工程・表示品をすべて選択してください。')
    return false
  }
  return true
}

const goList = () => {
  router.push({ name: 'GanttDisplayProductMapList' })
}

const goAddProcessFromCurrent = () => {
  if (!form.value.line || !form.value.final_product) return
  router.push({
    name: 'GanttDisplayProductMapCreate',
    query: {
      line: String(form.value.line),
      final_product: String(form.value.final_product),
    },
  })
}

const applyCreatePrefillFromQuery = async () => {
  resetForm()
  const queryLine = Number(route.query.line || 0)
  const queryFinal = Number(route.query.final_product || 0)

  if (queryLine > 0) {
    form.value.line = queryLine
    await ensureFinalProductsForLine(queryLine)
  }

  if (queryFinal > 0) {
    form.value.final_product = queryFinal
    const finalProduct = findFinalProductById(queryFinal)
    form.value.final_product_query = finalProduct ? formatProductLabel(finalProduct) : ''
    await ensureProcessOptionsForForm()
  }
}

const applyServerRecord = async (data) => {
  resetForm()

  form.value.line = data?.line ?? null
  form.value.final_product = data?.final_product ?? null
  form.value.process = data?.process ?? null
  form.value.display_product = data?.display_product ?? null

  await ensureFinalProductsForLine(form.value.line)
  await ensureProcessOptionsForForm()

  const finalProduct = findFinalProductById(form.value.final_product)
  const displayProduct = findDisplayProductById(form.value.display_product)

  form.value.final_product_query = finalProduct
    ? formatProductLabel(finalProduct)
    : formatProductLabel({ product_code: data?.final_product_code, product_name: data?.final_product_name })

  form.value.display_product_query = displayProduct
    ? formatProductLabel(displayProduct)
    : formatProductLabel({ product_code: data?.display_product_code, product_name: data?.display_product_name })
}

const saveForm = async (continueAdd) => {
  if (!canEdit.value) return
  if (!validateForm()) return

  saving.value = true
  const payload = {
    line: form.value.line,
    final_product: form.value.final_product,
    process: form.value.process,
    display_product: form.value.display_product,
  }

  try {
    if (isEdit.value) {
      await api.ganttDisplayProductMaps.updateGanttDisplayProductMap(recordId.value, payload)
      alert('更新しました。')
      goList()
      return
    }

    await api.ganttDisplayProductMaps.createGanttDisplayProductMap(payload)

    if (continueAdd) {
      const nextQuery = {
        line: String(form.value.line),
        final_product: String(form.value.final_product),
      }
      await router.replace({ name: 'GanttDisplayProductMapCreate', query: nextQuery })
      form.value.process = null
      form.value.display_product = null
      form.value.display_product_query = ''
      form.value.showDisplaySuggestions = false
      alert('登録しました。続けて工程と表示品を追加できます。')
      return
    }

    alert('登録しました。')
    goList()
  } catch (error) {
    console.error('ガント表示品マップの保存に失敗しました', error)
    const detail = error?.response?.data?.detail
    const firstFieldError = error?.response?.data && typeof error.response.data === 'object'
      ? Object.values(error.response.data)?.[0]
      : null
    const message = Array.isArray(firstFieldError) ? firstFieldError[0] : firstFieldError
    alert(detail || message || '保存に失敗しました。')
  } finally {
    saving.value = false
  }
}

const deleteMap = async () => {
  if (!isEdit.value || !recordId.value || !canEdit.value) return
  if (!confirm('このデータを削除しますか？')) return

  deleting.value = true
  try {
    await api.ganttDisplayProductMaps.deleteGanttDisplayProductMap(recordId.value)
    alert('削除しました。')
    goList()
  } catch (error) {
    console.error('ガント表示品マップの削除に失敗しました', error)
    alert('削除に失敗しました。')
  } finally {
    deleting.value = false
  }
}

const initializePage = async () => {
  if (initializing.value) return
  initializing.value = true
  loading.value = true
  try {
    finalProductOptionsByLine.value = {}
    processOptionsByFinalLine.value = {}
    routingDetailCache.value = {}

    await loadMasterData()

    if (isEdit.value && recordId.value) {
      const res = await api.ganttDisplayProductMaps.getGanttDisplayProductMap(recordId.value)
      await applyServerRecord(res?.data || {})
    } else {
      await applyCreatePrefillFromQuery()
    }
  } catch (error) {
    console.error('ガント表示品マップフォームの読込に失敗しました', error)
    alert('ガント表示品マップフォームの読込に失敗しました。')
  } finally {
    loading.value = false
    initializing.value = false
  }
}

onMounted(() => {
  initializePage()
})

watch(
  () => [route.params.id, route.query.line, route.query.final_product],
  () => {
    initializePage()
  }
)
</script>

<style scoped>
.settings-container {
  padding: 10px 12px 16px;
  background: #eef2f6;
  min-height: 100%;
  color: #1f2a44;
  font-family: "Noto Sans JP", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}
.helper-text {
  margin: 0 0 10px;
  color: #475569;
  font-size: 12px;
}
.card {
  background: #fff;
  border: 1px solid #c5cfde;
  border-radius: 6px;
  padding: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
  overflow: visible;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.warn-text {
  margin: 0 0 8px;
  color: #b45309;
  font-size: 12px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
  overflow: visible;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.form-group label {
  font-size: 12px;
  color: #334155;
}
.form-group select,
.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #cfd6e1;
  border-radius: 4px;
  font-size: 12px;
}
.autocomplete-group {
  position: relative;
  min-height: 72px;
}
.autocomplete {
  position: relative;
}
.suggestions {
  position: absolute;
  top: calc(100% + 2px);
  left: 0;
  right: 0;
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid #cfd6e1;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
  z-index: 20;
}
.suggestion-item {
  width: 100%;
  border: 0;
  border-bottom: 1px solid #edf2f7;
  background: #fff;
  text-align: left;
  padding: 6px 8px;
  font-size: 12px;
  cursor: pointer;
}
.suggestion-item:hover {
  background: #f8fafc;
}
.suggestion-empty {
  padding: 6px 8px;
  color: #64748b;
  font-size: 12px;
}
.btn {
  padding: 6px 10px;
  border: 1px solid #b5c1d2;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}
.btn.primary {
  background: #4a7ae5;
  color: #fff;
  border-color: #3865c7;
}
.btn.danger {
  background: #fff5f5;
  color: #b91c1c;
  border-color: #fecaca;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
@media (max-width: 1024px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

