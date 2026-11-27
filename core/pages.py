from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from .config import KELAS, STATUS, STATUS_LABEL

SEED = "data/siswa_seed.csv"


# ------------------------------------------------------------------ Dashboard
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
CSS = """<style>
.hero{background:linear-gradient(135deg,#1e3a8a,#2563eb 60%,#38bdf8);color:#fff;padding:22px 26px;border-radius:16px;margin-bottom:18px}
.hero h2{margin:0 0 4px 0;color:#fff;font-size:26px}.hero p{margin:0;opacity:.92;font-size:14px}
.card{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:14px 16px;background:rgba(128,128,128,.07);height:100%}
.card .n{font-size:30px;font-weight:700;line-height:1.15}.card .l{opacity:.75;font-size:13px}
.card .t{font-weight:700;font-size:16px;margin-bottom:4px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;margin:3px 4px 0 0;font-weight:600}
.ph{background:#16a34a2e;color:#22c55e}.pi{background:#2563eb2e;color:#60a5fa}
.ps{background:#d977062e;color:#fbbf24}.pa{background:#dc26262e;color:#f87171}
</style>"""


def _impor_awal(store):
    seed = pd.read_csv(SEED, dtype=str)
    have = set(store.read("siswa")["Kelas"])
    new = seed[~seed["Kelas"].isin(have)]
    if not new.empty:
        store.write("siswa", pd.concat([store.read("siswa"), new], ignore_index=True))
    return list(new["Kelas"].unique())


def _pindah(menu):
    st.session_state["menu"] = menu


def page_dashboard(store, cfg):
    from html import escape
    from .config import BULAN
    st.markdown(CSS, unsafe_allow_html=True)
    idn = store.identity()
    t = date.today()
    st.markdown(
        f'<div class="hero"><h2>Selamat datang, {escape(idn.get("nama", ""))} {cfg["ikon"]}</h2>'
        f'<p>{escape(cfg["nama"])} • {escape(idn.get("sekolah", ""))}<br>'
        f'{HARI[t.weekday()]}, {t.day} {BULAN[t.month]} {t.year} • TA {escape(idn.get("tahun_ajaran", ""))} '
        f'semester {escape(idn.get("semester", ""))}</p></div>', unsafe_allow_html=True)

    sis = store.read("siswa")
    if sis.empty:
        st.info("Data siswa belum dimuat. Klik tombol di bawah untuk memuat 93 siswa kelas 7A, 7B, 8, dan 9.")
        if st.button("⬇️ Muat data siswa awal", type="primary"):
            _impor_awal(store)
            st.rerun()
        return

    pres = store.read("presensi")
    today = str(t)
    terisi = sum(1 for k in KELAS if len(pres[(pres["Kelas"] == k) & (pres["Tanggal"] == today)]))
    persen = round((pres["Status"] == "H").mean() * 100, 1) if len(pres) else None

    def card(n, label):
        return f'<div class="card"><div class="n">{n}</div><div class="l">{label}</div></div>'

    c = st.columns(4)
    c[0].markdown(card(len(sis), "Total siswa"), unsafe_allow_html=True)
    c[1].markdown(card(len(KELAS), "Kelas diampu"), unsafe_allow_html=True)
    c[2].markdown(card(f"{terisi}/{len(KELAS)}", "Kelas sudah presensi hari ini"), unsafe_allow_html=True)
    c[3].markdown(card(f"{persen}%" if persen is not None else "—", "Rata-rata kehadiran"), unsafe_allow_html=True)

    st.markdown("#### Pintasan")
    b = st.columns(4)
    b[0].button("📝 Isi presensi", on_click=_pindah, args=("📝 Presensi",), width="stretch")
    b[1].button("📊 Input nilai", on_click=_pindah, args=("📊 Buku Nilai",), width="stretch")
    b[2].button("📘 Modul ajar", on_click=_pindah, args=("📘 Generate Modul Ajar",), width="stretch")
    b[3].button("🗓️ Prota & Prosem", on_click=_pindah, args=("🗓️ Prota & Prosem",), width="stretch")

    st.markdown("#### Presensi hari ini")
    cols = st.columns(len(KELAS))
    for col, k in zip(cols, KELAS):
        p = pres[(pres["Kelas"] == k) & (pres["Tanggal"] == today)]
        n = int((sis["Kelas"] == k).sum())
        if len(p):
            pills = "".join(f'<span class="pill p{s.lower()}">{s} {int((p["Status"] == s).sum())}</span>' for s in STATUS)
            stat = f"✅ sudah diisi<br>{pills}"
        else:
            stat = "⏳ belum diisi"
        col.markdown(f'<div class="card"><div class="t">Kelas {k}</div><div class="l">{n} siswa</div>'
                     f'<div style="margin-top:8px;font-size:13px">{stat}</div></div>', unsafe_allow_html=True)

    st.markdown("&nbsp;")
    left, right = st.columns(2)
    with left:
        st.markdown("#### Kehadiran per kelas (%)")
        if len(pres):
            tot = pres.groupby("Kelas")["Status"].apply(lambda s: round((s == "H").mean() * 100, 1))
            st.bar_chart(tot.rename("% hadir"))
        else:
            st.caption("Belum ada data presensi.")
    with right:
        st.markdown("#### Siswa dengan alpha terbanyak")
        al = pres[pres["Status"] == "A"].groupby(["Kelas", "Nama"]).size().rename("Alpha").reset_index()
        if len(al):
            st.dataframe(al.sort_values("Alpha", ascending=False).head(5), hide_index=True, width="stretch")
        else:
            st.caption("Belum ada catatan alpha.")

    st.markdown("#### Kelengkapan buku nilai (jumlah kolom nilai)")
    meta = store.read("meta_kolom")
    rows = []
    for k in KELAS:
        r = {"Kelas": k}
        for lab, sh in (("Harian", "nilai_harian"), ("Ulangan", "nilai_ulangan"), ("Ujian", "nilai_ujian")):
            r[lab] = int(((meta["Sheet"] == sh) & (meta["Kelas"] == k)).sum())
        rows.append(r)
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


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
