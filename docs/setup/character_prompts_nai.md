# TAPI Character Prompts - NovelAI

## ⚙️ NAI 권장 기본 설정

| 설정 | 권장값 |
|------|--------|
| Steps | 28 |
| Prompt Guidance (CFG) | 6 |
| Sampler | k_euler_ancestral |
| Noise Schedule | karras |
| CFG Rescale | 0.6 |
| Resolution | 832x1216 (세로) / 1216x832 (가로) |

---

## 📋 태그 강조 시스템

| 문법 | 효과 | 배율 |
|------|------|------|
| `{태그}` | 강조 | 1.05배 |
| `{{태그}}` | 강한 강조 | 1.10배 |
| `{{{태그}}}` | 매우 강한 강조 | 1.15배 |
| `[태그]` | 약화 | 0.95배 |
| `[[태그]]` | 강한 약화 | 0.90배 |

---

## 🎨 아티스트 스타일 프리셋

### 해골 느낌 그림체 (샤프하고 세련된 스타일)
```
[[artist:horikoshikouhei]], {p_(tidoriashi)}, [artist:secretbusiness], [[artist:canape_(canape0130)]], artist:mi2mi2_minmi, {artist:ratatatat74}, year 2024,
```

---

## 🔒 고정 품질 태그 (모든 프롬프트 맨 앞에 포함)
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}
```

## 🔒 고정 캐릭터 태그 (품질 태그 뒤에 포함)
```
1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, smile, blush, fair skin
```

## 🚫 기본 네거티브 프롬프트
```
worst quality, bad quality, displeasing, very displeasing, lowres, bad anatomy, bad perspective, bad proportions, bad aspect ratio, bad face, long face, bad teeth, bad neck, long neck, bad arm, bad hands, bad ass, bad leg, bad feet, bad reflection, bad shadow, bad link, bad source, wrong hand, wrong feet, missing limb, missing eye, missing tooth, missing ear, missing finger, extra faces, extra eyes, extra eyebrows, extra mouth, extra tongue, extra teeth, extra ears, extra breasts, extra arms, extra hands, extra legs, extra digits, fewer digits, cropped head, cropped torso, cropped shoulders, cropped arms, cropped legs, mutation, deformed, disfigured, unfinished, chromatic aberration, text, error, jpeg artifacts, watermark, scan, scan artifacts, {{{blurry}}}, {{blurry background}}, blurry foreground, {{{{{{monochrome}}}}}}, {{{{{{greyscale}}}}}}
```

---

## 📝 템플릿

### Template 1: 🌃 Urban Night Portrait
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, smile, blush, fair skin, upper body, white off-shoulder top, confident smile, neon lights, city background, night, vivid colors, eye level
```

---

### Template 2: 🎆 Summer Festival
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {cheerful smile}, blush, fair skin, upper body, white sleeveless top, arm up, dancing, dynamic pose, fireworks, summer night, festival lights, music notes, vivid colors
```

---

### Template 3: 🎨 Clean Banner
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, smile, blush, fair skin, upper body, white sleeveless top, looking at viewer, character on left, empty space on right, gradient background, simple background, soft lighting
```

---

### Template 4: 🏮 Korean Traditional Fusion
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {red hair ribbon}, smile, blush, fair skin, upper body, hanbok, modern hanbok, pastel colors, red accents, character on left, full moon, night sky, lanterns, autumn leaves, traditional korean, warm colors
```
**추가 Negative:** `oversized clothing, busy background`

---

### Template 5: 🎃 Halloween Festival
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {cheerful smile}, blush, fair skin, knees up, black dress, orange dress, halloween costume, frills, peace sign, jack-o'-lantern, bats, ghosts, music notes, orange background, halloween, purple accents
```
**추가 Negative:** `scary, horror, gore`

---

### Template 6: 🎃 Pumpkin Carving
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, focused expression, slight smile, blush, fair skin, upper body, black t-shirt, orange graphic, carving pumpkin, holding tool, crafting, cozy room, halloween decorations, warm lighting, indoor
```
**추가 Negative:** `witch costume, clean hands`

---

### Template 7: 🎃 Decoration Setup
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {determined expression}, smile, blush, fair skin, full body, tracksuit, black and orange outfit, hanging decorations, reaching up, dynamic pose, standing on tiptoes, halloween decorations, autumn leaves, daytime
```
**추가 Negative:** `witch costume`

