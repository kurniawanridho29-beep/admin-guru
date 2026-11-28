from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from .config import BULAN, HARI_ABBR, HARI_FULL, KELAS, N_NILAI, STATUS, STATUS_LABEL
from .domain import (NILAI_COLS, SKOR_DEFAULT, URUT, bulan_aktif, date_cols, hitung_nilai, hitung_status, jadwal,
                     kelas_aktif, norm_nilai, num, rekap_semester, rename_sheet_cols, skor_kehadiran, tab_nilai, tab_presensi, tahun_bulan,
                     tanggal_cols)

SEED = "data/siswa_seed.csv"
CSS = """<style>
.hero{background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:24px 28px;border-radius:14px;margin-bottom:14px}
.hero h2{margin:0 0 4px 0;color:#fff;font-size:26px}.hero p{margin:0;opacity:.95;font-size:15px}
.card{border:1px solid rgba(128,128,128,.28);border-radius:14px;padding:14px 16px;background:rgba(128,128,128,.07);height:100%}
.card .n{font-size:30px;font-weight:700;line-height:1.15}.card .l{opacity:.75;font-size:13px}
.card .t{font-weight:700;font-size:16px;margin-bottom:4px}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;margin:3px 4px 0 0;font-weight:600}
.ph{background:#16a34a2e;color:#22c55e}.pi{background:#2563eb2e;color:#60a5fa}
.ps{background:#d977062e;color:#fbbf24}.pa{background:#dc26262e;color:#f87171}
</style>"""


def _flash(key):
    msg = st.session_state.pop(key, None)
    if msg:
        st.success(msg)


def _impor_awal(store):
    seed = pd.read_csv(SEED, dtype=str)
    dimuat = []
    for k in KELAS:
        if store.siswa(k).empty:
            d = seed[seed["Kelas"] == k].rename(columns={"JK": "Jenis Kelamin"})
            store.save_siswa(k, d)
            dimuat.append(k)
    return dimuat


