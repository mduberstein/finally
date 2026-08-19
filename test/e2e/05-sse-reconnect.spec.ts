import { expect, test } from "@playwright/test";

// SSE reconnection scenario from planning/PLAN.md section 12. Exercises
// frontend/lib/connection.ts's client-side error handling through the
// exact onerror/onopen handlers frontend/lib/usePriceStream.ts registers
// on its EventSource — it does not exercise a server-side drop or restart
// (flagged assumption #2 in the plan). Asserts only the negative
// connection state, never which of the two degraded labels appears,
// because that depends on internal retry/staleness timing this spec
// should not pin.
//
// Root cause note (deviation from the plan's original design): confirmed
// empirically (30s of continuous polling, both with plain browser-context
// offline emulation and with Playwright's own documented offline-mode
// reload pattern) that this Chromium build's context-level offline toggle
// does NOT interrupt an already-open EventSource stream — the server
// keeps pushing price frames over the still-live connection and the
// indicator never leaves the connected state. This matches a known
// Chromium behavior: offline emulation blocks new request initiation, not
// already-granted streaming responses. The context-level toggle is still
// called below (it is the correct mechanism for blocking any *new*
// connection attempt while simulated-offline), but making the
// currently-open stream actually drop requires the addInitScript
// instrumentation that follows: it wraps the page's EventSource
// constructor to (a) let the very first connection through untouched, so
// the initial "connected" read is genuine, and (b) let the test drive the
// same onerror/onopen handlers the app itself registers, while
// withholding further real price frames during the simulated-offline
// window so they cannot silently reset the state back.

test("sse reconnect: the connection indicator degrades offline and recovers online", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const OriginalEventSource = window.EventSource;
    const controls = { simulateOffline: false, instance: null as EventSource | null };
    (window as unknown as { __sseTestControls: typeof controls }).__sseTestControls = controls;

    class TestableEventSource extends OriginalEventSource {
      constructor(url: string | URL, init?: EventSourceInit) {
        super(url, init);
        controls.instance = this;
      }

      addEventListener(
        type: string,
        listener: EventListenerOrEventListenerObject,
        options?: boolean | AddEventListenerOptions,
      ): void {
        if (type !== "price") {
          super.addEventListener(type, listener, options);
          return;
        }
        const wrapped = (event: Event) => {
          if (controls.simulateOffline) return;
          if (typeof listener === "function") listener(event);
          else listener.handleEvent(event);
        };
        super.addEventListener(type, wrapped, options);
      }
    }

    // @ts-expect-error test-only override of the global constructor, applied
    // before any application script runs on this page.
    window.EventSource = TestableEventSource;
  });

  await page.goto("/");

  const connectionStatus = page.getByRole("status");
  await expect(connectionStatus).toHaveText("Connected");

  await page.context().setOffline(true);
  await page.evaluate(() => {
    const controls = (
      window as unknown as {
        __sseTestControls: { simulateOffline: boolean; instance: EventSource | null };
      }
    ).__sseTestControls;
    controls.simulateOffline = true;
    controls.instance?.dispatchEvent(new Event("error"));
  });

  await expect(connectionStatus).not.toHaveText("Connected", { timeout: 10_000 });

  await page.context().setOffline(false);
  await page.evaluate(() => {
    const controls = (
      window as unknown as {
        __sseTestControls: { simulateOffline: boolean; instance: EventSource | null };
      }
    ).__sseTestControls;
    controls.simulateOffline = false;
    controls.instance?.dispatchEvent(new Event("open"));
  });

  await expect(connectionStatus).toHaveText("Connected", { timeout: 10_000 });
});
