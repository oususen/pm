<template>
  <div class="photo-upload-page">
    <header class="page-header">
      <h1>製品写真アップロード</h1>
      <p>フィルタして品番を選び、写真を保存します。</p>
    </header>

    <section class="filter-panel">
      <input
        v-model.trim="filters.search"
        type="text"
        placeholder="品番・品名で検索"
        @keyup.enter="fetchProducts"
      />

      <select v-model="filters.hasImage">
        <option value="">写真: すべて</option>
        <option value="true">写真あり</option>
        <option value="false">写真なし</option>
      </select>

      <select v-model="filters.customerCode">
        <option value="">購入先: すべて</option>
        <option v-for="supplier in suppliers" :key="supplier.id" :value="supplier.supplier_code">
          {{ supplier.supplier_code }} - {{ supplier.supplier_name }}
        </option>
      </select>

      <select v-model="filters.line">
        <option value="">ライン: すべて</option>
        <option v-for="line in lines" :key="line.id" :value="String(line.id)">
          {{ line.line_code }} - {{ line.line_name }}
        </option>
      </select>

      <select v-model="filters.process">
        <option value="">工程: すべて</option>
        <option v-for="process in processes" :key="process.id" :value="String(process.id)">
          {{ process.process_code }} - {{ process.process_name }}
        </option>
      </select>

      <div class="filter-actions">
        <button class="btn-primary" :disabled="loading" @click="fetchProducts">
          {{ loading ? "絞り込み中..." : "絞り込み実行" }}
        </button>
        <button class="btn-secondary" :disabled="loading" @click="resetFilters">リセット</button>
      </div>
    </section>

    <section class="result-panel">
      <template v-if="!hasSearched">
        <div class="empty-message">条件を選んで「絞り込み実行」を押してください</div>
      </template>
      <template v-else-if="loading">
        <div class="empty-message">製品を取得中です...</div>
      </template>
      <template v-else-if="products.length === 0">
        <div class="empty-message">条件に合う製品がありません</div>
      </template>
      <template v-else>
        <div class="result-count">{{ products.length }} 件</div>
        <div class="product-list">
          <button
            v-for="product in products"
            :key="product.id"
            class="product-card"
            :class="{ selected: selectedProduct?.id === product.id }"
            type="button"
            @click="selectProduct(product)"
          >
            <div class="product-main">
              <div class="product-code">{{ product.product_code }}</div>
            </div>
            <div class="product-meta">
              <span>{{ getProcessCode(product.process) || "工程未設定" }}</span>
            </div>
          </button>
        </div>
      </template>
    </section>

    <section class="preview-panel">
      <template v-if="selectedProduct">
        <h2>{{ selectedProduct.product_code }}</h2>
        <p class="product-name">{{ selectedProduct.product_name }}</p>

        <div class="image-wrap">
          <img v-if="previewUrl" :src="previewUrl" alt="製品写真" />
          <div v-else class="no-image">No Image</div>
        </div>

        <button class="btn-primary photo-btn" :disabled="uploading" @click="openFileDialog">
          {{ uploading ? "保存中..." : "撮影/選択して保存" }}
        </button>
        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          capture="environment"
          class="hidden-input"
          @change="onFileSelected"
        />
      </template>
      <template v-else>
        <div class="empty-message">製品を選択すると写真が表示されます</div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "@/api/client";

const products = ref([]);
const loading = ref(false);
const hasSearched = ref(false);
const selectedProduct = ref(null);
const previewUrl = ref("");
const uploading = ref(false);
const fileInputRef = ref(null);
const suppliers = ref([]);
const lines = ref([]);
const processes = ref([]);
const filters = ref({
  search: "",
  hasImage: "",
  customerCode: "",
  line: "",
  process: "",
});

const resolveImageUrl = (product) => String(product?.image_url || "").trim();

const selectProduct = (product) => {
  selectedProduct.value = product;
  previewUrl.value = resolveImageUrl(product);
};

const getProcessCode = (processId) => {
  if (!processId) return "";
  const process = processes.value.find((item) => item.id === processId);
  return process ? process.process_code : "";
};

const buildQueryParams = () => {
  const params = {
    page_size: 200,
    is_active: true,
  };
  if (filters.value.search) params.search = filters.value.search;
  if (filters.value.hasImage !== "") params.has_image = filters.value.hasImage === "true";
  if (filters.value.customerCode) params.supplier_code = filters.value.customerCode;
  if (filters.value.line) params.line = Number(filters.value.line);
  if (filters.value.process) params.process = Number(filters.value.process);
  return params;
};

