# aso-gap

Tool untuk mencari **celah kata kunci (keyword gap)** dan membedah **relevansi kompetitor asli** di Google Play Store.

Cara kerjanya:

1. Mengambil *search suggestions* organik langsung dari kolom pencarian Play Store web via Playwright menggunakan teknik ekspansi alfabet (`seed`, `seed a`, `seed b`, ... `seed z`).
2. Menangkap variasi kata kunci alami pengguna (termasuk permutasi kata / inversi kata seperti *"zombie fortnite 4"* dari query *"fortnite"*).
3. Memeriksa hasil pencarian Play Store via `google-play-scraper` dan melakukan **analisis relevansi pintar**: memisahkan kompetitor nyata dari aplikasi *filler* algoritma Play Store (seperti Uber/Teams/Paramount+ yang sering disodorkan Google saat hasil asli sedikit).
4. Menyimpan daftar kata kunci, jumlah total hasil, jumlah kompetitor relevan, serta daftar seluruh nama aplikasi relevan ke file CSV otomatis per-*seed*.

## Fitur Utama

- **Relevance & True Competition Filter**: Membedakan antara aplikasi yang benar-benar relevan (berdasarkan Title, App ID, dan Snippet) dengan aplikasi *filler* algoritma Play Store.
- **Daftar Seluruh Kompetitor Relevan**: Semua aplikasi relevan dicatat lengkap (Judul & Package ID) di kolom CSV.
- **Penamaan File Otomatis Per-Seed**: Output file otomatis dinamai sesuai *seed* (misal: `hasil_photo_editor_semua.csv`), sehingga tidak akan bertabrakan antar pencarian tanpa perlu hapus file manual.
- **Otomatis Fresh Start & Fitur `--resume`**: Setiap kali menjalankan kata kunci baru, script otomatis mulai bersih (*fresh*). Jika proses terhenti di tengah jalan, cukup tambahkan argumen `--resume` untuk melanjutkan tanpa mengulang.
- **Real Play Store Suggestions**: Saran diambil langsung dari antarmuka Play Store web via Playwright secara dinamis.
- **Target Global & Regional**: Default ke pasar global Play Store (`en-us`), dan mudah diarahkan ke negara/bahasa lain via argumen `--hl` dan `--gl`.
- **Mode Tes Cepat (`--test`)**: Memverifikasi alur Playwright, scraper, dan filter relevansi dalam hitungan detik untuk 1 query.

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

