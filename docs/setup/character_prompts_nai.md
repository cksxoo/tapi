# TAPI Character Prompts - NovelAI

## 목차

1. [기본 설정](#기본-설정)
2. [태그 강조 시스템](#태그-강조-시스템)
3. [고정 태그](#고정-태그)
4. [아티스트 스타일 프리셋](#아티스트-스타일-프리셋)
5. [템플릿](#템플릿)
   - [Portrait (인물)](#portrait-인물)
   - [Event (이벤트)](#event-이벤트)
   - [Logo (로고)](#logo-로고)
   - [Banner (배너)](#banner-배너)
   - [Pose (포즈)](#pose-포즈)
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

### Portrait (인물)

#### Urban Night Portrait

```
..., upper body, white off-shoulder top, confident smile,
neon lights, city background, night, vivid colors, eye level
```

#### Hair Touch Portrait

```
..., {gentle smile}, soft expression, {portrait}, face focus, three-quarter view,
{hand in hair}, touching hair, peaceful expression, looking away, gradient background
```
- 추가 Negative: `body visible, stiff pose, sad expression`

#### Face Fill Portrait

```
..., {large eyes}, {detailed eyes}, {gentle smile}, {portrait}, face focus,
face filling frame, looking up slightly, sparkling eyes, soft expression, minimal background
```
- 추가 Negative: `body visible, neck visible, extreme perspective, sad expression`

#### Low Angle

```
..., {cheerful smile}, upper body, white sleeveless top,
{from below}, looking down, confident expression, friendly expression,
dynamic perspective, sky background, gradient background
```
- 추가 Negative: `distorted proportions, intimidating expression`

#### High Angle

```
..., hair spread out, {bright eyes}, {sweet smile}, upper body, white sleeveless top,
{from above}, looking up, adorable expression, upward gaze, cute, gradient background
```
- 추가 Negative: `distorted proportions, sad expression`

#### Extreme Close-up

```
..., {detailed eyes}, eye focus, gentle smile, {extreme close-up}, partial face,
artistic crop, one eye visible, hair strands, confident gaze,
simple background, sharp lines, high contrast
```
- 추가 Negative: `full face, neck visible, body visible, multiple eyes`

---

### Event (이벤트)

#### Summer Festival

```
..., {cheerful smile}, upper body, white sleeveless top, arm up, dancing,
dynamic pose, fireworks, summer night, festival lights, music notes, vivid colors
```

#### Korean Traditional Fusion

```
..., {red hair ribbon}, upper body, hanbok, modern hanbok, pastel colors,
red accents, character on left, full moon, night sky, lanterns, autumn leaves,
traditional korean, warm colors
```
- 추가 Negative: `oversized clothing, busy background`

#### Halloween - Festival

```
..., {cheerful smile}, knees up, black dress, orange dress,
halloween costume, frills, peace sign, jack-o'-lantern, bats, ghosts, music notes,
orange background, halloween, purple accents
```
- 추가 Negative: `scary, horror, gore`

#### Halloween - Pumpkin Carving

```
..., focused expression, slight smile, upper body, black t-shirt,
orange graphic, carving pumpkin, holding tool, crafting, cozy room,
halloween decorations, warm lighting, indoor
```
- 추가 Negative: `witch costume, clean hands`

#### Halloween - Decoration Setup

```
..., {determined expression}, full body, tracksuit, black and orange outfit,
hanging decorations, reaching up, dynamic pose, standing on tiptoes,
halloween decorations, autumn leaves, daytime
```
- 추가 Negative: `witch costume`

#### Spring - Sofa Reading

```
..., {gentle smile}, sitting, legs tucked, oversized cardigan, bare legs,
sofa, open book, {cherry blossoms outside window}, afternoon sunlight,
spring, warm colors, soft focus, {depth of field}
```
- 추가 Negative: `night, outdoor, winter, standing`

#### Spring - Window Backlight

```
..., {looking back}, hand on curtain, oversized shirt, bare legs, collarbone,
bedroom, window, {cherry blossoms outside}, morning sunlight, backlight,
spring, lens flare, soft shadow, {depth of field}
```
- 추가 Negative: `night, outdoor, winter, dark colors`

#### Spring - Balcony Breeze

```
..., {sweet smile}, leaning on railing, oversized shirt, wind lift, bare legs, collarbone,
balcony, {cherry blossoms}, petals falling, morning sunlight,
spring, backlight, hair blowing, {depth of field}
```
- 추가 Negative: `night, winter, indoor, dark colors`

---

### Logo (로고)

#### Dynamic Angle

```
..., {bright eyes}, gentle smile, slight blush, {close-up}, face focus,
three-quarter view, head tilt, confident expression, looking away,
simple background, sharp lines, high contrast
```
- 추가 Negative: `body, shoulders, torso, stiff pose`

#### Side Profile

```
..., gentle smile, slight blush, {close-up}, face focus,
{profile}, from side, looking away, peaceful expression, white top,
simple background, sharp lines, high contrast
```
- 추가 Negative: `body, shoulders, torso, awkward angle`

#### Playful Wink

```
..., {wink}, one eye closed, cheerful smile, {close-up}, face focus,
hair movement, simple background, sharp lines, high contrast
```
- 추가 Negative: `body, shoulders, torso, forced expression`

---

### Banner (배너)

#### Clean Banner

```
..., upper body, white sleeveless top, looking at viewer,
character on left, empty space on right, gradient background,
simple background, soft lighting
```

---

### Pose (포즈)

#### Salute - School Uniform

```
..., {wink}, one eye closed, cheerful smile, upper body,
{school uniform}, white shirt, navy collar, navy plaid skirt,
{salute}, hand raised to forehead, playful expression, slight body tilt, warm colors
```
- 추가 Negative: `military uniform, serious expression`

#### Salute - Summer Casual

```
..., {wink}, one eye closed, cheerful smile, upper body,
{casual outfit}, white tank top, denim shorts,
{salute}, hand raised to forehead, playful expression,
summer, sky background, clouds, sunlight
```
- 추가 Negative: `serious expression, tight clothing`

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

### 의상

| 태그 | 설명 |
|------|------|
| `school uniform` | 교복 |
| `casual outfit` | 캐주얼 |
| `white top` | 흰 상의 |
| `sleeveless` | 민소매 |
| `off-shoulder` | 오프숄더 |
| `tank top` | 탱크탑 |
| `dress` | 원피스 |
| `hanbok` | 한복 |
| `tracksuit` | 트레이닝복 |

### 포즈 / 동작

| 태그 | 설명 |
|------|------|
| `salute` | 경례 포즈 |
| `hand in hair` | 머리카락 만지기 |
| `peace sign` | 피스 |
| `arm up` | 팔 올리기 |
| `dancing` | 춤추기 |
| `looking at viewer` | 시선 정면 |
| `looking away` | 시선 회피 |
| `looking up` | 위를 바라보기 |
| `looking down` | 아래를 바라보기 |
| `head tilt` | 고개 기울이기 |
