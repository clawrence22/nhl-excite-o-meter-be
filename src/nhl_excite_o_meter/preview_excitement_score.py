from math import ceil
import logging
import sys

MIN_GAME_ELAPSED_SECONDS = 300

NEXT_GOAL_WINS_BONUS = 3.66

TIE_GAME_BONUS = 5.0
ONE_GOAL_GAME_BONUS = 2.75
TWO_GOAL_GAME_BONUS = 1.66
GOALS_EXCITEMENT_THRESHOLD = 6.0
GOALS_EXP_BASE = 1.40
ICE_TILT_GOAL_THRESHOLD = 0.50
ICE_TILT_GOAL_PENALTY_BASE = 1.25
ICE_TILT_GOAL_PENALTY_DIFF_UNIT = 0.55
LOW_SCORE_CLOSE_GAME_PENALTY = 0.50

HDC_EXCITEMENT_THRESHOLD = 30
HDC_WEIGHT = 0.35
MDC_WEIGHT = 0.25
CHANCE_TILT_PERCENT = 66.0
CHANCE_TILT_PENALTY = 0.90

HIGH_HITS_THRESHOLD = 60
HIT_WEIGHT = .25

ICE_TILT_PENALTY = 0.5

XG_WEIGHT = .66

TOTAL_GAME_TIME_SECONDS = 3600

EXCITMENT_SCORE_MID_THRESHOLD = 33.20
EXCITMENT_SCORE_BUZZIN_THRESHOLD = 35.55
EXCITMENT_SCORE_BARN_BURNER_THRESHOLD = 39.10

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
logger = logging.getLogger(__name__)


def sort_excitement_score(excitement_score):
    if excitement_score >= EXCITMENT_SCORE_BARN_BURNER_THRESHOLD:
        return "Barn Burner"
    elif excitement_score >= EXCITMENT_SCORE_BUZZIN_THRESHOLD:
        return "Buzzin"
    elif excitement_score >= EXCITMENT_SCORE_MID_THRESHOLD:
        return "Mid"
    elif excitement_score == 0.0:
        return "Too Early"
    else:
        return "Meh"


def calculate_goal_score(home_goals, away_goals, total_goals):

    # Exponential scaling to emphasize higher-scoring games.
    goal_score = (pow(GOALS_EXP_BASE, total_goals))
    high_scoring_game = False
    ice_tilt = False

    goal_diff = abs(home_goals - away_goals)
    logger.info(f"GOAL DIFF: {goal_diff}")
    if total_goals >= GOALS_EXCITEMENT_THRESHOLD:
        high_scoring_game = True
    
    # Increase the penalty as the goal differential grows.
    if goal_diff >= ICE_TILT_GOAL_THRESHOLD:
        # Scale penalty by how far the goal diff exceeds the threshold.
        ice_tilt = True
        excess_diff = goal_diff - ICE_TILT_GOAL_THRESHOLD
        scaled_excess_diff = excess_diff / ICE_TILT_GOAL_PENALTY_DIFF_UNIT
        ice_tilt_penalty = pow(ICE_TILT_GOAL_PENALTY_BASE, -(scaled_excess_diff + 1))
        goal_score = goal_score * ice_tilt_penalty
        
       

    return round(goal_score,2),high_scoring_game, ice_tilt

def calculate_close_game_score(period, period_time_remaining, is_game_over, home_goals, away_goals):

    close_game_score = 1.0
    close_game = False
    next_goal_wins = False
    
    #only check for close games if someone has scored 
    if home_goals > 0 or away_goals > 0:
        goal_diff = abs(home_goals - away_goals)

        TIE_GAME_THRESHOLD = 0.25
        ONE_GOAL_THRESHOLD = .5
        TWO_GOAL_THRESHOLD = 1.0

        if goal_diff <= TWO_GOAL_THRESHOLD:
            close_game = True

        if goal_diff <= TIE_GAME_THRESHOLD:
            close_game_score = TIE_GAME_BONUS
        
        elif goal_diff <= ONE_GOAL_THRESHOLD:
            close_game_score = ONE_GOAL_GAME_BONUS

        elif goal_diff <= TWO_GOAL_THRESHOLD:
            close_game_score = TWO_GOAL_GAME_BONUS

    return round(close_game_score,2), close_game, next_goal_wins
        
def calculate_chances_score(home_hdc, away_hdc, total_hdc):
    
    frenzy = False
    
    if total_hdc == 0:
        ice_tilt = False
    else:
        ice_tilt = ((float(home_hdc / total_hdc) * 100) > CHANCE_TILT_PERCENT) or ((float(away_hdc / total_hdc) * 100) > CHANCE_TILT_PERCENT)
    
    hdc_chances_score = total_hdc * HDC_WEIGHT
    mdc_chances_score = total_hdc * MDC_WEIGHT



    if total_hdc > HDC_EXCITEMENT_THRESHOLD and not ice_tilt:
        frenzy = True

    if ice_tilt:
        hdc_chances_score *= CHANCE_TILT_PENALTY

    chances_score = hdc_chances_score + mdc_chances_score

    return round(chances_score,2), frenzy, ice_tilt

