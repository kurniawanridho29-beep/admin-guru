from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from .config import KELAS, STATUS, STATUS_LABEL

SEED = "data/siswa_seed.csv"


# ------------------------------------------------------------------ Dashboard
def page_dashboard(store, cfg):
    st.title(f"{cfg['ikon']} Administrasi Guru — {cfg['nama']}")
    sis = store.read("siswa")
    if sis.empty:
        st.info("Data siswa belum ada. Buka **Pengaturan Kelas** lalu klik *Impor data awal*.")
        return
    cols = st.columns(len(KELAS) + 1)
    cols[0].metric("Total siswa", len(sis))
    for c, k in zip(cols[1:], KELAS):
        c.metric(f"Kelas {k}", int((sis["Kelas"] == k).sum()))

    pres = store.read("presensi")
    today = str(date.today())
    st.subheader("Presensi hari ini")
    rows = []
    for k in KELAS:
        p = pres[(pres["Kelas"] == k) & (pres["Tanggal"] == today)]
        rows.append({"Kelas": k, "Status": "✅ sudah diisi" if len(p) else "— belum",
                     **{STATUS_LABEL[s]: int((p["Status"] == s).sum()) for s in STATUS}})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    if len(pres):
        st.subheader("Kehadiran keseluruhan")
        tot = pres.groupby("Kelas")["Status"].apply(lambda s: round((s == "H").mean() * 100, 1))
        st.bar_chart(tot.rename("% hadir"))


# ------------------------------------------------------------------ Pengaturan
def page_pengaturan(store, cfg):
    st.header("Pengaturan")
    t1, t2 = st.tabs(["Identitas", "Data Siswa per Kelas"])

    with t1:
        idn = store.identity()
        with st.form("form_identitas"):
            c1, c2 = st.columns(2)
            v = {
                "nama": c1.text_input("Nama guru", idn.get("nama", "")),
                "nip": c2.text_input("NIP / NUPTK", idn.get("nip", "")),
                "sekolah": c1.text_input("Nama sekolah", idn.get("sekolah", "")),
                "kota": c2.text_input("Kota (untuk tanda tangan)", idn.get("kota", "")),
                "kepsek": c1.text_input("Nama kepala sekolah", idn.get("kepsek", "")),
                "nip_kepsek": c2.text_input("NIP kepala sekolah", idn.get("nip_kepsek", "")),
                "tahun_ajaran": c1.text_input("Tahun ajaran", idn.get("tahun_ajaran", "2026/2027")),
                "semester": c2.selectbox("Semester", ["Ganjil", "Genap"],
                                         index=1 if idn.get("semester", "Genap") == "Genap" else 0),
            }
            if st.form_submit_button("💾 Simpan identitas", type="primary"):
                store.save_identity(v)
                st.success("Identitas tersimpan.")
                st.rerun()

    with t2:
        kelas = st.selectbox("Kelas", KELAS, key="set_kelas")
        df = store.siswa(kelas)[["No", "Nama", "JK"]]
        df["No"] = pd.to_numeric(df["No"], errors="coerce")
        st.caption(f"Jumlah siswa kelas {kelas}: **{len(df)}**. Tambah baris di bagian bawah tabel; "
                   "hapus dengan memilih baris lalu tombol Delete.")
        edited = st.data_editor(
            df, num_rows="dynamic", hide_index=True, width="stretch", key=f"sis_{kelas}",
            column_config={"No": st.column_config.NumberColumn(disabled=True),
                           "JK": st.column_config.SelectboxColumn("JK", options=["L", "P"], required=True)})
        c1, c2 = st.columns(2)
        if c1.button("💾 Simpan data kelas", type="primary", key=f"sv_sis_{kelas}"):
            out = edited.dropna(subset=["Nama"]).copy()
            out = out[out["Nama"].astype(str).str.strip() != ""]
            out["Nama"] = out["Nama"].astype(str).str.strip()
            out["JK"] = out["JK"].fillna("L")
            out["No"] = range(1, len(out) + 1)
            out.insert(0, "Kelas", kelas)
            store.replace_block("siswa", {"Kelas": kelas}, out)
            st.success(f"Data kelas {kelas} tersimpan ({len(out)} siswa).")
            st.rerun()
        if c2.button("⬇️ Impor data awal (hanya kelas yang masih kosong)"):
            seed = pd.read_csv(SEED, dtype=str)
            have = set(store.read("siswa")["Kelas"])
            new = seed[~seed["Kelas"].isin(have)]
            if new.empty:
                st.warning("Semua kelas sudah berisi data, tidak ada yang diimpor.")
            else:
                store.write("siswa", pd.concat([store.read("siswa"), new], ignore_index=True))
                st.success(f"Diimpor: kelas {', '.join(new['Kelas'].unique())}.")
                st.rerun()


