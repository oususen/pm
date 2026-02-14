const SPECIAL_ORDER_KEYS = [
  "special_display_order",
  "specialDisplayOrder",
  "special_order",
  "specialOrder",
  "display_order",
  "displayOrder",
  "product_display_order",
  "productDisplayOrder",
  "sort_order",
  "sortOrder",
  "priority_order",
  "priorityOrder",
];

const PRODUCT_CODE_KEYS = ["product_code", "productCode", "code"];

const toOrderNumber = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const defaultProductCodeGetter = (item) => {
  if (!item || typeof item !== "object") return "";
  for (const key of PRODUCT_CODE_KEYS) {
    if (item[key]) return String(item[key]);
  }
  return "";
};

export const resolveSpecialDisplayOrder = (item) => {
  if (!item || typeof item !== "object") return null;

  for (const key of SPECIAL_ORDER_KEYS) {
    const parsed = toOrderNumber(item[key]);
    if (parsed !== null) return parsed;
  }

  const nestedProduct = item.product;
  if (nestedProduct && typeof nestedProduct === "object") {
    for (const key of SPECIAL_ORDER_KEYS) {
      const parsed = toOrderNumber(nestedProduct[key]);
      if (parsed !== null) return parsed;
    }
  }

  return null;
};

export const compareBySpecialOrderThenProductCode = (a, b, options = {}) => {
  const orderGetter = options.orderGetter || resolveSpecialDisplayOrder;
  const productCodeGetter = options.codeGetter || defaultProductCodeGetter;

  const orderA = orderGetter(a);
  const orderB = orderGetter(b);
  const hasOrderA = orderA !== null;
  const hasOrderB = orderB !== null;

  if (hasOrderA && hasOrderB && orderA !== orderB) {
    return orderA - orderB;
  }
  if (hasOrderA !== hasOrderB) {
    return hasOrderA ? -1 : 1;
  }

  const codeA = productCodeGetter(a) || "";
  const codeB = productCodeGetter(b) || "";
  return codeA.localeCompare(codeB, "ja", { numeric: true, sensitivity: "base" });
};
