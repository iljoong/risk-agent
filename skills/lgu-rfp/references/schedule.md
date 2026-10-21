# 일정·D-Day 모드

출력: `output\rfp-schedule-{slug}.html`.
일정을 정규화하되 원문 날짜·시간·장소·필참여부와 근거를 보존한다.

## 필수 일정

`<table id="schedule-table">`의 본문 행에 `data-event`를 지정한다.
기존 11개를 유지하고 전자입찰 접수마감과 다른 **제안서 제출마감**을 독립 항목으로 추가했다.

| data-event | 내용 |
|---|---|
| notice | 공고일 |
| prespec-comments | 사전규격 의견 접수 기간 |
| questions | 질의 마감 |
| answers | 답변 게시 |
| briefing | 사업/현장/입찰 설명회, 장소, 필참 여부 |
| bid-open | 전자입찰서 접수개시 |
| bid-close | 전자입찰서 접수마감 |
| opening | 입찰/개찰 |
| presentation | 기술 제안서 평가/PT |
| preferred-bidder | 우선협상대상자 통보 |
| contract-start | 계약체결/사업착수 |
| proposal-close | 제안서 제출마감 |

미명시 일정은 "원문 미명시 — 확인 필요"로 행을 유지한다.
"설명회 미실시", "평가 후 통보" 등은 원문이 이를 명시할 때만 사실로 쓴다.
제안서 마감과 가격입찰 마감이 같다는 근거가 없으면 하나로 합치지 않는다.

## D-Day 마크업

```html
<div class="alert-box">제안서 제출 마감까지 <span id="dday-num">-</span>
  (마감: <span id="dday-date">-</span> KST)</div>
<div id="dday-config" data-deadline="2026-10-15T17:00:00+09:00"></div>
<p id="dday-error" role="alert"></p>
```

예시 마감값을 실제 원문 값으로 교체한다.
시간까지 명시된 값은 `YYYY-MM-DDTHH:MM:SS+09:00`, 날짜만 명시된 값은 `YYYY-MM-DD`.
날짜만 알면 임의로 17시/자정을 마감 시각으로 확정하지 않는다.
날짜도 미확인이면 `data-deadline=""`과 `class="deadline-warning"` 경고를 넣는다.
번들 D-Day 엔진을 삽입한다.

D-Day는 브라우저 타임존과 무관한 **KST 달력 날짜 차이**다.
당일은 D-Day이며 시각이 명시되고 이미 지났으면 당일에도 "마감 경과"를 표시한다.
날짜만 있으면 "시각 미확인"을 표시한다. 과거일은 D+N(경과).

`id="critical-dates"` 강조 박스에는 설명회(필참), 질의 마감, 제안서 제출 마감,
전자입찰 마감, 경과/촉박 일정, 확인 필요 항목 수를 표시한다.
일정의 변경/재공고 충돌을 양쪽 근거와 함께 표시한다.
