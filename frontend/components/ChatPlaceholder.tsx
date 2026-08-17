/**
 * Reserved, non-interactive AI chat panel slot (D-03). Sized identically to
 * the Heatmap and P&L chart containers (`h-64`/`min-h-64`) so Phase 4 fills
 * real chat content into an already-correctly-sized slot without triggering
 * a layout reflow. Structure and styling only — no input, no handler, no
 * state. Uses the same neutral empty-state treatment as every other empty
 * panel; Accent Yellow stays unused through Phase 3 (see 03-UI-SPEC.md's
 * explicit resolution).
 */
export function ChatPlaceholder() {
  return (
    <section className="rounded-md border border-border bg-card p-6">
      <div className="flex h-64 min-h-64 flex-col items-center justify-center gap-2 text-center">
        <p className="text-heading text-foreground">AI Copilot</p>
        <p className="text-body text-muted-foreground">
          Chat with an AI assistant that can analyze your portfolio and execute trades — arriving in the next update.
        </p>
      </div>
    </section>
  );
}
