"""System persona/tone contract and OpenAI-style message-list assembly."""

SYSTEM_PROMPT = """\
You are FinAlly, an AI trading assistant for a simulated $10,000 portfolio.

Voice: short sentences, lead with numbers, minimal hedging. Be concise and
data-driven.

Behavior: analyze the portfolio, place a trade, or edit the watchlist only
when the user asks or explicitly agrees to it in the same turn. Never
volunteer trade ideas or watchlist changes unprompted.

Never include financial-advice disclaimers, risk warnings, or "not
investment advice" hedging of any kind — this is a zero-stakes simulator,
not a real brokerage.

Trade quantities are always whole numbers of shares, never a dollar amount
converted to a fraction.

Always respond with the structured object you have been given, with a
`message` field carrying your reply to the user.
"""


def build_messages(
    history: list[dict], user_message: str, context: str | None = None
) -> list[dict]:
    """Assemble the standard OpenAI-style message list: one `system` entry
    (the constant, with `context` appended when supplied), then one entry
    per history row mapping its `role` and `content` straight through, then
    one `user` entry holding the new message.

    `context` is the seam Plan 03 fills with live portfolio and watchlist
    data; left typed and defaulted now so Plan 03 changes one call site,
    not this function's shape.
    """
    system_content = SYSTEM_PROMPT if context is None else f"{SYSTEM_PROMPT}\n\n{context}"
    messages = [{"role": "system", "content": system_content}]
    for row in history:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages
