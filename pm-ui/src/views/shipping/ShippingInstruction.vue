<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">出荷指示 <DataSourceDialog title="出荷指示" :sources="dsSources" /></h2>
    </div>
    <div class="page-content">
      <p>出荷指示画面は準備中です。</p>
    </div>
  </div>
</template>

<script setup>
import { authState } from '@/auth'
import DataSourceDialog from '@/components/DataSourceDialog.vue'

const dsSources = [
  { op: '読み取り', table: 't_shipping_instruction', desc: '出荷指示データ' },
]
</script>

