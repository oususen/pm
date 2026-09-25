<template>
  <nav class="side-menu">
    <div
      v-for="section in sections"
      :key="section.id"
      class="side-section"
    >
      <button
        type="button"
        class="side-section-title toggle"
        @click="toggleSection(section.id)"
      >
        <span>{{ section.title }}</span>
        <span class="chevron">{{ isOpen(section.id) ? '▲' : '▼' }}</span>
      </button>
      <ul v-if="isOpen(section.id)">
        <li v-for="item in section.items" :key="item.label">
          <RouterLink
            v-if="item.link"
            :to="item.link"
            class="link"
          >
            {{ item.label }}
          </RouterLink>
          <span v-else>{{ item.label }}</span>
        </li>
      </ul>
    </div>
  </nav>
</template>

<script setup>
import { RouterLink } from "vue-router";
import { reactive } from "vue";

const sections = [
  {
    id: "orders",
    title: "受注管理",
    items: [
      { label: "受注メニュー", link: "/orders/menu" },
      { label: "受注入力", link: "/csv-upload" },
      { label: "受注一覧", link: "/orders" },
    ],
  },
  {
    id: "shipping",
    title: "出荷管理",
    items: [
      { label: "出荷メニュー", link: "/shipping/menu" },
      { label: "出荷指示", link: "/shipping/instruction" },
      { label: "出荷実績", link: "/shipping/actual" },
      { label: "出荷進度照会", link: "/shipping/progress" },
    ],
  },
  {
    id: "production",
    title: "生産管理",
    items: [
      { label: "生産メニュー", link: "/production/menu" },
      { label: "進捗管理", link: "/production/progress" },
      { label: "進度のみ", link: "/production/progress-only" },
      { label: "在庫/残量", link: "/production/inventory" },
      { label: "ライン需要", link: "/production/line-demands" },
      { label: "在庫引当", link: "/production/stock-allocations" },
      { label: "製造指示", link: "/production/orders" },
      { label: "仕損品記録", link: "/production/scrap-record" },
      { label: "仕損履歴", link: "/production/scrap-history" },
    ],
  },
  {
    id: "purchase",
    title: "仕入れ管理",
    items: [
      { label: "仕入れメニュー", link: "/purchase/menu" },
      { label: "仕入れ計画", link: "/purchase/plan-input" },
      { label: "在庫/残量", link: "/purchase/inventory" },
    ],
  },
  {
    id: "inventory",
    title: "在庫管理",
    items: [
      { label: "在庫メニュー", link: "/inventory" },
      { label: "調整メニュー", link: "/inventory/adjustments" },
      { label: "進度調整", link: "/inventory/adjustments/progress" },
      { label: "在庫調整", link: "/inventory/adjustments/stock" },
    ],
  },
  {
    id: "consumables",
    title: "消耗品",
    items: [
      { label: "消耗品メニュー", link: "/consumables" },
      { label: "在庫一覧", link: "/consumables/inventory" },
      { label: "入出庫", link: "/consumables/operations" },
      { label: "注文依頼", link: "/consumables/requests" },
      { label: "注文書", link: "/consumables/dispatch-orders" },
      { label: "入出庫履歴", link: "/consumables/history" },
      { label: "消耗品マスタ", link: "/consumables/masters" },
    ],
  },
  {
    id: "quality",
    title: "品質管理",
    items: [
      { label: "品質メニュー", link: "/quality" },
      { label: "設備点検表", link: "/quality/equipment-inspection" },
    ],
  },
  {
    id: "overtime",
    title: "勤務管理",
    items: [
      { label: "勤務メニュー", link: "/overtime/menu" },
      { label: "シフトチャート", link: "/shifts/chart" },
    ],
  },
  {
    id: "masters",
    title: "マスタメンテ",
    items: [
      { label: "マスタメニュー", link: "/masters" },
      { label: "連絡先マスタ", link: "/masters/contact" },
    ],
  },
];

const openState = reactive(
  sections.reduce((acc, section) => {
    acc[section.id] = false;
    return acc;
  }, {})
);

const toggleSection = (id) => {
  openState[id] = !openState[id];
};

const isOpen = (id) => openState[id];
</script>
