<template>
  <AIAnalysisUser
    :key="authState.user?.id"
    :can-edit="canEdit"
    :can-view-all="false"
    :user-name="userName"
  />
</template>

<script setup>
import { computed } from 'vue'
import { authState } from '@/auth'
import { hasPermission } from '@/router'
import AIAnalysisUser from './AIAnalysisUser.vue'

// 分析APIは既存の ai.analysis 編集権限を要求する。画面入口は仕様どおり ai.chat を使う。
const canEdit = computed(() => hasPermission(authState.user, 'ai.analysis', 'edit'))
const userName = computed(() => {
  const user = authState.user
  return user ? (`${user.last_name || ''} ${user.first_name || ''}`.trim() || user.username || '') : ''
})
</script>
