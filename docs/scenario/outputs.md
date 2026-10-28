# Investigation outputs

These are fictional example outputs and record requirements, not results from an executed agent or live investigation.

## Verified calculation

| Measure | Calculation | Result |
|---|---|---|
| Incoming total | 18,000 + 16,000 + 14,000 | GBP 48,000 |
| Subsequent outgoing amount | TX-784 | GBP 45,500 |
| Outgoing / incoming ratio | 45,500 / 48,000 x 100 | 94.79%, rounded to two decimal places |
| Elapsed time | 09:12 to 10:08 UTC, 28 Oct 2026 | 56 minutes |

Source: [inputs.md](inputs.md), `SRC-01`, records `TX-781` through `TX-784`.

These calculations establish timing and amounts, not that the outgoing payment used those exact funds or that activity is criminal.

## Evidence item format

Each evidence item contains:

Evidence ID; exact source and record locator; relevant extract; source version; event time; retrieval time; coverage and freshness; relationship to the finding; access limitations.

Source freshness and retrieval time are different. A newly retrieved KYC document can still describe an earlier review.

## Evidence and gap register

| ID | Source locator | Classification | Finding and limitation |
|---|---|---|---|
| `E-01` | `SRC-01`, `TX-781` through `TX-784` | Supports concern | Closely timed credits and outgoing payment. Does not establish criminal intent or fund lineage. |
| `E-02` | `SRC-03`, available 90-day history | Supports concern | Beneficiary absent from available history. Does not prove a new commercial relationship. This absence is a stipulated scenario fact; the displayed sample rows are not the complete history. |
| `E-03` | `SRC-02`, `KYC-1041-v3`; `SRC-01`, `TX-701` and `TX-702` | Counterevidence | Supplier payments fit the customer's recorded business profile and have occurred previously. Does not verify this particular supplier or payment. |
| `E-04` | `SRC-01`, `TX-784`, payment reference | Possible alternative explanation | "Invoice MS-882" suggests invoice settlement, but the reference is uncorroborated. |
| `GAP-01` | `SRC-07` | Missing information | Supporting invoice unavailable. |
| `GAP-02` | `SRC-04`, `CASE-0812` reference | Access limitation | Previous-case contents inaccessible. Request authorized access or specialist review; do not bypass restrictions or infer adverse content. |

## Risk analysis summary

| Indicator | Explanation | Qualification |
|---|---|---|
| Rapid movement | Outgoing payment follows three incoming credits within 56 minutes. | Timing alone does not demonstrate wrongdoing. |
| Newly observed beneficiary | Meridian Supply is absent from the available 90-day history. | "Not observed" is not equivalent to "new supplier." |
| Large outgoing amount relative to selected credits | GBP 45,500 is 94.79% of GBP 48,000. | This is not a fund-lineage determination. |
| Plausible trade explanation | Supplier payments are consistent with the business profile and historical examples. | The specific invoice and business purpose remain unverified. |
| Incomplete context | Invoice missing and previous case inaccessible. | Findings and closure readiness must reflect these limitations. |

The original AML priority remains **High**. The agent's proposed next action is a separate recommendation, not a replacement priority or an unexplained confidence score.

## Example agent output

**AI draft - awaiting review**

The available records show rapid movement of funds to a beneficiary not observed in the available 90-day history [E-01, E-02]. Supplier payments are consistent with the customer's recorded business activity [E-03], but the stated invoice purpose is unverified [E-04, GAP-01]. Previous-case context could not be assessed [GAP-02].

**Proposed next action:** Obtain permitted invoice corroboration and resolve or route the material access gap before assessing closure readiness.

**Applicable demonstration policy:** `G-AML-07` v3, sections 4.2, 5.1 and 6.3; `L-01` v2, section 2.4.

## Example human-reviewed note

**Analyst:** Alex Morgan  
**Case:** CASE-1041  
**Analyst proposed disposition:** Refer for further investigation through the existing approval workflow.

**Rationale:** The timing warrants further assessment, but current evidence does not establish wrongdoing. The supplier explanation remains plausible and unverified. I corrected the draft's characterization of the beneficiary and have not treated inaccessible case content as adverse evidence.

**References:** E-01 through E-04; GAP-01 and GAP-02; G-AML-07 v3; L-01 v2.

**External saving/approval status:** Not confirmed by this workbench.

Reviewing the note does not constitute approval of escalation, closure, filing or account restriction. The proposed disposition proceeds through the existing authorized human workflow.

## Case state and review outputs

- Current journey stage and outstanding checks.
- Completed, failed, restricted and pending actions, distinguished explicitly.
- Separate supporting evidence, counterevidence and missing information.
- Versioned findings and draft notes.
- Analyst amendments, accepted/rejected recommendations and rationale.
- Reviewed note prepared for copying into the existing case system.
- External save or approval status kept unconfirmed unless independently evidenced.
- Material evidence changes after review mark affected findings and drafts as requiring re-review.

## Audit record

Each event records actor, timestamp, case, action, result, source references, request identifier and relevant evidence/draft versions.

The following is an illustrative event sequence, not a claim that the actions occurred:

| Event | Actor | Action / result | Record linkage |
|---|---|---|---|
| `AUD-01` | Analyst | Requests investigation preparation. | CASE-1041; investigation request. |
| `AUD-02` | Agent / automated retrieval | Retrieves permitted ledger snapshot and calculates selected totals. | SRC-01; E-01; calculation result. |
| `AUD-03` | Agent / automated retrieval | Previous-case content access denied; records limitation. | SRC-04; GAP-02. |
| `AUD-04` | Analyst | Challenges the initial concern. | Challenge request; current finding version. |
| `AUD-05` | Agent | Adds cited counterevidence and revises draft. | E-03; E-04; old and new draft versions. |
| `AUD-06` | Analyst | Corrects beneficiary interpretation and records rationale. | Analyst amendment; old and new draft versions. |
| `AUD-07` | Analyst | Reviews note and requests preparation for copying. | Reviewed note version; proposed disposition. |
| `AUD-08` | Workbench | Prepares copyable record. Does not claim an external save or approval. | Exported note version; external status unconfirmed. |

Actual timestamps and request identifiers belong to the recorded actions; do not fabricate them as execution evidence. Record material source access and failures, not hidden model reasoning. Preserve correction history rather than silently replacing prior content.