# ------------------------------------------------------------------ Presensi
def page_presensi(store, cfg):
    st.header("Presensi")
    t1, t2 = st.tabs(["Isi presensi", "Rekap"])

    with t1:
        c1, c2 = st.columns(2)
        kelas = c1.selectbox("Kelas", KELAS, key="pres_kelas")
        tgl = c2.date_input("Tanggal", value=date.today(), key="pres_tgl")
        roster = store.siswa(kelas)
        if roster.empty:
            st.warning("Belum ada siswa di kelas ini. Isi dulu di Pengaturan Kelas.")
        else:
            pres = store.read("presensi")
            ada = pres[(pres["Kelas"] == kelas) & (pres["Tanggal"] == str(tgl))].drop_duplicates("Nama")
            df = roster[["Nama"]].merge(ada[["Nama", "Status"]], on="Nama", how="left")
            df["Status"] = df["Status"].where(df["Status"].isin(STATUS), "H")
            st.caption("Sudah pernah disimpan untuk tanggal ini — data dimuat kembali." if len(ada)
                       else "Belum ada data tanggal ini. Semua diset **H**, ubah yang tidak hadir.")
            edited = st.data_editor(
                df, hide_index=True, width="stretch", disabled=["Nama"], key=f"pr_{kelas}_{tgl}",
                column_config={"Status": st.column_config.SelectboxColumn(
                    "Status (H/I/S/A)", options=STATUS, required=True)})
            cnt = edited["Status"].value_counts()
            st.write(" · ".join(f"**{STATUS_LABEL[s]}** {int(cnt.get(s, 0))}" for s in STATUS))
            if st.button("💾 Simpan presensi", type="primary"):
                out = edited.copy()
                out.insert(0, "Kelas", kelas)
                out.insert(0, "Tanggal", str(tgl))
                store.replace_block("presensi", {"Kelas": kelas, "Tanggal": str(tgl)}, out)
                st.success(f"Presensi kelas {kelas} tanggal {tgl} tersimpan.")

    with t2:
        kelas = st.selectbox("Kelas", KELAS, key="rek_kelas")
        pres = store.read("presensi")
        pres = pres[pres["Kelas"] == kelas]
        if pres.empty:
            st.info("Belum ada data presensi.")
        else:
            pv = pres.pivot_table(index="Nama", columns="Status", values="Tanggal",
                                  aggfunc="count", fill_value=0)
            pv = pv.reindex(columns=STATUS, fill_value=0)
            pv["% Hadir"] = (pv["H"] / pv.sum(axis=1) * 100).round(1)
            st.caption(f"Jumlah pertemuan tercatat: {pres['Tanggal'].nunique()}")
            st.dataframe(pv, width="stretch")
            st.download_button("⬇️ Unduh rekap (CSV)", pv.to_csv().encode(), f"rekap_presensi_{kelas}.csv")


# ------------------------------------------------------------------ Nilai
JENIS = {"Harian": "nilai_harian", "Ulangan": "nilai_ulangan", "Ujian": "nilai_ujian"}


def _kolom_kelas(store, sheet, kelas):
    m = store.read("meta_kolom")
    m = m[(m["Sheet"] == sheet) & (m["Kelas"] == kelas)].assign(_u=lambda x: pd.to_numeric(x["Urutan"]))
    return m.sort_values("_u")["Kolom"].tolist()


