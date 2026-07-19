from abc import ABC, abstractmethod

from app.core.preprocessor import EvidencePackage
from app.models.incident import IncidentReport


class BaseLLMProvider(ABC):
    @abstractmethod
    async def analyse(self, package: EvidencePackage) -> IncidentReport:
        ...
