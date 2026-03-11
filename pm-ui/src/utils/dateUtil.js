export const BUSINESS_DAY_BOUNDARY_HOUR = 8;

export const formatISODate = (date) => {
  const d = new Date(date);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
};

export const getBusinessDate = (date = new Date(), boundaryHour = BUSINESS_DAY_BOUNDARY_HOUR) => {
  const d = new Date(date);
  if (d.getHours() < boundaryHour) {
    d.setDate(d.getDate() - 1);
  }
  return d;
};

export const getBusinessISODate = (date = new Date(), boundaryHour = BUSINESS_DAY_BOUNDARY_HOUR) => {
  return formatISODate(getBusinessDate(date, boundaryHour));
};

export const parseISODate = (iso) => {
  return new Date(iso);
};

export const addDays = (date, delta) => {
  const d = new Date(date);
  d.setDate(d.getDate() + delta);
  return d;
};
