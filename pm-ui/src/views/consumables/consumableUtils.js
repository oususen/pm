// 消耗品画面の共通処理

// page_size=0 は全件返却（配列）。ページング形式にも対応する
export const rowsOf = (res) => (Array.isArray(res.data) ? res.data : res.data?.results || [])

export const errorMessage = (err) => {
  const data = err?.response?.data
  if (!data) return err?.message || 'エラーが発生しました'
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  return Object.entries(data)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`)
    .join('\n')
}

export const formatPrice = (v) => Number(v || 0).toLocaleString('ja-JP')

export const formatDateTime = (v) => {
  if (!v) return ''
  const d = new Date(v)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// ローカル日付 YYYY-MM-DD（toISOString はUTC変換で日付がずれるため使わない）
export const toLocalDateString = (d) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

// 業務日（日替わり8時）の今日
export const businessToday = () => {
  const now = new Date()
  if (now.getHours() < 8) now.setDate(now.getDate() - 1)
  return now
}
