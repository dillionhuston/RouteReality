from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Database import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.user_stats_repository import UserStatsRepository
from app.repositories.router_repository import RouteRepository
from app.repositories.journey_repository import JourneyRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.repositories.leaderboard_repository import LeaderboardRepository
from app.repositories.event_repository import EventRepository
from app.repositories.push_subscription_repository import PushSubscriptionRepository
from app.Services.auth import AuthService
from app.Services.v2.prediction.prediction_service import PredictionService
from app.Services.journeyService.journey_service import JourneyService
from app.Services.journeyService.eventHandler import JourneyEventHandler




async def get_leaderboard_repository(db: AsyncSession = Depends(get_db)) -> LeaderboardRepository:
    return LeaderboardRepository(db)

def get_auth_service(db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    return AuthService(repo)

def get_user_repository(db: AsyncSession = Depends(get_db)):
    return UserRepository(db)

def get_user_stats_repository(db: AsyncSession = Depends(get_db)):
    return UserStatsRepository(db)

def get_route_repository(db: AsyncSession = Depends(get_db)) -> RouteRepository:
    return RouteRepository(db)

def get_journey_repository(db: AsyncSession = Depends(get_db)) -> JourneyRepository:
    return JourneyRepository(db)

def get_snapshot_repository(db: AsyncSession = Depends(get_db)) -> SnapshotRepository:
    return SnapshotRepository(db)

def get_event_repository(db: AsyncSession = Depends(get_db)) -> EventRepository:
    return EventRepository(db)

def get_push_subscription_repository(db: AsyncSession = Depends(get_db)) -> PushSubscriptionRepository:
    return PushSubscriptionRepository(db)

def get_prediction_service() -> PredictionService:
    return PredictionService(PredictionRepository, EventRepository, JourneyRepository)

def get_journey_service(
    route_repo: RouteRepository = Depends(get_route_repository),
    pred_svc: PredictionService = Depends(get_prediction_service),
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    snapshot_repo: SnapshotRepository = Depends(get_snapshot_repository)) -> JourneyService:
    return JourneyService(route_repo, pred_svc, journey_repo, snapshot_repo)

async def get_journey_event_handler(
    journey_repo: JourneyRepository = Depends(get_journey_repository),
    event_repo: EventRepository = Depends(get_event_repository),
    user_stats_repo: UserStatsRepository = Depends(get_user_stats_repository)) -> JourneyEventHandler:
    return JourneyEventHandler(journey_repo, event_repo, user_stats_repo)