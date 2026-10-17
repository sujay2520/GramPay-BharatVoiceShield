/**
 * GramPay / BharatVoice Shield: Multilingual Configuration & Rural Word Banks
 * Senior Citizen Accessibility (Age 70+) & Regional Language Suite
 * 
 * Provides pure-script localized UI strings, prompts, rural word banks, and senior helpers for:
 * - Kannada ('kn'): Pure Noto Sans Kannada script (U+0C80 - U+0CFF)
 * - Hindi ('hi'): Pure Devanagari script (U+0900 - U+097F)
 * - English ('en'): Plain, respectful English for seniors
 * 
 * Guarantees & Senior Accessibility (Age 70+):
 * 1. 100% Pure native Unicode scripts without encoding corruption or mixed Latin characters.
 * 2. Warm, simple, rural phrasing easily understood by elderly grandparents and farmers:
 *    - Strictly avoids technical jargon: 'Biometrics', 'Aletheia', 'Acoustic waveform', 'AI', 'API', 'Vocoder'.
 *    - Emphasizes warm, comforting, and direct terminology:
 *      * 'ನಿಮ್ಮ ಧ್ವನಿ' (Your Voice) / 'आपकी आवाज़' / 'Your Voice'
 *      * 'ಸುರಕ್ಷತೆ' (Safety) / 'सुरक्षा' / 'Safety'
 *      * 'ನಕಲಿ ಕರೆ' (Fake Call) / 'नकली कॉल' / 'Fake Call'
 *      * 'ಖಾತೆ ಸುರಕ್ಷಿತ' (Account Safe) / 'खाता सुरक्षित' / 'Account Safe'
 * 3. Complete security reason maps for pre-gate biometrics & challenge verdicts.
 * 4. Helper functions:
 *    - getSeniorPrompt(lang, [promptType])
 *    - getSeniorResult(lang, decision)
 *    - getReasonText(lang, reasonKey)
 *    - getWordBank(lang)
 *    - normalizeLangCode(lang)
 */

