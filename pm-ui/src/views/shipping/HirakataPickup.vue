<template>
  <div class="hirakata-pickup">
    <h2 class="page-title">📦 枚方集荷依頼書</h2>

    <div class="info-box">
      <h4>📋 機能説明</h4>
      <ul>
        <li>指定期間の枚方製品の出荷予定をもとに集荷依頼書PDFを生成します</li>
        <li>各日ごとの容器種類と数量が自動集計されます</li>
        <li>集荷日は製品のリードタイムを考慮して自動計算されます</li>
        <li>集荷依頼は<strong>集荷前日の17時まで</strong>にメールで送信してください</li>
      </ul>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>期間選択</h3>
      </div>
      <div class="card-body">
        <!-- 日付範囲選択 -->
        <div class="date-range-selector">
          <div class="form-group">
            <label for="start-date">開始日</label>
            <input
              id="start-date"
              v-model="startDate"
              type="date"
              class="form-control"
              @change="onDateChange"
            />
          </div>

          <div class="form-group">
            <label for="end-date">終了日</label>
            <input
              id="end-date"
              v-model="endDate"
              type="date"
              class="form-control"
              @change="onDateChange"
            />
          </div>
        </div>

        <!-- バリデーションエラー -->
        <div v-if="dateError" class="alert alert-danger">
          {{ dateError }}
        </div>

        <!-- 集荷日期間表示 -->
        <div v-if="pickupDateRange" class="pickup-range-info">
          <div class="info-item">
            <span class="label">集荷期間:</span>
            <span class="value">{{ formatDate(pickupDateRange.pickup_start_date) }} ～ {{ formatDate(pickupDateRange.pickup_end_date) }}</span>
          </div>
          <div class="info-item">
            <span class="label">納品期間:</span>
            <span class="value">{{ formatDate(pickupDateRange.delivery_start_date) }} ～ {{ formatDate(pickupDateRange.delivery_end_date) }}</span>
          </div>
        </div>

        <!-- アクションボタン -->
        <div class="action-buttons">
          <button
            @click="generatePDF"
            class="btn btn-primary"
            :disabled="loading || !isValidDateRange"
          >
            📄 集荷依頼書PDF生成
          </button>
          <button
            @click="generateExcel"
            class="btn btn-secondary"
            :disabled="loading || !isValidDateRange"
          >
            📊 集荷製品詳細Excel
          </button>
          <button
            @click="loadDailyProducts"
            class="btn btn-info"
            :disabled="loading || !isValidDateRange"
          >
            🔍 製品リスト表示
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

    <!-- 日別製品リスト -->
    <div v-if="dailyProducts && Object.keys(dailyProducts).length > 0" class="card mt-3">
      <div class="card-header">
        <h3>📋 日別製品リスト</h3>
      </div>
      <div class="card-body">
        <div v-for="(products, date) in sortedDailyProducts" :key="date" class="date-section">
          <h4 class="date-header">
            📅 {{ formatDate(date) }} ({{ products.length }}製品)
          </h4>

          <div class="table-responsive">
            <table class="table">
              <thead>
                <tr>
                  <th>製品コード</th>
                  <th>製品名</th>
                  <th class="text-right">数量</th>
                  <th>容器種類</th>
                  <th class="text-right">必要容器数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(product, index) in products" :key="index">
                  <td>{{ product.product_code }}</td>
                  <td>{{ product.product_name }}</td>
                  <td class="text-right">{{ formatNumber(product.quantity) }}</td>
                  <td>{{ product.container_name }}</td>
                  <td class="text-right">{{ product.containers_needed }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="summary-row">
                  <td colspan="2"><strong>合計</strong></td>
                  <td class="text-right"><strong>{{ formatNumber(getTotalQuantity(products)) }}</strong></td>
                  <td></td>
                  <td class="text-right"><strong>{{ getTotalContainers(products) }}</strong></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- 使い方 -->
    <div class="card mt-3">
      <div class="card-header">
        <h3>📖 使い方</h3>
      </div>
      <div class="card-body">
        <h4>集荷依頼書PDF生成の流れ</h4>
        <ol>
          <li><strong>期間選択:</strong> 開始日と終了日を選択します</li>
          <li><strong>PDF生成:</strong> 「集荷依頼書PDF生成」ボタンをクリック</li>
          <li><strong>ダウンロード:</strong> 生成されたPDFが自動的にダウンロードされます</li>
          <li><strong>メール送付:</strong> 大友ロジスティクスサービスへメールで送信</li>
        </ol>

        <h4>注意事項</h4>
        <ul>
          <li>集荷依頼は<strong>集荷前日の17時まで</strong>にメールで送信してください</li>
          <li>送信先: <code>kyouto03@otomo-logi.co.jp</code></li>
          <li>PDFには指定期間内の全ての出荷日が含まれます</li>
          <li>容器数は積載計画データから自動集計されます</li>
        </ul>

        <h4>容器種類</h4>
        <ul>
          <li><strong>ＭＭ:</strong> アミ容器</li>
          <li><strong>37N-2 #37N:</strong> グレー・緑容器</li>
          <li><strong>TP392:</strong> 青容器</li>
          <li><strong>TP331:</strong> グレー小容器</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// 状態管理
const startDate = ref('');
const endDate = ref('');
const loading = ref(false);
const loadingMessage = ref('');
const errorMessage = ref('');
const successMessage = ref('');
const dateError = ref('');
const pickupDateRange = ref(null);
const dailyProducts = ref(null);

// 初期化
onMounted(() => {
  // デフォルトで今日から7日後までを設定
  const today = new Date();
  const nextWeek = new Date();
  nextWeek.setDate(today.getDate() + 7);

  startDate.value = formatDateForInput(today);
  endDate.value = formatDateForInput(nextWeek);

  // 初期表示時に集荷日期間を取得
  fetchPickupDateRange();
});

// 日付範囲の妥当性チェック
const isValidDateRange = computed(() => {
  if (!startDate.value || !endDate.value) return false;
  if (dateError.value) return false;
  return new Date(startDate.value) <= new Date(endDate.value);
});

// 日別製品リストをソート
const sortedDailyProducts = computed(() => {
  if (!dailyProducts.value) return {};

  const sorted = {};
  Object.keys(dailyProducts.value)
    .sort()
    .forEach(date => {
      sorted[date] = dailyProducts.value[date];
    });

  return sorted;
});

// 日付変更時の処理
const onDateChange = () => {
  dateError.value = '';
  successMessage.value = '';
  errorMessage.value = '';

  if (!startDate.value || !endDate.value) return;

  if (new Date(startDate.value) > new Date(endDate.value)) {
    dateError.value = '開始日は終了日より前である必要があります';
    pickupDateRange.value = null;
    return;
  }

  // 日付が有効な場合、集荷日期間を取得
  fetchPickupDateRange();
};

// 集荷日期間を取得
const fetchPickupDateRange = async () => {
  if (!isValidDateRange.value) return;

  try {
    const response = await axios.get(
      `${API_BASE_URL}/hirakata-pickup/date-range/`,
      {
        params: {
          start_date: startDate.value,
          end_date: endDate.value
        }
      }
    );
    pickupDateRange.value = response.data;
  } catch (error) {
    console.error('集荷日期間取得エラー:', error);
    pickupDateRange.value = null;
  }
};

// PDF生成
const generatePDF = async () => {
  loading.value = true;
  loadingMessage.value = 'PDFを生成中...';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.post(
      `${API_BASE_URL}/hirakata-pickup/generate-pdf/`,
      {
        start_date: startDate.value,
        end_date: endDate.value
      },
      {
        responseType: 'blob'
      }
    );

    // ファイル名をレスポンスヘッダーから取得（フォールバック付き）
    const contentDisposition = response.headers['content-disposition'];
    let filename = '枚方集荷依頼書.pdf';
    if (contentDisposition) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }

    // Blobからダウンロードリンクを作成
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    successMessage.value = 'PDF生成が完了しました';
  } catch (error) {
    console.error('PDF生成エラー:', error);
    errorMessage.value = error.response?.data?.error || 'PDF生成中にエラーが発生しました';
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

// Excel生成
const generateExcel = async () => {
  loading.value = true;
  loadingMessage.value = 'Excelを生成中...';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.post(
      `${API_BASE_URL}/hirakata-pickup/generate-excel/`,
      {
        start_date: startDate.value,
        end_date: endDate.value
      },
      {
        responseType: 'blob'
      }
    );

    // ファイル名をレスポンスヘッダーから取得（フォールバック付き）
    const contentDisposition = response.headers['content-disposition'];
    let filename = '枚方集荷製品詳細.xlsx';
    if (contentDisposition) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(contentDisposition);
      if (matches != null && matches[1]) {
        filename = matches[1].replace(/['"]/g, '');
      }
    }

    // Blobからダウンロードリンクを作成
    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    successMessage.value = 'Excel生成が完了しました';
  } catch (error) {
    console.error('Excel生成エラー:', error);
    errorMessage.value = error.response?.data?.error || 'Excel生成中にエラーが発生しました';
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

// 日別製品リスト取得
const loadDailyProducts = async () => {
  loading.value = true;
  loadingMessage.value = '製品リストを取得中...';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await axios.get(
      `${API_BASE_URL}/hirakata-pickup/daily-products/`,
      {
        params: {
          start_date: startDate.value,
          end_date: endDate.value
        }
      }
    );

    dailyProducts.value = response.data;

    if (Object.keys(response.data).length === 0) {
      errorMessage.value = '対象期間に出荷予定の製品がありません';
    } else {
      successMessage.value = '製品リストを取得しました';
    }
  } catch (error) {
    console.error('製品リスト取得エラー:', error);
    errorMessage.value = error.response?.data?.error || '製品リスト取得中にエラーが発生しました';
    dailyProducts.value = null;
  } finally {
    loading.value = false;
    loadingMessage.value = '';
  }
};

// 日付フォーマット（input用）
const formatDateForInput = (date) => {
  const d = new Date(date);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// 日付フォーマット（表示用）
const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
};

// 数値フォーマット
const formatNumber = (num) => {
  return new Intl.NumberFormat('ja-JP').format(num);
};

// 合計数量計算
const getTotalQuantity = (products) => {
  return products.reduce((sum, p) => sum + (p.quantity || 0), 0);
};

// 合計容器数計算
const getTotalContainers = (products) => {
  return products.reduce((sum, p) => sum + (p.containers_needed || 0), 0);
};
</script>

<style scoped>
.hirakata-pickup {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 20px;
  color: #333;
}

.info-box {
  background-color: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 15px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.info-box h4 {
  margin-top: 0;
  color: #1976d2;
}

.info-box ul {
  margin-bottom: 0;
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
  background-color: #f5f5f5;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.card-body {
  padding: 20px;
}

.date-range-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
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
  border-color: #2196f3;
  box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
}

.pickup-range-info {
  background-color: #f5f5f5;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-item .label {
  font-weight: 600;
  margin-right: 10px;
  min-width: 80px;
  color: #666;
}

.info-item .value {
  color: #333;
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
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #2196f3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1976d2;
}

.btn-secondary {
  background-color: #757575;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #616161;
}

.btn-info {
  background-color: #00bcd4;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background-color: #0097a7;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e0e0e0;
  border-top-color: #2196f3;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.alert {
  padding: 12px 16px;
  border-radius: 4px;
  margin-top: 15px;
}

.alert-danger {
  background-color: #ffebee;
  color: #c62828;
  border-left: 4px solid #f44336;
}

.alert-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border-left: 4px solid #4caf50;
}

.mt-3 {
  margin-top: 20px;
}

.date-section {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.date-section:last-child {
  border-bottom: none;
}

.date-header {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 15px;
  color: #333;
}

.table-responsive {
  overflow-x: auto;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.table th,
.table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.table th {
  background-color: #f5f5f5;
  font-weight: 600;
  color: #555;
}

.table tbody tr:hover {
  background-color: #f9f9f9;
}

.table .text-right {
  text-align: right;
}

.summary-row {
  background-color: #f5f5f5;
  font-weight: 600;
}

.summary-row td {
  border-top: 2px solid #333;
}

@media (max-width: 768px) {
  .date-range-selector {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
