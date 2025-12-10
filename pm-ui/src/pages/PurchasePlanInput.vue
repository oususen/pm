<template>
  <div class="purchase-plan-wrapper">
    <h2 class="page-title">仕入れ計画</h2>
    <ProductionPlanInput />
  </div>
</template>

<script setup>
import ProductionPlanInput from "./ProductionPlanInput.vue";
</script>

<style scoped>
.purchase-plan-wrapper {
  padding: 4px 0;
}
.page-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  color: #1f2a44;
}
</style>
