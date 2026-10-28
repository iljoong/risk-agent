# Fictional investigation inputs

All records below are fictional demonstration inputs, not extracts from real systems.

## Customer, account and case

| Record | Content |
|---|---|
| Customer `CUS-1041` | Harbour Components Ltd; industrial component wholesaler. |
| Account `ACC-1041` | GBP business current account; open since March 2022. |
| KYC `KYC-1041-v3` | Reviewed 17 September 2026; expected monthly receipts GBP 120,000-200,000; primarily domestic trade receipts and supplier payments. Ownership recorded with no unresolved ownership gap in this snapshot. |
| Alert `ALT-2041` | Existing AML system priority: High. Trigger: rapid movement of funds to a newly observed beneficiary. |
| Case `CASE-1041` | Assigned to Alex Morgan; initial state: Investigate. |
| Previous case `CASE-0812` | A related-case reference exists, but its contents are inaccessible to the investigator's current role. No conclusion may be inferred from that reference. |

The existing AML system owns the original alert trigger and priority. An agent recommendation must not silently replace either.

## Transaction records

All transaction times are UTC. "Newly observed" means absent from the available 90-day account history, not necessarily a new business relationship.

| Record | Date/time | Direction | Amount | Counterparty / reference |
|---|---|---|---:|---|
| `TX-701` | 14 Sep 2026, 11:20 | Outgoing | GBP 22,000 | Established supplier; "Components invoice" |
| `TX-702` | 12 Oct 2026, 15:40 | Outgoing | GBP 27,500 | Established supplier; "Inventory replenishment" |
| `TX-781` | 28 Oct 2026, 09:12 | Incoming | GBP 18,000 | Alder Industrial; "Order H-441" |
| `TX-782` | 28 Oct 2026, 09:31 | Incoming | GBP 16,000 | Beacon Assembly; "Order H-442" |
| `TX-783` | 28 Oct 2026, 09:54 | Incoming | GBP 14,000 | Cedar Parts; "Order H-443" |
| `TX-784` | 28 Oct 2026, 10:08 | Outgoing | GBP 45,500 | Meridian Supply; "Invoice MS-882" |

These are the displayed example records, not a complete 90-day ledger. The full-history source is defined below; additional underlying rows and account balances have not been enumerated in this guide. Do not present unprovided records or balances as verified demonstration facts.

## Source artifact register

| Source | Content and purpose | Availability / freshness |
|---|---|---|
| `SRC-01` | Transaction ledger, including the displayed records and opening/closing balances. | Defined source artifact; snapshot retrieved 28 Oct 2026, 10:15 UTC; activity through 10:08. Balance values are not specified in this pack. |
| `SRC-02` | Customer/account profile and KYC snapshot. | Retrieved 28 Oct 2026; KYC reviewed 17 Sep 2026. |
| `SRC-03` | Available 90-day transaction history and beneficiary identifiers. | Retrieved 28 Oct 2026, 10:15 UTC; coverage boundaries must be displayed. The absence of Meridian Supply is a stipulated fictional scenario fact, not derivable from the six displayed rows alone. |
| `SRC-04` | Previous-case reference. | Contents inaccessible; access limitation recorded. |
| `SRC-05` | Fictional Group Investigation Standard `G-AML-07`, v3, effective 1 Oct 2026. | Approved demonstration policy. |
| `SRC-06` | Fictional Local Supplement `L-01`, v2, effective 1 Oct 2026. | Illustrative local requirements, not a legal statement. Case applicability is stipulated for this fictional example. |
| `SRC-07` | Supplier invoice corresponding to reference MS-882. | Missing initially; reference text alone is not an invoice. |

The source IDs are locators within this fictional pack, not live system URLs. A source may be defined without being available: missing and restricted sources must remain explicit gaps.

## Illustrative approved policy passages

These are fictional demonstration passages, not quotations from actual law or policy.

| Policy locator | Version / effective date | Demonstration passage |
|---|---|---|
| `G-AML-07` section 4.2 | v3 / 1 Oct 2026 | Assess both supporting and contradicting evidence; record material information gaps. |
| `G-AML-07` section 5.1 | v3 / 1 Oct 2026 | Agent-generated findings are drafts requiring investigator validation. |
| `G-AML-07` section 6.3 | v3 / 1 Oct 2026 | Record disposition rationale and evidence references; retain applicable human approvals. |
| `L-01` section 2.4 | v2 / 1 Oct 2026 | For this demonstration, corroborate a newly observed beneficiary's business purpose before recommending closure. |

The group framework supports a global organization, but local applicability must be established case by case. `L-01` does not represent a named jurisdiction's laws.

## Analyst directions

| Request | Input context |
|---|---|
| Prepare investigation. | Selected alert, case, permitted sources and investigation scope. |
| Explain this pattern and show the calculation. | Selected transaction records and available history. |
| What evidence challenges this concern? | Current findings, supporting evidence and accessible counterevidence. |
| What additional checks are required before I can recommend closure or escalation? | Applicable approved policy passages, evidence and unresolved gaps. |
| Correct "new supplier" to "beneficiary not observed in the available 90-day history." | Analyst correction to an interpretation, with the original wording retained in version history. |
