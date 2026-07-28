#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KPX 육지 SMP 수집 스크립트 (GitHub Actions 용)

동작:
  1) KPX 엑셀 다운로드 URL 을 호출해 파일을 data/ 폴더에 저장
  2) 최신 엑셀에서 표를 파싱해 요약 텍스트를 만듦
  3) 직전에 저장해 둔 요약과 다르면 -> 텔레그램으로 알림 발송
  4) 파일 변경 여부는 GitHub Actions 워크플로가 git diff 로 감지해서 커밋

환경변수(=GitHub Secrets)로 받는 값:
  TELEGRAM_BOT_TOKEN  : 봇 토큰
  TELEGRAM_CHAT_ID    : 알림 받을 chat id
  (둘 다 없으면 알림은 건너뛰고 파일 저장만 함)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "last_summary.txt"   # 직전 요약 저장(변경 비교용)

URLS = {
    "today": "https://www.kpx.or.kr/xlsxdownload.es?act=smpInLand&division=smpInLand&gubun=today",
    "year": "https://www.kpx.or.kr/xlsxdownload.es?act=smpInLand&division=smpInLand&gubun=year",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.kpx.or.kr/smpInland.es?mid=a10606080100",
}
TIMEOUT = 30

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def download(url: str) -> bytes:
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    if resp.content[:2] != b"PK":
        raise ValueError(
            f"엑셀이 아닌 응답 (앞부분: {resp.content[:40]!r}). "
            "URL 변경 또는 차단 가능성."
        )
    return resp.content


def summarize(xlsx_path: Path) -> str:
    """엑셀에서 최근 날짜의 SMP 요약(가중평균/최대/최소)을 문자열로 뽑음."""
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    # 표 전체를 2차원 리스트로 읽음
    rows = []
    for r in ws.iter_rows(values_only=True):
        rows.append(["" if v is None else str(v).strip() for v in r])

    if not rows:
        return "(빈 파일)"

    # 헤더(날짜) 행 찾기: '구분' 이 포함된 행
    header = None
    for row in rows:
        if any("구분" in c for c in row):
            header = row
            break
    if header is None:
        header = rows[0]

    # 가중평균/최대/최소 행 추출
    wanted = ("가중평균", "최대", "최소")
    picked = {}
    for row in rows:
        label = row[0] if row else ""
        for w in wanted:
            if label == w:
                picked[w] = row

    # 가장 오른쪽(=가장 최근) 날짜 열 인덱스 = 마지막 유효 컬럼
    last_col = len(header) - 1
    while last_col > 0 and header[last_col] == "":
        last_col -= 1

    latest_date = header[last_col] if last_col < len(header) else "?"

    lines = [f"📅 최근 거래일: {latest_date}"]
    for w in wanted:
        if w in picked and last_col < len(picked[w]):
            lines.append(f"  {w}: {picked[w][last_col]} 원/kWh")
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        log("텔레그램 토큰/chat_id 없음 → 알림 건너뜀")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": text},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        log("텔레그램 알림 발송 완료")
    except Exception as e:
        log(f"텔레그램 발송 실패: {e}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 다운로드 & 저장
    for key, url in URLS.items():
        try:
            content = download(url)
            (DATA_DIR / f"smp_{key}.xlsx").write_bytes(content)
            log(f"[{key}] 다운로드/저장 완료 ({len(content):,} bytes)")
        except Exception as e:
            log(f"[{key}] 다운로드 실패: {e}")

    # 2) 최신(today) 요약
    today_path = DATA_DIR / "smp_today.xlsx"
    if not today_path.exists():
        log("today 파일이 없어 요약/알림 생략")
        sys.exit(0)

    try:
        summary = summarize(today_path)
    except Exception as e:
        log(f"요약 실패: {e}")
        sys.exit(0)

    # 3) 직전 요약과 비교
    prev = ""
    if STATE_FILE.exists():
        prev = STATE_FILE.read_text(encoding="utf-8")

    if summary.strip() == prev.strip():
        log("변경 없음 → 알림 생략")
        return

    # 4) 변경됨 → 알림 + 상태 저장
    STATE_FILE.write_text(summary, encoding="utf-8")
    msg = "⚡ KPX 육지 SMP 업데이트\n\n" + summary + \
          "\n\n출처: https://www.kpx.or.kr/smpInland.es?mid=a10606080100"
    log("변경 감지:\n" + summary)
    send_telegram(msg)


if __name__ == "__main__":
    main()
