# Changelog

---

v0.9.7: Playback Recovery & Reliability

- Playback Recovery: Auto-skip broken/unavailable tracks, prevent infinite retry loops, and restore loop mode after failures
- Auto-Heal: Health monitoring auto-restarts the audio server within ~30s if it becomes unresponsive
- Shutdown: Extended shutdown window to 30s so playback state and statistics are reliably saved before restart
- Fixed: Music control panel not being removed when stopping playback from the web dashboard
- Fixed: Missing Japanese translation for the auto-delete (`/setting autodel`) result message
- Summer theme: Updated status messages and bot description visuals

### *June 1, 2026* | v0.9.7: 재생 복구 & 안정성

|no|contents|
|:---:|:---|
|1| 재생 복구: 깨지거나 재생 불가한 곡 자동 스킵, 무한 재시도 루프 방지, 실패 후 반복 모드 복원|
|2| 자동 복구: 오디오 서버가 응답하지 않으면 약 30초 내 자동 재시작 (헬스 모니터링)|
|3| 종료: 종료 대기 시간을 30초로 연장해 재생 상태·통계를 안정적으로 저장|
|4| 수정: 웹 대시보드에서 재생 중지 시 음악 컨트롤 패널이 삭제되지 않던 문제|
|5| 수정: 자동 삭제(`/setting autodel`) 결과 메시지의 일본어 번역 누락|
|6| 여름 테마: 상태 메시지 및 봇 소개 이미지 업데이트|

---

v0.9.6: Voice Stability & Spring Theme

- Auto-Disconnect Reliability: Fixed race conditions and event ordering so the bot reliably leaves empty channels and never gets stuck (added periodic safety-net cleanup)
- Skip To Fix: Selecting a queued track now plays it directly, even in shuffle mode
- Playlist out of Beta: Removed the beta label — playlist is now a stable feature
- Spring theme: New banner artwork

### *April 14, 2026* | v0.9.6: 음성 안정성 & 봄 테마

|no|contents|
|:---:|:---|
|1| 자동 퇴장 안정성: 경쟁 조건 및 이벤트 순서 수정으로 빈 채널에서 봇이 확실히 퇴장하고 멈추지 않도록 개선 (주기적 안전망 정리 추가)|
|2| Skip To 수정: 셔플 모드에서도 큐의 특정 곡을 선택하면 해당 곡이 바로 재생됨|
|3| 플레이리스트 정식 출시: 베타 레이블 제거 — 플레이리스트가 정식 기능으로 안정화|
|4| 봄 테마: 새 배너 이미지 적용|

---

v0.9.5: Web Dashboard Recommendations & Queue Play

- Queue Track Play: Click any track in the queue to play it immediately
- Song Recommendations: Auto-generated recommendations based on current track (YouTube Mix)
- Horizontal card UI with drag-scroll, auto-refresh on track change, and auto-refill
- Skip To: Jump to any queued track without removing other tracks
- Uptime History: 90-day service uptime bar chart on the status page
- API (vote-worker) status monitoring added

### *March 20, 2026* | v0.9.5: 웹 대시보드 추천 & 큐 재생

|no|contents|
|:---:|:---|
|1| 큐 트랙 재생: 큐에서 곡을 클릭하면 즉시 해당 곡으로 건너뛰기|
|2| 곡 추천: 현재 재생 곡 기반 YouTube Mix 자동 추천|
|3| 가로 스크롤 카드 UI, 곡 변경 시 자동 갱신, 추천곡 재생 시 자동 리필|
|4| Skip To: 다른 곡을 삭제하지 않고 큐의 특정 곡으로 이동|
|5| 업타임 히스토리: 상태 페이지에 90일간 서비스별 가동률 바 차트 추가|
|6| API(vote-worker) 상태 모니터링 추가|

---

v0.9.4: Playlist Sharing

- Playlist Share Code: Each playlist now gets a unique share code (e.g. `tapi-4l1Ch`)
- `/play tapi-xxxxx`: Play anyone's shared playlist by entering their share code
- `/save` now displays the share code in the success message
- Web Share Button: Added Share button to the web playlist page — copies share code to clipboard
- Buy Me a Coffee button added to the playlist page

### *March 17, 2026* | v0.9.4: 플레이리스트 공유

|no|contents|
|:---:|:---|
|1| 플레이리스트 공유 코드: 각 플레이리스트에 고유 공유 코드 부여 (예: `tapi-4l1Ch`)|
|2| `/play tapi-xxxxx`: 공유 코드로 다른 사람의 플레이리스트 재생 가능|
|3| `/save` 저장 완료 시 공유 코드 표시|
|4| 웹 Share 버튼: 웹 플레이리스트 페이지에 공유 버튼 추가 — 클릭 시 코드 클립보드 복사|
|5| 플레이리스트 페이지에 Buy Me a Coffee 버튼 추가|

---

v0.9.3: Bug Fixes & Discord Voice Encryption Update

- Fixed an issue where the /setting command could not be used in the designated bot channel
- Fixed music playback failure caused by Discord's updated voice encryption policy
- Fixed YouTube source errors
- Applied self_deaf when connecting to voice channels

