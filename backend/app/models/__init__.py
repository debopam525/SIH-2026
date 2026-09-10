"""Import every model so ``Base.metadata`` is complete."""
from app.models.application import Application, Dependency, Repository
from app.models.asset import CryptographicAsset
from app.models.evidence import Evidence
from app.models.migration import MigrationStatus
from app.models.mosca import MoscaAssessment
from app.models.recommendation import Recommendation
from app.models.report import Report
from app.models.risk import RiskAssessment
from app.models.scan import Scan
from app.models.settings import SettingKV
from app.models.user import User

__all__ = [
    "Application",
    "Dependency",
    "Repository",
    "CryptographicAsset",
    "Evidence",
    "MigrationStatus",
    "MoscaAssessment",
    "Recommendation",
    "Report",
    "RiskAssessment",
    "Scan",
    "SettingKV",
    "User",
]
