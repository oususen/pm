<template>
  <div class="page-container ics-manager" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">工程一体チェックシート テンプレート管理</h2>
      <div class="page-actions">
        <button class="btn-secondary" @click="loadTemplateList" :disabled="loadingList">更新</button>
        <button class="btn-primary" @click="startNewTemplate" :disabled="saving || actionLoading">新規作成</button>
      </div>
    </div>

    <div class="main-layout" :class="{ 'list-collapsed': listCollapsed }">
      <!-- 左: 一覧パネル -->
      <section v-show="!listCollapsed" class="panel list-panel">
        <h3 class="panel-title">テンプレート一覧</h3>
        <div class="list-filter-bar">
          <input v-model="listFilter.keyword" class="list-filter-input" placeholder="製品名・テンプレ名" />
          <select v-model="listFilter.status" class="list-filter-select">
            <option value="">状態: すべて</option>
            <option value="DRAFT">下書き</option>
            <option value="SUPERVISOR_PENDING">班長確認待ち</option>
            <option value="CHIEF_PENDING">係長確認待ち</option>
            <option value="MANAGER_PENDING">部長承認待ち</option>
            <option value="APPROVED">承認済み</option>
            <option value="REJECTED">差戻し</option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>製品</th>
                <th>テンプレート名</th>
                <th>版</th>
                <th>状態</th>
                <th>更新日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filteredTemplates"
                :key="row.id"
                :class="{ selected: selectedTemplateId === row.id }"
                @click="selectTemplate(row.id)"
              >
                <td>{{ row.id }}</td>
                <td>{{ row.product_code || row.product_name || '-' }}</td>
                <td>{{ row.name || '-' }}</td>
                <td>{{ row.version }}</td>
                <td>
                  <span class="status-chip" :class="statusClass(row.status)">{{ statusLabel(row.status) }}</span>
                </td>
                <td>{{ formatDateTime(row.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredTemplates.length && !loadingList" class="no-data">データがありません</div>
      </section>

      <!-- 右: 編集パネル -->
      <section class="panel edit-panel">
        <template v-if="editMode">
          <div class="panel-title-row">
            <button class="btn-icon" :title="listCollapsed ? '一覧表示' : '一覧隠す'" @click="listCollapsed = !listCollapsed">
              {{ listCollapsed ? '&#9654;' : '&#9664;' }}
            </button>
            <h3 class="panel-title">{{ form.id ? 'テンプレート編集' : '新規テンプレート作成' }}</h3>
          </div>

          <div class="status-row">
            <span class="status-chip" :class="statusClass(form.status)">{{ statusLabel(form.status) }}</span>
            <span class="status-meta">作成者: {{ form.created_by_name || '-' }}</span>
            <span class="status-meta">班長担当: {{ form.reviewer_user_name || '-' }}</span>
            <span class="status-meta">係長担当: {{ form.chief_user_name || '-' }}</span>
            <span class="status-meta">部長担当: {{ form.approver_user_name || '-' }}</span>
          </div>

          <!-- 基本情報 -->
          <div class="form-grid">
            <label>
              ライン <span class="required-mark">*</span>
              <select v-model="form.line" :disabled="!!form.id">
                <option value="">選択してください</option>
                <option v-for="line in lineOptions" :key="line.id" :value="line.id">
                  {{ line.line_code }} - {{ line.line_name }}
                </option>
              </select>
            </label>
            <label>
              製品 <span class="required-mark">*</span>
              <div class="autocomplete">
                <input
                  v-model="productSearch"
                  type="text"
                  placeholder="品番・品名で検索"
                  autocomplete="off"
                  :disabled="!!form.id"
                  @input="onProductSearchInput"
                  @focus="showProductSuggestions = true"
                  @blur="hideProductSuggestions"
                  @keydown.enter.prevent="selectFirstProduct"
                />
                <div v-if="showProductSuggestions && !form.id" class="suggestions">
                  <button
                    v-for="product in productSuggestions"
                    :key="product.id"
                    type="button"
                    class="suggestion"
                    @mousedown.prevent="selectProduct(product)"
                  >
                    <span>{{ product.product_code }}</span>
                    <small>{{ product.product_name }}</small>
                  </button>
                  <p v-if="productSearching" class="suggestion-note">検索中...</p>
                  <p v-else-if="productSearch.trim() && !productSuggestions.length" class="suggestion-note">該当なし</p>
                  <p v-else-if="!productSearch.trim()" class="suggestion-note">品番または品名を入力してください。</p>
                </div>
              </div>
            </label>
            <label>
              テンプレート名 <span class="required-mark">*</span>
              <input v-model.trim="form.name" />
            </label>
            <label>
              帳票タイトル
              <input v-model.trim="form.document_title" />
            </label>
            <label>
              班長担当
              <select v-model="form.reviewer_user">
                <option :value="null">未設定</option>
                <option v-for="u in userOptions" :key="`reviewer-${u.id}`" :value="u.id">
                  {{ u.display_name }}
                </option>
              </select>
            </label>
            <label>
              係長担当
              <select v-model="form.chief_user">
                <option :value="null">未設定</option>
                <option v-for="u in userOptions" :key="`chief-${u.id}`" :value="u.id">
                  {{ u.display_name }}
                </option>
              </select>
            </label>
            <label>
              部長担当
              <select v-model="form.approver_user">
                <option :value="null">未設定</option>
                <option v-for="u in userOptions" :key="`approver-${u.id}`" :value="u.id">
                  {{ u.display_name }}
                </option>
              </select>
            </label>
            <label>
              元シート名
              <input v-model.trim="form.sheet_name" />
            </label>
            <label class="wide">
              改訂内容
              <textarea v-model.trim="form.revision_notes" rows="2" />
            </label>
            <label>
              改訂日
              <input v-model="form.revision_date" type="date" />
            </label>
            <label>
              運用開始日
              <input v-model="form.effective_from" type="date" />
            </label>
            <label>
              版
              <input type="number" min="1" v-model.number="form.version" />
            </label>
            <label class="check-line">
              <input type="checkbox" v-model="form.is_active" />
              有効
            </label>
          </div>

          <!-- 工程ブロック -->
          <div class="section-header">
            <h4>工程ブロック</h4>
            <button class="btn-secondary btn-sm" @click="addProcessBlock">ブロック追加</button>
          </div>

          <div v-if="!form.process_blocks.length" class="no-data">工程ブロックはまだありません。「ブロック追加」で追加してください。</div>

          <div
            v-for="(block, bIdx) in form.process_blocks"
            :key="block._key"
            class="process-block"
            :style="blockColorStyle(bIdx)"
          >
            <div class="block-header" :style="blockHeaderStyle(bIdx)" @click="toggleBlock(bIdx)">
              <span class="block-toggle">{{ block._expanded ? '&#9660;' : '&#9654;' }}</span>
              <span class="block-title">
                {{ blockLabel(block) }}
              </span>
              <span class="block-sort">順序: {{ block.sort_order }}</span>
              <div class="block-actions">
                <button class="btn-icon" title="上へ" :disabled="bIdx === 0" @click.stop="moveBlock(bIdx, -1)">&#9650;</button>
                <button class="btn-icon" title="下へ" :disabled="bIdx === form.process_blocks.length - 1" @click.stop="moveBlock(bIdx, 1)">&#9660;</button>
                <button class="btn-icon btn-icon-danger" title="削除" @click.stop="removeBlock(bIdx)">&#10005;</button>
              </div>
            </div>

            <div v-if="block._expanded" class="block-body">
              <div class="form-grid">
                <label>
                  工程 <span class="required-mark">*</span>
                  <select v-model="block.process">
                    <option value="">選択してください</option>
                    <option v-for="proc in availableProcessOptions" :key="proc.id" :value="proc.id">
                      {{ proc.process_code }} - {{ proc.process_name }}
                    </option>
                  </select>
                </label>
                <label>
                  並び順
                  <input type="number" v-model.number="block.sort_order" min="0" />
                </label>
              </div>

              <!-- チェック項目テーブル -->
              <div class="section-header">
                <h5>チェック項目</h5>
                <button class="btn-secondary btn-sm" @click="addItem(block)">項目追加</button>
              </div>
              <div class="table-wrap" v-if="block.items.length">
                <table class="data-table compact item-table">
                  <thead>
                    <tr>
                      <th style="width: 30px">No</th>
                      <th>項目名</th>
                      <th>基準値</th>
                      <th>頻度</th>
                      <th>方法</th>
                      <th style="width: 100px">記録種別</th>
                      <th>単位</th>
                      <th>判定基準</th>
                      <th style="width: 40px">必須</th>
                      <th style="width: 30px"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, iIdx) in block.items" :key="item._key">
                      <td>{{ iIdx + 1 }}</td>
                      <td><input v-model.trim="item.item_name" class="cell-input" /></td>
                      <td><input v-model.trim="item.standard" class="cell-input" /></td>
                      <td><input v-model.trim="item.frequency" class="cell-input cell-sm" /></td>
                      <td><input v-model.trim="item.method" class="cell-input cell-sm" /></td>
                      <td>
                        <select v-model="item.record_type" class="cell-input">
                          <option value="CHECK">CHECK</option>
                          <option value="NUMERIC">NUMERIC</option>
                          <option value="TEXT">TEXT</option>
                        </select>
                      </td>
                      <td><input v-model.trim="item.unit" class="cell-input cell-xs" /></td>
                      <td><input v-model.trim="item.criteria" class="cell-input" /></td>
                      <td class="center">
                        <input type="checkbox" v-model="item.is_required" />
                      </td>
                      <td class="center">
                        <button class="btn-icon btn-icon-danger" title="削除" @click="removeItem(block, iIdx)">&#10005;</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="no-data">チェック項目はまだありません。</div>

              <!-- 台紙アップロード（PDF / 画像） -->
              <div class="sketch-upload">
                <label>
                  台紙PDF
                  <input type="file" accept="application/pdf" @change="onSketchFileChange($event, block, 'pdf')" />
                </label>
                <label>
                  台紙画像
                  <input type="file" accept="image/*" @change="onSketchFileChange($event, block, 'image')" />
                </label>
                <button
                  type="button"
                  class="btn-secondary btn-sm"
                  :disabled="!block.sketch_image_url"
                  @click="openSketchEditor(block)"
                >
                  配置エディタを開く
                </button>
                <span v-if="block._uploadPending" class="sketch-file-note">※ 未アップロード: {{ block._uploadPending.name }}</span>
                <div v-if="block.sketch_image_url" class="sketch-thumb">
                  <img :src="block.sketch_image_url" alt="台紙" />
                </div>
                <div v-if="block.source_pdf_url" class="sketch-file-note">
                  <a :href="block.source_pdf_url" target="_blank">元PDF</a>
                </div>
              </div>

              <div class="section-header">
                <h5>台紙フィールド</h5>
                <button class="btn-secondary btn-sm" @click="addSketchField(block)">フィールド追加</button>
              </div>
              <div class="table-wrap" v-if="block.sketch_fields && block.sketch_fields.length">
                <table class="data-table compact item-table">
                  <thead>
                    <tr>
                      <th style="width: 50px">順序</th>
                      <th>キー</th>
                      <th>表示名</th>
                      <th style="width: 110px">種別</th>
                      <th style="width: 65px">X</th>
                      <th style="width: 65px">Y</th>
                      <th style="width: 75px">幅</th>
                      <th style="width: 75px">高さ</th>
                      <th style="width: 45px">必須</th>
                      <th style="width: 35px"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(field, sIdx) in block.sketch_fields" :key="field._key || sIdx">
                      <td><input type="number" min="0" v-model.number="field.sort_order" class="cell-input cell-xs" /></td>
                      <td><input v-model.trim="field.key" class="cell-input" /></td>
                      <td><input v-model.trim="field.label" class="cell-input" /></td>
                      <td>
                        <select v-model="field.field_type" class="cell-input">
                          <option value="text">テキスト</option>
                          <option value="checkbox">チェック</option>
                          <option value="aggregate_okng">OK/NG</option>
                          <option value="date">日付</option>
                          <option value="photo">写真</option>
                          <option value="pen">手書き</option>
                          <option value="worker_name">作業者名</option>
                        </select>
                      </td>
                      <td><input type="number" min="0" v-model.number="field.x" class="cell-input cell-xs" /></td>
                      <td><input type="number" min="0" v-model.number="field.y" class="cell-input cell-xs" /></td>
                      <td><input type="number" min="0" v-model.number="field.width" class="cell-input cell-xs" /></td>
                      <td><input type="number" min="0" v-model.number="field.height" class="cell-input cell-xs" /></td>
                      <td class="center"><input type="checkbox" v-model="field.required" /></td>
                      <td class="center">
                        <button class="btn-icon btn-icon-danger" title="削除" @click="removeSketchField(block, sIdx)">&#10005;</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="no-data">台紙フィールドはまだありません。</div>
            </div>
          </div>

          <!-- アクションボタン -->
          <div class="edit-actions">
            <button v-if="canDraftSave" class="btn-primary" @click="saveStructure" :disabled="saving">
              {{ saving ? '保存中...' : (form.id ? '下書き更新' : '下書き保存') }}
            </button>
            <button class="btn-secondary" @click="downloadPreviewPdf" :disabled="!form.id || saving || pdfLoading">{{ pdfLoading ? 'PDF生成中...' : 'PDF出力' }}</button>
            <button v-if="canSubmitForReview" class="btn-request" @click="submitForReview" :disabled="saving || actionLoading">確認依頼</button>
            <button v-if="canReview" class="btn-chief" @click="reviewTemplate" :disabled="saving || actionLoading">
              {{ reviewActionLabel }}
            </button>
            <button v-if="canApprove" class="btn-approve" @click="approveTemplate" :disabled="saving || actionLoading">部長承認</button>
            <button v-if="canReject" class="btn-reject" @click="rejectTemplate" :disabled="saving || actionLoading">差し戻し</button>
            <button v-if="canRevise" class="btn-revise" @click="reviseTemplate" :disabled="saving || actionLoading">改訂</button>
            <button class="btn-secondary" @click="cancelEdit">キャンセル</button>
          </div>
          <div v-if="form.status === 'REJECTED' && form.rejection_comment" class="rejection-banner">
            差戻しコメント: {{ form.rejection_comment }}
          </div>
        </template>

        <template v-else>
          <div class="panel-title-row" v-if="listCollapsed">
            <button class="btn-icon" title="一覧表示" @click="listCollapsed = false">&#9654;</button>
          </div>
          <div class="no-data">左の一覧からテンプレートを選択するか、「新規作成」で開始してください。</div>
        </template>
      </section>
    </div>

    <!-- 配置エディタモーダル（A案準拠） -->
    <div v-if="sketchEditorBlock" class="modal-overlay">
      <div class="sketch-editor-modal">
        <div class="sketch-editor-header">
          <h3>台紙フィールド配置 — {{ blockLabel(sketchEditorBlock) }}</h3>
          <div class="sketch-editor-actions">
            <button class="btn-primary btn-sm" @click="applySketchEditor">適用して閉じる</button>
            <button class="btn-secondary btn-sm" @click="closeSketchEditor">キャンセル</button>
          </div>
        </div>

        <div class="sketch-editor-grid">
          <!-- 左: コントロールパネル -->
          <div class="se-controls">
            <h4>項目追加</h4>
            <div class="se-form">
              <label>種類
                <select v-model="seNewField.field_type">
                  <option value="checkbox">チェック</option>
                  <option value="text">テキスト</option>
                  <option value="aggregate_okng">OK/NG</option>
                  <option value="date">日付</option>
                  <option value="photo">写真</option>
                  <option value="pen">手書き</option>
                  <option value="worker_name">作業者名</option>
                </select>
              </label>
              <label>表示名 <input v-model="seNewField.label" type="text" /></label>
              <label>内部キー <input v-model="seNewField.key" type="text" /></label>
              <label>必須
                <select v-model="seNewField.required">
                  <option :value="false">任意</option>
                  <option :value="true">必須</option>
                </select>
              </label>
              <p class="se-hint">台紙上の追加したい位置をクリックしてください。</p>
            </div>

            <h4>配置項目 ({{ sketchEditorFields.length }})</h4>
            <div class="se-field-list">
              <button
                v-for="(field, idx) in sketchEditorFields"
                :key="idx"
                class="se-field-row"
                :class="{ active: selectedFieldIdx === idx }"
                type="button"
                @click="selectedFieldIdx = idx"
              >
                <span>{{ field.label || field.key }}</span>
                <small>{{ field.field_type }} / {{ Math.round(field.x) }},{{ Math.round(field.y) }}</small>
              </button>
            </div>

            <div v-if="selectedFieldIdx !== null && sketchEditorFields[selectedFieldIdx]" class="se-detail">
              <h4>選択中</h4>
              <div class="se-form">
                <label>表示名 <input v-model="sketchEditorFields[selectedFieldIdx].label" type="text" /></label>
                <label>内部キー <input v-model="sketchEditorFields[selectedFieldIdx].key" type="text" /></label>
                <label>種類
                  <select v-model="sketchEditorFields[selectedFieldIdx].field_type">
                    <option value="checkbox">チェック</option>
                    <option value="text">テキスト</option>
                    <option value="aggregate_okng">OK/NG</option>
                    <option value="date">日付</option>
                    <option value="photo">写真</option>
                    <option value="pen">手書き</option>
                    <option value="worker_name">作業者名</option>
                  </select>
                </label>
                <label>必須
                  <select v-model="sketchEditorFields[selectedFieldIdx].required">
                    <option :value="false">任意</option>
                    <option :value="true">必須</option>
                  </select>
                </label>
                <label>X <input type="number" v-model.number="sketchEditorFields[selectedFieldIdx].x" /></label>
                <label>Y <input type="number" v-model.number="sketchEditorFields[selectedFieldIdx].y" /></label>
                <label>幅 <input type="number" v-model.number="sketchEditorFields[selectedFieldIdx].width" min="6" /></label>
                <label>高さ <input type="number" v-model.number="sketchEditorFields[selectedFieldIdx].height" min="6" /></label>
                <button class="btn-danger full-row" type="button" @click="deleteFieldInEditor(selectedFieldIdx)">削除</button>
              </div>
            </div>
          </div>

          <!-- 右: 台紙キャンバス -->
          <div class="se-sheet-panel">
            <div class="se-toolbar">
              <span>{{ blockLabel(sketchEditorBlock) }}</span>
              <button class="btn-secondary btn-sm" type="button" @click="seZoom = Math.max(0.3, seZoom - 0.1)">縮小</button>
              <span class="se-zoom-label">{{ Math.round(seZoom * 100) }}%</span>
              <button class="btn-secondary btn-sm" type="button" @click="seZoom = Math.min(3, seZoom + 0.1)">拡大</button>
            </div>
            <div class="se-sheet-scroll">
              <div
                class="se-stage"
                :style="seStageStyle"
                @click="handleStageClick"
              >
                <img
                  v-if="sketchEditorImageUrl"
                  :src="sketchEditorImageUrl"
                  class="se-sheet-image"
                  draggable="false"
                  @load="onSketchImageLoad"
                />
                <div
                  v-for="(field, idx) in sketchEditorFields"
                  :key="idx"
                  class="se-field-box"
                  :class="{ selected: selectedFieldIdx === idx }"
                  :style="seBoxStyle(field)"
                  @click.stop="selectedFieldIdx = idx"
                  @pointerdown.stop="startDragField($event, field, idx)"
                >
                  <span class="se-field-label-tag">{{ field.label || field.key }}</span>
                  <strong>{{ sePreviewText(field) }}</strong>
                  <span
                    v-if="selectedFieldIdx === idx"
                    class="se-resize-handle"
                    @pointerdown.stop.prevent="startResizeField($event, field)"
                  ></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="submitDialogVisible" class="modal-backdrop" @click.self="cancelSubmit">
      <div class="modal-panel reject-modal">
        <div class="reject-modal-body">
          <label class="reject-label">コメント（任意）</label>
          <textarea
            v-model="submitComment"
            class="reject-textarea"
            rows="5"
            placeholder="確認依頼時のコメントがあれば入力してください。"
            autofocus
          />
        </div>
        <div class="reject-modal-footer">
          <button class="btn-secondary" @click="cancelSubmit">キャンセル</button>
          <button class="btn-approve" @click="confirmSubmitForReview">確認依頼</button>
        </div>
      </div>
    </div>

    <div v-if="rejectDialogVisible" class="modal-backdrop" @click.self="cancelReject">
      <div class="modal-panel reject-modal">
        <div class="reject-modal-body">
          <label class="reject-label">差戻しコメント</label>
          <textarea
            v-model="rejectComment"
            class="reject-textarea"
            rows="8"
            placeholder="差戻しの理由や修正指示を入力してください。"
            autofocus
          />
        </div>
        <div class="reject-modal-footer">
          <button class="btn-secondary" @click="cancelReject">キャンセル</button>
          <button class="btn-reject" @click="confirmReject">差し戻し実行</button>
        </div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">工程一体チェックシート テンプレート管理</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '@/api/client'
import { authState } from '@/auth'
import { hasPermission } from '@/router'

// --- 権限 ---
const canAccessQuality = (resource, level = 'view') => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) return hasPermission(user, resource, level)
  return hasPermission(user, 'quality', level)
}
const canView = computed(() => canAccessQuality('quality', 'view'))

