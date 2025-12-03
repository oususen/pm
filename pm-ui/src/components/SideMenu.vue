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
      { label: "受注入力" },
      { label: "受注一覧" },
    ],
  },
  {
    id: "shipping",
    title: "出荷管理",
    items: [
      { label: "出荷指示" },
      { label: "出荷実績" },
    ],
  },
  {
    id: "production",
    title: "生産管理",
    items: [
      { label: "生産計画" },
      { label: "進捗管理" },
    ],
  },
  {
    id: "quality",
    title: "品質管理",
    items: [{ label: "検査実績" }],
  },
  {
    id: "masters",
    title: "マスタメンテ",
    items: [
      { label: "マスタメニュー", link: "/masters" },
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