const SENIOR_STRINGS = {
  // Kannada (Noto Sans Kannada)
  kn: {
    voice_label: "ನಿಮ್ಮ ಧ್ವನಿ",
    safety_label: "ಸುರಕ್ಷತೆ",
    fake_call: "ನಕಲಿ ಕರೆ",
    fake_voice: "ನಕಲಿ ಧ್ವನಿ",
    account_safe: "ಖಾತೆ ಸುರಕ್ಷಿತ",
    money_safe: "ನಿಮ್ಮ ಹಣ ಸುರಕ್ಷಿತ",
    speak_prompt: "ಹಣ ಕಳುಹಿಸಲು ಬಟನ್ ಒತ್ತಿ ನಿಮ್ಮ ಧ್ವನಿಯಲ್ಲಿ ಮಾತನಾಡಿ. ನಿಮ್ಮ ಖಾತೆ ಸಂಪೂರ್ಣ ಸುರಕ್ಷಿತ.",
    enroll_prompt: "ಖಾತೆಯ ಸುರಕ್ಷತೆಗಾಗಿ ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ದಾಖಲಿಸಿ: 'ನನ್ನ ಧ್ವನಿ ನನ್ನ ಸುರಕ್ಷತೆ, ನನ್ನ ಖಾತೆ ಸುರಕ್ಷಿತ' ಎಂದು ಹೇಳಿ.",
    challenge_prompt: "ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ, ದಯವಿಟ್ಟು ಕೆಳಗೆ ಕಾಣುವ ನಾಲ್ಕು ಸರಳ ಪದಗಳನ್ನು ನಿಮ್ಮ ಧ್ವನಿಯಲ್ಲಿ ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ.",
    checking_prompt: "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ, ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ...",
    results: {
      approved: "ನಿಮ್ಮ ಧ್ವನಿ ದೃಢಪಟ್ಟಿದೆ. ನಿಮ್ಮ ಖಾತೆ ಸುರಕ್ಷಿತವಾಗಿದೆ ಮತ್ತು ₹1,000 ಪಾವತಿಗೆ ಅನುಮೋದನೆ ನೀಡಲಾಗಿದೆ.",
      synthetic_blocked: "ಎಚ್ಚರಿಕೆ! ನಕಲಿ ಕರೆ ಅಥವಾ ನಕಲಿ ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ. ನಿಮ್ಮ ಖಾತೆಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿಡಲು ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      speaker_mismatch: "ಈ ಧ್ವನಿ ನಿಮ್ಮ ಧ್ವನಿಗೆ ಹೊಂದಿಕೆಯಾಗುತ್ತಿಲ್ಲ. ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ.",
      uncertain_challenge: "ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ದಯವಿಟ್ಟು ಕೆಳಗಿನ 4 ಸರಳ ಪದಗಳನ್ನು ಹೇಳಿ.",
      challenge_failed: "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಂಡಿಲ್ಲ. ನಿಮ್ಮ ಖಾತೆಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿಡಲು ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      api_error: "ಸಂಪರ್ಕದಲ್ಲಿ ತೊಂದರೆಯಾಗಿದೆ. ನಿಮ್ಮ ಹಣ ಮತ್ತು ಖಾತೆ ಸಂಪೂರ್ಣ ಸುರಕ್ಷಿತವಾಗಿದೆ. ದಯವಿಟ್ಟು ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ."
    }
  },

  // Hindi (Devanagari)
  hi: {
    voice_label: "आपकी आवाज़",
    safety_label: "सुरक्षा",
    fake_call: "नकली कॉल",
    fake_voice: "नकली आवाज़",
    account_safe: "खाता सुरक्षित",
    money_safe: "आपके पैसे सुरक्षित",
    speak_prompt: "पैसे भेजने के लिए बटन दबाकर अपनी आवाज़ में बोलें। आपका खाता पूरी तरह सुरक्षित है।",
    enroll_prompt: "खाते की सुरक्षा के लिए अपनी आवाज़ जोड़ें: 'मेरी आवाज़ मेरी सुरक्षा है, मेरा खाता सुरक्षित रहे' साफ़ बोलें।",
    challenge_prompt: "अतिरिक्त सुरक्षा के लिए, कृपया नीचे दिए गए चार आसान शब्द अपनी आवाज़ में साफ़ बोलें।",
    checking_prompt: "आपकी आवाज़ की जाँच हो रही है, कृपया थोड़ा इंतज़ार करें...",
    results: {
      approved: "आपकी आवाज़ पहचान ली गई है। आपका खाता सुरक्षित है और ₹1,000 का भुगतान स्वीकृत है।",
      synthetic_blocked: "सावधान! नकली कॉल या नकली आवाज़ पकड़ी गई है। आपका खाता सुरक्षित रखने के लिए भुगतान रोक दिया गया है।",
      speaker_mismatch: "यह आवाज़ आपकी आवाज़ से मेल नहीं खा रही है। आपकी सुरक्षा के लिए अतिरिक्त जाँच ज़रूरी है।",
      uncertain_challenge: "आवाज़ साफ़ सुनाई नहीं दी। आपकी सुरक्षा के लिए कृपया नीचे दिए गए 4 आसान शब्द बोलें।",
      challenge_failed: "सुरक्षा जाँच पूरी नहीं हुई। आपका खाता सुरक्षित रखने के लिए भुगतान रोक दिया गया है।",
      api_error: "तकनीकी समस्या आई है। आपका खाता और पैसे पूरी तरह सुरक्षित हैं। कृपया थोड़ी देर बाद फिर से प्रयास करें।"
    }
  },

  // English (Latin)
  en: {
    voice_label: "Your Voice",
    safety_label: "Safety",
    fake_call: "Fake Call",
    fake_voice: "Fake Voice",
    account_safe: "Account Safe",
    money_safe: "Your Money is Safe",
    speak_prompt: "Tap the button and speak in your natural voice to send money. Your account is completely safe.",
    enroll_prompt: "For account safety, record your voice: clearly say 'My voice is my safety, keep my account safe'.",
    challenge_prompt: "For your safety, please clearly repeat the four simple words shown below in your natural voice.",
    checking_prompt: "Checking your voice, please wait a moment...",
    results: {
      approved: "Your voice is verified. Your account is safe, and payment of ₹1,000 is approved.",
      synthetic_blocked: "Warning: Fake call or fake voice detected! To keep your account safe, this payment has been stopped.",
      speaker_mismatch: "This voice does not match your registered voice. For your safety, additional verification is required.",
      uncertain_challenge: "Voice was not clearly heard. For your safety, please repeat the 4 simple words below.",
      challenge_failed: "Voice verification could not be completed. Your account remains safe and payment is stopped.",
      api_error: "Connection problem encountered. Your money and account are completely safe. Please try again shortly."
    }
  }
};

