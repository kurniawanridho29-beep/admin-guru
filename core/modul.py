import json
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from . import ai
from .config import DIMENSI, KELAS, MODEL_PEMBELAJARAN, tingkat
from .docx_out import build_modul

SKEMA_CONTOH = (
    "Contoh (tulis sesuai selera, urutannya akan diikuti AI):\n"
    "1. Orientasi: guru menyajikan fenomena/kasus pemantik\n"
    "2. Eksplorasi: siswa menggali informasi dari sumber\n"
    "3. Diskusi kelompok: menganalisis & menyusun jawaban\n"
    "4. Presentasi & umpan balik teman\n"
    "5. Penguatan konsep oleh guru\n"
    "6. Refleksi"
)


def _ctx_text(c):
    return (
        f"Mata pelajaran: {c['mapel']}\nKelas: {c['kelas']} (Fase D)\nSemester: {c['semester']}\n"
        f"Bab/Tema: {c['bab']}\nMateri pokok: {c['materi']}\nCapaian Pembelajaran: {c['cp']}\n"
        f"Tujuan pembelajaran dari guru (boleh dirapikan; kosong = susun sendiri): {c['tp'] or '-'}\n"
        f"Jumlah pertemuan: {c['n_pertemuan']} x {c['jp_per_pertemuan']} JP x {c['menit_jp']} menit\n"
        f"Model: {c['model']}\nMetode: {c['metode']}\nMedia: {c['media']}\nSumber belajar: {c['sumber']}\n"
        f"Dimensi profil lulusan yang dipilih: {', '.join(c['dimensi'])}\n"
        f"Catatan tambahan guru: {c['catatan'] or '-'}"
    )


