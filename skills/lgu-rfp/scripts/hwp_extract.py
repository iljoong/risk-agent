#!/usr/bin/env python3
# lgu-rfp — HWP/HWPX text extraction
# 한글 문서 결정론적 텍스트 추출기. Python 표준 라이브러리만 사용 (무의존성).
#   - HWPX (.hwpx): ZIP + OWPML XML → 텍스트 + 표(마크다운/탭)
#   - 바이너리 HWP (.hwp): OLE/CFB 컨테이너 직접 파싱 + BodyText zlib 해제
#                          + PARA_TEXT 레코드 컨트롤 문자 디코딩 → 본문 텍스트
# 둘 다 외부 라이브러리(olefile/pyhwp 등) 없이 동작.
"""
사용:
    python3 hwp_extract.py 입력.hwpx [-o 출력.md] [--format md|txt]
    python3 hwp_extract.py 입력.hwp  [-o 출력.txt]
 
- 입력 형식은 매직 바이트로 자동 판별 (PK→HWPX, D0CF11E0→바이너리 HWP)
- -o 미지정 시 stdout 출력
- --format md (기본): HWPX 표를 마크다운 테이블로. (바이너리 HWP는 항상 평문 본문)
 
라이브러리로도 사용:
    from hwp_extract import extract, extract_hwpx, extract_hwp
    text = extract("입력.hwp")
"""
import sys
import re
import zlib
import struct
import zipfile
import argparse
import xml.etree.ElementTree as ET
 
 
# ────────────────────────────────────────────────────────────────────────
# HWPX (ZIP + OWPML XML)
# ────────────────────────────────────────────────────────────────────────
def _local(tag):
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag
 
 
def _t_text(t_el):
    return ''.join(t_el.itertext())
 
 
def _para_text(p_el):
    parts = []
 
    def rec(el):
        for node in el:
            ln = _local(node.tag)
            if ln == 'tbl':
                continue
            if ln == 't':
                parts.append(_t_text(node))
            elif ln in ('lineBreak', 'lineseg'):
                parts.append('\n')
            elif ln == 'tab':
                parts.append('\t')
            else:
                rec(node)
 
    rec(p_el)
    return ''.join(parts)
 
 
def _cell_text(tc_el):
    texts = []
    for p in tc_el.iter():
        if _local(p.tag) == 'p':
            txt = _para_text(p).strip()
            if txt:
                texts.append(txt)
    return ' '.join(' '.join(texts).split())
 
 
def _render_table_md(tbl_el):
    rows = []
    for tr in tbl_el:
        if _local(tr.tag) != 'tr':
            continue
        cells = [_cell_text(tc) for tc in tr if _local(tc.tag) == 'tc']
        if cells:
            rows.append(cells)
    if not rows:
        return ''
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]
    out = ['| ' + ' | '.join(c.replace('|', '\\|') for c in rows[0]) + ' |',
           '| ' + ' | '.join(['---'] * ncol) + ' |']
    for r in rows[1:]:
        out.append('| ' + ' | '.join(c.replace('|', '\\|') for c in r) + ' |')
    return '\n'.join(out)
 
 
def _render_table_txt(tbl_el):
    lines = []
    for tr in tbl_el:
        if _local(tr.tag) != 'tr':
            continue
        cells = [_cell_text(tc) for tc in tr if _local(tc.tag) == 'tc']
        if cells:
            lines.append('\t'.join(cells))
    return '\n'.join(lines)
 
 
def _walk_hwpx(el, out, fmt):
    for node in el:
        ln = _local(node.tag)
        if ln == 'tbl':
            out.append(_render_table_md(node) if fmt == 'md' else _render_table_txt(node))
        elif ln == 'p':
            txt = _para_text(node).strip()
            if txt:
                out.append(txt)
            for sub in node.iter():
                if _local(sub.tag) == 'tbl':
                    out.append(_render_table_md(sub) if fmt == 'md' else _render_table_txt(sub))
        else:
            _walk_hwpx(node, out, fmt)
 
 
def _section_keys(names):
    secs = [n for n in names if re.search(r'section\d+\.xml$', n, re.I)]
 
    def num(n):
        m = re.search(r'section(\d+)\.xml$', n, re.I)
        return int(m.group(1)) if m else 0
 
    return sorted(secs, key=num)
 
 
