# Admin Guru — IPS & PPKn (SMP)

Satu kode, dua app terpisah: `app_ips.py` (IPS) dan `app_ppkn.py` (PPKn).
Masing-masing punya Google Sheet sendiri, jadi data tidak pernah tercampur.

## Fitur
Dashboard + identitas (sidebar kiri) · Pengaturan Kelas (7A, 7B, 8, 9) · Presensi H/I/S/A ·
Buku Nilai (harian, ulangan, ujian + rekap nilai akhir) · Generate Modul Ajar (Deep Learning) · Prota & Prosem.

**Semua gratis.** Modul ajar dibuat lewat *mode gratis*: app menyusun prompt, Anda tempel ke chat Claude, lalu tempel jawabannya
kembali ke app untuk dijadikan Word. `ANTHROPIC_API_KEY` (berbayar) **opsional** — kalau tidak diisi, mode otomatis nonaktif.

## Langkah deploy
1. **Google Cloud**: buat project → aktifkan *Google Sheets API* → buat *Service Account* → buat key JSON.
2. **Google Sheets**: buat 2 spreadsheet kosong ("Admin IPS" dan "Admin PPKn"). Bagikan (Share) masing-masing ke
   `client_email` service account sebagai **Editor**. Salin ID dari URL (`/d/<ID>/edit`).
3. **GitHub**: upload seluruh isi folder ini ke satu repo (jangan upload secrets asli).
4. **streamlit.app**: *New app* dua kali dari repo yang sama:
   - App 1 → Main file `app_ips.py`
   - App 2 → Main file `app_ppkn.py`
5. Di tiap app: *Settings → Secrets*, isi seperti `.streamlit/secrets.toml.example`
   (`spreadsheet_id` BERBEDA untuk IPS dan PPKn; `ANTHROPIC_API_KEY` boleh sama).
6. Buka app → **Pengaturan Kelas** → isi Identitas → *Impor data awal* → Simpan.

Tab di Google Sheet dibuat otomatis oleh app. Jangan ubah nama tab/header-nya.

## Uji di komputer sendiri
`pip install -r requirements.txt` lalu `streamlit run app_ips.py` — tanpa secrets, data disimpan di folder
`data_local/` (hanya untuk uji coba; di streamlit.app folder ini hilang saat restart).
