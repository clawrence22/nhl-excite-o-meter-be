import requests
import db
import preview_excitement_score
import logging
import logging
import sys
from dataclasses import dataclass
from typing import Dict

import numpy as np

from db import get_recent_team_stats, get_league_averages
from preview_excitement_score import calculate_excitement_score, sort_excitement_score

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def get_data_from_nhl(game_id):
    logger.info(f"Getting teams for game {game_id}")
    nhl_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    response = requests.get(nhl_url)
    data = response.json()
    home_tla = data["homeTeam"]["abbrev"]
    away_tla = data["awayTeam"]["abbrev"]
    tv_broadcasts = data["tvBroadcasts"]

    return home_tla,away_tla,tv_broadcasts

def get_game_ids(date):
    nhl_url = f"https://api-web.nhle.com/v1/schedule/{date}"
    response = requests.get(nhl_url)
    data = response.json()
    games = data["gameWeek"][0]["games"]

    game_ids = []
    for game in games:
        game_ids.append(game["id"])

    return game_ids

def generate_date_preview(date):
    games = get_game_ids(date)
    preview_data = {}
    
    for game_id in games:
        tmp_game_data = generate_game_preview(game_id)
        if tmp_game_data != {}:
            preview_data[game_id] = tmp_game_data
            continue
    
    if len(preview_data) == 0:
        return {"000001":"No Games Today"}

    logger.debug(f"preview_data:{preview_data}")
    return preview_data

def sort_broadcast_data(tv_broadcasts):
    broadcast_data = []
    for broadcast in tv_broadcasts:
        market = "Stream"
        if broadcast["market"] == "H":
            market = "Home"
        elif broadcast["market"] == "A":
            market = "Away"
        elif broadcast["market"] == "N":
            market = "National"
        broadcast_data.append({"network": broadcast["network"], "market": market})
    
    return broadcast_data


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@dataclass
class TeamRates:
    games_played: int
    goals_for: float
    goals_against: float
    xg_for: float
    xg_against: float
    hits_for: float
    hits_against: float
    hdc_for: float
    hdc_against: float
    mdc_for: float
    mdc_against: float


def _build_team_rates(team_tla: str, lookback_games: int) -> TeamRates:
    recent = get_recent_team_stats(team_tla, lookback_games) or {}
    recent_games = int(recent.get("games_played") or 0)
    if recent_games == 0:
        return TeamRates(
            games_played=0,
            goals_for=0.0,
            goals_against=0.0,
            xg_for=0.0,
            xg_against=0.0,
            hits_for=0.0,
            hits_against=0.0,
            hdc_for=0.0,
            hdc_against=0.0,
            mdc_for=0.0,
            mdc_against=0.0,
        )

    goals_for = recent.get("goals_for_avg")
    xg_for = recent.get("xg_for_avg")
    hits_for = recent.get("hits_for_avg")
    hdc_for = recent.get("hdc_for_avg")
    mdc_for = recent.get("mdc_for_avg")

    goals_against = recent.get("goals_against_avg")
    xg_against = recent.get("xg_against_avg")
    hits_against = recent.get("hits_against_avg")
    hdc_against = recent.get("hdc_against_avg")
    mdc_against = recent.get("mdc_against_avg")
    return TeamRates(
        games_played=recent_games,
        goals_for=goals_for or 0.0,
        goals_against=goals_against or 0.0,
        xg_for=xg_for or 0.0,
        xg_against=xg_against or 0.0,
        hits_for=hits_for or 0.0,
        hits_against=hits_against or 0.0,
        hdc_for=hdc_for or 0.0,
        hdc_against=hdc_against or 0.0,
        mdc_for=mdc_for or 0.0,
        mdc_against=mdc_against or 0.0,
    )


def _expected_lambda(
    off_rate: float,
    def_rate: float,
    off_weight: float = 1.0,
    def_weight: float = 1.0,
) -> float:
    if off_rate <= 0 and def_rate <= 0:
        return 0.01
    if off_rate <= 0:
        return max(0.01, def_rate)
    if def_rate <= 0:
        return max(0.01, off_rate)
    total_weight = max(0.01, off_weight + def_weight)
    return max(0.01, (off_rate * off_weight + def_rate * def_weight) / total_weight)

def _blend_toward_league(value: float, league_value: float, blend: float) -> float:
    if league_value is None:
        return value
    return (value * (1.0 - blend)) + (league_value * blend)


