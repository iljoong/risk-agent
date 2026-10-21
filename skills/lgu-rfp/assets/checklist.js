"use strict";

(function () {
  function init() {
    const error = document.getElementById("checklist-error");
    function warn(err) {
      const message = `체크리스트 저장/초기화 오류: ${err.message}. 새로고침 후 상태 유지가 보장되지 않습니다.`;
      if (error) error.textContent = message;
      console.error(message);
    }
    try {
      const get = id => {
        const element = document.getElementById(id);
        if (!element) throw new Error(`필수 표시 영역 누락: ${id}`);
        return element;
      };
      const config = get("checklist-config");
      if (!config.dataset.key) throw new Error("사업별 저장 키가 없습니다.");
      if (!error) throw new Error("체크리스트 오류 표시 영역이 없습니다.");
      const table = get("checklist-table");
      const rows = [...table.querySelectorAll("tr[data-row]")];
      const reset = get("reset-checklist");
      const filter = get("filter-unchecked");
      const done = get("done-count"), total = get("total-count");
      const percent = get("done-pct"), progress = get("progress-bar");
      const updated = get("last-updated"), stages = get("stage-progress");
      const entries = rows.map(row => {
        const checkbox = row.querySelector(".doc-check");
        const badge = row.querySelector(".status-badge");
        if (!checkbox || !badge || !row.dataset.docId || checkbox.dataset.docId !== row.dataset.docId) {
          throw new Error("행의 식별자/체크박스/상태 배지를 확인하세요.");
        }
        const applicable = row.dataset.requirement !== "not-applicable";
        checkbox.disabled = !applicable;
        return { row, checkbox, badge, applicable };
      });
      if (new Set(entries.map(entry => entry.row.dataset.docId)).size !== entries.length) {
        throw new Error("중복 서류 저장 식별자가 있습니다.");
      }
      function refresh() {
        const active = entries.filter(entry => entry.applicable);
        const count = active.filter(entry => entry.checkbox.checked).length;
        done.textContent = String(count);
        total.textContent = String(active.length);
        const value = active.length ? Math.round(count / active.length * 100) : 0;
        percent.textContent = String(value);
        progress.value = value;
        const stageLabels = { registration: "사업참여등록", bid: "입찰", "post-award": "낙찰 후" };
        stages.textContent = Object.keys(stageLabels).map(stage => {
          const group = active.filter(entry => entry.row.dataset.stage === stage);
          return `${stageLabels[stage]}: ${group.filter(entry => entry.checkbox.checked).length}/${group.length}`;
        }).join(" | ");
        entries.forEach(({ row, checkbox, badge, applicable }) => {
          const checked = applicable && checkbox.checked;
          row.classList.toggle("checked", checked);
          badge.textContent = !applicable ? "해당 없음" : checked ? "완료" : "준비 중";
          badge.classList.toggle("status-done", checked);
          badge.classList.toggle("status-todo", applicable && !checked);
          row.hidden = filter.checked && (checked || !applicable);
        });
      }
      function save() {
        const state = { version: 1, updatedAt: new Date().toISOString(), checks: {} };
        entries.forEach(entry => { state.checks[entry.row.dataset.docId] = entry.applicable && entry.checkbox.checked; });
        updated.textContent = state.updatedAt;
        try {
          localStorage.setItem(config.dataset.key, JSON.stringify(state));
          error.textContent = "";
        } catch (err) { warn(err); }
      }
      function change() { refresh(); save(); }
      entries.forEach(({ row, checkbox, applicable }) => {
        checkbox.addEventListener("change", change);
        row.addEventListener("click", event => {
          if (!applicable || event.target.closest("a, button, input, label, select, textarea")) return;
          checkbox.checked = !checkbox.checked;
          change();
        });
      });
      filter.addEventListener("change", refresh);
      // Native confirm() is blocked in an opaque-origin sandbox; keep confirmation report-local.
      const confirmation = document.createElement("dialog");
      confirmation.setAttribute("aria-label", "체크리스트 전체 해제 확인");
      const question = document.createElement("p");
      question.textContent = "모든 체크를 해제하시겠습니까?";
      const accept = document.createElement("button");
      accept.type = "button";
      accept.textContent = "초기화 확인";
      const cancel = document.createElement("button");
      cancel.type = "button";
      cancel.textContent = "취소";
      confirmation.append(question, accept, cancel);
      document.body.append(confirmation);
      reset.addEventListener("click", () => {
        confirmation.showModal();
      });
      cancel.addEventListener("click", () => confirmation.close());
      accept.addEventListener("click", () => {
        entries.forEach(entry => { entry.checkbox.checked = false; });
        change();
        confirmation.close();
      });
      try {
        const raw = localStorage.getItem(config.dataset.key);
        if (raw !== null) {
          const state = JSON.parse(raw);
          if (!state || state.version !== 1 || typeof state.updatedAt !== "string" ||
              !state.checks || typeof state.checks !== "object" || Array.isArray(state.checks) ||
              Object.values(state.checks).some(value => typeof value !== "boolean")) {
            throw new Error("저장된 체크리스트 데이터 형식이 올바르지 않습니다.");
          }
          entries.forEach(entry => {
            entry.checkbox.checked = entry.applicable && state.checks[entry.row.dataset.docId] === true;
          });
          updated.textContent = state.updatedAt;
        }
      } catch (err) { warn(err); }
      refresh();
    } catch (err) { warn(err); }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else init();
})();
