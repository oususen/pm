<template>
  <div class="trip-progress-page">
    <div class="toolbar">
      <label class="field">
        <span>開始日</span>
        <input v-model="dateFrom" type="date" />
      </label>
      <label class="field">
        <span>終了日</span>
        <input v-model="dateTo" type="date" />
      </label>
      <label class="field">
        <span>業務区分</span>
        <select v-model="businessType">
          <option value="">すべて</option>
          <option v-for="item in businessTypes" :key="item" :value="item">{{ businessTypeLabel(item) }}</option>
        </select>
      </label>
      <label class="field">
        <span>ステータス</span>
        <select v-model="statusFilter">
          <option value="">すべて</option>
          <option value="PLANNED">未着手</option>
          <option value="LOADING">積込完了</option>
          <option value="DEPARTED">出発済</option>
          <option value="CLOSED">完了</option>
        </select>
      </label>
      <label class="field">
        <span>お気に入り</span>
        <select v-model="selectedFavoriteId" @change="applyFavorite">
          <option value="">選択</option>
          <option v-for="fav in favorites" :key="fav.id" :value="String(fav.id)">{{ fav.name }}</option>
        </select>
      </label>
      <label class="field">
        <span>登録名</span>
        <input v-model.trim="favoriteName" type="text" placeholder="お気に入り名" />
      </label>
      <button class="btn favorite-btn" title="お気に入り登録" :disabled="loading" @click="saveFavorite">★</button>
      <button class="btn" :disabled="loading" @click="loadProgress">表示</button>
      <DataSourceDialog title="" :sources="dsSources" />
    </div>

    <div class="panel">
      <h3>日別進捗</h3>
      <table class="summary-table">
        <thead>
          <tr>
            <th>出発日</th>
            <th>総便数</th>
            <th>未着手</th>
            <th>積込完了</th>
            <th>出発済</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in dailySummary" :key="row.date">
            <td>{{ row.date }}</td>
            <td class="num">{{ row.total }}</td>
            <td class="num">{{ row.planned }}</td>
            <td class="num">{{ row.loading }}</td>
            <td class="num">{{ row.departed }}</td>
          </tr>
          <tr v-if="!dailySummary.length">
            <td colspan="5" class="empty">対象データがありません。</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="panel">
      <h3>便一覧</h3>
      <table class="trip-table">
        <thead>
          <tr>
            <th>出発日</th>
            <th>業務区分</th>
            <th>便</th>
            <th>出荷担当者</th>
            <th>予定時刻</th>
            <th>実出発</th>
            <th>ステータス</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in trips" :key="row.id">
            <td>{{ row.departure_date }}</td>
            <td>{{ businessTypeLabel(row.business_type) }}</td>
            <td>{{ row.trip_code }}</td>
            <td>{{ row.shipping_staff || '-' }}</td>
            <td>{{ row.departure_time_plan || '-' }}</td>
            <td>{{ row.departure_time_actual || '-' }}</td>
            <td>{{ statusLabel(row.status) }}</td>
          </tr>
          <tr v-if="!trips.length">
            <td colspan="7" class="empty">対象便がありません。</td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '便 読み取り', table: 't_shipping_trip', desc: '便ヘッダ（ステータス・出発日時）' },
  { op: '便割付 読み取り', table: 't_shipping_trip_allocation', desc: '便ごとの製品割付明細' },
  { op: 'お気に入り 読み書き', table: 'user_favorite', desc: '画面フィルタのお気に入り保存' },
]

