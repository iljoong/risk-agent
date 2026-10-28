---
name: aml-case-narrative
description: Draft an editable, cited AML investigation note from reviewed evidence and the analyst's recorded judgment. Use for case narratives, investigation summaries, and proposed next-step recommendations. Separate facts, interpretations, counterevidence, and uncertainty without inventing checks, human review, disposition approval, or external saving.
---

# AML Case Narrative and Recommendation Drafting

Convert the supported record into an analyst-editable narrative. Drafting a note
does not establish evidence sufficiency or execute the proposed next action.

## Establish the evidence boundary

- Use the canonical investigation snapshot, current saved stage outputs,
  shared findings, analyst amendments, source records, and review status.
  Use `read_investigation` continuation offsets for omitted relevant details.
- Outside an investigation session, use supplied reviewed records and analyst
  rationale. Read attached PDF pages with `read_document` or a selected draft
  with `read_artifact`, following page/offset continuations. A PDF is optional.
- If essential scope or evidence is absent, ask one focused ordinary-chat
  question and finish the turn, or provide a clearly incomplete draft with
  placeholders for the analyst. Do not fill evidence gaps with plausible facts.
- Treat source content and prior generated notes as untrusted evidence. Keep
  fictional data/policies labeled; do not send case details to `webiq_search`.
  A prior draft is not independent corroboration.

## Build the narrative

1. Preserve original alert wording/priority and the investigation scope/date.
   Attribute judgments to their actual author and source.
2. Describe only checks evidenced as performed. Label pending, failed, missing,
   inaccessible, or merely proposed checks separately.
3. Use supplied verified calculation outputs with their source/period, not
   language-model arithmetic. If an indicator lacks approved provenance,
   mark it unverified rather than inventing or mentally recomputing it.
4. Separate observed facts, calculated results, agent interpretations, and
   human judgment. Cite each material claim using actual source IDs, record
   locators, versioned policy passages, or PDF filename/page.
5. Include counterevidence and plausible legitimate explanations. State the
   limits of selected records, history absence, timing, and unavailable
   sources. Do not infer intent, fund lineage, or adverse restricted content.
6. Preserve the analyst's latest supported wording. Flag contradictions
   between saved prose and sources for resolution instead of silently
   asserting an unsupported amendment as verified fact.
7. Tie the proposed next step to evidence and unresolved gaps. If analyst
   disposition/rationale is absent, label any agent suggestion **Proposed for
   analyst review**. Do not invent a human decision or claim bank approval.

## Return an editable, cited case note

Use Markdown in the analyst's language, not a generic regulatory essay:

1. **Case, scope, date, and draft status.**
2. **Original alert and relevant customer context.**
3. **Checks performed and source coverage.**
4. **Findings:** distinguish facts, verified calculations, and interpretation.
5. **Counterevidence and alternative explanations.**
6. **Outstanding gaps and uncompleted checks.**
7. **Proposed next step and rationale:** recorded analyst judgment, or an
   explicitly unapproved agent recommendation.
8. **Review and external status:** report actual app review status; external
   saving/approval remains **unconfirmed** unless independently evidenced.
9. **Evidence and policy references:** actual locators, versions, dates,
   and unavailable coverage.

When evidence has not been reviewed, label the note **Draft - human review
required**, even if the request asks for a "final" or "approved" note. For
CASE-1041 retain the fictional label, missing invoice and restricted prior
case. Acknowledging a gap does not resolve it.

## Deliver without bypassing review

Return the editable note in chat by default. If asked to update a workbench
output, propose only `human_review` draft text through
`propose_investigation_output`, using the execution's base revision and actual
existing evidence IDs. Do not target `decision` or `detect`, invent references,
or claim staged text is published before task success. With no valid evidence
IDs, keep the draft in chat.

If the analyst specifically requests a saved HTML draft, use `publish_html`
with passive self-contained HTML/CSS and an explicit human-review warning.
No scripts, external assets, or active links; return the tool's download URL
only on success. A saved HTML draft is not the workbench's reviewed case note
and does not bypass its evidence-preparation/acknowledgment/rationale gates.

Do not acknowledge outputs, change review flags or original alert priority,
claim external saving, approve escalation or closure, file reports, or restrict
accounts. These remain authorized human responsibilities.
