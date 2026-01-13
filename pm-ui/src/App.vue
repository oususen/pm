<template>
  <div class="app-root">
    <!-- グローバルナビゲーション -->
    <GlobalNavigation v-if="showLayout" :is-mobile="isMobile" :today-text="todayText" />

    <div class="app-body">
      <main class="app-main">
        <RouterView />
      </main>
    </div>

    <footer v-if="showLayout" class="app-footer">
      <span>ダイウン工業株式会社 / 王 崇栓</span>
      <span>データベース: DMSP</span>
      <button class="logout-btn" @click="handleLogout">F12: ログアウト</button>
    </footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import GlobalNavigation from "./components/GlobalNavigation.vue";
import { logout } from "./auth";

const todayText = computed(() => {
  const d = new Date();
  const youbi = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日（${youbi}曜日）`;
});

const isMobile = ref(false);
let mediaQuery = null;

const route = useRoute();
const router = useRouter();

const showLayout = computed(() => !route.meta?.hideLayout);

const syncMobileState = () => {
  if (!mediaQuery) return;
  isMobile.value = mediaQuery.matches;
};

const handleLogout = async () => {
  await logout();
  router.replace("/login");
};

onMounted(() => {
  mediaQuery = window.matchMedia("(max-width: 768px)");
  syncMobileState();
  mediaQuery.addEventListener("change", syncMobileState);
});

onBeforeUnmount(() => {
  if (mediaQuery) {
    mediaQuery.removeEventListener("change", syncMobileState);
  }
});
</script>
