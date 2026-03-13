from dataclasses import dataclass
import logging
import sys
from .db import get_recent_team_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class TeamRates:
    goals_for: float
    xg_for: float
    hits_for: float
    hdc_for: float
    mdc_for: float


def get_expected_value(avg: float, low: float, high: float) -> float:
    if avg is not None and avg != 0:
        return float(avg)
    if low is None or high is None:
        return float(low or high or 0.0)
    return float((low + high) / 2.0)

def build_team_rates(team_tla: str, lookback_games: int) -> TeamRates:


    recent_stats = get_recent_team_stats(team_tla, lookback_games) or {}
    if len(recent_stats) == 0:
        return TeamRates(
            goals_for=0.0,
            xg_for=0.0,
            hits_for=0.0,
            hdc_for=0.0,
            mdc_for=0.0,
        )
    return TeamRates(
        goals_for=float(recent_stats.get("goals_for_avg") or 0.0),
        xg_for=float(recent_stats.get("xg_for_avg") or 0.0),
        hits_for=float(recent_stats.get("hits_for_avg") or 0.0),
        hdc_for=float(recent_stats.get("hdc_for_avg") or 0.0),
        mdc_for=float(recent_stats.get("mdc_for_avg") or 0.0),
    )