def generate(c, progress):
    """Mengembalikan dict modul lengkap. progress(frac, teks)."""
    ctx = _ctx_text(c)
    n = c["n_pertemuan"]
    progress(0.05, "Menyusun komponen inti…")
    k = ai.call_json(f"""{ctx}

Susun komponen inti modul ajar. Keluarkan JSON dengan kunci persis:
{{"tujuan_pembelajaran":[4-6 kalimat, diawali kata kerja operasional],
"pemahaman_bermakna":"1 paragraf",
"pertanyaan_pemantik":{{"mindful":[3-4],"meaningful":[3-4],"joyful":[2-3]}},
"kompetensi_awal":[2-4],
"materi_esensial":[3-6],
"target_peserta":{{"reguler":"...","tinggi":"...","pendampingan":"..."}},
"kemitraan":[2-3 contoh mitra/orang tua/komunitas],
"lingkungan_belajar":"...",
"pemanfaatan_digital":"...",
"dimensi_profil":[{{"dimensi":"salah satu dimensi terpilih","wujud":"wujud nyata dalam bab ini"}}],
"rencana_pertemuan":[tepat {n} objek {{"judul":"...","fokus":"..."}} berurutan logis]}}""", 6000)
    progress(0.2, "Menyusun kegiatan tiap pertemuan…")
    pert = []
    total = c["jp_per_pertemuan"] * c["menit_jp"]
    for i, rp in enumerate(k["rencana_pertemuan"][:n], 1):
        pert.append(ai.call_json(f"""{ctx}

Tujuan pembelajaran bab: {k['tujuan_pembelajaran']}
Pertemuan {i} dari {n}: {rp['judul']} — fokus: {rp['fokus']}
Durasi total {total} menit: pendahuluan 10, inti {total - 20}, penutup 10.

SKEMA KEGIATAN INTI dari guru (WAJIB diikuti urutannya; tiap tahap memuat aktivitas guru DAN siswa):
{c['skema'] or 'Gunakan sintaks standar model ' + c['model']}

Aturan: kegiatan harus konkret, bisa dilaksanakan di kelas SMP, sesuai materi pertemuan ini saja (jangan
menyalin materi pertemuan lain). Pendahuluan memuat salam/doa, presensi, apersepsi, tujuan.
Keluarkan JSON:
{{"judul":"{rp['judul']}","tujuan":"tujuan khusus pertemuan ini",
"pendahuluan":[4-6 kalimat kegiatan],
"inti":[{{"tahap":"nama tahap sesuai skema","kegiatan":"aktivitas guru dan siswa","pengalaman":"memahami|mengaplikasi|merefleksi","prinsip":"mindful|meaningful|joyful"}}],
"penutup":[3-4 kalimat: simpulan, refleksi, tindak lanjut, doa],
"diferensiasi":{{"konten":"...","proses":"...","produk":"..."}}}}""", 5000))
        progress(0.2 + 0.4 * i / n, f"Pertemuan {i}/{n} selesai")
    progress(0.65, "Menyusun asesmen & soal…")
    npg, nes = c["n_pg"], c["n_esai"]
    a = ai.call_json(f"""{ctx}

Tujuan pembelajaran: {k['tujuan_pembelajaran']}
Susun asesmen. Soal harus sesuai materi, ada yang level penalaran (HOTS), tidak ambigu, satu kunci benar,
sebaran kunci A-D merata. JSON:
{{"asesmen_awal":"deskripsi asesmen diagnostik singkat",
"formatif":[{{"teknik":"observasi/penilaian diri/dll","instrumen":"...","deskripsi":"..."}}] (3-4),
"rubrik":[{{"aspek":"...","sangat_baik":"...","baik":"...","cukup":"...","kurang":"..."}}] (3-4 aspek),
"sumatif":{{"pg":[tepat {npg} objek {{"soal":"...","opsi":["teks A","teks B","teks C","teks D"],"kunci":"A|B|C|D"}}],
"esai":[tepat {nes} objek {{"soal":"...","kunci":"kriteria jawaban yang diharapkan"}}]}},
"pengayaan":"...","remedial":"...",
"refleksi_siswa":[4-5 pertanyaan],"refleksi_guru":[5-6 pertanyaan]}}""", 9000)
    progress(0.85, "Menyusun lampiran…")
    lamp = ai.call_json(f"""{ctx}

Susun lampiran. Bahan bacaan 3-5 paragraf ringkas yang akurat (tanpa angka/tahun/pasal yang tidak pasti).
Daftar pustaka: hanya sumber yang pasti ada (Buku Siswa/Guru mapel terkait Kemendikdasmen/Kemendikbudristek,
peraturan perundang-undangan yang relevan); jangan mengarang judul atau tahun, beri 2-4 butir umum. JSON:
{{"lkpd":{{"judul":"...","petunjuk":[3-5],"tugas":[3-5 tugas bernalar]}},
"bahan_bacaan":["paragraf",...],"glosarium":[{{"istilah":"...","arti":"..."}}] (5-8),
"daftar_pustaka":[...]}}""", 6000)
    progress(1.0, "Selesai")
    return {"ctx": c, "komponen": k, "pertemuan": pert, "asesmen": a, "lampiran": lamp}


REQUIRED = {
    "komponen": ["tujuan_pembelajaran", "pemahaman_bermakna", "pertanyaan_pemantik", "kompetensi_awal", "materi_esensial",
                 "target_peserta", "kemitraan", "lingkungan_belajar", "pemanfaatan_digital", "dimensi_profil"],
    "asesmen": ["asesmen_awal", "formatif", "rubrik", "sumatif", "pengayaan", "remedial", "refleksi_siswa", "refleksi_guru"],
    "lampiran": ["lkpd", "bahan_bacaan", "glosarium", "daftar_pustaka"],
}


