import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

/** jsdom has no canvas backend; the sparkline is expected to skip drawing. */
HTMLCanvasElement.prototype.getContext = () => null;

afterEach(() => {
  cleanup();
});
