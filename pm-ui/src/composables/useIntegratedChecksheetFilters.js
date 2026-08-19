import { computed, ref } from "vue"
import api from "@/api/client"

const TEMPLATE_FETCH_CHUNK_SIZE = 10

const toArray = (data) => data?.results || data || []
const uniqueSorted = (rows, key) => [...new Set(rows.map((row) => row[key] || "未設定"))].sort((a, b) => String(a).localeCompare(String(b), "ja"))
const isValidDateText = (value) => /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))

const loadTemplatesChunked = async (templateIds) => {
  const results = []
  for (let i = 0; i < templateIds.length; i += TEMPLATE_FETCH_CHUNK_SIZE) {
    const chunk = templateIds.slice(i, i + TEMPLATE_FETCH_CHUNK_SIZE)
    results.push(...(await Promise.all(chunk.map((id) => api.integratedChecksheets.getTemplate(id)))))
  }
  return results
}

export function useIntegratedChecksheetFilters({
  sourceRows,
  rowItemKey = "itemName",
  rowPersonKey = "person",
  rowUnitKey = "unit",
  favoriteScreenKey = "",
  enableFavorites = false,
} = {}) {
  const templateDefinitions = ref([])
  const selectedLine = ref("")
  const selectedProcess = ref("")
  const selectedProduct = ref("")
  const selectedItem = ref("")
  const selectedPerson = ref("")
  const selectedUnit = ref("")
  const startDate = ref("")
  const endDate = ref("")
  const favorites = ref([])
  const selectedFavoriteId = ref("")
  const favoriteName = ref("")

  const lineOptions = computed(() => uniqueSorted(templateDefinitions.value, "line"))
  const processOptions = computed(() => uniqueSorted(
    templateDefinitions.value.filter((row) => {
      if (selectedLine.value && row.line !== selectedLine.value) return false
      if (selectedProduct.value && row.product !== selectedProduct.value) return false
      return true
    }),
    "process",
  ))
  const productOptions = computed(() => uniqueSorted(
    templateDefinitions.value.filter((row) => {
      if (selectedLine.value && row.line !== selectedLine.value) return false
      if (selectedProcess.value && row.process !== selectedProcess.value) return false
      return true
    }),
    "product",
  ))
  const isItemSelectable = computed(() => Boolean(selectedProduct.value) && Boolean(selectedProcess.value))
  const itemOptions = computed(() => {
    if (!isItemSelectable.value) return []
    return uniqueSorted(
      templateDefinitions.value.filter((row) => row.product === selectedProduct.value && row.process === selectedProcess.value),
      "itemName",
    )
  })
  const personOptions = computed(() => uniqueSorted(sourceRows.value, rowPersonKey))
  const unitOptions = computed(() => uniqueSorted(sourceRows.value, rowUnitKey))

  const buildMonthStartText = () => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`
  }

  const toFavoritePayload = () => ({
    selectedLine: String(selectedLine.value || ""),
    selectedProcess: String(selectedProcess.value || ""),
    selectedProduct: String(selectedProduct.value || ""),
    selectedItem: String(selectedItem.value || ""),
    selectedPerson: String(selectedPerson.value || ""),
    selectedUnit: String(selectedUnit.value || ""),
    startDate: isValidDateText(startDate.value) ? String(startDate.value) : "",
    endDate: isValidDateText(endDate.value) ? String(endDate.value) : "",
  })

  const applyFavoritePayload = (payload) => {
    selectedLine.value = String(payload?.selectedLine || "")
    selectedProcess.value = String(payload?.selectedProcess || "")
    selectedProduct.value = String(payload?.selectedProduct || "")
    selectedItem.value = String(payload?.selectedItem || "")
    selectedPerson.value = String(payload?.selectedPerson || "")
    selectedUnit.value = String(payload?.selectedUnit || "")
    startDate.value = isValidDateText(payload?.startDate) ? String(payload.startDate) : ""
    endDate.value = isValidDateText(payload?.endDate) ? String(payload.endDate) : ""
  }

  const loadTemplateDefinitions = async () => {
    try {
      const res = await api.integratedChecksheets.listTemplates({ page_size: 500 })
      const templates = toArray(res.data)
      const templateIds = templates.map((template) => Number(template.id || 0)).filter((id) => id > 0)
      const templateResList = await loadTemplatesChunked(templateIds)
      const rows = []
      templateResList.forEach((response) => {
        const template = response.data
        const line = template?.line_code || "未設定"
        const product = template?.product_code || "未設定"
        ;(template?.process_blocks || []).forEach((block) => {
          const process = block.process_name || block.process_code || `工程${block.id}`
          if (!block.items?.length) {
            rows.push({
              templateId: Number(template.id || 0),
              line,
              lineId: template?.line || null,
              product,
              productId: template?.product || null,
              process,
              itemName: "未設定項目",
            })
            return
          }
          block.items.forEach((item) => {
            rows.push({
              templateId: Number(template.id || 0),
              line,
              lineId: template?.line || null,
              product,
              productId: template?.product || null,
              process,
              itemName: item.item_name || "未設定項目",
            })
          })
        })
      })
      templateDefinitions.value = rows
    } catch (e) {
      console.error("テンプレート定義取得失敗:", e)
    }
  }

  const loadFavorites = async () => {
    if (!enableFavorites || !favoriteScreenKey) return
    try {
      const res = await api.accounts.getFavorites({ screen_key: favoriteScreenKey, page_size: 200 })
      favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
    } catch (e) {
      console.error("お気に入り取得失敗:", e)
    }
  }

  const applyFavorite = () => {
    const id = Number(selectedFavoriteId.value || 0)
    if (!id) return
    const target = favorites.value.find((item) => Number(item.id) === id)
    if (!target) return
    favoriteName.value = target.name || ""
    applyFavoritePayload(target.payload || {})
  }

  const saveFavorite = async () => {
    if (!enableFavorites || !favoriteScreenKey) return
    const name = String(favoriteName.value || "").trim()
    if (!name) {
      window.alert("お気に入り名を入力してください。")
      return
    }
    const payload = { screen_key: favoriteScreenKey, name, payload: toFavoritePayload() }
    try {
      const id = Number(selectedFavoriteId.value || 0)
      if (id) await api.accounts.updateFavorite(id, payload)
      else await api.accounts.createFavorite(payload)
      await loadFavorites()
      const found = favorites.value.find((item) => item.name === name)
      selectedFavoriteId.value = found ? String(found.id) : ""
      window.alert("お気に入りを保存しました。")
    } catch (e) {
      window.alert(`お気に入り保存エラー: ${e?.response?.data?.detail || e?.message || "保存に失敗しました。"}`)
    }
  }

  return {
    templateDefinitions,
    selectedLine,
    selectedProcess,
    selectedProduct,
    selectedItem,
    selectedPerson,
    selectedUnit,
    startDate,
    endDate,
    favorites,
    selectedFavoriteId,
    favoriteName,
    lineOptions,
    processOptions,
    productOptions,
    isItemSelectable,
    itemOptions,
    personOptions,
    unitOptions,
    buildMonthStartText,
    isValidDateText,
    toFavoritePayload,
    applyFavoritePayload,
    loadTemplateDefinitions,
    loadFavorites,
    applyFavorite,
    saveFavorite,
  }
}
