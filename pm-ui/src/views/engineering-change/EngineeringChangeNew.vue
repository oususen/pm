<template>
  <div class="page">
    <h2 class="page-title">新規タイル <DataSourceDialog title="新規タイル" :sources="dsSources" /></h2>
    <div class="card">
      <p>この画面は現在未実装です。</p>
      <p class="sub">要件確定後に実装します。</p>
    </div>
  </div>
</template>

<script setup>
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み書き', table: 't_engineering_change', desc: '設計変更の登録（将来実装）' },
]
</script>

<style scoped>
.page {
  padding: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
}
.sub {
  color: #64748b;
}
</style>