# ------------------------------------------------------------------ Ringkasan
def page_dashboard(store, cfg):
    st.markdown(CSS, unsafe_allow_html=True)
    idn = store.identity()
    t = date.today()
    sis = {k: store.siswa(k) for k in KELAS}
    total = sum(len(v) for v in sis.values())
    if total == 0:
        st.info("Data siswa belum dimuat. Klik tombol di bawah untuk memuat 93 siswa kelas 7A, 7B, 8, dan 9 "
                "(masing-masing ke tab sheet sendiri).")
        if st.button("⬇️ Muat data siswa awal", type="primary"):
            _impor_awal(store)
            st.rerun()
        return

    bln = bulan_aktif()
    stat = {}          # kelas -> DataFrame presensi bulan terpilih
    for k in KELAS:
        stat[k] = store.read_tab(tab_presensi(k, tahun_bulan(idn, bln), bln))
    ab = HARI_ABBR[t.weekday()]
    label = f"{ab}, {t.day:02d}"
    kbm_hari_ini = [k for k in KELAS if ab in jadwal(idn, k)]
    sudah = [k for k in kbm_hari_ini if label in stat_today(store, idn, k, t).columns
             and stat_today(store, idn, k, t)[label].isin(STATUS).any()]
    semua = pd.concat([d[date_cols(d)].stack() for d in stat.values() if len(d) and date_cols(d)], ignore_index=True) \
        if any(len(d) and date_cols(d) for d in stat.values()) else pd.Series(dtype=str)
    semua = semua[semua.isin(STATUS)]
    persen = round((semua == "H").mean() * 100, 1) if len(semua) else None

    def card(n, lab):
        return f'<div class="card"><div class="n">{n}</div><div class="l">{lab}</div></div>'

    c = st.columns(4)
    c[0].markdown(card(total, "Total siswa"), unsafe_allow_html=True)
    c[1].markdown(card(len(KELAS), "Kelas diampu"), unsafe_allow_html=True)
    c[2].markdown(card(f"{len(sudah)}/{len(kbm_hari_ini)}", "Kelas ber-KBM hari ini yang sudah presensi"),
                  unsafe_allow_html=True)
    c[3].markdown(card(f"{persen}%" if persen is not None else "—", f"Kehadiran bulan {BULAN[bln]}"),
                  unsafe_allow_html=True)

    st.markdown("#### Presensi hari ini")
    cols = st.columns(len(KELAS))
    for col, k in zip(cols, KELAS):
        hari = jadwal(idn, k)
        if not hari:
            s = "⚙️ jadwal KBM belum diatur"
        elif ab not in hari:
            s = "— tidak ada KBM hari ini"
        else:
            d = stat_today(store, idn, k, t)
            if label in d.columns and d[label].isin(STATUS).any():
                pills = "".join(f'<span class="pill p{x.lower()}">{x} {int((d[label] == x).sum())}</span>' for x in STATUS)
                s = f"✅ sudah diisi<br>{pills}"
            else:
                s = "⏳ belum diisi"
        col.markdown(f'<div class="card"><div class="t">Kelas {k}</div><div class="l">{len(sis[k])} siswa'
                     f'{" • KBM " + ", ".join(HARI_FULL[HARI_ABBR.index(h)] for h in hari) if hari else ""}</div>'
                     f'<div style="margin-top:8px;font-size:13px">{s}</div></div>', unsafe_allow_html=True)

    st.markdown("&nbsp;")
    left, right = st.columns(2)
    with left:
        st.markdown(f"#### Kehadiran per kelas — {BULAN[bln]} (%)")
        rows = {}
        for k, d in stat.items():
            if len(d) and date_cols(d):
                v = d[date_cols(d)].stack()
                v = v[v.isin(STATUS)]
                if len(v):
                    rows[k] = round((v == "H").mean() * 100, 1)
        if rows:
            st.bar_chart(pd.Series(rows, name="% hadir"))
        else:
            st.caption("Belum ada data presensi pada bulan ini.")
    with right:
        st.markdown(f"#### Siswa dengan alpha terbanyak — {BULAN[bln]}")
        al = []
        for k, d in stat.items():
            if len(d) and date_cols(d):
                n = (d[date_cols(d)] == "A").sum(axis=1)
                al += [(k, nm, int(x)) for nm, x in zip(d["Nama"], n) if x > 0]
        if al:
            st.dataframe(pd.DataFrame(al, columns=["Kelas", "Nama", "Alpha"]).sort_values("Alpha", ascending=False).head(5),
                         hide_index=True, width="stretch")
        else:
            st.caption("Belum ada catatan alpha.")

    st.markdown("#### Kelengkapan buku nilai (kolom Nilai 2–15 yang sudah terisi)")
    rows = []
    for k in KELAS:
        d = norm_nilai(store.read_tab(tab_nilai(k)))
        terisi = sum(1 for c_ in NILAI_COLS if c_ in d.columns and pd.to_numeric(d[c_], errors="coerce").notna().any())
        rows.append({"Kelas": k, "Kolom terisi": f"{terisi} dari {N_NILAI - 1}", "Siswa": len(sis[k])})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def stat_today(store, idn, kelas, t):
    return store.read_tab(tab_presensi(kelas, tahun_bulan(idn, t.month), t.month))


