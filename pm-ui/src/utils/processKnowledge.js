export const PROCESS_KNOWLEDGE_TABS = [
  { key: 'common', label: '共通手順', icon: '📋' },
  { key: 'defects', label: '不良事例', icon: '⚠️' },
  { key: 'equipment', label: '設備別注意', icon: '🏭' },
  { key: 'checklist', label: '新人チェックリスト', icon: '✅' },
]

const normalizeId = (value) => String(value || '').trim()

export function buildProcessKnowledgePath({ processId, category, equipmentId }) {
  const normalizedProcessId = normalizeId(processId)
  if (!normalizedProcessId) return ''

  if (category === 'common') return `process-knowledge/${normalizedProcessId}/common`
  if (category === 'defects') return `process-knowledge/${normalizedProcessId}/defects`
  if (category === 'checklist') return `process-knowledge/${normalizedProcessId}/checklist`
  if (category === 'equipment') {
    const normalizedEquipmentId = normalizeId(equipmentId) || 'common'
    return `process-knowledge/${normalizedProcessId}/equipment/${normalizedEquipmentId}`
  }
  return ''
}

export function buildProcessKnowledgeDefaultContent({
  category,
  processLabel = '未選択工程',
  equipmentLabel = '',
}) {
  if (category === 'common') {
    return `# ${processLabel} 共通手順

## 目的
- 作業者ごとの差を減らし、安全と品質をそろえるための共通手順です

## 作業前確認
- 図面、品番、工程を確認する
- 使用設備、金型、治具、材料を確認する
- キズ、打痕、反りがないか確認する

## 作業の流れ
1. 段取り条件を確認する
2. 初品を加工して寸法と外観を確認する
3. 問題がなければ量産を開始する
4. 加工中は角度、寸法、キズを定期確認する
5. 終了時に実績と異常有無を残す

## 注意点
- 品番ごとの標準条件はここではなく製品別標準に残す
- 誰が見ても再現できる表現で書く
`
  }

  if (category === 'defects') {
    return `# ${processLabel} 不良事例

## 記入ルール
- 症状、原因、暫定対応、再発防止をセットで残す
- 品番固有条件ではなく、現場で再発しやすい判断ポイントを書く

## 事例テンプレート
### 事例名
- 発生日:
- 症状:
- 発生条件:
- 原因:
- その場対応:
- 再発防止:
- 備考:
`
  }

  if (category === 'equipment') {
    const targetLabel = equipmentLabel || '共通メモ'
    return `# ${processLabel} 設備別注意

## 対象設備
- 設備: ${targetLabel}

## 記入ルール
- 設備固有のクセ、立上げ時の確認事項、トラブル傾向を書く
- 設備未選択のときは工程共通メモとして使う

## メモ
- 立上げ確認:
- 加工時のクセ:
- キズ対策:
- よくあるトラブル:
- 注意する条件:
- その他:
`
  }

  if (category === 'checklist') {
    return `# ${processLabel} 新人チェックリスト

## 作業前
- 保護具を着用している
- 図面、作業順、使用設備を理解している
- 危険ポイントを理解している

## 作業中
- 初品確認の手順を説明できる
- 異常時の止め方と報告先を理解している
- キズ、寸法、向きの確認ポイントを理解している

## 作業後
- 実績入力ができる
- 次の人へ引継ぎ事項を残せる
`
  }

  return '# 未登録\n\nまだ登録されていません。'
}
