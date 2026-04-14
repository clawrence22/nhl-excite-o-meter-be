import requests
import logging
from typing import Dict

from datetime import datetime

from logging_config import setup_logging
import pytz
import db

import numpy as np

setup_logging()
logger = logging.getLogger(__name__)

GAME_EXCITEMENT_SCORE_LEVELS = [10, 25.0, 40.0, 54.25]
TEAM_EXCITEMENT_SCORE_LEVELS = [0 ,4.80,6.00, 8.00]

MID_THRESHOLD_NORMAL = 25
BUZZ_THRESHOLD_NORMAL = 50.00
BURNER_THRESHOLD_NORMAL = 75.00

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

    game_ids = [game["id"] for game in games ]

    return game_ids

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



def normalize_score(score,thresholds):
    
    # 1. Define your input thresholds (must be sorted)
    xp = thresholds

    # 2. Define the target normalized mapping for each threshold
    # Here, each threshold is mapped to an equal step (0, 0.25, 0.5, 0.75, 1.0)
    fp = [10,MID_THRESHOLD_NORMAL, BUZZ_THRESHOLD_NORMAL, BURNER_THRESHOLD_NORMAL]

    # 3. Perform piecewise interpolation
    normalized_values = np.interp([score], xp, fp)

    return normalized_values[0]


def sort_excitement_score(excitement_score):

    if excitement_score >= BURNER_THRESHOLD_NORMAL:
        return "Barn Burner"
    elif excitement_score >= BUZZ_THRESHOLD_NORMAL:
        return "Buzzin"
    elif excitement_score >= MID_THRESHOLD_NORMAL:
        return "Mid"
    elif excitement_score > 0.0:
        return "Meh"
    else:
        return "Too Early"

def calculate_excitement_score(home_team_excitement,away_team_excitement):

    TILT_PERCENT = 0.95
    TILT_PENALTY = 0.90

    avg_game_bump = 1.00
    raw_score = ((home_team_excitement + away_team_excitement)/2) * avg_game_bump

    home_per = home_team_excitement/raw_score
    away_per = away_team_excitement/raw_score

    potential_ice_tilt = (home_per > TILT_PERCENT or away_per > TILT_PERCENT)

    if potential_ice_tilt:
        raw_score *= TILT_PENALTY 

    return raw_score


def simulate_preview(
    home_avg: str,
    away_avg: str,
) -> Dict:
    
    logger.info(f"home_avg:{home_avg}")
    logger.info(f"away_avg:{away_avg}")

    home_excitment_avg = home_avg["team_excitement_avg"]
    logger.info(f"home_excitment_avg:{home_excitment_avg}")
    home_excitement_level = sort_excitement_score(home_excitment_avg)
    
    away_excitment_avg = away_avg["team_excitement_avg"]
    away_excitement_level = sort_excitement_score(away_excitment_avg)


    raw_excitment_score = calculate_excitement_score(home_excitment_avg,away_excitment_avg)
    excitment_score = normalize_score(raw_excitment_score,GAME_EXCITEMENT_SCORE_LEVELS)
    excitement_level = sort_excitement_score(excitment_score)

    preview_data = {
        "away_goals": round(away_avg["goals_for_avg"], 0),
        "away_hdc": round(away_avg["hdc_for_avg"], 0),
        "away_hits": round(away_avg["hits_for_avg"], 0),
        "away_mdc": round(away_avg["mdc_for_avg"], 0),
        "away_excitement": round(away_excitment_avg, 2),
        "away_excitement_level": away_excitement_level,
        "home_goals": round(home_avg["goals_for_avg"], 0),
        "home_hdc": round(home_avg["hdc_for_avg"], 0),
        "home_hits": round(home_avg["hits_for_avg"], 0),
        "home_mdc": round(home_avg["mdc_for_avg"], 0),
        "home_excitement": round(home_excitment_avg, 2),
        "home_excitement_level": home_excitement_level,
        "is_game_over": False,
        "period": "Preview",
        "excitement_level": excitement_level,
        "excitement_score": excitment_score,
        "raw_excitment_score":raw_excitment_score
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
    try:
        home_team_avg = db.get_recent_team_stats(home_tla,10)
        away_team_avg = db.get_recent_team_stats(away_tla,10)
    except Exception as ex:
        logger.error(f"Error Getting team stats:{ex}")
        raise ex

    preview_data = simulate_preview(home_team_avg,away_team_avg)

    preview_data["home_tla"] = home_tla
    preview_data["away_tla"] = away_tla
    preview_data["tv_broadcast"] = sort_broadcast_data(tv_broadcasts)
    preview_data["start_time"] = start_time
    
    logger.debug(f"preview_data:{preview_data}")

    return preview_data
