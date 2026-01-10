# TAPI Character Prompts

## 🎯 3단계 프롬프트 구조 (Template System)

### 1단계: 캐릭터 정체성 (Identity) - 고정 블록 ⭐
**모든 프롬프트의 시작 부분에 반드시 포함해야 하는 핵심 정체성**

```
Anime-style illustration of a blonde girl with long flowing hair, bright blue eyes, large red over-ear headphones. She has a gentle smile and slight blush with clean skin. Clean anime art style with crisp line art, vivid colors, smooth digital shading, expressive eyes, sharp outline, high contrast.
```

**핵심 요소 설명:**
- **이름/호칭**: TAPI, an anime girl
- **외형 특징**: long flowing blonde hair, bright blue eyes, fair skin, cheerful expression
- **시그니처 아이템**: large red over-ear headphones (캐릭터의 트레이드마크)
- **그림체**: Clean anime art style with crisp line art, smooth digital shading, highly detailed

### 2단계: 상황별 맥락 (Context) - 변경 가능 블록 🎨
**장면, 복장, 동작, 배경 등을 자유롭게 조정하는 부분**

**구성 요소:**
- **복장/액세서리**: 구체적인 옷 스타일과 색상 명시
- **동작/포즈**: 캐릭터의 구체적인 행동과 표정
- **배경/환경**: 분위기, 색상, 주요 오브젝트
- **구도/앵글**: 프레이밍, 시점, 비율 설정

### 3단계: 일관성 제어 (Control) - 네거티브 블록 🚫
**품질과 스타일 일관성을 위한 제외 요소들**

```
-- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, no deformed, no bad anatomy, no child-like, no chibi, no overly elaborate costume, no high fantasy, no fantasy elements, no armor, no sad, no bored
```

**네거티브 카테고리:**
- **품질/오류**: no blurry, no sweat, no sketch, no semi-realistic style, no 3D, no text
- **신체 오류**: no deformed, no bad anatomy, no distorted body, no deformed arms
- **스타일 제외**: no child-like, no chibi, no overly elaborate costume, no high fantasy, no armor
- **감정 제어**: no sad, no bored (기본적으로 밝고 긍정적인 표정 유지)

---

## 📝 실전 프롬프트 템플릿 (3단계 구조 적용)

### Template 1: 🌃 Urban Night Portrait
**[1단계 고정] + [2단계 맥락] -- Negative [3단계 제어]**
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Upper body portrait, wearing a sleek white off-shoulder top, holding one side of her headphones with a confident smile. Centered composition with a simple neon-lit city background softly blurred. Vivid neon colors, eye-level angle, wide aspect ratio. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, no deformed, no bad anatomy, no child-like, no chibi, no overly elaborate costume, no high fantasy, no fantasy elements, no armor, no sad, no bored
```

### Template 2: 🎆 Summer Festival Celebration  
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Waist-up view, wearing a simple white sleeveless festival top, raising one hand joyfully as if dancing. Dynamic pose with natural proportions, bright smile with sparkling eyes. Summer night background with colorful fireworks, glowing festival lights, floating music notes. Vivid summer colors (blue, pink, yellow), character emphasized in center. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, no deformed, no bad anatomy, no child-like, no chibi, no overly elaborate costume, no high fantasy, no fantasy elements, no armor, no sad, no bored
```

### Template 3: 🎨 Clean Banner (Text Space)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Upper body shot, wearing a simple white sleeveless top, bright smile looking at viewer. Character positioned on left side, natural proportions. Clean pastel gradient background with abstract glowing shapes, empty space on right side for text placement. Soft pastel colors (pink, blue, white), minimal background design. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, deformed, bad anatomy, baby face, small proportions, overly elaborate costume, high fantasy, fantasy elements, armor, sad, bored, busy background, complex scene
```

### Template 4: 🏮 Korean Traditional Fusion
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Upper body portrait, wearing a modern hanbok-inspired outfit in pastel colors with subtle red accents, bright red traditional ribbon hair accessory instead of headphones. Warm smile with slight blush, positioned on left side. Bright full moon in night sky background with soft glowing traditional lanterns and autumn leaves, minimal clean design with "TAPI" text space on right. Korean traditional colors (red, white, soft gold). -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, deformed, bad anatomy, baby face, small proportions, overly elaborate costume, high fantasy, fantasy elements, armor, sad, bored, oversized traditional clothing, busy background
```