def calculate_hits_score(total_hits):
    hits_score = total_hits * HIT_WEIGHT
    high_hit_game = False
    
    if total_hits > HIGH_HITS_THRESHOLD:
        high_hit_game = True

    
    return round(hits_score,2) , high_hit_game

def weight_xg(xg):
    return ceil(round(xg/2, 2)) * XG_WEIGHT

def calculate_game_elapsed(period, period_time_remaining):
    
    if period == "Preview" or period > 3:
        return TOTAL_GAME_TIME_SECONDS
    else:
        return ((1200 - period_time_remaining) + ((period - 1) * 1200))



def calculate_game_elapsed_adjustment(time_elapsed_seconds):
    
    adjustment = 1.0

    if time_elapsed_seconds <= 1200:
        adjustment  = 3.0
    elif time_elapsed_seconds <= 2400:
        adjustment = 1.5
    
    return adjustment

def calculate_excitement_score(game_data):

    
    final_excitement_score = 0.0

    modifiers = {
        "high-scoring" : False,
        "close-game" : False,
        "hit-fest" : False,
        "frenzy" : False,
        "next-goal-wins" : False,
        "ice-tilt" : False
    }

    excitement_makeup = {
        "chance_score" : 0.0,
        "goal_score" : 0.0,
        "xg_score" : 0.0,
        "hits_score" : 0.0
    }

    time_elapsed_seconds = calculate_game_elapsed(game_data["period"], game_data["period_time_seconds"])

    if time_elapsed_seconds > MIN_GAME_ELAPSED_SECONDS:
        
        game_prorate_adjustment = calculate_game_elapsed_adjustment(time_elapsed_seconds)
        
        home_hdc = game_data["home_hdc"] * game_prorate_adjustment
        away_hdc = game_data["away_hdc"] * game_prorate_adjustment
        total_hdc = game_data["total_hdc"] * game_prorate_adjustment

        home_goals = game_data["home_goals"] * game_prorate_adjustment
        away_goals = game_data["away_goals"] * game_prorate_adjustment
        total_goals = game_data["total_goals"] * game_prorate_adjustment

        home_xg = weight_xg(game_data["home_xg"] * game_prorate_adjustment)
        away_xg = weight_xg(game_data["away_xg"] * game_prorate_adjustment)
        total_xg = weight_xg(game_data["total_xg"] * game_prorate_adjustment)

        total_hits = game_data["total_hits"] * game_prorate_adjustment

        chances_score,frenzy_game,chances_ice_tilt = calculate_chances_score(home_hdc, away_hdc, total_hdc)
        goals_score,high_scoring_game,goals_ice_tilt = calculate_goal_score(home_goals, away_goals, total_goals)
        xg_score,high_xg_game,xgoals_ice_tilt = calculate_goal_score(home_xg, away_xg, total_xg)
        hit_score,hit_fest_game = calculate_hits_score(total_hits)
        close_game_score,close_game,next_goal_wins = calculate_close_game_score(game_data["period"],game_data["period_time_seconds"],game_data["is_game_over"],home_goals,away_goals)

        modifiers = {
        "high-scoring" : high_scoring_game,
        "close-game" : close_game,
        "hit-fest" : hit_fest_game, 
        "frenzy" : frenzy_game,
        "next-goal-wins" : next_goal_wins,
        "ice-tilt" : (chances_ice_tilt or goals_ice_tilt or xgoals_ice_tilt),
        "chances_ice_tilt" : chances_ice_tilt,
        "goals_ice_tilt" : goals_ice_tilt,
        "xgoals_ice_tilt": xgoals_ice_tilt
        }

        excitement_makeup["chance_score"] = chances_score
        excitement_makeup["goal_score"] = goals_score
        excitement_makeup["xg_score"] = xg_score
        excitement_makeup["hits_score"] = hit_score
        excitement_makeup["close_game_score"] = close_game_score

        final_excitement_score = close_game_score + chances_score + goals_score + xg_score + hit_score
        final_excitement_score = round(final_excitement_score/2,2) if modifiers["ice-tilt"]  else final_excitement_score
        logger.info(f"Final Excitement Score: {final_excitement_score}")
    
    else:
        logger.info(f"Game is too new to calculate excitement score. Seconds elapsed: {time_elapsed_seconds}")

    
    excitement_data = {"final_excitement_score": final_excitement_score, "modifiers" : modifiers,"excitement_makeup": excitement_makeup}
    

    return excitement_data
