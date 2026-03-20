export const createSpotLineActualsAPI = (client) => ({
  /** スポットライン計画取得 GET /spot-line-plan/?date=YYYY-MM-DD */
  getPlan(date) {
    return client.get('/spot-line-plan/', { params: date ? { date } : {} })
  },
  /** スポットライン加工品一覧（追加用） GET /spot-line-products/?process_id=X&date=YYYY-MM-DD */
  getProducts(processId, date) {
    const params = {}
    if (processId) params.process_id = processId
    if (date) params.date = date
    return client.get('/spot-line-products/', { params })
  },
  /** スポットライン設備一覧 GET /spot-line-equipments/ */
  getEquipments() {
    return client.get('/spot-line-equipments/')
  },
  /** 作業記録の最新状態取得 GET /spot-line-record/?plan_date=X&process_id=Y */
  getRecordStates(planDate, processId) {
    const params = {}
    if (planDate) params.plan_date = planDate
    if (processId) params.process_id = processId
    return client.get('/spot-line-record/', { params })
  },
  /** 作業記録保存 POST /spot-line-record/ */
  saveRecord(payload) {
    return client.post('/spot-line-record/', payload)
  },
})
