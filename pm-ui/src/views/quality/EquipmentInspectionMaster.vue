<template>
  <div class="page-container inspection-master" v-if="canView">
    <div class="page-header">
      <h2 class="page-title">点検項目作成</h2>
      <div class="page-actions">
        <button
          class="btn-secondary"
          @click="exportCurrentTemplateExcel"
          :disabled="detailLoading || !form.items.length"
        >
          Excel出力
        </button>
        <button class="btn-secondary" @click="printCurrentTemplate" :disabled="detailLoading">
          PDF出力
        </button>
        <button class="btn-secondary" @click="loadTemplateList" :disabled="loadingList || detailLoading">
          更新
        </button>
        <button
          class="btn-secondary"
          @click="toggleTemplateList"
          :disabled="saving || actionLoading"
        >
          {{ isListHidden ? "一覧表示" : "一覧隠す" }}
        </button>
        <button class="btn-secondary" @click="copyTemplate" :disabled="!form.id || saving || actionLoading || !canEdit">
          コピー作成
        </button>
        <button class="btn-primary" @click="startNewTemplate" :disabled="saving || actionLoading">
          新規作成
        </button>
      </div>
    </div>

    <div class="master-layout" :class="{ 'create-mode': isListHidden }">
      <section v-if="!isListHidden" class="panel list-panel">
        <h3 class="panel-title">テンプレート一覧</h3>
        <div class="list-filter-bar">
          <input
            v-model="listFilter.keyword"
            class="list-filter-input"
            placeholder="設備コード・名称"
          />
          <select v-model="listFilter.status" class="list-filter-select">
            <option value="">状態：すべて</option>
            <option value="DRAFT">下書き</option>
            <option value="SUPERVISOR_PENDING">班長確認待ち</option>
            <option value="CHIEF_PENDING">係長承認待ち</option>
            <option value="MANAGER_PENDING">部長承認待ち</option>
            <option value="APPROVED">承認済み</option>
            <option value="REJECTED">差戻し</option>
          </select>
          <select v-model="listFilter.unit_id" class="list-filter-select" @change="onUnitFilterChange">
            <option value="">グループ：すべて</option>
            <option v-for="u in unitOptions" :key="u.id" :value="u.id">{{ u.name }}</option>
          </select>
          <select v-model="listFilter.line_id" class="list-filter-select">
            <option value="">ライン：すべて</option>
            <option v-for="l in filterLineOptions" :key="l.id" :value="l.id">
              {{ l.line_code }} - {{ l.line_name }}
            </option>
          </select>
          <select v-model="listFilter.process_id" class="list-filter-select">
            <option value="">工程：すべて</option>
            <option v-for="p in processOptions" :key="p.id" :value="p.id">
              {{ p.process_code }} - {{ p.process_name }}
            </option>
          </select>
          <select v-model="listFilter.sheet_code" class="list-filter-select">
            <option value="">設備：すべて</option>
            <option v-for="e in equipmentOptions" :key="e.equipment_code" :value="e.equipment_code">
              {{ e.equipment_code }} - {{ e.equipment_name || '名称未設定' }}
            </option>
          </select>
        </div>
        <div class="table-wrap">
          <table class="data-table compact">
            <thead>
              <tr>
                <th>ID</th>
                <th>設備</th>
                <th>版</th>
                <th>状態</th>
                <th>更新者</th>
                <th>更新日時</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filteredTemplates"
                :key="row.id"
                :class="{ selected: Number(selectedTemplateId) === Number(row.id) }"
                @click="selectTemplate(row.id)"
              >
                <td>{{ row.id }}</td>
                <td>{{ row.sheet_code }} {{ row.sheet_name }}</td>
                <td>{{ row.version }}</td>
                <td>
                  <span class="status-chip" :class="statusClass(row.status)">
                    {{ statusLabel(row.status) }}
                  </span>
                </td>
                <td>{{ row.created_by_name || "-" }}</td>
                <td>{{ formatDateTime(row.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!filteredTemplates.length && !loadingList" class="no-data">データがありません</div>
      </section>

      <section class="panel edit-panel">
        <h3 class="panel-title">編集</h3>

        <div class="status-row">
          <span class="status-chip" :class="statusClass(form.status)">
            {{ statusLabel(form.status) }}
          </span>
          <span class="status-meta">
            作成者: {{ form.created_by_name || "-" }}
            <span v-if="form.created_at" class="status-date">（{{ formatDate(form.created_at) }}）</span>
          </span>
          <span class="status-meta">
            班長担当: {{ form.reviewer_user_name || "-" }}
            <span v-if="form.reviewed_at" class="status-date">（{{ formatDate(form.reviewed_at) }}）</span>
          </span>
          <span class="status-meta">
            係長担当: {{ form.chief_user_name || "-" }}
            <span v-if="form.chief_reviewed_at" class="status-date">（{{ formatDate(form.chief_reviewed_at) }}）</span>
          </span>
          <span class="status-meta">
            部長担当: {{ form.approver_user_name || "-" }}
            <span v-if="form.approved_at" class="status-date">（{{ formatDate(form.approved_at) }}）</span>
          </span>
        </div>

        <div class="form-grid">
          <label>
            設備コード <span class="required-mark">*</span>
            <select v-model="form.sheet_code" :disabled="!canEditFields || equipmentLoading" @change="handleSheetCodeChange">
              <option value="">選択してください</option>
              <option
                v-for="equipment in equipmentSelectOptions"
                :key="equipment.id || equipment.equipment_code"
                :value="equipment.equipment_code"
              >
                {{ equipment.equipment_code }} - {{ equipment.equipment_name || "名称未設定" }}
              </option>
            </select>
          </label>
          <label>
            設備名 <span class="required-mark">*</span>
            <input v-model.trim="form.sheet_name" :disabled="!canEditFields" />
          </label>
          <label class="wide">
            帳票タイトル <span class="required-mark">*</span>
            <input v-model.trim="form.title" :disabled="!canEditFields" />
          </label>
          <label>
            元シート名
            <input v-model.trim="form.source_sheet_name" :disabled="!canEditFields" />
          </label>
          <label>
            改訂日 <span class="required-mark">*</span>
            <input type="date" v-model="form.revision_date" :disabled="!canEditFields" />
          </label>
          <label class="wide">
            改訂内容 <span class="required-mark">*</span>
            <textarea v-model="form.revision_notes" :disabled="!canEditFields" rows="2" />
          </label>
          <label>
            運用開始日 <span class="required-mark">*</span>
            <input type="date" v-model="form.effective_from" :disabled="!canEditFields" />
          </label>
          <label>
            版 <span class="required-mark">*</span>
            <input type="number" min="1" v-model.number="form.version" :disabled="!canEditFields" />
          </label>
          <label class="check-line">
            <input type="checkbox" v-model="form.is_active" :disabled="!canEditFields" />
            有効
          </label>
          <div class="wide multi-select-group">
            <span class="multi-select-label">対象工程（複数選択可）</span>
            <div class="multi-select-row">
              <select v-model="form.processes" multiple :disabled="!canEditFields" size="4" class="multi-select">
                <option v-for="p in processOptions" :key="p.id" :value="p.id">
                  {{ p.process_code }} - {{ p.process_name }}
                </option>
              </select>
              <div class="selected-tags">
                <span v-if="!selectedProcessTags.length" class="no-selection">未選択</span>
                <span
                  v-for="p in selectedProcessTags"
                  :key="p.id"
                  class="selection-tag"
                >
                  {{ p.process_code }} - {{ p.process_name }}
                  <button v-if="canEditFields" class="tag-remove" @click="removeProcess(p.id)">×</button>
                </span>
              </div>
            </div>
          </div>
          <div class="wide multi-select-group">
            <span class="multi-select-label">対象ライン（複数選択可）</span>
            <div class="multi-select-row">
              <select v-model="form.lines" multiple :disabled="!canEditFields" size="4" class="multi-select">
                <option v-for="l in lineOptions" :key="l.id" :value="l.id">
                  {{ l.line_code }} - {{ l.line_name }}
                </option>
              </select>
              <div class="selected-tags">
                <span v-if="!selectedLineTags.length" class="no-selection">未選択</span>
                <span
                  v-for="l in selectedLineTags"
                  :key="l.id"
                  class="selection-tag"
                >
                  {{ l.line_code }} - {{ l.line_name }}
                  <button v-if="canEditFields" class="tag-remove" @click="removeLine(l.id)">×</button>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="form.rejection_comment" class="rejection-box">
          差戻しコメント: {{ form.rejection_comment }}
        </div>

        <div class="workflow-actions">
          <button class="btn-primary" @click="saveTemplate" :disabled="!canEditFields || saving">
            {{ form.id ? "下書き更新" : "下書き保存" }}
          </button>
          <button class="btn-secondary" @click="openOperationExcelPicker" :disabled="!canEditFields || excelImportLoading">
            {{ excelImportLoading ? "Excel読込中..." : "運用中Excel読込" }}
          </button>
          <input
            ref="operationExcelInput"
            type="file"
            accept=".xlsx,.xls"
            class="hidden-file-input"
            :disabled="!canEditFields || excelImportLoading"
            @change="onOperationExcelFileChange"
          />
          <button v-if="form.id" class="btn-secondary" @click="openTestOperation" :disabled="saving || actionLoading">テスト実施</button>
          <button class="btn-approve" @click="submitForReview" :disabled="!canSubmitForReview || actionLoading">
            確認依頼
          </button>
          <button class="btn-review" @click="completeReview" :disabled="!canReview || actionLoading">
            {{ reviewActionLabel }}
          </button>
          <button class="btn-approve" @click="approveTemplate" :disabled="!canApprove || actionLoading">
            部長承認
          </button>
          <button class="btn-danger" @click="rejectTemplate" :disabled="!canReject || actionLoading">
            差戻し
          </button>
          <button class="btn-revise" @click="reviseTemplate" :disabled="!canRevise || actionLoading">
            改訂
          </button>
        </div>

        <div class="item-section">
          <div class="section-header">
            <h4>日次点検項目</h4>
            <button class="btn-secondary btn-sm" @click="addItem('DAILY')" :disabled="!canEditFields">
              行追加
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table compact daily-inspection-table">
              <thead>
                <tr>
                  <th class="col-no">No</th>
                  <th>点検項目</th>
                  <th>規格</th>
                  <th>方法</th>
                  <th>確認頻度</th>
                  <th>記録種別</th>
                  <th>単位</th>
                  <th>判定基準</th>
                  <th>必須</th>
                  <th>有効</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dailyItems" :key="item.local_key" :class="{ 'diff-new': itemDiffStatus(item) === 'new', 'diff-changed': itemDiffStatus(item) === 'changed' }">
                  <td class="col-no">
                    <input
                      class="no-input"
                      type="number"
                      min="1"
                      v-model.number="item.inspection_no"
                      :disabled="!canEditFields"
                    />
                  </td>
                  <td>
                    <span v-if="itemDiffStatus(item) === 'new'" class="diff-badge diff-badge-new">新規</span>
                    <span v-else-if="itemDiffStatus(item) === 'changed'" class="diff-badge diff-badge-changed">{{ diffLabel }}</span>
                    <textarea class="auto-grow-textarea" v-model="item.item_name" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" />
                  </td>
                  <td><textarea class="auto-grow-textarea" v-model="item.standard" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td><textarea class="auto-grow-textarea" v-model="item.method" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td>
                    <select :value="frequencySelectValue(item)" :disabled="!canEditFields" @change="onFrequencySelect(item, $event)">
                      <option v-for="opt in FREQUENCY_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
                      <option value="__custom__">その他</option>
                    </select>
                    <input v-if="frequencySelectValue(item) === '__custom__'" v-model="item.frequency" :disabled="!canEditFields" placeholder="頻度を入力" style="margin-top:2px" />
                  </td>
                  <td>
                    <select v-model="item.record_type" :disabled="!canEditFields">
                      <option value="CHECK">チェック</option>
                      <option value="NUMERIC">数値</option>
                      <option value="PHOTO_NUMERIC">写真＋数値</option>
                      <option value="PHOTO">写真のみ</option>
                      <option value="TEXT">文字</option>
                    </select>
                  </td>
                  <td><input v-model="item.unit" :disabled="!canEditFields" /></td>
                  <td><textarea class="auto-grow-textarea" v-model="item.criteria" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td class="center"><input type="checkbox" v-model="item.is_required" :disabled="!canEditFields" /></td>
                  <td class="center"><input type="checkbox" v-model="item.is_active" :disabled="!canEditFields" /></td>
                  <td>
                    <button class="btn-secondary btn-sm" @click="openAttachmentDialog(item)">
                      付表{{ attachmentCountLabel(item) ? `(${attachmentCountLabel(item)})` : "" }}
                    </button>
                    <button class="btn-danger btn-sm" @click="removeItem(item)" :disabled="!canEditFields">削除</button>
                  </td>
                </tr>
                <tr
                  v-for="item in deletedItems.filter(i => i.section_type === 'DAILY')"
                  :key="`deleted-${item.inspection_no}-${item.item_name}`"
                  class="diff-deleted"
                >
                  <td class="col-no">{{ item.inspection_no }}</td>
                  <td>
                    <span class="diff-badge diff-badge-deleted">削除</span>
                    {{ item.item_name }}
                  </td>
                  <td>{{ item.standard }}</td>
                  <td>{{ item.method }}</td>
                  <td>{{ item.frequency }}</td>
                  <td>{{ recordTypeLabel(item.record_type) }}</td>
                  <td>{{ item.unit }}</td>
                  <td>{{ item.criteria }}</td>
                  <td colspan="3"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="item-section">
          <div class="section-header">
            <h4>{{ quarterlyTitle }}</h4>
            <div class="measurement-schedule-wrap" v-if="canEditFields">
              <label class="schedule-type-radio">
                <input type="radio" value="MONTHLY" v-model="form.measurement_schedule_type" /> 月
              </label>
              <label class="schedule-type-radio">
                <input type="radio" value="WEEKDAY" v-model="form.measurement_schedule_type" /> 曜日
              </label>
            </div>
            <div class="measurement-months-wrap" v-if="canEditFields && form.measurement_schedule_type === 'MONTHLY'">
              <span class="measurement-months-label">対象月:</span>
              <label v-for="m in 12" :key="m" class="measurement-month-check">
                <input type="checkbox" :checked="form.measurement_months.includes(m)" @change="toggleMeasurementMonth(m)" />
                {{ m }}月
              </label>
            </div>
            <div class="measurement-months-wrap" v-if="canEditFields && form.measurement_schedule_type === 'WEEKDAY'">
              <span class="measurement-months-label">対象曜日:</span>
              <label v-for="opt in WEEKDAY_OPTIONS" :key="opt.value" class="measurement-month-check">
                <input type="checkbox" :checked="form.measurement_weekdays.includes(opt.value)" @change="toggleMeasurementWeekday(opt.value)" />
                {{ opt.label }}
              </label>
            </div>
            <button class="btn-secondary btn-sm" @click="addItem('QUARTERLY')" :disabled="!canEditFields">
              行追加
            </button>
          </div>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th class="col-no">No</th>
                  <th>項目</th>
                  <th>規格（設定）</th>
                  <th>確認方法</th>
                  <th>参考値/単位</th>
                  <th>確認頻度</th>
                  <th>判定基準</th>
                  <th>記録種別</th>
                  <th>有効</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in quarterlyItems" :key="item.local_key" :class="{ 'diff-new': itemDiffStatus(item) === 'new', 'diff-changed': itemDiffStatus(item) === 'changed' }">
                  <td class="col-no">
                    <input
                      class="no-input"
                      type="number"
                      min="1"
                      v-model.number="item.inspection_no"
                      :disabled="!canEditFields"
                    />
                  </td>
                  <td>
                    <span v-if="itemDiffStatus(item) === 'new'" class="diff-badge diff-badge-new">新規</span>
                    <span v-else-if="itemDiffStatus(item) === 'changed'" class="diff-badge diff-badge-changed">{{ diffLabel }}</span>
                    <textarea class="auto-grow-textarea" v-model="item.item_name" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" />
                  </td>
                  <td><textarea class="auto-grow-textarea" v-model="item.standard" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td><textarea class="auto-grow-textarea" v-model="item.confirmation_method" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td><textarea class="auto-grow-textarea" v-model="item.method" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td>
                    <select :value="frequencySelectValue(item)" :disabled="!canEditFields" @change="onFrequencySelect(item, $event)">
                      <option v-for="opt in FREQUENCY_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
                      <option value="__custom__">その他</option>
                    </select>
                    <input v-if="frequencySelectValue(item) === '__custom__'" v-model="item.frequency" :disabled="!canEditFields" placeholder="頻度を入力" style="margin-top:2px" />
                  </td>
                  <td><textarea class="auto-grow-textarea" v-model="item.criteria" rows="2" :disabled="!canEditFields" @input="resizeTextarea" @focus="resizeTextarea" /></td>
                  <td>
                    <select v-model="item.record_type" :disabled="!canEditFields">
                      <option value="CHECK">チェック</option>
                      <option value="NUMERIC">数値</option>
                      <option value="PHOTO_NUMERIC">写真＋数値</option>
                      <option value="PHOTO">写真のみ</option>
                      <option value="TEXT">文字</option>
                    </select>
                  </td>
                  <td class="center"><input type="checkbox" v-model="item.is_active" :disabled="!canEditFields" /></td>
                  <td>
                    <button class="btn-secondary btn-sm" @click="openAttachmentDialog(item)">
                      付表{{ attachmentCountLabel(item) ? `(${attachmentCountLabel(item)})` : "" }}
                    </button>
                    <button class="btn-danger btn-sm" @click="removeItem(item)" :disabled="!canEditFields">削除</button>
                  </td>
                </tr>
                <tr
                  v-for="item in deletedItems.filter(i => i.section_type === 'QUARTERLY')"
                  :key="`deleted-q-${item.item_name}`"
                  class="diff-deleted"
                >
                  <td class="col-no">{{ item.inspection_no }}</td>
                  <td>
                    <span class="diff-badge diff-badge-deleted">削除</span>
                    {{ item.item_name }}
                  </td>
                  <td>{{ item.standard }}</td>
                  <td>{{ item.confirmation_method }}</td>
                  <td>{{ item.method }}</td>
                  <td>{{ item.frequency }}</td>
                  <td>{{ item.criteria }}</td>
                  <td>{{ recordTypeLabel(item.record_type) }}</td>
                  <td colspan="2"></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="item-section">
          <h4>ワークフロー履歴</h4>
          <div class="table-wrap">
            <table class="data-table compact">
              <thead>
                <tr>
                  <th>日時</th>
                  <th>操作</th>
                  <th>遷移</th>
                  <th>実施者</th>
                  <th>コメント</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in form.workflow_logs" :key="log.id">
                  <td>{{ formatDateTime(log.created_at) }}</td>
                  <td>{{ actionLabel(log.action) }}</td>
                  <td>{{ transitionLabel(log.from_status, log.to_status) }}</td>
                  <td>{{ log.actor_name || "-" }}</td>
                  <td>{{ log.comment || "-" }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!form.workflow_logs.length" class="no-data">履歴はありません</div>
        </div>
      </section>
    </div>

    <!-- 確認依頼コメントモーダル -->
    <div v-if="submitDialogVisible" class="modal-backdrop" @click.self="cancelSubmit">
      <div class="modal-panel reject-modal">
        <div class="modal-header">
          <h3 class="panel-title">確認依頼</h3>
        </div>
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

    <!-- 差戻しコメントモーダル -->
    <div v-if="rejectDialogVisible" class="modal-backdrop" @click.self="cancelReject">
      <div class="modal-panel reject-modal">
        <div class="modal-header">
          <h3 class="panel-title">差戻し</h3>
        </div>
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
          <button class="btn-danger" @click="confirmReject">差戻し実行</button>
        </div>
      </div>
    </div>

    <div v-if="attachmentDialogVisible" class="modal-backdrop" @click.self="closeAttachmentDialog">
      <div class="modal-panel attachment-modal">
        <div class="modal-header">
          <div>
            <h3 class="panel-title">付表編集</h3>
            <div class="attachment-target-name">{{ attachmentTargetItem?.item_name || "未選択" }}</div>
          </div>
          <button class="btn-secondary btn-sm" @click="closeAttachmentDialog">閉じる</button>
        </div>

        <div v-if="attachmentTargetItem" class="attachment-body">
          <div class="attachment-actions">
            <button class="btn-primary btn-sm" @click="addAttachment" :disabled="!canEditFields">
              付表追加
            </button>
          </div>

          <div v-if="!attachmentTargetItem.attachments.length" class="no-data">
            付表はまだありません。
          </div>

          <div
            v-for="attachment in attachmentTargetItem.attachments"
            :key="attachment.local_key"
            class="attachment-card"
          >
            <div class="attachment-card-header">
              <strong>付表 {{ attachment.display_order }}</strong>
              <button class="btn-danger btn-sm" @click="removeAttachment(attachment)" :disabled="!canEditFields">
                削除
              </button>
            </div>

            <div class="attachment-form-grid">
              <label>
                タイトル
                <input v-model.trim="attachment.title" :disabled="!canEditFields" />
              </label>
              <label>
                画像
                <input type="file" accept="image/*" :disabled="!canEditFields" @change="uploadAttachmentImage($event, attachment)" />
              </label>
              <label class="wide">
                補足説明
                <textarea v-model="attachment.description" rows="2" :disabled="!canEditFields" />
              </label>
              <label class="wide">
                確認ポイント
                <textarea v-model="attachment.check_point" rows="2" :disabled="!canEditFields" />
              </label>
              <label class="wide">
                OK例
                <textarea v-model="attachment.ok_example" rows="2" :disabled="!canEditFields" />
              </label>
              <label class="wide">
                NG例
                <textarea v-model="attachment.ng_example" rows="2" :disabled="!canEditFields" />
              </label>
            </div>

            <div v-if="attachment.image_url" class="attachment-preview">
              <img :src="attachment.image_url" :alt="attachment.title || attachmentTargetItem.item_name" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="page-container" v-else>
    <h2 class="page-title">点検項目作成</h2>
    <p class="no-data">品質の閲覧権限がありません。</p>
  </div>
</template>

<script setup>
import { formatISODate } from '@/utils/dateUtil'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue"
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router"
import * as XLSX from "xlsx"
import api from "@/api/client"
import { authState } from "@/auth"
import { hasPermission } from "@/router"

const STATUS_LABELS = {
  DRAFT: "下書き",
  REVIEW_PENDING: "班長確認待ち",
  APPROVAL_PENDING: "部長承認待ち",
  SUPERVISOR_PENDING: "班長確認待ち",
  CHIEF_PENDING: "係長承認待ち",
  MANAGER_PENDING: "部長承認待ち",
  APPROVED: "承認済み",
  REJECTED: "差戻し",
}

const ACTION_LABELS = {
  CREATED: "作成",
  UPDATED: "更新",
  SUBMITTED: "確認依頼",
  REVIEWED: "確認完了",
  SUPERVISOR_REVIEWED: "班長確認完了",
  CHIEF_REVIEWED: "係長承認",
  APPROVED: "部長承認",
  REJECTED: "差戻し",
}

const RECORD_TYPE_LABELS = {
  CHECK: "チェック",
  NUMERIC: "数値",
  PHOTO_NUMERIC: "写真＋数値",
  PHOTO: "写真のみ",
  TEXT: "文字",
}

const FREQUENCY_OPTIONS = ["始業時", "週初め", "週末", "月初め", "月末", "月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
function isPresetFrequency(val) {
  return FREQUENCY_OPTIONS.includes(val)
}
function onFrequencySelect(item, ev) {
  const v = ev.target.value
  if (v === "__custom__") {
    item.frequency = ""
  } else {
    item.frequency = v
  }
}
function frequencySelectValue(item) {
  if (!item.frequency) return "__custom__"
  return isPresetFrequency(item.frequency) ? item.frequency : "__custom__"
}

const route = useRoute()
const router = useRouter()

const templates = ref([])
const loadingList = ref(false)
const detailLoading = ref(false)
const saving = ref(false)
const actionLoading = ref(false)
const selectedTemplateId = ref(null)
const isListHidden = ref(false)
const equipmentOptions = ref([])
const equipmentLoading = ref(false)
const processOptions = ref([])
const lineOptions = ref([])
const attachmentDialogVisible = ref(false)
const attachmentTargetKey = ref("")
const rejectDialogVisible = ref(false)
const rejectComment = ref("")
const submitDialogVisible = ref(false)
const submitComment = ref("")
const listFilter = ref({ keyword: "", status: "", unit_id: "", line_id: "", process_id: "", sheet_code: "" })
const unitOptions = ref([])
const unitLineMappings = ref([])
const prevVersionItems = ref([])
const operationExcelInput = ref(null)
const excelImportLoading = ref(false)

const createEmptyForm = () => ({
  id: null,
  sheet_code: "",
  sheet_name: "",
  title: "",
  source_sheet_name: "",
  created_at: "",
  revision_date: "",
  revision_notes: "",
  effective_from: "",
  version: 1,
  status: "DRAFT",
  is_active: true,
  created_by: null,
  created_by_name: "",
  reviewer_user: null,
  reviewer_user_name: "",
  chief_user: null,
  chief_user_name: "",
  approver_user: null,
  approver_user_name: "",
  rejection_comment: "",
  reviewed_at: "",
  chief_reviewed_at: "",
  approved_at: "",
  processes: [],
  lines: [],
  items: [],
  measurement_months: [],
  measurement_schedule_type: "MONTHLY",
  measurement_weekdays: [],
  workflow_logs: [],
})

const form = ref(createEmptyForm())
const savedPayloadSnapshot = ref("")
const isRestoringRouteQuery = ref(false)
const UNSAVED_CHANGES_MESSAGE = "編集後保存せずに移動すると入力内容は失われます。移動しますか？未変更or保存した場合はOK、未保存の場合はキャンセルをクリックしてください"

const createPayloadSnapshot = () => JSON.stringify(buildPayload())
const markSavedSnapshot = () => {
  savedPayloadSnapshot.value = createPayloadSnapshot()
}
const hasUnsavedChanges = computed(() => {
  if (!canEditFields.value) return false
  if (detailLoading.value || saving.value || actionLoading.value) return false
  return createPayloadSnapshot() !== savedPayloadSnapshot.value
})
const confirmDiscardUnsavedChanges = () => {
  if (!hasUnsavedChanges.value) return true
  return window.confirm(UNSAVED_CHANGES_MESSAGE)
}

const equipmentSelectOptions = computed(() => {
  const options = Array.isArray(equipmentOptions.value) ? [...equipmentOptions.value] : []
  const currentCode = String(form.value.sheet_code || "").trim()
  if (!currentCode) return options
  const exists = options.some((item) => String(item.equipment_code || "").trim() === currentCode)
  if (exists) return options
  options.unshift({
    id: `legacy-${currentCode}`,
    equipment_code: currentCode,
    equipment_name: form.value.sheet_name || "マスタ未登録",
  })
  return options
})

const canAccessQuality = (resource, level = "view") => {
  const user = authState.user
  if (!user) return false
  if (user.is_superuser) return true
  const permissions = Array.isArray(user.effective_permissions) ? user.effective_permissions : []
  if (permissions.some((item) => item.resource === resource)) {
    return hasPermission(user, resource, level)
  }
  return hasPermission(user, "quality", level)
}

const canView = computed(() => canAccessQuality("quality.equipment_inspection_master", "view"))
const canEdit = computed(() => canAccessQuality("quality.equipment_inspection_master", "edit"))
const currentUserId = computed(() => Number(authState.user?.id || 0))
const normalizeStatus = (status) => String(status || "").trim().toUpperCase()
const normalizedFormStatus = computed(() => normalizeStatus(form.value.status) || "DRAFT")

const canEditFields = computed(() => {
  if (!canEdit.value) return false
  if (!form.value.id) return true
  return ["DRAFT", "REJECTED"].includes(normalizedFormStatus.value)
})

const canSubmitForReview = computed(() => {
  return Boolean(form.value.id) && canEditFields.value
})

const canReview = computed(() => {
  if (!canEdit.value) return false
  if (normalizedFormStatus.value === "SUPERVISOR_PENDING" || normalizedFormStatus.value === "REVIEW_PENDING") {
    const reviewerUserId = Number(form.value.reviewer_user || 0)
    return reviewerUserId === 0 || reviewerUserId === currentUserId.value
  }
  if (normalizedFormStatus.value === "CHIEF_PENDING") {
    const chiefUserId = Number(form.value.chief_user || 0)
    return chiefUserId === 0 || chiefUserId === currentUserId.value
  }
  return false
})

const canApprove = computed(() => {
  if (!canEdit.value) return false
  if (!["MANAGER_PENDING", "APPROVAL_PENDING"].includes(normalizedFormStatus.value)) return false
  const approverUserId = Number(form.value.approver_user || 0)
  return approverUserId === 0 || approverUserId === currentUserId.value
})

const canReject = computed(() => canReview.value || canApprove.value)
const canRevise = computed(() => canEdit.value && normalizedFormStatus.value === "APPROVED")

const selectedProcessTags = computed(() =>
  processOptions.value.filter((p) => (form.value.processes || []).map(Number).includes(Number(p.id)))
)
const selectedLineTags = computed(() =>
  lineOptions.value.filter((l) => (form.value.lines || []).map(Number).includes(Number(l.id)))
)
const unitLineIdsMap = computed(() => {
  const map = {}
  for (const m of unitLineMappings.value) {
    const uid = Number(m.unit)
    if (!map[uid]) map[uid] = []
    map[uid].push(Number(m.line))
  }
  return map
})

const filterLineOptions = computed(() => {
  const uid = Number(listFilter.value.unit_id || 0)
  if (!uid) return lineOptions.value
  const ids = unitLineIdsMap.value[uid] || []
  return lineOptions.value.filter(l => ids.includes(Number(l.id)))
})

const onUnitFilterChange = () => {
  const uid = Number(listFilter.value.unit_id || 0)
  if (!uid) return
  const lid = Number(listFilter.value.line_id || 0)
  if (!lid) return
  const ids = unitLineIdsMap.value[uid] || []
  if (!ids.includes(lid)) listFilter.value.line_id = ""
}

const filteredTemplates = computed(() => {
  const kw = listFilter.value.keyword.trim().toLowerCase()
  const st = listFilter.value.status
  const uid = Number(listFilter.value.unit_id || 0)
  const lid = Number(listFilter.value.line_id || 0)
  const pid = Number(listFilter.value.process_id || 0)
  const sc = listFilter.value.sheet_code
  return templates.value.filter((row) => {
    if (st && row.status !== st) return false
    if (kw) {
      const haystack = `${row.sheet_code || ""} ${row.sheet_name || ""}`.toLowerCase()
      if (!haystack.includes(kw)) return false
    }
    if (sc && row.sheet_code !== sc) return false
    if (pid) {
      const procs = (row.processes || []).map(Number)
      if (!procs.includes(pid)) return false
    }
    if (lid) {
      const lns = (row.lines || []).map(Number)
      if (!lns.includes(lid)) return false
    } else if (uid) {
      const groupLines = unitLineIdsMap.value[uid] || []
      const lns = (row.lines || []).map(Number)
      if (!lns.some(l => groupLines.includes(l))) return false
    }
    return true
  })
})
// 差分表示: 前版との比較 / 差し戻し後修正の比較
const DIFF_FIELDS = ["item_name", "standard", "frequency", "method", "record_type", "unit", "criteria", "is_required", "is_active"]
const PENDING_STATUSES = ["SUPERVISOR_PENDING", "CHIEF_PENDING", "MANAGER_PENDING"]

// スナップショット比較（差し戻し後再提出時）: 上長確認画面で前回提出時との差分を表示
const isSnapshotDiff = computed(() => {
  const snapshot = form.value.submitted_items_snapshot
  if (!snapshot || !snapshot.length) return false
  return PENDING_STATUSES.includes(normalizedFormStatus.value)
})

// 差分比較のベースとなるアイテム一覧（スナップショット優先、なければ前版）
const diffBaseItems = computed(() => {
  if (isSnapshotDiff.value) return form.value.submitted_items_snapshot
  return prevVersionItems.value
})
const showDiff = computed(() => diffBaseItems.value.length > 0)
// 差分の種別ラベル（改訂 vs 修正）
const diffLabel = computed(() => isSnapshotDiff.value ? "修正" : "改訂")

const isSameItem = (a, b) => {
  const sectionA = String(a?.section_type || "")
  const sectionB = String(b?.section_type || "")
  if (sectionA !== sectionB) return false

  const idA = Number(a?.id || 0)
  const idB = Number(b?.id || 0)
  if (idA > 0 && idB > 0) return idA === idB

  const noA = Number(a?.inspection_no || 0)
  const noB = Number(b?.inspection_no || 0)
  if (noA > 0 && noB > 0) return noA === noB

  const nameA = String(a?.item_name || "").trim()
  const nameB = String(b?.item_name || "").trim()
  if (nameA && nameB) return nameA === nameB

  return false
}

const findPrevItem = (item) => {
  return diffBaseItems.value.find((p) => isSameItem(p, item)) || null
}
const itemDiffStatus = (item) => {
  if (!showDiff.value) return null
  const prev = findPrevItem(item)
  if (!prev) return "new"
  for (const field of DIFF_FIELDS) {
    if (String(item[field] ?? "") !== String(prev[field] ?? "")) return "changed"
  }
  return null
}
const deletedItems = computed(() => {
  if (!showDiff.value) return []
  return diffBaseItems.value.filter((prev) =>
    !form.value.items.some((cur) => isSameItem(cur, prev))
  )
})

const removeProcess = (id) => {
  form.value.processes = (form.value.processes || []).filter((v) => Number(v) !== Number(id))
}
const removeLine = (id) => {
  form.value.lines = (form.value.lines || []).filter((v) => Number(v) !== Number(id))
}
const reviewActionLabel = computed(() => {
  if (normalizedFormStatus.value === "CHIEF_PENDING") return "係長承認"
  return "班長確認完了"
})

const statusLabel = (status) => {
  const normalized = normalizeStatus(status)
  return STATUS_LABELS[normalized] || status
}
const actionLabel = (action) => ACTION_LABELS[action] || action

const statusClass = (status) => {
  const normalized = normalizeStatus(status)
  if (normalized === "APPROVED") return "ok"
  if (normalized === "REJECTED") return "danger"
  if (["MANAGER_PENDING", "APPROVAL_PENDING"].includes(normalized)) return "approve"
  if (["SUPERVISOR_PENDING", "REVIEW_PENDING"].includes(normalized)) return "review"
  if (normalized === "CHIEF_PENDING") return "approve"
  return "draft"
}

const transitionLabel = (fromStatus, toStatus) => {
  const from = statusLabel(fromStatus || "")
  const to = statusLabel(toStatus || "")
  if (!from && !to) return "-"
  if (!from) return `→ ${to}`
  if (!to) return from
  return `${from} → ${to}`
}

const escapeHtml = (value) => {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
}

const toPrintCell = (value) => {
  return escapeHtml(String(value ?? "")).replace(/\n/g, "<br>")
}

const recordTypeLabel = (value) => RECORD_TYPE_LABELS[String(value || "").trim()] || (value || "")

const resolveApprovalNames = () => {
  const normalizedSupervisor = String(form.value.reviewer_user_name || "").trim()
  const normalizedChief = String(form.value.chief_user_name || "").trim()
  const normalizedManager = String(form.value.approver_user_name || "").trim()
  const names = {
    supervisor: normalizedSupervisor || "-",
    chief: normalizedChief || "-",
    manager: normalizedManager || "-",
  }

  ;(form.value.workflow_logs || []).forEach((log) => {
    const actorName = String(log?.actor_name || "").trim()
    if (!actorName) return
    const action = String(log?.action || "").trim()
    if (["REVIEWED", "SUPERVISOR_REVIEWED"].includes(action)) {
      names.supervisor = actorName
      return
    }
    if (action === "CHIEF_REVIEWED") {
      names.chief = actorName
      return
    }
    if (action === "APPROVED") {
      names.manager = actorName
    }
  })
  return names
}

const buildAttachmentAppendixRows = () => {
  const rows = []
  const targetItems = [...dailyItems.value, ...quarterlyItems.value]
  targetItems.forEach((item) => {
    const attachments = Array.isArray(item.attachments) ? item.attachments : []
    attachments.forEach((attachment, index) => {
      rows.push(["点検項目", item.item_name || ""])
      rows.push(["付表No", index + 1])
      rows.push(["タイトル", attachment.title || ""])
      rows.push(["画像URL", attachment.image_url || ""])
      rows.push(["補足説明", attachment.description || ""])
      rows.push(["確認ポイント", attachment.check_point || ""])
      rows.push(["OK例", attachment.ok_example || ""])
      rows.push(["NG例", attachment.ng_example || ""])
      rows.push([])
    })
  })
  return rows
}

const buildAttachmentPrintHtml = () => {
  const targetItems = [...dailyItems.value, ...quarterlyItems.value]
  const sections = targetItems
    .map((item) => {
      const attachments = Array.isArray(item.attachments) ? item.attachments : []
      if (!attachments.length) return ""
      const cards = attachments
        .map(
          (attachment, index) => `
          <div class="appendix-card">
            <div class="appendix-card-title">付表 ${index + 1} ${escapeHtml(attachment.title || "")}</div>
            ${
              attachment.image_url
                ? `<div class="appendix-image-wrap"><img class="appendix-image" src="${escapeHtml(
                    attachment.image_url
                  )}" alt="${escapeHtml(attachment.title || item.item_name || "付表画像")}" /></div>`
                : ""
            }
            <div class="appendix-text-row"><strong>補足説明:</strong> ${toPrintCell(attachment.description)}</div>
            <div class="appendix-text-row"><strong>確認ポイント:</strong> ${toPrintCell(attachment.check_point)}</div>
            <div class="appendix-text-row"><strong>OK例:</strong> ${toPrintCell(attachment.ok_example)}</div>
            <div class="appendix-text-row"><strong>NG例:</strong> ${toPrintCell(attachment.ng_example)}</div>
          </div>
        `
        )
        .join("")
      return `
        <section class="appendix-section">
          <div class="appendix-item-title">${escapeHtml(item.item_name || "点検項目")}</div>
          ${cards}
        </section>
      `
    })
    .filter(Boolean)
    .join("")

  if (!sections) return ""

  return `
    <div class="appendix-page-break"></div>
    <div class="appendix-root">
      <div class="appendix-root-title">付表</div>
      ${sections}
    </div>
  `
}

const exportCurrentTemplateExcel = () => {
  if (!form.value.items.length) {
    alert("出力対象の点検項目がありません。")
    return
  }

  const statusText = statusLabel(form.value.status)
  const exportedAt = new Date().toLocaleString("ja-JP")
  const sheetName = String(form.value.sheet_code || "設備点検表").slice(0, 31)
  const safeSheetCode = String(form.value.sheet_code || "template")
    .replace(/[\\/:*?"<>|]/g, "_")
    .trim()
  const safeStatus = String(statusText || "下書き").replace(/[\\/:*?"<>|]/g, "_").trim()
  const datePart = formatISODate(new Date())

  const rows = [
    [form.value.title || "設備点検表"],
    [],
    ["設備コード", form.value.sheet_code || ""],
    ["設備名", form.value.sheet_name || ""],
    ["版", form.value.version || ""],
    ["状態", statusText],
    ["改訂日", form.value.revision_date || ""],
    ["運用開始日", form.value.effective_from || ""],
    ["作成者", form.value.created_by_name || ""],
    ["班長担当", form.value.reviewer_user_name || ""],
    ["係長担当", form.value.chief_user_name || ""],
    ["部長担当", form.value.approver_user_name || ""],
    ["出力日時", exportedAt],
    [],
    ["日次点検項目"],
    ["No", "点検項目", "規格", "方法", "確認頻度", "記録種別", "単位", "判定基準"],
    ...dailyItems.value.map((item) => [
      item.inspection_no || "",
      item.item_name || "",
      item.standard || "",
      item.method || "",
      item.frequency || "",
      recordTypeLabel(item.record_type),
      item.unit || "",
      item.criteria || "",
    ]),
    [],
    [quarterlyTitle.value],
    ["No", "項目", "規格（設定）", "確認方法", "参考値/単位", "確認頻度", "判定基準", "記録種別"],
    ...quarterlyItems.value.map((item) => [
      item.inspection_no || "",
      item.item_name || "",
      item.standard || "",
      item.confirmation_method || "",
      item.method || "",
      item.frequency || "",
      item.criteria || "",
      recordTypeLabel(item.record_type),
    ]),
    ...(buildAttachmentAppendixRows().length ? [[], ["付表"]] : []),
    ...buildAttachmentAppendixRows(),
  ]

  const worksheet = XLSX.utils.aoa_to_sheet(rows)
  worksheet["!cols"] = [
    { wch: 8 },
    { wch: 32 },
    { wch: 28 },
    { wch: 14 },
    { wch: 34 },
    { wch: 12 },
    { wch: 12 },
    { wch: 24 },
  ]
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName || "設備点検表")
  XLSX.writeFile(workbook, `設備点検表_${safeSheetCode}_${safeStatus}_${datePart}.xlsx`)
}

const printCurrentTemplate = () => {
  if (!form.value.items.length) {
    alert("印刷対象の点検項目がありません。")
    return
  }

  const statusText = statusLabel(form.value.status)
  const revisionDate = form.value.revision_date || "-"
  const createdDate = form.value.created_at || form.value.revision_date || "-"
  const effectiveFrom = form.value.effective_from || "-"
  const printedAt = new Date().toLocaleString("ja-JP")
  const approvalNames = resolveApprovalNames()
  const dayNumbers = Array.from({ length: 31 }, (_, idx) => idx + 1)
  const dayHeaderHtml = dayNumbers.map((day) => `<th class="day-head">${day}</th>`).join("")
  const emptyDayCellsHtml = dayNumbers.map(() => '<td class="check-cell"></td>').join("")
  const supervisorCheckCellsHtml = dayNumbers.map(() => '<th class="supervisor-check-cell"></th>').join("")
  const inspectionColgroupHtml = `
    <colgroup>
      <col style="width: 22px;" />
      <col style="width: 170px;" />
      <col style="width: 150px;" />
      <col style="width: 200px;" />
      <col style="width: 46px;" />
      ${dayNumbers.map(() => '<col style="width: 14px;" />').join("")}
    </colgroup>
  `

  const dailyRowsHtml = dailyItems.value
    .map(
      (item) => `
      <tr>
        <td class="no-cell">${escapeHtml(item.inspection_no || "")}</td>
        <td>${toPrintCell(item.item_name)}</td>
        <td>${toPrintCell(item.standard)}</td>
        <td>${toPrintCell(item.method)}</td>
        <td>${toPrintCell(item.frequency)}</td>
        ${emptyDayCellsHtml}
      </tr>
    `
    )
    .join("")

  const quarterlyRowsHtml = quarterlyItems.value
    .map(
      (item) => `
      <tr>
        <td class="no-cell">${escapeHtml(item.inspection_no || "")}</td>
        <td>${toPrintCell(item.item_name)}</td>
        <td>${toPrintCell(item.standard)}</td>
        <td>${toPrintCell(item.confirmation_method)}</td>
        <td>${toPrintCell(item.method)}</td>
        <td></td>
        <td>${toPrintCell(item.criteria)}</td>
      </tr>
    `
    )
    .join("")
  const attachmentAppendixHtml = buildAttachmentPrintHtml()

  const html = `
  <!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <title>設備点検表 PDF出力</title>
      <style>
        @page { size: A4 landscape; margin: 4mm 10mm; }
        body { font-family: "Yu Gothic", "Meiryo", sans-serif; color: #111827; font-size: 9px; margin: 0; }
        .sheet { padding: 0; }
        .header-row { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 2px; }
        .title-row { font-size: 18px; line-height: 1.0; font-weight: 700; letter-spacing: 0.02em; flex: 1; }
        .confirm-wrap { display: inline-flex; align-items: center; gap: 4px; flex-shrink: 0; }
        .confirm-box { font-size: 9px; font-weight: 700; line-height: 1.0; white-space: nowrap; }
        .confirm-sign-box { width: 90px; height: 16px; border: 1px solid #111827; }
        .meta-row { display: flex; flex-wrap: wrap; gap: 6px 10px; margin-bottom: 2px; font-size: 8px; }
        .meta-item { white-space: nowrap; }
        table { width: 100%; border-collapse: collapse; table-layout: fixed; }
        th, td { border: 1px solid #111827; padding: 1px 2px; vertical-align: top; word-break: break-word; }
        thead th { background: #f5f5f5; }
        .inspection-table .no-head, .inspection-table .no-cell { width: 24px; text-align: center; }
        .inspection-table .item-head { width: 200px; }
        .inspection-table .std-head { width: 180px; }
        .inspection-table .method-head { width: 200px; }
        .inspection-table .freq-head { width: 46px; text-align: center; }
        .inspection-table .day-head { width: 2.5px; padding: 0; text-align: center; font-size: 6px; font-weight: 700; }
        .inspection-table .check-cell { width: 2.5px; padding: 0; height: 19px; }
        .inspection-table .supervisor-title-space { border-right: 1px solid #111827; }
        .inspection-table .supervisor-title-cell { text-align: left; font-size: 9px; padding: 0 4px; }
        .inspection-table .supervisor-check-cell { width: 9px; padding: 0; height: 13px; }
        .quarterly-title { margin: 2px 0 1px; font-size: 9px; font-weight: 700; }
        .quarterly-table th, .quarterly-table td { padding: 1px 3px; font-size: 8px; }
        .footer { margin-top: 1px; text-align: right; font-size: 7px; color: #334155; }
        .appendix-page-break { page-break-before: always; }
        .appendix-root { padding: 4px; }
        .appendix-root-title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
        .appendix-section { margin-bottom: 12px; page-break-inside: avoid; }
        .appendix-item-title { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
        .appendix-card { border: 1px solid #cbd5e1; padding: 8px; margin-bottom: 8px; }
        .appendix-card-title { font-size: 11px; font-weight: 700; margin-bottom: 4px; }
        .appendix-image-wrap { margin-bottom: 6px; }
        .appendix-image { max-width: 100%; max-height: 260px; border: 1px solid #cbd5e1; object-fit: contain; }
        .appendix-text-row { margin-bottom: 4px; line-height: 1.5; }
      </style>
    </head>
    <body>
      <div class="sheet">
        <div class="header-row">
          <div class="title-row">${escapeHtml(form.value.title || "設備始業点検表")}</div>
          <div class="confirm-wrap">
            <div class="confirm-box">月度確認</div>
            <div class="confirm-sign-box"></div>
          </div>
        </div>
        <div class="meta-row">
          <div class="meta-item">作成日: ${escapeHtml(createdDate)}</div>
          <div class="meta-item">設備コード: ${escapeHtml(form.value.sheet_code || "-")}</div>
          <div class="meta-item">設備名: ${escapeHtml(form.value.sheet_name || "-")}</div>
          <div class="meta-item">版: ${escapeHtml(form.value.version || "-")}</div>
          <div class="meta-item">状態: ${escapeHtml(statusText)}</div>
          <div class="meta-item">出力日時: ${escapeHtml(printedAt)}</div>
          <div class="meta-item">改訂日: ${escapeHtml(revisionDate)}</div>
          <div class="meta-item">作成者: ${escapeHtml(form.value.created_by_name || "-")}</div>
          <div class="meta-item">班長: ${escapeHtml(approvalNames.supervisor)}</div>
          <div class="meta-item">係長: ${escapeHtml(approvalNames.chief)}</div>
          <div class="meta-item">部長: ${escapeHtml(approvalNames.manager)}</div>
          <div class="meta-item">運用開始日: ${escapeHtml(effectiveFrom)}</div>
        </div>

        <table class="inspection-table">
          ${inspectionColgroupHtml}
          <thead>
            <tr>
              <th class="supervisor-title-space" colspan="5"></th>
              <th class="supervisor-title-cell" colspan="31">監督者確認</th>
            </tr>
            <tr>
              <th class="supervisor-title-space" colspan="5"></th>
              ${supervisorCheckCellsHtml}
            </tr>
            <tr>
              <th class="no-head">No</th>
              <th class="item-head">点検項目</th>
              <th class="std-head">規格</th>
              <th class="method-head">方法</th>
              <th class="freq-head">確認頻度</th>
              ${dayHeaderHtml}
            </tr>
          </thead>
          <tbody>
            ${dailyRowsHtml || '<tr><td colspan="36">データなし</td></tr>'}
          </tbody>
        </table>

        <div class="quarterly-title">${escapeHtml(quarterlyTitle.value)}</div>
        <table class="quarterly-table">
          <thead>
            <tr>
              <th>No</th>
              <th>項目</th>
              <th>設定・規格</th>
              <th>確認方法</th>
              <th>参考値</th>
              <th>実測値</th>
              <th>判定基準</th>
            </tr>
          </thead>
          <tbody>
            ${quarterlyRowsHtml || '<tr><td colspan="7">データなし</td></tr>'}
          </tbody>
        </table>
        <div class="footer">PM 設備点検表</div>
      </div>
      ${attachmentAppendixHtml}
    </body>
  </html>
  `

  const printWindow = window.open("", "_blank")
  if (!printWindow) {
    alert("ポップアップがブロックされました。許可して再実行してください。")
    return
  }

  printWindow.document.open()
  printWindow.document.write(html)
  printWindow.document.close()
  printWindow.focus()
  setTimeout(() => {
    printWindow.print()
  }, 200)
}

const formatDateTime = (value) => {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("ja-JP")
}

const formatDate = (value) => {
  if (!value) return ""
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString("ja-JP")
}

const resizeTextarea = (eventOrElement) => {
  const element = eventOrElement?.target || eventOrElement
  if (!(element instanceof HTMLTextAreaElement)) return
  element.style.height = "auto"
  element.style.height = `${element.scrollHeight}px`
}

const resizeAllTextareas = async () => {
  await nextTick()
  const textareas = document.querySelectorAll(".inspection-master textarea.auto-grow-textarea")
  textareas.forEach((textarea) => {
    resizeTextarea(textarea)
  })
}

const findEquipmentByCode = (code) => {
  const target = String(code || "").trim()
  if (!target) return null
  return (
    equipmentOptions.value.find((item) => String(item.equipment_code || "").trim() === target) || null
  )
}

const applyEquipmentToForm = (code) => {
  const equipment = findEquipmentByCode(code)
  if (!equipment) return
  form.value.sheet_name = String(equipment.equipment_name || form.value.sheet_name || "")
  form.value.source_sheet_name = String(equipment.equipment_code || form.value.source_sheet_name || "")
  // タイトルが未入力のときだけ自動生成
  if (!form.value.title.trim()) {
    form.value.title = `設備始業点検表（${equipment.equipment_code}：${equipment.equipment_name}）`
  }
}

const handleSheetCodeChange = () => {
  applyEquipmentToForm(form.value.sheet_code)
}

const createLocalKey = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`

const createAttachment = (raw = {}) => ({
  local_key: raw.local_key || createLocalKey(),
  id: raw.id || null,
  display_order: Number(raw.display_order || 1),
  title: raw.title || "",
  description: raw.description || "",
  check_point: raw.check_point || "",
  ok_example: raw.ok_example || "",
  ng_example: raw.ng_example || "",
  image_url: raw.image_url || "",
})

const attachmentTargetItem = computed(() => {
  return form.value.items.find((item) => item.local_key === attachmentTargetKey.value) || null
})

const attachmentCountLabel = (item) => {
  return Array.isArray(item?.attachments) ? item.attachments.length : 0
}

const dailyItems = computed(() =>
  [...form.value.items]
    .filter((item) => item.section_type === "DAILY")
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
)

const quarterlyItems = computed(() =>
  [...form.value.items]
    .filter((item) => item.section_type === "QUARTERLY")
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
)

const WEEKDAY_OPTIONS = [
  { value: "月", label: "月" },
  { value: "火", label: "火" },
  { value: "水", label: "水" },
  { value: "木", label: "木" },
  { value: "金", label: "金" },
  { value: "土", label: "土" },
  { value: "週末", label: "週末" },
  { value: "週初め", label: "週初め" },
]

const quarterlyTitle = computed(() => {
  const schedType = form.value.measurement_schedule_type
  if (schedType === "WEEKDAY") {
    const days = form.value.measurement_weekdays
    if (!days || days.length === 0) return "定期実測項目"
    const formatted = days.map((d) => ["週末", "週初め"].includes(d) ? d : `毎週${d}曜日`)
    return `定期実測項目（${formatted.join("・")}）`
  }
  const months = form.value.measurement_months
  if (!months || months.length === 0) return "定期実測項目"
  return `定期実測項目（${months.map((m) => `${m}月`).join("・")}）`
})

const toggleMeasurementMonth = (month) => {
  const idx = form.value.measurement_months.indexOf(month)
  if (idx >= 0) {
    form.value.measurement_months.splice(idx, 1)
  } else {
    form.value.measurement_months.push(month)
    form.value.measurement_months.sort((a, b) => a - b)
  }
}

const toggleMeasurementWeekday = (day) => {
  const idx = form.value.measurement_weekdays.indexOf(day)
  if (idx >= 0) {
    form.value.measurement_weekdays.splice(idx, 1)
  } else {
    form.value.measurement_weekdays.push(day)
  }
}

const resequenceSection = (sectionType) => {
  const targetItems = form.value.items
    .filter((item) => item.section_type === sectionType)
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0))
  targetItems.forEach((item, index) => {
    item.display_order = index + 1
  })
}

const addItem = (sectionType) => {
  const nextOrder =
    Math.max(
      0,
      ...form.value.items
        .filter((item) => item.section_type === sectionType)
        .map((item) => Number(item.display_order || 0))
    ) + 1

  form.value.items.push({
    local_key: createLocalKey(),
    section_type: sectionType,
    display_order: nextOrder,
    inspection_no: nextOrder,
    item_name: "",
    standard: "",
    frequency: sectionType === "DAILY" ? "始業時" : "3ヶ月/1回",
    method: "",
    confirmation_method: "",
    record_type: "CHECK",
    unit: "",
    criteria: "",
    is_required: true,
    is_active: true,
    attachments: [],
  })
  resizeAllTextareas()
}

const removeItem = (targetItem) => {
  form.value.items = form.value.items.filter((item) => item.local_key !== targetItem.local_key)
  resequenceSection(targetItem.section_type)
  resizeAllTextareas()
}

const resequenceAttachments = (item) => {
  if (!item || !Array.isArray(item.attachments)) return
  item.attachments.forEach((attachment, index) => {
    attachment.display_order = index + 1
  })
}

const openAttachmentDialog = (item) => {
  if (!Array.isArray(item.attachments)) {
    item.attachments = []
  }
  resequenceAttachments(item)
  attachmentTargetKey.value = item.local_key
  attachmentDialogVisible.value = true
}

const closeAttachmentDialog = () => {
  attachmentDialogVisible.value = false
  attachmentTargetKey.value = ""
}

const addAttachment = () => {
  if (!attachmentTargetItem.value) return
  if (!Array.isArray(attachmentTargetItem.value.attachments)) {
    attachmentTargetItem.value.attachments = []
  }
  attachmentTargetItem.value.attachments.push(
    createAttachment({ display_order: attachmentTargetItem.value.attachments.length + 1 })
  )
}

const removeAttachment = (targetAttachment) => {
  if (!attachmentTargetItem.value) return
  attachmentTargetItem.value.attachments = attachmentTargetItem.value.attachments.filter(
    (attachment) => attachment.local_key !== targetAttachment.local_key
  )
  resequenceAttachments(attachmentTargetItem.value)
}

const uploadAttachmentImage = async (event, attachment) => {
  const file = event?.target?.files?.[0]
  if (!file) return
  try {
    const formData = new FormData()
    formData.append("file", file)
    const response = await api.qualityEquipmentInspections.uploadAttachmentImage(formData)
    attachment.image_url = response.data?.image_url || ""
    alert("付表画像をアップロードしました。")
  } catch (error) {
    console.error("付表画像アップロードに失敗:", error)
    alert("付表画像のアップロードに失敗しました。")
  } finally {
    if (event?.target) {
      event.target.value = ""
    }
  }
}

const normalizeImportHeader = (value) => {
  return String(value || "")
    .normalize("NFKC")
    .replace(/\s+/g, "")
    .replace(/[()（）]/g, "")
    .trim()
}

const normalizeRecordTypeFromExcel = (value) => {
  const text = String(value || "").trim()
  if (!text) return "CHECK"
  if ((text.includes("写真") && text.includes("数")) || text.includes("PHOTO_NUMERIC")) return "PHOTO_NUMERIC"
  if ((text.includes("写真") && text.includes("のみ")) || text.includes("PHOTO")) return "PHOTO"
  if (text.includes("数")) return "NUMERIC"
  if (text.includes("文") || text.includes("テキスト")) return "TEXT"
  if (text.includes("CHECK") || text.includes("チェック")) return "CHECK"
  return "CHECK"
}

const normalizeBooleanFromExcel = (value, defaultValue = true) => {
  const text = String(value || "").trim().toLowerCase()
  if (!text) return defaultValue
  if (["false", "0", "off", "no", "無効", "いいえ"].includes(text)) return false
  if (["true", "1", "on", "yes", "有効", "はい"].includes(text)) return true
  return defaultValue
}

const normalizeExcelDateString = (value) => {
  const text = String(value || "").trim()
  if (!text) return ""
  const m = text.match(/^(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})/)
  if (!m) return text
  const y = m[1]
  const month = String(m[2]).padStart(2, "0")
  const day = String(m[3]).padStart(2, "0")
  return `${y}-${month}-${day}`
}

const rowToJoinedText = (row) =>
  (Array.isArray(row) ? row : [])
    .map((cell) => String(cell || "").trim())
    .filter(Boolean)
    .join(" ")

const buildImportHeaderMap = (headerRow) => {
  const map = {}
  ;(Array.isArray(headerRow) ? headerRow : []).forEach((cell, index) => {
    const key = normalizeImportHeader(cell)
    const lower = key.toLowerCase()
    const normalizedNo = lower.replace(/[.\-_:。．]/g, "")
    if (!key) return
    if (["no", "番号"].includes(normalizedNo) || key === "No") map.inspection_no = index
    if (key.includes("点検項目") || key === "項目") map.item_name = index
    if (key.includes("規格") || key.includes("設定")) map.standard = index
    if (key.includes("確認頻度")) map.frequency = index
    if (key.includes("確認方法")) map.confirmation_method = index
    else if (key.includes("方法") || key.includes("参考値単位") || key.includes("参考値")) map.method = index
    if (key.includes("記録種別")) map.record_type = index
    if (key === "単位") map.unit = index
    if (key.includes("判定基準")) map.criteria = index
    if (key.includes("必須")) map.is_required = index
    if (key === "有効") map.is_active = index
  })
  return map
}

const parseInspectionNoValue = (value) => {
  const text = String(value || "").trim()
  if (!text) return null
  const matched = text.match(/\d+/)
  if (!matched) return null
  const num = Number(matched[0])
  return Number.isFinite(num) ? num : null
}

const findHeaderRowIndex = (rows, sectionType) => {
  const normalizedRows = Array.isArray(rows) ? rows : []
  for (let i = 0; i < normalizedRows.length; i += 1) {
    const headerMap = buildImportHeaderMap(normalizedRows[i] || [])
    const hasItemName = Number.isInteger(headerMap.item_name)
    const hasSectionSpecificKey =
      sectionType === "DAILY"
        ? Number.isInteger(headerMap.inspection_no) || Number.isInteger(headerMap.frequency)
        : Number.isInteger(headerMap.standard) || Number.isInteger(headerMap.method)
    if (hasItemName && hasSectionSpecificKey) return i
  }
  return -1
}

const isSectionBreakRow = (rowText) => {
  return (
    rowText.includes("日次点検項目") ||
    rowText.includes("定期実測項目") ||
    rowText.includes("3ヶ月/1回実測確認") ||
    rowText.includes("3ヶ月1回実測確認") ||
    rowText.includes("ワークフロー履歴") ||
    rowText.includes("異常時記入") ||
    rowText.includes("特記事項") ||
    rowText.includes("付表")
  )
}

const parseImportedRows = (rows, sectionType, defaults = {}) => {
  const normalizedRows = Array.isArray(rows) ? rows : []
  const sectionItems = []
  if (!normalizedRows.length) return sectionItems

  const headerIndex = findHeaderRowIndex(normalizedRows, sectionType)
  if (headerIndex < 0) return sectionItems

  const headerMap = buildImportHeaderMap(normalizedRows[headerIndex] || [])
  for (let i = headerIndex + 1; i < normalizedRows.length; i += 1) {
    const row = normalizedRows[i] || []
    const rowText = rowToJoinedText(row)
    if (!rowText) continue
    if (isSectionBreakRow(rowText)) break

    const itemName = String(row[headerMap.item_name] || "").trim()
    const inspectionNoRaw =
      Number.isInteger(headerMap.inspection_no) && headerMap.inspection_no >= 0
        ? String(row[headerMap.inspection_no] || "").trim()
        : ""
    const inspectionNoNum = parseInspectionNoValue(inspectionNoRaw)
    const hasInspectionNo = sectionType !== "DAILY" || inspectionNoNum !== null
    if (!itemName) {
      // 旧帳票で改行が次行に分割される場合、直前行へ連結する
      const prev = sectionItems[sectionItems.length - 1]
      if (!prev) continue
      const standardCont = String(row[headerMap.standard] || "").trim()
      const frequencyCont = String(row[headerMap.frequency] || "").trim()
      const methodCont = String(row[headerMap.method] || "").trim()
      const unitCont = String(row[headerMap.unit] || "").trim()
      const criteriaCont = String(row[headerMap.criteria] || "").trim()
      if (standardCont) prev.standard = prev.standard ? `${prev.standard}\n${standardCont}` : standardCont
      if (frequencyCont) prev.frequency = prev.frequency ? `${prev.frequency}\n${frequencyCont}` : frequencyCont
      if (methodCont) prev.method = prev.method ? `${prev.method}\n${methodCont}` : methodCont
      if (unitCont) prev.unit = prev.unit ? `${prev.unit}\n${unitCont}` : unitCont
      if (criteriaCont) prev.criteria = prev.criteria ? `${prev.criteria}\n${criteriaCont}` : criteriaCont
      continue
    }

    // 日次でNoが空の行は「前行の続き（セル内改行が行分割されたケース）」として扱う
    if (sectionType === "DAILY" && !hasInspectionNo) {
      const prev = sectionItems[sectionItems.length - 1]
      if (!prev) continue
      const standardCont = String(row[headerMap.standard] || "").trim()
      const frequencyCont = String(row[headerMap.frequency] || "").trim()
      const methodCont = String(row[headerMap.method] || "").trim()
      const unitCont = String(row[headerMap.unit] || "").trim()
      const criteriaCont = String(row[headerMap.criteria] || "").trim()
      prev.item_name = prev.item_name ? `${prev.item_name}\n${itemName}` : itemName
      if (standardCont) prev.standard = prev.standard ? `${prev.standard}\n${standardCont}` : standardCont
      if (frequencyCont) prev.frequency = prev.frequency ? `${prev.frequency}\n${frequencyCont}` : frequencyCont
      if (methodCont) prev.method = prev.method ? `${prev.method}\n${methodCont}` : methodCont
      if (unitCont) prev.unit = prev.unit ? `${prev.unit}\n${unitCont}` : unitCont
      if (criteriaCont) prev.criteria = prev.criteria ? `${prev.criteria}\n${criteriaCont}` : criteriaCont
      continue
    }
    if (normalizeImportHeader(itemName).includes("点検項目")) continue

    sectionItems.push({
      local_key: createLocalKey(),
      section_type: sectionType,
      display_order: sectionItems.length + 1,
      inspection_no: inspectionNoNum || sectionItems.length + 1,
      item_name: itemName,
      standard: String(row[headerMap.standard] || "").trim(),
      frequency:
        sectionType === "DAILY"
          ? String(row[headerMap.frequency] || defaults.frequency || "始業時").trim()
          : String(row[headerMap.frequency] || defaults.frequency || "3ヶ月/1回").trim(),
      method: String(row[headerMap.method] || "").trim(),
      confirmation_method: String(row[headerMap.confirmation_method] || "").trim(),
      record_type: normalizeRecordTypeFromExcel(row[headerMap.record_type]),
      unit: String(row[headerMap.unit] || "").trim(),
      criteria: String(row[headerMap.criteria] || "").trim(),
      is_required: normalizeBooleanFromExcel(row[headerMap.is_required], true),
      is_active: normalizeBooleanFromExcel(row[headerMap.is_active], true),
      attachments: [],
    })
  }
  return sectionItems
}

const splitTemplateRowsBySection = (rows) => {
  const normalizedRows = Array.isArray(rows) ? rows : []
  const result = {
    dailyRows: [],
    quarterlyRows: [],
    metaRows: [],
  }

  let dailyStart = -1
  let quarterlyStart = -1
  for (let i = 0; i < normalizedRows.length; i += 1) {
    const row = normalizedRows[i] || []
    const rowText = rowToJoinedText(row)
    const headerMap = buildImportHeaderMap(row)
    if (
      dailyStart < 0 &&
      (rowText.includes("日次点検項目") || (Number.isInteger(headerMap.item_name) && Number.isInteger(headerMap.inspection_no)))
    ) {
      dailyStart = i
    }
    if (
      quarterlyStart < 0 &&
      (rowText.includes("定期実測項目") ||
        rowText.includes("3ヶ月/1回実測確認") ||
        rowText.includes("3ヶ月1回実測確認"))
    ) {
      quarterlyStart = i
    }
  }

  // タイトル行が無いExcel向け: 日次表の後にある「No列なし」の項目ヘッダを定期実測として扱う
  if (dailyStart > -1 && quarterlyStart < 0) {
    for (let i = dailyStart + 1; i < normalizedRows.length; i += 1) {
      const headerMap = buildImportHeaderMap(normalizedRows[i] || [])
      if (Number.isInteger(headerMap.item_name) && !Number.isInteger(headerMap.inspection_no)) {
        quarterlyStart = i
        break
      }
    }
  }

  const metaEnd = [dailyStart, quarterlyStart].filter((idx) => idx > -1).sort((a, b) => a - b)[0]
  result.metaRows = normalizedRows.slice(0, Number.isInteger(metaEnd) ? metaEnd : normalizedRows.length)
  if (dailyStart > -1) {
    const dailyEnd = quarterlyStart > -1 ? quarterlyStart : normalizedRows.length
    result.dailyRows = normalizedRows.slice(dailyStart, dailyEnd)
  }
  if (quarterlyStart > -1) {
    let quarterlyEnd = normalizedRows.length
    for (let i = quarterlyStart + 1; i < normalizedRows.length; i += 1) {
      const rowText = rowToJoinedText(normalizedRows[i] || [])
      if (rowText.includes("付表")) {
        quarterlyEnd = i
        break
      }
    }
    result.quarterlyRows = normalizedRows.slice(quarterlyStart, quarterlyEnd)
  }
  return result
}

const collectDailyRowsFallback = (rows, startIndex, endIndex) => {
  if (startIndex < 0) return []
  const collected = []
  for (let i = startIndex; i < endIndex; i += 1) {
    const row = rows[i] || []
    const rowText = rowToJoinedText(row)
    if (!rowText) continue
    if (rowText.includes("異常時記入") || rowText.includes("特記事項")) break
    collected.push(row)
  }
  return collected
}

const collectQuarterlyRowsFallback = (rows, startIndex) => {
  if (startIndex < 0) return []
  const collected = []
  for (let i = startIndex; i < rows.length; i += 1) {
    const row = rows[i] || []
    const rowText = rowToJoinedText(row)
    if (!rowText) continue
    if (rowText.includes("ワークフロー履歴") || rowText.includes("付表")) break
    collected.push(row)
  }
  return collected
}

const extractMetaFromImportedRows = (metaRows) => {
  const metadata = {}
  const rows = Array.isArray(metaRows) ? metaRows : []
  rows.forEach((row) => {
    const key = String(row?.[0] || "").trim()
    const value = String(row?.[1] || "").trim()
    if (!key) return
    if (key === "設備コード") metadata.sheet_code = value
    if (key === "設備名") metadata.sheet_name = value
    if (key === "帳票タイトル") metadata.title = value
    if (key === "元シート名") metadata.source_sheet_name = value
    if (key === "改訂日") metadata.revision_date = normalizeExcelDateString(value)
    if (key === "改訂内容") metadata.revision_notes = value
    if (key === "運用開始日") metadata.effective_from = normalizeExcelDateString(value)
    if (key === "版") metadata.version = Number(value || 1) || 1
  })

  if (!metadata.title) {
    const firstCell = String(rows?.[0]?.[0] || "").trim()
    if (firstCell) metadata.title = firstCell
  }
  return metadata
}

const getSheetRows = (workbook, sheetName) => {
  const sheet = workbook?.Sheets?.[sheetName]
  if (!sheet) return []
  return XLSX.utils.sheet_to_json(sheet, {
    header: 1,
    defval: "",
    raw: false,
    blankrows: false,
  })
}

const scoreSheetRows = (rows) => {
  const normalizedRows = Array.isArray(rows) ? rows : []
  let score = 0
  normalizedRows.forEach((row) => {
    const rowText = rowToJoinedText(row)
    if (!rowText) return
    if (rowText.includes("設備点検") || rowText.includes("点検表")) score += 1
    if (rowText.includes("日次点検項目")) score += 3
    if (rowText.includes("定期実測項目")) score += 3
    if (rowText.includes("点検項目") && rowText.includes("規格")) score += 2
  })
  return score
}

const selectBestSheetName = (workbook) => {
  const names = Array.isArray(workbook?.SheetNames) ? workbook.SheetNames : []
  if (!names.length) return ""
  const preferred = names.find((name) => String(name || "").toUpperCase().includes("SM-"))
  if (preferred) return preferred

  let bestName = names[0]
  let bestScore = -1
  names.forEach((name) => {
    const score = scoreSheetRows(getSheetRows(workbook, name))
    if (score > bestScore) {
      bestScore = score
      bestName = name
    }
  })
  return bestName
}

const readTemplateItemsFromExcel = async (file) => {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: "array", cellDates: true })
  const sheetName = selectBestSheetName(workbook)
  if (!sheetName) {
    throw new Error("シートが存在しません。")
  }
  const rows = getSheetRows(workbook, sheetName)

  const { dailyRows, quarterlyRows, metaRows } = splitTemplateRowsBySection(rows)
  let importedDailyItems = parseImportedRows(dailyRows, "DAILY", { frequency: "始業時" })
  let importedQuarterlyItems = parseImportedRows(quarterlyRows, "QUARTERLY", { frequency: "3ヶ月/1回" })

  // SM-010 など旧帳票向けフォールバック: 全シートから日次/定期の表を再抽出
  if (!importedDailyItems.length || !importedQuarterlyItems.length) {
    const dailyHeaderIndex = findHeaderRowIndex(rows, "DAILY")
    const quarterlySectionIndex = rows.findIndex((row) => {
      const text = rowToJoinedText(row)
      return (
        text.includes("定期実測項目") ||
        text.includes("3ヶ月/1回実測確認") ||
        text.includes("3ヶ月1回実測確認")
      )
    })
    const dailyFallbackRows = collectDailyRowsFallback(
      rows,
      Math.max(0, dailyHeaderIndex),
      quarterlySectionIndex > -1 ? quarterlySectionIndex : rows.length
    )
    const quarterlyHeaderIndexInAll = findHeaderRowIndex(
      rows.slice(Math.max(0, quarterlySectionIndex), rows.length),
      "QUARTERLY"
    )
    const quarterlyHeaderAbsolute =
      quarterlySectionIndex > -1 && quarterlyHeaderIndexInAll > -1
        ? quarterlySectionIndex + quarterlyHeaderIndexInAll
        : findHeaderRowIndex(rows, "QUARTERLY")
    const quarterlyFallbackRows = collectQuarterlyRowsFallback(rows, Math.max(0, quarterlyHeaderAbsolute))

    if (!importedDailyItems.length) {
      importedDailyItems = parseImportedRows(dailyFallbackRows, "DAILY", { frequency: "始業時" })
    }
    if (!importedQuarterlyItems.length) {
      importedQuarterlyItems = parseImportedRows(quarterlyFallbackRows, "QUARTERLY", { frequency: "3ヶ月/1回" })
    }
  }

  const importedItems = [...importedDailyItems, ...importedQuarterlyItems]
  if (!importedItems.length) {
    throw new Error(`点検項目が見つかりません（シート: ${sheetName}）。`)
  }
  const metadata = extractMetaFromImportedRows(metaRows)
  return { metadata, importedItems }
}

const applyImportedTemplateData = ({ metadata, importedItems }) => {
  if (metadata.sheet_code) form.value.sheet_code = metadata.sheet_code
  if (metadata.sheet_name) form.value.sheet_name = metadata.sheet_name
  if (metadata.title) form.value.title = metadata.title
  if (metadata.source_sheet_name) form.value.source_sheet_name = metadata.source_sheet_name
  if (metadata.revision_date) form.value.revision_date = metadata.revision_date
  if (metadata.revision_notes) form.value.revision_notes = metadata.revision_notes
  if (metadata.effective_from) form.value.effective_from = metadata.effective_from
  if (metadata.version) form.value.version = Number(metadata.version || 1) || 1
  form.value.items = importedItems
}

const openOperationExcelPicker = () => {
  operationExcelInput.value?.click()
}

const onOperationExcelFileChange = async (event) => {
  const file = event?.target?.files?.[0]
  if (!file) return

  if (form.value.items.length > 0) {
    const ok = window.confirm("現在の項目を運用中Excelの内容で上書きします。よろしいですか？")
    if (!ok) {
      if (event?.target) event.target.value = ""
      return
    }
  }

  excelImportLoading.value = true
  try {
    const importedData = await readTemplateItemsFromExcel(file)
    applyImportedTemplateData(importedData)
    await resizeAllTextareas()
    alert(`Excelを読み込みました。${importedData.importedItems.length}件の点検項目を反映しました。`)
  } catch (error) {
    console.error("設備点検表Excel読込に失敗:", error)
    alert(`Excel読込に失敗しました。${error?.message || "既存の設備点検表Excel形式か確認してください。"}`)
  } finally {
    excelImportLoading.value = false
    if (event?.target) event.target.value = ""
  }
}

const toFormModel = (raw) => {
  return {
    id: raw.id,
    sheet_code: raw.sheet_code || "",
    sheet_name: raw.sheet_name || "",
    title: raw.title || "",
    source_sheet_name: raw.source_sheet_name || "",
    created_at: raw.created_at || "",
    revision_date: raw.revision_date || "",
    revision_notes: raw.revision_notes || "",
    effective_from: raw.effective_from || "",
    version: Number(raw.version || 1),
    status: normalizeStatus(raw.status) || "DRAFT",
    is_active: Boolean(raw.is_active),
    created_by: raw.created_by || null,
    created_by_name: raw.created_by_name || "",
    reviewer_user: raw.reviewer_user || null,
    reviewer_user_name: raw.reviewer_user_name || "",
    chief_user: raw.chief_user || null,
    chief_user_name: raw.chief_user_name || "",
    approver_user: raw.approver_user || null,
    approver_user_name: raw.approver_user_name || "",
    rejection_comment: raw.rejection_comment || "",
    submitted_items_snapshot: Array.isArray(raw.submitted_items_snapshot) ? raw.submitted_items_snapshot : null,
    measurement_months: Array.isArray(raw.measurement_months) ? raw.measurement_months : [],
    measurement_schedule_type: raw.measurement_schedule_type || "MONTHLY",
    measurement_weekdays: Array.isArray(raw.measurement_weekdays) ? raw.measurement_weekdays : [],
    reviewed_at: raw.reviewed_at || "",
    chief_reviewed_at: raw.chief_reviewed_at || "",
    approved_at: raw.approved_at || "",
    processes: Array.isArray(raw.processes) ? raw.processes : [],
    lines: Array.isArray(raw.lines) ? raw.lines : [],
    workflow_logs: Array.isArray(raw.workflow_logs) ? raw.workflow_logs : [],
    items: Array.isArray(raw.items)
      ? raw.items.map((item) => ({
          local_key: createLocalKey(),
          id: item.id || null,
          section_type: item.section_type || "DAILY",
          display_order: Number(item.display_order || 1),
          inspection_no: item.inspection_no ?? null,
          item_name: item.item_name || "",
          standard: item.standard || "",
          frequency: item.frequency || "",
          method: item.method || "",
          confirmation_method: item.confirmation_method || "",
          record_type: item.record_type || "CHECK",
          unit: item.unit || "",
          criteria: item.criteria || "",
          is_required: Boolean(item.is_required),
          is_active: Boolean(item.is_active),
          attachments: Array.isArray(item.attachments)
            ? item.attachments.map((attachment) =>
                createAttachment({
                  id: attachment.id || null,
                  display_order: Number(attachment.display_order || 1),
                  title: attachment.title || "",
                  description: attachment.description || "",
                  check_point: attachment.check_point || "",
                  ok_example: attachment.ok_example || "",
                  ng_example: attachment.ng_example || "",
                  image_url: attachment.image_url || "",
                })
              )
            : [],
        }))
      : [],
  }
}

const buildPayload = () => {
  const normalizedItems = form.value.items
    .filter((item) => String(item.item_name || "").trim())
    .map((item) => ({
      section_type: item.section_type,
      display_order: Number(item.display_order || 1),
      inspection_no: Number(item.inspection_no || 0) || null,
      item_name: String(item.item_name || "").trim(),
      standard: String(item.standard || "").trim(),
      frequency: String(item.frequency || "").trim(),
      method: String(item.method || "").trim(),
      confirmation_method: String(item.confirmation_method || "").trim(),
      record_type: item.record_type || "CHECK",
      unit: String(item.unit || "").trim(),
      criteria: String(item.criteria || "").trim(),
      is_required: Boolean(item.is_required),
      is_active: Boolean(item.is_active),
      attachments: Array.isArray(item.attachments)
        ? item.attachments.map((attachment, index) => ({
            display_order: Number(attachment.display_order || index + 1),
            title: String(attachment.title || "").trim(),
            description: String(attachment.description || "").trim(),
            check_point: String(attachment.check_point || "").trim(),
            ok_example: String(attachment.ok_example || "").trim(),
            ng_example: String(attachment.ng_example || "").trim(),
            image_url: String(attachment.image_url || "").trim(),
          }))
        : [],
    }))

  return {
    sheet_code: String(form.value.sheet_code || "").trim(),
    sheet_name: String(form.value.sheet_name || "").trim(),
    title: String(form.value.title || "").trim(),
    source_sheet_name: String(form.value.source_sheet_name || "").trim(),
    revision_date: form.value.revision_date || null,
    revision_notes: String(form.value.revision_notes || ""),
    effective_from: form.value.effective_from || null,
    version: Number(form.value.version || 1),
    is_active: Boolean(form.value.is_active),
    processes: Array.isArray(form.value.processes) ? form.value.processes.map(Number) : [],
    lines: Array.isArray(form.value.lines) ? form.value.lines.map(Number) : [],
    measurement_months: Array.isArray(form.value.measurement_months) ? form.value.measurement_months : [],
    measurement_schedule_type: form.value.measurement_schedule_type || "MONTHLY",
    measurement_weekdays: Array.isArray(form.value.measurement_weekdays) ? form.value.measurement_weekdays : [],
    items: normalizedItems,
  }
}

const loadEquipmentOptions = async () => {
  equipmentLoading.value = true
  try {
    const response = await api.equipments.getEquipments({
      is_active: true,
      ordering: "display_order,equipment_code",
    })
    equipmentOptions.value = response.data?.results || response.data || []
  } catch (error) {
    console.error("設備マスタ取得に失敗:", error)
    equipmentOptions.value = []
  } finally {
    equipmentLoading.value = false
  }
}

const loadProcessAndLineOptions = async () => {
  try {
    const [procRes, lineRes] = await Promise.all([
      api.processes.getProcesses({ is_active: true }),
      api.lines.getLines({ line_type: 'PROD', is_active: true }),
    ])
    processOptions.value = procRes.data?.results || procRes.data || []
    lineOptions.value = lineRes.data?.results || lineRes.data || []
  } catch (error) {
    console.error("工程/ライン取得に失敗:", error)
  }
}

const loadUnitOptions = async () => {
  try {
    const [unitRes, mappingRes] = await Promise.all([
      api.accounts.getUnits({ page_size: 20000 }),
      api.accounts.getUnitLineMappings({ page_size: 20000 }),
    ])
    unitOptions.value = Array.isArray(unitRes.data) ? unitRes.data : (unitRes.data?.results || [])
    unitLineMappings.value = Array.isArray(mappingRes.data) ? mappingRes.data : (mappingRes.data?.results || [])
  } catch (error) {
    console.error("グループ取得に失敗:", error)
  }
}

const loadTemplateList = async () => {
  if (!canView.value) return
  loadingList.value = true
  try {
    const response = await api.qualityEquipmentInspections.list()
    templates.value = response.data?.results || response.data || []
  } catch (error) {
    console.error("設備点検テンプレート一覧取得に失敗:", error)
    alert("テンプレート一覧の取得に失敗しました。")
  } finally {
    loadingList.value = false
  }
}

const loadPrevVersion = async (sheetCode, version) => {
  prevVersionItems.value = []
  if (!sheetCode || version <= 1) return
  try {
    const response = await api.qualityEquipmentInspections.list({
      sheet_code: sheetCode,
      version: version - 1,
    })
    const results = response.data?.results || response.data || []
    if (results.length > 0) {
      prevVersionItems.value = results[0].items || []
    }
  } catch (error) {
    console.error("前版テンプレート取得に失敗:", error)
  }
}

const loadTemplateDetail = async (id) => {
  if (!id) return
  detailLoading.value = true
  try {
    const response = await api.qualityEquipmentInspections.get(id)
    form.value = toFormModel(response.data)
    selectedTemplateId.value = id
    await resizeAllTextareas()
    await loadPrevVersion(form.value.sheet_code, form.value.version)
    markSavedSnapshot()
  } catch (error) {
    console.error("設備点検テンプレート詳細取得に失敗:", error)
    alert("テンプレート詳細の取得に失敗しました。")
  } finally {
    detailLoading.value = false
  }
}

const selectTemplate = async (id) => {
  const numericId = Number(id || 0)
  if (!numericId || numericId === Number(selectedTemplateId.value || 0)) return
  if (!confirmDiscardUnsavedChanges()) return
  await router.replace({
    path: route.path,
    query: { ...route.query, id: String(numericId) },
  })
  await loadTemplateDetail(numericId)
}

const copyTemplate = async () => {
  if (!confirmDiscardUnsavedChanges()) return
  if (!form.value.id) return
  const src = JSON.parse(JSON.stringify(form.value))
  if (route.query.id) {
    await router.replace({ path: route.path, query: {} })
  }
  form.value = {
    ...src,
    id: null,
    sheet_code: '',
    sheet_name: '',
    status: 'DRAFT',
    version: 1,
    is_active: true,
    rejection_comment: '',
    created_at: '',
    created_by: null,
    created_by_name: '',
    reviewer_user_name: '',
    chief_user_name: '',
    approver_user_name: '',
    reviewed_at: '',
    chief_reviewed_at: '',
    approved_at: '',
    workflow_logs: [],
    items: src.items.map((item) => ({
      ...item,
      id: null,
      local_key: createLocalKey(),
      attachments: (item.attachments || []).map((att) => ({
        ...att,
        id: null,
        local_key: createLocalKey(),
      })),
    })),
  }
  selectedTemplateId.value = null
  isListHidden.value = true
  prevVersionItems.value = []
  await nextTick()
  resizeAllTextareas()
  markSavedSnapshot()
}

const startNewTemplate = async () => {
  if (!confirmDiscardUnsavedChanges()) return
  if (route.query.id) {
    await router.replace({ path: route.path, query: {} })
  }
  isListHidden.value = true
  selectedTemplateId.value = null
  form.value = createEmptyForm()
  prevVersionItems.value = []
  resizeAllTextareas()
  markSavedSnapshot()
}

const toggleTemplateList = () => {
  isListHidden.value = !isListHidden.value
}

// フォームバリデーション（保存前チェック）
const validateForm = () => {
  if (!form.value.sheet_code) {
    alert("設備コードは必須です。")
    return false
  }
  if (!form.value.sheet_name) {
    alert("設備名は必須です。")
    return false
  }
  if (!form.value.title) {
    alert("帳票タイトルは必須です。")
    return false
  }
  if (!form.value.revision_date) {
    alert("改訂日は必須です。")
    return false
  }
  if (!form.value.effective_from) {
    alert("運用開始日は必須です。")
    return false
  }
  if (!String(form.value.revision_notes || "").trim()) {
    alert("改訂内容は必須です。")
    return false
  }
  if (!form.value.version) {
    alert("版は必須です。")
    return false
  }
  if (!form.value.items.length) {
    alert("点検項目を1件以上入力してください。")
    return false
  }
  return true
}

// フォームを保存してIDを返す（成功時）
const saveTemplateInternal = async () => {
  const payload = buildPayload()
  let response
  if (form.value.id) {
    response = await api.qualityEquipmentInspections.update(form.value.id, payload)
  } else {
    response = await api.qualityEquipmentInspections.create(payload)
  }
  const savedId = response.data?.id
  const targetId = Number(savedId || form.value.id || 0)
  await loadTemplateList()
  if (targetId) await loadTemplateDetail(targetId)
  else markSavedSnapshot()
  return targetId || savedId
}

const saveTemplate = async () => {
  if (!canEditFields.value) return
  if (!validateForm()) return

  saving.value = true
  try {
    await saveTemplateInternal()
    alert("保存しました。")
  } catch (error) {
    console.error("設備点検テンプレート保存に失敗:", error)
    alert("保存に失敗しました。")
  } finally {
    saving.value = false
  }
}

const openTestOperation = () => {
  if (!form.value.id) return
  router.push({
    path: '/quality/equipment-inspection/operation',
    query: { test_template_id: String(form.value.id) },
  })
}

const submitForReview = () => {
  if (!form.value.id || !canSubmitForReview.value) return
  if (!validateForm()) return
  submitComment.value = ""
  submitDialogVisible.value = true
}

const cancelSubmit = () => {
  submitDialogVisible.value = false
  submitComment.value = ""
}

const confirmSubmitForReview = async () => {
  if (!form.value.id) return
  submitDialogVisible.value = false
  actionLoading.value = true
  try {
    // 未保存の編集内容を先に保存してから確認依頼
    const savedId = await saveTemplateInternal()
    const targetId = savedId || form.value.id
    await api.qualityEquipmentInspections.submitForReview(targetId, submitComment.value)
    await loadTemplateList()
    await loadTemplateDetail(targetId)
    submitComment.value = ""
    alert("確認依頼を登録しました。")
  } catch (error) {
    console.error("確認依頼に失敗:", error)
    alert("確認依頼に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const completeReview = async () => {
  if (!form.value.id || !canReview.value) return
  const actionLabelText = reviewActionLabel.value
  const ok = window.confirm(`${actionLabelText}にします。よろしいですか？`)
  if (!ok) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.review(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert(`${actionLabelText}を登録しました。`)
  } catch (error) {
    console.error("確認完了に失敗:", error)
    alert("確認完了に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const approveTemplate = async () => {
  if (!form.value.id || !canApprove.value) return
  const ok = window.confirm("部長承認します。よろしいですか？")
  if (!ok) return

  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.approve(form.value.id)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    alert("部長承認しました。")
  } catch (error) {
    console.error("承認に失敗:", error)
    alert("承認に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const rejectTemplate = () => {
  if (!form.value.id || !canReject.value) return
  rejectComment.value = form.value.rejection_comment || ""
  rejectDialogVisible.value = true
}

const cancelReject = () => {
  rejectDialogVisible.value = false
  rejectComment.value = ""
}

const confirmReject = async () => {
  if (!form.value.id) return
  rejectDialogVisible.value = false
  actionLoading.value = true
  try {
    await api.qualityEquipmentInspections.reject(form.value.id, rejectComment.value)
    await loadTemplateList()
    await loadTemplateDetail(form.value.id)
    rejectComment.value = ""
    alert("差戻ししました。")
  } catch (error) {
    console.error("差戻しに失敗:", error)
    alert("差戻しに失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

const reviseTemplate = async () => {
  if (!form.value.id || !canRevise.value) return
  const ok = window.confirm(
    `v${form.value.version} を基に改訂版（v${form.value.version + 1}）を作成します。よろしいですか？`
  )
  if (!ok) return

  actionLoading.value = true
  try {
    const response = await api.qualityEquipmentInspections.revise(form.value.id)
    const newId = response.data?.id
    await loadTemplateList()
    if (newId) {
      await loadTemplateDetail(newId)
    }
    alert(`改訂版（v${response.data?.version}）を作成しました。`)
  } catch (error) {
    console.error("改訂に失敗:", error)
    alert(error.response?.data?.detail || "改訂に失敗しました。")
  } finally {
    actionLoading.value = false
  }
}

watch(
  () => route.query.id,
  async (nextId) => {
    if (isRestoringRouteQuery.value) return
    const numericId = Number(nextId || 0)
    if (!numericId || numericId === Number(selectedTemplateId.value || 0)) return
    const exists = templates.value.some((item) => Number(item.id) === numericId)
    if (!exists) return
    if (!confirmDiscardUnsavedChanges()) {
      try {
        isRestoringRouteQuery.value = true
        if (selectedTemplateId.value) {
          await router.replace({ path: route.path, query: { ...route.query, id: String(selectedTemplateId.value) } })
        } else {
          await router.replace({ path: route.path, query: {} })
        }
      } finally {
        isRestoringRouteQuery.value = false
      }
      return
    }
    await loadTemplateDetail(numericId)
  }
)

onBeforeRouteLeave((to, from, next) => {
  if (!confirmDiscardUnsavedChanges()) {
    next(false)
    return
  }
  next()
})

const handleBeforeUnload = (event) => {
  if (!hasUnsavedChanges.value) return
  event.preventDefault()
  event.returnValue = ""
}

onMounted(async () => {
  window.addEventListener("beforeunload", handleBeforeUnload)
  if (!canView.value) return
  await Promise.all([loadEquipmentOptions(), loadProcessAndLineOptions(), loadUnitOptions()])
  await loadTemplateList()

  const routeTemplateId = Number(route.query.id || 0)
  if (routeTemplateId && templates.value.some((item) => Number(item.id) === routeTemplateId)) {
    await loadTemplateDetail(routeTemplateId)
  } else if (templates.value.length) {
    await loadTemplateDetail(templates.value[0].id)
  } else {
    await startNewTemplate()
  }
  await resizeAllTextareas()
  markSavedSnapshot()
})

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", handleBeforeUnload)
})
</script>

<style scoped>
.inspection-master {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #111827;
  font-family: "Meiryo", "Yu Gothic UI", "Yu Gothic", sans-serif;
  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.02em;
}
.master-layout {
  display: grid;
  grid-template-columns: 34% 1fr;
  gap: 12px;
  min-height: 0;
}
.master-layout.create-mode {
  grid-template-columns: 1fr;
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
  gap: 4px 6px;
  padding: 4px 0 6px;
  flex-wrap: wrap;
}
.list-filter-input {
  flex: 1 1 100px;
  min-width: 80px;
  padding: 3px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
}
.list-filter-select {
  flex: 0 1 auto;
  max-width: 180px;
  padding: 3px 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 12px;
}
.required-mark {
  color: #dc2626;
  font-size: 12px;
  margin-left: 2px;
}
/* 差分表示 */
tr.diff-new td {
  background: #f0fdf4;
}
tr.diff-changed td {
  background: #fefce8;
}
tr.diff-deleted td {
  background: #fef2f2;
  color: #9ca3af;
  text-decoration: line-through;
  pointer-events: none;
}
.diff-badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  border-radius: 3px;
  padding: 1px 5px;
  margin-right: 4px;
  vertical-align: middle;
  white-space: nowrap;
}
.diff-badge-new {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}
.diff-badge-changed {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
}
.diff-badge-deleted {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
  text-decoration: none;
}
.table-wrap {
  overflow: auto;
  border: 1px solid #dde2ea;
  border-radius: 4px;
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
.daily-inspection-table th.col-no,
.daily-inspection-table td.col-no {
  width: 72px;
  min-width: 72px;
  max-width: 72px;
}
.daily-inspection-table td.col-no {
  padding-left: 4px;
  padding-right: 4px;
}
.daily-inspection-table td.col-no .no-input {
  min-width: 0;
  text-align: right;
  padding-left: 4px;
  padding-right: 4px;
}
.data-table.compact tbody tr {
  cursor: pointer;
}
.data-table.compact tbody tr.selected {
  background: #e7f0ff;
}
.status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
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
.status-chip.review {
  background: #fff4e5;
  border-color: #f5d19b;
  color: #9a5c00;
}
.status-chip.approve {
  background: #eaf7ff;
  border-color: #8ecdf3;
  color: #0c4a6e;
}
.status-chip.ok {
  background: #e9f7ef;
  border-color: #9fd9b4;
  color: #166534;
}
.status-chip.danger {
  background: #fdecec;
  border-color: #f7b1b1;
  color: #991b1b;
}
.status-meta {
  font-size: 14px;
  font-weight: 500;
  color: #334155;
}
.status-date {
  font-size: 12px;
  font-weight: 400;
  color: #64748b;
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
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.check-line {
  flex-direction: row !important;
  align-items: center;
  margin-top: 18px;
}
.multi-select-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.multi-select-label {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}
.multi-select-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.multi-select {
  width: 220px;
  flex-shrink: 0;
  min-height: 80px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  font-size: 13px;
  padding: 2px;
}
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-content: flex-start;
  flex: 1;
}
.no-selection {
  font-size: 12px;
  color: #94a3b8;
}
.selection-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #7dd3fc;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 12px;
  white-space: nowrap;
}
.tag-remove {
  background: none;
  border: none;
  color: #0369a1;
  cursor: pointer;
  padding: 0;
  font-size: 13px;
  line-height: 1;
}
.workflow-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.44);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 30;
}
.modal-panel {
  width: min(1100px, 100%);
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #d7dde7;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
  padding: 16px;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}
.attachment-target-name {
  margin-top: 4px;
  color: #475569;
  font-size: 13px;
}
.attachment-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.attachment-actions {
  display: flex;
  justify-content: flex-end;
}
.attachment-card {
  border: 1px solid #d7dde7;
  border-radius: 6px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.attachment-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.attachment-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 8px;
}
.attachment-form-grid .wide {
  grid-column: span 2;
}
.attachment-form-grid label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #334155;
}
.attachment-preview {
  display: flex;
  justify-content: flex-start;
}
.attachment-preview img {
  max-width: 100%;
  max-height: 280px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  object-fit: contain;
  background: #f8fafc;
}
.item-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item-section h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 6px;
}
.measurement-schedule-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 12px;
}
.schedule-type-radio {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.schedule-type-radio input[type="radio"] {
  width: auto;
  margin: 0;
}
.measurement-months-wrap {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  flex: 1;
  margin-left: 12px;
}
.measurement-months-label {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.measurement-month-check {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}
.measurement-month-check input[type="checkbox"] {
  width: auto;
  margin: 0;
}
.center {
  text-align: center;
}
input,
select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 4px 6px;
  background: #fff;
  font-size: 14px;
  line-height: 1.45;
  color: #0f172a;
  font-weight: 400;
  letter-spacing: 0.02em;
}
input::placeholder,
textarea::placeholder {
  color: #64748b;
}
input:disabled,
select:disabled,
textarea:disabled {
  color: #334155;
  background: #f8fafc;
  opacity: 1;
}
textarea {
  resize: none;
  overflow: hidden;
  min-height: 2.8em;
}
.auto-grow-textarea {
  line-height: 1.45;
}
.rejection-box {
  border: 1px solid #f5b7b1;
  background: #fff5f5;
  color: #7f1d1d;
  font-size: 12px;
  padding: 8px;
  border-radius: 4px;
}
.reject-modal {
  width: 520px;
  max-width: 95vw;
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
  min-height: 160px;
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
.btn-primary,
.btn-secondary,
.btn-review,
.btn-approve,
.btn-danger,
.btn-revise {
  border: 1px solid transparent;
  border-radius: 4px;
  padding: 5px 10px;
  font-size: 12px;
  cursor: pointer;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
}
.btn-secondary {
  background: #f1f5f9;
  color: #334155;
  border-color: #cbd5e1;
}
.btn-review {
  background: #f59e0b;
  color: #111827;
}
.btn-approve {
  background: #16a34a;
  color: #fff;
}
.btn-danger {
  background: #dc2626;
  color: #fff;
}
.btn-revise {
  background: #0e7490;
  color: #fff;
}
.btn-sm {
  padding: 3px 8px;
}
.hidden-file-input {
  display: none;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (max-width: 1100px) {
  .master-layout {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
  .attachment-form-grid {
    grid-template-columns: 1fr;
  }
  .attachment-form-grid .wide {
    grid-column: span 1;
  }
}
@media (max-width: 700px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .form-grid .wide {
    grid-column: span 1;
  }
  .modal-backdrop {
    padding: 10px;
  }
  .modal-panel {
    padding: 12px;
  }
}
</style>
