from datetime import date, timedelta

import pandas as pd
import streamlit as st

from . import ai
from .config import BULAN, KELAS, tingkat
from .docx_out import build_prosem, build_prota


def build_weeks(start, end):
    d = start - timedelta(days=start.weekday())
    weeks = []
    while d <= end:
        mid = d + timedelta(days=3)
        weeks.append({"mon": d, "bulan": mid.month, "tahun": mid.year})
        d += timedelta(days=7)
    cnt = {}
    for w in weeks:
        key = (w["tahun"], w["bulan"])
        cnt[key] = cnt.get(key, 0) + 1
        w["ke"] = cnt[key]
        w["label"] = f"Mgg {w['ke']} {BULAN[w['bulan']][:3]} ({w['mon']:%d/%m})"
    return weeks


def alokasi(df, weeks, jp_minggu):
    """Isi JP berurutan ke minggu efektif. Mengembalikan (rows, sisa_kapasitas, kekurangan)."""
    eff = [i for i, w in enumerate(weeks) if w["efektif"]]
    cap = {i: jp_minggu for i in eff}
    pos, rows, kurang = 0, [], 0
    for _, r in df.iterrows():
        sisa, alloc = int(r["JP"]), {}
        while sisa > 0 and pos < len(eff):
            i = eff[pos]
            ambil = min(sisa, cap[i])
            if ambil > 0:
                alloc[i] = alloc.get(i, 0) + ambil
                cap[i] -= ambil; sisa -= ambil
            if cap[i] == 0:
                pos += 1
        kurang += sisa
        rows.append((str(r["Materi"]), int(r["JP"]), alloc))
    return rows, sum(cap.values()), kurang


