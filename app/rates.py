"""South African Reserve Bank repo rate: every change since March 2023, with a source for each.

The table lists announcement dates of the Monetary Policy Committee (MPC) decisions that *changed*
the rate; meetings that left it unchanged are not listed because the rate in force is the same.
The prime lending rate in South Africa is set by convention at repo + 3.5 percentage points.

Figures were checked against the news reports linked below on DATA_AS_OF. They are reference
data, not a live feed: after each MPC meeting, add a row and update DATA_AS_OF.
For official figures, see https://www.resbank.co.za.
"""

from dataclasses import dataclass
from datetime import date

DATA_AS_OF = date(2026, 11, 9)
PRIME_SPREAD = 3.5      # prime = repo + 3.5 percentage points


@dataclass(frozen=True)
class RepoChange:
    announced: date
    rate_percent: float
    source: str


REPO_CHANGES: tuple[RepoChange, ...] = (
    RepoChange(date(2023, 3, 30), 7.75,
               "https://www.global-rates.com/de/zinssatze/zentralbanken/zentralbank-sudafrika/sarb-zinssatz.aspx"),
    RepoChange(date(2023, 5, 25), 8.25,
               "https://www.global-rates.com/de/zinssatze/zentralbanken/zentralbank-sudafrika/sarb-zinssatz.aspx"),
    RepoChange(date(2024, 9, 19), 8.00, "https://mg.co.za/business/2024-09-19-reserve-bank-cuts-repo-rate-to-8/"),
    RepoChange(date(2024, 11, 21), 7.75, "https://ewn.co.za/2024/11/21/sarb-mpc-cuts-repo-rate-to-775"),
    RepoChange(date(2025, 1, 30), 7.50,
               "https://thestar.com.my/news/world/2025/01/31/south-african-central-bank-cuts-repurchase-rate-by-25-basis-points"),
    RepoChange(date(2025, 5, 29), 7.25, "https://www.ooba.co.za/faq/repo-rate-cut/"),
    RepoChange(date(2025, 7, 31), 7.00,
               "https://iol.co.za/business/economy/2025-07-31-interest-rates-reduced-how-the-sarbs-latest-move-impacts-you/"),
    RepoChange(date(2025, 11, 20), 6.75, "https://www.sanews.gov.za/south-africa/repo-rate-reduced-675-0"),
    RepoChange(date(2026, 5, 28), 7.00, "https://tradingeconomics.com/south-africa/interest-rate/news/554513"),
    RepoChange(date(2026, 9, 23), 7.25, "https://tradingeconomics.com/south-africa/interest-rate/news/554513"),
)


def rate_on(day: date) -> RepoChange:
    """The repo rate decision in force on `day` (decisions take effect from the announcement date here).

    Raises ValueError for dates before the first change in the table, where the table cannot say.
    """
    if day < REPO_CHANGES[0].announced:
        raise ValueError(f"No data before {REPO_CHANGES[0].announced.isoformat()}")
    in_force = REPO_CHANGES[0]
    for change in REPO_CHANGES:
        if change.announced <= day:
            in_force = change
        else:
            break
    return in_force


def change_bp(change: RepoChange) -> int | None:
    """Size of the move in basis points (+25 = hike), or None for the first row in the table."""
    i = REPO_CHANGES.index(change)
    if i == 0:
        return None
    return round((change.rate_percent - REPO_CHANGES[i - 1].rate_percent) * 100)
