import asyncio
import copy
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from skill_chat.contracts import InvalidInput
from skill_chat.investigations.fixtures import ALERTS, EVIDENCE, SOURCES


class InvestigationConnector(Protocol):
    async def retrieve(self, source_id: str) -> dict: ...


class DemoInvestigationConnector:
    async def retrieve(self, source_id: str) -> dict:
        if source_id not in SOURCES:
            raise InvalidInput("Unknown demonstration source")
        await asyncio.sleep(0.1)
        return {
            "source_id": source_id, "connector": "demo", "fictional": True,
            "retrieved_at": datetime.now(UTC).isoformat(), **copy.deepcopy(SOURCES[source_id]),
        }


async def collect_sources(service, scope, task, connector, tasks):
    from skill_chat.storage.models import turns

    turn = service.repo.get(turns, scope, task["turn_id"])
    context = turn["request"]["investigation"]
    alert_id = context["snapshot"]["original_alert"]["id"]
    if any(item["id"] == alert_id and item["evidence"] == "none" for item in ALERTS):
        gap = "No demonstration records are packaged for this alert."
        service.stage_candidate(scope, task["id"], context["base_revision"], {
            "sources": [{
                "source_id": "SRC-00", "title": f"Demonstration records for {alert_id}", "status": "missing",
                "snapshot_at": None, "version": None, "connector": "demo", "fictional": True,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "coverage": f"{gap} Nothing was retrieved; infer no adverse or exculpatory content.", "data": {},
            }],
            "transactions": [],
            "evidence": [{"id": "GAP-01", "kind": "Missing information", "title": "No demonstration records",
                          "source_ids": ["SRC-00"], "locators": [alert_id], "text": gap}],
            "calculations": {}, "prepared": True,
            "output_updates": {
                "gather_evidence": {"text": f"{gap} GAP-01: evidence not collected.", "evidence_ids": ["GAP-01"]},
                "analyze": {"text": "No evidence is available to support or contradict the alert [GAP-01]. "
                                    "No finding can be drawn; obtain source records before any assessment.",
                            "evidence_ids": ["GAP-01"]},
            },
        })
        tasks.finish(scope, task["id"], "succeeded",
                     "Preparation completed. No demonstration records are packaged for this alert.")
        return
    sources = []
    for source_id in SOURCES:
        tasks.stage(scope, task["id"], f"Demo connector: retrieving {source_id}")
        source = await connector.retrieve(source_id)
        sources.append(source)
        service.stage_candidate(scope, task["id"], context["base_revision"], {"sources": sources})
        tasks.stage(scope, task["id"], f"Demo connector: {source_id} {source['status']}")
    rows = sources[0]["data"]["transactions"]
    incoming = sum(row["amount_gbp"] for row in rows if row["direction"] == "incoming")
    outgoing = sum(row["amount_gbp"] for row in rows if row["direction"] == "outgoing")
    elapsed = datetime.fromisoformat(rows[-1]["timestamp"]) - datetime.fromisoformat(rows[0]["timestamp"])
    calculations = {
        "incoming_gbp": incoming, "outgoing_gbp": outgoing,
        "ratio_percent": str((Decimal(outgoing) / Decimal(incoming) * 100).quantize(Decimal("0.01"))),
        "elapsed_minutes": int(elapsed.total_seconds() // 60),
    }
    service.stage_candidate(scope, task["id"], context["base_revision"], {
        "sources": sources, "transactions": rows, "evidence": copy.deepcopy(EVIDENCE),
        "calculations": calculations, "prepared": True,
        "output_updates": {
            "gather_evidence": {
                "text": "Demo connector retrieved permitted fictional sources. E-01 through E-04 available; "
                        "GAP-01: invoice missing. GAP-02: prior case contents restricted. "
                        "Coverage: selected ledger rows and stipulated 90-day history assertion only.",
                "evidence_ids": ["E-01", "E-02", "E-03", "E-04", "GAP-01", "GAP-02"],
            },
            "analyze": {
                "text": f"Selected records show GBP {incoming:,} incoming and GBP {outgoing:,} outgoing; "
                        f"{calculations['ratio_percent']}% within {calculations['elapsed_minutes']} minutes [E-01]. "
                        "Timing and amount do not establish wrongdoing or fund lineage. "
                        "Supplier payments fit the business profile [E-03]; this invoice remains unverified [E-04, GAP-01]. "
                        "Restricted case contents are not adverse evidence [GAP-02].",
                "evidence_ids": ["E-01", "E-02", "E-03", "E-04", "GAP-01", "GAP-02"],
            },
        },
    })
    tasks.finish(scope, task["id"], "succeeded",
                 "Demo evidence preparation completed using fictional records. Invoice missing; prior case restricted.")
