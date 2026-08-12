"use client";

import { useEffect, useRef } from "react";
import { priceStore } from "@/lib/priceStore";

const WIDTH = 56;
const HEIGHT = 18;

const STROKE = {
  up: "#21c07a",
  down: "#f0576b",
  flat: "#59616f",
} as const;

interface SparklineProps {
  ticker: string;
  tone: keyof typeof STROKE;
  /** Latest price, used only to trigger a redraw when a tick lands. */
  price: number | null | undefined;
}

/**
 * Session price action, accumulated from the stream since page load. Draws
 * straight to canvas so a tick never costs a React render beyond its row.
 */
export function Sparkline({ ticker, tone, price }: SparklineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const ratio = window.devicePixelRatio || 1;
    canvas.width = WIDTH * ratio;
    canvas.height = HEIGHT * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, WIDTH, HEIGHT);

    const points = priceStore.getSeries(ticker);
    if (points.length < 2) return;

    const values = points.map((point) => point.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    const step = WIDTH / (values.length - 1);

    context.beginPath();
    values.forEach((value, index) => {
      const x = index * step;
      const y = HEIGHT - 1 - ((value - min) / span) * (HEIGHT - 2);
      if (index === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.strokeStyle = STROKE[tone];
    context.lineWidth = 1;
    context.stroke();
  }, [ticker, tone, price]);

  return (
    <canvas
      ref={canvasRef}
      data-testid={`sparkline-${ticker}`}
      style={{ width: WIDTH, height: HEIGHT }}
      aria-hidden
    />
  );
}
