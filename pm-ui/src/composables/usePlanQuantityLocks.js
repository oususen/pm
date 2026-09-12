import { ref, watch } from 'vue'
import api from '@/api/client'

// ロックは日×製品の数量を保持する。ロット順序は固定しない。
export function usePlanQuantityLocks({ lineId, startDate, endDate, rows, processing, canEdit }) {
  const lockMode = ref(false)
  const lockedQuantities = ref(new Map())
  const locksReady = ref(false)
  const lockBusy = ref(false)
  const keyOf = (day, product) => `${day}_${product}`
  const total = (daily) => Number(daily?.plan || 0) +
    (daily?.extraLots || []).reduce((sum, lot) => sum + Number(lot.plan_qty || 0), 0)

  watch([lineId, startDate, endDate], () => {
    lockMode.value = false
    lockedQuantities.value = new Map()
    locksReady.value = false
  }, { flush: 'sync' })

  const fetchLocks = async () => {
    const scope = [lineId.value, startDate.value, endDate.value].join('|')
    locksReady.value = false
    if (!lineId.value) return
    const res = await api.productionLock.list({
      lock_type: 'auto_plan', line_id: lineId.value, start: startDate.value, end: endDate.value,
    })
    if (scope !== [lineId.value, startDate.value, endDate.value].join('|')) {
      throw new Error('表示条件が変更されました。再表示してください。')
    }
    if (!Array.isArray(res.data)) throw new Error('ロック情報を取得できませんでした。')
    lockedQuantities.value = new Map(res.data.map(lock => [keyOf(lock.plan_date, lock.product_id), Number(lock.locked_qty)]))
    locksReady.value = true
  }
  const isLocked = (day, product) => lockedQuantities.value.has(keyOf(day, product))
  const hasLocksOnDate = (day) => [...lockedQuantities.value.keys()].some(key => key.startsWith(`${day}_`))
  const applyQuantities = (from = startDate.value, to = endDate.value) => {
    if (!locksReady.value) throw new Error('ロック情報を再取得してください。')
    for (const row of rows.value) {
      for (const [day, daily] of Object.entries(row.daily || {})) {
        const key = keyOf(day, row.product_id)
        if (day < from || day > to || !lockedQuantities.value.has(key)) continue
        const qty = lockedQuantities.value.get(key)
        if (total(daily) === qty) continue
        daily.plan = qty
        if (Array.isArray(daily.extraLots)) daily.extraLots = []
      }
    }
  }
  const toggleLock = async (day, product) => {
    if (!lineId.value || processing.value || lockBusy.value || !locksReady.value || (canEdit && !canEdit.value)) return
    const row = rows.value.find(r => Number(r.product_id) === Number(product))
    const daily = row?.daily?.[day]
    if (!daily) return
    const key = keyOf(day, product)
    const scope = lineId.value
    const payload = { lock_type: 'auto_plan', line_id: scope, plan_date: day, product_id: product }
    lockBusy.value = true
    try {
      if (isLocked(day, product)) {
        await api.productionLock.unlock(payload)
        if (lineId.value === scope) lockedQuantities.value.delete(key)
      } else {
        const qty = total(daily)
        if (!Number.isFinite(qty) || qty < 0) {
          alert('計画数は0以上の数値で入力してください。')
          return
        }
        const res = await api.productionLock.lock({ ...payload, locked_qty: qty })
        if (lineId.value === scope) lockedQuantities.value.set(key, Number(res.data.locked_qty))
      }
    } catch (e) {
      alert(e?.response?.data?.detail || 'ロックの切替に失敗しました。再表示してください。')
    } finally {
      lockBusy.value = false
    }
  }
  return { lockMode, lockedQuantities, locksReady, lockBusy, fetchLocks, isLocked, hasLocksOnDate, applyQuantities, toggleLock }
}
