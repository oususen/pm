<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">製品マスタ</h1>
      <div class="page-actions">
        <button @click="fetchProducts" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>品番コード</th>
            <th>品名</th>
            <th>カテゴリ</th>
            <th>単位</th>
            <th>標準LT(日)</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in products" :key="product.id">
            <td>{{ product.product_code }}</td>
            <td>{{ product.product_name }}</td>
            <td>{{ product.category }}</td>
            <td>{{ product.unit }}</td>
            <td>{{ product.standard_lt_days }}</td>
            <td>{{ product.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editProduct(product)" class="btn-sm">編集</button>
              <button @click="deleteProduct(product.id)" class="btn-sm btn-danger">削除</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="products.length === 0" class="no-data">
        データがありません
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const products = ref([])

const fetchProducts = async () => {
  try {
    const response = await api.getProducts()
    products.value = response.data
  } catch (error) {
    console.error('製品取得エラー:', error)
    alert('製品データの取得に失敗しました')
  }
}

const showNewDialog = () => {
  alert('新規作成機能は未実装です')
}

const editProduct = (product) => {
  alert(`編集機能は未実装です: ${product.product_name}`)
}

const deleteProduct = async (id) => {
  if (!confirm('本当に削除しますか？')) return

  try {
    await api.deleteProduct(id)
    await fetchProducts()
    alert('削除しました')
  } catch (error) {
    console.error('削除エラー:', error)
    alert('削除に失敗しました')
  }
}

onMounted(() => {
  fetchProducts()
})
</script>