### Template 5: 🎃 Halloween Festival Banner
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Knees-up view, wearing a black and orange Halloween dress with cute frills, sitting casually with one hand raised in peace sign gesture. Playful bright smile, natural proportions. Vibrant Halloween background with bright orange gradient, decorative jack-o'-lanterns, floating bats and ghosts, musical notes. Halloween colors (orange, black, purple), character emphasized in center. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, deformed, bad anatomy, baby face, small proportions, overly elaborate costume, high fantasy, fantasy elements, armor, sad, bored, scary elements
```

### Template 6: 🎃 Halloween Pumpkin Carving (Activity Scene)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Waist-up view, wearing a simple black T-shirt with subtle orange Halloween graphic, focused intently on carving a pumpkin with a cute slightly messy smile. Leaning over pumpkin, holding small carving tool, active crafting pose. Warm cozy room background decorated for Halloween, crafting supplies and unfinished decorations around. Warm Halloween colors (orange, brown, soft black), cozy indoor lighting. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, deformed, bad anatomy, baby face, small proportions, overly elaborate costume, full witch costume, high fantasy, fantasy elements, armor, sad, bored, finished celebration, clean hands
```

### Template 7: 🎃 Halloween Decoration Setup (Dynamic Action)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Clean anime art style with crisp line art, smooth digital shading, highly detailed, cheerful expression. Full-body shot, wearing comfortable black and orange tracksuit, energetically hanging Halloween decorations on wall with joyful determined expression. Standing on tiptoes or small stool, reaching up, dynamic action pose. Brightly lit room or porch being decorated, boxes of decorations nearby, scattered autumn leaves. Vivid Halloween colors (orange, black, red), active daytime lighting. -- Negative: no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, no deformed, no bad anatomy, no child-like, no chibi, no overly elaborate costume, no full witch costume, no high fantasy, no fantasy elements, no armor, no sad, no bored, no finished celebration
```

### Template 8: 🎯 Logo Close-up (Dynamic Angle)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a gentle smile and slight blush with clean skin. Extreme close-up of face only, cropping at neck level, focusing primarily on facial features and headphones. Slight three-quarter angle view with a subtle head tilt, looking slightly off to the side with a confident and approachable expression. Clean anime art style with crisp line art, vivid colors, smooth digital shading, expressive eyes, sharp outline, high contrast. Plain pastel background (soft blue or pale lavender), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no direct stare, no stiff pose, no body, no shoulders, no torso
```

### Template 9: 🎯 Logo Close-up (Side Profile - Casual)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a gentle smile and slight blush with clean skin. Extreme close-up face shot, cropping at neck level, focusing on facial profile and headphones. Side profile view showing elegant facial features, hair flowing gracefully, headphones prominently visible from the side. Peaceful and contemplative expression, eyes looking into the distance. Wearing a simple white sleeveless top with visible collar area. Clean anime art style with ultra-thick line art, bold black outlines, vivid colors, smooth digital shading, expressive eyes, heavy outline weight, maximum contrast, strong line definition. Plain pastel background (soft pink or mint green), perfect for logo use. -- Negative: no blurry, no washed-out colors, no thin lines, no faint outlines, no soft edges, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward angle, no body, no shoulders, no torso
```

### Template 11: 🎯 Logo Close-up (Side Profile - White Top)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a gentle smile and slight blush with clean skin. Extreme close-up face shot, cropping at neck level, focusing on facial profile and headphones. Side profile view showing elegant facial features, hair flowing gracefully, headphones prominently visible from the side. Peaceful and contemplative expression, eyes looking into the distance. Wearing a simple white sleeveless top with clean collar area. Clean anime art style with crisp line art, vivid colors, smooth digital shading, expressive eyes, sharp outline, high contrast. Plain pastel background (soft lavender or peach), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward angle, no body, no shoulders, no torso
```

