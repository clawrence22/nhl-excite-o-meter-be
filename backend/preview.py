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


AVG_GAME_BUMP = db.get_game_excitement_bonus_average(100) 

GAME_EXCITEMENT_SCORE_LEVELS = [10, 20.0, 35.0, 40.0, 50.0]
TEAM_EXCITEMENT_SCORE_LEVELS = [3,6,11.67,13.3,17]

MID_THRESHOLD_NORMAL = 33.00
BUZZ_THRESHOLD_NORMAL = 66.00
BURNER_THRESHOLD_NORMAL = 80.00


def get_data_from_nhl(game_id):
    logger.info(f"Getting teams for game {game_id}")
    nhl_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
    response = requests.get(nhl_url)
    data = response.json()

    nhl_data = {
        "home_tla": data["homeTeam"]["abbrev"],
        "away_tla": data["awayTeam"]["abbrev"],
        "home_team_name": data["homeTeam"]["commonName"]["default"],
        "away_team_name": data["awayTeam"]["commonName"]["default"],
        "tv_broadcasts": data["tvBroadcasts"],
        "start_time_utc": data["startTimeUTC"]
    }

    return nhl_data

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
    fp = [10,MID_THRESHOLD_NORMAL, BUZZ_THRESHOLD_NORMAL, BURNER_THRESHOLD_NORMAL,100]

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
    return ((home_team_excitement + away_team_excitement)) * AVG_GAME_BUMP



def simulate_preview(
    home_avg: str,
    away_avg: str,
) -> Dict:
    
    logger.info(f"home_avg:{home_avg}")
    logger.info(f"away_avg:{away_avg}")

    home_excitment_avg = home_avg["excitement_avg"]
    home_excitment_norm = normalize_score(home_excitment_avg, TEAM_EXCITEMENT_SCORE_LEVELS)
    logger.info(f"home_excitment_avg:{home_excitment_avg}")
    home_excitement_level = sort_excitement_score(home_excitment_norm)

    home_team_excitement = {"raw_excitement_score": home_excitment_avg, "excitement_score": home_excitment_norm,"excitement_level":home_excitement_level,"goal_score": 0.0,"hdc_score": 0.0, "mdc_score": 0.0}
    
    away_excitment_avg = away_avg["excitement_avg"]
    away_excitment_norm = normalize_score(home_excitment_avg, TEAM_EXCITEMENT_SCORE_LEVELS)
    away_excitement_level = sort_excitement_score(away_excitment_norm)

    away_team_excitement = {"raw_excitement_score": away_excitment_avg, "excitement_score": away_excitment_norm,"excitement_level":away_excitement_level,"goal_score": 0.0,"hdc_score": 0.0, "mdc_score": 0.0}

    raw_excitment_score = calculate_excitement_score(home_excitment_avg,away_excitment_avg)
    excitment_score = normalize_score(raw_excitment_score,GAME_EXCITEMENT_SCORE_LEVELS)
    excitement_level = sort_excitement_score(excitment_score)

    game_excitement = {"excitement_score":excitment_score,"excitement_level":excitement_level,"raw_score":raw_excitment_score}

    preview_data = {
        "home": {"hdc": round(home_avg["hdc_avg"], 0), "mdc": round(home_avg["mdc_avg"], 0), 
                 "goals": round(home_avg["goals_avg"], 0), "hits": round(home_avg["hits_avg"], 0),
                 "ovr_excitment" :home_team_excitement,"pulse_excitment" :{"excitement_score":0.0,"excitement_level":"Too Early"} },
        "away": {"hdc": round(away_avg["hdc_avg"], 0), "mdc": round(away_avg["mdc_avg"], 0), 
                 "goals": round(away_avg["goals_avg"], 0), "hits": round(away_avg["hits_avg"], 0),
                 "ovr_excitment" :away_team_excitement,"pulse_excitment" :{"excitement_score":0.0,"excitement_level":"Too Early"}  },
        
        "game": { "ovr_excitment":game_excitement , "pulse_excitment" :{"excitement_score":0.0,"excitement_level":"Too Early"} }
    }
    return preview_data


def generate_game_preview(game_id,playoffData,game_date = ""):
    team_tlas = [ "ANA", "BOS", "BUF", "CAR", "CBJ",
                  "CGY", "CHI", "COL", "DAL", "DET", 
                  "EDM", "FLA", "LAK", "MIN", "MTL", 
                  "NJD", "NSH", "NYI", "NYR", "OTT", 
                  "PHI", "PIT", "SEA", "SJS", "STL", 
                  "TBL", "TOR", "UTA", "VAN", "VGK", 
                  "WPG", "WSH"]
    
    nhl_data = get_data_from_nhl(game_id)

    if nhl_data["home_tla"] not in team_tlas or nhl_data["away_tla"] not in team_tlas:
        return {}
    try:
        num_games_series = 5 if playoffData == None else (playoffData["gameNumberOfSeries"] - 1)
        series_avg = db.get_series_average(nhl_data["home_tla"], nhl_data["away_tla"], num_games_series)
        home_team_avg = series_avg.get(nhl_data["home_tla"])
        away_team_avg = series_avg.get(nhl_data["away_tla"])
    except Exception as ex:
        logger.error(f"Error Getting team stats:{ex}")
        raise ex
    logger.info(f"home_team_avg:{home_team_avg}")
    logger.info(f"away_team_avg:{away_team_avg}")
    preview_data = simulate_preview(home_team_avg,away_team_avg)

    preview_data["home"]["tla"] = nhl_data["home_tla"]
    preview_data["home"]["name"] = nhl_data["home_team_name"]
    preview_data["away"]["tla"] = nhl_data["away_tla"]
    preview_data["away"]["name"] = nhl_data["away_team_name"]

    preview_data["game"]["tv_broadcast"] = sort_broadcast_data(nhl_data["tv_broadcasts"])
    preview_data["game"]["start_time"] = nhl_data["start_time_utc"]
    preview_data["game"]["game_date"] = game_date
    preview_data["game"]["period"] = "Preview"
    preview_data["game"]["is_game_over"] = False
    preview_data["game"]["intermission"] = False

    playoff_data = {}

    if playoffData is None:
        playoff_data["is_playoff"] = False
        playoff_data["game_seven"] = False
        playoff_data["elimination_game"] = False
        playoff_data["cup_final"] = False
    else:
        playoff_data["is_playoff"] = True
        playoff_data["game_seven"] = (playoffData["gameNumberOfSeries"] == 7)
        playoff_data["elimination_game"] = (playoffData["topSeedWins"] == 3 or playoffData["bottomSeedWins"] == 3 )
        playoff_data["cup_final"] = (playoffData["round"] == 4)
       
    
    preview_data["playoffs"] = playoff_data
    preview_data["playoffs"]["data"] = playoffData
    preview_data["excitement"] = {"modifiers": {}, "bonuses": {"avg_game_bump": AVG_GAME_BUMP}}
    
    logger.debug(f"preview_data:{preview_data}")

    return preview_data
