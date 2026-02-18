export const createCalendarsAPI = (client) => ({
  getCalendars(params = {}) {
    return client.get('/calendars/', { params })
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
  getCalendarDays(calendarId, params = {}) {
    return client.get('/calendar-days/', {
      params: {
        ...params,
        calendar: calendarId,
      },
    })
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
