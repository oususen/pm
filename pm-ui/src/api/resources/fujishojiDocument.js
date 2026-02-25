export const createFujishojiDocumentAPI = (client) => ({
  getAvailableDates: () => client.get('/shipping/fujishoji-document/available-dates/'),
  getData: (date) => client.get(`/shipping/fujishoji-document/${date}/`),
  generatePdf: (date) =>
    client.post(
      '/shipping/fujishoji-document/generate-pdf/',
      { target_date: date },
      { responseType: 'blob' }
    ),
})
