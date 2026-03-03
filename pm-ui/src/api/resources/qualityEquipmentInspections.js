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
  submitForReview(id) {
    return client.post(`/equipment-inspection-templates/${id}/submit_for_review/`);
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
  workflowLogs(id) {
    return client.get(`/equipment-inspection-templates/${id}/workflow_logs/`);
  },
});
