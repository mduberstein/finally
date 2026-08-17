import type { PricePoint } from "@/lib/priceHistory";

interface SparklineProps {
  points: PricePoint[];
  width?: number;
  height?: number;
}

/**
 * Hand-rolled inline SVG sparkline, deliberately not a chart-library
 * instance — ten-plus concurrent library chart instances each registering a
 * resize observer and re-rendering every 500ms is the per-tick recompute
 * cost STATE.md flagged as T-02-13 to address in this phase (03-RESEARCH.md
 * Anti-Patterns). Marked `aria-hidden`: the autoscaled shape is decoration,
 * the row's signed percent change beside it remains the authoritative
 * statement of how much the price actually moved.
 */
export function Sparkline({ points, width = 96, height = 28 }: SparklineProps) {
  if (points.length < 2) {
    return <svg width={width} height={height} aria-hidden="true" />;
  }

  const prices = points.map((point) => point.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;

  const coords = points.map((point, index) => {
    const x = (index / (points.length - 1)) * width;
    const y = height - ((point.price - min) / range) * height;
    return `${x},${y}`;
  });

  const trendingUp = points[points.length - 1].price >= points[0].price;
  const stroke = trendingUp ? "var(--up)" : "var(--down)";

  return (
    <svg width={width} height={height} aria-hidden="true">
      <polyline points={coords.join(" ")} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}
