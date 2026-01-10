<template>
  <div class="shipping-order-document">
    <h2 class="page-title">出荷指示書</h2>

    <div class="card">
      <div class="card-header">
        <h3>出荷指示書生成</h3>
      </div>
      <div class="card-body">
        <!-- 日付選択 -->
        <div class="form-group">
          <label for="target-date">出荷日</label>
          <div class="date-selector">
            <input
              id="target-date"
              v-model="targetDate"
              type="date"
              class="form-control"
              :min="minDate"
            />
            <button @click="loadAvailableDates" class="btn btn-secondary" :disabled="loading">
              📅 利用可能な日付を表示
            </button>
          </div>
        </div>

        <!-- 利用可能な日付リスト -->
        <div v-if="availableDates.length > 0" class="available-dates">
          <h4>利用可能な日付（本日以降）</h4>
          <div class="date-chips">
            <button
              v-for="date in availableDates"
              :key="date"
              @click="selectDate(date)"
              class="date-chip"
              :class="{ active: targetDate === date }"
            >
              {{ formatDate(date) }}
            </button>
          </div>
        </div>

        <!-- 作成者名 -->
        <div class="form-group">
          <label for="creator-name">作成者名</label>
          <input
            id="creator-name"
            v-model="creatorName"
            type="text"
            class="form-control"
            placeholder="例: 山田太郎"
          />
        </div>

        <!-- アクションボタン -->
        <div class="action-buttons">
          <button
            @click="previewData"
            class="btn btn-info"
            :disabled="loading || !targetDate"
          >
            🔍 データプレビュー
          </button>
          <button
            @click="generatePDF"
            class="btn btn-primary"
            :disabled="loading || !targetDate || !creatorName"
          >
            📄 PDF生成
          </button>
        </div>

        <!-- ローディング表示 -->
        <div v-if="loading" class="loading-indicator">
          <div class="spinner"></div>
          <p>{{ loadingMessage }}</p>
        </div>

        <!-- エラーメッセージ -->
        <div v-if="errorMessage" class="alert alert-danger">
          {{ errorMessage }}
        </div>

        <!-- 成功メッセージ -->
        <div v-if="successMessage" class="alert alert-success">
          {{ successMessage }}
        </div>
      </div>
    </div>

    <!-- データプレビュー -->
    <div v-if="showPreview" class="card mt-3">
      <div class="card-header">
        <h3>出荷データプレビュー - {{ formatDate(targetDate) }}</h3>
      </div>
      <div class="card-body">
        <!-- 注意事項 -->
        <div v-if="shippingData.attachment_note" class="alert alert-warning">
          <strong>⚠️ 注意:</strong> {{ shippingData.attachment_note }}
        </div>

        <!-- 統計情報 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">1便目 (06:00)</div>
            <div class="stat-value">{{ formatTripCount(shippingData.trip1) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">2便目 (06:30)</div>
            <div class="stat-value">{{ formatTripCount(shippingData.trip2) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">3便目 (10:00)</div>
            <div class="stat-value">{{ formatTripCount(shippingData.trip3) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">4便目 (13:00)</div>
            <div class="stat-value">{{ formatTripCount(shippingData.trip4) }}</div>
          </div>
        </div>

        <!-- 各便の詳細 -->
        <div class="trip-details">
          <!-- 1便目 -->
          <div class="trip-section">
            <h4>1便目 (AM 06:00) - 4t／5tブレード(1)</h4>
            <div v-if="trip1Items.length > 0" class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>製品コード</th>
                    <th>製品名</th>
                    <th>機種名</th>
                    <th>Cテーブル</th>
                    <th>数量</th>
                    <th>容器入り数</th>
                    <th>グループ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in trip1Items" :key="index">
                    <td>{{ item.product_code }}</td>
                    <td>{{ item.product_name }}</td>
                    <td>{{ item.model_name || '-' }}</td>
                    <td>{{ item.c_table_no || '-' }}</td>
                    <td class="text-right">{{ item.order_quantity }}</td>
                    <td class="text-right">{{ item.capacity || '-' }}</td>
                    <td>{{ item.group_name || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-message">該当する製品がありません</div>
          </div>

          <!-- 2便目 -->
          <div class="trip-section">
            <h4>2便目 (AM 06:30) - ブレード</h4>
            <div v-if="shippingData.trip2 && shippingData.trip2.length > 0" class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>製品コード</th>
                    <th>製品名</th>
                    <th>機種名</th>
                    <th>数量</th>
                    <th>容器入り数</th>
                    <th>グループ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in shippingData.trip2" :key="index">
                    <td>{{ item.product_code }}</td>
                    <td>{{ item.product_name }}</td>
                    <td>{{ item.model_name || '-' }}</td>
                    <td class="text-right">{{ item.order_quantity }}</td>
                    <td class="text-right">{{ item.capacity || '-' }}</td>
                    <td>{{ item.group_name || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-message">該当する製品がありません</div>

            <!-- 特記事項 -->
            <div v-if="shippingData.trip2_special_annotations && shippingData.trip2_special_annotations.length > 0" class="special-annotations">
              <h5>特記事項</h5>
              <ul>
                <li v-for="(ann, index) in shippingData.trip2_special_annotations" :key="index">
                  {{ ann.group_code }}: {{ ann.containers }}容器
                </li>
              </ul>
            </div>
          </div>

          <!-- 3便目 -->
          <div class="trip-section">
            <h4>3便目 (AM 10:00) - オイルタンク・シートベース</h4>
            <div v-if="shippingData.trip3 && shippingData.trip3.length > 0" class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>製品コード</th>
                    <th>製品名</th>
                    <th>機種名</th>
                    <th>数量</th>
                    <th>容器入り数</th>
                    <th>グループ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in shippingData.trip3" :key="index">
                    <td>{{ item.product_code }}</td>
                    <td>{{ item.product_name }}</td>
                    <td>{{ item.model_name || '-' }}</td>
                    <td class="text-right">{{ item.order_quantity }}</td>
                    <td class="text-right">{{ item.capacity || '-' }}</td>
                    <td>{{ item.group_name || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-message">該当する製品がありません</div>
          </div>

          <!-- 4便目 -->
          <div class="trip-section">
            <h4>4便目 (PM 13:00) - 4t／5tブレード(2)</h4>
            <div v-if="trip4Items.length > 0" class="table-responsive">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>製品コード</th>
                    <th>製品名</th>
                    <th>機種名</th>
                    <th>Cテーブル</th>
                    <th>数量</th>
                    <th>容器入り数</th>
                    <th>グループ</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, index) in trip4Items" :key="index">
                    <td>{{ item.product_code }}</td>
                    <td>{{ item.product_name }}</td>
                    <td>{{ item.model_name || '-' }}</td>
                    <td>{{ item.c_table_no || '-' }}</td>
                    <td class="text-right">{{ item.order_quantity }}</td>
                    <td class="text-right">{{ item.capacity || '-' }}</td>
                    <td>{{ item.group_name || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-message">該当する製品がありません</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

// 状態管理
const targetDate = ref('');
const creatorName = ref('システム');
const loading = ref(false);
const loadingMessage = ref('');
const errorMessage = ref('');
const successMessage = ref('');
const availableDates = ref([]);
const shippingData = ref({
  date: null,
  trip1: [],
  trip2: [],
  trip3: [],
  trip4: [],
  trip2_special_annotations: [],
  attachment_note: null
});
const showPreview = ref(false);

// 計算プロパティ
const minDate = computed(() => {
  const today = new Date();
  return today.toISOString().split('T')[0];
});

const countUniqueItems = (items) => {
  if (!Array.isArray(items)) return 0;
  const seen = new Set();
  items.forEach((item, index) => {
    const key = item?.product_code || item?.order_id || item?.product_name || `idx:${index}`;
    seen.add(key);
  });
  return seen.size;
};

const nonZeroItems = (items) => {
  if (!Array.isArray(items)) return [];
  return items.filter((item) => Number(item?.order_quantity || 0) > 0);
};

const trip1Items = computed(() => nonZeroItems(shippingData.value.trip1));
const trip4Items = computed(() => nonZeroItems(shippingData.value.trip4));

const formatTripCount = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return '0/0品目';
  }
  const targetCount = countUniqueItems(items);
  const loadedCount = countUniqueItems(nonZeroItems(items));
  return `${loadedCount}/${targetCount}品目`;
};

// メソッド
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = weekdays[date.getDay()];
  return `${month}月${day}日(${weekday})`;
};

const loadAvailableDates = async () => {
  loading.value = true;
  loadingMessage.value = '利用可能な日付を取得中...';
  errorMessage.value = '';

  try {
    const response = await axios.get('/api/shipping/available-dates/');
    const rawDates = response.data.dates || [];
    const today = minDate.value;
    availableDates.value = rawDates.filter((date) => date >= today);

    if (availableDates.value.length === 0) {
      errorMessage.value = '出荷データが存在しません';
    }
  } catch (error) {
    console.error('日付取得エラー:', error);
    errorMessage.value = '日付の取得に失敗しました: ' + (error.response?.data?.error || error.message);
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

const selectDate = (date) => {
  targetDate.value = date;
  errorMessage.value = '';
  successMessage.value = '';
};

const previewData = async () => {
  if (!targetDate.value) {
    errorMessage.value = '出荷日を選択してください';
    return;
  }

  loading.value = true;
  loadingMessage.value = '出荷データを取得中...';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.get(`/api/shipping/order-data/${targetDate.value}/`);
    shippingData.value = response.data;
    showPreview.value = true;
    successMessage.value = 'データを取得しました';
  } catch (error) {
    console.error('データ取得エラー:', error);
    errorMessage.value = 'データの取得に失敗しました: ' + (error.response?.data?.error || error.message);
    showPreview.value = false;
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

const generatePDF = async () => {
  if (!targetDate.value) {
    errorMessage.value = '出荷日を選択してください';
    return;
  }

  if (!creatorName.value) {
    errorMessage.value = '作成者名を入力してください';
    return;
  }

  loading.value = true;
  loadingMessage.value = 'PDFを生成中...';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.post(
      '/api/shipping/generate-pdf/',
      {
        target_date: targetDate.value,
        creator_name: creatorName.value,
      },
      {
        responseType: 'blob',
      }
    );

    // PDFをダウンロード
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `出荷指示書_${targetDate.value}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    successMessage.value = 'PDFを生成しました';
  } catch (error) {
    console.error('PDF生成エラー:', error);
    errorMessage.value = 'PDFの生成に失敗しました: ' + (error.response?.data?.error || error.message);
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

// 初期化
onMounted(() => {
  // 今日の日付をデフォルトに設定
  const today = new Date();
  targetDate.value = today.toISOString().split('T')[0];
});
</script>

<style scoped>
.shipping-order-document {
  padding: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #2c3e50;
}

.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.card-header {
  padding: 15px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.card-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #555;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.1);
}

.date-selector {
  display: flex;
  gap: 10px;
  align-items: center;
}

.date-selector input {
  flex: 1;
  max-width: 200px;
}

.available-dates {
  margin: 20px 0;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 4px;
}

.available-dates h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #666;
}

.date-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.date-chip {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: white;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.date-chip:hover {
  background: #f0f0f0;
}

.date-chip.active {
  background: #4caf50;
  color: white;
  border-color: #4caf50;
}

.action-buttons {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #4caf50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #5a6268;
}

.btn-info {
  background: #17a2b8;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #138496;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-top: 20px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.alert {
  padding: 15px;
  border-radius: 4px;
  margin-top: 20px;
}

.alert-danger {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.alert-success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.alert-warning {
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.stat-card {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #2c3e50;
}

.trip-details {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.trip-section {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 15px;
}

.trip-section h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  color: #2c3e50;
  padding-bottom: 10px;
  border-bottom: 2px solid #4caf50;
}

.table-responsive {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.table th,
.table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #555;
  font-size: 13px;
}

.table td {
  font-size: 14px;
}

.table tr:hover {
  background: #f8f9fa;
}

.text-right {
  text-align: right !important;
}

.empty-message {
  padding: 40px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.special-annotations {
  margin-top: 15px;
  padding: 15px;
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  border-radius: 4px;
}

.special-annotations h5 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  color: #856404;
}

.special-annotations ul {
  margin: 0;
  padding-left: 20px;
}

.special-annotations li {
  margin-bottom: 5px;
  color: #856404;
}

.mt-3 {
  margin-top: 20px;
}
</style>
