SUBJECTS = {
    "IPS": {"nama": "Ilmu Pengetahuan Sosial (IPS)", "singkat": "IPS", "jp": 4, "ikon": "🌏"},
    "PPKN": {"nama": "Pendidikan Pancasila (PPKn)", "singkat": "PPKn", "jp": 3, "ikon": "🇮🇩"},
}
KELAS = ["7A", "7B", "8", "9"]
STATUS = ["H", "I", "S", "A"]
STATUS_LABEL = {"H": "Hadir", "I": "Izin", "S": "Sakit", "A": "Alpha"}
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
DIMENSI = [
    "Keimanan dan Ketakwaan terhadap Tuhan YME",
    "Kewargaan",
    "Penalaran Kritis",
    "Kreativitas",
    "Kolaborasi",
    "Kemandirian",
    "Kesehatan",
    "Komunikasi",
]
MODEL_PEMBELAJARAN = [
    "Problem Based Learning", "Project Based Learning", "Discovery Learning", "Inquiry Learning",
    "Cooperative Learning tipe Jigsaw", "Group Investigation", "Active Debate", "Station Learning",
    "Pembelajaran Berbasis Kasus", "Role Playing",
]
KEBIASAAN_7 = [
    ("Bangun pagi", "Bagaimana kamu memulai hari dengan baik?"),
    ("Beribadah", "Apa yang kamu lakukan untuk mengingat Tuhan setiap hari?"),
    ("Berolahraga", "Mengapa penting berolahraga setiap hari?"),
    ("Gemar belajar", "Apa hal yang kamu pelajari hari ini?"),
    ("Makan sehat dan bergizi", "Makanan sehat apa yang kamu konsumsi?"),
    ("Bermasyarakat", "Apa yang kamu lakukan untuk membantu teman atau keluarga?"),
    ("Tidur cepat", "Mengapa tidur yang cukup itu penting?"),
]


def tingkat(kelas: str) -> str:
    return str(kelas)[0]
