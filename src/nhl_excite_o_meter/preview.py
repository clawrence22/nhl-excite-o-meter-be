import requests
import logging
from typing import Dict

from datetime import datetime

import numpy as np

from .teamrates import build_team_rates

from .preview_excitement_score import calculate_excitement_score

from .logging_config import setup_logging
import pytz

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
    start_time = data["startTimeUTC"]
    
    time_format = "%Y-%m-%dT%H:%M:%SZ"
    output_format = "%I:%M %p %Z"

    naive_utc_dt = datetime.strptime(start_time, time_format)

    utc_dt = pytz.utc.localize(naive_utc_dt) 

    est_timezone = pytz.timezone('America/New_York')

    est_dt = utc_dt.astimezone(est_timezone)
    
    start_time = est_dt.strftime(output_format)

    return home_tla,away_tla,tv_broadcasts,start_time

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

def get_random_poisson_value(
    value: float = 0.0,
    sims: int = 10000,
    rng=None,
) -> float:
    # Generate a random value using poisson function
    if rng is None:
        rng = np.random.default_rng()
    return rng.poisson(value, sims).astype(float)

def get_distributed_value(
    value: float = 0.0,
    std_deviate: float = 4.5,
    sims: int = 10000,
    rng=None,
) -> float:
    if rng is None:
        rng = np.random.default_rng()
    sim_value = rng.normal(value, std_deviate, sims)
    sim_value = np.maximum(0,np.round(sim_value))
    sim_value = np.percentile(sim_value, [25,75])
    return sim_value

def simulate_preview(
    home_tla: str,
    away_tla: str,
    tv_broadcasts=None,
    lookback_games: int = 5,
    n_sims: int = 10000,
    start_time = "Missing Start Time",
    rng=None,
) -> Dict:
    if rng is None:
        rng = np.random.default_rng()
    home = build_team_rates(home_tla, lookback_games)
    away = build_team_rates(away_tla, lookback_games)

    


    ##Sim how many goals,XG, hits and chances each team may get based on low,highs and avg

    home_goals = get_random_poisson_value(home.goals_for, n_sims, rng=rng)
    away_goals = get_random_poisson_value(away.goals_for, n_sims, rng=rng)
    home_xg = get_random_poisson_value(home.xg_for, n_sims, rng=rng)
    away_xg = get_random_poisson_value(away.xg_for, n_sims, rng=rng)

    home_hdc = get_distributed_value(home.hdc_for, sims=n_sims, rng=rng)
    away_hdc = get_distributed_value(away.hdc_for, sims=n_sims, rng=rng)
    home_mdc = get_distributed_value(home.mdc_for, sims=n_sims, rng=rng)
    away_mdc = get_distributed_value(away.mdc_for, sims=n_sims, rng=rng)
    home_hits = get_distributed_value(home.hits_for, sims=n_sims, rng=rng)
    away_hits = get_distributed_value(away.hits_for, sims=n_sims, rng=rng)


    #average out sim results
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
        "start_time" : start_time
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
    
    home_tla,away_tla,tv_broadcasts,start_time = get_data_from_nhl(game_id)

    if home_tla not in team_tlas or away_tla not in team_tlas:
        return {}

    preview_data = simulate_preview(home_tla, away_tla, tv_broadcasts=tv_broadcasts)
    
    excitment_data = calculate_excitement_score(preview_data)

    preview_data["excitement_level"] =  excitment_data["excitement_level"]
    preview_data["excitement_score"] = excitment_data["final_excitement_score"]
    preview_data["excitement_modifiers"] = excitment_data["modifiers"]
    preview_data["excitement_makeup"] = excitment_data["excitement_makeup"]
    preview_data["start_time"] = start_time
    
    logger.debug(f"preview_data:{preview_data}")

    return preview_data