const formatDate = (d) => {
  const yyyy = String(d.getFullYear())
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

const today = new Date()
const nextWeek = new Date()
nextWeek.setDate(today.getDate() + 6)

const dateFrom = ref(formatDate(today))
const dateTo = ref(formatDate(nextWeek))
const businessType = ref('')
const statusFilter = ref('')
const businessTypes = ref([])
const dailySummary = ref([])
const trips = ref([])
const loading = ref(false)
const favorites = ref([])
const selectedFavoriteId = ref('')
const favoriteName = ref('')

const FAVORITE_SCREEN_KEY = 'shipping.trip_progress_summary'

const statusLabel = (status) => {
  if (status === 'PLANNED') return '未着手'
  if (status === 'LOADING') return '積込完了'
  if (status === 'DEPARTED') return '出発済'
  if (status === 'CLOSED') return '完了'
  return status || '-'
}

const businessTypeLabel = (value) => {
  const map = {
    KUBOTA_SAKAI: 'クボタ堺',
    KUBOTA_HIRAKATA: 'クボタ枚方',
    TIERA_HQ: 'ティエラ本社',
    TIERA_HOKUSHIN: 'ティエラ北進',
    TIERA_FUJISHOJI: 'ティエラ富士商事',
    TIERA_WATANABE: 'ティエラ渡辺',
  }
  return map[value] || value
}

const toFavoritePayload = () => ({
  businessType: String(businessType.value || ''),
  statusFilter: String(statusFilter.value || ''),
})

const applyFavorite = () => {
  const id = Number(selectedFavoriteId.value || 0)
  if (!id) return
  const target = favorites.value.find((item) => Number(item.id) === id)
  if (!target) return
  favoriteName.value = target.name || ''
  const payload = target.payload || {}
  businessType.value = String(payload.businessType || '')
  statusFilter.value = String(payload.statusFilter || '')
  loadProgress()
}

const loadFavorites = async () => {
  try {
    const res = await api.accounts.getFavorites({ screen_key: FAVORITE_SCREEN_KEY, page_size: 200 })
    favorites.value = Array.isArray(res.data) ? res.data : res.data?.results || []
  } catch (e) {
    console.error('お気に入り取得失敗:', e)
  }
}

const saveFavorite = async () => {
  const name = String(favoriteName.value || '').trim()
  if (!name) {
    alert('お気に入り名を入力してください。')
    return
  }
  const payload = {
    screen_key: FAVORITE_SCREEN_KEY,
    name,
    payload: toFavoritePayload(),
  }
  try {
    const id = Number(selectedFavoriteId.value || 0)
    if (id) {
      await api.accounts.updateFavorite(id, payload)
    } else {
      await api.accounts.createFavorite(payload)
    }
    await loadFavorites()
    const found = favorites.value.find((item) => item.name === name)
    selectedFavoriteId.value = found ? String(found.id) : ''
    alert('お気に入りを保存しました。')
  } catch (e) {
    const detail = e?.response?.data?.detail || e?.message || '保存に失敗しました。'
    alert(`お気に入り保存エラー: ${detail}`)
  }
}

const loadProgress = async () => {
  if (dateFrom.value > dateTo.value) {
    alert('開始日は終了日以前を指定してください。')
    return
  }
  loading.value = true
  try {
    const res = await api.shippingTrips.progress({
      date_from: dateFrom.value,
      date_to: dateTo.value,
      business_type: businessType.value || undefined,
      status: statusFilter.value || undefined,
    })
    const data = res.data || {}
    businessTypes.value = Array.isArray(data.business_types) ? data.business_types : []
    dailySummary.value = Array.isArray(data.daily_summary) ? data.daily_summary : []
    trips.value = Array.isArray(data.trips) ? data.trips : []
  } catch (error) {
    const msg = error?.response?.data?.detail || '進捗の取得に失敗しました。'
    alert(msg)
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await loadFavorites()
  await loadProgress()
})
</script>

<style scoped>
.trip-progress-page {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: flex-end;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}
.field input,
.field select {
  min-width: 160px;
  height: 32px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 0 8px;
}
.btn {
  height: 32px;
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 6px;
  padding: 0 12px;
}
.favorite-btn {
  background: #facc15;
  border-color: #eab308;
  color: #78350f;
  font-weight: 700;
  min-width: 34px;
  padding: 0 10px;
}
.panel {
  background: #fff;
  border: 1px solid #dbe2ee;
  border-radius: 10px;
  padding: 10px;
}
.panel h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.summary-table,
.trip-table {
  width: 100%;
  border-collapse: collapse;
}
.summary-table th,
.summary-table td,
.trip-table th,
.trip-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 6px 4px;
  text-align: left;
  font-size: 13px;
}
.num {
  text-align: right;
}
.empty {
  text-align: center;
  color: #64748b;
}
</style>
