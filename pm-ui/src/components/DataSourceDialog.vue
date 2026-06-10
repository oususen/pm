<template>
  <button v-if="authState.user?.is_superuser" class="ds-trigger-btn" @click="show = true" title="データソース">
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/><path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/>
    </svg>
  </button>
  <Teleport to="body">
    <div v-if="show" class="ds-overlay" @click.self="show = false">
      <div class="ds-modal">
        <div class="ds-header">
          <h3>データソース{{ title ? ' — ' + title : '' }}</h3>
          <button class="ds-close" @click="show = false">&times;</button>
        </div>
        <table class="ds-table">
          <thead><tr><th>操作</th><th>テーブル</th><th>説明</th></tr></thead>
          <tbody>
            <template v-for="(row, i) in sources" :key="i">
              <tr v-if="row.section" class="ds-section"><td colspan="3"><strong>{{ row.section }}</strong></td></tr>
              <tr v-else><td>{{ row.op }}</td><td>{{ row.table }}</td><td>{{ row.desc }}</td></tr>
            </template>
          </tbody>
        </table>
        <p v-if="note" class="ds-note">{{ note }}</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { authState } from '@/auth'

defineProps({
  title: { type: String, default: '' },
  sources: { type: Array, required: true },
  note: { type: String, default: '' },
})

const show = ref(false)
</script>

<style scoped>
.ds-trigger-btn { margin-left: 8px; padding: 4px 6px; border: 1px solid #94a3b8; border-radius: 4px; background: #f8fafc; color: #475569; cursor: pointer; vertical-align: middle; display: inline-flex; align-items: center; }
.ds-trigger-btn:hover { background: #e2e8f0; }
.ds-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 9999; display: flex; align-items: center; justify-content: center; }
.ds-modal { background: #fff; border-radius: 8px; box-shadow: 0 4px 24px rgba(0,0,0,.2); max-width: 700px; width: 90%; max-height: 80vh; overflow: auto; }
.ds-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; border-bottom: 1px solid #e5e7eb; }
.ds-header h3 { margin: 0; font-size: 15px; }
.ds-close { border: none; background: none; font-size: 22px; cursor: pointer; color: #64748b; }
.ds-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ds-table th, .ds-table td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }
.ds-table th { background: #f8fafc; font-weight: 600; color: #374151; }
.ds-table td:first-child { white-space: nowrap; font-weight: 500; color: #2563eb; }
.ds-table td:nth-child(2) { font-family: monospace; font-size: 12px; color: #0f172a; }
.ds-section td { background: #f0f4ff; padding: 6px 12px; }
.ds-note { padding: 8px 18px 14px; margin: 0; font-size: 12px; color: #64748b; }
</style>