# Melanjutkan scraping sebelumnya yang sempat terhenti
python scrape.py "photo editor" --resume
```

### Opsi CLI

| Argumen / Opsi | Keterangan | Default | Contoh |
|---|---|---|---|
| `seed` *(wajib)* | Kata kunci utama / niche yang dicari | - | `"photo editor"` |
| `--extra` | Kata tambahan pada query | `""` | `--extra "app"` |
| `--hl` | Bahasa Play Store (*Host Language*, ISO 639-1) | `"en"` | `--hl id` |
| `--gl` | Negara katalog Play Store (*Geolocation*, ISO 3166-1) | `"us"` | `--gl id` |
| `--max-few` | Batas maksimal hasil relevan untuk file `sedikit` | `3` | `--max-few 5` |
| `--resume` | Lanjutkan proses dari file CSV yang sudah ada | `False` | `--resume` |
| `--prefix` | Prefix kustom nama file output CSV | `hasil_<seed>` | `--prefix "riset_game"` |
| `--headful` | Tampilkan jendela browser saat scraping | `False` (headless) | `--headful` |
| `--test` | Tes cepat 1 query tanpa scraping 27 query | `False` | `--test` |

### Referensi Kode Bahasa (`--hl`) & Negara (`--gl`) Berdasarkan eCPM AdMob

Urutan tier target pasar monetisasi AdMob dari eCPM tertinggi hingga terendah.

> [!WARNING]
> **Penting:**
> - `--hl` (*Host Language*): Kode bahasa 2 huruf (ISO 639-1).
> - `--gl` (*Geolocation*): Kode negara 2 huruf (ISO 3166-1 alpha-2).
> - Jangan tertukar! Contoh kasus Malaysia: gunakan `--hl ms --gl my`. Jika menggunakan `--hl my`, Google Play akan dibuka dalam bahasa Burma/Myanmar.

#### Tier 1 (eCPM Tertinggi / High-Yield)
Negara dengan lelang iklan tertinggi (estimasi US\$15 – US\$40+ pada interstitial & rewarded ads).

| Negara | Kode Negara (`--gl`) | Bahasa Utama | Kode Bahasa (`--hl`) | Contoh Perintah |
|---|---|---|---|---|
| Amerika Serikat | `us` | English | `en` | `python scrape.py "keyword" --hl en --gl us` |
| Australia | `au` | English | `en` | `python scrape.py "keyword" --hl en --gl au` |
| Kanada | `ca` | English / French | `en` / `fr` | `python scrape.py "keyword" --hl en --gl ca` |
| Inggris Raya (UK) | `gb` | English | `en` | `python scrape.py "keyword" --hl en --gl gb` |
| Swiss | `ch` | German / French | `de` / `fr` | `python scrape.py "keyword" --hl de --gl ch` |
| Jerman | `de` | German | `de` | `python scrape.py "keyword" --hl de --gl de` |
| Norwegia | `no` | Norwegian | `no` | `python scrape.py "keyword" --hl no --gl no` |
| Swedia | `se` | Swedish | `sv` | `python scrape.py "keyword" --hl sv --gl se` |
| Denmark | `dk` | Danish | `da` | `python scrape.py "keyword" --hl da --gl dk` |
| Belanda | `nl` | Dutch | `nl` | `python scrape.py "keyword" --hl nl --gl nl` |
| Selandia Baru | `nz` | English | `en` | `python scrape.py "keyword" --hl en --gl nz` |
| Jepang | `jp` | Japanese | `ja` | `python scrape.py "keyword" --hl ja --gl jp` |
| Korea Selatan | `kr` | Korean | `ko` | `python scrape.py "keyword" --hl ko --gl kr` |
| Singapura | `sg` | English / Chinese | `en` / `zh` | `python scrape.py "keyword" --hl en --gl sg` |
| Prancis | `fr` | French | `fr` | `python scrape.py "keyword" --hl fr --gl fr` |
| Austria | `at` | German | `de` | `python scrape.py "keyword" --hl de --gl at` |
| Belgia | `be` | Dutch / French | `nl` / `fr` | `python scrape.py "keyword" --hl nl --gl be` |
| Finlandia | `fi` | Finnish | `fi` | `python scrape.py "keyword" --hl fi --gl fi` |
| Irlandia | `ie` | English | `en` | `python scrape.py "keyword" --hl en --gl ie` |
| Uni Emirat Arab | `ae` | Arabic / English | `ar` / `en` | `python scrape.py "keyword" --hl ar --gl ae` |
| Arab Saudi | `sa` | Arabic | `ar` | `python scrape.py "keyword" --hl ar --gl sa` |

#### Tier 2 (eCPM Menengah / Medium-Yield)
Pasar dengan eCPM stabil (estimasi US\$5 – US\$15) dan volume pengguna menengah-keatas.

| Negara | Kode Negara (`--gl`) | Bahasa Utama | Kode Bahasa (`--hl`) | Contoh Perintah |
|---|---|---|---|---|
| Italia | `it` | Italian | `it` | `python scrape.py "keyword" --hl it --gl it` |
| Spanyol | `es` | Spanish | `es` | `python scrape.py "keyword" --hl es --gl es` |
| Taiwan | `tw` | Chinese (Tradisional) | `zh` | `python scrape.py "keyword" --hl zh --gl tw` |
| Hong Kong | `hk` | Chinese / English | `zh` / `en` | `python scrape.py "keyword" --hl zh --gl hk` |
| Israel | `il` | Hebrew | `iw` / `he` | `python scrape.py "keyword" --hl iw --gl il` |
| Polandia | `pl` | Polish | `pl` | `python scrape.py "keyword" --hl pl --gl pl` |
| Portugal | `pt` | Portuguese | `pt` | `python scrape.py "keyword" --hl pt --gl pt` |
| Ceko | `cz` | Czech | `cs` | `python scrape.py "keyword" --hl cs --gl cz` |
| Yunani | `gr` | Greek | `el` | `python scrape.py "keyword" --hl el --gl gr` |
| Afrika Selatan | `za` | English | `en` | `python scrape.py "keyword" --hl en --gl za` |
| Malaysia | `my` | Melayu / English | `ms` / `en` | `python scrape.py "keyword" --hl ms --gl my` |
| Thailand | `th` | Thai | `th` | `python scrape.py "keyword" --hl th --gl th` |
| Meksiko | `mx` | Spanish | `es` | `python scrape.py "keyword" --hl es --gl mx` |
| Chili | `cl` | Spanish | `es` | `python scrape.py "keyword" --hl es --gl cl` |
| Brasil | `br` | Portuguese | `pt` | `python scrape.py "keyword" --hl pt --gl br` |

#### Tier 3 (Volume Tinggi / eCPM Rendah)
Pasar dengan unduhan & impresi sangat masif, tetapi eCPM relatif rendah (estimasi US\$0.50 – US\$4).

| Negara | Kode Negara (`--gl`) | Bahasa Utama | Kode Bahasa (`--hl`) | Contoh Perintah |
|---|---|---|---|---|
| Indonesia | `id` | Indonesian | `id` | `python scrape.py "keyword" --hl id --gl id` |
| Filipina | `ph` | English / Tagalog | `en` / `tl` | `python scrape.py "keyword" --hl en --gl ph` |
| Vietnam | `vn` | Vietnamese | `vi` | `python scrape.py "keyword" --hl vi --gl vn` |
| Turki | `tr` | Turkish | `tr` | `python scrape.py "keyword" --hl tr --gl tr` |
| Kolombia | `co` | Spanish | `es` | `python scrape.py "keyword" --hl es --gl co` |
| Argentina | `ar` | Spanish | `es` | `python scrape.py "keyword" --hl es --gl ar` |
| Mesir | `eg` | Arabic | `ar` | `python scrape.py "keyword" --hl ar --gl eg` |
| India | `in` | Hindi / English | `hi` / `en` | `python scrape.py "keyword" --hl en --gl in` |
| Pakistan | `pk` | Urdu / English | `ur` / `en` | `python scrape.py "keyword" --hl en --gl pk` |
| Nigeria | `ng` | English | `en` | `python scrape.py "keyword" --hl en --gl ng` |
| Bangladesh | `bd` | Bengali | `bn` | `python scrape.py "keyword" --hl bn --gl bd` |

## Tes Cepat (`--test`)

Untuk mengecek apakah koneksi Playwright, scraper, dan analisis relevansi berfungsi normal:

```powershell
python scrape.py "fortnite zero hour" --test
```

Contoh output:
```text
Memeriksa relevansi & jumlah aplikasi untuk: 'fortnite zero hour'...
Hasil: 1 aplikasi relevan dari total 30 aplikasi terdeteksi.
Aplikasi relevan (1):
  * Fortnite (com.epicgames.fortnite)

