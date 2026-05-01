import json
import locale
from pathlib import Path

LOCALE_DIR = Path(__file__).parent.parent / "locale"
import sys

# Detectar si estamos en PyInstaller para resolver rutas correctamente
if getattr(sys, 'frozen', False):
    # Si estamos compilados con PyInstaller, resolver desde el ejecutable
    LOCALE_DIR = Path(sys.executable).parent / "locale"
else:
    # En desarrollo, es relativo al módulo
    LOCALE_DIR = Path(__file__).parent.parent / "locale"
SUPPORTED = {
    "es": "es",
    "en": "en",
    "zh": "zh",
    "ja": "ja",
    "de": "de",
}

class Translator:
    def __init__(self, lang=None):
        self.lang = self._detect_language(lang)
        self.translations = self._load_translations(self.lang)

    def _detect_language(self, lang=None):
        if lang and lang in SUPPORTED:
            return SUPPORTED[lang]
        sys_lang = locale.getdefaultlocale()[0] or "en"
        code = sys_lang.split("_")[0].lower()
        return SUPPORTED.get(code, "en")

    def _load_translations(self, lang):
        path = LOCALE_DIR / f"{lang}.json"
        if not path.exists():
            path = LOCALE_DIR / "en.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def t(self, key, **kwargs):
        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

translator = Translator()

def set_language(lang):
    global translator
    translator = Translator(lang)


def t(key, **kwargs):
    return translator.t(key, **kwargs)