### Template 12: 🎯 Logo Close-up (Side Profile - Clean White)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a gentle smile and slight blush with clean skin. Extreme close-up face shot, cropping at neck level, focusing on facial profile and headphones. Side profile view showing elegant facial features, hair flowing gracefully, headphones prominently visible from the side. Peaceful and contemplative expression, eyes looking into the distance. Wearing a simple white sleeveless top with minimal collar detail. Clean anime art style with crisp line art, vivid colors, smooth digital shading, expressive eyes, sharp outline, high contrast. Plain pastel background (soft blue or cream), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward angle, no body, no shoulders, no torso
```

### Template 10: 🎯 Logo Close-up (Playful Wink)
```
TAPI, an anime girl with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a playful wink and cheerful smile with clean skin. Extreme close-up face shot, cropping at neck level, focusing on facial expression and headphones. Slightly tilted head with a cute wink, one eye closed in a friendly gesture, other eye sparkling with joy. Hair bouncing slightly as if in motion. Clean anime art style with crisp line art, vivid colors, smooth digital shading, expressive eyes, sharp outline, high contrast. Plain pastel background (soft yellow or lavender), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no forced expression, no body, no shoulders, no torso
```

### Template 13: 🔥 Extreme Close-up (Artistic Crop)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a gentle smile with clean appearance. Extreme artistic close-up showing partial face with good composition - one eye, eyebrow area, cheek, flowing hair section, and headphone detail prominently featured. Cropping shows approximately 35-40% of face area with artistic balance. Focus on detailed eye with pupil highlights, natural facial curves, blonde hair texture and flow, red headphone structure and padding. Dynamic yet gentle expression, eye looking slightly off-center with confident gaze. Clean anime art style with crisp line art, vivid colors, smooth digital shading, highly detailed facial features, sharp outline, high contrast. Plain pastel background (soft pink or mint), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no full face visible, no neck visible, no body parts, no revealing areas, no mature content, no multiple eyes, no eye-only composition, no awkward cropping
```

### Template 14: 🔥 Extreme Close-up (Balanced Partial Face)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a peaceful smile with clean appearance. Extreme close-up showing balanced portion of face - one detailed eye, eyebrow, part of nose, cheek area, flowing blonde hair, and prominent red headphone. Cropping shows approximately 40-50% of face area with good balance between facial features and headphone detail. Eye with detailed highlights, natural facial contours, hair strands framing the composition, headphone padding and structure clearly visible. Gentle confident expression through visible eye and slight smile hint. Clean anime art style with crisp line art, vivid colors, smooth digital shading, highly detailed facial features, sharp outline, high contrast. Plain pastel background (soft blue or cream), perfect for logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no full face visible, no neck visible, no body parts, no revealing areas, no mature content, no multiple eyes, no scary expression, no eye-only focus, no unbalanced cropping
```

### Template 15: 📸 Low Angle Look-up (Dynamic Perspective)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a bright cheerful smile with clean appearance. Low angle shot from below, character looking down at camera with confident and friendly expression. Upper body portrait showing face and headphones from below perspective, hair flowing naturally downward due to gravity. Slight head tilt with sparkling eyes looking directly at viewer, gentle smile with approachable demeanor. Wearing a simple white sleeveless top, headphones prominently displayed from low angle view. Dynamic perspective with natural foreshortening, emphasizing facial features and headphone design. Clean anime art style with crisp line art, vivid colors, smooth digital shading, highly detailed facial features, sharp outline, high contrast. Plain gradient background (soft sky blue to white), perfect for impactful logo use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward perspective, no distorted proportions, no intimidating expression, no body visible below shoulders, no revealing areas, no mature content
```

### Template 16: 🎭 High Angle Look-down (Cute Perspective)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a sweet gentle smile and bright expression. High angle shot from above, character looking up at camera with adorable and innocent expression. Upper body portrait showing face and headphones from above perspective, hair spreading naturally outward due to position. Upward gaze with bright sparkling eyes, soft smile with endearing charm, slight blush on cheeks. Wearing a simple white sleeveless top, headphones clearly visible from overhead view. Graceful perspective with natural proportions, emphasizing cute facial expression and headphone design. Clean anime art style with ultra-crisp line art, vibrant bold colors, precise digital rendering, maximum detail sharpness, razor-sharp outline, ultra-high contrast. Plain pastel background (soft pink to white gradient), perfect for charming logo use. -- Negative: no blurry, no washed-out colors, no soft focus, no faded colors, no low contrast, no smudged lines, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward perspective, no distorted proportions, no sad expression, no body visible below shoulders, no revealing areas, no mature content, no overly dramatic angle
```

### Template 17: 🎭 Gentle Look-up Face-Fill (Natural Close-up)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a sweet gentle smile with clean appearance. Slight upward angle close-up with face filling entire frame, character looking up at camera with natural adorable expression. Face takes up 90% of composition, showing detailed facial features from forehead to chin, hair flowing naturally around frame edges. Large sparkling blue eyes with gentle upward gaze, soft smile with slight blush, headphones naturally positioned around head. Hair falls naturally with slight outward flow due to gentle angle, creating balanced composition. Maximum facial detail with every feature clearly visible - eyes, eyebrows, nose, lips, cheeks all perfectly rendered. Natural perspective without extreme distortion, emphasizing cute facial expression and clear headphone design. Clean anime art style with crisp line art, vivid colors, smooth digital shading, ultra-detailed facial rendering, sharp outline, high contrast. Minimal pastel background visible around hair edges only. Perfect for avatar or profile picture use. -- Negative: no blurry, no washed-out colors, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no extreme perspective, no distorted proportions, no sad expression, no body visible, no neck visible, no revealing areas, no mature content, no background distractions, no overhead view
```

