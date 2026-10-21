"use strict";

function calculateDday(deadlineText, now = new Date()) {
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(deadlineText);
  if (!dateOnly && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$/.test(deadlineText)) {
    throw new Error("마감일은 YYYY-MM-DD 또는 초까지 포함한 KST 시각이어야 합니다.");
  }
  const deadline = new Date(dateOnly ? deadlineText + "T00:00:00+09:00" : deadlineText);
  if (!Number.isFinite(deadline.getTime()) || !Number.isFinite(now.getTime())) {
    throw new Error("마감일 또는 현재 시각이 유효하지 않습니다.");
  }
  const kstParts = date => new Date(date.getTime() + 9 * 3600000).toISOString();
  const deadlineKst = kstParts(deadline);
  const expected = dateOnly ? deadlineText : deadlineText.slice(0, 19);
  if ((dateOnly ? deadlineKst.slice(0, 10) : deadlineKst.slice(0, 19)) !== expected) {
    throw new Error("존재하지 않는 날짜 또는 시각입니다.");
  }
  const diff = Math.round(
    (Date.parse(deadlineKst.slice(0, 10)) - Date.parse(kstParts(now).slice(0, 10))) / 86400000
  );
  const expired = dateOnly ? diff < 0 : now >= deadline;
  return {
    diff,
    expired,
    label: diff > 0 ? `D-${diff}` : diff < 0 ? `D+${-diff} (경과)` : expired ? "D-Day (마감 경과)" : "D-Day",
    date: dateOnly ? `${deadlineText} (시각 미확인)` : deadline.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })
  };
}

(function () {
  function init() {
    const error = document.getElementById("dday-error");
    try {
      const config = document.getElementById("dday-config");
      const number = document.getElementById("dday-num");
      const date = document.getElementById("dday-date");
      if (!config || !number || !date || !error) throw new Error("D-Day 필수 표시 영역이 없습니다.");
      const result = calculateDday(config.dataset.deadline || "");
      number.textContent = result.label;
      date.textContent = result.date;
      error.textContent = "";
    } catch (err) {
      const message = `D-Day 계산 불가: ${err.message}`;
      if (error) error.textContent = message;
      console.error(message);
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