def prompt_lengkap(c):
    total = c["jp_per_pertemuan"] * c["menit_jp"]
    return f"""Kamu perancang pembelajaran SMP berpengalaman (Kurikulum Merdeka, Pembelajaran Mendalam: berkesadaran/mindful,
bermakna/meaningful, menggembirakan/joyful; pengalaman belajar memahami-mengaplikasi-merefleksi). Bahasa Indonesia baku.
Jangan mengarang fakta, angka, tahun, pasal, kutipan, atau judul pustaka; jika ragu gunakan rumusan umum.

{_ctx_text(c)}

SKEMA KEGIATAN INTI dari guru (WAJIB diikuti urutannya; tiap tahap memuat aktivitas guru DAN siswa):
{c['skema'] or 'Gunakan sintaks standar model ' + c['model']}

Tiap pertemuan {total} menit: pendahuluan 10, inti {total - 20}, penutup 10. Kegiatan konkret, bisa dilaksanakan di kelas SMP,
dan tiap pertemuan membahas bagian materi yang berbeda secara berurutan.

KELUARKAN HANYA SATU BLOK JSON VALID (tanpa penjelasan di luar blok) dengan struktur persis:
{{"komponen":{{"tujuan_pembelajaran":[4-6 kalimat berawalan kata kerja operasional],"pemahaman_bermakna":"1 paragraf",
 "pertanyaan_pemantik":{{"mindful":[3-4],"meaningful":[3-4],"joyful":[2-3]}},"kompetensi_awal":[2-4],"materi_esensial":[3-6],
 "target_peserta":{{"reguler":"","tinggi":"","pendampingan":""}},"kemitraan":[2-3],"lingkungan_belajar":"","pemanfaatan_digital":"",
 "dimensi_profil":[{{"dimensi":"salah satu dimensi terpilih","wujud":"wujud nyata di bab ini"}}]}},
"pertemuan":[tepat {c['n_pertemuan']} objek: {{"judul":"","tujuan":"","pendahuluan":[4-6 kalimat],
 "inti":[{{"tahap":"nama tahap sesuai skema","kegiatan":"aktivitas guru dan siswa","pengalaman":"memahami|mengaplikasi|merefleksi","prinsip":"mindful|meaningful|joyful"}}],
 "penutup":[3-4 kalimat],"diferensiasi":{{"konten":"","proses":"","produk":""}}}}],
"asesmen":{{"asesmen_awal":"","formatif":[{{"teknik":"","instrumen":"","deskripsi":""}}](3-4),
 "rubrik":[{{"aspek":"","sangat_baik":"","baik":"","cukup":"","kurang":""}}](3-4),
 "sumatif":{{"pg":[tepat {c['n_pg']} objek {{"soal":"","opsi":["teks A","teks B","teks C","teks D"],"kunci":"A|B|C|D"}}],
 "esai":[tepat {c['n_esai']} objek {{"soal":"","kunci":"kriteria jawaban"}}]}},
 "pengayaan":"","remedial":"","refleksi_siswa":[4-5],"refleksi_guru":[5-6]}},
"lampiran":{{"lkpd":{{"judul":"","petunjuk":[3-5],"tugas":[3-5]}},"bahan_bacaan":["3-5 paragraf akurat"],
 "glosarium":[{{"istilah":"","arti":""}}](5-8),"daftar_pustaka":[2-4 butir umum, jangan mengarang judul/tahun]}}}}
Soal harus sesuai materi, ada yang level penalaran, satu kunci benar, sebaran kunci A-D merata."""


def parse_manual(txt, c):
    a, b = txt.find("{"), txt.rfind("}")
    data = json.loads(txt[a:b + 1])
    for top, keys in REQUIRED.items():
        miss = [k for k in keys if k not in data.get(top, {})]
        if top not in data or miss:
            raise ValueError(f"bagian '{top}' belum lengkap: {miss or 'tidak ada'}")
    if not data.get("pertemuan"):
        raise ValueError("bagian 'pertemuan' kosong")
    for i, p in enumerate(data["pertemuan"], 1):
        for k in ("judul", "tujuan", "pendahuluan", "inti", "penutup"):
            if k not in p:
                raise ValueError(f"pertemuan {i} tidak punya '{k}'")
    c = dict(c); c["n_pertemuan"] = len(data["pertemuan"])
    return {"ctx": c, "komponen": data["komponen"], "pertemuan": data["pertemuan"],
            "asesmen": data["asesmen"], "lampiran": data["lampiran"]}