def simulate_preview(
    home_tla: str,
    away_tla: str,
    tv_broadcasts=None,
    lookback_games: int = 10,
    n_sims: int = 1000,
    off_weight: float = 1.0,
    def_weight: float = 1.0,
    league_blend: float = 0.27,
) -> Dict:
    home = _build_team_rates(home_tla, lookback_games)
    away = _build_team_rates(away_tla, lookback_games)

    home_goals_against = away.goals_against
    away_goals_against = home.goals_against
    home_xg_against = away.xg_against
    away_xg_against = home.xg_against
    home_hits_against = away.hits_against
    away_hits_against = home.hits_against
    home_hdc_against = away.hdc_against
    away_hdc_against = home.hdc_against
    home_mdc_against = away.mdc_against
    away_mdc_against = home.mdc_against

    lambdas = {
        "home_goals": _expected_lambda(home.goals_for, home_goals_against, off_weight, def_weight),
        "away_goals": _expected_lambda(away.goals_for, away_goals_against, off_weight, def_weight),
        "home_xg": _expected_lambda(home.xg_for, home_xg_against, off_weight, def_weight),
        "away_xg": _expected_lambda(away.xg_for, away_xg_against, off_weight, def_weight),
        "home_hits": _expected_lambda(home.hits_for, home_hits_against, off_weight, def_weight),
        "away_hits": _expected_lambda(away.hits_for, away_hits_against, off_weight, def_weight),
        "home_hdc": _expected_lambda(home.hdc_for, home_hdc_against, off_weight, def_weight),
        "away_hdc": _expected_lambda(away.hdc_for, away_hdc_against, off_weight, def_weight),
        "home_mdc": _expected_lambda(home.mdc_for, home_mdc_against, off_weight, def_weight),
        "away_mdc": _expected_lambda(away.mdc_for, away_mdc_against, off_weight, def_weight),
    }

    logger.info("home rates: %s", home)
    logger.info("away rates: %s", away)
    logger.info("lambdas: %s", lambdas)


    rng = np.random.default_rng()

    home_goals = rng.poisson(lambdas["home_goals"], n_sims)
    away_goals = rng.poisson(lambdas["away_goals"], n_sims)
    home_xg = rng.poisson(lambdas["home_xg"], n_sims).astype(float)
    away_xg = rng.poisson(lambdas["away_xg"], n_sims).astype(float)
    home_hits = rng.poisson(lambdas["home_hits"], n_sims)
    away_hits = rng.poisson(lambdas["away_hits"], n_sims)
    home_hdc = rng.poisson(lambdas["home_hdc"], n_sims)
    away_hdc = rng.poisson(lambdas["away_hdc"], n_sims)
    home_mdc = rng.poisson(lambdas["home_mdc"], n_sims)
    away_mdc = rng.poisson(lambdas["away_mdc"], n_sims)

    away_goals_mean = float(np.mean(away_goals))
    away_hdc_mean = float(np.mean(away_hdc))
    away_hits_mean = float(np.mean(away_hits))
    away_mdc_mean = float(np.mean(away_mdc))
    away_xg_mean = float(np.mean(away_xg))
    home_goals_mean = float(np.mean(home_goals))
    home_hdc_mean = float(np.mean(home_hdc))
    home_hits_mean = float(np.mean(home_hits))
    home_mdc_mean = float(np.mean(home_mdc))
    home_xg_mean = float(np.mean(home_xg))

    league_avgs = get_league_averages() or {}
    league_goals = league_avgs.get("goals_avg")
    league_xg = league_avgs.get("xg_avg")
    league_hits = league_avgs.get("hits_avg")
    league_hdc = league_avgs.get("hdc_avg")
    league_mdc = league_avgs.get("mdc_avg")

    away_goals_mean = _blend_toward_league(away_goals_mean, league_goals, league_blend)
    home_goals_mean = _blend_toward_league(home_goals_mean, league_goals, league_blend)
    away_xg_mean = _blend_toward_league(away_xg_mean, league_xg, league_blend)
    home_xg_mean = _blend_toward_league(home_xg_mean, league_xg, league_blend)
    away_hits_mean = _blend_toward_league(away_hits_mean, league_hits, league_blend)
    home_hits_mean = _blend_toward_league(home_hits_mean, league_hits, league_blend)
    away_hdc_mean = _blend_toward_league(away_hdc_mean, league_hdc, league_blend)
    home_hdc_mean = _blend_toward_league(home_hdc_mean, league_hdc, league_blend)
    away_mdc_mean = _blend_toward_league(away_mdc_mean, league_mdc, league_blend)
    home_mdc_mean = _blend_toward_league(home_mdc_mean, league_mdc, league_blend)

    preview_data = {
        "away_goals": round(away_goals_mean, 1),
        "away_hdc": round(away_hdc_mean, 1),
        "away_hits": round(away_hits_mean, 1),
        "away_mdc": round(away_mdc_mean, 1),
        "away_tla": away_tla,
        "away_xg": round(away_xg_mean, 1),
        "home_goals": round(home_goals_mean, 1),
        "home_hdc": round(home_hdc_mean, 1),
        "home_hits": round(home_hits_mean, 1),
        "home_mdc": round(home_mdc_mean, 1),
        "home_tla": home_tla,
        "home_xg": round(home_xg_mean, 1),
        "tv_broadcast": sort_broadcast_data(tv_broadcasts or []),
        "total_goals": round(away_goals_mean + home_goals_mean, 1),
        "total_hdc": round(away_hdc_mean + home_hdc_mean, 1),
        "total_hits": round(away_hits_mean + home_hits_mean, 1),
        "total_mdc": round(away_mdc_mean + home_mdc_mean, 1),
        "total_xg": round(away_xg_mean + home_xg_mean, 1),
        "period_time_seconds": 3600,
        "is_game_over": False,
        "period": "Preview",
    }

    return preview_data


def generate_game_preview(game_id):
    team_tlas = [ "ANA", "BOS", "BUF", "CAR", "CBJ",
                  "CGY", "CHI", "COL", "DAL", "DET", 
                  "EDM", "FLA", "LAK", "MIN", "MTL", 
                  "NJD", "NSH", "NYI", "NYR", "OTT", 
                  "PHI", "PIT", "SEA", "SJS", "STL", 
                  "TBL", "TOR", "UTA", "VAN", "VGK", 
                  "WPG", "WSH"]
    
    home_tla,away_tla,tv_broadcasts = get_data_from_nhl(game_id)

    if home_tla not in team_tlas or away_tla not in team_tlas:
        return {}

    preview_data = simulate_preview(home_tla, away_tla, tv_broadcasts=tv_broadcasts)
    
    excitment_data = calculate_excitement_score(preview_data)

    preview_data["excitement_level"] =  sort_excitement_score(excitment_data["final_excitement_score"])
    preview_data["excitement_score"] = excitment_data["final_excitement_score"]
    preview_data["excitement_modifiers"] = excitment_data["modifiers"]
    preview_data["excitement_makeup"] = excitment_data["excitement_makeup"]

    return preview_data
