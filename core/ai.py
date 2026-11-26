import json

import streamlit as st

SYSTEM = (
    "Kamu adalah perancang pembelajaran SMP berpengalaman di Indonesia yang menguasai Kurikulum Merdeka "
    "dan pendekatan Pembelajaran Mendalam (Deep Learning): prinsip berkesadaran (mindful), bermakna "
    "(meaningful), menggembirakan (joyful); pengalaman belajar memahami-mengaplikasi-merefleksi; dan "
    "8 dimensi Profil Lulusan. Tulis dalam Bahasa Indonesia baku. Keluaran HANYA JSON valid, tanpa markdown "
    "dan tanpa penjelasan. Jangan mengarang fakta, angka, tahun, pasal, kutipan, atau nama tokoh; "
    "jika ragu gunakan rumusan umum."
)


def available():
    try:
        return bool(st.secrets.get("ANTHROPIC_API_KEY"))
    except Exception:
        return False


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])


def model_name():
    try:
        return st.secrets.get("anthropic_model", "claude-sonnet-5-5")
    except Exception:
        return "claude-sonnet-5-5"


def call_json(user: str, max_tokens: int = 8000, system: str = SYSTEM):
    client = _client()
    last = None
    for _ in range(2):
        r = client.messages.create(model=model_name(), max_tokens=max_tokens, system=system,
                                   messages=[{"role": "user", "content": user}])
        txt = "".join(b.text for b in r.content if b.type == "text")
        a, b = txt.find("{"), txt.rfind("}")
        if a == -1 or b == -1:
            a, b = txt.find("["), txt.rfind("]")
        try:
            return json.loads(txt[a:b + 1])
        except Exception as e:  # noqa
            last = e
            user += "\n\nCATATAN: keluaran sebelumnya bukan JSON valid / terpotong. Kirim ulang HANYA JSON valid dan ringkas."
    raise ValueError(f"AI tidak mengembalikan JSON valid: {last}")
