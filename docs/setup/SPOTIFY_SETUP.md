# 🎧 Spotify 설정 가이드 / Spotify Setup Guide

## 한국어 (Korean)

### 🔒 보안 주의사항

**⚠️ 매우 중요: Spotify Client Secret은 비밀번호와 같습니다!**
- 절대 GitHub, Discord, 공개 채널에 공유하지 마세요
- `.env` 파일은 이미 `.gitignore`에 포함되어 있습니다
- 실수로 노출된 경우 즉시 Spotify Dashboard에서 재발급 받으세요

### Spotify API 키 발급받기

1. **Spotify Developer Dashboard 접속**
   - https://developer.spotify.com/dashboard 로 이동
   - Spotify 계정으로 로그인

2. **애플리케이션 생성**
   - "Create app" 버튼 클릭
   - App name: 원하는 이름 입력 (예: "TAPI Bot")
   - App description: 간단한 설명 입력
   - Redirect URI: `http://localhost` (필수)
   - API 체크박스 선택: "Web API" 체크
   - "Save" 클릭

3. **Client ID와 Client Secret 확인**
   - 생성된 앱을 클릭
   - "Settings" 버튼 클릭
   - **Client ID**와 **Client Secret**을 복사

### .env 파일 설정 (필수!)

**`.env` 파일은 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다!**

1. `.env.example` 파일을 복사하여 `.env` 파일 생성:
```bash
cp .env.example .env
```

2. `.env` 파일을 열고 발급받은 키 입력:
```bash
# --- Spotify API Credentials ---
SPOTIFY_CLIENT_ID=여기에_발급받은_CLIENT_ID_입력
SPOTIFY_CLIENT_SECRET=여기에_발급받은_CLIENT_SECRET_입력
SPOTIFY_COUNTRY_CODE=KR
```

3. 파일 확인:
```yaml
plugins:
  lavasrc:
    sources:
      spotify: true  # Spotify 활성화
    spotify:
      clientId: "${SPOTIFY_CLIENT_ID:}"  # 환경변수에서 자동 로드
      clientSecret: "${SPOTIFY_CLIENT_SECRET:}"  # 환경변수에서 자동 로드
      countryCode: "${SPOTIFY_COUNTRY_CODE:KR}"
```

4. Docker 재시작:
```bash
docker-compose down
docker-compose up -d
```

### 사용 방법

1. **Spotify 전용 명령어**:
   - `/spplay [곡명]` - Spotify에서 검색
   - `/spplay [Spotify URL]` - Spotify 링크로 재생

2. **일반 명령어**:
   - `/play [Spotify URL]` - Spotify 링크도 자동 인식

3. **지원하는 Spotify 형식**:
   - 트랙 (Track)
   - 앨범 (Album)
   - 플레이리스트 (Playlist)
   - 아티스트 인기곡 (Artist Top Tracks)

---

## English

### 🔒 Security Warning

**⚠️ CRITICAL: Treat your Spotify Client Secret like a password!**
- NEVER share it on GitHub, Discord, or public channels
- `.env` file is already in `.gitignore`
- If accidentally exposed, regenerate immediately on Spotify Dashboard

### Getting Spotify API Keys

1. **Access Spotify Developer Dashboard**
   - Go to https://developer.spotify.com/dashboard
   - Log in with your Spotify account

2. **Create Application**
   - Click "Create app" button
   - App name: Enter desired name (e.g., "TAPI Bot")
   - App description: Enter brief description
   - Redirect URI: `http://localhost` (required)
   - Select API checkbox: Check "Web API"
   - Click "Save"

3. **Get Client ID and Client Secret**
   - Click on the created app
   - Click "Settings" button
   - Copy **Client ID** and **Client Secret**

### Environment Variable Setup (Recommended)

**This method keeps your keys safe from GitHub exposure!**

1. Copy `.env.example` to create `.env` file:
```bash
cp .env.example .env
```

2. Open `.env` file and enter your keys:
```bash
# --- Spotify API Credentials ---
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_COUNTRY_CODE=US
```

3. Verify `lavalink/application.yml`:
```yaml
plugins:
  lavasrc:
    sources:
      spotify: true  # Enable Spotify
    spotify:
      clientId: "${SPOTIFY_CLIENT_ID:}"  # Auto-loaded from env
      clientSecret: "${SPOTIFY_CLIENT_SECRET:}"  # Auto-loaded from env
      countryCode: "${SPOTIFY_COUNTRY_CODE:KR}"
```

