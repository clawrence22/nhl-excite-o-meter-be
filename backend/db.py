import os
import logging
import boto3

from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    func, cast, select, event, or_, and_
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# --- Environment Configuration ---

DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_USER = os.environ["DB_USER"]
DB_NAME = os.environ["DB_NAME"]
DB_REGION = os.environ["DB_REGION"]
DB_SSLMODE = os.environ["DB_SSLMODE"]
DB_AUTH_HOST = os.getenv("DB_AUTH_HOST", DB_HOST)
DB_AUTH_PORT = int(os.getenv("DB_AUTH_PORT", DB_PORT))

logger = logging.getLogger(__name__)
Base = declarative_base()

# --- SQLAlchemy Models ---

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    home = Column(JSONB)
    away = Column(JSONB)
    game = Column(JSONB)


class Team(Base):
    __tablename__ = "teams"

    tla = Column(String, primary_key=True)


# --- Connection Management ---

_engine = None
_SessionFactory = None


def init_db():
    """Initializes the SQLAlchemy engine and session factory."""
    global _engine, _SessionFactory

    if _engine:
        return

    logger.info("Initializing SQLAlchemy Engine (Host: %s)", DB_HOST)

    connection_url = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    _engine = create_engine(
        connection_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        connect_args={"sslmode": DB_SSLMODE},
        future=True,
    )

    # Inject IAM auth token dynamically
    @event.listens_for(_engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        client = boto3.client("rds", region_name=DB_REGION)
        token = client.generate_db_auth_token(
            DBHostname=DB_AUTH_HOST,
            Port=DB_AUTH_PORT,
            DBUsername=DB_USER,
            Region=DB_REGION,
        )
        cparams["password"] = token

    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


def get_session():
    """Provides a new database session."""
    if not _SessionFactory:
        init_db()
    return _SessionFactory()


# --- Query Helpers ---

def extract_side(team_side, games_subq):
    """Extracts stats for either home or away side using JOIN (optimized)."""
    return (
        select(
            team_side["tla"].astext.label("team_tla"),
            cast(team_side["goals"].astext, Float).label("goals"),
            cast(team_side["hits"].astext, Float).label("hits"),
            cast(team_side["hdc"].astext, Float).label("hdc"),
            cast(team_side["mdc"].astext, Float).label("mdc"),
            cast(
                team_side["ovr_excitment"]["raw_excitement_score"].astext,
                Float,
            ).label("excitement"),
            cast(
                Game.game["ovr_excitment"]["raw_excitement_score"].astext,
                Float,
            ).label("game_excitement"),
        )
        .select_from(Game)
        .join(games_subq, Game.id == games_subq.c.id)
    )


# --- Data Functions ---

def get_game_data(game_id):
    """Fetches game by ID and returns data minus the PK."""
    with get_session() as session:
        stmt = select(Game).where(Game.id == game_id)
        game = session.execute(stmt).scalar_one_or_none()

        if not game:
            logger.info(f"No game with id {game_id}")
            return None

        return {
            "home": game.home,
            "away": game.away,
            "game": game.game,
        }


def get_team_avg(team_tla, num_games):
    """Get team averages over last N games."""
    with get_session() as session:

        team_filter = or_(
            Game.home["tla"].astext == team_tla,
            Game.away["tla"].astext == team_tla,
        )

        team_games = (
            select(Game.id)
            .where(team_filter)
            .order_by(Game.id.desc())
            .limit(num_games)
            .subquery()
        )

        combined = (
            extract_side(Game.home, team_games)
            .union_all(extract_side(Game.away, team_games))
            .subquery()
        )

        stmt = (
            select(
                combined.c.team_tla,
                func.avg(combined.c.goals).label("goals_avg"),
                func.avg(combined.c.hits).label("hits_avg"),
                func.avg(combined.c.hdc).label("hdc_avg"),
                func.avg(combined.c.mdc).label("mdc_avg"),
                func.avg(combined.c.excitement).label("excitement_avg"),
            )
            .group_by(combined.c.team_tla)
        )

        results = session.execute(stmt).all()

        for row in results:
            if row.team_tla == team_tla:
                team_results  = dict(row._mapping)
        
        logger.info(f"Team Results {team_results}")

        return team_results


def get_series_average(tla_1: str, tla_2: str, lookback_games: int):
    """Get averages for a matchup between two teams."""
    with get_session() as session:

        matchup_filter = or_(
            and_(
                Game.home["tla"].astext == tla_1,
                Game.away["tla"].astext == tla_2,
            ),
            and_(
                Game.home["tla"].astext == tla_2,
                Game.away["tla"].astext == tla_1,
            ),
        )

        matchup_games = (
            select(Game.id)
            .where(matchup_filter)
            .order_by(Game.id.desc())
            .limit(lookback_games)
            .subquery()
        )

        # ✅ FIXED: correctly execute count
        count_stmt = select(func.count()).select_from(matchup_games)
        game_count = session.execute(count_stmt).scalar_one()

        if game_count == 0:
            logger.info(f"No Games found between {tla_1} and {tla_2}")
            return None

        combined = (
            extract_side(Game.home, matchup_games)
            .union_all(extract_side(Game.away, matchup_games))
            .subquery()
        )

        stmt = (
            select(
                combined.c.team_tla,
                func.avg(combined.c.goals).label("goals_avg"),
                func.avg(combined.c.hits).label("hits_avg"),
                func.avg(combined.c.hdc).label("hdc_avg"),
                func.avg(combined.c.mdc).label("mdc_avg"),
                func.avg(combined.c.excitement).label("excitement_avg"),
                func.avg(combined.c.game_excitement).label("game_excitement_avg"),
            )
            .group_by(combined.c.team_tla)
        )

        results = session.execute(stmt).all()

        return {row.team_tla: dict(row._mapping) for row in results}