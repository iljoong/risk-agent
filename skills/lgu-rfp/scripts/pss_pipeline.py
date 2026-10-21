#!/usr/bin/env python3
"""
scripts/pss_pipeline.py — 보존된 선택적 PSS 데이터 파이프라인
LG U+ PSS xlsx 4단계 필터 ETL. lgu-rfp 기본 다섯 보고서에서는 실행하지 않음.
─────────────────────────────────────────────────────────────────────────────
[사용법] 승인된 PSS xlsx를 사용자가 제공한 뒤,
        아래 명령으로 파싱·필터링 결과를 JSON으로 받는다.
 
  python "<실제 스킬 위치의 pss_pipeline.py 절대 경로>" \
      --xlsx <다운로드된 xlsx 경로> \
      --keywords "전용회선,국가융합망" \
      --position retention \
      [--industry "공공,교육,금융"] \
      [--max-rows 20]
 
[출력] stdout — JSON
  {
    "fetch_status": "success",
    "total_rows": 1234,
    "filter1_passed": N,          # 대표서비스 키워드 일치
    "filter2_passed": N,          # 제안결과=수주
    "filter3_passed": N,          # 업종=공공/교육/금융
    "final_count": N,
    "position": "retention",
    "position_dist": {"retention": N, "winback": N, "신규": N, "기타": N},
    "proposal_date_source": "제안서제출",   ← Gate-9 마커값
    "proposal_date_stats": {"제안서제출": N, "제안발표": N, "요청일": N},
    "keywords_used": ["전용회선", "국가융합망"],
    "rows": [
      {
        "사업명": "...", "고객명": "...", "대표서비스": "...",
        "제안년월": "YYYY-MM", "제안년월_출처": "제안서제출|제안발표|요청일",
        "업종": "...", "사업성격": "...", "제안결과": "수주", "영업담당": "..."
      }, ...
    ]
  }
 
[PSS 컬럼 인덱스 — 원본 고정 스키마, 0-based; 실행 전 실제 헤더 확인 필요]
  고객명=10  사업명=11  영업담당=12  영업사원=14  요청일=15
  업종=17    대표서비스=18  사업성격=19  RFP공고=20
  제안서제출=21(MUST, ④ 1순위)  제안발표=22(fallback-2)
  수주결과통보일=23  제안결과=37
 
[원본 보고서용 메타데이터 — lgu-rfp 검증 게이트가 아님]
  Gate-4 : fetch_status="success"  → data-pss-fetch="success"
  Gate-5 : filter1_passed          → data-filter1-passed
  Gate-6 : filter2_passed          → data-filter2-passed
  Gate-7 : filter3_passed          → data-filter3-passed
  Gate-9 : proposal_date_source    → data-proposal-date-source="제안서제출"
 
[④ 제안년월 fallback 체인 — § 4.5.3.1]
  1순위: 제안서제출(col[21])  2순위: 제안발표(col[22])
  3순위: 요청일(col[15]) — 사용 시 "YYYY-MM (요청일 기준)" 로 표기
 
[의존성] openpyxl. 사전 설치를 가정하지 않음.
유사도 점수/증빙 파일 링크를 제공하지 않는 필터이며 유사도 순위로 해석 금지.
"""
 
import sys
import json
import argparse
from datetime import datetime
 
try:
    import openpyxl
except ImportError:
    print(json.dumps({
        "fetch_status": "failed",
        "error": "openpyxl 미설치 — xlsx 스킬 환경에서 실행하거나 pip install openpyxl 필요",
    }, ensure_ascii=False))
    sys.exit(1)
 
# ─── PSS 컬럼 인덱스 (0-based, § 4.5.0.3) ─────────────────────────────────
COL = {
    "고객명":         10,
    "사업명":         11,
    "영업담당":       12,
    "영업사원":       14,
    "요청일":         15,   # fallback-3 전용 (컨설팅팀 접수일, ④ 제안년월에 최후순위만 사용)
    "업종":           17,
    "대표서비스":     18,
    "사업성격":       19,
    "RFP공고":        20,
    "제안서제출":     21,   # ④ 제안년월 1순위 MUST
    "제안발표":       22,   # ④ 제안년월 fallback-2
    "수주결과통보일": 23,
    "제안결과":       37,
}
 