4. Restart Docker:
```bash
docker-compose down
docker-compose up -d
```

### Usage

1. **Spotify-specific commands**:
   - `/spplay [song name]` - Search on Spotify
   - `/spplay [Spotify URL]` - Play from Spotify link

2. **General commands**:
   - `/play [Spotify URL]` - Automatically recognizes Spotify links

3. **Supported Spotify formats**:
   - Tracks
   - Albums
   - Playlists
   - Artist Top Tracks

---

## 日本語 (Japanese)

### 🔒 セキュリティ警告

**⚠️ 重要: Spotify Client Secretはパスワードと同じです！**
- 絶対にGitHub、Discord、公開チャンネルで共有しないでください
- `.env`ファイルは既に`.gitignore`に含まれています
- 誤って公開した場合は、すぐにSpotify Dashboardで再発行してください

### Spotify APIキーの取得

1. **Spotify Developer Dashboardにアクセス**
   - https://developer.spotify.com/dashboard へ移動
   - Spotifyアカウントでログイン

2. **アプリケーションの作成**
   - "Create app"ボタンをクリック
   - App name: 任意の名前を入力（例：「TAPI Bot」）
   - App description: 簡単な説明を入力
   - Redirect URI: `http://localhost` (必須)
   - APIチェックボックス: "Web API"をチェック
   - "Save"をクリック

3. **Client IDとClient Secretの確認**
   - 作成したアプリをクリック
   - "Settings"ボタンをクリック
   - **Client ID**と**Client Secret**をコピー

### 環境変数設定（推奨）

**この方法でGitHubへの公開を防げます！**

1. `.env.example`をコピーして`.env`ファイルを作成:
```bash
cp .env.example .env
```

2. `.env`ファイルを開いて取得したキーを入力:
```bash
# --- Spotify API Credentials ---
SPOTIFY_CLIENT_ID=ここにCLIENT_IDを入力
SPOTIFY_CLIENT_SECRET=ここにCLIENT_SECRETを入力
SPOTIFY_COUNTRY_CODE=JP
```

3. `lavalink/application.yml`を確認:
```yaml
plugins:
  lavasrc:
    sources:
      spotify: true  # Spotifyを有効化
    spotify:
      clientId: "${SPOTIFY_CLIENT_ID:}"  # 環境変数から自動読み込み
      clientSecret: "${SPOTIFY_CLIENT_SECRET:}"  # 環境変数から自動読み込み
      countryCode: "${SPOTIFY_COUNTRY_CODE:KR}"
```

4. Dockerを再起動:
```bash
docker-compose down
docker-compose up -d
```

### 使用方法

1. **Spotify専用コマンド**:
   - `/spplay [曲名]` - Spotifyで検索
   - `/spplay [Spotify URL]` - SpotifyリンクからRE生

2. **一般コマンド**:
   - `/play [Spotify URL]` - Spotifyリンクも自動認識

3. **対応Spotifyフォーマット**:
   - トラック (Track)
   - アルバム (Album)
   - プレイリスト (Playlist)
   - アーティスト人気曲 (Artist Top Tracks)

---

## 🔐 보안 체크리스트 / Security Checklist

- [ ] `.env` 파일 생성 및 키 입력 완료
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] `application.yml`에 실제 키가 하드코딩되어 있지 않은지 확인
- [ ] GitHub에 커밋하기 전에 `git status`로 `.env` 파일이 제외되었는지 확인
- [ ] 팀원과 공유할 때는 `.env.example` 파일만 공유

---

## 🎵 작동 원리 / How It Works

Spotify는 직접 오디오 스트리밍을 제공하지 않습니다. TAPI는 다음과 같이 작동합니다:

1. **Spotify API**에서 곡 메타데이터 가져오기 (제목, 아티스트, 앨범 아트, ISRC 코드)
2. **YouTube**에서 동일한 곡 검색 (ISRC 코드 또는 제목+아티스트)
3. **YouTube 오디오** 스트리밍 + **Spotify 메타데이터** 표시

이 방식을 "**Mirroring**"이라고 하며, LavaSrc 플러그인이 자동으로 처리합니다.

---

**Made with 💖 by TAPI Team**
