const TARGET_LINE_CODES_KEY = 'production_record_target_line_codes'
const PRODUCT_MAPPINGS_KEY = 'production_record_product_mappings'
const DEFAULT_ENTER_COUNT = 2

const TAB_KEYS = ['tank', 'floor', 'blade', 'laser', 'brake']
const DEFAULT_TARGET_LINE_CODES_BY_TAB = {
  tank: ['L2200', 'L2201'],
  floor: [],
  blade: [],
  laser: [],
  brake: [],
}

const normalize = (value) => String(value || '').trim().toUpperCase()

const canUseStorage = () => typeof window !== 'undefined' && !!window.localStorage

const parseJson = (raw, fallback) => {
  try {
    return JSON.parse(raw)
  } catch (_e) {
    return fallback
  }
}

const normalizeLineCodes = (lineCodes) => Array.from(
  new Set((Array.isArray(lineCodes) ? lineCodes : []).map((v) => normalize(v)).filter(Boolean)),
)

const normalizeEnterCount = (value) => {
  if (value === null || value === undefined || value === '') return DEFAULT_ENTER_COUNT
  const parsed = parseInt(value, 10)
  if (!Number.isFinite(parsed)) return DEFAULT_ENTER_COUNT
  if (parsed < 1 || parsed > 20) return DEFAULT_ENTER_COUNT
  return parsed
}

const normalizeMappingRows = (rows) => (Array.isArray(rows) ? rows : [])
  .map((row) => {
    const enterCount = normalizeEnterCount(row?.enterCount)
    return {
      appProductCode: normalize(row?.appProductCode),
      processCode: normalize(row?.processCode),
      coreProductCode: String(row?.coreProductCode || '').trim(),
      coreProcessOrder: String(row?.coreProcessOrder || '').trim(),
      enterCount,  // 品番確定後→工程順のEnter回数（未指定時は既定値2）
    }
  })
  .filter((row) => row.appProductCode && row.coreProductCode)

export const createDefaultTargetLineCodesByTab = () => ({
  tank: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.tank],
  floor: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.floor],
  blade: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.blade],
  laser: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.laser],
  brake: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.brake],
})

export const normalizeTargetLineCodesByTab = (lineCodesByTab) => {
  const base = createDefaultTargetLineCodesByTab()
  TAB_KEYS.forEach((tabKey) => {
    base[tabKey] = normalizeLineCodes(lineCodesByTab?.[tabKey] ?? base[tabKey])
  })
  return base
}

export const loadTargetLineCodesByTab = () => {
  const defaults = createDefaultTargetLineCodesByTab()
  if (!canUseStorage()) return defaults

  const raw = window.localStorage.getItem(TARGET_LINE_CODES_KEY)
  const parsed = parseJson(raw, null)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return defaults

  const next = createDefaultTargetLineCodesByTab()
  TAB_KEYS.forEach((tabKey) => {
    next[tabKey] = normalizeLineCodes(parsed?.[tabKey] ?? next[tabKey])
  })
  return next
}

export const saveTargetLineCodesByTab = (lineCodesByTab) => {
  const base = normalizeTargetLineCodesByTab(lineCodesByTab)
  if (canUseStorage()) {
    window.localStorage.setItem(TARGET_LINE_CODES_KEY, JSON.stringify(base))
  }
  return base
}

export const getTargetLineCodesByTab = (lineCodesByTab, tabKey) => {
  const normalizedTabKey = String(tabKey || '').trim().toLowerCase()
  const source = lineCodesByTab && typeof lineCodesByTab === 'object'
    ? lineCodesByTab
    : createDefaultTargetLineCodesByTab()
  const current = normalizeLineCodes(source?.[normalizedTabKey])
  if (current.length) return current
  return normalizeLineCodes(DEFAULT_TARGET_LINE_CODES_BY_TAB[normalizedTabKey] || [])
}

export const createDefaultMappingsByTab = () => ({
  tank: [],
  floor: [],
  blade: [],
  laser: [],
  brake: [],
})

export const normalizeProductionRecordMappingsByTab = (mappingsByTab) => {
  const base = createDefaultMappingsByTab()
  TAB_KEYS.forEach((tabKey) => {
    base[tabKey] = normalizeMappingRows(mappingsByTab?.[tabKey])
  })
  return base
}

export const loadProductionRecordMappingsByTab = () => {
  const defaults = createDefaultMappingsByTab()
  if (!canUseStorage()) return defaults

  const raw = window.localStorage.getItem(PRODUCT_MAPPINGS_KEY)
  const parsed = parseJson(raw, null)

  if (Array.isArray(parsed)) {
    // 旧形式互換: 全件を tank 扱い
    return {
      ...defaults,
      tank: normalizeMappingRows(parsed),
    }
  }

  if (!parsed || typeof parsed !== 'object') return defaults

  const next = createDefaultMappingsByTab()
  TAB_KEYS.forEach((tabKey) => {
    next[tabKey] = normalizeMappingRows(parsed?.[tabKey])
  })
  return next
}

export const saveProductionRecordMappingsByTab = (mappingsByTab) => {
  const base = normalizeProductionRecordMappingsByTab(mappingsByTab)
  if (canUseStorage()) {
    window.localStorage.setItem(PRODUCT_MAPPINGS_KEY, JSON.stringify(base))
  }
  return base
}

export const getProductionRecordMappingsByTab = (mappingsByTab, tabKey) => {
  const normalizedTabKey = String(tabKey || '').trim().toLowerCase()
  const source = mappingsByTab && typeof mappingsByTab === 'object'
    ? mappingsByTab
    : createDefaultMappingsByTab()
  return normalizeMappingRows(source?.[normalizedTabKey])
}

export const resolveCoreMapping = (appProductCode, processCode, mappings = []) => {
  const source = normalizeMappingRows(mappings)
  const app = normalize(appProductCode)
  const proc = normalize(processCode)
  if (!app) return { coreProductCode: '', coreProcessOrder: '', enterCount: DEFAULT_ENTER_COUNT, mapped: false }

  const exact = source.find(
    (row) => normalize(row.appProductCode) === app && normalize(row.processCode) === proc,
  )
  if (exact) {
    return {
      coreProductCode: exact.coreProductCode || appProductCode,
      coreProcessOrder: exact.coreProcessOrder || '',
      enterCount: exact.enterCount ?? DEFAULT_ENTER_COUNT,
      mapped: true,
    }
  }

  // 工程コード空のマッピングで品番一致
  const fallback = source.find(
    (row) => normalize(row.appProductCode) === app && !normalize(row.processCode),
  )
  if (fallback) {
    return {
      coreProductCode: fallback.coreProductCode || appProductCode,
      coreProcessOrder: fallback.coreProcessOrder || '',
      enterCount: fallback.enterCount ?? DEFAULT_ENTER_COUNT,
      mapped: true,
    }
  }

  return { coreProductCode: appProductCode, coreProcessOrder: '', enterCount: DEFAULT_ENTER_COUNT, mapped: false }
}
