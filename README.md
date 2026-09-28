# aso-gap

Tool kecil untuk mencari **celah keyword (keyword gap)** di Google Play Store.

Cara kerjanya:

1. Ambil banyak *search suggestion* dari seed keyword (pakai teknik alphabet expansion: `seed a`, `seed b`, ... `seed z`).
2. Cek satu per satu di Google Play: berapa app yang muncul untuk keyword itu.
3. Simpan keyword dengan hasil **0** atau **sangat sedikit** ke CSV. Ini kandidat niche yang belum digarap.

## Catatan penting

- Suggestion diambil dari **autocomplete Google Search umum** (`suggestqueries.google.com`), bukan dari kolom search Play Store. Endpoint autocomplete Play Store yang lama sudah mati (404). Hasilnya kurang lebih mirip, tapi tidak identik. Kata tambahan seperti `aplikasi` di `EXTRA` membantu menggeser suggestion ke arah app.
- Play Store hampir selalu mengembalikan sesuatu untuk query apa pun, jadi hasil **benar-benar 0** itu langka. Karena itu ada juga output `hasil_sedikit.csv` (hasil 0 sampai N).
- Endpoint yang dipakai tidak resmi dan bisa berubah kapan saja. Kalau script berhenti jalan, cek dulu endpoint-nya.

## Kebutuhan

- Python 3.9+
- Koneksi internet

## Setup (Windows 11)

Buka terminal di folder repo ini (klik kanan di folder, **Open in Terminal**), lalu:

```powershell
# 1. Buat virtual environment
python -m venv venv

# 2. Aktifkan
venv\Scripts\activate

# 3. Install dependency
pip install -r requirements.txt
```

Kalau muncul error *execution policy* saat aktivasi di PowerShell, jalankan sekali:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

lalu ulangi langkah 2.

### Setup di macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Cara pakai

1. Buka `scrape.py`, atur konfigurasi di bagian atas file:

   | Variabel | Fungsi | Contoh |
   |---|---|---|
   | `SEED` | Keyword utama / niche yang dicari | `"editor foto"` |
   | `EXTRA` | Kata tambahan biar suggestion condong ke app. Kosongkan `""` untuk menonaktifkan | `"aplikasi"` |
   | `MAX_HASIL_DIANGGAP_SEDIKIT` | Batas atas jumlah hasil untuk masuk `hasil_sedikit.csv` | `3` |

2. Jalankan:

   ```powershell
   python scrape.py
   ```

3. Tunggu sampai muncul tulisan `Selesai`. Estimasi: sekitar 1,5 detik per keyword ditambah 27 request suggestion di awal. Untuk 150 keyword kira-kira 4-5 menit.

## Output

| File | Isi |
|---|---|
| `hasil_semua.csv` | Semua keyword beserta jumlah hasilnya (`-1` berarti error saat dicek) |
| `hasil_nol.csv` | Keyword dengan hasil persis 0 |
| `hasil_sedikit.csv` | Keyword dengan hasil 0 sampai `MAX_HASIL_DIANGGAP_SEDIKIT` |

## Cek endpoint (troubleshooting)

Kalau script tidak menghasilkan suggestion sama sekali, tes endpoint-nya dulu:

```powershell
python test.py
```

Harusnya muncul `Status: 200` dan daftar keyword. Kalau status 404 atau kosong, endpoint sudah berubah dan perlu diganti.

## Tips

- **Jangan terlalu cepat.** Jeda `time.sleep` di script sengaja dipasang supaya tidak kena rate limit atau captcha. Kalau mau dipercepat, naikkan risiko diblok sementara.
- Coba beberapa seed berbeda dan gabungkan hasilnya.
- Hasil 0 belum tentu peluang bagus. Cek juga apakah ada orang yang benar-benar mencari keyword itu (volume), bukan cuma tidak ada kompetitor.

## Struktur repo

```
aso-gap/
├── scrape.py          # script utama
├── test.py            # tes endpoint suggestion
├── requirements.txt
├── .gitignore
└── README.md
```

## Lisensi & disclaimer

Proyek ini memakai endpoint dan halaman publik Google yang tidak punya API resmi. Gunakan dengan wajar, patuhi ketentuan layanan Google, dan jangan dipakai untuk scraping dalam skala besar.
