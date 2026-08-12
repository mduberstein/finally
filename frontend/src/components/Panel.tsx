import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  /** Right-aligned content in the title strip: counts, controls, status. */
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
}

/**
 * A pane of the instrument. Panels sit flush against each other with 1px void
 * gutters between them; the accent tick in the title strip is the only
 * decoration any panel gets.
 */
export function Panel({ title, aside, children, className = "", testId }: PanelProps) {
  return (
    <section
      data-testid={testId}
      className={`flex h-full min-h-0 min-w-0 flex-col bg-panel ${className}`}
    >
      <header className="flex h-7 shrink-0 items-center gap-2 border-b border-line-soft px-2">
        <span aria-hidden className="h-2.5 w-0.5 bg-accent" />
        <h2 className="label">{title}</h2>
        <div className="ml-auto flex items-center gap-2">{aside}</div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </section>
  );
}
