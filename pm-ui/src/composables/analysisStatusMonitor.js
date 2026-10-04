import { ref } from 'vue'

// 開発用の暫定値。実行期限ではなく、画面のGET監視だけを制限する。
export const STATUS_INTERVAL_MS = 3000
export const STATUS_LIMIT_MS = 20 * 60 * 1000
export const STATUS_FAILURE_LIMIT = 3
const progress = ['pending', 'running', 'cancel_requested']
const endings = ['success', 'failed', 'cancelled', 'expired', 'unknown']
const messages = {
  hidden: '画面が非表示の間は自動更新を一時停止しています。',
  limit: '自動更新の上限20分に達しました。手動で再取得してください。実行を中止したわけではありません。',
  failures: '状態の取得に3回続けて失敗しました。手動で再取得してください。',
  missing: '実行情報が見つからないか、保持期限が切れています。自動更新を停止しました。履歴・後始末を確認してください。',
  forbidden: '実行情報を取得する権限を確認できません。自動更新を停止しました。',
  unknown: '状態不明のため自動更新を停止しました。手動取得または管理者による確認が必要です。',
  ended: '終了状態を確認したため自動更新を停止しました。',
  invalid: '実行状態を確認できないため自動更新を停止しました。手動で再取得してください。',
}

// タイマー・単調時計を差し替えて検証できる、状態GET専用の窓口。
export function createAnalysisStatusMonitor({ request, apply, manualError, canRead = () => true,
  now = () => performance.now(), later = (fn, ms) => setTimeout(fn, ms), clear = id => clearTimeout(id) }) {
  const message = ref(''), notice = ref(null), acknowledged = ref(false), reading = ref(false)
  let target = null, status = null, started = null, failures = 0, halted = '', visible = true
  let disposed = false, revision = 0, timer = null, deadline = null, pending = null, controller = null
  let documentRef = null, panelVisible = true, resumeImmediately = false, ackRevision = 0
  function clearTimers() { clear(timer); clear(deadline); timer = deadline = null }
  function acknowledge() { acknowledged.value = true; ackRevision++ }
  function invalidate() { revision++; controller?.abort(); clear(timer); timer = null }
  function stop(reason, abort = true) {
    halted = reason; message.value = messages[reason] || ''; clearTimers()
    if (abort) invalidate()
  }
  function withinLimit() { return started === null || now() - started < STATUS_LIMIT_MS }
  function schedule(delay = STATUS_INTERVAL_MS) {
    clearTimers()
    if (disposed || !target || halted || !visible || (!progress.includes(status) && status !== null)) return
    if (!withinLimit()) { stop('limit'); return }
    if (started === null) started = now()
    deadline = later(() => stop('limit'), STATUS_LIMIT_MS - (now() - started))
    if (!pending) timer = later(() => {
      timer = null
      if (canRead()) read(false)
      else schedule()
    }, delay)
  }
  function track(id, nextStatus = null) {
    if (disposed) return
    if (id !== target) {
      invalidate(); clearTimers(); target = id || null; started = null; failures = 0; halted = ''
      notice.value = null; acknowledged.value = false; message.value = ''; resumeImmediately = nextStatus === null
    }
    status = nextStatus
    if (!target) { clearTimers(); return }
    if (endings.includes(status)) { stop(status === 'unknown' ? 'unknown' : 'ended', false); return }
    if (status !== null && !progress.includes(status)) { stop('invalid'); return }
    if (!visible) { message.value = messages.hidden; return }
    schedule(resumeImmediately ? 0 : STATUS_INTERVAL_MS)
  }
  async function read(manual = false) {
    if (manual) acknowledge()
    if (disposed || !target || (!manual && (halted || !visible || !withinLimit()))) return
    // 手動と自動のGETを共有する。旧ジョブの取得も終了するまで重ねない。
    if (pending) {
      const current = target, existing = pending
      if (manual) existing.manualRequested = true
      await existing.promise
      if (!disposed && current === target && pending === null && current !== existing.id) return read(manual)
      return
    }
    if (!manual && !canRead()) { schedule(); return }
    const id = target, version = revision, previous = status, ackAtStart = ackRevision
    const token = { id, promise: null, manualRequested: manual }
    clear(timer); timer = null; resumeImmediately = false
    controller = new AbortController(); const signal = controller.signal
    reading.value = true
    token.promise = (async () => {
      // 同期的に通信準備が失敗しても、取得枠を確保してから後始末する。
      await Promise.resolve()
      try {
        if (disposed || version !== revision || id !== target || signal.aborted) return
        const data = await request(id, signal)
        if (disposed || version !== revision || id !== target || (!manual && !visible)) return
        if (data?.id !== id) { stop('invalid', false); if (token.manualRequested) manualError(); return }
        failures = 0; halted = ''; message.value = ''; status = data.status
        if (notice.value && notice.value.status !== status) notice.value = null
        apply(data)
        if (!manual && progress.includes(previous) && endings.includes(status)) {
          notice.value = { status, cleanupComplete: ['db_connection', 'container'].every(k => ['closed', 'not_started'].includes(data.cleanup?.[k])) }
          acknowledged.value = ackAtStart !== ackRevision
        }
        if (endings.includes(status)) stop(status === 'unknown' ? 'unknown' : 'ended', false)
        else if (!progress.includes(status)) stop('invalid', false)
      } catch (e) {
        if (disposed || version !== revision || id !== target || signal.aborted) return
        if (token.manualRequested) manualError()
        const code = e.response?.status
        if ([404, 410].includes(code)) stop('missing', false)
        else if ([401, 403].includes(code)) stop('forbidden', false)
        else if (previous === null) stop('invalid', false) // 初回照合で進行中と確認できなければ監視しない。
        else if (++failures >= STATUS_FAILURE_LIMIT) stop('failures', false)
        else message.value = '状態を取得できませんでした。間隔を延ばして再取得します。'
      } finally {
        if (pending === token) {
          pending = null; controller = null; reading.value = false
          schedule(resumeImmediately ? 0 : STATUS_INTERVAL_MS * 2 ** failures)
        }
      }
    })()
    pending = token
    await token.promise
  }
  function setVisible(value) {
    panelVisible = value
    const next = panelVisible && !documentRef?.hidden
    if (next === visible || disposed) return
    visible = next
    if (!visible) { invalidate(); clearTimers(); if (target && !halted) message.value = messages.hidden }
    else if (!halted && target) { message.value = ''; resumeImmediately = true; schedule(0) }
  }
  function visibilityChanged() { setVisible(panelVisible) }
  function mount(doc) {
    documentRef = doc; documentRef?.addEventListener('visibilitychange', visibilityChanged)
    visibilityChanged()
  }
  function dispose() {
    disposed = true; invalidate(); clearTimers()
    documentRef?.removeEventListener('visibilitychange', visibilityChanged)
  }
  return { message, notice, acknowledged, reading, acknowledge, invalidate, track, read, setVisible, mount, dispose }
}
