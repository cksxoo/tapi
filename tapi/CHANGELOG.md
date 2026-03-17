# Changelog

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