### Template 18: 🎭 High Angle Face-Only (Ultra Close-up)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Sweet gentle smile, clean dry skin. High angle shot from above, looking up at camera with adorable expression. Face-only cropping at chin level, hair spreading naturally outward for width balance. Large red headphones framing the head from overhead view. Clean anime art style with crisp line art, vivid colors, sharp outline, high contrast. Minimal pastel background around hair edges. -- Negative: no body visible, no neck visible, no shoulders visible, no sweat, no moisture, no blurry, no soft focus, no sketch, no 3D, no child-like, no chibi, no deformed, no bad anatomy, no narrow face, no small headphones, no sad expression, no mature content
```

### Template 19: 🎖️ Playful Salute Pose (School Uniform)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a playful wink and cheerful smile with bright expression. Upper body portrait showing waist-up view, character making a cute salute gesture with right hand raised to forehead while giving a playful wink. Wearing a crisp white school shirt with navy blue collar trim and a navy blue plaid pleated skirt. Confident and mischievous expression with one eye closed in a friendly wink, other eye sparkling with joy. Natural standing pose with slight body tilt, headphones clearly visible and properly positioned. Clean anime art style with ultra-crisp line art, vibrant bold colors, precise digital rendering, maximum detail sharpness, razor-sharp outline, ultra-high contrast. Soft warm pastel background (peachy pink to cream gradient), perfect for character illustration. -- Negative: no blurry, no washed-out colors, no soft focus, no faded colors, no low contrast, no smudged lines, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward perspective, no distorted proportions, no sad expression, no revealing areas, no mature content, no military uniform, no overly serious expression, no background distractions
```

