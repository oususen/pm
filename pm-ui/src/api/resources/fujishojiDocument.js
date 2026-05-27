export const createFujishojiDocumentAPI = (client) => ({
  getAvailableDates: () => client.get('/shipping/fujishoji-document/available-dates/'),
  getConfig: () => client.get('/shipping/fujishoji-document/config/'),
  saveConfig: (payload) => client.post('/shipping/fujishoji-document/config/save/', payload),
  getData: (date) => client.get(`/shipping/fujishoji-document/${date}/`),
  generatePdf: (date) =>
    client.post(
      '/shipping/fujishoji-document/generate-pdf/',
      { target_date: date },
      { responseType: 'blob' }
    ),
})
