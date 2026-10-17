// NEEDS NATIVE REVIEW
/**
 * GramPay / BharatVoice Shield: Multilingual Configuration & Rural Word Banks
 * 
 * Provides pure-script localized UI strings, prompts, and rural word banks for:
 * - Kannada ('kn'): Noto Sans Kannada script
 * - Hindi ('hi'): Devanagari script
 * - English ('en'): Latin script
 * 
 * Guarantees:
 * - Pure Unicode scripts with zero mixed-character corruption.
 * - Everyday rural vocabulary for Indian agricultural and micro-payment contexts.
 * - Complete security reason maps for pre-gate biometrics & challenge verdicts.
 */

// NEEDS NATIVE REVIEW
const LANGUAGES = {
  // NEEDS NATIVE REVIEW (Kannada / Noto Sans Kannada)
  kn: {
    label: "ಕನ್ನಡ",
    enroll_prompt: "ನನ್ನ ಧ್ವನಿಯನ್ನು ಗ್ರಾಮಪೇ ಸುರಕ್ಷತೆಗಾಗಿ ನೋಂದಾಯಿಸುತ್ತಿದ್ದೇನೆ",
    speak_cta: "ಮಾತನಾಡಲು ಇಲ್ಲಿ ಒತ್ತಿರಿ (ಉದಾ: ಇಫ್ಕೊ ಗೊಬ್ಬರಕ್ಕೆ 1000 ರೂಪಾಯಿ ಕಳುಹಿಸಿ)",
    checking: "ಧ್ವನಿಯನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
    challenge_title: "ಹೆಚ್ಚುವರಿ ಧ್ವನಿ ಪರಿಶೀಲನೆ: ದಯವಿಟ್ಟು ಈ 4 ಪದಗಳನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ",
    word_bank: [
      "ಹಸಿರು",
      "ಮಳೆ",
      "ಕಮಲ",
      "ನವಿಲು",
      "ಸೂರ್ಯ",
      "ನದಿ",
      "ಬೆಟ್ಟ",
      "ಮಾವು",
      "ಭೂಮಿ",
      "ಬೆಳಕು",
      "ಹೂವು",
      "ಮರ"
    ],
    reasons: {
      approved: "ನೈಜ ಧ್ವನಿ ಮತ್ತು ಖಾತೆದಾರರ ಗುರುತು ದೃಢಪಟ್ಟಿದೆ. ₹1,000 ಪಾವತಿಗೆ ಅನುಮತಿ ನೀಡಲಾಗಿದೆ.",
      synthetic_blocked: "ಎಚ್ಚರಿಕೆ: ಕೃತಕ (ನಕಲಿ) ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ. ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      speaker_mismatch: "ಧ್ವನಿ ಹೊಂದಾಣಿಕೆಯಾಗಿಲ್ಲ. ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ.",
      uncertain_challenge: "ಧ್ವನಿ ಅಸ್ಪಷ್ಟವಾಗಿದೆ. ದಯವಿಟ್ಟು ಕೆಳಗಿನ 4 ಪದಗಳನ್ನು ಹೇಳಿ.",
      challenge_failed: "ಮರು-ಪರಿಶೀಲನೆ ವಿಫಲವಾಗಿದೆ. ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      api_error: "ತಾಂತ್ರಿಕ ದೋಷ: ಸುರಕ್ಷತೆಗಾಗಿ ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ."
    }
  },

  // NEEDS NATIVE REVIEW (Hindi / Devanagari)
  hi: {
    label: "हिन्दी",
    enroll_prompt: "मैं ग्रामपे सुरक्षा के लिए अपनी आवाज़ दर्ज कर रहा हूँ",
    speak_cta: "बोलने के लिए दबाएँ (उदा: इफको खाद को 1000 रुपये भेजें)",
    checking: "आवाज़ की जाँच हो रही है...",
    challenge_title: "अतिरिक्त सुरक्षा जाँच: कृपया ये 4 शब्द साफ़ बोलें",
    word_bank: [
      "हरा",
      "बादल",
      "कमल",
      "मोर",
      "सूरज",
      "नदी",
      "पहाड़",
      "आम",
      "धरती",
      "उजाला",
      "फूल",
      "पानी"
    ],
    reasons: {
      approved: "असली आवाज़ और पहचान प्रमाणित। ₹1,000 भुगतान स्वीकृत।",
      synthetic_blocked: "सावधान: कृत्रिम (नकली) आवाज़ पकड़ी गई। भुगतान रोक दिया गया है।",
      speaker_mismatch: "आवाज़ मेल नहीं खाई। अतिरिक्त जाँच आवश्यक है।",
      uncertain_challenge: "आवाज़ स्पष्ट नहीं है। कृपया नीचे दिए गए 4 शब्द बोलें।",
      challenge_failed: "सुरक्षा जाँच विफल। भुगतान रोक दिया गया है।",
      api_error: "तकनीकी त्रुटि: सुरक्षा के लिए भुगतान रोक दिया गया है।"
    }
  },

  // English (Latin)
  en: {
    label: "English",
    enroll_prompt: "I am enrolling my voice for GramPay security",
    speak_cta: "Tap and speak (e.g., Send Rs. 1,000 to IFFCO Fertilizer)",
    checking: "Checking voice...",
    challenge_title: "Extra security check: Please say these 4 words clearly",
    word_bank: [
      "green",
      "monsoon",
      "lotus",
      "peacock",
      "sunrise",
      "river",
      "mango",
      "mountain",
      "garden",
      "lantern",
      "forest",
      "harvest"
    ],
    reasons: {
      approved: "Real voice and enrolled speaker verified. Rs. 1,000 payment unlocked.",
      synthetic_blocked: "Blocked: Synthetic AI voice detected. Payment tool remains locked.",
      speaker_mismatch: "Speaker voiceprint mismatch. Extra verification required.",
      uncertain_challenge: "Uncertain audio score. Please repeat the 4 challenge words below.",
      challenge_failed: "Challenge verification failed. Payment tool remains locked.",
      api_error: "Verification unavailable (fail-closed). Payment tool remains locked."
    }
  }
};

