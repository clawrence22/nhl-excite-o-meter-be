import os

os.environ["DB_HOST"]="dummy"
os.environ["DB_PORT"]="5432"
os.environ["DB_USER"]="dummy"
os.environ["DB_NAME"]="dummy"
os.environ["DB_REGION"]="us-east-1"
os.environ["DB_SSLMODE"]="require"

import preview
from preview import TeamRates
from preview_excitement_score import calculate_excitement_score, sort_excitement_score

preview.get_league_averages = lambda: {
    "goals_avg": 3.1, "xg_avg": 2.9, "hits_avg": 20.0, "hdc_avg": 8.0, "mdc_avg": 12.0
}


# class TeamRates(
#     games_played: int,
#     goals_for: float,
#     goals_against: float,
#     xg_for: float,
#     xg_against: float,
#     hits_for: float,
#     hits_against: float,
#     hdc_for: float,
#     hdc_against: float,
#     mdc_for: float,
#     mdc_against: float
# )


profiles = {
    "EDM": TeamRates(5,4.1,3.6,3.5,3.1,19.0,21.0,10.5,9.7,14.0,13.2),
    "TOR": TeamRates(5,3.8,3.4,3.3,3.0,18.5,20.5,9.8,9.1,13.1,12.8),
    "NSH": TeamRates(5,2.4,2.5,2.3,2.4,22.0,21.5,6.0,6.2,9.0,9.3),
    "MIN": TeamRates(5,2.5,2.6,2.4,2.5,21.0,20.0,6.3,6.4,9.1,9.0),
    "VGK": TeamRates(5,3.0,2.9,2.8,2.7,24.0,23.5,7.5,7.2,11.0,10.8),
    "NYI": TeamRates(5,2.7,2.8,2.6,2.6,23.0,22.5,7.0,7.1,10.2,10.1),
}
preview._build_team_rates = lambda team, _: profiles[team]

results = {}

for home, away in [("EDM","TOR"), ("NSH","MIN"), ("VGK","NYI")]:
    out = {}
    for _ in range(100):
        game = preview.simulate_preview(home, away, tv_broadcasts=[], n_sims=10)
        score = calculate_excitement_score(game)["final_excitement_score"]
        label = sort_excitement_score(score)
        out[label] = out.get(label, 0) + 1
    results[f"{away}@{home}"] = out

print(results)