POSITION_ALIASES = {
    "retention": ["retention", "리텐션"],
    "winback":   ["win-back", "윈백", "winback"],
    "신규":      ["신규", "new"],
}
 
DEFAULT_INDUSTRY = {"공공", "교육", "금융"}
 
 
# ─── 유틸리티 ──────────────────────────────────────────────────────────────
 
def normalize_position(raw):
    """사용자 입력 포지션 → 내부 키 (retention/winback/신규/미정)."""
    pl = raw.lower().strip()
    for key, aliases in POSITION_ALIASES.items():
        if pl in [a.lower() for a in aliases] or pl == key:
            return key
    return "미정"
 
 
def parse_date(val):
    """datetime 객체 또는 날짜 문자열 → 'YYYY-MM'. 파싱 실패 시 None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m")
    s = str(val).strip()
    if not s or s in ("-", "N/A", "없음", ""):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m"):
        try:
            return datetime.strptime(s[: len(fmt)], fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None
 
 
def cell_val(row, col_idx):
    """0-based col_idx → Cell.value (범위 초과 시 None)."""
    try:
        return row[col_idx].value
    except (IndexError, AttributeError):
        return None
 
 
def str_val(row, col_idx, default=""):
    """cell_val → 공백 제거된 문자열. 값 없으면 default."""
    v = cell_val(row, col_idx)
    return str(v).strip() if v is not None else default
 
 
# ─── 메인 파이프라인 ──────────────────────────────────────────────────────────
 
def run_pipeline(xlsx_path, keywords, position, allowed_industry, max_rows):
    """
    PSS xlsx를 읽어 4단계 필터를 적용하고 결과 dict를 반환한다.
    에러 시 {"fetch_status": "failed", "error": "..."}를 반환 (예외 raise 없음).
    """
    try:
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    except Exception as e:
        return {"fetch_status": "failed", "error": f"xlsx 로딩 실패: {e}"}
 
    ws = wb.worksheets[0]
    rows_iter = ws.iter_rows()
 
    # 헤더 행 건너뜀
    try:
        next(rows_iter)
    except StopIteration:
        return {"fetch_status": "failed", "error": "시트가 비어 있습니다."}
 
    total = 0
    f1, f2, f3 = [], [], []
 
    # ── 필터 1: 대표서비스 키워드 일치 (§ 4.5.2.1) ────────────────────────
    for row in rows_iter:
        total += 1
        svc = str_val(row, COL["대표서비스"])
        if any(kw in svc for kw in keywords):
            f1.append(row)
 
    # ── 필터 2: 제안결과 = "수주" (§ 4.5.2.2) ────────────────────────────
    for row in f1:
        if str_val(row, COL["제안결과"]) == "수주":
            f2.append(row)
 
    # ── 필터 3: 업종 = 공공/교육/금융 (§ 4.5.2.3) ────────────────────────
    for row in f2:
        industry = str_val(row, COL["업종"])
        if any(a in industry for a in allowed_industry):
            f3.append(row)
 
    # ── 필터 4: 사업성격 정렬 + 그룹 내 제안서제출 내림차순 (§ 4.5.2.4) ──
    pos_aliases_lower = [a.lower() for a in POSITION_ALIASES.get(position, [])]
 
    def sort_key(row):
        biz = str_val(row, COL["사업성격"]).lower()
        # 포지션 일치 → 0(우선), 불일치 → 1(후순)
        pos_rank = 0 if any(a in biz for a in pos_aliases_lower) else 1
        # 제안서제출 내림차순: 날짜 없으면 최후순위
        d = parse_date(cell_val(row, COL["제안서제출"]))
        if d:
            y, m = d.split("-")
            date_rank = (-int(y), -int(m))
        else:
            date_rank = (9999, 99)
        return (pos_rank,) + date_rank
 
    f3.sort(key=sort_key)
    final = f3[:max_rows]
 
    # ── ④ 제안년월 fallback 체인 + 통계 (§ 4.5.3.1) ─────────────────────
    date_stats = {"제안서제출": 0, "제안발표": 0, "요청일": 0}
 
    def proposal_date(row):
        v = parse_date(cell_val(row, COL["제안서제출"]))
        if v:
            date_stats["제안서제출"] += 1
            return v, "제안서제출"
        v = parse_date(cell_val(row, COL["제안발표"]))
        if v:
            date_stats["제안발표"] += 1
            return v, "제안발표"
        v = parse_date(cell_val(row, COL["요청일"]))
        if v:
            date_stats["요청일"] += 1
            return v + " (요청일 기준)", "요청일"
        return None, None
 
    # ── 포지션 분포 집계 (전체 필터3 기준) ──────────────────────────────
    pos_dist = {"retention": 0, "winback": 0, "신규": 0, "기타": 0}
    for row in f3:
        biz = str_val(row, COL["사업성격"]).lower()
        matched = False
        for key, aliases in POSITION_ALIASES.items():
            if any(a.lower() in biz for a in aliases):
                pos_dist[key] += 1
                matched = True
                break
        if not matched:
            pos_dist["기타"] += 1
 
    # ── 최종 행 직렬화 ──────────────────────────────────────────────────
    rows_out = []
    for row in final:
        date_val, date_src = proposal_date(row)
        rows_out.append({
            "사업명":       str_val(row, COL["사업명"],   "확인 필요"),
            "고객명":       str_val(row, COL["고객명"],   "확인 필요"),
            "대표서비스":   str_val(row, COL["대표서비스"]),
            "제안년월":     date_val or "확인 필요",
            "제안년월_출처": date_src or "",
            "업종":         str_val(row, COL["업종"]),
            "사업성격":     str_val(row, COL["사업성격"]),
            "제안결과":     str_val(row, COL["제안결과"]),
            "영업담당":     str_val(row, COL["영업담당"]) or str_val(row, COL["영업사원"]),
        })
 
    return {
        "fetch_status":        "success",
        "total_rows":          total,
        "filter1_passed":      len(f1),    # Gate-5
        "filter2_passed":      len(f2),    # Gate-6
        "filter3_passed":      len(f3),    # Gate-7
        "final_count":         len(rows_out),
        "position":            position,
        "position_dist":       pos_dist,
        "proposal_date_source": "제안서제출",  # Gate-9 마커 — dominant source 고정
        "proposal_date_stats": date_stats,
        "keywords_used":       keywords,
        "rows":                rows_out,
    }
 
 
def main():
    parser = argparse.ArgumentParser(
        description="선택적 PSS xlsx 4단계 필터 ETL (lgu-rfp)"
    )
    parser.add_argument(
        "--xlsx", required=True,
        help="다운로드된 PSS xlsx 경로 (ReadFileContent 결과 경로)",
    )
    parser.add_argument(
        "--keywords", required=True,
        help="대표서비스 매칭 키워드, 쉼표 구분 (예: '전용회선,국가융합망')",
    )
    parser.add_argument(
        "--position", default="미정",
        help="RFP 포지션: retention | winback | 신규 | 미정",
    )
    parser.add_argument(
        "--industry", default="공공,교육,금융",
        help="허용 업종, 쉼표 구분 (기본값: 공공,교육,금융)",
    )
    parser.add_argument(
        "--max-rows", type=int, default=20,
        help="최종 출력 최대 행 수 (기본값: 20)",
    )
    args = parser.parse_args()
 
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        print(json.dumps({"fetch_status": "failed", "error": "--keywords 값이 비어 있습니다."},
                         ensure_ascii=False))
        sys.exit(1)
 
    position         = normalize_position(args.position)
    allowed_industry = {i.strip() for i in args.industry.split(",") if i.strip()} \
                       or DEFAULT_INDUSTRY
 
    result = run_pipeline(args.xlsx, keywords, position, allowed_industry, args.max_rows)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("fetch_status") == "success" else 1)
 
 
if __name__ == "__main__":
    main()

 