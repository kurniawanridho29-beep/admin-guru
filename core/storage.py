"""Penyimpanan: Google Sheets (produksi) atau CSV lokal (uji coba). Satu tab per kelas untuk siswa/presensi/nilai."""
import base64
import json
import os
import zlib

import pandas as pd
import streamlit as st

from .config import DEFAULT_IDENTITAS

HEADERS = {
    "identitas": ["Kunci", "Nilai"],
    "modul": ["ID", "Part", "Judul", "Kelas", "Dibuat", "Data"],
    "skema": ["Nama", "Isi"],
    "prota": ["Tingkat", "Semester", "No", "Materi", "TP", "JP"],
}
CHUNK = 40000  # batas sel Google Sheets = 50.000 karakter


class Store:
    def __init__(self, subject: str):
        self.subject = subject
        self.cache = {}
        self.ss = None
        self.ws = {}
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
                self.ws = {w.title: w for w in self.ss.worksheets()}
                self.mode = "sheets"
        except Exception as e:  # noqa
            self.err = str(e)

    # ---------- tab generik ----------
    def exists(self, name):
        return name in self.ws if self.mode == "sheets" else os.path.exists(f"{self.dir}/{name}.csv")

    def _load(self, name):
        if self.mode == "sheets":
            vals = self.ws[name].get_all_values(value_render_option="UNFORMATTED_VALUE")
            if not vals:
                return pd.DataFrame(columns=HEADERS.get(name, []))
            width = len(vals[0])
            df = pd.DataFrame([r + [""] * (width - len(r)) for r in vals[1:]], columns=[str(c) for c in vals[0]])
        else:
            df = pd.read_csv(f"{self.dir}/{name}.csv", dtype=str, keep_default_na=False)
        if name in HEADERS:
            df = df.astype(str)
        else:
            for c in ("Nama", "No", "Jenis Kelamin"):
                if c in df.columns:
                    df[c] = df[c].astype(str)
        return df

    def read_tab(self, name, columns=None):
        if name not in self.cache:
            self.cache[name] = self._load(name) if self.exists(name) else \
                pd.DataFrame(columns=columns or HEADERS.get(name, []))
        return self.cache[name].copy()

    read = read_tab

    def reload(self, name=None):
        self.cache.pop(name, None) if name else self.cache.clear()

    def write_tab(self, name, df):
        df = df.copy()
        if name in HEADERS:
            for h in HEADERS[name]:
                if h not in df.columns:
                    df[h] = ""
            df = df[HEADERS[name] + [c for c in df.columns if c not in HEADERS[name]]]
        cols = [str(c) for c in df.columns]
        clean = df.astype(object)
        clean = clean.where(clean.notna(), "")
        if self.mode == "sheets":
            values = [cols] + [[(v.item() if hasattr(v, "item") else v) for v in row] for row in clean.values.tolist()]
            if name not in self.ws:
                self.ws[name] = self.ss.add_worksheet(title=name, rows=max(len(values) + 20, 100), cols=max(len(cols), 10))
            ws = self.ws[name]
            ws.clear()
            ws.resize(rows=max(len(values) + 20, 100), cols=max(len(cols), 10))
            ws.update(values=values, range_name="A1", value_input_option="RAW")
        else:
            clean.to_csv(f"{self.dir}/{name}.csv", index=False)
        self.cache[name] = clean.reset_index(drop=True)

    write = write_tab

    def replace_block(self, name, filters: dict, new_df):
        df = self.read_tab(name)
        mask = pd.Series(True, index=df.index)
        for k, v in filters.items():
            mask &= df[k].astype(str) == str(v)
        frames = [f for f in (df[~mask], new_df) if len(f)]
        self.write_tab(name, pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=HEADERS[name]))

    # ---------- identitas & pengaturan (kunci-nilai) ----------
    def identity(self):
        df = self.read_tab("identitas")
        d = dict(DEFAULT_IDENTITAS)
        d.update({k: v for k, v in zip(df["Kunci"], df["Nilai"]) if str(v).strip()})
        return d

    def save_identity(self, d: dict):
        self.write_tab("identitas", pd.DataFrame({"Kunci": list(d), "Nilai": [str(v) for v in d.values()]}))

    # ---------- siswa: satu tab per kelas ----------
    def siswa(self, kelas):
        df = self.read_tab(f"Siswa {kelas}", ["Nama", "No", "Jenis Kelamin"])
        for c in ("Nama", "No", "Jenis Kelamin"):
            if c not in df.columns:
                df[c] = ""
        df = df.assign(_n=pd.to_numeric(df["No"], errors="coerce")).sort_values("_n", kind="stable")
        return df[["Nama", "No", "Jenis Kelamin"]].reset_index(drop=True)

    def save_siswa(self, kelas, df):
        self.write_tab(f"Siswa {kelas}", df[["Nama", "No", "Jenis Kelamin"]])

    # ---------- modul: terkompresi + dipecah supaya muat di sel Sheets ----------
    def save_modul(self, mid, judul, kelas, dibuat, payload: dict):
        blob = base64.b64encode(zlib.compress(json.dumps(payload, ensure_ascii=False).encode())).decode()
        parts = [blob[i:i + CHUNK] for i in range(0, len(blob), CHUNK)]
        new = pd.DataFrame([{"ID": mid, "Part": i, "Judul": judul, "Kelas": kelas, "Dibuat": dibuat, "Data": p}
                            for i, p in enumerate(parts)])
        self.replace_block("modul", {"ID": mid}, new)

    def list_modul(self):
        df = self.read_tab("modul")
        return df if df.empty else df[df["Part"] == "0"][["ID", "Judul", "Kelas", "Dibuat"]].reset_index(drop=True)

    def load_modul(self, mid):
        df = self.read_tab("modul")
        df = df[df["ID"] == str(mid)].assign(_p=lambda x: pd.to_numeric(x["Part"])).sort_values("_p")
        return json.loads(zlib.decompress(base64.b64decode("".join(df["Data"].tolist()))).decode())


@st.cache_resource(show_spinner="Menghubungkan ke penyimpanan…")
def get_store(subject):
    return Store(subject)
