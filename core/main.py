from datetime import date
from html import escape

import streamlit as st

from .config import BULAN, KELAS, SUBJECTS
from .modul import page_modul
from .pages import CSS, page_dashboard, page_nilai, page_pengaturan, page_presensi
from .prota import page_prota
from .storage import get_store

TABS = [
    ("🏠 Ringkasan", page_dashboard),
    ("📝 Presensi", page_presensi),
    ("📊 Buku Nilai", page_nilai),
    ("📘 Generator Modul Ajar", page_modul),
    ("🗓️ Prota & Prosem", page_prota),
    ("⚙️ Data Siswa", page_pengaturan),
]
FIELDS = ("sekolah", "nama", "nip", "tahun_ajaran", "semester", "kota", "kepsek", "nip_kepsek")


def _simpan_identitas(store):
    d = store.identity()
    for k in FIELDS:
        v = st.session_state.get("idn_" + k)
        if v is not None:
            d[k] = v
    store.save_identity(d)


def run(subject: str):
    cfg = SUBJECTS[subject]
    st.set_page_config(page_title=f"Admin Guru {cfg['singkat']}", page_icon=cfg["ikon"], layout="wide")
    store = get_store(subject)
    if store.mode != "sheets":      # koneksi gagal tidak boleh tersimpan permanen: coba sambungkan lagi
        get_store.clear()
        store = get_store(subject)
    idn = store.identity()
    cb = dict(on_change=_simpan_identitas, args=(store,))

    with st.sidebar:
        st.markdown("### 🧑‍🏫 Identitas Pengajar")
        st.text_input("Nama Sekolah", idn.get("sekolah", ""), key="idn_sekolah", **cb)
        st.text_input("Nama Guru / Penyusun", idn.get("nama", ""), key="idn_nama", **cb)
        st.text_input("NIP / NUPTK", idn.get("nip", ""), key="idn_nip", **cb)
        c1, c2 = st.columns(2)
        c1.text_input("Tahun Ajaran", idn.get("tahun_ajaran", "2026/2027"), key="idn_tahun_ajaran", **cb)
        c2.selectbox("Semester", ["Ganjil", "Genap"], index=1 if idn.get("semester", "Genap") == "Genap" else 0,
                     key="idn_semester", **cb)
        with st.expander("Data tanda tangan dokumen"):
            st.text_input("Kota", idn.get("kota", ""), key="idn_kota", **cb)
            st.text_input("Nama kepala sekolah", idn.get("kepsek", ""), key="idn_kepsek", **cb)
            st.text_input("NIP kepala sekolah", idn.get("nip_kepsek", ""), key="idn_nip_kepsek", **cb)
        st.divider()
        st.markdown("### 🏫 Pengaturan Kelas, Mapel & Bulan")
        st.selectbox("Mata Pelajaran", [cfg["nama"]], disabled=True)
        st.selectbox("Pilih Kelas Aktif", KELAS, key="kelas_aktif", format_func=lambda k: f"Kelas {k}")
        st.selectbox("Pilih Bulan Presensi", ["Semua bulan"] + BULAN[1:], index=date.today().month, key="bulan_aktif")
        st.divider()
        st.caption("Penyimpanan: Google Sheets ✅ (tersimpan otomatis)" if store.mode == "sheets"
                   else "Penyimpanan: lokal (sementara) ⚠️")

    idn = store.identity()
    kelas = st.session_state.get("kelas_aktif", KELAS[0])
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="hero"><h2>🎓 Portal Administrasi & Pembelajaran Guru</h2>'
        f'<p>Selamat datang, <b>{escape(idn.get("nama", ""))}</b> | {escape(idn.get("sekolah", ""))} | '
        f'Mapel: <b>{escape(cfg["singkat"])}</b> | <b>Kelas {kelas}</b> '
        f'(TA {escape(idn.get("tahun_ajaran", ""))} - Semester {escape(idn.get("semester", ""))})</p></div>',
        unsafe_allow_html=True)
    if store.mode != "sheets":
        st.warning("Google Sheets belum terhubung — data hanya sementara dan HILANG saat app restart."
                   + (f"  Detail: {store.err}" if store.err else ""))

    for tab, (_, fn) in zip(st.tabs([t for t, _ in TABS]), TABS):
        with tab:
            fn(store, cfg)
