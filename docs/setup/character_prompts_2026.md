# TAPI Character Prompts 2026

## 목차

1. [기본 설정](#기본-설정)
2. [태그 강조 시스템](#태그-강조-시스템)
3. [고정 태그](#고정-태그)
4. [아티스트 스타일 프리셋](#아티스트-스타일-프리셋)
5. [템플릿](#템플릿)
   - [Logo (로고)](#logo-로고)
   - [Banner (배너)](#banner-배너)
6. [태그 레퍼런스](#태그-레퍼런스)

---

## 기본 설정

| 설정 | 권장값 |
|------|--------|
| Steps | 28 |
| Prompt Guidance (CFG) | 6 |
| Sampler | k_euler_ancestral |
| Noise Schedule | karras |
| CFG Rescale | 0.6 |
| Resolution | 832x1216 (세로) / 1216x832 (가로) |

---

## 태그 강조 시스템

### 중괄호/대괄호 강조

| 문법 | 효과 | 배율 |
|------|------|------|
| `{태그}` | 강조 | 1.05배 |
| `{{태그}}` | 강한 강조 | 1.10배 |
| `{{{태그}}}` | 매우 강한 강조 | 1.15배 |
| `[태그]` | 약화 | 0.95배 |
| `[[태그]]` | 강한 약화 | 0.90배 |

### 가중치 문법

| 문법 | 효과 | 예시 |
|------|------|------|
| `가중치::태그::` | 태그에 가중치 적용 | `0.8::laliberte::` (0.8 강도) |
| `-가중치::태그::` | 태그 억제 | `-0.8::feet::` (발 억제) |

---

## 고정 태그

모든 프롬프트는 아래 구조를 따릅니다:

```
[캐릭터 태그], [템플릿 고유 태그], [아티스트 태그], [품질 태그]
```

### 캐릭터 태그 (맨 앞)

```
1girl, solo, blonde hair, long hair, blue eyes, bright eyes, smile, blush, fair skin
```

### 품질 태그 (맨 뒤에 포함)

```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres},
very aesthetic, masterpiece, no text, rating:general
```

### 기본 네거티브 프롬프트

```
worst quality, bad quality, displeasing, very displeasing, lowres, bad anatomy, bad perspective,
bad proportions, bad aspect ratio, bad face, long face, bad teeth, bad neck, long neck, bad arm,
bad hands, bad ass, bad leg, bad feet, bad reflection, bad shadow, bad link, bad source, wrong hand,
wrong feet, missing limb, missing eye, missing tooth, missing ear, missing finger, extra faces,
extra eyes, extra eyebrows, extra mouth, extra tongue, extra teeth, extra ears, extra breasts,
extra arms, extra hands, extra legs, extra digits, fewer digits, cropped head, cropped torso,
cropped shoulders, cropped arms, cropped legs, mutation, deformed, disfigured, unfinished,
chromatic aberration, text, error, jpeg artifacts, watermark, scan, scan artifacts,
{{{blurry}}}, {{blurry background}}, blurry foreground,
{{{{{{monochrome}}}}}}, {{{{{{greyscale}}}}}}
```

---

## 아티스트 스타일 프리셋

### 샤프하고 세련된 스타일

```
[[artist:horikoshikouhei]], {p_(tidoriashi)}, [artist:secretbusiness],
[[artist:canape_(canape0130)]], artist:mi2mi2_minmi, {artist:ratatatat74}, year 2024,
```

---

## 템플릿

> 아래 템플릿의 `...` 부분은 `[캐릭터 태그]`를 의미합니다.
> 실제 사용: `[캐릭터], [템플릿 태그], [아티스트], [품질]` 순서로 조합하세요.

### Logo (로고)

#### Sunny Spring Close-up

```
..., centered composition, extreme close-up of face, face filling frame,
tight composition, face focused, no busy background,
wearing oversized tortoiseshell-framed sunglasses, woven straw hat on head,
simple uniform unblemished light blue background, warm spring daylight, soft lighting
```

---

### Banner (배너)

#### Mediterranean Coastline

```
..., banner composition, wide-angle landscape, upper body view,
character positioned on the left side of frame, open space on the right side,
expansive view of an unbroken mediterranean coastline,
long white sand beach stretching to horizon, turquoise ocean,
distant unified white resort architecture, minimum stylized palm trees,
uniform soft blue sky with subtle cloud gradients,
wearing oversized tortoiseshell-framed sunglasses, woven straw hat with a thin blue ribbon,
warm spring daylight, soft lighting, {depth of field}
```

#### Pastel Cardigan Look

```
..., aroused, lovestruck, licking lips, index finger together,
banner composition, wide-angle landscape, upper body view,
character positioned on the right side of frame, open space on the left side,
{gentle smile}, looking back over shoulder, three-quarter view,
pastel cardigan, open cardigan, simple white linen summer dress,
{{oversized tortoiseshell-framed sunglasses worn on face}}, {bare shoulders}, collarbone,
minimalist gold necklace,
simple uniform unblemished pastel pale yellow background, no background details, empty background,
warm spring daylight, soft lighting, {depth of field}
```

---

## 태그 레퍼런스

### 구도

| 태그 | 설명 |
|------|------|
| `close-up` | 얼굴 클로즈업 |
| `extreme close-up` | 극단적 클로즈업 (눈 등) |
| `portrait` | 인물 초상 |
| `upper body` | 상반신 |
| `full body` | 전신 |
| `from above` | 위에서 내려다보는 앵글 |
| `from below` | 아래에서 올려다보는 앵글 |
| `from side` | 측면 |
| `dutch angle` | 기울어진 앵글 |
| `dynamic angle` | 역동적 앵글 |
| `three-quarter view` | 3/4 뷰 |
| `face focus` | 얼굴 중심 |
| `eye level` | 눈높이 |
| `banner composition` | 와이드 배너 구도 |
| `wide-angle landscape` | 광각 풍경 |

### 표정

| 태그 | 설명 |
|------|------|
| `smile` | 미소 |
| `gentle smile` | 부드러운 미소 |
| `cheerful smile` | 밝은 미소 |
| `confident` | 자신감 있는 |
| `wink` | 윙크 |
| `one eye closed` | 한쪽 눈 감기 |
| `blush` | 볼 홍조 |
| `happy` | 행복한 |
| `focused expression` | 집중한 표정 |
| `peaceful expression` | 평화로운 표정 |

### 배경

| 태그 | 설명 |
|------|------|
| `simple background` | 심플 배경 |
| `gradient background` | 그라데이션 |
| `white background` | 흰 배경 |
| `outdoors` | 야외 |
| `indoors` | 실내 |
| `night` | 밤 |
| `day` / `daytime` | 낮 |
| `sky background` | 하늘 배경 |
| `city background` | 도시 배경 |
| `mediterranean coastline` | 지중해 해안 |
| `turquoise ocean` | 청록색 바다 |

### 의상 / 소품

| 태그 | 설명 |
|------|------|
| `tortoiseshell-framed sunglasses` | 거북 등껍질 무늬 선글라스 |
| `woven straw hat` | 밀짚모자 |
| `school uniform` | 교복 |
| `casual outfit` | 캐주얼 |
| `white top` | 흰 상의 |
| `sleeveless` | 민소매 |
| `off-shoulder` | 오프숄더 |
| `tank top` | 탱크탑 |
| `dress` | 원피스 |