### *March 3, 2026* | v0.9.3: 버그 수정 & Discord 음성 암호화 대응

|no|contents|
|:---:|:---|
|1| /setting 명령어가 지정된 봇 채널에서 사용 불가능하던 문제 수정|
|2| Discord 음성 암호화 정책 변경으로 인한 음악 재생 불가 문제 수정|
|3| YouTube 소스 오류 수정|
|4| 음성 채널 연결 시 self_deaf 적용|

---

v0.9.2: 🌸 Cherry Blossom Edition & Bot Settings

- 🌸 Cherry Blossom Edition: Updated bot description images and HTML with cherry blossom theme
- Bot Settings: Added `/settings` command — admins can configure bot channel restriction and other settings

### *February 27, 2026* | v0.9.2: 🌸 벚꽃 에디션 & 봇 설정

|no|contents|
|:---:|:---|
|1| 🌸 벚꽃 에디션: 봇 소개 이미지 및 설명 벚꽃 테마로 업데이트|
|2| 봇 설정 커맨드: `/settings` 커맨드 추가 — 봇 전용 채널 지정 등 설정 가능|

---

v0.9.1: Web Playlist & Queue Limits

- Web Playlist Management: View, add, delete, and reorder personal playlists on the web
- Playlist Button: Added `Playlist (beta)` button to Now Playing message
- `/load` Behavior Change: Clears existing queue and stops current track before loading playlist
- Queue Limits: Player queue max 50 tracks, playlist max 20 tracks (beta)

### *February 20, 2026* | v0.9.1: 웹 플레이리스트 & 큐 제한

|no|contents|
|:---:|:---|
|1| 웹 플레이리스트 관리: 웹에서 개인 플레이리스트 조회/추가/삭제/순서 변경|
|2| Playlist 버튼: Now Playing 메시지에 `Playlist (beta)` 버튼 추가|
|3| `/load` 동작 변경: 기존 큐를 비우고 현재 곡을 정지한 후 플레이리스트를 새로 로드|
|4| 큐 제한: 플레이어 큐 최대 50곡, 플레이리스트 최대 20곡 (베타)|

---

v0.9: Web Dashboard & UI Renewal

- Web Dashboard: Deployed beta version (Discord OAuth2 login, real-time player controls)
- UI/UX Renewal: Language pack overhaul (minimal tone), help/welcome messages cleaned up, etc.
- Unified control button order: Discord, Web same layout (Shuffle / Stop / Play / Skip / Repeat)

### *February 17, 2026* | v0.9: 웹 대시보드 & UI 리뉴얼

|no|contents|
|:---:|:---|
|1| 웹 대시보드: beta 버전 배포 (Discord OAuth2 로그인, 실시간 플레이어 컨트롤)|
|2| UI/UX 리뉴얼: 언어팩 전면 개편, 도움말/환영 메시지 정리 등|
|3| 컨트롤 버튼 순서 통일: Discord, Web 동일 배치 (Shuffle / Stop / Play / Skip / Repeat)|

---

v0.8.9: New Year Update

- New Year Theme: Updated bot status, banner, and logo with New Year theme
- Infrastructure: Applied Cloudflare CDN for vote webhook verification

### *January 1, 2026* | v0.8.9: New Year Update

|no|contents|
|:---:|:---|
|1| 새해 테마: 봇 상태, 배너, 로고 새해 테마 적용|
|2| 인프라: Cloudflare CDN 적용 (vote webhook 검증)|

---

v0.8.3: 🎃 Halloween Update & Stability Improvements

- UI Enhancement: Player updated with Halloween theme
- Stability Improvements: Fixed Discord interaction errors and added user-friendly error messages

### *October 31, 2025* | v0.8.3: 🎃 Halloween Update & Stability Improvements

|no|contents|
|:---:|:---|
|1| UI 개선: 플레이어 할로윈 테마 적용|
|2| 안정성 개선: Discord interaction 오류 수정, 사용자 친화적 에러 메시지 추가|

---

v0.8: Multi-language Support & Database Migration

- Japanese Language Pack: Added Japanese language support (`/language ja`)
- Database Migration: Upgraded to cloud database for 300+ servers
- Enhanced Performance: Optimized database connections and real-time statistics

### 한국어

|no|contents|
|:---:|:---|
|1| 일본어 언어팩: 일본어 지원 추가 (`/language ja`)|
|2| 데이터베이스 마이그레이션: 300+ 서버 대응 클라우드 DB 전환|
|3| 성능 최적화: DB 연결 및 실시간 통계 최적화|

---

v0.7.5: Music Recommendations Based on Current Track

- Current Track Recommendations: Added music suggestion feature based on the currently playing song
- Discover new music that matches your current listening mood

### 한국어

|no|contents|
|:---:|:---|
|1| 현재 트랙 기반 추천: 재생 중인 곡 기반 음악 추천 기능 추가|
|2| 현재 감상 분위기에 맞는 새로운 음악 발견|
