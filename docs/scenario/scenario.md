# Scenario and operating model

## Purpose and audience

Demonstrate to a Head of AML and analysts how an investigator's work changes when a Copilot Studio agent gathers, analyzes and organizes evidence within a single case workbench.

The demonstration emphasizes reduced manual collection, evidence challenge, source traceability and human accountability. It is not simply a transaction-monitoring dashboard or a blank chatbot.

This document describes behavior, not a technical implementation. All people, organizations, records and policies are fictional.

## Fictional organization

**Northbridge Financial** is a fictional global financial services group.

The organization uses fictional group AML policies with versioned local supplements. Policy applicability must be identified for each case; the demonstration does not assume a single worldwide AML rulebook or claim legal compliance.

## Primary persona

**Alex Morgan, Financial Crime Investigator**

| Area | Description |
|---|---|
| Responsibilities | Investigate assigned alerts, validate evidence, consider alternative explanations, document findings and recommend a disposition. |
| Objectives | Reach a defensible conclusion with a traceable evidence record and appropriate human approvals. |
| Current pain points | Switching between systems, manually reconciling transactions, searching policies, copying evidence and reconstructing the investigation history. |
| To Be working model | Direct the agent from one case workbench; spend more time challenging evidence and applying judgment, less time collecting and organizing information. |
| Accountability | Own the investigation rationale and proposed disposition. Authorized human approvers retain existing approval responsibilities. |

## Investigation narrative

Harbour Components Ltd is a fictional industrial component wholesaler with a GBP business current account. An existing AML monitoring alert identifies three incoming payments totaling GBP 48,000, followed by a GBP 45,500 outgoing payment to Meridian Supply.

The outgoing beneficiary is not observed in the available 90-day account history. This does not establish that the supplier or business relationship is new. The activity warrants investigation, but an ordinary supplier-payment explanation remains plausible.

Alex opens the alert and selects **Prepare investigation**. The Copilot Studio agent gathers permitted customer, account, KYC, transaction, case and policy information. It calculates figures, builds a timeline, and separates supporting evidence, counterevidence and missing information.

Alex inspects the underlying transactions, asks what challenges the concern and checks applicable policy passages. The agent updates the investigation pack rather than merely answering in chat. An inaccessible prior case is shown as a limitation, not treated as adverse evidence.

Alex corrects an interpretation, reviews the draft and records a proposed disposition with rationale. The reviewed note is prepared for copying into the existing case system for manual saving and the existing approval process. Preparing or copying a note does not confirm saving, approval or case closure.

## Single-workbench experience

| Area | Display | Analyst interaction |
|---|---|---|
| Alert queue | Assigned alerts with existing AML priority, trigger, age and investigation status. | Open an alert without leaving the workbench. |
| Journey | Detect -> Investigate -> Gather Evidence -> Analyze -> Human Review -> Decision. | Immediately identify the selected case's current stage. |
| Case overview | Profile, expected activity, original alert reason, relevant history and gaps. | Expand context and select Prepare investigation. |
| Transaction timeline | Relevant transactions, verified totals and underlying record links. | Filter available periods, inspect calculations and request comparisons. |
| Evidence workspace | Supporting evidence, contradicting evidence and missing information, clearly separated. | Open sources and challenge whether each item supports a finding. |
| Agent panel | Investigation request, observable actions, completed checks and limitations. | Request a permitted check, challenge a finding or redirect work. |
| Policy and guidance | Approved demonstration passages, version, effective date and applicability. | Inspect citations and identify unresolved requirements. |
| Draft and human review | Editable AI draft, uncertainty, citations, proposed next action and review status. | Amend wording, accept or reject recommendations and record rationale. |
| Audit trail | Automated actions, human activities, source access, failures and version history. | Inspect how the record developed. |

The original AML priority stays distinct from the agent's proposed next action. No unexplained confidence percentage or hidden internal reasoning is displayed.

## Responsibility boundaries

| Copilot Studio / automated activities | Human investigation and review | Human-only decisions and accountability |
|---|---|---|
| Retrieve permitted sources and organize evidence. | Validate material claims and source context. | Assess evidence sufficiency and exercise professional judgment. |
| Calculate totals and identify patterns or supported relationships. | Challenge interpretations and consider alternatives. | Own the investigation rationale and proposed disposition. |
| Surface counterevidence, uncertainty and gaps. | Correct draft wording and accept or reject recommendations. | Make and approve closure, escalation, regulatory reporting, account restriction and other consequential decisions according to authorized roles. |
| Prepare cited drafts and proposed next actions. | Prepare the reviewed record for the existing workflow. | Retain existing approval responsibilities; exporting is not approval. |

## Boundaries

- Fictional customer data only; no real customer information is required.
- No technical architecture, deployment or implementation is included.
- No agent tool may file a report, restrict an account, close a case or approve escalation.
- Evidence collection remains bounded by the analyst's authorized request and access.
- The illustrative local policy supplement is not a statement of any country's laws.
- The visual mockup does not prove that these controls have been implemented.