### Template 20: 🌞 Summer Salute Pose (Casual Outfit)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. She has a playful wink and cheerful smile with bright expression. Upper body portrait showing waist-up view, character making a cute salute gesture with right hand raised to forehead while giving a playful wink. Wearing a simple white sleeveless tank top and light blue denim shorts with a casual summer vibe. Confident and mischievous expression with one eye closed in a friendly wink, other eye sparkling with joy. Natural standing pose with slight body tilt, headphones clearly visible and properly positioned. Fresh and energetic summer feeling with clean casual style. Clean anime art style with ultra-crisp line art, vibrant bold colors, precise digital rendering, maximum detail sharpness, razor-sharp outline, ultra-high contrast. Bright sunny background (sky blue to white gradient) with soft clouds and gentle sunlight. -- Negative: no blurry, no washed-out colors, no soft focus, no faded colors, no low contrast, no smudged lines, no sweat, no tears, no water effects, no sketch, no semi-realistic style, no 3D, no extra accessories, no child-like, no chibi, no deformed, no bad anatomy, no awkward perspective, no distorted proportions, no sad expression, no revealing areas, no mature content, no overly tight clothing, no background distractions
```

### Template 21: 💫 Gentle Hair Touch Face-Only (Close-up Portrait)
```
TAPI, an anime character with long flowing blonde hair, bright blue eyes, large red over-ear headphones. Sweet gentle smile with soft expression. Three-quarter angle face-only close-up, cropping at neck level, character delicately touching her hair with hand gesture visible near face. Peaceful contemplative expression with gentle eyes looking slightly to the side, soft smile with natural charm. Hair flowing beautifully around the touching hand, headphones clearly visible and naturally positioned. Clean anime art style with crisp line art, vivid colors, sharp outline, high contrast. Soft pastel background (cream to light pink gradient). -- Negative: no body visible, no shoulders visible, no chest visible, no arms visible, no sweat, no moisture, no blurry, no sketch, no 3D, no child-like, no chibi, no deformed, no bad anatomy, no stiff pose, no forced gesture, no sad expression, no mature content
```

---

## 🔧 커스터마이징 가이드

### 📋 3단계 템플릿 구조
```
[1단계: 고정 프롬프트 블록], [2단계: 상황별 맥락 및 디테일]. -- Negative [3단계: 네거티브 프롬프트 블록]
```

### 🎨 2단계 맥락 요소 변수표

#### **복장/액세서리 [Outfit]**
- **캐주얼**: simple white sleeveless top, casual t-shirt, comfortable hoodie
- **축제**: festival yukata, summer dress, party outfit  
- **할로윈**: black and orange Halloween dress, witch hat, pumpkin accessories
- **전통**: hanbok-inspired outfit, traditional ribbon hair accessory
- **활동복**: tracksuit, overalls, sporty outfit

#### **동작/포즈 [Pose and Expression]**
- **정적**: holding headphones with confident smile, looking at viewer, peaceful expression
- **동적**: raising hand joyfully, dancing pose, reaching up, crafting activity
- **감정**: bright smile, playful wink, focused expression, determined look
- **구체적 행동**: carving pumpkin, hanging decorations, listening to music

#### **구도/앵글 [Framing]**
- **클로즈업**: upper body portrait, close-up shot, face focus
- **미디엄**: waist-up view, three-quarter shot  
- **풀샷**: full-body shot, knees-up view, standing pose
- **배치**: centered composition, character on left side, dynamic angle

#### **배경/환경 [Background]**
- **도시**: neon-lit city (blurred), urban night scene, city skyline
- **자연**: summer festival with fireworks, autumn leaves, bright moon
- **실내**: cozy room, decorated space, crafting area
- **추상**: clean pastel gradient, abstract shapes, minimal background
- **테마**: Halloween night, traditional Korean setting, music venue

#### **색상 팔레트 [Color Palette]**
- **네온**: vivid neon colors (blue, pink, cyan)
- **여름**: vivid summer colors (yellow, orange, blue)  
- **할로윈**: Halloween colors (orange, black, purple)
- **전통**: Korean traditional colors (red, white, gold)
- **파스텔**: soft pastel colors (pink, blue, white)

### 🚫 3단계 네거티브 확장 옵션

#### **기본 네거티브 (항상 포함)**
```
no sweat, no blurry, no distorted body, no deformed arms, no sketch, no semi-realistic style, no 3D, no text, no deformed, no bad anatomy, no child-like, no chibi, no overly elaborate costume, no high fantasy, no fantasy elements, no armor, no sad, no bored
```

#### **추가 네거티브 (필요시 선택)**
- **배경 제어**: busy background, multiple characters, complex scene, detailed background
- **구도 제어**: full body (상체만 원할 때), sitting, standing (동적 포즈 원할 때)  
- **테마별**: scary elements (할로윈), oversized traditional clothing (한복), clean hands (활동 장면)
- **품질**: pixelated, low quality, jpeg artifacts, watermark

---

## ✨ 일관성 유지 체크리스트

### 🎯 필수 요소 (모든 프롬프트에 포함)
- ✅ **1단계 고정 블록**: TAPI 캐릭터 정체성 + 그림체 스타일
- ✅ **헤드폰**: large red over-ear headphones (시그니처 아이템)
- ✅ **외형**: long flowing blonde hair, bright blue eyes  
- ✅ **표정**: cheerful expression (기본 밝은 표정)
- ✅ **3단계 네거티브**: 기본 네거티브 블록 포함

### 📐 구도별 가이드라인
- **배너/로고용**: 캐릭터 왼쪽 배치, 오른쪽 텍스트 공간 확보
- **프로필용**: 상체 중심, centered composition, eye-level angle
- **액션 장면**: 동적 포즈, 자연스러운 비율, 배경과의 조화
- **테마 이벤트**: 테마 색상 우선, 캐릭터 특징 유지하면서 분위기 반영

### 🔄 품질 최적화 팁
1. **캐릭터 우선순위**: 1단계 블록을 가장 앞에 배치하여 모델이 캐릭터를 우선 인식
2. **구체적 디테일**: 모호한 표현보다 구체적인 색상, 포즈, 배경 묘사
3. **네거티브 활용**: 원하지 않는 요소를 명확히 제외하여 결과물 안정성 확보
4. **일관된 스타일**: "Clean anime art style with crisp line art" 고정 사용
5. **감정 통일**: 기본적으로 밝고 긍정적인 캐릭터성 유지