def _load_nilai(store, sheet, kelas):
    roster = store.siswa(kelas)[["Nama"]].drop_duplicates("Nama")
    cols = _kolom_kelas(store, sheet, kelas)
    saved = store.read(sheet)
    saved = saved[saved["Kelas"] == kelas].drop_duplicates("Nama")
    cols = [c for c in cols if c in saved.columns]
    df = roster.merge(saved[["Nama"] + cols], on="Nama", how="left") if cols else roster.copy()
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _nilai_tab(store, label, sheet, kelas):
    sk = f"nilai_{sheet}_{kelas}"
    if sk not in st.session_state:
        st.session_state[sk] = _load_nilai(store, sheet, kelas)
        st.session_state[sk + "_v"] = 0
    base = st.session_state[sk]
    ver = st.session_state[sk + "_v"]
    cols = [c for c in base.columns if c != "Nama"]
    if base.empty:
        st.warning("Belum ada siswa di kelas ini.")
        return
    edited = st.data_editor(
        base, hide_index=True, width="stretch", disabled=["Nama"], key=f"ed_{sk}_{ver}",
        column_config={c: st.column_config.NumberColumn(c, min_value=0, max_value=100, step=0.5) for c in cols})

    c1, c2, c3 = st.columns([2, 2, 2])
    nama_baru = c1.text_input("Nama kolom baru", key=f"nk_{sk}", placeholder=f"mis. {label} 1 – Bab 1")
    if c1.button("➕ Tambah kolom", key=f"ak_{sk}"):
        nb = nama_baru.strip()
        if not nb or nb in ("Nama", "Kelas") or nb in cols:
            st.warning("Nama kolom kosong atau sudah dipakai.")
        else:
            edited[nb] = np.nan
            st.session_state[sk] = edited
            st.session_state[sk + "_v"] = ver + 1
            st.rerun()
    hapus = c2.selectbox("Hapus kolom", ["—"] + cols, key=f"hk_{sk}")
    if c2.button("🗑️ Hapus", key=f"dk_{sk}") and hapus != "—":
        st.session_state[sk] = edited.drop(columns=hapus)
        st.session_state[sk + "_v"] = ver + 1
        st.rerun()
    if c3.button("↻ Muat ulang dari sheet", key=f"rl_{sk}"):
        store.reload(sheet); store.reload("meta_kolom")
        del st.session_state[sk]
        st.rerun()

    if len(cols):
        ra = edited[cols].apply(pd.to_numeric, errors="coerce").mean(axis=1).round(1)
        st.caption(f"Rata-rata kelas: **{ra.mean():.1f}**" if ra.notna().any() else "Belum ada nilai terisi.")

    if st.button(f"💾 Simpan nilai {label.lower()} kelas {kelas}", type="primary", key=f"sv_{sk}"):
        out = edited.copy()
        out.insert(0, "Kelas", kelas)
        store.replace_block(sheet, {"Kelas": kelas}, out)
        meta = pd.DataFrame({"Sheet": sheet, "Kelas": kelas, "Urutan": range(len(cols)), "Kolom": cols})
        store.replace_block("meta_kolom", {"Sheet": sheet, "Kelas": kelas}, meta)
        st.session_state[sk] = edited
        st.success("Tersimpan ke sheet.")


def page_nilai(store, cfg):
    st.header("Buku Nilai")
    kelas = st.selectbox("Kelas", KELAS, key="nilai_kelas")
    tabs = st.tabs(["Nilai Harian", "Nilai Ulangan", "Nilai Ujian", "Rekap Nilai Akhir"])
    for tab, (label, sheet) in zip(tabs[:3], JENIS.items()):
        with tab:
            _nilai_tab(store, label, sheet, kelas)
    with tabs[3]:
        st.caption("Rata-rata tiap jenis nilai dari data yang **sudah disimpan**, lalu dibobot.")
        c = st.columns(3)
        w = [c[0].number_input("Bobot Harian (%)", 0, 100, 40),
             c[1].number_input("Bobot Ulangan (%)", 0, 100, 30),
             c[2].number_input("Bobot Ujian (%)", 0, 100, 30)]
        if sum(w) != 100:
            st.warning(f"Total bobot {sum(w)}%, harus 100%.")
        rek = store.siswa(kelas)[["Nama"]].drop_duplicates("Nama").set_index("Nama")
        for (label, sheet), wi in zip(JENIS.items(), w):
            d = _load_nilai(store, sheet, kelas).set_index("Nama")
            rek[label] = d.apply(pd.to_numeric, errors="coerce").mean(axis=1) if len(d.columns) else np.nan
        rek["Nilai Akhir"] = sum(rek[l].fillna(0) * wi / 100 for l, wi in zip(JENIS, w))
        st.dataframe(rek.round(1), width="stretch")
        st.download_button("⬇️ Unduh rekap (CSV)", rek.round(1).to_csv().encode(), f"rekap_nilai_{kelas}.csv")
