"""Penyimpanan: Google Sheets (produksi) atau CSV lokal (uji coba)."""
import base64
import json
import os
import zlib

import pandas as pd
import streamlit as st

from .config import DEFAULT_IDENTITAS

HEADERS = {
    "identitas": ["Kunci", "Nilai"],
    "siswa": ["Kelas", "No", "Nama", "JK"],
    "presensi": ["Tanggal", "Kelas", "Nama", "Status"],
    "nilai_harian": ["Kelas", "Nama"],
    "nilai_ulangan": ["Kelas", "Nama"],
    "nilai_ujian": ["Kelas", "Nama"],
    "meta_kolom": ["Sheet", "Kelas", "Urutan", "Kolom"],
    "modul": ["ID", "Part", "Judul", "Kelas", "Dibuat", "Data"],
    "skema": ["Nama", "Isi"],
    "prota": ["Tingkat", "Semester", "No", "Materi", "TP", "JP"],
}
TEXT_COLS = ["Kelas", "Nama", "Tanggal", "Status", "Tingkat", "Kunci", "Nilai", "Judul", "ID", "Part",
             "Dibuat", "Data", "Materi", "TP", "Semester", "Sheet", "Kolom", "JK", "No", "Isi", "Urutan"]
CHUNK = 40000  # batas sel Google Sheets = 50.000 karakter


class Store:
    def __init__(self, subject: str):
        self.subject = subject
        self.cache = {}
        self.ss = None
        self.mode = "lokal"
        self.err = ""
        self.dir = f"data_local/{subject.lower()}"
        os.makedirs(self.dir, exist_ok=True)
        try:
            if "gcp_service_account" in st.secrets and "spreadsheet_id" in st.secrets:
                import gspread
                info = dict(st.secrets["gcp_service_account"])
                info["private_key"] = str(info.get("private_key", "")).replace("\\n", "\n").strip()
                pk = info["private_key"]
                if "..." in pk or len(pk) < 1000 or "GANTI" in pk:
                    raise ValueError(f"private_key tampak belum diisi benar (panjang {len(pk)} karakter; seharusnya sekitar 1700, "
                                     "tanpa '...' atau 'GANTI')")
                gc = gspread.service_account_from_dict(info)
                self.ss = gc.open_by_key(st.secrets["spreadsheet_id"])
                self.mode = "sheets"
        except Exception as e:  # noqa
            self.err = str(e)

    # ---------- dasar ----------
    def _empty(self, name):
        return pd.DataFrame(columns=HEADERS[name])

    def _load(self, name):
        if self.mode == "sheets":
            import gspread
            try:
                ws = self.ss.worksheet(name)
            except gspread.WorksheetNotFound:
                ws = self.ss.add_worksheet(title=name, rows=200, cols=max(10, len(HEADERS[name])))
                ws.update(values=[HEADERS[name]], range_name="A1")
                return self._empty(name)
            vals = ws.get_all_values(value_render_option="UNFORMATTED_VALUE")
            if not vals:
                return self._empty(name)
            width = len(vals[0])
            rows = [r + [""] * (width - len(r)) for r in vals[1:]]
            df = pd.DataFrame(rows, columns=vals[0])
        else:
            path = f"{self.dir}/{name}.csv"
            if not os.path.exists(path):
                return self._empty(name)
            df = pd.read_csv(path, dtype=str, keep_default_na=False)
        for c in TEXT_COLS:
            if c in df.columns and not name.startswith("nilai_"):
                df[c] = df[c].astype(str)
            elif c in ("Kelas", "Nama") and c in df.columns:
                df[c] = df[c].astype(str)
        return df

    def read(self, name):
        if name not in self.cache:
            self.cache[name] = self._load(name)
        return self.cache[name].copy()

    def reload(self, name=None):
        if name:
            self.cache.pop(name, None)
        else:
            self.cache.clear()

    def write(self, name, df):
        df = df.copy()
        for h in HEADERS[name]:
            if h not in df.columns:
                df[h] = ""
        cols = HEADERS[name] + [c for c in df.columns if c not in HEADERS[name]]
        df = df[cols].astype(object)
        df = df.where(df.notna(), "")
        if self.mode == "sheets":
            import gspread
            try:
                ws = self.ss.worksheet(name)
            except gspread.WorksheetNotFound:
                ws = self.ss.add_worksheet(title=name, rows=200, cols=max(10, len(cols)))
            values = [cols] + df.values.tolist()
            ws.clear()
            ws.resize(rows=max(len(values) + 20, 100), cols=max(len(cols), 10))
            ws.update(values=values, range_name="A1", value_input_option="RAW")
        else:
            df.to_csv(f"{self.dir}/{name}.csv", index=False)
        self.cache[name] = df.reset_index(drop=True)

    def replace_block(self, name, filters: dict, new_df):
        df = self.read(name)
        mask = pd.Series(True, index=df.index)
        for k, v in filters.items():
            mask &= df[k].astype(str) == str(v)
        keep = df[~mask]
        frames = [f for f in (keep, new_df) if len(f)]
        out = pd.concat(frames, ignore_index=True) if frames else self._empty(name)
        self.write(name, out)

    # ---------- helper ----------
    def identity(self):
        df = self.read("identitas")
        d = dict(DEFAULT_IDENTITAS)
        d.update({k: v for k, v in zip(df["Kunci"], df["Nilai"]) if str(v).strip()})
        return d

    def save_identity(self, d: dict):
        self.write("identitas", pd.DataFrame({"Kunci": list(d), "Nilai": [str(v) for v in d.values()]}))

    def siswa(self, kelas=None):
        df = self.read("siswa")
        if kelas is not None:
            df = df[df["Kelas"] == str(kelas)]
        df = df.assign(_n=pd.to_numeric(df["No"], errors="coerce")).sort_values("_n", kind="stable")
        return df.drop(columns="_n").reset_index(drop=True)

    # modul disimpan terkompresi + dipecah supaya muat di sel Sheets
    def save_modul(self, mid, judul, kelas, dibuat, payload: dict):
        blob = base64.b64encode(zlib.compress(json.dumps(payload, ensure_ascii=False).encode())).decode()
        parts = [blob[i:i + CHUNK] for i in range(0, len(blob), CHUNK)]
        new = pd.DataFrame([{"ID": mid, "Part": i, "Judul": judul, "Kelas": kelas, "Dibuat": dibuat, "Data": p}
                            for i, p in enumerate(parts)])
        self.replace_block("modul", {"ID": mid}, new)

    def list_modul(self):
        df = self.read("modul")
        if df.empty:
            return df
        return df[df["Part"] == "0"][["ID", "Judul", "Kelas", "Dibuat"]].reset_index(drop=True)

    def load_modul(self, mid):
        df = self.read("modul")
        df = df[df["ID"] == str(mid)].assign(_p=lambda x: pd.to_numeric(x["Part"])).sort_values("_p")
        blob = "".join(df["Data"].tolist())
        return json.loads(zlib.decompress(base64.b64decode(blob)).decode())


@st.cache_resource(show_spinner="Menghubungkan ke penyimpanan…")
def get_store(subject):
    return Store(subject)