# ------------------------------------------------------------------ Pengaturan Kelas
def page_pengaturan(store, cfg):
    st.header("⚙️ Pengaturan Kelas")
    t1, t2 = st.tabs(["Jadwal KBM", "Data Siswa"])

    with t1:
        st.caption(f"Pilih hari mengajar {cfg['singkat']} di tiap kelas. Kolom tanggal di Buku Presensi dibuat otomatis "
                   "mengikuti hari-hari ini.")
        idn = store.identity()
        pilih = {}
        cols = st.columns(len(KELAS))
        for col, k in zip(cols, KELAS):
            pilih[k] = col.multiselect(f"Kelas {k}", HARI_ABBR, default=jadwal(idn, k), key=f"jd_{k}",
                                       format_func=lambda a: HARI_FULL[HARI_ABBR.index(a)])
        if st.button("💾 Simpan jadwal KBM", type="primary"):
            d = store.identity()
            for k, v in pilih.items():
                d[f"jadwal_{k}"] = ",".join(sorted(v, key=HARI_ABBR.index))
            store.save_identity(d)
            st.success("Jadwal KBM tersimpan.")
            st.rerun()

    with t2:
        kelas = kelas_aktif()
        st.caption(f"Kelas aktif: **{kelas}** (ganti lewat sidebar kiri). Data tersimpan di tab sheet **Siswa {kelas}**.")
        df = store.siswa(kelas).rename(columns={"Jenis Kelamin": "JK"})[["No", "Nama", "JK"]]
        df["No"] = pd.to_numeric(df["No"], errors="coerce")
        edited = st.data_editor(
            df, num_rows="dynamic", hide_index=True, width="stretch", key=f"sis_{kelas}",
            column_config={"No": st.column_config.NumberColumn(disabled=True),
                           "JK": st.column_config.SelectboxColumn("JK", options=["L", "P"], required=True)})
        st.caption(f"Jumlah siswa kelas {kelas}: **{len(df)}**. Tambah baris di bagian bawah tabel; hapus dengan memilih baris lalu tombol Delete.")
        c1, c2 = st.columns(2)
        if c1.button("💾 Simpan data kelas", type="primary", key=f"sv_sis_{kelas}"):
            out = edited.dropna(subset=["Nama"]).copy()
            out["Nama"] = out["Nama"].astype(str).str.strip()
            out = out[out["Nama"] != ""]
            out["JK"] = out["JK"].fillna("L")
            out["No"] = range(1, len(out) + 1)
            store.save_siswa(kelas, out.rename(columns={"JK": "Jenis Kelamin"}))
            st.success(f"Data kelas {kelas} tersimpan ({len(out)} siswa).")
            st.rerun()
        if c2.button("⬇️ Impor data awal (hanya kelas yang masih kosong)"):
            dimuat = _impor_awal(store)
            st.success(f"Diimpor: kelas {', '.join(dimuat)}." if dimuat else "Semua kelas sudah berisi data.")
            if dimuat:
                st.rerun()


