export function Header() {
  return (
    <header className="flex items-center justify-between border-b border-border bg-card p-6">
      <span className="text-heading text-primary">FinAlly</span>
      {/* Connection status indicator slot — filled in by Plan 04 */}
      <div />
    </header>
  );
}
