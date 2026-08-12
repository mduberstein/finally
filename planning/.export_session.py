"""Render a Claude Code session transcript to readable Markdown.

Conversation text in full; each tool call collapsed to a one-line summary.
Subagent sidechains are excluded - they are separate transcripts.
"""

import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
DST = Path(sys.argv[2])


def flat(text, limit=160):
    """One line, whitespace collapsed, truncated."""
    line = re.sub(r"\s+", " ", str(text)).strip()
    return line if len(line) <= limit else line[: limit - 1] + "…"


def tool_line(block):
    """A one-line summary of a single tool call."""
    name = block.get("name", "tool")
    args = block.get("input", {}) or {}
    if name == "Bash":
        detail = args.get("description") or args.get("command", "")
    elif name in ("Read", "Write", "Edit", "NotebookEdit"):
        detail = args.get("file_path", "")
    elif name == "SendMessage":
        detail = f"to {args.get('to', '?')} - {args.get('summary') or flat(args.get('message', ''), 80)}"
    elif name == "Agent":
        detail = f"{args.get('subagent_type', '?')} - {args.get('description', '')}"
    elif name == "ToolSearch":
        detail = args.get("query", "")
    elif name == "Skill":
        detail = args.get("skill", "")
    elif name == "Artifact":
        detail = args.get("file_path") or args.get("action", "")
    else:
        detail = flat(json.dumps(args), 120)
    return f"- `{name}` - {flat(detail)}"


BOILERPLATE = re.compile(
    r"This came from another Claude session.*?(?=\Z|\n\n)", re.S
)
CAVEAT = re.compile(r"<local-command-caveat>.*?</local-command-caveat>", re.S)
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def speaker(entry):
    """Label a user-role entry by what it actually is."""
    content = entry.get("message", {}).get("content")
    text = content if isinstance(content, str) else ""
    if "<teammate-message" in text or "<agent-message" in text:
        match = re.search(r'(?:teammate_id|from)="([^"]+)"', text)
        return f"Teammate: {match.group(1)}" if match else "Teammate"
    if "<local-command" in text or "<command-name>" in text:
        return "Local command"
    return "User"


def user_text(content):
    """Plain text of a user entry, dropping tool results and repeated boilerplate."""
    if isinstance(content, str):
        text = content
    else:
        text = "\n".join(
            b.get("text", "") for b in content or [] if b.get("type") == "text"
        )

    text = CAVEAT.sub("", text)
    text = REMINDER.sub("", text)
    text = BOILERPLATE.sub("", text)
    # Unwrap the XML envelopes so the doc reads as prose.
    text = re.sub(r"</?(?:teammate-message|agent-message)[^>]*>", "", text)
    text = re.sub(r"<command-name>(.*?)</command-name>", r"Command: \1", text)
    text = re.sub(r"<command-message>.*?</command-message>", "", text, flags=re.S)
    text = re.sub(r"<command-args></command-args>", "", text)
    text = re.sub(r"<command-args>(.*?)</command-args>", r"Args: \1", text, flags=re.S)
    text = re.sub(
        r"<local-command-stdout>(.*?)</local-command-stdout>",
        r"Output:\n\n```\n\1\n```",
        text,
        flags=re.S,
    )
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def main():
    out = [
        "# FinAlly - Agent Team Build Session",
        "",
        "Full conversation. Each tool call is collapsed to a one-line summary;",
        "subagent transcripts are separate and not included.",
        "",
        "---",
        "",
    ]
    turns = 0
    pending = []  # consecutive assistant output, flushed as one turn

    def flush():
        """Emit accumulated assistant output as a single section."""
        nonlocal turns, pending
        if not pending:
            return
        out.extend(["## Claude", ""])
        for texts, tools in pending:
            if texts:
                out.extend(["\n\n".join(texts), ""])
            if tools:
                out.extend(["*Tool calls:*", "", *tools, ""])
        pending = []
        turns += 1

    for line in SRC.open():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain") or entry.get("isMeta"):
            continue
        if entry.get("type") not in ("user", "assistant"):
            continue

        content = entry.get("message", {}).get("content")

        if entry["type"] == "user":
            text = user_text(content)
            if not text:
                continue
            flush()
            out += [f"## {speaker(entry)}", "", text, ""]
            turns += 1
            continue

        texts, tools = [], []
        for block in content or []:
            kind = block.get("type")
            if kind == "text" and block.get("text", "").strip():
                texts.append(block["text"].strip())
            elif kind == "tool_use":
                tools.append(tool_line(block))
        if texts or tools:
            pending.append((texts, tools))

    flush()
    DST.write_text("\n".join(out))
    print(f"{turns} turns -> {DST} ({DST.stat().st_size / 1024:.0f} KB)")


main()