---

### Template 8: 🎯 Logo - Dynamic Angle
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, {bright eyes}, gentle smile, slight blush, fair skin, {close-up}, face focus, three-quarter view, head tilt, confident expression, looking away, simple background, sharp lines, high contrast
```
**추가 Negative:** `body, shoulders, torso, stiff pose`

---

### Template 9: 🎯 Logo - Side Profile
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, gentle smile, slight blush, fair skin, {close-up}, face focus, {profile}, from side, looking away, peaceful expression, white top, simple background, sharp lines, high contrast
```
**추가 Negative:** `body, shoulders, torso, awkward angle`

---

### Template 10: 🎯 Logo - Playful Wink
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {wink}, one eye closed, cheerful smile, blush, fair skin, {close-up}, face focus, hair movement, simple background, sharp lines, high contrast
```
**추가 Negative:** `body, shoulders, torso, forced expression`

---

### Template 11: 🔥 Extreme Close-up
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, blue eyes, {detailed eyes}, eye focus, gentle smile, fair skin, {extreme close-up}, partial face, artistic crop, one eye visible, hair strands, confident gaze, simple background, sharp lines, high contrast
```
**추가 Negative:** `full face, neck visible, body visible, multiple eyes`

---

### Template 12: 📸 Low Angle
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {cheerful smile}, blush, fair skin, upper body, white sleeveless top, {from below}, looking down, confident expression, friendly expression, dynamic perspective, sky background, gradient background
```
**추가 Negative:** `distorted proportions, intimidating expression`

---

### Template 13: 🎭 High Angle
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, hair spread out, blue eyes, {bright eyes}, {sweet smile}, blush, fair skin, upper body, white sleeveless top, {from above}, looking up, adorable expression, upward gaze, cute, gradient background
```
**추가 Negative:** `distorted proportions, sad expression`

---

### Template 14: 🎭 Face Fill Portrait
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, {large eyes}, {detailed eyes}, {gentle smile}, blush, fair skin, {portrait}, face focus, face filling frame, looking up slightly, sparkling eyes, soft expression, minimal background
```
**추가 Negative:** `body visible, neck visible, extreme perspective, sad expression`

---

### Template 15: 🎖️ Salute Pose - School Uniform
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {wink}, one eye closed, cheerful smile, blush, fair skin, upper body, {school uniform}, white shirt, navy collar, navy plaid skirt, {salute}, hand raised to forehead, playful expression, slight body tilt, warm colors
```
**추가 Negative:** `military uniform, serious expression`

---

### Template 16: 🌞 Salute Pose - Summer Casual
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {wink}, one eye closed, cheerful smile, blush, fair skin, upper body, {casual outfit}, white tank top, denim shorts, {salute}, hand raised to forehead, playful expression, summer, sky background, clouds, sunlight
```
**추가 Negative:** `serious expression, tight clothing`

---

### Template 17: 💫 Hair Touch Portrait
**Positive:**
```
{best quality, amazing quality, very aesthetic, highres, incredibly absurdres}, 1girl, solo, blonde hair, long hair, flowing hair, blue eyes, bright eyes, {gentle smile}, soft expression, blush, fair skin, {portrait}, face focus, three-quarter view, {hand in hair}, touching hair, peaceful expression, looking away, gradient background
```
**추가 Negative:** `body visible, stiff pose, sad expression`

---

## 🏷️ 유용한 태그 모음

### 구도 태그
```
close-up, portrait, upper body, full body, from above, from below, from side, dutch angle, dynamic angle
```

### 표정 태그
```
smile, gentle smile, cheerful, wink, one eye closed, blush, happy, confident
```

### 배경 태그
```
simple background, gradient background, white background, outdoors, indoors, night, day
```

### 의상 태그
```
school uniform, casual outfit, white top, sleeveless, off-shoulder, tank top, dress
```
