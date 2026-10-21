# 평가·배점·가격 시뮬레이션 모드

출력: `output\rfp-evaluation-{slug}.html`와 동일 슬러그의 `.xlsx`.
배점과 산식의 정확성은 실제 투찰 판단에 영향을 주므로 추정값을 확정값처럼 사용하지 않는다.

## 분석

1. 기술:가격 비율, 평가항목/세부배점, 정량/정성, 가점/감점, 실격 조건을 추출한다.
2. `id="score-table"`에 배점표를 쓰고 합계를 재검산한다. 충돌/누락을 표시한다.
3. 차등점수는 적용/미적용/원문 미확인, 등급/폭/방식을 표시한다.
4. 복수예가는 적용/단일/미확인, 원문 산정 방식과 공개 여부를 표시한다.
   예가 ±3% 또는 15개 중 4개는 원문 근거가 없으면 임의 적용하지 않는다.
5. 저가입찰 기준을 "% 미만", "추정가격", "예정가격", "가격평가" 등으로 찾고
   상한·하한·분모·최저입찰가 처리·최저가 보정·반올림 규칙까지 확인한다.
6. 가격/기술 중심, 실적 중심, 기존 사업자 유리성 등의 전략적 의미를 한 문단으로 설명한다.

## 산식 선택과 지원 범위

**RFP의 적용 산식/위임 기준/유효한 공식 규정이 우선**이다.
기존 문서의 2012년 규정과 80/70을 현재 법령의 자동 기본값으로 사용하지 않는다.
사용자 제공 규정 또는 공개 공식 자료로 적용 버전/조항/산식을 검증하고 인용한다.
외부 확인이 불가능하면 필요한 규정/승인을 요청한다.

`id="formula-status"`에 `data-status="verified"`, `assumption`, `unavailable` 중 하나를 넣는다.
`id="sim-formula-label"`과 `id="sim-threshold-label"`에 산식/기준의 출처와 상태를 표시한다.

번들 엔진의 지원 산식은 아래 **ratio-penalty-v1** 한 종류다.
RFP가 이 산식과 동일한 경우에만 `verified`로 사용한다.
사용자가 명시적으로 구형 예시 산식을 시나리오로 승인하면 `assumption`으로 사용할 수 있다.
그때 `class="formula-warning"`에 "가정 시나리오 — 실제 평가 규정 미확인"을 표시한다.

```text
myBid = est * ratio / 100
lowest = myBid  (시나리오 가정; 실제 경쟁사 최저가 아님)
upperPrice = est * thrU
lowerPrice = est * thrL
myBid >= upperPrice:
  score = wt * lowest / myBid
myBid < upperPrice:
  score = wt * (lowest / upperPrice
          - 2 * (upperPrice - myBid) / (upperPrice - lowerPrice))
score = max(0, min(wt, score))
```

"내 투찰가 = 최저가"는 **낙관적 가정**이며 점수 예측/최적 투찰가 보장이 아니다.
상한 이상 모든 비율이 이 가정에서 같은 배점을 얻으므로
"상한 직상이 유일한 최고점수 권장가"라는 자동 결론을 내리지 않는다.
원가/경쟁가격/참여 제한을 고려하지 않은 결과임을 표시한다.

다른 산식, 경쟁사 최저가 보정, 지원하지 않는 반올림 규칙이면 엔진을 억지로 적용하지 않는다.
`unavailable` 상태와 `class="formula-warning"`에 이유를 쓰고 계산 UI는 비활성/미제공한다.
HTML과 Excel 모두 "계산 불가 — 적용 산식 확인 필요"를 표시한다.

## 지원 산식의 UI 계약

아래 상수는 RFP 실제값/승인된 가정으로 교체한다.
`est`는 해당 산식의 정확한 기준가격이며 사업예산과 자동으로 동일시하지 않는다.
`est > 0`, `wt > 0`, `0 < thrL < thrU <= 1`을 만족해야 한다.

```html
<div id="sim-constants" data-formula="ratio-penalty-v1"
     data-est-price="1000000000" data-price-weight="20"
     data-threshold-upper="0.80" data-threshold-lower="0.70"></div>
<p id="price-error" role="alert"></p>
<label>기준가격 대비 투찰률 (%)
  <input id="sim-ratio-num" type="number" min="50" max="110" step="0.1" value="88">
</label>
<input id="sim-ratio-slider" aria-label="투찰률" type="range" min="50" max="110" step="0.1" value="88">
```

상수 표시 ID: `sim-est-display`, `sim-weight-display`.
결과 ID: `r-ratio`, `r-bid`, `r-branch`, `r-score`, `r-limit`, `r-penalty`.
사용자 입력은 **투찰률(%) 한 변수**로 숫자/슬라이더를 동기화한다. 원 단위는 출력 전용.
입력 범위는 분석한 시나리오에 맞추고 임계값의 ±1%를 포함시킨다.
기술 실점수가 확인된 경우만 읽기 전용 합산한다. 없으면 총점 확인 필요로 표시한다.
`buildPriceTable`로 100/95/90/85와 상한·하한 인접 구간을 만든다.
원문에 소수 임계값이 있으면 정수로 반올림하지 않는다.
패널티 행은 옅은 빨강/위험도 배지. 비속어 대신 "저가입찰 패널티 구간"을 사용한다.

## Excel

세 시트: `산식 설명`, `시뮬레이션`, `구간표`.
지원 산식은 HTML과 동일 상수/가정/경계/수식/반올림을 사용한다.
미지원일 때도 세 시트를 제공하되 계산 불가 이유와 확인 과제를 표시한다.

- 산식 설명: 적용 규정/버전/원문 위치·인용, 변수/VAT/예가/최저가 가정, 지원 상태.
- 시뮬레이션: 입력 투찰률(노랑), 고정 상수(회색), 계산 결과(파랑).
  비율 셀에 입력 제한, 상수는 사용자 입력으로 오인하지 않게 구분한다.
- 구간표: 상한/하한과 ±1%를 포함; 모든 결과를 실제 재계산해 HTML과 대조.
- 헤더는 뉴트럴 + 마젠타 하단선. HTML에는 실제 XLSX 파일명으로 상대 다운로드 링크.

이름 정의 `est`, `wt`, `thrU`, `thrL`, `ratio`, `myBid`, `lowest`를 사용할 경우:

```text
=MAX(0,MIN(wt,IF(myBid>=est*thrU,wt*(lowest/myBid),wt*((lowest/(est*thrU))-2*((est*thrU-myBid)/(est*thrU-est*thrL))))))
```

지원 산식의 XLSX를 생성할 수 없거나 재계산 도구가 없으면 이를 명시한다.
파일 존재만으로 가격 시뮬레이션 검증 완료라고 보고하지 않는다.
