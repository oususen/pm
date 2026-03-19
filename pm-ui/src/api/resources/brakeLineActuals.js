export const createBrakeLineActualsAPI = (client) => ({
  /** ブレーキライン自動計画取得 GET /brake-line-plan/?date=YYYY-MM-DD */
  getPlan(date) {
    return client.get('/brake-line-plan/', { params: date ? { date } : {} })
  },
  /** ブレーキライン加工品一覧（追加用セレクト） GET /brake-line-products/?process_id=X&date=YYYY-MM-DD */
  getProducts(processId, date) {
    const params = {}
    if (processId) params.process_id = processId
    if (date) params.date = date
    return client.get('/brake-line-products/', { params })
  },
  /** ブレーキライン設備一覧 GET /brake-line-equipments/ */
  getEquipments(processId) {
    return client.get('/brake-line-equipments/', { params: processId ? { process_id: processId } : {} })
  },
  /** 作業記録の最新状態取得 GET /brake-line-record/?plan_date=X&process_id=Y */
  getRecordStates(planDate, processId) {
    const params = {}
    if (planDate) params.plan_date = planDate
    if (processId) params.process_id = processId
    return client.get('/brake-line-record/', { params })
  },
  /** 作業記録保存 POST /brake-line-record/ */
  saveRecord(payload) {
    return client.post('/brake-line-record/', payload)
  },
  /** 実績累積加算（後方互換） POST /brake-line-actual/add/ */
  addActual(payload) {
    return client.post('/brake-line-actual/add/', payload)
  },
  /** 生産実績照会用セッション一覧 GET /brake-line-sessions/ */
  getSessions(params) {
    return client.get('/brake-line-sessions/', { params: params || {} })
  },
  /** 生産実績変更（レーザ/ブレーキ由来） PATCH /brake-line-sessions/{id}/ */
  updateSession(sessionId, payload) {
    return client.patch(`/brake-line-sessions/${sessionId}/`, payload || {})
  },
  /** 生産実績変更（レーザ/ブレーキ由来） DELETE /brake-line-sessions/{id}/ */
  deleteSession(sessionId, payload = null) {
    return client.delete(`/brake-line-sessions/${sessionId}/`, payload ? { data: payload } : undefined)
  },
})
