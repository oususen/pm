// 単調時計とタイマーだけを模擬し、HTTP・実AIを呼ばない。
export function fakeClock() {
  let time = 0, next = 0
  const timers = new Map()
  const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
  return {
    now: () => time,
    later: (fn, delay) => { const id = ++next; timers.set(id, { at: time + delay, fn }); return id },
    clear: id => timers.delete(id),
    size: () => timers.size,
    flush,
    async advance(ms) {
      const end = time + ms
      await flush()
      while (true) {
        const due = [...timers].filter(([, timer]) => timer.at <= end).sort((a, b) => a[1].at - b[1].at)[0]
        if (!due) break
        time = due[1].at; timers.delete(due[0]); due[1].fn(); await flush()
      }
      time = end; await flush()
    },
  }
}

export function fakeDocument() {
  const listeners = new Set()
  return { hidden: false, listeners,
    addEventListener: (name, fn) => { if (name === 'visibilitychange') listeners.add(fn) },
    removeEventListener: (name, fn) => { if (name === 'visibilitychange') listeners.delete(fn) },
    hide(value) { this.hidden = value; for (const fn of listeners) fn() },
  }
}
