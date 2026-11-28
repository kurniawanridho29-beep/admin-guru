"""Aturan inti: jadwal KBM, kolom tanggal, nilai kehadiran otomatis, nilai akhir."""
import calendar
import re
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from .config import BULAN, HARI_ABBR, KELAS, N_NILAI

DATE_RE = re.compile(r"^(Sen|Sel|Rab|Kam|Jum|Sab|Min), \d{2}$")
SKOR_DEFAULT = {"H": 100.0, "S": 75.0, "I": 75.0, "A": 0.0}
URUT = ["H", "S", "I", "A"]          # urutan kolom rekap di sheet
NILAI_COLS = [f"Nilai {n}" for n in range(2, N_NILAI + 1)]


def kelas_aktif():
    return st.session_state.get("kelas_aktif", KELAS[0])


def bulan_aktif():
    return BULAN.index(st.session_state.get("bulan_aktif", BULAN[date.today().month]))


def tahun_bulan(idn, bulan):
    try:
        y1, y2 = [int(x) for x in idn.get("tahun_ajaran", "").split("/")]
    except Exception:
        y1 = y2 = date.today().year
    return y1 if bulan >= 7 else y2


def bulan_semester(idn):
    return list(range(7, 13)) if idn.get("semester", "Genap") == "Ganjil" else list(range(1, 7))


def jadwal(idn, kelas):
    return [x for x in idn.get(f"jadwal_{kelas}", "").split(",") if x in HARI_ABBR]


def tanggal_cols(hari, tahun, bulan):
    out = []
    for d in range(1, calendar.monthrange(tahun, bulan)[1] + 1):
        ab = HARI_ABBR[date(tahun, bulan, d).weekday()]
        if ab in hari:
            out.append(f"{ab}, {d:02d}")
    return out


def tab_presensi(kelas, tahun, bulan):
    return f"Presensi {kelas} {BULAN[bulan]} {tahun}"


def tab_nilai(kelas):
    return f"Nilai {kelas}"


def date_cols(df):
    return [c for c in df.columns if DATE_RE.match(str(c))]


def hitung_status(df, cols):
    if not cols:
        return pd.DataFrame({s: np.zeros(len(df), dtype=int) for s in URUT}, index=df.index)
    return pd.DataFrame({s: (df[cols] == s).sum(axis=1) for s in URUT}, index=df.index)


def num(idn, key, default):
    try:
        return float(idn.get(key, default))
    except Exception:
        return float(default)


def skor_kehadiran(store, idn, kelas):
    """Nilai kehadiran otomatis per siswa = rata-rata skor status pada semua pertemuan yang sudah terisi di semester."""
    w = {s: num(idn, f"skor_{s}", d) for s, d in SKOR_DEFAULT.items()}
    tot, cnt = {}, {}
    for m in bulan_semester(idn):
        df = store.read_tab(tab_presensi(kelas, tahun_bulan(idn, m), m))
        if df.empty or "Nama" not in df.columns:
            continue
        for c in date_cols(df):
            for nama, v in zip(df["Nama"], df[c]):
                if v in w:
                    tot[nama] = tot.get(nama, 0) + w[v]
                    cnt[nama] = cnt.get(nama, 0) + 1
    return {n: round(tot[n] / cnt[n], 2) for n in tot}


def rekap_semester(store, idn, kelas):
    rows = {}
    for m in bulan_semester(idn):
        df = store.read_tab(tab_presensi(kelas, tahun_bulan(idn, m), m))
        if df.empty or "Nama" not in df.columns:
            continue
        cols = date_cols(df)
        cnt = hitung_status(df, cols)
        for nama, r in zip(df["Nama"], cnt.itertuples(index=False)):
            cur = rows.setdefault(nama, dict.fromkeys(URUT, 0))
            for s, v in zip(URUT, r):
                cur[s] += int(v)
    out = pd.DataFrame.from_dict(rows, orient="index", columns=URUT)
    if len(out):
        out["% Hadir"] = (out["H"] / out.sum(axis=1).replace(0, np.nan) * 100).round(1)
    return out


def hitung_nilai(df, hadir, bobot):
    """df berisi kolom Nama dan Nilai 2..15. Mengembalikan (kehadiran, rata akademik, nilai akhir)."""
    ra = df[NILAI_COLS].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    h = pd.Series([hadir.get(n, np.nan) for n in df["Nama"]], index=df.index, dtype=float)
    na = ra * (1 - bobot) + h * bobot
    na = na.where(h.notna(), ra).where(ra.notna(), np.nan)
    return h, ra.round(2), na.round(2)
