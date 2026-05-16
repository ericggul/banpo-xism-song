[Script Info]
Title: 반포자이즘 B급 Lyric (9:16 vertical)
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

; Vertical (YouTube Shorts) variant of style/b_kyu.ass.tpl
; - Canvas 1080×1920 portrait
; - Lyric / LyricAlt subtitles use Alignment=5 (middle-center of the frame)
;   so they read clean over the cover art without colliding with the
;   bottom-right "반포자이즘" logotype
; - Section labels stay top-center (Alignment=8) as small ghost captions
; - Font sizes bumped vs the horizontal template (1080 wide → text needs
;   to be physically bigger to stay phone-readable at 100% Shorts crop)

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyric,    AppleSDGothicNeo-Bold, 96,  &H0000F0FF, &H000000FF, &H00000000, &H80000000, -1, 0, 0, 0, 100, 100, 2, 0, 1, 7, 4, 5, 60, 60, 0, 1
Style: LyricAlt, AppleSDGothicNeo-Bold, 104, &H00FFFFFF, &H000000FF, &H001020A0, &H80000000, -1, 0, 0, 0, 100, 100, 2, 0, 1, 8, 4, 5, 60, 60, 0, 1
Style: Section,  AppleGothic,           60,  &H00C0C0C0, &H000000FF, &H00000000, &H80000000, -1, 0, 0, 0, 100, 100, 4, 0, 1, 5, 2, 8, 80, 80, 80, 1
Style: Karaoke,  AppleSDGothicNeo-Bold, 110, &H0000F0FF, &H0000A0FF, &H00000000, &H80000000, -1, 0, 0, 0, 100, 100, 3, 0, 1, 8, 5, 5, 60, 60, 0, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
