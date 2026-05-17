"""Tests for deep-link /start parameter parsing."""
from src.bot.handlers.commands import _parse_deep_link


class TestParseDeepLink:
    """Tests for _parse_deep_link function."""

    def test_no_args(self):
        """Returns empty action when no args provided."""
        assert _parse_deep_link(None) == ("", 0)
        assert _parse_deep_link("") == ("", 0)

    def test_monthly(self):
        """Returns monthly action with 0 days (show tier selection)."""
        assert _parse_deep_link("monthly") == ("monthly", 0)

    def test_monthly_with_days(self):
        """Returns monthly action with specific duration days."""
        assert _parse_deep_link("monthly_30") == ("monthly", 30)
        assert _parse_deep_link("monthly_90") == ("monthly", 90)
        assert _parse_deep_link("monthly_180") == ("monthly", 180)

    def test_monthly_with_invalid_days(self):
        """Invalid days after monthly_ falls back to tier selection."""
        assert _parse_deep_link("monthly_0") == ("monthly", 0)
        assert _parse_deep_link("monthly_abc") == ("monthly", 0)
        assert _parse_deep_link("monthly_-1") == ("monthly", 0)

    def test_monthly_case_insensitive(self):
        """Case-insensitive parsing."""
        assert _parse_deep_link("Monthly") == ("monthly", 0)
        assert _parse_deep_link("MONTHLY") == ("monthly", 0)

    def test_tokens_without_count(self):
        """Returns tokens action with 0 count (show selection)."""
        assert _parse_deep_link("tokens") == ("tokens", 0)

    def test_tokens_with_count(self):
        """Returns tokens action with specific count."""
        assert _parse_deep_link("tokens_5") == ("tokens", 5)
        assert _parse_deep_link("tokens_10") == ("tokens", 10)
        assert _parse_deep_link("tokens_1") == ("tokens", 1)
        assert _parse_deep_link("tokens_25") == ("tokens", 25)

    def test_tokens_with_count_case_insensitive(self):
        """Case-insensitive tokens_N parsing."""
        assert _parse_deep_link("Tokens_5") == ("tokens", 5)
        assert _parse_deep_link("TOKENS_10") == ("tokens", 10)

    def test_tokens_with_zero_count(self):
        """tokens_0 falls back to token selection (count must be > 0)."""
        assert _parse_deep_link("tokens_0") == ("tokens", 0)

    def test_tokens_with_invalid_count(self):
        """Invalid count after tokens_ falls back to token selection."""
        assert _parse_deep_link("tokens_abc") == ("tokens", 0)
        assert _parse_deep_link("tokens_-1") == ("tokens", 0)

    def test_unknown_param(self):
        """Unknown deep link parameter returns empty action."""
        assert _parse_deep_link("unknown") == ("", 0)
        assert _parse_deep_link("foo_bar") == ("", 0)

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped."""
        assert _parse_deep_link("  monthly  ") == ("monthly", 0)
        assert _parse_deep_link(" tokens_5 ") == ("tokens", 5)
