#!/usr/bin/env python3
"""
Generate one prompt file per song in image/prompts/<N>-<tag>.txt.

Each prompt is built from:
  · LOCKED composition (identical across all 21 covers — same girl, pose,
    skyline, "반포자이즘" logotype bottom-right)
  · TONE profile (per genre tag — palette, lighting, atmosphere, expression)
  · PER-TRACK FLAVOR (handcrafted variation so 1 & 18, or 3 & 11, or three
    kdrama-OST tracks don't generate the same image)
  · AUDIO FEATURE NOTES (BPM / key / mode / brightness / busy-ness derived
    from tracks/audio_features.json — concrete handles like "weighty 69 BPM
    rubato", "F minor introspective", "harsh stage strobes match the 4.5
    onsets/sec attack density")

Run:
    tools/build_prompts.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


LOCKED_HORIZONTAL = """\
Album cover, 16:9 horizontal, ~1920×1080, illustrated / anime-adjacent style with painterly shading (no photoreal skin).

COMPOSITION (identical to the reference cover for song 1 — keep girl, pose, props, skyline, and logotype consistent across the whole series):
A young Korean woman in her early twenties with long dark hair stands on a high apartment balcony at night, body turned three-quarters to the right so her profile faces camera-left. She wears a small ornamental gold crown perched on her head. In her right hand she holds up a smartphone displaying a real-estate listing screen (apartment thumbnail visible). In her left hand she carries a luxury paper shopping bag (cream/beige with "LUXURY" lettering on the side). Behind her, the Banpo (반포) riverside apartment complex stretches across the Han river at night — dense rows of lit-up high-rise residential towers, the iconic rainbow-lit Banpo Bridge moonlight fountain spilling colored light across the water in mid-frame, the Lotte World Tower spire on the left horizon, distant Seoul skyline.

LOCKED LOGOTYPE — bottom-right corner: the stylized 3D Korean wordmark "반포자이즘" rendered in thick chunky letterforms, glossy yellow-to-orange gradient fill with a bright cyan/teal outline and subtle glow. This must match the exact same logo style as cover 1 (treat as a fixed brand mark across the whole 21-cover series; never alter it regardless of tone).
"""


LOCKED_VERTICAL = """\
Album cover, 9:16 vertical, ~1080×1920 (YouTube Shorts / Reels / TikTok), illustrated / anime-adjacent style with painterly shading (no photoreal skin).

COMPOSITION (identical to the reference cover for song 1 — keep girl, pose, props, skyline, and logotype consistent across the whole series):
A young Korean woman in her early twenties with long dark hair stands on a high apartment balcony at night, body turned three-quarters to the right so her profile faces camera-left. She wears a small ornamental gold crown perched on her head. In her right hand she holds up a smartphone displaying a real-estate listing screen (apartment thumbnail visible). In her left hand she carries a luxury paper shopping bag (cream/beige with "LUXURY" lettering on the side). Behind her, the Banpo (반포) riverside apartment complex stretches across the Han river at night — dense rows of lit-up high-rise residential towers, the iconic rainbow-lit Banpo Bridge moonlight fountain spilling colored light across the water in mid-frame, the Lotte World Tower spire on the left horizon, distant Seoul skyline.

