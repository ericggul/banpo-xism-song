/* ── Karaoke track metadata & lyrics ── */
/*  Source of truth for the 반포자이즘 album:
 *  - 18 Korean tracks (반포자이즘-1 .. 반포자이즘-18) walking the i0 diagonal
 *  - 3 language bonus tracks (JA / FR / DE) — distinct titles
 *  Mirrors the structure used elsewhere in the wider project.
 *  Keep this file as the canonical metadata; tracks/tracks.json is a
 *  derived view for shell tooling (rebuild via tools/sync_tracks.py).
 */

import { getApartmentIdentity } from '@/utils/functions/pricing';

// Track → apartment cell mapping. Tracks 1..18 walk the diagonal from 반포자이 (i0=18)
// down to 산포차이 (i0=1). Track 19 is reserved for the future 빤포짜이즘 (i0=0).
// Bonus tracks (19..21) have no apartment cell — price/speed rows stay blank.
// Returns `null` for bonus/invalid indices so callers can cleanly branch.
export function getTrackCell(trackIndex) {
  const k = Math.floor(Number(trackIndex) || 0);
  if (k < 1 || k > 18) return null;
  const i0 = 19 - k;
  return { loc0: i0, brand0: i0, loc1: i0 + 1, brand1: i0 + 1, flat: i0 * 19 + i0 };
}

function koTrackLabel(trackIndex) {
  const cell = getTrackCell(trackIndex);
  if (!cell) return '반포자이즘';
  const { fullName } = getApartmentIdentity(cell.loc0, cell.brand0);
  return `${fullName}즘`;
}

const KO_TRACK_META = [
  { duration: '2:33', genre: 'K-Pop, Synth-driven, Electronic' },
  { duration: '2:45', genre: 'Alternative Pop, Baroque Pop, Dream Pop, Sadcore' },
  { duration: '2:06', genre: '2025 House Electronic Hip Hop' },
  { duration: '1:56', genre: 'K-Pop, Synth-driven, Electronic' },
  { duration: '1:19', genre: '90s East Coast Hip-Hop' },
  { duration: '2:29', genre: 'Electropop, Dark Indie Pop' },
  { duration: '4:06', genre: '2020s Progressive House' },
  { duration: '3:03', genre: 'Korean Drama OST' },
  { duration: '1:49', genre: 'K-Pop Hip Hop' },
  { duration: '2:12', genre: 'Europop 2000s' },
  { duration: '2:02', genre: '2025 House Electronic Hip Hop' },
  { duration: '2:49', genre: 'Berlin House, Hardcore, Minimal' },
  { duration: '3:09', genre: 'Korean Drama OST' },
  { duration: '2:35', genre: '1930s Jazz & Blues' },
  { duration: '2:32', genre: 'Europop 2000s' },
  { duration: '2:50', genre: 'Korean Drama OST' },
  { duration: '1:31', genre: 'K-Pop Hip Hop' },
  { duration: '2:03', genre: 'K-Pop, Synth-driven, Electronic' },
];

export const TRACKS = [
  ...KO_TRACK_META.map((meta, i) => {
    const index = i + 1;
    return {
      index,
      label: koTrackLabel(index),
      filename: `반포자이즘-${index}`,
      duration: meta.duration,
      genre: meta.genre,
      lang: 'KO',
    };
  }),
  { index: 19, label: 'バンポザイの夢',      filename: 'バンポザイの夢',    duration: '2:56', genre: 'Japanese Anime Ending OST', lang: 'JA', isBonus: true },
  { index: 20, label: 'Le rêve de BanpoXi', filename: 'Le rêve de BanpoXi', duration: '2:44', genre: '1980s French Song',         lang: 'FR', isBonus: true },
  { index: 21, label: 'BanpoXis Traum',     filename: 'BanpoXis Traum',     duration: '2:46', genre: 'Late 90s Berlin House',     lang: 'DE', isBonus: true },
];

export const TRACK_COUNT = TRACKS.length;

/* ── Lyrics by language ── */

