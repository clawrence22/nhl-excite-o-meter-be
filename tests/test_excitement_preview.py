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
        goals_for_low=goals_for,
        goals_for_high=goals_for,
        xg_for=xg_for,
        xg_for_low=xg_for,
        xg_for_high=xg_for,
        hits_for=hits_for,
        hits_for_low=hits_for,
        hits_for_high=hits_for,
        hdc_for=hdc_for,
        hdc_for_low=hdc_for,
        hdc_for_high=hdc_for,
        mdc_for=mdc_for,
        mdc_for_low=mdc_for,
        mdc_for_high=mdc_for,
    )


PROFILES = {
    "EDM": make_rates(goals_for=4.1, xg_for=3.5, hits_for=19.0, hdc_for=10.5, mdc_for=14.0),
    "TOR": make_rates(goals_for=3.8, xg_for=3.3, hits_for=18.5, hdc_for=9.8, mdc_for=13.1),
    "NSH": make_rates(goals_for=2.4, xg_for=2.3, hits_for=18.0, hdc_for=6.0, mdc_for=9.0),
    "MIN": make_rates(goals_for=2.5, xg_for=2.4, hits_for=19.0, hdc_for=6.3, mdc_for=9.1),
    "VGK": make_rates(goals_for=3.0, xg_for=2.8, hits_for=24.0, hdc_for=7.5, mdc_for=11.0),
    "NYI": make_rates(goals_for=2.7, xg_for=2.6, hits_for=23.0, hdc_for=7.0, mdc_for=10.2),
    "NYR": make_rates(goals_for=3.6, xg_for=2.8, hits_for=19.0, hdc_for=8.5, mdc_for=11.0),
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
        ("VGK", "NYI", "Mid"),
        ("NYR", "SJS", "Buzzin"),
    ],
)
def test_excitement_label_for_matchup(home, away, expected_label):
    rng = np.random.default_rng(12345)
    game = preview.simulate_preview(home, away, tv_broadcasts=[], n_sims=100, rng=rng)
    score = calculate_excitement_score(game)["final_excitement_score"]
    label = sort_excitement_score(score)
    print(f"{home} vs {away}: {score:.2f} -> {label}")
    print(f"Actual {label} == Expected {expected_label}")
    assert label == expected_label
