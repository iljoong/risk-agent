# 사업 개요 모드

출력: `output\rfp-overview-{slug}.html`.
기업 전제와 원문으로 참여 가능성을 판단하고 최상단에 판정/근거/권장 조치를 표시한다.

## 필수 27개 필드

`<table id="overview-table">`의 각 `<tbody>` 행에 `data-field`를 지정한다.
기존 문서의 "22개"라는 숫자는 실제 열거한 27개 필드와 불일치하여 27개로 정정했다.
미명시 필드도 행을 유지하고 "원문 미명시 — 확인 필요"로 표시한다.

| data-field | 내용 |
|---|---|
| project-name | 사업명 |
| notice-name | 공고명 |
| notice-number | 공고번호 |
| issuer | 발주처 |
| beneficiary | 수요기관 |
| scope | 사업범위 |
| equipment | 회선·장비 구성 |
| budget | 사업금액, VAT 포함 여부 |
| estimated-price | 추정가격, VAT 기준 |
| installments | 차수별 금액·기간 |
| project-period | 사업기간 |
| service-period | 서비스 기간 |
| contract-method | 계약방식 |
| estimated-price-method | 복수예가/단일예가/미확인 |
| differential-scoring | 차등점수 적용/미적용/미확인 |
| eligibility | 참가자격 |
| consortium | 공동수급 여부/비율/대표사 조건 |
| subcontracting | 하도급 허용/불가/일부 허용과 비율 |
| bid-guarantee | 입찰보증금/면제/지급각서 조건 |
| contract-guarantee | 계약보증금/대체 조건 |
| warranty | 하자보수 조건·기간 |
| acceptance | 검수 절차·기준 |
| delay-damages | 지체상금 |
| liability | 손해배상 |
| sla | SLA 페널티 |
| contact | 연락처 |
| special-notes | 재공고/정정/분리발주/제출형식/발표자/전자입찰 특이사항 |

참가자격 셀에 아래 7개 `<li data-qualification="…">`를 모두 포함한다.
`licenses`, `experience`, `personnel`, `finance`, `security`, `region`, `consortium`.
각각 인증/면허, 실적, 인력, 재무, 보안, 지역, 공동수급 조건이며
원문 미발견은 "없음"이 아니라 "원문 미명시"다.

연락처 셀에는 아래 5개 `data-contact` 필드를 포함한다.
`department`, `person`, `phone`, `email`, `address-system`.
주소/접수 시스템이 미명시이면 확인 필요로 표시한다. 나라장터라고 임의 확정하지 않는다.

금액은 원 단위와 VAT 여부를 같이 표시한다. 추정가격을 VAT 포함 예산과 동일시하지 않는다.
기업 면허 및 보증 대체는 프로필 전제/원문 조건/증빙 확인을 분리한다.
모든 중요 조건에 원문 위치와 인용을 포함하고 원천 인벤토리를 하단에 둔다.
