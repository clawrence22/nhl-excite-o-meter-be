import os
import logging
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import psycopg2
import traceback
import boto3

from .logging_config import setup_logging

DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_USER = os.environ["DB_USER"]
DB_NAME = os.environ["DB_NAME"]
DB_REGION = os.environ["DB_REGION"]
DB_SSLMODE = os.environ["DB_SSLMODE"]

setup_logging()
logger = logging.getLogger(__name__)


def _get_password():
    client = boto3.client("rds", region_name=DB_REGION)
    return client.generate_db_auth_token(
        DBHostname=DB_HOST,
        Port=DB_PORT,
        DBUsername=DB_USER,
        Region=DB_REGION,
    )


def _connect():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=_get_password(),
        sslmode=DB_SSLMODE,
        cursor_factory=RealDictCursor,
    )

def get_game_data(game_id):
    conn = None
    cur = None

    try:
        logger.info(
            "Connecting to database %s at %s:%s (iam_auth=true)",
            DB_NAME,
            DB_HOST,
            DB_PORT,
        )
        conn = _connect()
        cur = conn.cursor()

        fetch_sql = sql.SQL("""
            SELECT *
            FROM games
            WHERE id = {gameid}
        """).format(gameid=sql.Literal(game_id))
        cur.execute(fetch_sql)
        game_data = cur.fetchone()

        return game_data
    except Exception as e:
        logger.error("Error fetching game data: %s", e)
        traceback.print_exc(limit=None, file=None, chain=True)
        raise e
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_team_data(team_tla):
    conn = None
    cur = None

    try:
        logger.info(
            "Connecting to database %s at %s:%s (iam_auth=true)",
            DB_NAME,
            DB_HOST,
            DB_PORT,
        )
        conn = _connect()
        cur = conn.cursor()

        fetch_sql = sql.SQL("""
            SELECT *
            FROM teams
            WHERE tla = {teamtla}
        """).format(teamtla=sql.Literal(team_tla))
        cur.execute(fetch_sql)
        team_data = cur.fetchone()

        return team_data
    except Exception as e:
        logger.error("Error fetching team data: %s", e)
        traceback.print_exc(limit=None, file=None, chain=True)
        raise e
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_date_games_data(game_date):
    conn = None
    cur = None

    try:
        logger.info(
            "Connecting to database %s at %s:%s (iam_auth=true)",
            DB_NAME,
            DB_HOST,
            DB_PORT,
        )
        conn = _connect()
        cur = conn.cursor()

        fetch_sql = sql.SQL("""
            SELECT *
            FROM games
            WHERE game_date = {gamedate}
        """).format(gamedate=sql.Literal(game_date))
        cur.execute(fetch_sql)
        rows = cur.fetchall()
        games_data = {}
        for row in rows:
            games_data[row["id"]] = {k: v for k, v in row.items() if k != "id"}

        return games_data
    except Exception as e:
        logger.error("Error fetching games data: %s", e)
        traceback.print_exc(limit=None, file=None, chain=True)
        raise e
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_recent_team_stats(team_tla: str, lookback_games: int):
    conn = None
    cur = None
    try:
        conn = _connect()
        cur = conn.cursor()

        select_team_games = sql.SQL(
            "WITH team_games AS ("
            "SELECT id, game_date, home_tla AS team_tla, "
            "home_goals AS goals_for, "
            "home_xg AS xg_for, "
            "home_hits AS hits_for, "
            "home_hdc AS hdc_for, "
            "home_mdc AS mdc_for "
            "FROM public.games WHERE home_tla={team_tla} "
            "UNION ALL "
            "SELECT id, game_date, away_tla AS team_tla, "
            "away_goals AS goals_for, "
            "away_xg AS xg_for, "
            "away_hits AS hits_for, "
            "away_hdc AS hdc_for, "
            "away_mdc AS mdc_for "
            "FROM public.games WHERE away_tla={team_tla}"
            "), "
            "recent_team_games AS ("
            "SELECT * FROM team_games "
            "ORDER BY id DESC "
            "LIMIT {game_limit}"
            ") "
            "SELECT "
            "COUNT(*)::int AS games_played, "
            "AVG(goals_for)::float AS goals_for_avg, "
            "AVG(xg_for)::float AS xg_for_avg, "
            "AVG(hits_for)::float AS hits_for_avg, "
            "AVG(hdc_for)::float AS hdc_for_avg, "
            "AVG(mdc_for)::float AS mdc_for_avg "
            "FROM recent_team_games"
        ).format(team_tla=sql.Literal(team_tla), game_limit=sql.Literal(lookback_games))

        cur.execute(select_team_games)
        return cur.fetchone()
    except Exception as e:
        logger.error("Error fetching recent team stats: %s", e)
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
