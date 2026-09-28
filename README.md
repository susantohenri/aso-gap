# aso-gap

Tool kecil untuk mencari **celah keyword (keyword gap)** di Google Play Store.

Cara kerjanya:

1. Ambil banyak *search suggestion* langsung dari kolom pencarian Play Store menggunakan Playwright (dengan teknik alphabet expansion: `seed a`, `seed b`, ... `seed z`).
2. Cek satu per satu di Google Play via `google-play-scraper`: berapa aplikasi yang muncul untuk keyword tersebut.
3. Simpan keyword dengan hasil **0** atau **sangat sedikit** ke CSV. Ini kandidat niche yang belum digarap kompetitor.

## Fitur Utama

- **Real Play Store Suggestions**: Saran diambil langsung dari kolom pencarian Play Store web via Playwright (bukan Google Search biasa).
- **Target Global & Regional**: Default ke pasar global Play Store (`en-us`), dan mudah diarahkan ke negara/bahasa lain via argumen CLI.
- **Auto-Save & Resume**: Hasil disimpan berkala ke CSV tiap kali satu kata kunci selesai diperiksa. Jika terputus di tengah jalan, script otomatis melanjutkan tanpa mengulang dari awal.
- **Validasi Seed Input**: Menolak query kosong agar tidak membuang waktu mengambil saran acak yang tidak relevan.
- **Mode Tes Cepat (`--test`)**: Memverifikasi koneksi Playwright dan scraper dalam hitungan detik tanpa scraping penuh.

## Kebutuhan

- Python 3.9+
- Koneksi internet
- Browser Chromium untuk Playwright

## Setup (Windows 11)

Buka terminal di folder repo ini (klik kanan di folder, **Open in Terminal**), lalu:

```powershell
# 1. Buat virtual environment
python -m venv venv

# 2. Aktifkan
venv\Scripts\activate

# 3. Install dependency
pip install -r requirements.txt

# 4. Install Chromium browser untuk Playwright
playwright install chromium
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
playwright install chromium
```

## Cara Pakai

Jalankan langsung melalui command line dengan menyertakan kata kunci utama (*seed*):

```powershell
# Contoh pencarian pasar Global (default: en-us)
python scrape.py "photo editor"

# Contoh pencarian pasar Indonesia
python scrape.py "editor foto" --hl id --gl id

# Contoh dengan kata tambahan
python scrape.py "fitness tracker" --extra "app"
```

### Opsi CLI

| Argumen / Opsi | Keterangan | Default | Contoh |
|---|---|---|---|
| `seed` *(wajib)* | Kata kunci utama / niche yang dicari | - | `"photo editor"` |
| `--extra` | Kata tambahan pada query | `""` | `--extra "app"` |
| `--hl` | Bahasa Play Store (*Host Language*) | `"en"` | `--hl id` |
| `--gl` | Negara katalog Play Store (*Geolocation*) | `"us"` | `--gl id` |
| `--max-few` | Batas maksimal hasil untuk `hasil_sedikit.csv` | `3` | `--max-few 5` |
| `--headful` | Tampilkan jendela browser saat scraping | `False` (headless) | `--headful` |
| `--test` | Tes cepat 1 query tanpa scraping 27 query | `False` | `--test` |

## Tes Cepat (`--test`)

Untuk mengecek apakah koneksi Playwright ke Play Store dan scraper berfungsi dengan baik tanpa menunggu seluruh 27 query selesai:

```powershell
python scrape.py "photo editor" --test
```

Jika sukses, terminal akan menampilkan `Status: OK` beserta daftar saran kata kunci dan jumlah aplikasi yang terdeteksi.

## Output

Setiap file CSV memiliki 2 kolom sederhana: `keyword` dan `jumlah_hasil`:

| File | Isi |
|---|---|
| `hasil_semua.csv` | Semua keyword beserta jumlah hasilnya (`-1` berarti error saat dicek) |
| `hasil_nol.csv` | Keyword dengan hasil persis 0 |
| `hasil_sedikit.csv` | Keyword dengan hasil 0 sampai `max-few` |

> **Catatan Resume**: Jika file `hasil_semua.csv` sudah ada, script akan otomatis mendeteksi keyword yang sudah selesai diproses dan melewatinya. Untuk memulai pencarian baru dari nol, hapus file CSV hasil sebelum menjalankan script.

## Tips

- **Jeda Otomatis**: Script sudah dilengkapi jeda acak alami (1.5-3.5 detik) antar query untuk menghindari pemblokiran/captcha dari Google.
- Coba beberapa seed berbeda dan gabungkan hasilnya.
- Hasil 0 belum tentu peluang bagus. Cek juga apakah ada orang yang benar-benar mencari keyword itu (volume pencarian), bukan sekadar tidak ada kompetitor.

## Struktur Repo

```
aso-gap/
├── scrape.py          # script utama (CLI, Playwright suggestion, scraper, & mode --test)
├── requirements.txt   # daftar dependency Python
├── .gitignore         # aturan pengabaian file git (venv, cache, CSV hasil)
└── README.md          # dokumentasi
```

## Lisensi & Disclaimer

Proyek ini memakai halaman web publik Google Play Store yang tidak memiliki API publik resmi. Gunakan dengan wajar, patuhi ketentuan layanan Google, dan jangan dipakai untuk scraping dalam skala berlebihan.