def page_modul(store, cfg):
    st.header("Generate Modul Ajar")
    idn = store.identity()
    if not ai.available():
        st.info("Mode otomatis (berbayar) nonaktif karena API key tidak diisi. Mode gratis lewat chat Claude tetap bisa dipakai.")

    tab_gen, tab_riw = st.tabs(["Buat modul baru", "Riwayat modul"])

    with tab_gen:
        with st.expander("1 · Identitas modul", expanded=True):
            c1, c2, c3 = st.columns(3)
            kelas = c1.selectbox("Kelas", KELAS, index=KELAS.index(st.session_state.get("kelas_aktif", KELAS[0])), key="m_kelas")
            bab = c2.text_input("Bab / Tema", key="m_bab")
            semester = c3.selectbox("Semester", ["Genap", "Ganjil"], index=0 if idn.get("semester", "Genap") == "Genap" else 1)
            materi = st.text_area("Materi pokok", height=70, key="m_materi")
            c1, c2, c3 = st.columns(3)
            n_p = c1.number_input("Jumlah pertemuan", 1, 12, 6)
            jp = c2.number_input("JP per pertemuan", 1, 6, 2)
            menit = c3.number_input("Menit per JP", 30, 50, 40, help="SMP umumnya 40 menit; contoh modul Anda memakai 45.")
        with st.expander("2 · CP dan tujuan pembelajaran", expanded=True):
            cp = st.text_area("Capaian Pembelajaran (salin dari CP resmi mapel ini)", height=110, key="m_cp")
            tp = st.text_area("Tujuan pembelajaran (opsional — kosongkan agar AI yang menyusun)", height=80, key="m_tp")
        with st.expander("3 · Model, metode, media (diatur sendiri)", expanded=True):
            model = st.multiselect("Model pembelajaran", MODEL_PEMBELAJARAN, default=["Problem Based Learning"])
            model_lain = st.text_input("Model lain (opsional)")
            metode = st.text_input("Metode", "Diskusi kelompok, tanya jawab, presentasi, ceramah singkat")
            media = st.text_input("Media", "Slide presentasi, video, LKPD, papan tulis")
            sumber = st.text_input("Sumber belajar", "Buku Siswa dan Buku Guru Kurikulum Merdeka kelas ... , artikel/berita terpercaya")
            dimensi = st.multiselect("Dimensi Profil Lulusan", DIMENSI, default=DIMENSI[1:3] + [DIMENSI[4]])
        with st.expander("4 · Skema kegiatan inti (urutan langkah versi Anda)", expanded=True):
            sk = store.read("skema")
            pilih = st.selectbox("Skema tersimpan", ["(tulis baru)"] + sk["Nama"].tolist())
            isi0 = sk.loc[sk["Nama"] == pilih, "Isi"].iloc[0] if pilih != "(tulis baru)" else ""
            skema = st.text_area("Deskripsikan langkah-langkah kegiatan inti", isi0, height=160,
                                 placeholder=SKEMA_CONTOH, key=f"m_skema_{pilih}")
            cs1, cs2 = st.columns([2, 1])
            nm = cs1.text_input("Simpan skema ini dengan nama", placeholder="mis. PBL 6 langkah")
            if cs2.button("💾 Simpan skema") and nm.strip() and skema.strip():
                new = sk[sk["Nama"] != nm.strip()]
                store.write("skema", pd.concat(
                    [new, pd.DataFrame([{"Nama": nm.strip(), "Isi": skema}])], ignore_index=True))
                st.success("Skema tersimpan."); st.rerun()
        with st.expander("5 · Opsi lain"):
            c1, c2 = st.columns(2)
            n_pg = c1.number_input("Jumlah soal pilihan ganda", 0, 30, 10)
            n_es = c2.number_input("Jumlah soal uraian", 0, 10, 5)
            label = st.checkbox("Tampilkan label Mindful / Meaningful / Joyful di kegiatan inti", True)
            keb7 = st.checkbox("Sertakan pembiasaan 7 Kebiasaan Anak Indonesia Hebat", True)
            catatan = st.text_area("Catatan tambahan untuk AI (opsional)", height=60)

        def _c():
            return dict(mapel=cfg["nama"], kelas=kelas, semester=semester, bab=bab.strip(), materi=materi.strip(),
                        cp=cp.strip(), tp=tp.strip(), n_pertemuan=int(n_p), jp_per_pertemuan=int(jp), menit_jp=int(menit),
                        model=", ".join(model + ([model_lain] if model_lain else [])) or "sesuai kebutuhan",
                        metode=metode, media=media, sumber=sumber, dimensi=dimensi or DIMENSI[:3],
                        skema=skema.strip(), n_pg=int(n_pg), n_esai=int(n_es), label_prinsip=label,
                        kebiasaan7=keb7, catatan=catatan.strip(),
                        jumlah_siswa=int((store.siswa(kelas)["Kelas"] == kelas).sum()) or "")
        ok = bool(bab.strip() and materi.strip() and cp.strip())

        st.markdown("### Cara membuat modul")
        st.markdown("**Mode gratis** — pakai chat Claude (salin–tempel):")
        if st.button("📋 Buat prompt dari form di atas", type="primary"):
            if not ok:
                st.warning("Lengkapi minimal Bab/Tema, Materi pokok, dan CP.")
            else:
                st.session_state["prompt_manual"] = prompt_lengkap(_c())
                st.session_state["c_manual"] = _c()
        if st.session_state.get("prompt_manual"):
            st.caption("1) Salin prompt ini → tempel ke chat Claude (claude.ai) → tunggu sampai selesai.  "
                       "2) Salin jawaban JSON-nya → tempel di kotak bawah → klik Buat modul.")
            st.code(st.session_state["prompt_manual"], language=None, wrap_lines=True)
            hasil_txt = st.text_area("Tempel jawaban Claude (JSON) di sini", height=200, key="m_paste")
            if st.button("📄 Buat modul dari jawaban"):
                try:
                    st.session_state["modul_hasil"] = parse_manual(hasil_txt, st.session_state["c_manual"])
                    st.session_state["modul_id"] = uuid.uuid4().hex[:8]
                except Exception as e:  # noqa
                    st.error(f"Jawaban belum bisa dipakai: {e}. Minta Claude: 'kirim ulang JSON lengkap saja, dalam satu blok'.")

        if ai.available():
            st.markdown("**Mode otomatis** (AI di dalam app, berbayar):")
            if st.button("✨ Generate otomatis"):
                if not ok:
                    st.warning("Lengkapi minimal Bab/Tema, Materi pokok, dan CP.")
                else:
                    bar = st.progress(0.0, "Memulai…")
                    try:
                        st.session_state["modul_hasil"] = generate(_c(), lambda f, t: bar.progress(f, t))
                        st.session_state["modul_id"] = uuid.uuid4().hex[:8]
                    except Exception as e:  # noqa
                        st.error(f"Gagal generate: {e}")

        hasil = st.session_state.get("modul_hasil")
        if hasil:
            st.success("Modul siap. Unduh, lalu rapikan di Word bila perlu.")
            _tampil(hasil, idn, cfg)
            if st.button("💾 Simpan ke riwayat"):
                store.save_modul(st.session_state["modul_id"], hasil["ctx"]["bab"], hasil["ctx"]["kelas"],
                                 datetime.now().strftime("%Y-%m-%d %H:%M"), hasil)
                st.success("Tersimpan di riwayat.")

    with tab_riw:
        lst = store.list_modul()
        if lst.empty:
            st.info("Belum ada modul tersimpan.")
        else:
            opsi = {f"{r.Judul} (kelas {r.Kelas}, {r.Dibuat})": r.ID for r in lst.itertuples()}
            pil = st.selectbox("Pilih modul", list(opsi))
            if st.button("Buka modul ini"):
                st.session_state["modul_hasil"] = store.load_modul(opsi[pil])
                st.session_state["modul_id"] = opsi[pil]
                st.success("Dimuat — lihat tab 'Buat modul baru' untuk unduh.")


def _tampil(h, idn, cfg):
    c = h["ctx"]
    fn = f"Modul_Ajar_{cfg['singkat']}_Kelas{c['kelas']}_{c['bab'][:30].replace(' ', '_')}.docx"
    st.download_button("⬇️ Unduh modul ajar (.docx)", build_modul(h, idn, cfg["nama"]), fn,
                       "application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")
    with st.expander("Pratinjau ringkas"):
        st.markdown("**Tujuan pembelajaran**")
        for t in h["komponen"]["tujuan_pembelajaran"]: st.markdown(f"- {t}")
        for i, p in enumerate(h["pertemuan"], 1):
            st.markdown(f"**Pertemuan {i} — {p['judul']}**")
            for s in p["inti"]: st.markdown(f"- *{s['tahap']}*: {s['kegiatan']}")
