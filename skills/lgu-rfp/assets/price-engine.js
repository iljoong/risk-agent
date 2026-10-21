"use strict";

function validatePriceConstants(est, weight, upper, lower) {
  if (![est, weight, upper, lower].every(Number.isFinite) ||
      est <= 0 || weight <= 0 || lower <= 0 || upper > 1 || lower >= upper) {
    throw new Error("기준가격/배점은 양수, 임계값은 0 < 하한 < 상한 <= 1이어야 합니다.");
  }
}

function calculatePriceScore(est, weight, upper, lower, ratio) {
  validatePriceConstants(est, weight, upper, lower);
  if (!Number.isFinite(ratio) || ratio <= 0) throw new Error("투찰률은 유효한 양수여야 합니다.");
  const bid = est * ratio / 100;
  const penalty = ratio < upper * 100;
  const raw = penalty
    ? weight * (ratio / (upper * 100) - 2 * ((upper * 100 - ratio) / ((upper - lower) * 100)))
    : weight;
  return { ratio, bid, score: Math.max(0, Math.min(weight, raw)), penalty };
}

function buildPriceTable(est, weight, upper, lower) {
  validatePriceConstants(est, weight, upper, lower);
  const u = upper * 100;
  const l = lower * 100;
  const ratios = [...new Set(
    [100, 95, 90, 85, u + 1, u, u - 1, u - 2, u - 5, l + 2, l + 1, l, l - 1, l - 2]
      .map(value => Number(value.toFixed(8)))
  )].filter(value => value > 0).sort((a, b) => b - a);
  return ratios.map(ratio => calculatePriceScore(est, weight, upper, lower, ratio));
}

(function () {
  function init() {
    const error = document.getElementById("price-error");
    let outputs = [];
    function fail(err) {
      outputs.forEach(element => { element.textContent = "계산 불가"; });
      const message = `가격 계산 불가: ${err.message}`;
      if (error) error.textContent = message;
      console.error(message);
    }
    try {
      const get = id => {
        const element = document.getElementById(id);
        if (!element) throw new Error(`필수 표시 영역 누락: ${id}`);
        return element;
      };
      const config = get("sim-constants");
      if (!error) throw new Error("가격 오류 표시 영역이 없습니다.");
      if (config.dataset.formula !== "ratio-penalty-v1") throw new Error("지원하지 않는 가격 산식입니다.");
      const values = [
        config.dataset.estPrice, config.dataset.priceWeight,
        config.dataset.thresholdUpper, config.dataset.thresholdLower
      ].map(Number);
      validatePriceConstants(...values);
      const number = get("sim-ratio-num");
      const slider = get("sim-ratio-slider");
      const min = Number(number.min);
      const max = Number(number.max);
      if (!Number.isFinite(min) || !Number.isFinite(max) || min <= 0 || min >= max ||
          Number(slider.min) !== min || Number(slider.max) !== max) {
        throw new Error("투찰률 입력 범위가 유효하지 않거나 서로 다릅니다.");
      }
      const [est, weight, upper, lower] = values;
      get("sim-est-display").textContent = est.toLocaleString("ko-KR");
      get("sim-weight-display").textContent = String(weight);
      get("r-limit").textContent = String(weight);
      outputs = ["r-ratio", "r-bid", "r-branch", "r-score", "r-penalty"].map(get);
      const total = document.getElementById("r-total");
      const technicalText = config.dataset.technicalScore;
      const technical = technicalText === undefined ? null : Number(technicalText);
      if (technical !== null && (!Number.isFinite(technical) || technical < 0 || !total)) {
        throw new Error("기술 실점수 또는 합산 표시 영역을 확인하세요.");
      }
      if (total) outputs.push(total);
      function sync(source) {
        try {
          if (source.value.trim() === "") throw new Error("투찰률을 입력하세요.");
          const ratio = Number(source.value);
          if (!Number.isFinite(ratio) || ratio < min || ratio > max) {
            throw new Error(`투찰률은 ${min}%~${max}% 범위여야 합니다.`);
          }
          const result = calculatePriceScore(est, weight, upper, lower, ratio);
          number.value = String(ratio);
          slider.value = String(ratio);
          outputs[0].textContent = `${ratio.toFixed(2)} %`;
          outputs[1].textContent = Math.round(result.bid).toLocaleString("ko-KR");
          outputs[2].textContent = result.penalty ? `${upper * 100}% 미만 구간` : `${upper * 100}% 이상 구간`;
          outputs[3].textContent = result.score.toFixed(3);
          outputs[4].textContent = result.penalty ? "저가입찰 패널티 구간" : "패널티 아님";
          outputs[4].className = result.penalty ? "risk-high" : "risk-low";
          if (total) total.textContent = technical === null ? "기술 실점수 확인 필요" : (technical + result.score).toFixed(3);
          error.textContent = "";
        } catch (err) { fail(err); }
      }
      number.addEventListener("input", () => sync(number));
      slider.addEventListener("input", () => sync(slider));
      sync(number);
    } catch (err) { fail(err); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