const LANGUAGES = {
  // Kannada (Noto Sans Kannada)
  kn: {
    label: "ಕನ್ನಡ",
    enroll_prompt: "ಖಾತೆಯ ಸುರಕ್ಷತೆಗಾಗಿ ನನ್ನ ಧ್ವನಿಯನ್ನು ನೋಂದಾಯಿಸುತ್ತಿದ್ದೇನೆ",
    speak_cta: "ಮಾತನಾಡಲು ಬಟನ್ ಒತ್ತಿ ನಿಮ್ಮ ಧ್ವನಿಯಲ್ಲಿ ಹೇಳಿ (ಉದಾ: ಗೊಬ್ಬರಕ್ಕೆ 1000 ರೂಪಾಯಿ ಕಳುಹಿಸಿ)",
    checking: "ನಿಮ್ಮ ಧ್ವನಿಯನ್ನು ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ...",
    challenge_title: "ಹೆಚ್ಚುವರಿ ಸುರಕ್ಷತೆ: ದಯವಿಟ್ಟು ಈ 4 ಸರಳ ಪದಗಳನ್ನು ನಿಮ್ಮ ಧ್ವನಿಯಲ್ಲಿ ಸ್ಪಷ್ಟವಾಗಿ ಹೇಳಿ",
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
      approved: "ನಿಮ್ಮ ಧ್ವನಿ ದೃಢಪಟ್ಟಿದೆ. ನಿಮ್ಮ ಖಾತೆ ಸುರಕ್ಷಿತವಾಗಿದೆ ಮತ್ತು ₹1,000 ಪಾವತಿಗೆ ಅನುಮೋದನೆ ನೀಡಲಾಗಿದೆ.",
      synthetic_blocked: "ಎಚ್ಚರಿಕೆ: ನಕಲಿ ಕರೆ ಅಥವಾ ನಕಲಿ ಧ್ವನಿ ಪತ್ತೆಯಾಗಿದೆ! ನಿಮ್ಮ ಖಾತೆಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿಡಲು ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      speaker_mismatch: "ಧ್ವನಿ ಹೊಂದಾಣಿಕೆಯಾಗಿಲ್ಲ. ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ಹೆಚ್ಚುವರಿ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ.",
      uncertain_challenge: "ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ದಯವಿಟ್ಟು ಕೆಳಗಿನ 4 ಸರಳ ಪದಗಳನ್ನು ಹೇಳಿ.",
      challenge_failed: "ಧ್ವನಿ ಪರಿಶೀಲನೆ ಪೂರ್ಣಗೊಂಡಿಲ್ಲ. ನಿಮ್ಮ ಖಾತೆಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿಡಲು ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ.",
      api_error: "ಸಂಪರ್ಕದಲ್ಲಿ ತೊಂದರೆಯಾಗಿದೆ. ನಿಮ್ಮ ಸುರಕ್ಷತೆಗಾಗಿ ಪಾವತಿಯನ್ನು ತಡೆಯಲಾಗಿದೆ, ನಿಮ್ಮ ಹಣ ಸುರಕ್ಷಿತವಾಗಿದೆ."
    },
    senior: SENIOR_STRINGS.kn
  },

  // Hindi (Devanagari)
  hi: {
    label: "हिन्दी",
    enroll_prompt: "खाते की सुरक्षा के लिए अपनी आवाज़ दर्ज कर रहा हूँ",
    speak_cta: "बोलने के लिए बटन दबाएँ और अपनी आवाज़ में बोलें (उदा: खाद के लिए 1000 रुपये भेजें)",
    checking: "आपकी आवाज़ की जाँच हो रही है...",
    challenge_title: "अतिरिक्त सुरक्षा जाँच: कृपया ये 4 आसान शब्द अपनी आवाज़ में साफ़ बोलें",
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
      approved: "आपकी आवाज़ पहचान ली गई है। आपका खाता सुरक्षित है और ₹1,000 का भुगतान स्वीकृत है।",
      synthetic_blocked: "सावधान: नकली कॉल या नकली आवाज़ पकड़ी गई है! आपके खाते की सुरक्षा के लिए भुगतान रोक दिया गया है।",
      speaker_mismatch: "आवाज़ मेल नहीं खाई। आपके खाते की सुरक्षा के लिए अतिरिक्त जाँच आवश्यक है।",
      uncertain_challenge: "आवाज़ साफ़ सुनाई नहीं दी। आपकी सुरक्षा के लिए कृपया नीचे दिए गए 4 आसान शब्द बोलें।",
      challenge_failed: "सुरक्षा जाँच पूरी नहीं हुई। आपके खाते को सुरक्षित रखने के लिए भुगतान रोक दिया गया है।",
      api_error: "तकनीकी समस्या आई है। आपकी सुरक्षा के लिए भुगतान रोक दिया गया है, आपके पैसे सुरक्षित हैं।"
    },
    senior: SENIOR_STRINGS.hi
  },

  // English (Latin)
  en: {
    label: "English",
    enroll_prompt: "I am recording my voice to keep my account safe",
    speak_cta: "Tap the button and speak in your voice (e.g., Send Rs. 1,000 for fertilizer)",
    checking: "Checking your voice...",
    challenge_title: "Extra safety check: Please say these 4 simple words in your voice clearly",
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
      approved: "Your voice is verified. Your account is safe and payment of ₹1,000 is approved.",
      synthetic_blocked: "Warning: Fake call or fake voice detected! To keep your account safe, payment has been stopped.",
      speaker_mismatch: "Voice does not match. For your account safety, extra verification is required.",
      uncertain_challenge: "Voice was not clearly heard. For your safety, please repeat the 4 simple words below.",
      challenge_failed: "Verification could not be completed. Your account is safe and payment has been stopped.",
      api_error: "Connection problem. To keep your account safe, payment was stopped. Your money is safe."
    },
    senior: SENIOR_STRINGS.en
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
 * Returns a warm, simple, senior-accessible prompt instruction (Age 70+)
 * in the requested language (Kannada, Hindi, or English).
 * 
 * Free of tech jargon (no 'biometrics', 'acoustic', 'waveform', 'AI').
 * Uses warm rural phrasing focusing on 'Your Voice' and 'Account Safety'.
 * 
 * @param {string} [lang='en'] - 'kn' | 'hi' | 'en' (or language name)
 * @param {string} [promptType='speak'] - 'speak' | 'enroll' | 'challenge' | 'checking'
 * @returns {string} - Warm, elderly-friendly instruction
 */
