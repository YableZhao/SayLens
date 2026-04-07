"""Edit-distance alignment between expected and actual phoneme sequences."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PhonemeComparison:
    """Result of comparing one position in expected vs actual phoneme sequences."""
    expected: str | None  # None if insertion
    actual: str | None    # None if deletion
    match_type: str       # "correct", "substitution", "insertion", "deletion"
    position: int         # index in the alignment


class PhonemeComparator:
    """Compare expected vs actual phoneme sequences using Levenshtein alignment."""

    def compare(self, expected: list[str], actual: list[str]) -> list[PhonemeComparison]:
        """Align two phoneme sequences and classify each position.

        Returns:
            List of PhonemeComparison indicating match/substitution/insertion/deletion.
        """
        n, m = len(expected), len(actual)

        # DP table
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n + 1):
            dp[i][0] = i
        for j in range(m + 1):
            dp[0][j] = j

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if expected[i - 1] == actual[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],     # deletion
                        dp[i][j - 1],     # insertion
                        dp[i - 1][j - 1], # substitution
                    )

        # Backtrace
        results = []
        i, j = n, m
        while i > 0 or j > 0:
            if i > 0 and j > 0 and expected[i - 1] == actual[j - 1]:
                results.append(PhonemeComparison(
                    expected=expected[i - 1], actual=actual[j - 1],
                    match_type="correct", position=i - 1,
                ))
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
                results.append(PhonemeComparison(
                    expected=expected[i - 1], actual=actual[j - 1],
                    match_type="substitution", position=i - 1,
                ))
                i -= 1
                j -= 1
            elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
                results.append(PhonemeComparison(
                    expected=None, actual=actual[j - 1],
                    match_type="insertion", position=i,
                ))
                j -= 1
            else:
                results.append(PhonemeComparison(
                    expected=expected[i - 1], actual=None,
                    match_type="deletion", position=i - 1,
                ))
                i -= 1

        results.reverse()
        # Re-number positions sequentially
        for idx, r in enumerate(results):
            r.position = idx
        return results

    def accuracy(self, comparisons: list[PhonemeComparison]) -> float:
        """Compute fraction of correct matches."""
        if not comparisons:
            return 0.0
        correct = sum(1 for c in comparisons if c.match_type == "correct")
        return correct / len(comparisons)