const fetchProducts = async () => {
  hasSearched.value = true;
  loading.value = true;
  try {
    const response = await api.products.getProducts(buildQueryParams());
    const data = response.data;
    products.value = data?.results || data || [];

    if (!selectedProduct.value) return;
    const latest = products.value.find((item) => item.id === selectedProduct.value.id);
    if (latest) {
      selectProduct(latest);
    } else {
      selectedProduct.value = null;
      previewUrl.value = "";
    }
  } catch (error) {
    console.error("製品一覧取得エラー:", error);
    alert("製品一覧の取得に失敗しました");
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  filters.value = {
    search: "",
    hasImage: "",
    customerCode: "",
    line: "",
    process: "",
  };
  hasSearched.value = false;
  products.value = [];
  selectedProduct.value = null;
  previewUrl.value = "";
};

const fetchFilterMasters = async () => {
  try {
    const [suppliersRes, linesRes, processesRes] = await Promise.all([
      api.suppliers.getSuppliers(),
      api.lines.getLines({ is_active: true, line_type: "PROD" }),
      api.processes.getProcesses({ is_active: true }),
    ]);
    suppliers.value = suppliersRes.data?.results || suppliersRes.data || [];
    lines.value = linesRes.data?.results || linesRes.data || [];
    processes.value = processesRes.data?.results || processesRes.data || [];
  } catch (error) {
    console.error("フィルタ候補取得エラー:", error);
  }
};

const openFileDialog = () => {
  if (!selectedProduct.value || uploading.value) return;
  fileInputRef.value?.click();
};

const onFileSelected = async (event) => {
  const file = event.target.files?.[0];
  if (!file || !selectedProduct.value) return;

  const originalPreview = previewUrl.value;
  const objectUrl = URL.createObjectURL(file);
  previewUrl.value = objectUrl;
  uploading.value = true;

  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.products.uploadProductImage(selectedProduct.value.id, formData);
    const imageUrl = String(response?.data?.image_url || "").trim();
    previewUrl.value = imageUrl || originalPreview;

    selectedProduct.value = {
      ...selectedProduct.value,
      image_url: imageUrl,
    };
    products.value = products.value.map((item) =>
      item.id === selectedProduct.value.id
        ? { ...item, image_url: imageUrl }
        : item,
    );
    alert("製品写真を保存しました");
  } catch (error) {
    console.error("製品写真アップロードエラー:", error);
    previewUrl.value = originalPreview;
    alert("製品写真の保存に失敗しました");
  } finally {
    URL.revokeObjectURL(objectUrl);
    if (fileInputRef.value) fileInputRef.value.value = "";
    uploading.value = false;
  }
};

onMounted(fetchFilterMasters);
</script>

<style scoped>
.photo-upload-page {
  padding: 12px;
  display: grid;
  gap: 10px;
}

.page-header h1 {
  margin: 0;
  font-size: 20px;
}

.page-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.filter-panel,
.result-panel,
.preview-panel {
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #fff;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.filter-panel input,
.filter-panel select {
  width: 100%;
  min-height: 44px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 15px;
}

.filter-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.btn-primary,
.btn-secondary {
  min-height: 44px;
  border: none;
  border-radius: 8px;
  font-weight: 700;
}

.btn-primary {
  background: #1d4ed8;
  color: #fff;
}

.btn-secondary {
  background: #e2e8f0;
  color: #1e293b;
}

.result-count {
  font-size: 13px;
  color: #475569;
}

.product-list {
  display: grid;
  gap: 8px;
  max-height: 40vh;
  overflow: auto;
}

.product-card {
  text-align: left;
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  display: grid;
  gap: 6px;
}

.product-card.selected {
  border-color: #1d4ed8;
  background: #eff6ff;
}

.product-code {
  font-weight: 700;
}

.product-name {
  margin: 0;
  color: #334155;
}

.product-meta {
  display: grid;
  gap: 2px;
  font-size: 12px;
  color: #64748b;
}

.preview-panel h2 {
  margin: 0;
  font-size: 18px;
}

.image-wrap {
  width: 100%;
  min-height: 220px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  display: grid;
  place-items: center;
  overflow: hidden;
  background: #f8fafc;
}

.image-wrap img {
  width: 100%;
  max-height: 360px;
  object-fit: contain;
}

.photo-btn {
  width: 100%;
}

.hidden-input {
  display: none;
}

.no-image,
.empty-message {
  color: #64748b;
  text-align: center;
}

@media (min-width: 1024px) {
  .photo-upload-page {
    grid-template-columns: 360px minmax(420px, 1fr) 420px;
    align-items: start;
  }
}
</style>
