# Product and security knowledge

SYNTHETIC COMPANY DATA - TEST USE ONLY. Baseline: 21 October 2026.
Record owners: Product Lead and Security Lead.

## CAP-01 - Identity and migration

SAML 2.0 sign-in and regional role separation are supported. User deactivation
synchronizes every four hours; a 60-minute maximum is not supported today.
The largest completed synthetic migration was 8,000 documents / 35 GB. A
12,500-document / 60 GB migration requires a pilot and capacity validation.

## CAP-02 - Search and performance

Page-cited search and version-aware exports are supported. The latest synthetic
load test achieved 6.2-second p95 search latency at 80 concurrent users.
Performance at 180 concurrent users has not been measured. Do not claim a
4-second p95 or infer that named-user licensing establishes concurrent capacity.

## SEC-01 - Hosting and encryption

Primary content and indexes are hosted in the EU. Disaster-recovery backups
currently reside in the United States. Moving backups into the EU is an
unfunded design change, not an approved option. TLS 1.2+ and AES-256 are used;
key rotation evidence is not included. Customer-managed keys are unsupported.

## SEC-02 - Assurance

The simulated company has a SOC 2 Type I report, no SOC 2 Type II report and
no ISO 27001 certificate. Type II is a target for Q3 2027, not a commitment.
Do not call Type I equivalent to Type II or claim certification is already met.

## SEC-03 - Audit and incidents

Audit events cover sign-ins, exports and administrator changes, with 90-day
retention. Thirteen-month retention requires unpriced development.
The standard incident policy promises notification within 48 hours of
confirmation, not 24 hours.

## SEC-04 - AI data handling and exit

The product team states it does not train shared models on customer content.
Signed model-provider terms proving retention/training restrictions are absent:
contractual compliance is Needs confirmation. Standard export lead time is
60 days; primary deletion is within 90 days after export approval. Backup
expiry is 12 months. Faster exit/deletion terms require approved remediation.