def page_prota(store, cfg):
    st.header("Prota & Prosem")
    idn = store.identity()
    c1, c2, c3 = st.columns(3)
    tk = c1.selectbox("Tingkat", ["7", "8", "9"], help="7A dan 7B memakai prota/prosem yang sama.")
    jp_minggu = c2.number_input("JP per minggu", 1, 10, cfg["jp"], help="Sesuaikan dengan jam mengajar di sekolah Anda.")
    sem = c3.selectbox("Semester (untuk prosem)", ["Genap", "Ganjil"], index=0 if idn.get("semester", "Genap") == "Genap" else 1)

    saved = store.read("prota")
    saved = saved[saved["Tingkat"] == tk]
    base = pd.DataFrame({"Semester": saved["Semester"], "Materi": saved["Materi"], "TP": saved["TP"],
                         "JP": pd.to_numeric(saved["JP"], errors="coerce")})
    if base.empty:
        base = pd.DataFrame({"Semester": ["Genap"], "Materi": [""], "TP": [""], "JP": [0]})

    st.subheader(f"1 · Daftar bab/materi & alokasi JP — kelas {tk}")
    if ai.available() and st.button("✨ Usulkan struktur bab (AI)"):
        with st.spinner("Menyusun usulan…"):
            try:
                r = ai.call_json(
                    f"Mapel {cfg['nama']} SMP kelas {tk} Kurikulum Merdeka (Fase D), {jp_minggu} JP/minggu. "
                    "Usulkan daftar bab per semester beserta tujuan pembelajaran ringkas dan alokasi JP yang realistis "
                    "(sekitar 30 minggu efektif per tahun). Ini hanya DRAFT; urutan/nama bab harus disesuaikan dengan buku yang dipakai. "
                    'JSON: {"bab":[{"semester":"Ganjil|Genap","materi":"...","tp":"ringkas","jp":angka}]}')
                base = pd.DataFrame([{"Semester": b["semester"], "Materi": b["materi"], "TP": b["tp"], "JP": b["jp"]}
                                     for b in r["bab"]])
                st.session_state[f"prota_{tk}"] = base
            except Exception as e:  # noqa
                st.error(f"Gagal: {e}")
    base = st.session_state.get(f"prota_{tk}", base)
    ed = st.data_editor(base, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_prota_{tk}_{len(base)}",
                        column_config={"Semester": st.column_config.SelectboxColumn(options=["Ganjil", "Genap"], required=True),
                                       "Materi": st.column_config.TextColumn("Bab / Materi", width="medium"),
                                       "TP": st.column_config.TextColumn("Tujuan Pembelajaran", width="large"),
                                       "JP": st.column_config.NumberColumn("JP", min_value=0, step=1)})
    ed = ed[ed["Materi"].fillna("").str.strip() != ""].copy()
    ed["JP"] = pd.to_numeric(ed["JP"], errors="coerce").fillna(0).astype(int)
    ed["TP"] = ed["TP"].fillna("")
    st.caption("Tips: tambahkan baris 'Penilaian Tengah Semester' dan 'Penilaian Akhir Semester' agar JP-nya ikut terhitung di prosem.")
    c1, c2 = st.columns(2)
    if c1.button("💾 Simpan daftar materi", type="primary"):
        out = ed.reset_index(drop=True).assign(Tingkat=tk, No=lambda x: range(1, len(x) + 1))
        store.replace_block("prota", {"Tingkat": tk}, out)
        st.success("Tersimpan.")
    if len(ed):
        c2.download_button("⬇️ Unduh PROTA (.docx)", build_prota(idn, cfg["nama"], tk, ed),
                           f"PROTA_{cfg['singkat']}_Kelas{tk}.docx",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.subheader(f"2 · Prosem semester {sem}")
    th = idn.get("tahun_ajaran", "2026/2027")
    try:
        y = int(th.split("/")[1] if sem == "Genap" else th.split("/")[0])
    except Exception:
        y = date.today().year
    d1, d2 = st.columns(2)
    mulai = d1.date_input("Hari pertama masuk semester", date(y, 1, 4) if sem == "Genap" else date(y, 7, 13), key=f"mulai_{sem}")
    akhir = d2.date_input("Hari terakhir semester", date(y, 6, 20) if sem == "Genap" else date(y, 12, 19), key=f"akhir_{sem}")
    if akhir <= mulai:
        st.warning("Tanggal akhir harus setelah tanggal mulai."); return
    weeks = build_weeks(mulai, akhir)
    libur = st.multiselect("Minggu TIDAK efektif (libur Ramadan/Idulfitri, ujian sekolah, kegiatan sekolah, dll.)",
                           [w["label"] for w in weeks],
                           help="Sesuaikan dengan kalender pendidikan sekolah/dinas — app tidak mengisinya otomatis.")
    for w in weeks: w["efektif"] = w["label"] not in libur
    sub = ed[ed["Semester"] == sem]
    if sub.empty:
        st.info(f"Belum ada materi untuk semester {sem}."); return
    rows, sisa, kurang = alokasi(sub, weeks, int(jp_minggu))
    n_eff = sum(w["efektif"] for w in weeks)
    st.write(f"Minggu efektif: **{n_eff}** · kapasitas **{n_eff * jp_minggu} JP** · terpakai **{int(sub['JP'].sum())} JP** · sisa **{sisa} JP**")
    if kurang:
        st.error(f"Kekurangan {kurang} JP: materi melebihi minggu efektif. Kurangi JP atau cek kembali minggu libur.")
    mat = pd.DataFrame({"Materi": [r[0] for r in rows], "JP": [r[1] for r in rows]})
    for i, w in enumerate(weeks):
        mat[w["label"]] = [r[2].get(i, "") if w["efektif"] else "✕" for r in rows]
    st.dataframe(mat, hide_index=True, width="stretch")
    st.download_button("⬇️ Unduh PROSEM (.docx)", build_prosem(idn, cfg["nama"], tk, sem, weeks, rows),
                       f"PROSEM_{cfg['singkat']}_Kelas{tk}_{sem}.docx",
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
