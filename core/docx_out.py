"""Pembuat file Word: modul ajar, prota, prosem."""
import io

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .config import BULAN, KEBIASAAN_7

LABEL = {"mindful": "Berkesadaran/Mindful", "meaningful": "Bermakna/Meaningful",
         "joyful": "Menggembirakan/Joyful"}
PENGALAMAN = {"memahami": "Memahami", "mengaplikasi": "Mengaplikasi", "merefleksi": "Merefleksi"}


# ---------------------------------------------------------------- dasar
def new_doc(landscape=False):
    d = Document()
    s = d.sections[0]
    if landscape:
        s.orientation = WD_ORIENT.LANDSCAPE
        s.page_width, s.page_height = Cm(29.7), Cm(21)
    else:
        s.page_width, s.page_height = Cm(21), Cm(29.7)
    for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(s, m, Cm(2))
    n = d.styles["Normal"]
    n.font.name = "Times New Roman"
    n.font.size = Pt(11)
    n.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    return d


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def P(d, text="", bold=False, italic=False, size=None, align=None, color=None, space=4):
    p = d.add_paragraph()
    r = p.add_run(str(text))
    r.bold, r.italic = bold, italic
    if size: r.font.size = Pt(size)
    if color: r.font.color.rgb = RGBColor.from_string(color)
    if align == "c": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if align == "j": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(space)
    return p


def H(d, text, level=1):
    size = {1: 13, 2: 12, 3: 11}[level]
    p = P(d, text, bold=True, size=size, space=4)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.keep_with_next = True
    return p


def bullets(d, items, style="List Bullet"):
    for it in items:
        p = d.add_paragraph(style=style)
        p.add_run(str(it))
        p.paragraph_format.space_after = Pt(2)


def numbered(d, items):
    for i, it in enumerate(items, 1):
        p = d.add_paragraph()
        p.add_run(f"{i}. {it}")
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.first_line_indent = Cm(-0.6)
        p.paragraph_format.space_after = Pt(2)


def cell_write(cell, lines, bold=False, size=None):
    """lines: list of str | (str, tag)."""
    first = True
    for ln in lines if isinstance(lines, list) else [lines]:
        p = cell.paragraphs[0] if first else cell.add_paragraph()
        first = False
        txt, tag = ln if isinstance(ln, tuple) else (ln, "")
        r = p.add_run(str(txt)); r.bold = bold
        if size: r.font.size = Pt(size)
        if tag:
            r2 = p.add_run(f"  ({tag})"); r2.italic = True
            r2.font.color.rgb = RGBColor(0x1F, 0x4E, 0x9A)
            if size: r2.font.size = Pt(size)
        p.paragraph_format.space_after = Pt(2)


