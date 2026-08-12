import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "./ChatPanel";
import type { ChatMessage } from "@/lib/types";

const HISTORY: ChatMessage[] = [
  {
    role: "user",
    content: "buy 10 shares of Apple",
    actions: [],
    created_at: "2026-08-11T12:00:00+00:00",
  },
  {
    role: "assistant",
    content: "Bought 10 AAPL at $195.00.",
    actions: [
      {
        type: "trade",
        status: "executed",
        detail: "Bought 10 AAPL @ $195.00",
        ticker: "AAPL",
      },
      {
        type: "watchlist",
        status: "failed",
        detail: "PYPL is already on the watchlist",
        ticker: "PYPL",
      },
    ],
    created_at: "2026-08-11T12:00:01+00:00",
  },
];

describe("ChatPanel", () => {
  it("invites the user to act when there is no history", () => {
    render(<ChatPanel messages={[]} loading={false} error={null} onSend={vi.fn()} />);
    expect(screen.getByTestId("chat-empty")).toBeInTheDocument();
  });

  it("renders both roles in order", () => {
    render(<ChatPanel messages={HISTORY} loading={false} error={null} onSend={vi.fn()} />);

    const messages = screen.getAllByTestId("chat-message");
    expect(messages).toHaveLength(2);
    expect(messages[0]).toHaveAttribute("data-role", "user");
    expect(messages[0]).toHaveTextContent("buy 10 shares of Apple");
    expect(messages[1]).toHaveAttribute("data-role", "assistant");
  });

  it("renders executed and failed actions as chips", () => {
    render(<ChatPanel messages={HISTORY} loading={false} error={null} onSend={vi.fn()} />);

    const chips = screen.getAllByTestId("chat-action-chip");
    expect(chips).toHaveLength(2);
    expect(chips[0]).toHaveAttribute("data-status", "executed");
    expect(chips[0]).toHaveTextContent("Bought 10 AAPL @ $195.00");
    expect(chips[1]).toHaveAttribute("data-status", "failed");
    expect(chips[1]).toHaveTextContent("PYPL is already on the watchlist");
  });

  it("shows the loading indicator and blocks sending while waiting", () => {
    render(<ChatPanel messages={HISTORY} loading error={null} onSend={vi.fn()} />);

    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    expect(screen.getByTestId("chat-send")).toBeDisabled();
  });

  it("sends the message and clears the input", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} loading={false} error={null} onSend={onSend} />);

    await user.type(screen.getByTestId("chat-input"), "how am I doing?");
    await user.click(screen.getByTestId("chat-send"));

    expect(onSend).toHaveBeenCalledWith("how am I doing?");
    expect(screen.getByTestId("chat-input")).toHaveValue("");
  });

  it("surfaces an assistant failure", () => {
    render(
      <ChatPanel
        messages={HISTORY}
        loading={false}
        error="The assistant is unavailable."
        onSend={vi.fn()}
      />,
    );
    expect(screen.getByTestId("chat-error")).toHaveTextContent("The assistant is unavailable.");
  });
});
