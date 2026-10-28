import copy

from sqlalchemy import func, select

from skill_chat.contracts import Conflict, Scope
from skill_chat.investigations.service import InvestigationService
from skill_chat.storage.models import investigation_ui_events
from skill_chat.storage.repository import Repository


class InvestigationProjection:
    def __init__(self, repository: Repository):
        self.repo = repository
        self.service = InvestigationService(repository)

    def snapshot_with_watermark(self, scope: Scope) -> tuple[dict, int]:
        self.repo.get_chat(scope)
        with self.repo.db.transaction() as connection:
            snapshot = copy.deepcopy(self.service.row(connection, scope)["state"])
            sequence = connection.execute(select(func.max(investigation_ui_events.c.id)).where(
                self.repo.owned(investigation_ui_events, scope),
            )).scalar() or 0
            return snapshot, sequence

    def read_ui_events(self, scope: Scope, after: int) -> list[dict]:
        self.repo.get_chat(scope)
        with self.repo.db.engine.connect() as connection:
            self.service.row(connection, scope)
            if after < 0 or after and not connection.execute(
                select(investigation_ui_events.c.id).where(
                    self.repo.owned(investigation_ui_events, scope),
                    investigation_ui_events.c.id == after,
                )
            ).first():
                raise Conflict("Investigation event checkpoint is invalid; reload the workspace snapshot")
            return [dict(row) for row in connection.execute(
                select(investigation_ui_events).where(
                    self.repo.owned(investigation_ui_events, scope),
                    investigation_ui_events.c.id > after,
                ).order_by(investigation_ui_events.c.id)
            ).mappings()]