def table(d, header, rows, widths=None, head_color="C6D9F1", size=10):
    t = d.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        cell_write(t.rows[0].cells[i], [h], bold=True, size=size)
        shade(t.rows[0].cells[i], head_color)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cell_write(cells[i], v if isinstance(v, list) else [v], size=size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    d.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def kv_table(d, pairs):
    t = d.add_table(rows=0, cols=2)
    t.style = "Table Grid"
    for k, v in pairs:
        c = t.add_row().cells
        cell_write(c[0], [k], bold=True); shade(c[0], "EAF1FB")
        cell_write(c[1], v if isinstance(v, list) else [str(v)])
        c[0].width, c[1].width = Cm(5), Cm(12)
    d.add_paragraph()


def tanda_tangan(d, idn):
    d.add_paragraph()
    t = d.add_table(rows=1, cols=2)
    kota = idn.get("kota", "")
    cell_write(t.rows[0].cells[0], ["Mengetahui,", "Kepala Sekolah", "", "", "", idn.get("kepsek", "…………………"),
                                    f"NIP. {idn.get('nip_kepsek', '…………')}"])
    cell_write(t.rows[0].cells[1], [f"{kota}, ………………………", "Guru Mata Pelajaran", "", "", "",
                                    idn.get("nama", "…………………"), f"NIP. {idn.get('nip', '…………')}"])


def to_bytes(d):
    b = io.BytesIO(); d.save(b); return b.getvalue()


# ---------------------------------------------------------------- MODUL AJAR
def build_modul(m: dict, idn: dict, mapel: str) -> bytes:
    c, k, A, L = m["ctx"], m["komponen"], m["asesmen"], m["lampiran"]
    d = new_doc()
    # sampul
    for _ in range(4): P(d)
    P(d, "MODUL AJAR", True, size=20, align="c")
    P(d, mapel.upper(), True, size=16, align="c")
    P(d, f"KELAS {c['kelas']} • FASE D", True, size=14, align="c")
    P(d, "Kurikulum Merdeka — Pembelajaran Mendalam (Deep Learning)", italic=True, size=12, align="c")
    P(d); P(d, c["bab"], True, size=15, align="c"); P(d)
    P(d, f"{c['n_pertemuan']} Pertemuan × {c['jp_per_pertemuan']} JP", size=12, align="c")
    for _ in range(5): P(d)
    P(d, "PENYUSUN", True, align="c"); P(d, idn.get("nama", "…………………"), align="c")
    P(d, idn.get("sekolah", ""), align="c"); P(d, f"Tahun Ajaran {idn.get('tahun_ajaran', '')}", align="c")
    d.add_page_break()

    # I. INFORMASI UMUM
    H(d, "I. INFORMASI UMUM")
    H(d, "A. Identitas Modul", 2)
    kv_table(d, [
        ("Nama Penyusun", idn.get("nama", "")), ("Satuan Pendidikan", idn.get("sekolah", "")),
        ("Tahun Penyusunan", idn.get("tahun_ajaran", "")), ("Mata Pelajaran", mapel),
        ("Fase / Kelas / Semester", f"D / {c['kelas']} / {idn.get('semester', c.get('semester', ''))}"),
        ("Bab / Tema", c["bab"]), ("Materi Pokok", c["materi"]),
        ("Alokasi Waktu", f"{c['n_pertemuan']} pertemuan × {c['jp_per_pertemuan']} JP × {c['menit_jp']} menit = "
                          f"{c['n_pertemuan'] * c['jp_per_pertemuan'] * c['menit_jp']} menit"),
        ("Jumlah Peserta Didik", c.get("jumlah_siswa", "")),
    ])
    H(d, "B. Capaian Pembelajaran", 2); P(d, c["cp"], align="j")
    H(d, "C. Dimensi Profil Lulusan", 2)
    table(d, ["Dimensi", "Wujud dalam pembelajaran"], [[x["dimensi"], x["wujud"]] for x in k["dimensi_profil"]],
          widths=[5.5, 11.5])
    H(d, "D. Kompetensi Awal", 2); bullets(d, k["kompetensi_awal"])
    H(d, "E. Sarana dan Prasarana", 2)
    kv_table(d, [("Media", c["media"]), ("Sumber belajar", c["sumber"]),
                 ("Lingkungan belajar", k["lingkungan_belajar"]),
                 ("Pemanfaatan digital", k["pemanfaatan_digital"]),
                 ("Kemitraan pembelajaran", "; ".join(k["kemitraan"]))])
    H(d, "F. Materi Esensial", 2); bullets(d, k["materi_esensial"])
    H(d, "G. Target Peserta Didik", 2)
    bullets(d, [f"Reguler/tipikal: {k['target_peserta']['reguler']}",
                f"Pencapaian tinggi: {k['target_peserta']['tinggi']}",
                f"Memerlukan pendampingan: {k['target_peserta']['pendampingan']}"])
    H(d, "H. Model, Metode, dan Pendekatan Pembelajaran", 2)
    kv_table(d, [("Model", c["model"]), ("Metode", c["metode"]),
                 ("Pendekatan", "Pembelajaran Mendalam: berkesadaran, bermakna, menggembirakan; "
                                "pengalaman belajar memahami – mengaplikasi – merefleksi")])
    if c.get("kebiasaan7"):
        H(d, "I. Pembiasaan 7 Kebiasaan Anak Indonesia Hebat", 2)
        P(d, "Di awal pembelajaran guru dapat menanyakan pelaksanaan kebiasaan berikut:")
        bullets(d, [f"{a} — {b}" for a, b in KEBIASAAN_7])

    # II. KOMPONEN INTI
    d.add_page_break()
    H(d, "II. KOMPONEN INTI")
    H(d, "A. Tujuan Pembelajaran", 2); numbered(d, k["tujuan_pembelajaran"])
    H(d, "B. Pemahaman Bermakna", 2); P(d, k["pemahaman_bermakna"], align="j")
    H(d, "C. Pertanyaan Pemantik", 2)
    for key, title in (("mindful", "Berkesadaran (Mindful Learning)"), ("meaningful", "Bermakna (Meaningful Learning)"),
                       ("joyful", "Menggembirakan (Joyful Learning)")):
        if k["pertanyaan_pemantik"].get(key):
            P(d, title, bold=True); numbered(d, k["pertanyaan_pemantik"][key])
    H(d, "D. Persiapan Pembelajaran", 2)
    bullets(d, ["Menyiapkan bahan bacaan/media (buku, video, tautan) dan lembar kerja peserta didik.",
                "Menyiapkan alat dan bahan, pengaturan kelas, serta instrumen asesmen.",
                "Memetakan kebutuhan belajar peserta didik (diferensiasi konten, proses, produk)."])
    H(d, "E. Kegiatan Pembelajaran", 2)
    for i, pt in enumerate(m["pertemuan"], 1):
        inti_min = c["jp_per_pertemuan"] * c["menit_jp"] - 20
        t = d.add_table(rows=1, cols=2); t.style = "Table Grid"
        cell_write(t.rows[0].cells[0], [f"Pembelajaran ke-{i} ({c['jp_per_pertemuan']} JP × {c['menit_jp']} menit): "
                                        f"{pt['judul']}", f"Tujuan: {pt['tujuan']}"], bold=True)
        cell_write(t.rows[0].cells[1], ["Alokasi Waktu"], bold=True)
        for cc in t.rows[0].cells: shade(cc, "D8E4BC")

        def row(title, menit, lines, color=None):
            cells = t.add_row().cells
            cell_write(cells[0], [(title, "")] + [(f"• {x[0]}", x[1]) if isinstance(x, tuple) else f"• {x}"
                                                  for x in lines])
            cells[0].paragraphs[0].runs[0].bold = True
            cell_write(cells[1], [f"{menit} menit"], bold=True)
            if color: shade(cells[0], color); shade(cells[1], color)
        row("KEGIATAN PENDAHULUAN", 10, pt["pendahuluan"])
        inti = []
        for s in pt["inti"]:
            tags = [PENGALAMAN.get(s.get("pengalaman", ""), "")]
            if c.get("label_prinsip") and s.get("prinsip") in LABEL: tags.append(LABEL[s["prinsip"]])
            inti.append((f"{s['tahap']}: {s['kegiatan']}", " · ".join(x for x in tags if x)))
        row("KEGIATAN INTI", inti_min, inti, "DCE6F1")
        dif = pt.get("diferensiasi", {})
        row("CATATAN GURU", "—", [f"Diferensiasi konten: {dif.get('konten', '-')}",
                                  f"Diferensiasi proses: {dif.get('proses', '-')}",
                                  f"Diferensiasi produk: {dif.get('produk', '-')}",
                                  "Amati sikap: disiplin, percaya diri, jujur, tangguh, rasa ingin tahu, peduli lingkungan."],
            "FFFF99")
        row("KEGIATAN PENUTUP", 10, pt["penutup"])
        for r_ in t.rows:
            r_.cells[0].width, r_.cells[1].width = Cm(14), Cm(3)
        d.add_paragraph()
    H(d, "F. Refleksi", 2)
    P(d, "Refleksi Peserta Didik", bold=True); numbered(d, A["refleksi_siswa"])
    P(d, "Refleksi Guru", bold=True); numbered(d, A["refleksi_guru"])

    # ASESMEN
    d.add_page_break()
    H(d, "III. ASESMEN")
    H(d, "A. Asesmen Awal (diagnostik)", 2); P(d, A["asesmen_awal"], align="j")
    H(d, "B. Asesmen Formatif", 2)
    table(d, ["Teknik", "Instrumen", "Keterangan"],
          [[x["teknik"], x["instrumen"], x["deskripsi"]] for x in A["formatif"]], widths=[3.5, 4.5, 9])
    P(d, "Rubrik Penilaian Formatif (skala 4 = Sangat baik, 3 = Baik, 2 = Cukup, 1 = Perlu bimbingan)", bold=True)
    table(d, ["Aspek", "4", "3", "2", "1"],
          [[r["aspek"], r["sangat_baik"], r["baik"], r["cukup"], r["kurang"]] for r in A["rubrik"]],
          widths=[3, 3.5, 3.5, 3.5, 3.5], size=9)
    H(d, "C. Asesmen Sumatif", 2)
    pg, es = A["sumatif"]["pg"], A["sumatif"]["esai"]
    P(d, "Nama: ……………………  Kelas: ………  Tanggal: …………………", italic=True)
    P(d, "A. Pilihan Ganda — pilih satu jawaban yang paling tepat!", bold=True)
    for i, q in enumerate(pg, 1):
        P(d, f"{i}. {q['soal']}", space=1)
        for o, txt in zip("ABCD", q["opsi"]):
            p = P(d, f"{o}. {txt}", space=0); p.paragraph_format.left_indent = Cm(0.8)
        P(d, "", space=2)
    if es:
        P(d, "B. Uraian — jawablah dengan jelas!", bold=True)
        for i, q in enumerate(es, 1): P(d, f"{i}. {q['soal']}", space=4)
    H(d, "Kunci Jawaban dan Pedoman Penskoran", 3)
    table(d, ["No", "Kunci"], [[i, q["kunci"]] for i, q in enumerate(pg, 1)], widths=[2, 4])
    if es:
        table(d, ["No uraian", "Jawaban/kriteria yang diharapkan"], [[i, q["kunci"]] for i, q in enumerate(es, 1)],
              widths=[3, 14])
    skor_pg = round(50 / max(len(pg), 1), 2); skor_es = round(50 / max(len(es), 1), 2) if es else 0
    bullets(d, [f"Pilihan ganda: benar = {skor_pg} poin per butir (total 50).",
                f"Uraian: skor maksimal {skor_es} per butir (total 50), dinilai: lengkap & benar = 100%; "
                "benar tetapi kurang lengkap = 70%; sebagian besar salah = 50%; tidak menjawab/salah = 0.",
                "Nilai akhir = skor pilihan ganda + skor uraian (maksimal 100)."])
    H(d, "D. Pengayaan dan Remedial", 2)
    P(d, "Pengayaan: " + A["pengayaan"], align="j"); P(d, "Remedial: " + A["remedial"], align="j")

    # LAMPIRAN
    d.add_page_break()
    H(d, "IV. LAMPIRAN")
    lk = L["lkpd"]
    H(d, f"A. Lembar Kerja Peserta Didik (LKPD): {lk['judul']}", 2)
    P(d, "Nama: ……………………  Kelas: ………  Tanggal: …………………", italic=True)
    P(d, "Petunjuk", bold=True); numbered(d, lk["petunjuk"])
    P(d, "Tugas", bold=True); numbered(d, lk["tugas"])
    H(d, "B. Lembar Observasi Kegiatan Pembelajaran", 2)
    aspek = [("Pendahuluan", ["Berdoa sebelum belajar", "Mencermati penjelasan guru"]),
             ("Kegiatan inti", ["Keaktifan dalam pembelajaran", "Kerja sama dalam diskusi kelompok", "Mengajukan pertanyaan",
                                "Menyampaikan pendapat", "Menghargai pendapat orang lain", "Menggunakan media/alat pembelajaran"]),
             ("Penutup", ["Menyampaikan refleksi", "Mengerjakan latihan secara mandiri", "Memperhatikan arahan guru"])]
    rows = []
    for g, items in aspek:
        rows.append([g, "", "", "", ""])
        rows += [[f"   {x}", "", "", "", ""] for x in items]
    P(d, "Nama siswa: ………………  Kelas: ………  Pertemuan ke-: ………  Tanggal: …………", italic=True)
    table(d, ["Aspek yang diamati", "1 Kurang", "2 Cukup", "3 Baik", "4 Sangat baik"], rows, widths=[7, 2.5, 2.5, 2.5, 2.5], size=9)
    P(d, "Nilai = skor yang diperoleh ÷ 44 × 100")
    H(d, "C. Bahan Bacaan Guru dan Peserta Didik", 2)
    for para in L["bahan_bacaan"]: P(d, para, align="j")
    H(d, "D. Glosarium", 2)
    for g in L["glosarium"]:
        p = d.add_paragraph(); r = p.add_run(g["istilah"]); r.bold = True; p.add_run(f": {g['arti']}")
        p.paragraph_format.space_after = Pt(2)
    H(d, "E. Daftar Pustaka", 2)
    P(d, "(Verifikasi kembali sebelum digunakan.)", italic=True, size=9)
    bullets(d, L["daftar_pustaka"])
    tanda_tangan(d, idn)
    return to_bytes(d)


# ---------------------------------------------------------------- PROTA / PROSEM
def _head(d, judul, idn, mapel, kelas_txt, extra=""):
    P(d, judul, True, size=14, align="c", space=0)
    P(d, f"{mapel} — Kelas {kelas_txt} (Fase D)", True, align="c", space=0)
    P(d, f"{idn.get('sekolah', '')} • Tahun Ajaran {idn.get('tahun_ajaran', '')}{extra}", align="c")


def build_prota(idn, mapel, tingkat, df) -> bytes:
    d = new_doc()
    _head(d, "PROGRAM TAHUNAN (PROTA)", idn, mapel, tingkat)
    rows, nomor = [], 0
    for sem in ("Ganjil", "Genap"):
        sub = df[df["Semester"] == sem]
        if sub.empty: continue
        rows.append([[f"Semester {sem}"], "", "", ""])
        for _, r in sub.iterrows():
            nomor += 1
            rows.append([str(nomor), r["Materi"], r["TP"], str(int(r["JP"]))])
        rows.append(["", [f"Jumlah JP semester {sem}"], "", str(int(sub["JP"].sum()))])
    rows.append(["", ["JUMLAH JP SETAHUN"], "", str(int(df["JP"].sum()))])
    table(d, ["No", "Bab / Materi", "Tujuan Pembelajaran", "Alokasi (JP)"], rows, widths=[1.2, 5.5, 8, 2.3])
    tanda_tangan(d, idn)
    return to_bytes(d)


def build_prosem(idn, mapel, tingkat, semester, weeks, rows) -> bytes:
    """weeks: list of dict(bulan, tahun, ke, efektif, label) ; rows: list of (materi, total_jp, {week_idx: jp})."""
    d = new_doc(landscape=True)
    _head(d, "PROGRAM SEMESTER (PROSEM)", idn, mapel, tingkat, f" • Semester {semester}")
    n = len(weeks)
    t = d.add_table(rows=2, cols=3 + n + 1); t.style = "Table Grid"
    for i, h in enumerate(["No", "Bab / Materi", "JP"]):
        a = t.cell(0, i).merge(t.cell(1, i)); cell_write(a, [h], bold=True, size=8); shade(a, "C6D9F1")
    i = 0
    while i < n:
        j = i
        while j + 1 < n and (weeks[j + 1]["bulan"], weeks[j + 1]["tahun"]) == (weeks[i]["bulan"], weeks[i]["tahun"]): j += 1
        a = t.cell(0, 3 + i).merge(t.cell(0, 3 + j)); cell_write(a, [BULAN[weeks[i]["bulan"]]], bold=True, size=8)
        shade(a, "C6D9F1"); a.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        i = j + 1
    for i, w in enumerate(weeks):
        cell_write(t.cell(1, 3 + i), [str(w["ke"])], bold=True, size=8)
        shade(t.cell(1, 3 + i), "C6D9F1" if w["efektif"] else "BFBFBF")
    a = t.cell(0, 3 + n).merge(t.cell(1, 3 + n)); cell_write(a, ["Ket."], bold=True, size=8); shade(a, "C6D9F1")
    for no, (materi, jp, alloc) in enumerate(rows, 1):
        c = t.add_row().cells
        cell_write(c[0], [str(no)], size=8); cell_write(c[1], [materi], size=8); cell_write(c[2], [str(jp)], size=8)
        for i, w in enumerate(weeks):
            if not w["efektif"]: shade(c[3 + i], "BFBFBF")
            elif i in alloc: cell_write(c[3 + i], [str(alloc[i])], size=8); shade(c[3 + i], "FFF2CC")
    for row in t.rows:
        row.cells[0].width, row.cells[1].width, row.cells[2].width = Cm(0.8), Cm(6), Cm(0.9)
        for i in range(n): row.cells[3 + i].width = Cm(0.55)
    P(d, "Keterangan: sel abu-abu = minggu tidak efektif (libur/kegiatan sekolah); angka = JP yang dialokasikan pada minggu tersebut.", size=9)
    tanda_tangan(d, idn)
    return to_bytes(d)