def extract_hwpx(path, fmt='md'):
    """HWPX 파일에서 본문 텍스트(+표)를 추출."""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if 'mimetype' in names:
            mt = zf.read('mimetype').decode('utf-8', 'ignore').strip().lower()
            if mt and 'hwp' not in mt:
                raise ValueError(f"HWPX가 아닌 패키지입니다(mimetype={mt}).")
        sec_names = _section_keys(names)
        if not sec_names:
            raise ValueError("Contents/section*.xml 본문을 찾을 수 없습니다.")
        blocks = []
        for sn in sec_names:
            try:
                root = ET.fromstring(zf.read(sn))
            except ET.ParseError as e:
                raise ValueError(f"HWPX 섹션 {sn} 파싱 실패 — 부분 추출로 진행하지 않습니다: {e}") from e
            _walk_hwpx(root, blocks, fmt)
    return '\n\n'.join(b for b in blocks if b and b.strip())
 
 
# ────────────────────────────────────────────────────────────────────────
# 바이너리 HWP (OLE/CFB 컨테이너 직접 파싱)
# ────────────────────────────────────────────────────────────────────────
_FREESECT = 0xFFFFFFFF
_ENDOFCHAIN = 0xFFFFFFFE
_FATSECT = 0xFFFFFFFD
_DIFSECT = 0xFFFFFFFC
_OLE_SIG = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
_HWPTAG_PARA_TEXT = 16 + 51  # = 67
 
 
class _CFB:
    """최소 기능 OLE/CFB(복합 파일) 리더 — 빅/미니 스트림 모두 지원."""
 
    def __init__(self, data):
        if data[:8] != _OLE_SIG:
            raise ValueError("OLE/CFB 서명이 아닙니다.")
        self.data = data
        self.sector_size = 1 << struct.unpack_from('<H', data, 30)[0]
        self.mini_size = 1 << struct.unpack_from('<H', data, 32)[0]
        self.num_fat = struct.unpack_from('<I', data, 44)[0]
        self.first_dir = struct.unpack_from('<I', data, 48)[0]
        self.mini_cutoff = struct.unpack_from('<I', data, 56)[0]
        self.first_minifat = struct.unpack_from('<I', data, 60)[0]
        self.num_minifat = struct.unpack_from('<I', data, 64)[0]
        self.first_difat = struct.unpack_from('<I', data, 68)[0]
        self.num_difat = struct.unpack_from('<I', data, 72)[0]
        self._build_difat()
        self._build_fat()
        self._build_dir()
        self._build_minifat()
 
    def _sector(self, sid):
        off = (sid + 1) * self.sector_size
        return self.data[off:off + self.sector_size]
 
    def _u32_array(self, buf):
        return list(struct.unpack('<%dI' % (len(buf) // 4), buf[:len(buf) // 4 * 4]))
 
    def _build_difat(self):
        difat = list(struct.unpack_from('<109I', self.data, 76))
        sid = self.first_difat
        guard = 0
        while sid not in (_ENDOFCHAIN, _FREESECT) and guard < 1 << 20:
            arr = self._u32_array(self._sector(sid))
            difat.extend(arr[:-1])
            sid = arr[-1]
            guard += 1
        self.fat_sectors = [s for s in difat if s != _FREESECT]
 
    def _build_fat(self):
        fat = []
        for sid in self.fat_sectors:
            fat.extend(self._u32_array(self._sector(sid)))
        self.fat = fat
 
    def _chain(self, start):
        out = []
        sid = start
        guard = 0
        limit = len(self.fat) + 1
        while sid not in (_ENDOFCHAIN, _FREESECT) and guard < limit:
            out.append(sid)
            sid = self.fat[sid] if sid < len(self.fat) else _ENDOFCHAIN
            guard += 1
        return out
 
    def _read_big(self, start, size):
        buf = b''.join(self._sector(s) for s in self._chain(start))
        return buf[:size] if size else buf
 
    def _build_dir(self):
        raw = self._read_big(self.first_dir, 0)
        self.entries = []
        for i in range(0, len(raw) - 127, 128):
            e = raw[i:i + 128]
            name_len = struct.unpack_from('<H', e, 64)[0]
            if name_len <= 0:
                name = ''
            else:
                name = e[:name_len - 2].decode('utf-16-le', 'ignore')
            etype = e[66]
            start = struct.unpack_from('<I', e, 116)[0]
            esize = struct.unpack_from('<Q', e, 120)[0]
            self.entries.append({'name': name, 'type': etype,
                                 'start': start, 'size': esize})
        # root entry (type 5) → 미니 스트림 컨테이너
        self.root = next((x for x in self.entries if x['type'] == 5), None)
 
    def _build_minifat(self):
        if self.num_minifat == 0 or self.first_minifat in (_ENDOFCHAIN, _FREESECT):
            self.minifat = []
            self.mini_stream = b''
            return
        mf = b''.join(self._sector(s) for s in self._chain(self.first_minifat))
        self.minifat = self._u32_array(mf)
        self.mini_stream = self._read_big(self.root['start'], self.root['size']) if self.root else b''
 
    def _read_mini(self, start, size):
        out = []
        mid = start
        guard = 0
        limit = len(self.minifat) + 1
        while mid not in (_ENDOFCHAIN, _FREESECT) and guard < limit:
            off = mid * self.mini_size
            out.append(self.mini_stream[off:off + self.mini_size])
            mid = self.minifat[mid] if mid < len(self.minifat) else _ENDOFCHAIN
            guard += 1
        buf = b''.join(out)
        return buf[:size] if size else buf
 
    def read_stream(self, entry):
        if entry['size'] < self.mini_cutoff and entry['type'] != 5:
            return self._read_mini(entry['start'], entry['size'])
        return self._read_big(entry['start'], entry['size'])
 
    def find(self, name):
        return next((e for e in self.entries
                     if e['name'] == name and e['type'] == 2), None)
 
    def find_all(self, pattern):
        rx = re.compile(pattern)
        return [e for e in self.entries if e['type'] == 2 and rx.match(e['name'])]
 
 
# PARA_TEXT 컨트롤 문자 분류 (HWP 5.0 스펙)
_CTRL_INLINE = {4, 5, 6, 7, 8, 9, 19, 20}              # 8 wchar 차지
_CTRL_EXTENDED = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}  # 8 wchar
_CTRL_CHAR1 = {0, 24, 25, 26, 27, 28, 29, 30, 31}      # 1 wchar (건너뜀)
 
 
def _parse_para_text_record(body):
    """PARA_TEXT 레코드(UTF-16LE + 컨트롤 문자)에서 보이는 텍스트만 추출."""
    n = len(body) // 2
    if n == 0:
        return ''
    u = struct.unpack('<%dH' % n, body[:n * 2])
    out = []
    i = 0
    while i < n:
        ch = u[i]
        if ch >= 32:
            out.append(chr(ch))
            i += 1
        elif ch in (10, 13):
            out.append('\n')
            i += 1
        elif ch == 9:                 # 탭(인라인 컨트롤)
            out.append('\t')
            i += 8
        elif ch in _CTRL_INLINE or ch in _CTRL_EXTENDED:
            i += 8
        elif ch in _CTRL_CHAR1:
            i += 1
        else:
            i += 1
    return ''.join(out)
 
 
def _iter_records(buf):
    """해제된 섹션 버퍼에서 (tag_id, level, body) 레코드를 순회."""
    pos, ln = 0, len(buf)
    while pos + 4 <= ln:
        header = struct.unpack_from('<I', buf, pos)[0]
        pos += 4
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        if size == 0xFFF:
            if pos + 4 > ln:
                break
            size = struct.unpack_from('<I', buf, pos)[0]
            pos += 4
        body = buf[pos:pos + size]
        pos += size
        yield tag_id, level, body
 
 
def extract_hwp(path):
    """바이너리 HWP(.hwp)에서 본문 텍스트를 추출."""
    with open(path, 'rb') as f:
        data = f.read()
    cfb = _CFB(data)
 
    fh = cfb.find('FileHeader')
    if fh is None:
        raise ValueError("FileHeader 스트림이 없습니다 — HWP 5.0 형식이 아닐 수 있습니다.")
    head = cfb.read_stream(fh)
    if not head[:32].startswith(b'HWP Document File'):
        raise ValueError("HWP 5.0 서명을 찾을 수 없습니다.")
    flags = struct.unpack_from('<I', head, 36)[0] if len(head) >= 40 else 0
    compressed = bool(flags & 0x01)
    encrypted = bool(flags & 0x02)
    if encrypted:
        raise ValueError("암호화된 HWP 문서입니다 — 복호화 후 변환본을 사용하세요.")
 
    sections = cfb.find_all(r'Section\d+$')
    sections.sort(key=lambda e: int(re.search(r'(\d+)$', e['name']).group(1)))
    if not sections:
        # 폴백: PrvText(미리보기 평문, UTF-16LE)
        prv = cfb.find('PrvText')
        if prv:
            sys.stderr.write("[hwp_extract] 본문 없음 — PrvText 미리보기만 추출합니다. 전체 분석 불가.\n")
            return cfb.read_stream(prv).decode('utf-16-le', 'ignore').strip()
        raise ValueError("BodyText 섹션을 찾을 수 없습니다.")
 
    paras = []
    for sec in sections:
        raw = cfb.read_stream(sec)
        if compressed:
            try:
                raw = zlib.decompress(raw, -15)
            except zlib.error:
                try:
                    raw = zlib.decompress(raw)
                except zlib.error as e:
                    raise ValueError(f"HWP 섹션 {sec['name']} 압축 해제 실패 — 변환본 필요") from e
        for tag_id, _level, body in _iter_records(raw):
            if tag_id == _HWPTAG_PARA_TEXT:
                txt = _parse_para_text_record(body)
                for line in txt.split('\n'):
                    line = line.strip()
                    if line:
                        paras.append(line)
    if not paras:
        prv = cfb.find('PrvText')
        if prv:
            sys.stderr.write("[hwp_extract] 본문 텍스트 없음 — PrvText 미리보기만 추출합니다. 전체 분석 불가.\n")
            return cfb.read_stream(prv).decode('utf-16-le', 'ignore').strip()
    return '\n'.join(paras)
 
 
# ────────────────────────────────────────────────────────────────────────
# 통합 진입점
# ────────────────────────────────────────────────────────────────────────
def extract(path, fmt='md'):
    """확장자/매직 바이트로 형식을 판별해 HWPX 또는 HWP 텍스트를 추출."""
    with open(path, 'rb') as f:
        magic = f.read(8)
    if magic[:2] == b'PK':
        return extract_hwpx(path, fmt=fmt)
    if magic == _OLE_SIG:
        return extract_hwp(path)
    # 확장자 보조 판별
    low = path.lower()
    if low.endswith('.hwpx'):
        return extract_hwpx(path, fmt=fmt)
    if low.endswith('.hwp'):
        return extract_hwp(path)
    raise ValueError("HWPX(ZIP) 또는 바이너리 HWP(OLE/CFB)가 아닙니다 — "
                     "변환본(DOCX/PDF/TXT/MD) 또는 원문 텍스트를 사용하세요.")
 
 
def main(argv=None):
    ap = argparse.ArgumentParser(description="한글 문서(HWPX/HWP) 본문 추출기 (stdlib, 무의존성)")
    ap.add_argument("input", help="입력 .hwpx / .hwp 경로")
    ap.add_argument("-o", "--output", help="출력 파일 경로(미지정 시 stdout)")
    ap.add_argument("--format", dest="fmt", choices=["md", "txt"], default="md",
                    help="HWPX 표 렌더링 형식 (기본: md). 바이너리 HWP는 평문 본문.")
    args = ap.parse_args(argv)
    try:
        text = extract(args.input, fmt=args.fmt)
    except (ValueError, zipfile.BadZipFile, OSError, struct.error) as e:
        sys.stderr.write(f"[hwp_extract] {e}\n")
        return 2
    if not text.strip():
        sys.stderr.write("[hwp_extract] 추출된 본문이 없습니다 — OCR/변환본 필요.\n")
        return 2
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        sys.stderr.write(f"[hwp_extract] {len(text)} chars -> {args.output}\n")
    else:
        sys.stdout.write(text + "\n")
    return 0
 
 
if __name__ == "__main__":
    raise SystemExit(main())

 