# ------------------------------------------------------------------ Presensi
def page_presensi(store, cfg):
    idn = store.identity()
    kelas, bln = kelas_aktif(), bulan_aktif()
    tahun = tahun_bulan(idn, bln)
    st.header(f"📖 Buku Presensi Harian ({cfg['singkat']} - Kelas {kelas} - Bulan {BULAN[bln]})")
    tp, tr = st.tabs(["Isi presensi", "Rekap semester"])

    with tp:
        _flash("flash_pres")
        hari = jadwal(idn, kelas)
        labels = tanggal_cols(hari, tahun, bln)
        roster = store.siswa(kelas)
        if not hari:
            st.warning("Jadwal KBM kelas ini belum diatur. Buka tab **⚙️ Pengaturan Kelas → Jadwal KBM**.")
        elif roster.empty:
            st.warning("Belum ada siswa di kelas ini. Isi dulu di tab **⚙️ Pengaturan Kelas → Data Siswa**.")
        elif not labels:
            st.info(f"Tidak ada hari KBM pada bulan {BULAN[bln]} {tahun}.")
        else:
            st.caption(f"📅 Kolom tanggal otomatis disesuaikan dengan Jadwal KBM {cfg['singkat']} di Kelas {kelas} "
                       f"pada bulan {BULAN[bln]}. Kosongkan sel untuk pertemuan yang belum/tidak ada.")
            name = tab_presensi(kelas, tahun, bln)
            sk = f"pres_{kelas}_{tahun}_{bln}"
            if sk not in st.session_state:
                saved = store.read_tab(name)
                base = roster[["No", "Nama"]].copy()
                base["No"] = pd.to_numeric(base["No"], errors="coerce")
                for lb in labels:
                    m = dict(zip(saved["Nama"], saved[lb])) if "Nama" in saved.columns and lb in saved.columns else {}
                    base[lb] = [m.get(n) if m.get(n) in STATUS else None for n in base["Nama"]]
                st.session_state[sk], st.session_state[sk + "_v"] = base, 0
            base, ver = st.session_state[sk], st.session_state[sk + "_v"]
            show = pd.concat([base, hitung_status(base, labels)], axis=1)
            cfgcols = {lb: st.column_config.SelectboxColumn(lb, options=STATUS, required=False, width="small") for lb in labels}
            cfgcols["Nama"] = st.column_config.TextColumn("Nama Siswa")
            edited = st.data_editor(show, hide_index=True, width="stretch", key=f"ed_{sk}_{ver}",
                                    disabled=["No", "Nama"] + URUT, column_config=cfgcols)
            st.caption("Angka H / S / I / A diperbarui setelah klik Simpan.")
            core = edited.drop(columns=URUT)

            c1, c2, c3 = st.columns([2, 2, 2])
            tgl = c1.selectbox("Isi cepat untuk tanggal", labels, key=f"qf_{sk}")
            if c1.button("Set yang kosong = H"):
                core[tgl] = core[tgl].where(core[tgl].isin(STATUS), "H")
                st.session_state[sk], st.session_state[sk + "_v"] = core, ver + 1
                st.rerun()
            if c3.button("↻ Muat ulang dari sheet"):
                store.reload(name)
                del st.session_state[sk]
                st.rerun()
            if c2.button(f"💾 Simpan presensi {BULAN[bln]}", type="primary"):
                out = roster[["Nama", "No", "Jenis Kelamin"]].merge(core[["Nama"] + labels], on="Nama", how="left")
                out = pd.concat([out, hitung_status(out, labels)[URUT]], axis=1)
                store.write_tab(name, out)
                st.session_state[sk] = core
                st.session_state["flash_pres"] = f"Presensi kelas {kelas} bulan {BULAN[bln]} tersimpan ke tab '{name}'."
                st.rerun()

    with tr:
        rk = rekap_semester(store, idn, kelas)
        st.caption(f"Akumulasi semua bulan semester {idn.get('semester', '')} untuk kelas {kelas}.")
        if rk.empty:
            st.info("Belum ada data presensi.")
        else:
            st.dataframe(rk, width="stretch")
            st.download_button("⬇️ Unduh rekap (CSV)", rk.to_csv().encode(), f"rekap_presensi_{kelas}.csv")


