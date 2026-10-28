# RCI Agent transition scope

Date: 2026-10-27
Specification: [RCI Agent design](../specs/2026-10-27-rci-agent-design.md)

## Agreed scope

Use RCI (Risk and Compliance Intelligent) Agent as the product identity. Keep
the app general-purpose for now, with finance as the intended domain. Detailed
anomaly-triage requirements will be provided later.

This document replaces the earlier domain-specific implementation plan. It
records the current transition boundary, not a claim that a finance workflow
has been implemented or that future capabilities have been approved.

## Changes in this transition

1. Replace the old product specification, plan, and discovery transcript with
   the current RCI specification and this transition scope.
2. Update README and contributor guidance, preserving installation, provider
   configuration, local access restrictions, worker operations, extension
   contracts, and offline verification instructions.
3. Replace domain-specific welcome prompts and composer text with ordinary-chat
   starters for document review and question exploration. Do not automatically
   select a removed skill.
4. Describe generated content as versioned HTML artifacts rather than a required
   presentation format. Keep preview isolation and artifact-context behavior.
5. Generalize the remaining public organization research sample and its
   evaluations without claiming customer due diligence or financial screening.
6. Preserve internal package identifiers, migration history, existing data,
   API contracts, and the three-process deployment model.

The removed specialist extensions are not reinstated. Historical backend test
fixtures and compatibility code may retain old identifiers; removing those is
not required to change the current product experience.

## Validation boundary

Use focused UI regressions for editable starter prompts and clearing a selected
skill. Keep sandbox and version-context checks aligned with artifact labels.
Use deterministic browser fixtures for document-to-artifact, persistence,
cancellation/retry, and provider-failure behavior. Run the existing applicable
linters, type checks, and offline tests from README.

Documentation links must resolve to current files. Product documentation must
not promise removed extensions, a detector, structured case management, or
validated compliance outcomes. Runtime and billable provider tests remain
explicitly opt-in; fixture results do not prove finance-domain quality.

## Next specification, once details are supplied

Define one risk domain and one end-to-end analyst scenario before adding a
specialized workflow. Capture inputs and permissions, evidence requirements,
triage and escalation states, human decision ownership, jurisdiction/policies,
privacy/retention, audit expectations, integrations, and acceptance examples.

Choose implementation and evaluation changes from those requirements rather
than reusing assumptions from the previous product. No risk taxonomy, detection
threshold, decision automation, or regulatory filing is authorized by this plan.
