import os
import logging
import traceback
import threading

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from logging_config import setup_logging

DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_USER = os.environ["DB_USER"]
DB_NAME = os.environ["DB_NAME"]
DB_REGION = os.environ["DB_REGION"]
DB_SSLMODE = os.environ["DB_SSLMODE"]
DB_USE_IAM_AUTH = os.getenv("DB_USE_IAM_AUTH")
DB_AUTH_HOST = os.getenv("DB_AUTH_HOST")
DB_AUTH_PORT = os.getenv("DB_AUTH_PORT")
if not DB_AUTH_HOST:
    DB_AUTH_HOST = DB_HOST
if not DB_AUTH_PORT:
    DB_AUTH_PORT = int(DB_PORT)
setup_logging()
logger = logging.getLogger(__name__)

_POOL = None
_POOL_LOCK = threading.Lock()


def _get_password():
    client = boto3.client("rds", region_name=DB_REGION)
    return client.generate_db_auth_token(
        DBHostname=DB_AUTH_HOST,
        Port=DB_AUTH_PORT,
        DBUsername=DB_USER,
        Region=DB_REGION,
    )


def init_db_pool(minconn: int = 1, maxconn: int = 5) -> None:
    global _POOL
    if _POOL is not None:
        return
    with _POOL_LOCK:
        if _POOL is not None:
            return
        logger.info("Initializing DB pool (min=%s max=%s)", minconn, maxconn)
        _POOL = ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=_get_password(),
            sslmode=DB_SSLMODE,
            cursor_factory=RealDictCursor,
        )


def close_db_pool() -> None:
    global _POOL
    with _POOL_LOCK:
        if _POOL is None:
            return
        logger.info("Closing DB pool")
        _POOL.closeall()
        _POOL = None


def _get_conn():
    if _POOL is None:
        init_db_pool()
    try:
        return _POOL.getconn()
    except Exception:
        # Pool may be stale (e.g., IAM token rotation). Recreate once.
        logger.exception("DB pool getconn failed; recreating pool")
        close_db_pool()
        init_db_pool()
        return _POOL.getconn()


def _put_conn(conn) -> None:
    if _POOL is None:
        conn.close()
        return
    _POOL.putconn(conn)

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
        conn = _get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        fetch_sql = sql.SQL("""
            SELECT *
            FROM games
            WHERE id = {gameid}
        """).format(gameid=sql.Literal(game_id))
        cur.execute(fetch_sql)
        row = cur.fetchone()
        
        if row is None:
            logger.info(f"No game with id {game_id}. {str(row)}")
            return None
        
        game_data = {k: v for k, v in row.items() if k != "id"}
        logger.info(f"DB RETURN game with id {game_id}:{game_data}")
        return game_data
    except Exception as e:
        logger.error("Error fetching game data: %s", e)
        traceback.print_exc(limit=None, file=None, chain=True)
        raise e
    finally:
        if cur:
            cur.close()
        if conn:
            _put_conn(conn)

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
        conn = _get_conn()
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
            _put_conn(conn)

def get_series_average(home_tla: str, away_tla: str, lookback_games: int):
    conn = None
    cur = None
    try:
        conn = _get_conn()
        cur = conn.cursor()

        select_team_games = sql.SQL(
            "WITH series_games AS ("
            "SELECT id, home_tla AS team_tla, "
            "home_goals AS goals_for, home_hits AS hits_for, "
            "home_hdc AS hdc_for, home_mdc AS mdc_for, home_excitement AS team_excitement "
            "FROM public.games WHERE home_tla={home_tla} AND away_tla={away_tla} "
            "UNION ALL "
            "SELECT id, away_tla AS team_tla, "
            "away_goals AS goals_for, away_hits AS hits_for, "
            "away_hdc AS hdc_for, away_mdc AS mdc_for, away_excitement AS team_excitement "
            "FROM public.games WHERE home_tla={home_tla} AND away_tla={away_tla}"
            "), "
            "recent_ids AS ("
            "SELECT DISTINCT id FROM series_games ORDER BY id DESC LIMIT {game_limit}"
            ") "
            "SELECT team_tla, "
            "AVG(goals_for)::float AS goals_for_avg, "
            "AVG(hits_for)::float AS hits_for_avg, "
            "AVG(hdc_for)::float AS hdc_for_avg, "
            "AVG(mdc_for)::float AS mdc_for_avg, "
            "AVG(team_excitement)::float AS team_excitement_avg "
            "FROM series_games WHERE id IN (SELECT id FROM recent_ids) "
            "GROUP BY team_tla"
        ).format(
            home_tla=sql.Literal(home_tla),
            away_tla=sql.Literal(away_tla),
            game_limit=sql.Literal(lookback_games)
        )

        cur.execute(select_team_games)
        rows = cur.fetchall()

        logger.info(f"DB RETURN series average for {home_tla} vs {away_tla} with lookback {lookback_games}:{rows}")

        if not rows:
            logger.info(f"No series games found between {home_tla} and {away_tla}")
            return {}

        return {row["team_tla"]: dict(row) for row in rows}
    except Exception as e:
        logger.error("Error fetching series average: %s", e)
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            _put_conn(conn)