/**
 * Normalizes language string input to 'kn', 'hi', or 'en'.
 * Defaults to 'en' when unrecognized.
 * 
 * @param {string} [lang] - Language code or name (e.g., 'kn', 'kn-IN', 'kannada', 'hi')
 * @returns {string} - 'kn' | 'hi' | 'en'
 */
function normalizeLangCode(lang) {
  if (!lang || typeof lang !== "string") return "en";
  const clean = lang.trim().toLowerCase();
  if (clean.startsWith("kn") || clean.includes("kannada")) return "kn";
  if (clean.startsWith("hi") || clean.includes("hindi")) return "hi";
  if (clean.startsWith("en") || clean.includes("english")) return "en";
  return clean;
}

/**
 * Returns localized reason string for a given language and reason key,
 * with graceful fallback to English and then to the raw reasonKey.
 * 
 * @param {string} lang - Language code ('kn', 'hi', 'en', etc.)
 * @param {string} reasonKey - Reason identifier ('approved', 'synthetic_blocked', etc.)
 * @returns {string} - Localized reason message
 */
function getReasonText(lang, reasonKey) {
  if (!reasonKey) return "";
  const code = normalizeLangCode(lang);

  // 1. Check requested language
  if (LANGUAGES[code] && LANGUAGES[code].reasons && LANGUAGES[code].reasons[reasonKey]) {
    return LANGUAGES[code].reasons[reasonKey];
  }

  // 2. Fallback to English
  if (LANGUAGES.en && LANGUAGES.en.reasons && LANGUAGES.en.reasons[reasonKey]) {
    return LANGUAGES.en.reasons[reasonKey];
  }

  // 3. Fallback to key itself
  return String(reasonKey);
}

/**
 * Returns the 12-word rural word bank for the specified language,
 * falling back to English if the language is unsupported.
 * 
 * @param {string} lang - Language code ('kn', 'hi', 'en')
 * @returns {string[]} - Array of 12 everyday rural words
 */
function getWordBank(lang) {
  const code = normalizeLangCode(lang);

  if (LANGUAGES[code] && Array.isArray(LANGUAGES[code].word_bank)) {
    return [...LANGUAGES[code].word_bank];
  }

  if (LANGUAGES.en && Array.isArray(LANGUAGES.en.word_bank)) {
    return [...LANGUAGES.en.word_bank];
  }

  return [];
}

// Global browser window fallback
if (typeof window !== "undefined") {
  window.LANGUAGES = LANGUAGES;
  window.getReasonText = getReasonText;
  window.getWordBank = getWordBank;
}

// CommonJS compatibility
if (typeof module !== "undefined" && typeof module.exports !== "undefined") {
  module.exports = {
    LANGUAGES,
    getReasonText,
    getWordBank
  };
}