# ------------------------------------------------------------------ Buku Nilai
def page_nilai(store, cfg):
    idn = store.identity()
    kelas = kelas_aktif()
    st.header(f"📊 Buku Nilai & Akumulasi Realtime ({cfg['singkat']} - Kelas {kelas})")
    _flash("flash_nilai")

    with st.expander("📌 Pengaturan Kategori/Jenis Penilaian per Kolom"):
        st.caption("Beri nama kategori tiap kolom (mis. Tugas Individu, Ulangan Harian, UTS, UAS). Nilai 1 selalu Nilai Kehadiran (otomatis).")
        cols, kat = st.columns(3), {}
        for n in range(2, N_NILAI + 1):
            kat[n] = cols[(n - 2) % 3].text_input(f"Nilai {n}", idn.get(f"kat_{kelas}_{n}", ""), key=f"kat_{kelas}_{n}",
                                                  placeholder="mis. Tugas Individu")
        if st.button("💾 Simpan kategori"):
            d = store.identity()
            d.update({f"kat_{kelas}_{n}": v.strip() for n, v in kat.items()})
            store.save_identity(d)
            lama = store.read_tab(tab_nilai(kelas))
            if len(lama):
                store.write_tab(tab_nilai(kelas), rename_sheet_cols(norm_nilai(lama), d, kelas))
            st.success("Kategori tersimpan; judul kolom di sheet ikut diperbarui.")
            st.rerun()

    with st.expander("⚖️ Pengaturan nilai kehadiran & nilai akhir"):
        st.caption("Nilai kehadiran = rata-rata skor status pada semua pertemuan yang sudah terisi (0–100). "
                   "Nilai akhir = rata akademik (Nilai 2–15) dikalikan (100% − bobot) + nilai kehadiran × bobot.")
        c = st.columns(5)
        sk_ = {s: c[i].number_input(f"Skor {STATUS_LABEL[s]}", 0.0, 100.0, num(idn, f"skor_{s}", SKOR_DEFAULT[s]), key=f"skor_in_{s}")
               for i, s in enumerate(["H", "S", "I", "A"])}
        bobot = c[4].number_input("Bobot kehadiran (%)", 0.0, 100.0, num(idn, "bobot_kehadiran", 10), key="bobot_in")
        if st.button("💾 Simpan pengaturan nilai"):
            d = store.identity()
            d.update({f"skor_{s}": v for s, v in sk_.items()})
            d["bobot_kehadiran"] = bobot
            store.save_identity(d)
            st.success("Tersimpan.")
            st.rerun()

    roster = store.siswa(kelas)
    if roster.empty:
        st.warning("Belum ada siswa di kelas ini.")
        return
    name = tab_nilai(kelas)
    sk = f"nilai_{kelas}"
    if sk not in st.session_state:
        saved = norm_nilai(store.read_tab(name))
        base = roster[["No", "Nama"]].copy()
        base["No"] = pd.to_numeric(base["No"], errors="coerce")
        for cn in NILAI_COLS:
            m = dict(zip(saved["Nama"], pd.to_numeric(saved[cn], errors="coerce"))) \
                if "Nama" in saved.columns and cn in saved.columns else {}
            base[cn] = [m.get(n, np.nan) for n in base["Nama"]]
        st.session_state[sk], st.session_state[sk + "_v"] = base, 0
    base, ver = st.session_state[sk], st.session_state[sk + "_v"]
    hadir = skor_kehadiran(store, idn, kelas)
    bobot_f = num(idn, "bobot_kehadiran", 10) / 100

    show = base.copy()
    show.insert(2, "Nilai 1", [hadir.get(n, np.nan) for n in show["Nama"]])
    cc = {"Nama": st.column_config.TextColumn("Nama Siswa"),
          "Nilai 1": st.column_config.NumberColumn("Nilai 1 (Nilai Kehadiran (Otomatis))", format="%.2f")}
    for n in range(2, N_NILAI + 1):
        k = idn.get(f"kat_{kelas}_{n}", "")
        cc[f"Nilai {n}"] = st.column_config.NumberColumn(f"Nilai {n} ({k})" if k else f"Nilai {n}", min_value=0,
                                                         max_value=100, step=0.5)
    edited = st.data_editor(show, hide_index=True, width="stretch", key=f"ed_{sk}_{ver}",
                            disabled=["No", "Nama", "Nilai 1"], column_config=cc)
    core = edited.drop(columns=["Nilai 1"])
    h, ra, na = hitung_nilai(core, hadir, bobot_f)
    st.markdown("**Hasil sementara (terhitung langsung dari isian di atas)**")
    hasil = pd.DataFrame({"Nama": core["Nama"], "Nilai Kehadiran": h, "📚 Rata Akademik": ra, "📊 Nilai Akhir": na})
    st.dataframe(hasil, hide_index=True, width="stretch")

    c1, c2 = st.columns(2)
    if c1.button(f"💾 Simpan nilai kelas {kelas}", type="primary"):
        out = roster[["Nama", "No", "Jenis Kelamin"]].merge(core[["Nama"] + NILAI_COLS], on="Nama", how="left")
        out.insert(3, "Nilai 1", [hadir.get(n, np.nan) for n in out["Nama"]])
        h2, ra2, na2 = hitung_nilai(out, hadir, bobot_f)
        out["📚 Rata Akademik"], out["📊 Nilai Akhir"] = ra2, na2
        store.write_tab(name, rename_sheet_cols(out, idn, kelas))
        st.session_state[sk] = core
        st.session_state["flash_nilai"] = f"Nilai kelas {kelas} tersimpan ke tab '{name}'."
        st.rerun()
    if c2.button("↻ Muat ulang dari sheet", key="rl_nilai"):
        store.reload(name)
        del st.session_state[sk]
        st.rerun()
