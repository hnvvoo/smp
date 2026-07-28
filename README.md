# KPX 육지 SMP 자동 수집 (GitHub Actions)

내 컴퓨터를 켜둘 필요 없이, GitHub의 무료 서버에서 정해진 시각에 자동으로
KPX 육지 SMP 엑셀을 받아오고, 값이 바뀌면 텔레그램으로 알림을 보냅니다.

## 폴더 구성
```
smp-github/
├─ smp_fetch.py                 # 수집 + 요약 + 텔레그램 알림
├─ requirements.txt
├─ data/                        # 받은 엑셀과 상태파일이 자동 저장됨
└─ .github/workflows/smp.yml    # 자동 실행 스케줄
```

## 설치 순서

### 1. GitHub 저장소 만들기
1. github.com 로그인 → 우측 상단 `+` → **New repository**
2. 이름 예: `kpx-smp` (Public 이면 Actions 완전 무료)
3. 이 폴더의 파일들을 그대로 올립니다.
   - 웹에서 하려면: 저장소 페이지 → **Add file → Upload files** 로 드래그
   - `.github/workflows/smp.yml` 경로가 유지되도록 폴더째 올리세요.

### 2. 텔레그램 봇 준비
1. 텔레그램에서 **@BotFather** 검색 → 대화 시작
2. `/newbot` 입력 → 봇 이름/아이디 정하면 **토큰**을 줍니다.
   (형식: `123456789:AAE...` — 이게 `TELEGRAM_BOT_TOKEN`)
3. 방금 만든 내 봇을 검색해서 **먼저 아무 메시지나** 한 번 보냅니다.
4. **chat_id 확인**: 브라우저에서 아래 주소 열기
   `https://api.telegram.org/bot<봇토큰>/getUpdates`
   응답에서 `"chat":{"id":숫자` 의 숫자가 `TELEGRAM_CHAT_ID` 입니다.

### 3. GitHub Secrets 등록
저장소 → **Settings → Secrets and variables → Actions → New repository secret**
두 개를 등록합니다:
| 이름 | 값 |
|------|-----|
| `TELEGRAM_BOT_TOKEN` | BotFather가 준 토큰 |
| `TELEGRAM_CHAT_ID`   | 위에서 확인한 chat id |

> Secrets 에 넣으면 값이 코드/로그에 노출되지 않습니다.

### 4. 실행 확인
- 저장소 **Actions** 탭 → 워크플로 선택 → **Run workflow** 로 수동 실행
- 로그가 초록불이면 성공. `data/` 폴더에 엑셀이 생기고, 값이 새로우면 텔레그램 알림이 옵니다.
- 이후에는 `smp.yml` 의 cron 시각(기본: KST 오전 8시·오후 4시)에 자동 실행됩니다.

## 실행 주기
현재 설정은 **KST 16:00~19:50 사이 10분 간격**입니다 (SMP 갱신 시간대).
`.github/workflows/smp.yml` 의 cron 으로 조절하며 **UTC 기준**입니다 (KST = UTC+9).

- 현재값: `*/10 7-10 * * *`  → UTC 7~10시대 매 10분 = KST 16~19시대
- 다른 예) 매일 KST 오전 10시 한 번만 → `0 1 * * *`

그 시간대에 값이 한 번 갱신되면, 이후 실행들은 직전 요약과 비교해
**동일하므로 알림을 자동으로 생략**합니다. 즉 알림은 그날 딱 한 번(값이
처음 바뀐 순간) 옵니다.

## 참고
- GitHub Actions 의 schedule 은 서버 부하에 따라 몇 분~십수 분 지연될 수 있습니다(정상).
  실제 실행 간격이 설정값보다 벌어질 수 있으나, 갱신을 놓치지는 않습니다(다음 실행에서 감지).
- KPX 가 다운로드 URL 형식을 바꾸면 `smp_fetch.py` 의 URL 을 수정해야 합니다.
