// Languages that use non-Latin scripts and benefit from romanization hint
const NON_LATIN_LANGS = new Set([
  'hi', 'te', 'ta', 'kn', 'ml', 'mr', 'bn', 'gu', 'pa',
  'ar', 'fa', 'ur', 'he', 'ru', 'uk', 'bg', 'sr', 'el',
  'zh', 'ja', 'ko', 'th', 'vi', 'my', 'km', 'si',
]);

// Simple character-level transliteration maps
const MAPS: Record<string, Record<string, string>> = {
  ru: {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z',
    'и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r',
    'с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch','ш':'sh',
    'щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
  },
  el: {
    'α':'a','β':'v','γ':'g','δ':'d','ε':'e','ζ':'z','η':'i','θ':'th',
    'ι':'i','κ':'k','λ':'l','μ':'m','ν':'n','ξ':'x','ο':'o','π':'p',
    'ρ':'r','σ':'s','τ':'t','υ':'y','φ':'f','χ':'ch','ψ':'ps','ω':'o',
  },
  uk: {
    'а':'a','б':'b','в':'v','г':'h','д':'d','е':'e','є':'ye','ж':'zh',
    'з':'z','и':'y','і':'i','ї':'yi','й':'y','к':'k','л':'l','м':'m',
    'н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f',
    'х':'kh','ц':'ts','ч':'ch','ш':'sh','щ':'shch','ю':'yu','я':'ya',
  },
};

function transliterateWithMap(text: string, map: Record<string, string>): string {
  return text.toLowerCase().split('').map(c => map[c] ?? c).join('');
}

// Devanagari (Hindi, Marathi) basic transliteration
function transliterateDevanagari(text: string): string {
  const map: Record<string, string> = {
    'अ':'a','आ':'aa','इ':'i','ई':'ee','उ':'u','ऊ':'oo','ए':'e','ऐ':'ai',
    'ओ':'o','औ':'au','क':'ka','ख':'kha','ग':'ga','घ':'gha','च':'cha',
    'छ':'chha','ज':'ja','झ':'jha','ट':'ta','ड':'da','त':'ta','थ':'tha',
    'द':'da','ध':'dha','न':'na','प':'pa','फ':'pha','ब':'ba','भ':'bha',
    'म':'ma','य':'ya','र':'ra','ल':'la','व':'va','श':'sha','ष':'sha',
    'स':'sa','ह':'ha','ं':'n','ः':'h','ा':'a','ि':'i','ी':'ee','ु':'u',
    'ू':'oo','े':'e','ै':'ai','ो':'o','ौ':'au','्':'',
  };
  return text.split('').map(c => map[c] ?? c).join('');
}

// Telugu basic transliteration
function transliterateTelugu(text: string): string {
  const map: Record<string, string> = {
    'అ':'a','ఆ':'aa','ఇ':'i','ఈ':'ee','ఉ':'u','ఊ':'oo','ఎ':'e','ఏ':'ee',
    'ఐ':'ai','ఒ':'o','ఓ':'oo','ఔ':'au','క':'ka','ఖ':'kha','గ':'ga',
    'ఘ':'gha','చ':'cha','జ':'ja','ట':'ta','డ':'da','త':'tha','థ':'tha',
    'ద':'da','ధ':'dha','న':'na','ప':'pa','ఫ':'pha','బ':'ba','భ':'bha',
    'మ':'ma','య':'ya','ర':'ra','ల':'la','వ':'va','శ':'sha','ష':'sha',
    'స':'sa','హ':'ha','ళ':'la','ా':'a','ి':'i','ీ':'ee','ు':'u',
    'ూ':'oo','ె':'e','ే':'ee','ై':'ai','ొ':'o','ో':'oo','ౌ':'au','్':'',
  };
  return text.split('').map(c => map[c] ?? c).join('');
}

// Arabic basic transliteration
function transliterateArabic(text: string): string {
  const map: Record<string, string> = {
    'ا':'a','ب':'b','ت':'t','ث':'th','ج':'j','ح':'h','خ':'kh','د':'d',
    'ذ':'dh','ر':'r','ز':'z','س':'s','ش':'sh','ص':'s','ض':'d','ط':'t',
    'ظ':'z','ع':'a','غ':'gh','ف':'f','ق':'q','ك':'k','ل':'l','م':'m',
    'ن':'n','ه':'h','و':'w','ي':'y','ة':'a','ى':'a','أ':'a','إ':'i','آ':'aa',
  };
  return text.split('').map(c => map[c] ?? c).join('');
}

export function getRomanization(text: string, langCode: string): string | null {
  if (!text || !NON_LATIN_LANGS.has(langCode)) return null;
  // Only romanize if text has non-ASCII characters
  if (!/[^\x00-\x7F]/.test(text)) return null;

  let result = '';
  try {
    switch (langCode) {
      case 'ru': result = transliterateWithMap(text, MAPS.ru); break;
      case 'uk': result = transliterateWithMap(text, MAPS.uk); break;
      case 'el': result = transliterateWithMap(text, MAPS.el); break;
      case 'hi': case 'mr': result = transliterateDevanagari(text); break;
      case 'te': result = transliterateTelugu(text); break;
      case 'ar': case 'fa': case 'ur': result = transliterateArabic(text); break;
      default: return null;
    }
    // Clean up repeated spaces and non-useful chars
    result = result.replace(/\s+/g, ' ').trim();
    return result.length > 2 ? result : null;
  } catch {
    return null;
  }
}
