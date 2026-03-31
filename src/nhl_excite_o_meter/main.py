"""
Flask application wiring for the NHL Excite-o-Meter API (class-based).

Endpoints
---------
GET /healthz
GET /excitement/<date>

Return shape for /excitement/<gamePk>
------------------------------------
The endpoint returns a JSON object with several keys:
- score_raw: raw, time-decayed excitement sum (no sigmoid normalization).
- raw: same numeric as score_raw for clarity.
- context: snapshot of the game state (period, inOT, time remaining, home/away goals, applied context multiplier).
- sampledEvents: up to the last 30 play events that contributed to the score, showing type, tags (GOAL, HDC, HITx, etc.), points, context multiplier, decay factor, and contribution.
- params: the configuration parameters used when scoring (half-life, event cap, spacing, and weights).

Design notes
------------
- This file is intentionally thin: routing + dependency wiring only.
- The heavy lifting (fetching & scoring) lives in the `exciteo/` package.
- You can swap implementations (e.g., different client or scorer) without touching routes.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import atexit
from datetime import datetime
from threading import Lock
from typing import Any, Tuple
import time
import traceback
import requests
import json

from flask import Flask, jsonify, request, make_response, g
from flask_cors import CORS

from .logging_config import setup_logging
from . import preview
from . import db

def get_game_ids(date):
    nhl_url = f"https://api-web.nhle.com/v1/schedule/{date}"
    response = requests.get(nhl_url)
    data = response.json()
    games = data["gameWeek"][0]["games"]
    
    game_ids = [game["id"] for game in games ]
    

    return (game_ids)

def create_app() -> Flask:
    """Assemble the Flask API with shared dependencies.

    New contributors: this function is where we wire the HTTP surface to the
    scoring and preview engines. It owns CORS policy, dependency injection, and
    an initial cache clear so the recent-game preview stays warm.
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    app = Flask(__name__)
    # add near the top of create_app(), after app = Flask(__name__)
    ALLOWED_ORIGINS = {
        "https://hockeyexcitometer.com",
        "http://localhost:8080",
        "http://localhost:3000",
    }

    db.init_db_pool()
    atexit.register(db.close_db_pool)

    @app.after_request
    def add_cors_headers(resp):
        origin = request.headers.get("Origin")
        if origin in ALLOWED_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Vary"] = "Origin"
            # If you don't send cookies/Authorization from the browser, set this to "false" and remove credentials support.
            resp.headers["Access-Control-Allow-Credentials"] = "false"
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    # handle preflights globally
    @app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
    @app.route("/<path:path>", methods=["OPTIONS"])
    def cors_preflight(path):
        resp = make_response("", 204)
        return add_cors_headers(resp)

    CORS(app, 
     origins=["https://hockeyexcitometer.com", "http://localhost:8080", "http://localhost:3000"],
     resources={r"/*": {"origins": ["https://hockeyexcitometer.com", "http://localhost:8080", "http://localhost:3000"]}})
    
    logger.info("Flask app initialized")

    @app.get("/healthz")
    def healthz():
        return jsonify({"ImAlive:":"Im Still Alive"})

    @app.get("/excitement_date/<game_date>")
    def excitement_date(game_date: str):
        logger.info(f"Processing excitement for the date {game_date}")
        game_ids = get_game_ids(game_date)
        games_data = {}
        
        try:
            for game_id in game_ids:
                game_data = db.get_game_data(game_id)
                if game_data is None:
                    logger.info(f"Game {game_id} not found in db, assuming future game, getting preview")
                    game_data = preview.generate_game_preview(game_id)
                games_data[game_id] = game_data
            
            logger.info(f"games_data:{games_data}")
            
            return jsonify(games_data)   
        
        except Exception as e:
            logger.error(f"Error processing games for date {game_date}: {e}")
            traceback.print_exc(limit=None, file=None, chain=True)
            return jsonify({"error": "Internal error", "detail": str(e)}), 500
        
        
    @app.get("/excitement_game/<game_id>")
    def excitement_game(game_id: int):
        logger.info(f"Processing excitement for the game {game_id}")
        try:
            game_data = db.get_game_data(game_id)
            if game_data is None:
                logger.info(f"Game {game_id} not found in db, assuming future game, getting preview")
                game_data = preview.generate_game_preview(game_id)
            
            return jsonify(game_data)
        except Exception as e:
            logger.error(f"Error processing game {game_id}: {e}")
            traceback.print_exc(limit=None, file=None, chain=True)
            return jsonify({"error": "Internal error", "detail": str(e)}), 500
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001)
