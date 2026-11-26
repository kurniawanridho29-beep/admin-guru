import streamlit as st

from .config import SUBJECTS
from .modul import page_modul
from .pages import page_dashboard, page_nilai, page_pengaturan, page_presensi
from .prota import page_prota
from .storage import get_store

MENU = {
    "🏠 Dashboard": page_dashboard,
    "⚙️ Pengaturan Kelas": page_pengaturan,
    "📝 Presensi": page_presensi,
    "📊 Buku Nilai": page_nilai,
    "📘 Generate Modul Ajar": page_modul,
    "🗓️ Prota & Prosem": page_prota,
}


def run(subject: str):
    cfg = SUBJECTS[subject]
    st.set_page_config(page_title=f"Admin Guru {cfg['singkat']}", page_icon=cfg["ikon"], layout="wide")
    store = get_store(subject)
    idn = store.identity()
    with st.sidebar:
        st.markdown(f"## {cfg['ikon']} {cfg['singkat']}")
        st.markdown(f"**{idn.get('nama') or '(isi nama di Pengaturan)'}**")
        info = [("NIP", idn.get("nip")), ("Sekolah", idn.get("sekolah")),
                ("Mapel", cfg["nama"]), ("TA", f"{idn.get('tahun_ajaran', '')} • {idn.get('semester', '')}")]
        st.caption("  \n".join(f"{k}: {v}" for k, v in info if v))
        st.divider()
        menu = st.radio("Menu", list(MENU), label_visibility="collapsed")
        st.divider()
        st.caption("Penyimpanan: Google Sheets ✅" if store.mode == "sheets" else "Penyimpanan: lokal (sementara) ⚠️")
    if store.mode != "sheets":
        st.warning("Google Sheets belum terhubung — data hanya tersimpan sementara dan HILANG saat app restart. "
                   "Lengkapi Secrets (lihat README)." + (f"  Detail: {store.err}" if store.err else ""))
    MENU[menu](store, cfg)
