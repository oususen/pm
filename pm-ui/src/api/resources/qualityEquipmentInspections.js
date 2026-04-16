export const createQualityEquipmentInspectionsAPI = (client) => ({
  list(params = {}) {
    return client.get("/equipment-inspection-templates/", { params });
  },
  get(id) {
    return client.get(`/equipment-inspection-templates/${id}/`);
  },
  create(data) {
    return client.post("/equipment-inspection-templates/", data);
  },
  update(id, data) {
    return client.put(`/equipment-inspection-templates/${id}/`, data);
  },
  delete(id) {
    return client.delete(`/equipment-inspection-templates/${id}/`);
  },
  submitForReview(id, comment = "") {
    return client.post(`/equipment-inspection-templates/${id}/submit_for_review/`, { comment });
  },
  review(id) {
    return client.post(`/equipment-inspection-templates/${id}/review/`);
  },
  approve(id) {
    return client.post(`/equipment-inspection-templates/${id}/approve/`);
  },
  reject(id, comment = "") {
    return client.post(`/equipment-inspection-templates/${id}/reject/`, { comment });
  },
  revise(id) {
    return client.post(`/equipment-inspection-templates/${id}/revise/`);
  },
  workflowLogs(id) {
    return client.get(`/equipment-inspection-templates/${id}/workflow_logs/`);
  },
  uploadAttachmentImage(formData) {
    return client.post("/equipment-inspection-templates/upload_attachment_image/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  listTasks(params = {}) {
    return client.get("/equipment-inspection-tasks/", { params });
  },
  listRecords(params = {}) {
    return client.get("/equipment-inspection-records/", { params });
  },
  getRecord(id) {
    return client.get(`/equipment-inspection-records/${id}/`);
  },
  createRecord(data) {
    return client.post("/equipment-inspection-records/", data);
  },
  updateRecord(id, data) {
    return client.put(`/equipment-inspection-records/${id}/`, data);
  },
  prepareRecord(params = {}) {
    return client.get("/equipment-inspection-records/prepare/", { params });
  },
  monthlyOverview(params = {}) {
    return client.get("/equipment-inspection-records/monthly_overview/", { params });
  },
  listConfirmations(params = {}) {
    return client.get("/equipment-inspection-confirmations/", { params });
  },
  upsertConfirmation(data) {
    return client.post("/equipment-inspection-confirmations/upsert/", data);
  },
});
