import api from '@/api/client'

const normalizeCalendarId = (value) => {
  if (!value) return null
  if (typeof value === 'object') return value.id ?? null
  return value
}

const resolveLineObject = async (lineId, lineCandidates = []) => {
  const found = (Array.isArray(lineCandidates) ? lineCandidates : []).find(
    (line) => String(line?.id) === String(lineId)
  )
  if (found) return found
  const res = await api.lines.getLine(lineId)
  return res.data || null
}

const buildLineLabel = (line) => {
  const code = String(line?.line_code || '').trim()
  const name = String(line?.line_name || '').trim()
  if (code && name) return `${code} ${name}`
  return code || name || '対象ライン'
}

const toDateKey = (value) => String(value || '').slice(0, 10)

const getDateKeysInRange = (startDate, endDate) => {
  const start = toDateKey(startDate)
  const end = toDateKey(endDate)
  if (!start || !end || start > end) return []

  const result = []
  const current = new Date(`${start}T00:00:00`)
  const last = new Date(`${end}T00:00:00`)
  while (current <= last) {
    const year = current.getFullYear()
    const month = String(current.getMonth() + 1).padStart(2, '0')
    const day = String(current.getDate()).padStart(2, '0')
    result.push(`${year}-${month}-${day}`)
    current.setDate(current.getDate() + 1)
  }
  return result
}

export const ensureLineCalendarReady = async ({
  lineId,
  lineCandidates = [],
  actionLabel = '実行',
  startDate = '',
  endDate = '',
}) => {
  if (!lineId) {
    window.alert(`ラインを選択してから${actionLabel}してください。`)
    return false
  }

  let line = null
  try {
    line = await resolveLineObject(lineId, lineCandidates)
  } catch (error) {
    window.alert(`ライン情報の取得に失敗したため${actionLabel}できません。`)
    return false
  }

  const lineLabel = buildLineLabel(line)
  const calendarId = normalizeCalendarId(line?.calendar)
  if (!calendarId) {
    window.alert(`ライン ${lineLabel} の勤務カレンダが未設定のため${actionLabel}できません。`)
    return false
  }

  try {
    const dateKeys = getDateKeysInRange(startDate, endDate)
    const params = dateKeys.length
      ? { target_date__gte: dateKeys[0], target_date__lte: dateKeys.at(-1) }
      : {}
    const res = await api.calendars.getCalendarDays(calendarId, params)
    const rows = res.data?.results || res.data || []
    if (!Array.isArray(rows) || rows.length === 0) {
      window.alert(`ライン ${lineLabel} の勤務カレンダに日別設定がないため${actionLabel}できません。`)
      return false
    }
    const hasWorkingDay = rows.some((row) => row?.is_working_day)
    if (!hasWorkingDay) {
      window.alert(`ライン ${lineLabel} の勤務カレンダに出勤日がないため${actionLabel}できません。`)
      return false
    }
  } catch (error) {
    window.alert(`勤務カレンダの確認に失敗したため${actionLabel}できません。`)
    return false
  }

  return true
}
