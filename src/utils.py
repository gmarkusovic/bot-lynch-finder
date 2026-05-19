"""Shared formatting utilities used across notifier, html_reporter and bot_commands."""

SIGNAL_EMOJI: dict[str, str] = {
    "COMPRA_FUERTE": "🚀",
    "COMPRA":        "🟢",
    "SEGUIMIENTO":   "👀",
    "SOBRECOMPRADA": "⚠️",
    "VENTA":         "🔴",
    "NEUTRAL":       "⚪",
    "PENDIENTE":     "⏳",
}

SIGNAL_ORDER = ["COMPRA_FUERTE", "COMPRA", "SEGUIMIENTO", "SOBRECOMPRADA", "VENTA"]
SHOW_SIGNALS  = set(SIGNAL_ORDER)


def fmt(val, decimals: int = 2, suffix: str = "") -> str:
    """Format a numeric value or return '—' if None."""
    return "—" if val is None else f"{val:.{decimals}f}{suffix}"


def fcf_icon(fcf) -> str:
    """Return ✅/❌/— based on free cash flow sign."""
    if fcf is None:
        return "—"
    return "✅" if fcf > 0 else "❌"


def pages_url() -> str:
    """Build GitHub Pages URL from GITHUB_REPOSITORY env var. Returns '' if unavailable."""
    import os
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo or "/" not in repo:
        return ""
    owner, repo_name = repo.split("/", 1)
    return f"https://{owner}.github.io/{repo_name}/"
