<template>
  <main class="analysis-workspace">
    <header><h1>AI分析</h1><span>準備中</span></header>
    <p class="notice" role="status">分析の実行基盤は未実装です。現在は分析目的の入力のみ可能で、データ取得・AI送信・SQL／Python実行・テンプレート保存は行いません。</p>
    <p v-if="!canEdit">閲覧のみの権限です。分析目的の編集には「AI分析」の編集権限が必要です。</p>
    <label for="analysis-purpose">分析目的</label>
    <textarea id="analysis-purpose" v-model="purpose" rows="5" :readonly="!canEdit" placeholder="何を調べ、どの判断に使いたいかを入力してください。"></textarea>
    <p v-if="source" class="source">起点画面: {{ source }}</p>
    <p>初期の分析対象（予定）: 入荷実績・出荷実績。生産・仕損・中断・残業は対応ビューの整備後に追加します。</p>
    <button type="button" disabled>分析案を作成（準備中）</button>
    <small>入力はタブ切替時に保持します。画面を離れる・再読込する・利用者を切り替えると消えます。</small>
  </main>
</template>

<script setup>
import { ref, watch } from 'vue'
const props = defineProps({ request: { type: Object, default: null }, canEdit: { type: Boolean, default: false } })
const purpose = ref('')
const source = ref('')
watch(() => props.request, (request) => {
  if (!request) return
  // 検索結果や会話履歴は受け取らず、質問文と起点だけを画面内で引き継ぐ。
  purpose.value = request.question || ''
  source.value = request.screenContext || ''
}, { immediate: true })
</script>

<style scoped>
.analysis-workspace { padding: 20px; max-width: 980px; margin: auto; color: #334b50; }
header { display: flex; align-items: center; gap: 12px; }
h1 { font-size: 22px; margin: 0; }
header span { background: #fff0d0; color: #805b19; border-radius: 5px; padding: 4px 8px; }
.notice { background: #edf6f5; border-left: 3px solid #168779; padding: 12px; line-height: 1.7; }
label { display: block; font-weight: 700; margin-bottom: 8px; }
textarea { box-sizing: border-box; width: 100%; border: 1px solid #b9cccc; border-radius: 8px; padding: 12px; font: inherit; resize: vertical; }
p { line-height: 1.7; }
button { padding: 10px 16px; border: 1px solid #d4dddd; border-radius: 6px; color: #647777; background: #eef2f2; }
small { display: block; margin-top: 12px; color: #657b80; }
</style>