LOCKED LOGOTYPE — bottom-right corner: the stylized 3D Korean wordmark "반포자이즘" rendered in thick chunky letterforms, glossy yellow-to-orange gradient fill with a bright cyan/teal outline and subtle glow. This must match the exact same logo style as cover 1 (treat as a fixed brand mark across the whole 21-cover series; never alter it regardless of tone).
"""


# ─── Tone profiles ────────────────────────────────────────────────────────────
# Keyed by tone-tag (the second half of the filename). Each is a *base*; the
# per-track flavor block overrides/extends.
TONES = {
    "synth-pop": {
        "name": "K-Pop synth-driven electronic — vivid neon",
        "palette": "saturated cyan + magenta + electric pink + lemon-yellow accents; chrome highlights on the smartphone and crown",
        "lighting": "harsh stage rim-light, hot pink hair light + cyan key light from screen-side, crisp specular shine",
        "atmosphere": "clear sharp night, light cherry-petal sparkles in the air, faint lens flares, no haze",
        "expression": "confident, lips slightly parted, eyes open, gentle wind in hair",
        "extra": "tiny holographic shimmer on her cheek, neon billboard letter-fragments dissolved into the city bokeh",
    },
    "ballad": {
        "name": "Ballad / alternative pop / baroque pop / dream pop / sadcore",
        "palette": "cool desaturated blues, muted lavenders, dusty grays, soft warm lamp accents — opposite of the synth-pop neon",
        "lighting": "hazy diffuse glow, soft warm balcony lamp brushing one side of her face, low contrast",
        "atmosphere": "light drizzle, faint fog rolling off the Han river, gentle bokeh from far city lights, a few raindrops beading on the balcony railing",
        "expression": "melancholic and contemplative, eyes slightly lowered, lips closed in a soft wistful expression; a single subtle tear gleam optional",
        "extra": "faint film grain, soft watercolor edges, pastel softness — like a 2010s indie sleeve (Lana Del Rey / Mitski / 한국 발라드 cover aesthetic)",
    },
    "house-hip-hop": {
        "name": "2025 house × electronic hip-hop hybrid — hyper-modern club",
        "palette": "chrome silver + acid magenta + obsidian black; cold blue night with red laser glints",
        "lighting": "punchy specular highlights, glossy plasticky shine, sharp shadow edges, occasional strobe-frozen blur",
        "atmosphere": "crowd silhouettes far below the balcony, low-flying drone lights, ribbon-like motion streaks frozen mid-air",
        "expression": "cocky head-tilt, half-smile, eyes narrowed slightly",
        "extra": "tiny crystalline particles suspended in air, faint vapor curling around her wrist, treated like a 2025 club-mix promo still",
    },
    "90s-hip-hop": {
        "name": "90s East Coast hip-hop — boombap warmth",
        "palette": "sepia-warm browns, mustard yellows, deep burgundy, brass + brick textures",
        "lighting": "single warm streetlamp from upper right, deep shadow on the river side, golden-hour leaked-light streaks",
        "atmosphere": "graininess everywhere, faint VHS noise + scanlines, NYC-style brick-pattern overlay subtly visible on adjacent walls, scattered cassette + walkman silhouettes in bokeh",
        "expression": "stone-faced, jaw set, gaze fixed cold and steady on the city",
        "extra": "a chunky gold dookie chain hanging at her chest, a single oversized hoop earring, paper bag taking on slight sepia tint",
    },
    "dark-indie": {
        "name": "Electropop × dark indie pop — gothic synth",
        "palette": "deep oxblood reds, ink-purples, near-black with violet highlights; warm candle gold accents",
        "lighting": "single low warm flame source casting long shadows up her face, hard contrast, much of the frame in deep shadow",
        "atmosphere": "smoke curling slowly, a half-melted candle on the railing, distant flicker of bare bulbs, no stars (clouded sky)",
        "expression": "haunted, eyes wide and dilated, mouth set in a flat hard line — half-defiant, half-blank",
        "extra": "subtle film stain, smoke-edge fade on the corners, treatment like a 2017 dark-pop record sleeve",
    },
    "prog-house": {
        "name": "2020s progressive house — festival cathedral",
        "palette": "deep oceanic blues + cold cyan + soft white laser; small accents of rose gold",
        "lighting": "huge volumetric blue laser shafts cutting downward through mist, multiple parallel beams, central spotlight crowning her",
        "atmosphere": "thick stage fog at her ankles, distant raised silhouetted hands of a festival crowd visible far below as a sea, smoke catching every light beam",
        "expression": "eyes closed in transcendent calm, head tilted slightly upward into the light, expression peaceful at the drop",
        "extra": "wind streamers / confetti frozen mid-air, glitter dust, EDC-style stage aesthetic; this should look like a Tomorrowland after-movie keyframe",
    },
    "kdrama-ost-spring": {
        "name": "Korean Drama OST — spring rain ballad",
        "palette": "soft sage greens, ivory whites, blush pinks, warm amber lamp glow",
        "lighting": "gentle overcast daylight bleeding into early evening, soft halation on hairline, warm window light from inside the apartment",
        "atmosphere": "spring rain drizzling, cherry blossom petals stuck to the wet rail, transparent umbrella implied off-frame, a delicate watery sheen on everything",
        "expression": "soft sorrow, eyes glistening but not crying, mouth softly parted, looking at the city with quiet ache",
        "extra": "treatment like a tvN drama poster — handwritten-feel framing, slight glow halo around the lamp",
    },
    "kdrama-ost-winter": {
        "name": "Korean Drama OST — winter snow climax",
        "palette": "navy blues, pure whites, warm amber lamp pools on snow, breath-fog cool whites",
        "lighting": "warm tungsten streetlamp from below-left, cool moonlight wash, breath visible against dark sky",
        "atmosphere": "thick gentle snow flurries falling around her, soft white powder on shoulders and crown, small puffs of breath, an empty park bench far below",
        "expression": "softly wistful, slight smile through cold, eyes shining, a single snowflake on her eyelash",
        "extra": "treatment like an 'Goblin (도깨비)' or 'Crash Landing on You' OST cover, cinematic 21:9 wide framing energy compressed into 16:9",
    },
    "kdrama-ost-autumn": {
        "name": "Korean Drama OST — autumn farewell",
        "palette": "warm rust oranges, golden ochres, deep walnut browns, soft cream highlights",
        "lighting": "low golden-hour sunset bleeding sideways across her face, long warm shadows, soft halation",
        "atmosphere": "red maple + ginkgo leaves drifting through the air, a few caught on her crown and bag, late-autumn warmth fighting an evening chill",
        "expression": "bittersweet half-smile, eyes turned to the river slightly downcast, expression of letting-go",
        "extra": "treatment like a JTBC romance drama poster — softly painterly, slight oil-paint canvas grain",
    },
    "kpop-hh-glossy": {
        "name": "K-Pop hip-hop — glossy bling swagger",
        "palette": "obsidian black + 24k gold + hot pink + ice white",
        "lighting": "studio-bright key from camera-right, hard rim of pink neon, glossy plasticky surfaces",
        "atmosphere": "subtle smoke at her ankles, gold chain glints catching light, paper bag re-treated with embossed gold foil texture, faint dollar-sign or hash-tag sparkles",
        "expression": "sharp smirk, one brow raised, tinted black sunglasses pushed down on her nose",
        "extra": "chunky Cuban-link gold chain, oversized hoop earrings, manicured nails visible on the phone",
    },
    "kpop-hh-misty": {
        "name": "K-Pop hip-hop — late-night trap chill",
        "palette": "deep teal + muted gold + foggy lavender; less saturation than the glossy variant",
        "lighting": "soft phone-screen glow lighting her face from below-right, dim warm streetlamp far away",
        "atmosphere": "thick low fog, occasional drifting embers, a long exhale of vapor near her mouth, subtle muted city haze",
        "expression": "drowsy half-lidded eyes, deadpan, lips slightly pursed — the look of 3 a.m.",
        "extra": "thin chain instead of dookie, smaller earrings, headphone cable trailing from her ear; like a 88rising / Crush 4 a.m. record sleeve",
    },
    "europop-glitter": {
        "name": "Europop 2000s — glitter ball euphoria",
        "palette": "silver chrome + hot pink + magenta + electric blue; mirrorball facets reflected everywhere",
        "lighting": "shifting disco-ball spots speckling her face, hot pink key light, bright catchlights in her eyes",
        "atmosphere": "thousands of tiny mirrorball reflections crawling across the wall and the apartment buildings behind her, confetti drifting, sparkle particles",
        "expression": "open joyful smile, eyes wide, head turned playfully",
        "extra": "outfit upgraded with metallic silver puffer collar, glittery makeup; treatment like a 2003 ABBA-meets-Cascada single sleeve",
    },
    "europop-sad-disco": {
        "name": "Europop 2000s — sad disco / 3 a.m. after the party",
        "palette": "ghostly silver + muted purple + cold blue, with a single warm pink spotlight",
        "lighting": "low single mirrorball still spinning, weaker than peak; mostly cool moonlight",
        "atmosphere": "stray confetti on the wet balcony floor, smudged mascara, an empty plastic cup tipped over far in the corner, faint glitter dust",
        "expression": "vacant stare into nothing, eyes glassy, lips slightly downturned, the smile gone",
        "extra": "metallic clothing visible but tired/wrinkled; treatment like an Annie / Robyn 'Dancing On My Own' sleeve",
    },
    "berlin-minimal": {
        "name": "Berlin house × hardcore × minimal — industrial gray + single red",
        "palette": "concrete gray, raw steel, ink black, with one single saturated red light source",
        "lighting": "harsh red point-source from upper-left casting long sharp shadows, otherwise flat gray, no warm tones at all",
        "atmosphere": "thick haze of dry-ice fog at calf height, exposed pipes / rebar texture on nearby walls, water dripping somewhere, a single distant strobe burst frozen",
        "expression": "completely blank, eyes closed listening, body subtly leaning into the beat",
        "extra": "minimal techno asceticism — strip out warmth wherever possible; the only saturated color in the frame should be the red light, the rainbow bridge (subdued), and the locked 반포자이즘 logotype",
    },
    "30s-jazz": {
        "name": "1930s jazz & blues — sepia speakeasy",
        "palette": "deep sepia + tarnished brass + smoky charcoal + warm amber",
        "lighting": "single hanging incandescent bulb above her, hard warm-yellow falloff, much of frame in deep shadow",
        "atmosphere": "thick blue-gray cigarette smoke curling through the frame, faint film projector flicker, dust motes in beam, vintage record-grain stippling overlay",
        "expression": "smoky-lidded gaze, lips painted dark red, head tilted into the light",
        "extra": "outfit reinterpreted as a 1930s silk slip-dress silhouette + long gloves under her cardigan, an art-deco frame border subtly visible at the canvas edges, treatment like a vintage RCA 78rpm sleeve",
    },
    "anime-ed": {
        "name": "Japanese anime ending — pastel watercolor",
        "palette": "soft pastel pinks, baby blues, cream whites, warm peach; sky bleeding into rose gold",
        "lighting": "very soft and even, no hard shadows, slight halation on every bright edge",
        "atmosphere": "cherry blossom petals drifting up gently, light breeze, distant train passing softly in the bokeh, a single warm window across the river",
        "expression": "soft closed-mouth smile, eyes slightly downcast, peaceful and slightly sad",
        "extra": "treatment like a Makoto Shinkai film ED card — visible watercolor brushstroke edges, subtle paper texture, hand-lettered feel for everything *except* the locked 반포자이즘 logo (which stays the same)",
    },
    "80s-french": {
        "name": "1980s French song — pastel cassette aesthetic",
        "palette": "dusty rose + cream + powder mint + soft lilac; warm white highlights",
        "lighting": "soft diffuse studio key, gauzy filter, slight pink push in shadows",
        "atmosphere": "subtle VHS scanline overlay, slight chromatic aberration on bright edges, vintage Polaroid border feeling but not literally bordered, scattered tiny stars",
        "expression": "elegant melancholy, head turned more profile, eyes half-closed, lips in a refined slight pout",
        "extra": "outfit re-styled with an 80s pussybow blouse hint and shoulder pads under the cardigan; treatment like a Sylvie Vartan / France Gall LP sleeve from 1983",
    },
    "berlin-90s": {
        "name": "Late 90s Berlin house — post-wall rave",
        "palette": "concrete gray + acid green laser + cold magenta + cigarette smoke yellow",
        "lighting": "horizontal acid-green laser sweeping past her, mixed with cold magenta backlight; harsh, alternating, restless",
        "atmosphere": "thick stage haze, exposed concrete walls covered in faded paste-up posters, a kick-drum implied by everything subtly vibrating, late-90s rave flyer textures bleeding in at the edges",
        "expression": "lost in the music, eyes closed, slight smile, one hand barely visible raised",
        "extra": "subtle CRT chromatic aberration, period-correct 90s typographic noise around the frame; treatment like a Tresor or E-Werk flyer scan",
    },
}


# ─── Per-track flavor: small handcrafted variation so duplicates don't render identically ──
TRACK_FLAVOR = {
    1:  {"tag": "synth-pop",          "outfit": "powder-blue cardigan over a white tee, the original reference cover", "extra": "reference cover — keep as the canonical look every other track varies from"},
    2:  {"tag": "ballad",             "outfit": "dusty plum cardigan, sleeves pulled over her hands",                  "extra": "raindrops bead on the balcony railing; a single wet leaf stuck to the bag"},
    3:  {"tag": "house-hip-hop",      "outfit": "chrome-silver puffer collar over the cardigan, glossy black nails",   "extra": "magenta-on-cyan acid bias; she stands slightly off-center as if mid-beat-drop"},
    4:  {"tag": "synth-pop",          "outfit": "dusty lilac cardigan, smudged silver eyeshadow",                      "extra": "MINOR-key synth-pop variation — pull the saturation back vs cover 1, push the violet end of the palette; she's quieter, eyes lowered, this is the moodier sibling of cover 1"},
    5:  {"tag": "90s-hip-hop",        "outfit": "oversized varsity-style jacket over the cardigan, gold dookie chain", "extra": "single warm-amber streetlamp upper right, hard shadow on the river; cassette-era warmth"},
    6:  {"tag": "dark-indie",         "outfit": "near-black cardigan, a single tarnished silver locket at her throat", "extra": "a half-melted black candle on the railing, smoke curling toward the bag handles"},
    7:  {"tag": "prog-house",         "outfit": "white silk shirt under the cardigan (cardigan slung loose)",          "extra": "she stands at the front of an implied festival cathedral; the Banpo Bridge below blurs into a single laser line, drop-moment energy"},
    8:  {"tag": "kdrama-ost-spring",  "outfit": "cream knit cardigan, small pearl earring",                            "extra": "slowest of all 21 tracks (69 BPM rubato) — pose is fully still, almost photographic; tear-glisten allowed"},
    9:  {"tag": "kpop-hh-glossy",     "outfit": "black crop top under an open white blazer, gold hoops, tinted shades",  "extra": "she's pushing the shades down with one finger; high-gloss, mid-action attitude"},
    10: {"tag": "europop-glitter",    "outfit": "silver metallic puffer collar, holographic eye glitter",              "extra": "mirrorball reflections crawl across the apartments behind her; bubblegum euphoria"},
    11: {"tag": "house-hip-hop",      "outfit": "burgundy leather jacket replaces the cardigan",                      "extra": "DIFFERENT from cover 3 — push palette toward sunrise rooftop pool-party (warm orange + amber + soft pink) rather than club magenta; same hyper-modern energy but warmer hour, busiest onset density (4.1/sec) translates to scattered floating champagne droplets"},
    12: {"tag": "berlin-minimal",     "outfit": "raw concrete-gray cardigan, no metallic accents anywhere",            "extra": "the busiest track of the album (4.6 onsets/sec) but rendered as relentless monochrome — only the red point-source, the subdued bridge, and the locked logotype carry color"},
    13: {"tag": "kdrama-ost-winter",  "outfit": "ivory wool cardigan, beige scarf loose at her neck",                   "extra": "snow crown the perched gold crown; this OST is faster (143 BPM) so a sweeping wind catches her hair and a few cherry-blossom-like snow swirls cross the frame"},
    14: {"tag": "30s-jazz",           "outfit": "silk slip-dress hint under cardigan, long opera gloves, dark red lip","extra": "art-deco gold border subtly evoked at the canvas edges; jazz lounge warmth; a vintage condenser microphone shadow implied off-frame"},
    15: {"tag": "europop-sad-disco",  "outfit": "wrinkled metallic silver top, smudged mascara, hair slightly mussed", "extra": "minor-key europop after-party — the disco ball still spinning weakly, the joy of cover 10 worn off into hollow stare"},
    16: {"tag": "kdrama-ost-autumn",  "outfit": "soft camel coat over the cardigan, knit scarf",                       "extra": "longest intro of the album (6.1s) — gives the cover a more deliberate, painterly stillness; maple + ginkgo leaves drifting"},
    17: {"tag": "kpop-hh-misty",     "outfit": "oversized hoodie under cardigan, hood half-up, wired earbuds in ear", "extra": "the slowest kpop-hh track (89 BPM, A# major) — late-night, the phone-screen is the brightest light on her face"},
    18: {"tag": "synth-pop",          "outfit": "icy mint-green cardigan, pink hair gradient at the tips",             "extra": "SAME 136 BPM D# major as cover 1 — variation by palette swap (push green + cyber-pink instead of cyan + magenta) and a Y2K cybergrunge tint (faint dithered noise overlay); same energy, second outfit"},
    19: {"tag": "anime-ed",           "outfit": "soft cream cardigan, ribbon tie at the collar, school-uniform-adjacent","extra": "Japanese anime ED card — cherry blossom petals drifting *upward*, a distant white train crossing the river bokeh, watercolor brushstrokes faintly visible"},
    20: {"tag": "80s-french",         "outfit": "pussybow blouse under the cardigan, hint of shoulder pad",            "extra": "VHS pastel filter, slight chromatic aberration on the bridge lights; treat as a 1983 French disco LP sleeve"},
    21: {"tag": "berlin-90s",         "outfit": "black mesh top under cardigan, smudged dark eye-makeup",             "extra": "acid green laser horizontal sweep across the apartment façade, paste-up rave posters bleeding in at the canvas edges; this is the post-wall Berlin '95 sister of cover 12 (which is its modern 2025 minimal grandchild)"},
}


def fmt_features(meta: dict, feats: dict) -> str:
    bpm = feats["tempo_bpm"]
    key = feats["key"]
    mode = feats["mode"]
    centroid = feats["spectral_centroid_hz_mean"]
    onset = feats["onset_rate_hz"]
    intro = feats["intro_silence_s"]

    bpm_note = (
        "very slow rubato" if bpm < 80 else
        "slow ballad pace" if bpm < 100 else
        "mid-tempo" if bpm < 120 else
        "uptempo" if bpm < 140 else
        "fast / driving" if bpm < 160 else "very fast"
    )
    bright_note = (
        "dark / muffled spectrum" if centroid < 2200 else
        "warm mid spectrum" if centroid < 2700 else
        "bright spectrum" if centroid < 3000 else
        "very bright / glassy spectrum"
    )
    busy_note = (
        "sparse attack density (slow events)" if onset < 2.5 else
        "moderate attack density" if onset < 3.5 else
        "busy attack density (lots of motion)" if onset < 4.5 else
        "very busy attack density (relentless motion)"
    )
    intro_note = (
        "long instrumental intro — favor stillness in the pose" if intro >= 3.0 else
        "modest intro" if intro >= 1.0 else "almost no intro — straight into energy"
    )
    return (
        f"AUDIO-DERIVED NOTES (use these to calibrate energy & mood — these are objective features pulled from the actual mp3):\n"
        f"- Tempo: {bpm:.0f} BPM ({bpm_note}). Match the cover's implied movement to this — wind, particles, hair sway.\n"
        f"- Key: {key} ({mode}). {'Push warmer / more triumphant palette accents.' if mode == 'major' else 'Push cooler / more melancholy palette accents.'}\n"
        f"- Spectral centroid: {centroid:.0f} Hz — {bright_note}. {'Lean brighter highlights.' if centroid >= 2700 else 'Lean dimmer, more shadow.'}\n"
        f"- Onset rate: {onset:.2f} events/sec — {busy_note}. {'Add scattered motion particles / streaks.' if onset >= 3.5 else 'Keep negative space; avoid busy particles.'}\n"
        f"- Intro silence: {intro:.1f}s — {intro_note}.\n"
    )


def build_one(n: int, meta: dict, feats: dict, orientation: str) -> tuple[str, str]:
    """orientation: 'horizontal' or 'vertical'."""
    flavor = TRACK_FLAVOR[n]
    tag = flavor["tag"]
    tone = TONES[tag]

    tone_block = (
        f"TONE — {tone['name']}:\n"
        f"- Palette: {tone['palette']}.\n"
        f"- Lighting: {tone['lighting']}.\n"
        f"- Atmosphere: {tone['atmosphere']}.\n"
        f"- Expression: {tone['expression']}.\n"
        f"- Extra: {tone['extra']}.\n"
    )
    flavor_block = (
        f"THIS TRACK ({n}) — {meta['genre']}, {meta['duration']}, {feats['tempo_bpm']:.0f} BPM, {feats['key']}:\n"
        f"- Outfit / styling: {flavor['outfit']}.\n"
        f"- Track-specific note: {flavor['extra']}.\n"
    )
    audio_block = fmt_features(meta, feats)

    locked = LOCKED_HORIZONTAL if orientation == "horizontal" else LOCKED_VERTICAL
    body = (
        locked
        + "\n"
        + tone_block
        + "\n"
        + flavor_block
        + "\n"
        + audio_block
        + "\nThe locked 반포자이즘 logotype in the bottom-right corner ALWAYS keeps its original vivid yellow-orange gradient and cyan/teal outline — never restyle it to match the tone. It should remain the consistent brand mark across all 21 covers, identical between horizontal and vertical variants.\n"
        + "\nAvoid: harsh deviations from the locked composition, additional UI elements, watermarks, photoreal faces, exaggerated anime proportions, extra captions or text overlays.\n"
    )
    return tag, body


def main():
    tracks = json.loads((ROOT / "tracks/tracks.json").read_text(encoding="utf-8"))
    feats_all = json.loads((ROOT / "tracks/audio_features.json").read_text(encoding="utf-8"))

    targets = [
        ("horizontal", ROOT / "image/prompts"),
        ("vertical",   ROOT / "image/prompts/vertical"),
    ]
    for _, d in targets:
        d.mkdir(parents=True, exist_ok=True)

    totals = {}
    for orientation, out_dir in targets:
        # clear stale auto-generated prompts (preserve _MASTER.md, _MASTER-vertical.md, etc.)
        for p in out_dir.glob("*.txt"):
            p.unlink()

        written = []
        for t in tracks:
            n = t["index"]
            feats = feats_all.get(str(n))
            if not feats:
                continue
            tag, body = build_one(n, t, feats, orientation)
            out_p = out_dir / f"{n}-{tag}.txt"
            out_p.write_text(body, encoding="utf-8")
            written.append((n, tag, len(body)))
        totals[orientation] = written

    for orientation, written in totals.items():
        print(f"\n── {orientation} ── ({targets[0][1] if orientation == 'horizontal' else targets[1][1]})")
        for n, tag, sz in written:
            print(f"  {n:>2}-{tag:<20}  {sz:>5} chars")
        print(f"  wrote {len(written)} prompt files")


if __name__ == "__main__":
    main()
