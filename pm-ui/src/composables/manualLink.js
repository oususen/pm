// マニュアル（pm-ui/public/manual 配下のパス）を別タブで開く
export const openManual = (manualPath) => {
  const encoded = String(manualPath || '').split('/').filter(Boolean).map(encodeURIComponent).join('/')
  window.open(`/manual?path=${encoded}`, '_blank', 'noopener')
}