export const LYRICS = {
  KO: [
    { section: 'Verse',
      lines: [
        '반포의 빛이 나를 부르네',
        '자이의 품에 안기고 싶어',
        '강남의 별들 아래 꿈꾸네',
        '높은 순위 속에 날 세우고 싶어',
      ] },
    { section: 'Chorus',
      lines: [
        '반포야 반포야 너는 나의 별',
        '자이야 자이야 나를 안아줘',
        '상급지의 왕관 내가 쓸래',
        '학군지도 나를 반겨줄래',
      ] },
    { section: 'Verse 2',
      lines: [
        '강바람 속에 흩날리는 꿈',
        '부동산 지도 속 반짝이는 점',
        '하급지는 뒤로 상급지로 달려',
        '자이의 문턱 넘고 싶어',
      ] },
    { section: 'Chorus',
      lines: [
        '반포야 반포야 너는 나의 별',
        '자이야 자이야 나를 안아줘',
        '상급지의 왕관 내가 쓸래',
        '학군지도 나를 반겨줄래',
      ] },
    { section: 'Bridge',
      lines: [
        '순위의 숫자에 내 마음이 춤춰',
        '반포의 꿈이 나를 깨우네',
        '자이의 이름을 가슴에 새기며',
        '내 미래를 이곳에 맡기고 싶어',
      ] },
    { section: 'Chorus',
      lines: [
        '반포야 반포야 너는 나의 별',
        '자이야 자이야 나를 안아줘',
        '상급지의 왕관 내가 쓸래',
        '학군지도 나를 반겨줄래',
      ] },
  ],

  JA: [
    { section: 'Verse',
      lines: [
        'バンポの光が私を呼ぶ',
        'ジャイの胸に抱きしめたい',
        '江南の星の下で夢を見る',
        '高い順位の中に私を立てたい',
      ] },
    { section: 'Chorus',
      lines: [
        'Banpoya Banpoya あなたは私の星です',
        'ジャイヤ ジャイヤ 私を抱きしめて',
        '上級地の王冠私が寂しい',
        '学区も私を歓迎します。',
      ] },
    { section: 'Verse 2',
      lines: [
        '川の風の中に散らばる夢',
        '不動産地図の中の輝く点',
        '下給紙は後ろに上級紙に走ります',
        'ジャイのしきい値を超えたい',
      ] },
    { section: 'Chorus',
      lines: [
        'Banpoya Banpoya あなたは私の星です',
        'ジャイヤ ジャイヤ 私を抱きしめて',
        '上級地の王冠私が寂しい',
        '学区も私を歓迎します。',
      ] },
    { section: 'Bridge',
      lines: [
        'ランキングの数に私の心が踊る',
        'バンポの夢は私を目覚めさせる',
        'ジャイの名前を胸に刻む',
        '私の未来をここに任せたい',
      ] },
    { section: 'Chorus',
      lines: [
        'Banpoya Banpoya あなたは私の星です',
        'ジャイヤ ジャイヤ 私を抱きしめて',
        '上級地の王冠私が寂しい',
        '学区も私を歓迎します。',
      ] },
  ],

  FR: [
    { section: 'Couplet',
      lines: [
        "La lumière de Banpo m'appelle",
        'Je veux être tenu dans les bras de Jai',
        'Je rêve sous les étoiles de Gangnam',
        'Je veux me placer dans un haut classement',
      ] },
    { section: 'Refrain',
      lines: [
        'Banpo, Banpo, tu es mon étoile',
        'Xi, Xi, embrasse-moi',
        'Je veux porter la couronne de la classe supérieure',
        "Le plan du district scolaire m'accueillera-t-il ?",
      ] },
    { section: 'Couplet 2',
      lines: [
        'Un rêve flottant dans le vent de la rivière',
        'Points brillants sur la carte immobilière',
        'Le niveau inférieur va en arrière vers le niveau supérieur.',
        'Je veux franchir le seuil de Jai',
      ] },
    { section: 'Refrain',
      lines: [
        'Banpo, Banpo, tu es mon étoile',
        'Xi, Xi, embrasse-moi',
        'Je veux porter la couronne de la classe supérieure',
        "Le plan du district scolaire m'accueillera-t-il ?",
      ] },
    { section: 'Pont',
      lines: [
        'Mon cœur danse au nombre de classements',
        'Le rêve de Banpo me réveille',
        'Avec le nom de Jai gravé dans mon cœur',
        'Je veux confier mon avenir ici',
      ] },
    { section: 'Refrain',
      lines: [
        'Banpo, Banpo, tu es mon étoile',
        'Xi, Xi, embrasse-moi',
        'Je veux porter la couronne de la classe supérieure',
        "Le plan du district scolaire m'accueillera-t-il ?",
      ] },
  ],

  DE: [
    { section: 'Vers',
      lines: [
        'Das Licht von Banpo ruft mich',
        'Ich möchte in Jais Armen gehalten werden',
        'Ich träume unter den Sternen von Gangnam',
        'Ich möchte mich in einem hohen Ranking platzieren',
      ] },
    { section: 'Chor',
      lines: [
        'Banpo, Banpo, du bist mein Star',
        'Jai, Jai, umarme mich',
        'Ich möchte die Krone der Oberschicht tragen',
        'Wird mich die Karte des Schulbezirks willkommen heißen?',
      ] },
    { section: 'Vers 2',
      lines: [
        'Ein Traum, der im Flusswind flattert',
        'Leuchtende Punkte auf der Immobilienkarte',
        'Die untere Ebene verläuft rückwärts zur oberen Ebene.',
        'Ich möchte Jais Schwelle überschreiten',
      ] },
    { section: 'Chor',
      lines: [
        'Banpo, Banpo, du bist mein Star',
        'Jai, Jai, umarme mich',
        'Ich möchte die Krone der Oberschicht tragen',
        'Wird mich die Karte des Schulbezirks willkommen heißen?',
      ] },
    { section: 'Brücke',
      lines: [
        'Mein Herz tanzt bei der Anzahl der Rankings',
        'Banpos Traum weckt mich',
        'Mit Jais Namen in meinem Herzen eingraviert',
        'Hier möchte ich meine Zukunft anvertrauen',
      ] },
    { section: 'Chor',
      lines: [
        'Banpo, Banpo, du bist mein Star',
        'Jai, Jai, umarme mich',
        'Ich möchte die Krone der Oberschicht tragen',
        'Wird mich die Karte des Schulbezirks willkommen heißen?',
      ] },
  ],
};
