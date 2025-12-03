export const createCalendarsAPI = (client) => ({
  getCalendars() {
    return client.get('/calendars/')
  },
  getCalendar(id) {
    return client.get(`/calendars/${id}/`)
  },
  createCalendar(data) {
    return client.post('/calendars/', data)
  },
  updateCalendar(id, data) {
    return client.put(`/calendars/${id}/`, data)
  },
  deleteCalendar(id) {
    return client.delete(`/calendars/${id}/`)
  },

  // Calendar Days
  getCalendarDays(calendarId) {
    return client.get(`/calendar-days/?calendar=${calendarId}`)
  },
  createCalendarDay(data) {
    return client.post('/calendar-days/', data)
  },
  updateCalendarDay(id, data) {
    return client.put(`/calendar-days/${id}/`, data)
  },
  deleteCalendarDay(id) {
    return client.delete(`/calendar-days/${id}/`)
  },
})
