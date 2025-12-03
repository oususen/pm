<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">得意先マスタ</h1>
      <div class="page-actions">
        <button @click="fetchCustomers" class="btn-primary">更新</button>
        <button @click="showNewDialog" class="btn-success">新規</button>
      </div>
    </div>

    <div class="page-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>得意先コード</th>
            <th>得意先名</th>
            <th>略称</th>
            <th>有効</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="customer in customers" :key="customer.id">
            <td>{{ customer.customer_code }}</td>
            <td>{{ customer.customer_name }}</td>
            <td>{{ customer.short_name }}</td>
            <td>{{ customer.is_active ? '有効' : '無効' }}</td>
            <td>
              <button @click="editCustomer(customer)" class="btn-sm">編集</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="customers.length === 0" class="no-data">
        データがありません
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/client'

const customers = ref([])

const fetchCustomers = async () => {
  try {
    const response = await api.getCustomers()
    customers.value = response.data
  } catch (error) {
    console.error('得意先取得エラー:', error)
    alert('得意先データの取得に失敗しました')
  }
}

const showNewDialog = () => {
  alert('新規作成機能は未実装です')
}

const editCustomer = (customer) => {
  alert(`編集機能は未実装です: ${customer.customer_name}`)
}

onMounted(() => {
  fetchCustomers()
})
</script>
