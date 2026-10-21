#!/usr/bin/env python3
"""Validate one generated RFP report's structure, assets, and workbook package."""

import argparse
import json
import math
import posixpath
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


SKILL_ROOT = Path(__file__).resolve().parents[1]
OVERVIEW_FIELDS = (
    "project-name notice-name notice-number issuer beneficiary scope equipment budget "
    "estimated-price installments project-period service-period contract-method "
    "estimated-price-method differential-scoring eligibility consortium subcontracting "
    "bid-guarantee contract-guarantee warranty acceptance delay-damages liability sla contact special-notes"
).split()
SCHEDULE_EVENTS = (
    "notice prespec-comments questions answers briefing bid-open bid-close opening "
    "presentation preferred-bidder contract-start proposal-close"
).split()
MEMBER_DOCS = set((
    "registration corporate-register business-register credit financial national-tax "
    "local-tax insurance security-pledge background-consent agreement share"
).split())
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    line: int = 0
    children: list["Element"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    parent: "Element | None" = None

    def descendants(self, tag=None):
        for child in self.children:
            if tag is None or child.tag == tag:
                yield child
            yield from child.descendants(tag)

    def text(self):
        return "".join(self.text_parts) + "".join(child.text() for child in self.children)

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()

    def visible(self):
        node = self
        while node is not None:
            style = (node.attrs.get("style") or "").replace(" ", "").lower()
            if "hidden" in node.attrs or node.attrs.get("aria-hidden") == "true" or "display:none" in style or "visibility:hidden" in style:
                return False
            node = node.parent
        return bool(self.text().strip())


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Element("root", {})
        self.stack = [self.root]
        self.errors = []

    def handle_starttag(self, tag, attrs):
        node = Element(tag, dict(attrs), self.getpos()[0], parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1].tag != tag:
            self.errors.append(f"line {self.getpos()[0]}: unexpected closing tag </{tag}>")
            return
        self.stack.pop()

    def handle_data(self, data):
        self.stack[-1].text_parts.append(data)


def validate_report(mode, html_path, xlsx_path=None, asset_root=None):
    asset_root = Path(asset_root) if asset_root is not None else SKILL_ROOT / "assets"
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    parser = ReportParser()
    parser.feed(Path(html_path).read_text(encoding="utf-8"))
    parser.close()
    errors.extend(parser.errors)
    require(len(parser.stack) == 1, "HTML has unclosed tags")
    nodes = list(parser.root.descendants())
    ids = [node.attrs["id"] for node in nodes if node.attrs.get("id")]
    require(len(ids) == len(set(ids)), "HTML IDs must be unique")
    by_id = {node.attrs["id"]: node for node in nodes if node.attrs.get("id")}

    def get(identifier):
        node = by_id.get(identifier)
        require(node is not None, f"Missing #{identifier}")
        return node

    def control(identifier, tag, input_type=None):
        node = get(identifier)
        require(node is not None and node.tag == tag, f"#{identifier} must be {tag}")
        if input_type is not None:
            require(node is not None and node.attrs.get("type") == input_type, f"#{identifier} must be type={input_type}")
        return node

    def class_visible(name, scope=None):
        return any(node.has_class(name) and node.visible() for node in (scope.descendants() if scope else nodes))

    def asset(name):
        matches = [node for node in nodes if node.tag == "script" and node.attrs.get("data-asset") == name]
        require(len(matches) == 1, f"Expected exactly one bundled script: {name}")
        if len(matches) == 1:
            expected = (asset_root / name).read_text(encoding="utf-8").strip()
            require(matches[0].text().strip() == expected, f"Bundled script content differs: {name}")
            require("src" not in matches[0].attrs, f"Script must be inline: {name}")

    def table_rows(identifier):
        table = get(identifier)
        if table is None:
            return []
        require(table.tag == "table", f"#{identifier} must be a table")
        require(any(table.descendants("thead")), f"#{identifier} needs thead")
        bodies = list(table.descendants("tbody"))
        require(bool(bodies), f"#{identifier} needs tbody")
        return [row for body in bodies for row in body.children if row.tag == "tr"]

    def fields(rows, attribute, expected):
        counts = Counter(row.attrs.get(attribute) for row in rows)
        for key in expected:
            require(counts[key] == 1, f"Expected one {attribute}={key}, found {counts[key]}")

    require(any(node.tag == "meta" and (node.attrs.get("charset") or "").lower() == "utf-8" for node in nodes), "Missing UTF-8 meta")
    require(any(node.tag == "html" and node.attrs.get("lang") == "ko" for node in nodes), "Missing Korean HTML language")
    body = get(mode)
    require(body is not None and body.tag == "section" and body.has_class("page-panel"), "Missing report section.page-panel")
    for identifier in ("source-inventory", "diagnostics"):
        node = get(identifier)
        require(node is not None and bool(node.text().strip()), f"#{identifier} must have content")
    require(by_id.get("diagnostics") is not None and by_id["diagnostics"].tag == "details", "Diagnostics must be a details block")
    css = (asset_root / "report.css").read_text(encoding="utf-8").strip()
    require(any(node.tag == "style" and node.text().strip() == css for node in nodes), "Missing unmodified bundled report CSS")
    require(not any(node.tag == "script" and "src" in node.attrs for node in nodes), "External scripts are not allowed")
    require(not any(node.tag == "link" and "stylesheet" in (node.attrs.get("rel") or "") for node in nodes), "External stylesheets are not allowed")

    coverage = get("source-coverage")
    if coverage is not None:
        attrs = coverage.attrs
        require(attrs.get("data-unit") in ("pages", "sections"), "Invalid coverage unit")
        require(attrs.get("data-scanned") in ("yes", "no", "unknown"), "Invalid scanned state")
        require(attrs.get("data-partial") in ("yes", "no"), "Invalid partial state")
        values = [attrs.get("data-covered") or "", attrs.get("data-total") or ""]
        require(all(value == "unknown" or value.isascii() and value.isdigit() for value in values), "Invalid coverage counts")
        known = all(value.isascii() and value.isdigit() for value in values)
        partial = not known
        if known:
            covered, total = map(int, values)
            require(0 <= covered <= total and total > 0, "Coverage counts must satisfy 0 <= covered <= total and total > 0")
            partial = covered < total
        require(not partial or attrs.get("data-partial") == "yes", "Partial/unknown coverage must declare partial=yes")
        if partial or attrs.get("data-partial") == "yes" or attrs.get("data-scanned") != "no":
            require(class_visible("coverage-warning"), "Partial/scanned/unknown input needs a visible coverage warning")

    if mode == "overview":
        rows = table_rows("overview-table")
        fields(rows, "data-field", OVERVIEW_FIELDS)
        for field_name, attribute, expected in (
            ("eligibility", "data-qualification", "licenses experience personnel finance security region consortium".split()),
            ("contact", "data-contact", "department person phone email address-system".split()),
        ):
            row = next((row for row in rows if row.attrs.get("data-field") == field_name), None)
            fields(list(row.descendants()) if row else [], attribute, expected)
    elif mode == "schedule":
        fields(table_rows("schedule-table"), "data-event", SCHEDULE_EVENTS)
        get("critical-dates")
        config = get("dday-config")
        for identifier in ("dday-num", "dday-date", "dday-error"):
            get(identifier)
        if config is not None:
            deadline = config.attrs.get("data-deadline") or ""
            if deadline:
                from datetime import datetime
                try:
                    parsed = datetime.fromisoformat(deadline)
                    date_only = re.fullmatch(r"\d{4}-\d{2}-\d{2}", deadline)
                    timestamp = re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00", deadline)
                    require(bool(date_only) or bool(timestamp) and parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 32400, "Deadline must be a date or second-precision KST timestamp")
                except ValueError:
                    require(False, "Invalid deadline")
            else:
                require(class_visible("deadline-warning"), "Unknown deadline needs a visible warning")
        asset("dday.js")
    elif mode == "evaluation":
        table_rows("score-table")
        status_node = get("formula-status")
        status = status_node.attrs.get("data-status") if status_node else None
        require(status in ("verified", "assumption", "unavailable"), "Invalid formula status")
        for identifier in ("sim-formula-label", "sim-threshold-label"):
            node = get(identifier)
            require(node is not None and bool(node.text().strip()), f"#{identifier} needs source/status text")
        supported = status in ("verified", "assumption")
        if status != "verified":
            require(class_visible("formula-warning"), "Unverified formula needs a visible warning")
        if supported:
            config = get("sim-constants")
            if config is not None:
                require(config.attrs.get("data-formula") == "ratio-penalty-v1", "Unsupported engine formula")
                try:
                    est, weight, upper, lower = [float(config.attrs.get(key) or "") for key in (
                        "data-est-price", "data-price-weight", "data-threshold-upper", "data-threshold-lower"
                    )]
                    require(all(math.isfinite(value) for value in (est, weight, upper, lower)) and est > 0 and weight > 0 and 0 < lower < upper <= 1, "Invalid price constants")
                except ValueError:
                    require(False, "Missing/non-numeric price constants")
            number = control("sim-ratio-num", "input", "number")
            slider = control("sim-ratio-slider", "input", "range")
            if number is not None and slider is not None:
                try:
                    minimum, maximum = [float(number.attrs.get(key) or "") for key in ("min", "max")]
                    require(math.isfinite(minimum) and math.isfinite(maximum) and 0 < minimum < maximum, "Invalid ratio input range")
                    require(float(slider.attrs.get("min") or "") == minimum and float(slider.attrs.get("max") or "") == maximum, "Ratio input ranges differ")
                    if config is not None:
                        upper_percent = float(config.attrs.get("data-threshold-upper") or "") * 100
                        lower_percent = float(config.attrs.get("data-threshold-lower") or "") * 100
                        require(minimum <= lower_percent - 1 and maximum >= upper_percent + 1, "Ratio range must include both threshold +/-1% boundaries")
                except ValueError:
                    require(False, "Missing/non-numeric ratio input range")
            for identifier in ("price-error", "sim-est-display",
                               "sim-weight-display", "r-ratio", "r-bid", "r-branch", "r-score", "r-limit", "r-penalty"):
                get(identifier)
            asset("price-engine.js")
        else:
            require(not any(node.attrs.get("data-asset") == "price-engine.js" for node in nodes), "Unavailable formula must not run price engine")
        require(xlsx_path is not None, "Evaluation requires --xlsx")
        if xlsx_path is not None:
            workbook = Path(xlsx_path).resolve()
            links = []
            for node in nodes:
                if node.tag == "a":
                    href = urlparse(node.attrs.get("href") or "")
                    if not href.scheme and not href.netloc and href.path:
                        links.append((Path(html_path).parent / unquote(href.path)).resolve())
            require(workbook in links, "HTML must link to the supplied XLSX")
            errors.extend(validate_workbook(workbook, supported))
    elif mode == "strategy":
        rows = table_rows("risk-table")
        table = by_id.get("risk-table")
        headers = [node for head in table.descendants("thead") for node in head.descendants("th")] if table else []
        require(len(headers) == 6, "Risk table needs exactly six headers")
        require(bool(rows), "Risk table needs a result row")
        require(all(len([cell for cell in row.children if cell.tag == "td"]) == 6 and all(cell.text().strip() for cell in row.children if cell.tag == "td") for row in rows), "Risk rows need six nonempty cells")
        get("personnel-risks")
        get("differentiation")
        trends = get("customer-trends")
        blocks = list(trends.descendants()) if trends else []
        fields(blocks, "data-trend", [f"B-{number}" for number in range(1, 7)])
        for block in (node for node in blocks if node.attrs.get("data-trend")):
            sourced = any(node.tag == "a" and urlparse(node.attrs.get("href") or "").scheme in ("http", "https") for node in block.descendants())
            require(sourced or class_visible("research-unavailable", block), f"{block.attrs['data-trend']} needs a public source or visible research limitation")
    elif mode == "checklist":
        rows = table_rows("checklist-table")
        require(len(rows) >= 45, "Checklist needs at least 45 preparation-baseline rows")
        table = by_id.get("checklist-table")
        headers = [node for head in table.descendants("thead") for node in head.descendants("th")] if table else []
        require(len(headers) == 11 and headers[-1].text().strip() == "상태", "Checklist needs eleven headers ending in 상태")
        doc_ids = []
        for row in rows:
            require("data-row" in row.attrs, "Checklist row lacks data-row")
            identifier = row.attrs.get("data-doc-id")
            require(bool(identifier), "Checklist row lacks document identity")
            doc_ids.append(identifier)
            require(row.attrs.get("data-stage") in ("registration", "bid", "post-award"), "Invalid checklist stage")
            require(row.attrs.get("data-requirement") in ("required", "recommended", "not-applicable", "unknown"), "Missing/invalid requirement classification")
            cells = [cell for cell in row.children if cell.tag == "td"]
            require(len(cells) == 11, "Checklist row needs eleven cells")
            checks = [node for node in row.descendants("input") if node.has_class("doc-check")]
            require(len(checks) == 1 and checks[0].attrs.get("type") == "checkbox" and checks[0].attrs.get("data-doc-id") == identifier and bool(checks[0].attrs.get("id")), "Checklist row needs one uniquely identified matching checkbox")
            if checks and row.attrs.get("data-requirement") == "not-applicable":
                require("disabled" in checks[0].attrs, "Not-applicable checkbox must be disabled")
            require(bool(cells) and any(node.has_class("status-badge") for node in cells[-1].descendants()), "Last cell needs a status badge")
            require(any("data-evidence" in node.attrs and node.text().strip() for node in row.descendants()), "Checklist row needs evidence/baseline provenance")
        require(len(doc_ids) == len(set(doc_ids)), "Checklist document identities must be unique")
        config = get("checklist-config")
        if config:
            require((config.attrs.get("data-key") or "").startswith("rfp-checklist-"), "Invalid checklist storage key")
            state = config.attrs.get("data-consortium")
            require(state in ("solo", "consortium", "undecided", "prohibited"), "Invalid consortium state")
            if state in ("consortium", "undecided"):
                members_node = get("consortium-members")
                members = [node.attrs["data-member-id"] for node in members_node.descendants() if node.attrs.get("data-member-id")] if members_node else []
                require(bool(members) and len(members) == len(set(members)), "Declare unique consortium members")
                for member in members:
                    keys = {row.attrs.get("data-member-doc") for row in rows if row.attrs.get("data-member") == member}
                    require(MEMBER_DOCS <= keys, f"Member {member} lacks atomic baseline document types: {sorted(MEMBER_DOCS - keys)}")
                require(all(not row.attrs.get("data-member") or row.attrs["data-member"] in members for row in rows), "Undeclared checklist member")
        for identifier in ("done-count", "total-count", "done-pct", "progress-bar", "last-updated",
                           "stage-progress", "reset-checklist", "filter-unchecked", "checklist-error"):
            get(identifier)
        control("progress-bar", "progress")
        control("reset-checklist", "button")
        control("filter-unchecked", "input", "checkbox")
        resources = get("internal-resources")
        links = {node.attrs.get("href") for node in resources.descendants("a") if urlparse(node.attrs.get("href") or "").hostname == "lgupluscorp.sharepoint.com"} if resources else set()
        require(len(links) >= 3, "Need three distinct internal reference links")
        asset("checklist.js")
    else:
        require(False, f"Unknown report mode: {mode}")
    return errors


def validate_workbook(path, supported):
    try:
        with zipfile.ZipFile(path) as archive:
            archive.read("[Content_Types].xml")
            root = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {node.attrib["Id"]: node.attrib["Target"] for node in rels}
            sheets = {node.attrib["name"]: node for node in root.findall(".//{*}sheet")}
            if set(sheets) != {"산식 설명", "시뮬레이션", "구간표"}:
                return ["Workbook must contain exactly 산식 설명, 시뮬레이션, 구간표"]
            for name, sheet in sheets.items():
                relationship = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                target = targets[relationship]
                member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
                worksheet = ET.fromstring(archive.read(member))
                if name != "산식 설명":
                    formulas = worksheet.findall(".//{*}f")
                    if supported and not formulas:
                        return [f"Supported simulation sheet has no formulas: {name}"]
                    if not supported and formulas:
                        return [f"Unavailable simulation must not provide calculation formulas: {name}"]
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError) as err:
        return [f"Cannot validate XLSX package: {err}"]
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("overview", "schedule", "evaluation", "strategy", "checklist"))
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--xlsx", type=Path)
    parser.add_argument("--asset-root", type=Path)
    args = parser.parse_args(argv)
    try:
        errors = validate_report(args.mode, args.html, args.xlsx, args.asset_root)
    except (OSError, UnicodeError) as err:
        errors = [f"Cannot read report/resources: {err}"]
    print(json.dumps({"status": "FAIL" if errors else "PASS", "mode": args.mode,
                      "html": str(args.html), "errors": errors,
                      "scope": "Structure/assets/package only; source truth, browser behavior, and workbook recalculation require separate verification."},
                     ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