Tes berhasil! Alur Playwright dan analisis relevansi bekerja normal.
```

## Output CSV

File CSV dibuat otomatis dengan format nama `hasil_<seed>_*.csv`.

Setiap file CSV memiliki 4 kolom:
1. `keyword`: Kata kunci saran Play Store.
2. `total_hasil`: Jumlah total aplikasi yang dimuat Play Store (termasuk rekomendasi filler).
3. `hasil_relevan`: Jumlah aplikasi yang benar-benar relevan dengan query.
4. `daftar_app_relevan`: Daftar lengkap semua judul dan Package ID aplikasi relevan (dipisahkan tanda `|`).

| File | Kriteria Penyaringan |
|---|---|
| `hasil_<seed>_semua.csv` | Semua kata kunci yang berhasil diperiksa. |
| `hasil_<seed>_nol.csv` | Kata kunci dengan **`hasil_relevan == 0`** (potensi gap tanpa kompetitor relevan sama sekali). |
| `hasil_<seed>_sedikit.csv` | Kata kunci dengan **`hasil_relevan <= max-few`** (default $\le 3$, potensi kompetisi rendah). |

## Tips Riset ASO

- **Waspada Angka 30**: Google Play sering menampilkan 30 hasil meskipun query sangat sepi, karena mengisi slot dengan aplikasi populer (Uber, Paramount+, Teams, dsb). Selalu jadikan kolom `hasil_relevan` sebagai acuan kompetisi sebenarnya.
- **Perhatikan Variasi Natural**: Autocomplete Play Store sering memunculkan variasi query inversi (seperti `"zombie fortnite 4"` dari input `"fortnite z"`). Ini menandakan query tersebut memiliki riwayat pencarian nyata dari user.
- **Jeda Otomatis**: Script sudah dilengkapi jeda acak alami (1.5–3.5 detik) antar query untuk menjaga kestabilan dan meminimalisir pembatasan dari Play Store.

## Lisensi & Disclaimer

Proyek ini memakai halaman web publik Google Play Store yang tidak memiliki API publik resmi. Gunakan dengan wajar, patuhi ketentuan layanan Google, dan jangan dipakai untuk scraping dalam skala berlebihan.
