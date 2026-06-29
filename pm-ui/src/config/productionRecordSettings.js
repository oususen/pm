const TARGET_LINE_CODES_KEY = 'production_record_target_line_codes'
const PRODUCT_MAPPINGS_KEY = 'production_record_product_mappings'
const DEFAULT_ENTER_COUNT = 2

const TAB_KEYS = ['tank', 'floor', 'team2', 'blade', 'laser', 'brake']
const DEFAULT_TARGET_LINE_CODES_BY_TAB = {
  tank: ['L2200', 'L2201'],
  floor: ['L2100'],
  team2: ['L2200', 'L2201', 'L2100'],
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
  team2: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.team2],
  blade: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.blade],
  laser: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.laser],
  brake: [...DEFAULT_TARGET_LINE_CODES_BY_TAB.brake],
})

export const normalizeTargetLineCodesByTab = (lineCodesByTab) => {
  const base = createDefaultTargetLineCodesByTab()
  TAB_KEYS.forEach((tabKey) => {
    base[tabKey] = normalizeLineCodes(lineCodesByTab?.[tabKey] ?? base[tabKey])
  })
  if (lineCodesByTab && typeof lineCodesByTab === 'object' && !Array.isArray(lineCodesByTab)) {
    Object.keys(lineCodesByTab).forEach((tabKey) => {
      if (!(tabKey in base)) {
        base[tabKey] = normalizeLineCodes(lineCodesByTab[tabKey])
      }
    })
  }
  return base
}

export const loadTargetLineCodesByTab = () => {
  const defaults = createDefaultTargetLineCodesByTab()
  if (!canUseStorage()) return defaults

  const raw = window.localStorage.getItem(TARGET_LINE_CODES_KEY)
  const parsed = parseJson(raw, null)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return defaults

  return normalizeTargetLineCodesByTab(parsed)
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

export const normalizeProductMappings = (mappings) => {
  if (Array.isArray(mappings)) return normalizeMappingRows(mappings)
  // 旧形式（タブ別オブジェクト）→ フラット化
  if (mappings && typeof mappings === 'object') {
    const seen = new Set()
    const result = []
    for (const tabKey of Object.keys(mappings)) {
      for (const row of normalizeMappingRows(mappings[tabKey])) {
        const key = `${row.appProductCode}__${row.processCode}`
        if (!seen.has(key)) {
          seen.add(key)
          result.push(row)
        }
      }
    }
    return result
  }
  return []
}

export const loadProductMappings = () => {
  if (!canUseStorage()) return []
  const raw = window.localStorage.getItem(PRODUCT_MAPPINGS_KEY)
  const parsed = parseJson(raw, null)
  if (parsed === null) return []
  return normalizeProductMappings(parsed)
}

export const saveProductMappings = (mappings) => {
  const normalized = normalizeMappingRows(Array.isArray(mappings) ? mappings : [])
  if (canUseStorage()) {
    window.localStorage.setItem(PRODUCT_MAPPINGS_KEY, JSON.stringify(normalized))
  }
  return normalized
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

  // マッピング未設定時のみ固定ルールを適用
  // 工程4010/4040: 末尾B削除 / 工順020 / Enter回数2
  if (proc === '4010' || proc === '4040') {
    return {
      coreProductCode: String(appProductCode || '').replace(/[BＢ]$/i, ''),
      coreProcessOrder: '020',
      enterCount: 2,
      mapped: true,
    }
  }
  // 工程4013: 品番そのまま / 工順010 / Enter回数1
  if (proc === '4013') {
    return {
      coreProductCode: String(appProductCode || ''),
      coreProcessOrder: '010',
      enterCount: 1,
      mapped: true,
    }
  }

  return { coreProductCode: appProductCode, coreProcessOrder: '', enterCount: DEFAULT_ENTER_COUNT, mapped: false }
}
