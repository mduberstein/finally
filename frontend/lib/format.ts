const EM_DASH = "—";

/** Format a price with exactly 2 decimal places and a thousands separator. */
export function formatPrice(value: number | null | undefined): string {
  if (value == null) return EM_DASH;
  return value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Format a percent change with 2 decimals and an explicit sign, except on exact zero. */
export function formatPercent(value: number | null | undefined): string {
  if (value == null) return EM_DASH;
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}