// --- 状態 ---
const STATUS_LABELS = {
  DRAFT: '下書き',
  SUPERVISOR_PENDING: '班長確認待ち',
  CHIEF_PENDING: '係長確認待ち',
  MANAGER_PENDING: '部長承認待ち',
  APPROVED: '承認済み',
  REJECTED: '差戻し',
}
const statusLabel = (s) => STATUS_LABELS[s] || s || '-'
const statusClass = (s) => {
  if (s === 'APPROVED') return 'ok'
  if (s === 'REJECTED') return 'rejected'
  if (s && s.includes('PENDING')) return 'pending'
  return 'draft'
}

// --- 一覧トグル ---
const listCollapsed = ref(false)

// --- 一覧 ---
const templates = ref([])
const loadingList = ref(false)
const selectedTemplateId = ref(null)
const listFilter = ref({ keyword: '', status: '' })

const filteredTemplates = computed(() => {
  const kw = listFilter.value.keyword.trim().toLowerCase()
  const st = listFilter.value.status
  return templates.value.filter((row) => {
    if (st && row.status !== st) return false
    if (kw) {
      const haystack = `${row.product_code || ''} ${row.product_name || ''} ${row.name || ''}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    return true
  })
})

const availableProcessOptions = computed(() => {
  if (!form.value.line) return []
  return processOptions.value.filter((proc) => String(proc.line || '') === String(form.value.line))
})

// --- マスタ ---
const lineOptions = ref([])
const processOptions = ref([])
const userOptions = ref([])
const productSearch = ref('')
const productSuggestions = ref([])
const productSearching = ref(false)
const showProductSuggestions = ref(false)
const selectedProductLabel = ref('')
let productSearchTimer = null
let productSearchSerial = 0

// --- 編集 ---
const editMode = ref(false)
const saving = ref(false)
const actionLoading = ref(false)
const pdfLoading = ref(false)
const rejectDialogVisible = ref(false)
const rejectComment = ref('')
const submitDialogVisible = ref(false)
const submitComment = ref('')
let itemKeySeq = 0
const nextKey = () => `_k${++itemKeySeq}`

const createEmptyForm = () => ({
  id: null,
  product: '',
  line: '',
  name: '',
  document_title: '',
  sheet_name: '',
  revision_date: '',
  revision_notes: '',
  effective_from: '',
  version: 1,
  status: 'DRAFT',
  is_active: true,
  created_by_name: '',
  reviewer_user: null,
  reviewer_user_name: '',
  chief_user: null,
  chief_user_name: '',
  approver_user: null,
  approver_user_name: '',
  rejection_comment: '',
  process_blocks: [],
})

const form = ref(createEmptyForm())
const canEdit = computed(() => canAccessQuality('quality', 'edit'))
const currentUserId = computed(() => Number(authState.user?.id || 0))
const normalizeStatus = (status) => String(status || '').trim().toUpperCase()
const normalizedFormStatus = computed(() => normalizeStatus(form.value.status) || 'DRAFT')

// --- ユーティリティ ---
const formatDateTime = (value) => {
  if (!value) return '-'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString('ja-JP')
}

const blockLabel = (block) => {
  if (!block.process) return '(未選択)'
  const proc = processOptions.value.find((p) => p.id === block.process)
  return proc ? `${proc.process_code} - ${proc.process_name}` : `工程ID: ${block.process}`
}

const searchProducts = async () => {
  const keyword = productSearch.value.trim()
  const serial = ++productSearchSerial
  if (!keyword) {
    productSuggestions.value = []
    return
  }
  productSearching.value = true
  try {
    const res = await api.products.getProducts({
      is_active: true,
      is_line_final_product: true,
      search: keyword,
      page_size: 20,
    })
    if (serial !== productSearchSerial) return
    productSuggestions.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('製品検索失敗:', e)
    if (serial === productSearchSerial) productSuggestions.value = []
  } finally {
    if (serial === productSearchSerial) productSearching.value = false
  }
}

const onProductSearchInput = () => {
  showProductSuggestions.value = true
  if (productSearch.value !== selectedProductLabel.value) {
    form.value.product = ''
    selectedProductLabel.value = ''
  }
  if (productSearchTimer) clearTimeout(productSearchTimer)
  productSearchTimer = setTimeout(searchProducts, 250)
}

const selectProduct = (product) => {
  form.value.product = product.id
  selectedProductLabel.value = `${product.product_code} - ${product.product_name}`
  productSearch.value = selectedProductLabel.value
  productSuggestions.value = [product]
  showProductSuggestions.value = false
  applyAutoTitles()
}

const selectFirstProduct = () => {
  if (productSuggestions.value.length) selectProduct(productSuggestions.value[0])
}

const hideProductSuggestions = () => {
  setTimeout(() => {
    showProductSuggestions.value = false
  }, 150)
}

const applyAutoTitles = () => {
  if (form.value.id) return
  if (!form.value.line || !form.value.product) return
  const line = lineOptions.value.find((item) => String(item.id) === String(form.value.line))
  const product = productSuggestions.value.find((item) => String(item.id) === String(form.value.product))
  const lineName = line?.line_name || ''
  const productCode = product?.product_code || ''
  if (!lineName || !productCode) return
  const autoTitle = `${lineName} ${productCode} チェックシート`
  form.value.name = autoTitle
  form.value.document_title = autoTitle
}

// --- マスタ読込 ---
const loadMasters = async () => {
  try {
    const [lineRes, procRes, productRes, userRes] = await Promise.all([
      api.lines.getLines({ line_type: 'PROD', page_size: 1000 }),
      api.processes.getProcesses({ is_active: true, page_size: 1000 }),
      api.products.getProducts({ page_size: 20 }),
      api.accounts.getUsers({ is_active: true, page_size: 1000 }),
    ])
    lineOptions.value = lineRes.data?.results || lineRes.data || []
    processOptions.value = procRes.data?.results || procRes.data || []
    productSuggestions.value = productRes.data?.results || productRes.data || []
    const users = userRes.data?.results || userRes.data || []
    userOptions.value = users.map((u) => {
      const code = u.employee_code || u.profile?.employee_code || ''
      const name = `${u.last_name || ''} ${u.first_name || ''}`.trim() || u.full_name || u.username || `user-${u.id}`
      return {
        id: u.id,
        display_name: code ? `${code} ${name}` : name,
      }
    })
  } catch (e) {
    console.error('マスタ取得失敗:', e)
  }
}

// --- 一覧読込 ---
const loadTemplateList = async () => {
  if (!canView.value) return
  loadingList.value = true
  try {
    const res = await api.integratedChecksheets.listTemplates({ page_size: 500 })
    templates.value = res.data?.results || res.data || []
  } catch (e) {
    console.error('テンプレート一覧取得失敗:', e)
    alert('テンプレート一覧の取得に失敗しました。')
  } finally {
    loadingList.value = false
  }
}

// --- テンプレート選択 ---
const selectTemplate = async (id) => {
  selectedTemplateId.value = id
  try {
    const res = await api.integratedChecksheets.getTemplate(id)
    const data = res.data
    form.value = {
      id: data.id,
      product: data.product || '',
      line: data.line || '',
      name: data.name || '',
      document_title: data.document_title || data.name || '',
      sheet_name: data.sheet_name || '',
      revision_date: data.revision_date || '',
      revision_notes: data.revision_notes || '',
      effective_from: data.effective_from || '',
      version: data.version || 1,
      status: data.status || 'DRAFT',
      is_active: data.is_active !== false,
      created_by_name: data.created_by_name || '',
      reviewer_user: data.reviewer_user || null,
      reviewer_user_name: data.reviewer_user_name || '',
      chief_user: data.chief_user || null,
      chief_user_name: data.chief_user_name || '',
      approver_user: data.approver_user || null,
      approver_user_name: data.approver_user_name || '',
      rejection_comment: data.rejection_comment || '',
      process_blocks: (data.process_blocks || []).map((b) => ({
        id: b.id,
        process: b.process || '',
        sort_order: b.sort_order ?? 0,
        sketch_image_url: b.sketch_image_url || '',
        source_pdf_url: b.source_pdf_url || '',
        _uploadPending: null,
        _uploadType: null,
        _expanded: true,
        _key: nextKey(),
        items: (b.items || []).map((item) => ({
          id: item.id,
          item_name: item.item_name || '',
          standard: item.standard || '',
          frequency: item.frequency || '',
          method: item.method || '',
          record_type: item.record_type || 'CHECK',
          unit: item.unit || '',
          criteria: item.criteria || '',
          is_required: Boolean(item.is_required),
          _key: nextKey(),
        })),
        sketch_fields: b.sketch_fields || [],
      })),
    }
    if (data.product_code) {
      selectedProductLabel.value = `${data.product_code} - ${data.product_name || ''}`
      productSearch.value = selectedProductLabel.value
    } else {
      selectedProductLabel.value = ''
      productSearch.value = ''
    }
    editMode.value = true
  } catch (e) {
    console.error('テンプレート詳細取得失敗:', e)
    alert('テンプレート詳細の取得に失敗しました。')
  }
}

// --- 新規作成 ---
const startNewTemplate = () => {
  selectedTemplateId.value = null
  form.value = createEmptyForm()
  productSearch.value = ''
  selectedProductLabel.value = ''
  productSuggestions.value = []
  editMode.value = true
}

const cancelEdit = () => {
  editMode.value = false
  selectedTemplateId.value = null
  form.value = createEmptyForm()
  productSearch.value = ''
  selectedProductLabel.value = ''
  productSuggestions.value = []
}

// --- 工程ブロック色 ---
const BLOCK_COLORS = [
  { bg: '#2962a8', light: '#dce5f2', border: '#2962a8' },
  { bg: '#a83832', light: '#f5d7d5', border: '#a83832' },
  { bg: '#2e8550', light: '#d4eedc', border: '#2e8550' },
  { bg: '#9c6e1e', light: '#f5ebc8', border: '#9c6e1e' },
  { bg: '#6a3a94', light: '#e6daf0', border: '#6a3a94' },
  { bg: '#1e8296', light: '#cdebf2', border: '#1e8296' },
  { bg: '#b45a28', light: '#f5e1d2', border: '#b45a28' },
  { bg: '#505050', light: '#e1e1e1', border: '#505050' },
]
const blockColorStyle = (idx) => ({
  borderLeft: `4px solid ${BLOCK_COLORS[idx % BLOCK_COLORS.length].border}`,
})
const blockHeaderStyle = (idx) => ({
  background: BLOCK_COLORS[idx % BLOCK_COLORS.length].light,
})

// --- 工程ブロック操作 ---
const addProcessBlock = () => {
  form.value.process_blocks.push({
    id: null,
    process: '',
    sort_order: form.value.process_blocks.length + 1,
    sketch_image_url: null,
    _uploadPending: null,
    _uploadType: null,
    _expanded: true,
    _key: nextKey(),
    items: [],
    sketch_fields: [],
  })
}

const removeBlock = (idx) => {
  if (!window.confirm('この工程ブロックを削除しますか?')) return
  form.value.process_blocks.splice(idx, 1)
  // 並び順を振り直す
  form.value.process_blocks.forEach((b, i) => { b.sort_order = i + 1 })
}

const moveBlock = (idx, direction) => {
  const target = idx + direction
  if (target < 0 || target >= form.value.process_blocks.length) return
  const blocks = form.value.process_blocks
  const temp = blocks[idx]
  blocks[idx] = blocks[target]
  blocks[target] = temp
  // 並び順を振り直す
  blocks.forEach((b, i) => { b.sort_order = i + 1 })
}

const toggleBlock = (idx) => {
  form.value.process_blocks[idx]._expanded = !form.value.process_blocks[idx]._expanded
}

// --- チェック項目操作 ---
const addItem = (block) => {
  block.items.push({
    id: null,
    item_name: '',
    standard: '',
    frequency: '',
    method: '',
    record_type: 'CHECK',
    unit: '',
    criteria: '',
    is_required: false,
    _key: nextKey(),
  })
}

const removeItem = (block, idx) => {
  block.items.splice(idx, 1)
}

const addSketchField = (block) => {
  if (!Array.isArray(block.sketch_fields)) block.sketch_fields = []
  const next = block.sketch_fields.length + 1
  block.sketch_fields.push({
    key: `field_${next}`,
    label: '',
    field_type: 'text',
    x: 0,
    y: 0,
    width: 160,
    height: 36,
    required: false,
    sort_order: next,
    _key: nextKey(),
  })
}

const removeSketchField = (block, idx) => {
  if (!Array.isArray(block.sketch_fields)) return
  block.sketch_fields.splice(idx, 1)
}

// --- 台紙ファイル選択 ---
const onSketchFileChange = async (event, block, type) => {
  const file = event.target.files?.[0]
  if (!file) return
  block._uploadPending = file
  block._uploadType = type

  if (!block.id || !form.value.id) {
    alert('台紙をアップロードするには、先に構造を保存してください。')
    return
  }
  await uploadBlockSketch(block)
}

const uploadBlockSketch = async (block) => {
  if (!block._uploadPending || !block.id || !form.value.id) return
  const fd = new FormData()
  if (block._uploadType === 'pdf') {
    fd.append('source_pdf', block._uploadPending)
  } else {
    fd.append('source_image', block._uploadPending)
  }
  try {
    const res = await api.integratedChecksheets.uploadSketch(form.value.id, block.id, fd)
    block.sketch_image_url = res.data.sketch_image_url || ''
    block.source_pdf_url = res.data.source_pdf_url || ''
    block._uploadPending = null
    block._uploadType = null
  } catch (e) {
    console.error('台紙アップロード失敗:', e)
    alert(`台紙アップロードに失敗しました: ${e.response?.data?.detail || e.message}`)
  }
}

// --- 配置エディタ（A案準拠: PointerEvents + zoom） ---
const sketchEditorBlock = ref(null)
const sketchEditorFields = ref([])
const sketchEditorImageUrl = ref('')
const selectedFieldIdx = ref(null)
const seZoom = ref(1)
const seImgW = ref(800)
const seImgH = ref(600)
const seDragState = ref(null)
const seResizeState = ref(null)
const seNewField = ref({ field_type: 'checkbox', label: 'チェック', key: '', required: false })

const openSketchEditor = (block) => {
  const url = block?.sketch_image_url
  if (!url) {
    alert('台紙画像がありません。先にPDFまたは画像をアップロードしてください。')
    return
  }
  sketchEditorBlock.value = block
  sketchEditorImageUrl.value = url
  sketchEditorFields.value = JSON.parse(JSON.stringify(block.sketch_fields || []))
  selectedFieldIdx.value = null
  seZoom.value = 1
  window.addEventListener('pointermove', seOnPointerMove)
  window.addEventListener('pointerup', seStopAction)
  window.addEventListener('pointercancel', seStopAction)
}

const closeSketchEditor = () => {
  window.removeEventListener('pointermove', seOnPointerMove)
  window.removeEventListener('pointerup', seStopAction)
  window.removeEventListener('pointercancel', seStopAction)
  sketchEditorBlock.value = null
  sketchEditorFields.value = []
  selectedFieldIdx.value = null
}

const applySketchEditor = () => {
  if (!sketchEditorBlock.value) return
  sketchEditorBlock.value.sketch_fields = sketchEditorFields.value.map((f, i) => ({
    ...f,
    sort_order: i,
    _key: f._key || nextKey(),
  }))
  closeSketchEditor()
}

const onSketchImageLoad = (e) => {
  seImgW.value = e.target.naturalWidth || 800
  seImgH.value = e.target.naturalHeight || 600
}

const seStageStyle = computed(() => ({
  width: `${seImgW.value}px`,
  height: `${seImgH.value}px`,
  transform: `scale(${seZoom.value})`,
  transformOrigin: 'top left',
}))

const seBoxStyle = (field) => ({
  left: `${field.x}px`,
  top: `${field.y}px`,
  width: `${field.width}px`,
  height: `${field.height}px`,
})

const sePreviewText = (field) => {
  const m = { checkbox: '□', photo: '写真', pen: '手書き', aggregate_okng: 'OK/NG', date: '日付', worker_name: '作業者' }
  return m[field.field_type] || '入力'
}

const seDefaultSize = (type) => {
  if (type === 'checkbox') return { width: 28, height: 28 }
  if (type === 'photo') return { width: 180, height: 120 }
  if (type === 'pen') return { width: 220, height: 120 }
  return { width: 150, height: 34 }
}

const seUniqueKey = (base) => {
  const stem = String(base || `field_${sketchEditorFields.value.length + 1}`).trim().toLowerCase().replace(/[^a-z0-9_]+/g, '_') || `field_${sketchEditorFields.value.length + 1}`
  const taken = new Set(sketchEditorFields.value.map((f) => f.key))
  let key = stem
  let n = 1
  while (taken.has(key)) { key = `${stem}_${n}`; n++ }
  return key
}

const handleStageClick = (e) => {
  const rect = e.currentTarget.getBoundingClientRect()
  const x = Math.round((e.clientX - rect.left) / seZoom.value)
  const y = Math.round((e.clientY - rect.top) / seZoom.value)
  const size = seDefaultSize(seNewField.value.field_type)
  const field = {
    key: seUniqueKey(seNewField.value.key || seNewField.value.label),
    label: seNewField.value.label || '項目',
    field_type: seNewField.value.field_type,
    x: Math.max(0, Math.min(x, seImgW.value - size.width)),
    y: Math.max(0, Math.min(y, seImgH.value - size.height)),
    width: size.width,
    height: size.height,
    required: Boolean(seNewField.value.required),
    sort_order: sketchEditorFields.value.length,
  }
  sketchEditorFields.value.push(field)
  selectedFieldIdx.value = sketchEditorFields.value.length - 1
}

const deleteFieldInEditor = (idx) => {
  sketchEditorFields.value.splice(idx, 1)
  if (selectedFieldIdx.value === idx) selectedFieldIdx.value = null
  else if (selectedFieldIdx.value > idx) selectedFieldIdx.value--
}

const startDragField = (e, field, idx) => {
  if (seResizeState.value) return
  selectedFieldIdx.value = idx
  seDragState.value = {
    field,
    startX: e.clientX,
    startY: e.clientY,
    originX: Number(field.x || 0),
    originY: Number(field.y || 0),
  }
  e.currentTarget.setPointerCapture(e.pointerId)
}

const startResizeField = (e, field) => {
  seDragState.value = null
  seResizeState.value = {
    field,
    startX: e.clientX,
    startY: e.clientY,
    originWidth: Number(field.width || 0),
    originHeight: Number(field.height || 0),
  }
  e.currentTarget.setPointerCapture(e.pointerId)
}

const seOnPointerMove = (e) => {
  if (seResizeState.value) {
    const s = seResizeState.value
    s.field.width = Math.max(6, Math.round(s.originWidth + (e.clientX - s.startX) / seZoom.value))
    s.field.height = Math.max(6, Math.round(s.originHeight + (e.clientY - s.startY) / seZoom.value))
    return
  }
  if (!seDragState.value) return
  const s = seDragState.value
  s.field.x = Math.max(0, Math.round(s.originX + (e.clientX - s.startX) / seZoom.value))
  s.field.y = Math.max(0, Math.round(s.originY + (e.clientY - s.startY) / seZoom.value))
}

const seStopAction = () => {
  seDragState.value = null
  seResizeState.value = null
}

const persistCurrentTemplate = async () => {
  // バリデーション
  if (!form.value.product) {
    alert('製品を選択してください。')
    return null
  }
  if (!form.value.line) {
    alert('ラインを選択してください。')
    return null
  }
  if (!form.value.name) {
    alert('テンプレート名を入力してください。')
    return null
  }

  let templateId = form.value.id

  // テンプレート未作成の場合はまず作成
  if (!templateId) {
    const createRes = await api.integratedChecksheets.createTemplate({
      product: form.value.product,
      line: form.value.line,
      name: form.value.name,
      document_title: form.value.document_title,
      sheet_name: form.value.sheet_name,
      reviewer_user: form.value.reviewer_user || null,
      chief_user: form.value.chief_user || null,
      approver_user: form.value.approver_user || null,
      revision_notes: form.value.revision_notes,
      revision_date: form.value.revision_date || null,
      effective_from: form.value.effective_from || null,
      version: form.value.version,
      is_active: form.value.is_active,
    })
    templateId = createRes.data.id
    form.value.id = templateId
  } else {
    await api.integratedChecksheets.updateTemplate(templateId, {
      name: form.value.name,
      line: form.value.line,
      document_title: form.value.document_title,
      sheet_name: form.value.sheet_name,
      reviewer_user: form.value.reviewer_user || null,
      chief_user: form.value.chief_user || null,
      approver_user: form.value.approver_user || null,
      revision_notes: form.value.revision_notes,
      revision_date: form.value.revision_date || null,
      effective_from: form.value.effective_from || null,
      version: form.value.version,
      is_active: form.value.is_active,
    })
  }

  // 工程ブロック・チェック項目の一括保存
  const blocksPayload = form.value.process_blocks.map((b) => ({
    id: b.id || undefined,
    process: b.process,
    sort_order: b.sort_order,
    items: b.items.map((item) => ({
      id: item.id || undefined,
      item_name: item.item_name,
      standard: item.standard,
      frequency: item.frequency,
      method: item.method,
      record_type: item.record_type,
      unit: item.unit,
      criteria: item.criteria,
      is_required: item.is_required,
    })),
    sketch_fields: b.sketch_fields || [],
  }))

  await api.integratedChecksheets.saveStructure(templateId, {
    process_blocks: blocksPayload,
  })

  // 未アップロードの台紙があればアップロード
  for (const block of form.value.process_blocks) {
    if (block._uploadPending && block.id) {
      await uploadBlockSketch(block)
    }
  }

  return templateId
}

// --- 構造保存 ---
const saveStructure = async () => {
  saving.value = true
  try {
    const templateId = await persistCurrentTemplate()
    if (!templateId) return
    // 再読込
    await loadTemplateList()
    await selectTemplate(templateId)
    alert('構造を保存しました。')
  } catch (e) {
    console.error('保存失敗:', e)
    const detail = e.response?.data?.detail || e.response?.data?.message || e.message
    alert(`保存に失敗しました: ${detail}`)
  } finally {
    saving.value = false
  }
}

// --- ワークフロー状態 ---
const canDraftSave = computed(() => !form.value.status || ['DRAFT', 'REJECTED'].includes(normalizedFormStatus.value))
const canSubmitForReview = computed(() => Boolean(form.value.id) && canEdit.value && canDraftSave.value)
const canReview = computed(() => {
  if (!form.value.id || !canEdit.value) return false
  if (normalizedFormStatus.value === 'SUPERVISOR_PENDING') {
    const reviewerUserId = Number(form.value.reviewer_user || 0)
    return reviewerUserId === 0 || reviewerUserId === currentUserId.value
  }
  if (normalizedFormStatus.value === 'CHIEF_PENDING') {
    const chiefUserId = Number(form.value.chief_user || 0)
    return chiefUserId === 0 || chiefUserId === currentUserId.value
  }
  return false
})
const canApprove = computed(() => {
  if (!form.value.id || !canEdit.value || normalizedFormStatus.value !== 'MANAGER_PENDING') return false
  const approverUserId = Number(form.value.approver_user || 0)
  return approverUserId === 0 || approverUserId === currentUserId.value
})
const canReject = computed(() => canReview.value || canApprove.value)
const canRevise = computed(() => form.value.id && canEdit.value && normalizedFormStatus.value === 'APPROVED')
const reviewActionLabel = computed(() => (normalizedFormStatus.value === 'CHIEF_PENDING' ? '係長承認' : '班長承認'))

const submitForReview = async () => {
  if (!form.value.id || !canSubmitForReview.value) return
  submitComment.value = ''
  submitDialogVisible.value = true
}

const cancelSubmit = () => {
  submitDialogVisible.value = false
  submitComment.value = ''
}

const confirmSubmitForReview = async () => {
  if (!form.value.id) return
  submitDialogVisible.value = false
  actionLoading.value = true
  try {
    const savedTemplateId = await persistCurrentTemplate()
    const targetId = savedTemplateId || form.value.id
    if (!targetId) return
    await api.integratedChecksheets.submitForReview(targetId, submitComment.value)
    await loadTemplateList()
    await selectTemplate(targetId)
    submitComment.value = ''
    alert('確認依頼を送信しました。')
  } catch (e) {
    alert(`確認依頼に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const reviewTemplate = async () => {
  if (!form.value.id || !canReview.value) return
  if (!window.confirm(`${reviewActionLabel.value}します。よろしいですか？`)) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.reviewTemplate(form.value.id)
    await loadTemplateList()
    await selectTemplate(form.value.id)
    alert(`${reviewActionLabel.value}しました。`)
  } catch (e) {
    alert(`${reviewActionLabel.value}に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const approveTemplate = async () => {
  if (!form.value.id || !canApprove.value) return
  if (!window.confirm('部長承認します。よろしいですか？')) return
  actionLoading.value = true
  try {
    await api.integratedChecksheets.approveTemplate(form.value.id)
    await loadTemplateList()
    await selectTemplate(form.value.id)
    alert('部長承認しました。')
  } catch (e) {
    alert(`承認に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const rejectTemplate = () => {
  if (!form.value.id || !canReject.value) return
  rejectComment.value = form.value.rejection_comment || ''
  rejectDialogVisible.value = true
}

const cancelReject = () => {
  rejectDialogVisible.value = false
  rejectComment.value = ''
}

const confirmReject = async () => {
  if (!form.value.id) return
  rejectDialogVisible.value = false
  actionLoading.value = true
  try {
    await api.integratedChecksheets.rejectTemplate(form.value.id, { comment: rejectComment.value })
    await loadTemplateList()
    await selectTemplate(form.value.id)
    rejectComment.value = ''
    alert('差戻ししました。')
  } catch (e) {
    alert(`差戻しに失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    actionLoading.value = false
  }
}

const reviseTemplate = async () => {
  if (!form.value.id) return
  if (!window.confirm('新しい版（改訂）を作成します。よろしいですか？')) return
  saving.value = true
  try {
    const res = await api.integratedChecksheets.reviseTemplate(form.value.id)
    await loadTemplateList()
    await selectTemplate(res.data.id)
    alert(`v${res.data.version} を作成しました。`)
  } catch (e) {
    alert(`改訂に失敗しました: ${e.response?.data?.detail || e.message}`)
  } finally {
    saving.value = false
  }
}

const downloadPreviewPdf = async () => {
  if (!form.value.id) return
  pdfLoading.value = true
  try {
    const res = await api.integratedChecksheets.previewPdf(form.value.id)
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `integrated_checksheet_${form.value.id}.pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('PDF出力に失敗:', error)
    alert('PDF出力に失敗しました。')
  } finally {
    pdfLoading.value = false
  }
}

const notImplementedAction = (label) => {
  alert(`${label}はB案API未実装のため、現在は利用できません。`)
}

// --- 初期化 ---
onMounted(async () => {
  if (!canView.value) return
  await loadMasters()
  await loadTemplateList()
})

watch(
  () => form.value.line,
  () => {
    applyAutoTitles()
    form.value.process_blocks.forEach((block) => {
      if (!block.process) return
      const valid = processOptions.value.some(
        (proc) => String(proc.id) === String(block.process) && String(proc.line || '') === String(form.value.line || '')
      )
      if (!valid) block.process = ''
    })
  }
)
</script>

<style scoped>
.ics-manager {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #111827;
  font-family: 'Meiryo', 'Yu Gothic UI', 'Yu Gothic', sans-serif;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}
.page-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.main-layout {
  display: grid;
  grid-template-columns: 34% 1fr;
  gap: 12px;
  min-height: 0;
}
.panel {
  background: #fff;
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.list-filter-bar {
  display: flex;
  gap: 8px;
  padding: 6px 0 8px;
  flex-wrap: wrap;
}
.list-filter-input {
  flex: 1 1 120px;
  min-width: 100px;
  padding: 4px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.list-filter-select {
  flex: 0 0 auto;
  padding: 4px 8px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th,
.data-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #edf1f5;
  text-align: left;
}
.data-table th {
  background: #f7f9fb;
  font-size: 13px;
  font-weight: 700;
}
.data-table.compact th,
.data-table.compact td {
  padding: 4px 6px;
  font-size: 14px;
  line-height: 1.45;
  vertical-align: top;
  color: #0f172a;
  letter-spacing: 0.02em;
}
.data-table.compact th {
  font-weight: 700;
}
.data-table.compact td {
  font-weight: 400;
}
.data-table.compact tbody tr {
  cursor: pointer;
}
.data-table.compact tbody tr.selected {
  background: #e7f0ff;
}
.status-chip {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}
.status-chip.draft {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #3730a3;
}
.status-chip.ok {
  background: #e9f7ef;
  border-color: #9fd9b4;
  color: #166534;
}
.status-chip.pending {
  background: #fef9e7;
  border-color: #f5d76e;
  color: #92640d;
}
.status-chip.rejected {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #991b1b;
}
.required-mark {
  color: #dc2626;
  font-size: 12px;
  margin-left: 2px;
}
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
.status-meta {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(140px, 1fr));
  gap: 8px;
}
.form-grid .wide {
  grid-column: span 2;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
  font-weight: 500;
}
.form-grid input,
.form-grid select,
.form-grid textarea {
  padding: 5px 7px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.form-grid input:disabled,
.form-grid select:disabled,
.form-grid textarea:disabled {
  background: #f8fafc;
  color: #64748b;
}
.check-line {
  flex-direction: row !important;
  align-items: center;
  gap: 6px !important;
}
.autocomplete {
  position: relative;
}
.suggestions {
  position: absolute;
  z-index: 20;
  left: 0;
  right: 0;
  top: calc(100% + 4px);
  max-height: 280px;
  overflow: auto;
  border: 1px solid #cfd6df;
  border-radius: 6px;
  background: #fff;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.14);
}
.suggestion {
  width: 100%;
  border: 0;
  border-bottom: 1px solid #edf1f5;
  background: #fff;
  padding: 8px 10px;
  display: grid;
  gap: 2px;
  text-align: left;
  cursor: pointer;
}
.suggestion:hover {
  background: #eff6ff;
}
.suggestion span {
  font-weight: 700;
  color: #111827;
}
.suggestion small {
  color: #4b5563;
}
.suggestion-note {
  margin: 0;
  padding: 10px;
  color: #6b7280;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 6px;
  border-top: 1px solid #edf1f5;
}
.section-header h4,
.section-header h5 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}
.no-data {
  color: #6b7280;
  padding: 8px 0;
  font-size: 13px;
}

/* 工程ブロック */
.process-block {
  border: 1px solid #d5d8dc;
  border-radius: 6px;
  overflow: hidden;
}
.block-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
}
.block-toggle {
  font-size: 11px;
  color: #64748b;
  width: 14px;
  text-align: center;
}
.block-title {
  font-weight: 600;
  font-size: 14px;
  color: #0f172a;
  flex: 1;
}
.block-sort {
  font-size: 12px;
  color: #64748b;
}
.block-actions {
  display: flex;
  gap: 4px;
}
.block-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-top: 1px solid #edf1f5;
}

/* 台紙画像 */
.sketch-upload {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.sketch-upload label {
  font-size: 13px;
  color: #334155;
  font-weight: 500;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sketch-preview {
  max-width: 200px;
  max-height: 120px;
  overflow: hidden;
  border: 1px solid #dde2ea;
  border-radius: 4px;
}
.sketch-preview img {
  width: 100%;
  height: auto;
  display: block;
}
.sketch-file-note {
  font-size: 12px;
  color: #475569;
}

/* チェック項目テーブル */
.item-table th,
.item-table td {
  padding: 3px 4px !important;
  font-size: 13px !important;
}
.cell-input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 3px 5px;
  border: 1px solid #cbd5e1;
  border-radius: 3px;
  font-size: 13px;
}
.cell-sm {
  max-width: 80px;
}
.cell-xs {
  max-width: 50px;
}
.center {
  text-align: center;
}

/* アクションボタン */
.edit-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0 0;
  border-top: 1px solid #edf1f5;
}
.rejection-banner {
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  color: #991b1b;
  font-size: 13px;
}

/* ボタン共通 */
.btn-primary,
.btn-secondary,
.btn-sm,
.btn-approve,
.btn-request,
.btn-chief,
.btn-reject,
.btn-revise {
  border-radius: 6px;
  padding: 7px 14px;
  cursor: pointer;
  border: 1px solid transparent;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}
.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.btn-primary:disabled {
  background: #93c5fd;
  border-color: #93c5fd;
  cursor: not-allowed;
}
.btn-secondary {
  background: #fff;
  color: #2563eb;
  border-color: #2563eb;
}
.btn-approve {
  background: #059669;
  color: #fff;
  border-color: #059669;
}
.btn-approve:disabled {
  background: #6ee7b7;
  border-color: #6ee7b7;
  cursor: not-allowed;
}
.btn-request {
  background: #86efac;
  color: #14532d;
  border-color: #4ade80;
}
.btn-chief {
  background: #fcd34d;
  color: #78350f;
  border-color: #fbbf24;
}
.btn-reject {
  background: #fca5a5;
  color: #7f1d1d;
  border-color: #f87171;
}
.btn-revise {
  background: #c4b5fd;
  color: #4c1d95;
  border-color: #a78bfa;
}
.btn-icon {
  background: none;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 2px 5px;
  cursor: pointer;
  font-size: 11px;
  color: #334155;
  line-height: 1;
}
.btn-icon:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.btn-icon:hover:not(:disabled) {
  background: #f1f5f9;
}
.btn-icon-danger {
  color: #dc2626;
  border-color: #fca5a5;
}
.btn-icon-danger:hover:not(:disabled) {
  background: #fef2f2;
}

/* 一覧��りたたみ */
.main-layout.list-collapsed {
  grid-template-columns: 1fr;
}
.panel-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 台紙サムネイル */
.sketch-thumb {
  margin-top: 4px;
}
.sketch-thumb img {
  max-width: 200px;
  max-height: 100px;
  border: 1px solid #dde2ea;
  border-radius: 4px;
  object-fit: contain;
}
.sketch-file-note {
  font-size: 12px;
  color: #475569;
}
.sketch-file-note a {
  color: #2563eb;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-panel {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.25);
  max-width: 520px;
  width: 100%;
}
.reject-modal {
  padding: 0;
}
.reject-modal-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.reject-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.reject-textarea {
  width: 100%;
  resize: vertical;
  min-height: 120px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 8px;
}
.reject-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #e2e8f0;
}

/* 配置エディタモーダル（A案準拠） */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: stretch;
  padding: 16px;
}
.sketch-editor-modal {
  background: #fff;
  border-radius: 8px;
  width: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.sketch-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-bottom: 1px solid #e5e7eb;
  gap: 8px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.sketch-editor-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
.sketch-editor-actions { display: flex; gap: 6px; align-items: center; }
.sketch-editor-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 300px 1fr;
  min-height: 0;
}

/* 左: コントロール */
.se-controls {
  border-right: 1px solid #e5e7eb;
  padding: 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.se-controls h4 { margin: 0; font-size: 14px; font-weight: 700; border-bottom: 1px solid #edf1f5; padding-bottom: 4px; }
.se-form { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.se-form label { display: flex; flex-direction: column; gap: 3px; font-size: 12px; color: #374151; }
.se-form input, .se-form select { border: 1px solid #cfd6df; border-radius: 5px; padding: 5px 7px; font-size: 12px; }
.se-form .full-row { grid-column: 1 / -1; }
.se-hint { margin: 0; color: #6b7280; font-size: 11px; grid-column: 1 / -1; }
.se-field-list { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.se-field-row { display: flex; justify-content: space-between; gap: 6px; border: 1px solid #d8dee6; background: #fff; border-radius: 5px; padding: 6px 8px; text-align: left; cursor: pointer; font-size: 12px; }
.se-field-row.active { border-color: #2563eb; background: #eff6ff; }
.se-field-row small { color: #6b7280; white-space: nowrap; }
.se-detail { border-top: 1px solid #edf1f5; padding-top: 8px; }

/* 右: 台紙キャンバス */
.se-sheet-panel { display: flex; flex-direction: column; min-height: 0; }
.se-toolbar { display: flex; gap: 8px; align-items: center; padding: 6px 10px; border-bottom: 1px solid #edf1f5; flex-shrink: 0; font-size: 13px; }
.se-zoom-label { font-size: 12px; color: #6b7280; min-width: 36px; text-align: center; }
.se-sheet-scroll { flex: 1; overflow: auto; background: #f8fafc; border: 1px solid #edf1f5; }
.se-stage { position: relative; cursor: crosshair; }
.se-sheet-image { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }

/* フィールドボックス */
.se-field-box {
  position: absolute;
  border: 2px solid #2563eb;
  background: rgba(37, 99, 235, 0.12);
  cursor: move;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #111827;
}
.se-field-box.selected { border-color: #dc2626; background: rgba(220, 38, 38, 0.16); }
.se-field-label-tag {
  position: absolute;
  left: 0;
  top: -18px;
  background: #111827;
  color: #fff;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
  font-size: 10px;
  pointer-events: none;
}
.se-field-box.selected .se-field-label-tag { background: #dc2626; }
.se-resize-handle {
  position: absolute;
  right: -8px;
  bottom: -8px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #f59e0b;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.2);
  cursor: nwse-resize;
}
.btn-danger { background: #fff; border: 1px solid #dc2626; color: #dc2626; border-radius: 5px; padding: 5px 10px; cursor: pointer; font-size: 12px; }

@media (max-width: 960px) {
  .main-layout {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
