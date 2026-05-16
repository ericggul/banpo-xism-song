# Workflow — "이미지 저장됨 → 비디오"

곡 한 곡당 끝까지 가는 가장 짧은 길.

## 0. 준비물 (이미 됨)

- `audio/<slug>.mp3` — 19개 mp3 + 3개 보너스 트랙 mp3
- `lyrics/lyrics.txt` — 한국어 가사 (24줄, 6섹션)
- `tracks/TRACKS.js` + `tracks/tracks.json` — 21곡 메타데이터 (장르/길이/언어)
- 파이프라인: `whisper → align(v2) → make_ass → render`

## 1. 곡 한 곡 만들기 (3단계)

**① 이미지를 저장한다.**

너가 어떤 도구로 만들든 (ChatGPT / Midjourney / Imagen / Sora / Adobe) 결과 PNG를 다음 위치 중 하나에 저장한다:

```
image/<N>.png                 ← 추천. 예: image/2.png
image/<slug>.png              ← 또는: image/반포자이즘-2.png
image/バンポザイの夢.png       ← 보너스 트랙은 슬러그 그대로
```

`render.sh`는 이 순서로 자동 찾는다:
1. `IMAGE=...` 환경변수
2. `image/<slug>.png`
3. `image/<N>.png` (슬러그가 `반포자이즘-N` 형태일 때)
4. `image/1.png` (fallback)

**② 한 줄로 비디오 생성.**

```bash
tools/build.sh 반포자이즘-2
```

이 한 줄이 다 한다:
- 캐시된 whisper transcript 사용 (없으면 mlx-whisper로 새로 만듦, ~40초)
- v2 정렬 (단조 세그먼트 워크 + 국지적 NW)
- ASS 자막 생성 (B급 스타일)
- ffmpeg burn-in 렌더 → `output/반포자이즘-2.mp4`

이미지가 위 위치 중 하나에 있으면 자동으로 그걸 씀.

**③ 결과 확인.**

```bash
open output/반포자이즘-2.mp4
```

타이밍 잘못됐으면 → 강제 재정렬:
```bash
FORCE_ALIGN=1 tools/build.sh 반포자이즘-2
```

whisper도 다시 돌리고 싶으면:
```bash
FORCE_WHISPER=1 tools/build.sh 반포자이즘-2
```

## 2. 19곡 + 3보너스 일괄 처리

이미지가 `image/1.png` ~ `image/21.png` (또는 `image/<slug>.png`) 다 있다고 가정:

```bash
# 한국어 18곡
for n in {1..18}; do
  tools/build.sh "반포자이즘-${n}"
done

# 보너스 3곡 (외국어)
tools/build.sh "バンポザイの夢"
tools/build.sh "Le rêve de BanpoXi"
tools/build.sh "BanpoXis Traum"
```

곡당 약 2분 (whisper 40s + 정렬 5s + 렌더 60s). 21곡 ≈ 40분.

> 주의: 외국어 보너스 트랙은 가사 파일이 다르다. 현재 `lyrics/lyrics.txt`는 한국어 전용. JA/FR/DE 트랙 돌리려면 먼저 해당 언어 가사 파일을 만들어서 `LYRICS=lyrics/lyrics-ja.txt tools/build.sh ...` 식으로 넘겨야 한다. (메타데이터는 `tracks/TRACKS.js`에 있음.)

## 3. 환경변수 cheat sheet

| 변수 | 효과 |
|---|---|
| `IMAGE=image/foo.png` | 이미지 자동 탐색 무시하고 강제 |
| `V=1` | v1 정렬(LCS)로 회귀. 기본은 v2 |
| `LYRICS=lyrics/lyrics-ja.txt` | 가사 파일 교체 (보너스 트랙용) |
| `NO_RENDER=1` | `.ass`만 만들고 mp4 렌더 건너뜀 |
| `FORCE_ALIGN=1` | 캐시된 `timings/<slug>.json` 무시하고 재정렬 |
| `FORCE_WHISPER=1` | 캐시된 whisper transcript 무시하고 재인식 |

## 4. 파일 구조 한눈에

```
banpo-xism-song/
├── audio/                  21개 mp3
├── image/                  곡당 이미지 (1.png, 2.png, ...)
│   └── prompts/            (선택) 이미지 생성용 프롬프트
├── lyrics/lyrics.txt       한국어 가사
├── tracks/
│   ├── TRACKS.js           21곡 메타 (canonical, JS)
│   └── tracks.json         같은 메타 (derived, JSON — shell용)
├── style/b_kyu.ass.tpl     B급 자막 스타일
├── timings/
│   ├── <slug>.whisper.json   whisper 결과 캐시
│   ├── <slug>.json           정렬된 줄별 타이밍
│   └── <slug>.ass            burn-in용 자막
├── tools/
│   ├── build.sh            ★ 메인 진입점
│   ├── transcribe.py       mlx-whisper 호출
│   ├── align_lyrics_v2.py  ★ 정렬 (기본)
│   ├── align_lyrics.py     v1 (legacy 호환)
│   ├── make_ass.py         가사+타이밍 → .ass
│   ├── render.sh           이미지+오디오+.ass → mp4
│   └── tap_timing.html     수동 타이밍 보정 (필요시)
├── output/                 완성된 mp4
├── legacy/                 v1 시절 출력 보존
└── WORKFLOW.md             이 파일
```
