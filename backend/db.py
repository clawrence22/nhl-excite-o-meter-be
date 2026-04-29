import os
import logging
import traceback
import boto3
from sqlalchemy import create_engine, Column, Integer, String, func, cast, Float,event,or_, and_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

# Environment Configuration
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_USER = os.environ["DB_USER"]
DB_NAME = os.environ["DB_NAME"]
DB_REGION = os.environ["DB_REGION"]
DB_SSLMODE = os.environ["DB_SSLMODE"]
DB_AUTH_HOST = os.getenv("DB_AUTH_HOST", DB_HOST)
DB_AUTH_PORT = int(os.getenv("DB_AUTH_PORT", DB_PORT))

logger = logging.getLogger(__name__)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
Base = declarative_base()

# --- SQLAlchemy Models ---

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True)
    home = Column(JSONB)  # Contains goals, hits, hdc, mdc, excitement, tla
    away = Column(JSONB)
    game = Column(JSONB)
    playoffs = Column(JSONB)
    excitement = Column(JSONB)

class Team(Base):
    __tablename__ = 'teams'
    tla = Column(String, primary_key=True)
    # Add other persistent columns here

# --- Connection Management ---

_engine = None
_SessionFactory = None

def init_db():
    """Initializes the SQLAlchemy engine and session factory."""
    global _engine, _SessionFactory
    if _engine:
        return

    logger.info("Initializing SQLAlchemy Engine (Host: %s)", DB_HOST)
    
    # Connection URL (Password is injected via creator to handle rotations)
    connection_url = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    _engine = create_engine(
        connection_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        connect_args={"sslmode": DB_SSLMODE}
    )
    # 2. Attach a listener to inject the token before connecting
    @event.listens_for(_engine, "do_connect")
    def provide_token(dialect, conn_rec, cargs, cparams):
        client = boto3.client("rds", region_name=DB_REGION)
        token = client.generate_db_auth_token(
            DBHostname=DB_AUTH_HOST,
            Port=DB_AUTH_PORT,
            DBUsername=DB_USER,
            Region=DB_REGION
        )
        # Inject the token into the connection parameters
        cparams["password"] = token
    
    _SessionFactory = sessionmaker(bind=_engine)

def get_session():
    """Provides a new database session."""
    if not _SessionFactory:
        init_db()
    return _SessionFactory()

# --- Data Functions ---

def get_game_data(game_id):
    """Fetches game by ID and returns data minus the PK."""
    session = get_session()
    try:
        game = session.query(Game).filter(Game.id == game_id).first()
        if not game:
            logger.info(f"No game with id {game_id}")
            return None
        
        return {
            "home": game.home,
            "away": game.away,
            "game": game.game,
            "playoffs": game.playoffs,
            "excitement": game.excitement
        }
    except Exception as e:
        logger.error("Error fetching game data: %s", e)
        raise e
    finally:
        session.close()

def get_team_data(team_tla):
    """Fetches team details by TLA."""
    session = get_session()
    try:
        team = session.query(Team).filter(Team.tla == team_tla).first()
        return team
    finally:
        session.close()

def get_game_excitement_bonus_average(num_games: int ):
    session = get_session()
    try:
    #Grab the last <num_games> and get each game's game_excitement_bonus and then average it
        avg_excitement = session.query(func.avg(cast(Game.excitement["bonuses"]['game_excitement_bonus'].astext, Float))).limit(num_games).scalar()
        logger.info(f"Average excitement bonus for last {num_games} games: {avg_excitement}")
        return avg_excitement
    except Exception as e:
        logger.error(f"Error: {e}")
        raise e
    finally:
        session.close()


def get_series_average(tla_1: str, tla_2: str, lookback_games: int):
    session = get_session()
    try:
        # 1. Match both scenarios: (T1 vs T2) OR (T2 vs T1)
        matchup_filter = or_(
            and_(Game.home['tla'].astext == tla_1, Game.away['tla'].astext == tla_2),
            and_(Game.home['tla'].astext == tla_2, Game.away['tla'].astext == tla_1)
        )

        # 2. Get the recent Game IDs for this bidirectional matchup
        matchup_games = (
            session.query(Game.id)
            .filter(matchup_filter)
            .order_by(Game.id.desc())
            .limit(lookback_games)
            .subquery()
        )

        # 3. Extract stats (Identify which team is which within the JSON)
        # We use a CASE statement or simply extract both sides and filter by the TLAs we want
        def extract_side(side_col):
            return session.query(
                side_col['tla'].astext.label('team_tla'),
                cast(side_col['goals'].astext, Float).label('goals'),
                cast(side_col['hits'].astext, Float).label('hits'),
                cast(side_col['hdc'].astext, Float).label('hdc'),
                cast(side_col['mdc'].astext, Float).label('mdc'),
                cast(side_col['ovr_excitment']['raw_excitement_score'].astext, Float).label('excitement')
            ).filter(Game.id.in_(matchup_games))

        # Union the home side data and away side data
        combined = extract_side(Game.home).union_all(extract_side(Game.away)).subquery()

        # 4. Final Aggregation
        # This will group by TLA, giving you one row for Team 1 and one for Team 2
        stats = session.query(
            combined.c.team_tla,
            func.avg(combined.c.goals).label('goals_avg'),
            func.avg(combined.c.hits).label('hits_avg'),
            func.avg(combined.c.hdc).label('hdc_avg'),
            func.avg(combined.c.mdc).label('mdc_avg'),
            func.avg(combined.c.excitement).label('excitement_avg')
        ).group_by(combined.c.team_tla).all()

        return {row.team_tla: row._asdict() for row in stats}

    except Exception as e:
        logger.error(f"Error: {e}")
        return {}
    finally:
        session.close()