function getSeniorPrompt(lang, promptType = "speak") {
  const code = normalizeLangCode(lang);
  const data = SENIOR_STRINGS[code] || SENIOR_STRINGS.en;
  const key = String(promptType || "speak").toLowerCase();

  if (key.includes("enroll")) {
    return data.enroll_prompt;
  }
  if (key.includes("challenge") || key.includes("word") || key.includes("extra")) {
    return data.challenge_prompt;
  }
  if (key.includes("check") || key.includes("wait")) {
    return data.checking_prompt;
  }
  // Default to speak / pay prompt
  return data.speak_prompt;
}

/**
 * Returns a warm, reassuring, senior-accessible verdict message (Age 70+)
 * explaining the security decision in simple, comforting terms.
 * 
 * Explains whether the account is safe, if a fake call was blocked,
 * or if additional simple words are required, without scary jargon.
 * 
 * @param {string} [lang='en'] - 'kn' | 'hi' | 'en' (or language name)
 * @param {string|object} decision - Security verdict ('APPROVE', 'BLOCK', 'CHALLENGE', 'synthetic_blocked', etc.)
 * @returns {string} - Clear, reassuring message for senior citizens
 */
function getSeniorResult(lang, decision) {
  const code = normalizeLangCode(lang);
  const data = SENIOR_STRINGS[code] || SENIOR_STRINGS.en;

  let key = "";
  if (decision && typeof decision === "object") {
    key = String(decision.reason_key || decision.decision || decision.verdict || decision.status || "").toLowerCase();
  } else {
    key = String(decision || "").toLowerCase();
  }

  // 1. Approved / Allow / Pay / Pass / Verified
  if (
    key.includes("approve") ||
    key.includes("allow") ||
    key.includes("pay") ||
    key.includes("pass") ||
    key.includes("verified") ||
    key === "ok"
  ) {
    return data.results.approved;
  }

  // 2. Fake call / Synthetic AI clone blocked
  if (
    key.includes("synthetic") ||
    key.includes("clone") ||
    key.includes("fake") ||
    key.includes("fraud") ||
    key === "block" ||
    key.includes("blocked")
  ) {
    return data.results.synthetic_blocked;
  }

  // 3. Speaker mismatch
  if (
    key.includes("mismatch") ||
    key.includes("unknown") ||
    key.includes("wrong_speaker")
  ) {
    return data.results.speaker_mismatch;
  }

  // 4. Extra challenge / Uncertain audio
  if (
    key.includes("extra_check") ||
    (key.includes("challenge") && !key.includes("fail")) ||
    key.includes("uncertain")
  ) {
    return data.results.uncertain_challenge;
  }

  // 5. Challenge verification failed
  if (
    key.includes("fail") ||
    key.includes("challenge_failed")
  ) {
    return data.results.challenge_failed;
  }

  // 6. Network error / Timeout / API error
  if (
    key.includes("error") ||
    key.includes("unavailable") ||
    key.includes("timeout") ||
    key.includes("fail_closed")
  ) {
    return data.results.api_error;
  }

  // Fallback to checking reasonText or general safe message
  const fallback = getReasonText(code, key);
  if (fallback && fallback !== key) {
    return fallback;
  }
  return data.account_safe + ": " + data.results.api_error;
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

// Global browser window bindings
if (typeof window !== "undefined") {
  window.LANGUAGES = LANGUAGES;
  window.SENIOR_STRINGS = SENIOR_STRINGS;
  window.getReasonText = getReasonText;
  window.getWordBank = getWordBank;
  window.getSeniorPrompt = getSeniorPrompt;
  window.getSeniorResult = getSeniorResult;
}

// CommonJS module exports
if (typeof module !== "undefined" && typeof module.exports !== "undefined") {
  module.exports = {
    LANGUAGES,
    SENIOR_STRINGS,
    getReasonText,
    getWordBank,
    getSeniorPrompt,
    getSeniorResult,
    normalizeLangCode
  };
}
