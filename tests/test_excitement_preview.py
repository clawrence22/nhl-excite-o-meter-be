import os

import numpy as np
import pytest

from nhl_excite_o_meter import preview
from nhl_excite_o_meter.teamrates import TeamRates
from nhl_excite_o_meter.preview_excitement_score import (
    calculate_excitement_score,
    sort_excitement_score,
)


def make_rates(
    goals_for: float,
    xg_for: float,
    hits_for: float,
    hdc_for: float,
    mdc_for: float,
) -> TeamRates:
    # Keep low/high equal to average for deterministic testing.
    return TeamRates(
        goals_for=goals_for,
        xg_for=xg_for,
        hits_for=hits_for,
        hdc_for=hdc_for,
        mdc_for=mdc_for
    )


PROFILES = {

    ##Mid
    "CBJ": make_rates(goals_for=4.2, xg_for=3.4, hits_for=18.0, hdc_for=13.0, mdc_for=12.0),
    "FLA": make_rates(goals_for=2.8, xg_for=2.5, hits_for=27.0, hdc_for=15.0, mdc_for=9.0),

    ##Burner
    "EDM": make_rates(goals_for=4.1, xg_for=3.5, hits_for=19.0, hdc_for=10.5, mdc_for=14.0),
    "TOR": make_rates(goals_for=3.8, xg_for=3.3, hits_for=18.5, hdc_for=9.8, mdc_for=13.1),
    
    ##Meh
    "NSH": make_rates(goals_for=2.4, xg_for=1.6, hits_for=18.0, hdc_for=6.0, mdc_for=5.0),
    "MIN": make_rates(goals_for=6.5, xg_for=1.4, hits_for=15.0, hdc_for=6.3, mdc_for=5.0),
    
    ##Buzzin
    "NYR": make_rates(goals_for=3.6, xg_for=2.8, hits_for=19.0, hdc_for=9.0, mdc_for=11.0),
    "SJS": make_rates(goals_for=3.3, xg_for=2.6, hits_for=18.0, hdc_for=7.0, mdc_for=10.2),
}


@pytest.fixture(autouse=True)
def _env_setup(monkeypatch):
    monkeypatch.setenv("DB_HOST", "dummy")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "dummy")
    monkeypatch.setenv("DB_NAME", "dummy")
    monkeypatch.setenv("DB_REGION", "us-east-1")
    monkeypatch.setenv("DB_SSLMODE", "require")


@pytest.fixture(autouse=True)
def _team_rates_stub(monkeypatch):
    monkeypatch.setattr(preview, "build_team_rates", lambda team, _: PROFILES[team])


@pytest.mark.parametrize(
    "home,away,expected_label",
    [
        ("EDM", "TOR", "Barn Burner"),
        ("NSH", "MIN", "Meh"),
        ("NYR", "SJS", "Buzzin"),
        ("CBJ", "FLA", "Mid"),
    ],
)
def test_excitement_label_for_matchup(home, away, expected_label):
    rng = np.random.default_rng(12345)
    game = preview.simulate_preview(home, away, tv_broadcasts=[], n_sims=100, rng=rng)
    game_data = calculate_excitement_score(game)
    score = game_data["final_excitement_score"]
    label = sort_excitement_score(score)
    print(f"{home} vs {away}: {score:.2f} -> {label}")
    print(f"game:{game}")
    print(f"data:{game_data}")
    assert label == expected_label
