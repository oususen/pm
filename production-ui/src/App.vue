<template>
  <div class="app-root">
    <header class="app-header">
      <div class="app-header-left">
        <span class="app-title">ダイウン工業 [マスタメンテ]</span>
      </div>
      <div class="app-header-right">
        <span>{{ todayText }}</span>
      </div>
    </header>

    <div class="app-body">
      <aside class="app-sidebar">
        <SideMenu />
      </aside>

      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <footer class="app-footer">
      <span>ダイウン工業株式会社 / 王 素柱</span>
      <span>データベース: DMSP</span>
      <button class="logout-btn">F12: ログアウト</button>
    </footer>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterView } from "vue-router";
import SideMenu from "./components/SideMenu.vue";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});
</script>
