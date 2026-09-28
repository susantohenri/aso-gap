import argparse
import csv
import os
import random
import string
import sys
import time
from typing import Dict, List, Set

# Pastikan output terminal di Windows mendukung UTF-8
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import google_play_scraper as gps
from google_play_scraper.exceptions import NotFoundError
from playwright.sync_api import sync_playwright

MIN_DELAY = 1.5  # Jeda minimal antar query Playwright (detik)
MAX_DELAY = 3.5  # Jeda maksimal antar query Playwright (detik)
MAX_RETRIES = 2  # Batas percobaan ulang jika dropdown gagal muncul

CSV_ALL = "hasil_semua.csv"
CSV_ZERO = "hasil_nol.csv"
CSV_FEW = "hasil_sedikit.csv"


def get_queries(seed: str, extra: str = "") -> List[str]:
    """Menghasilkan query alphabet expansion (seed + seed a..z)."""
    base = f"{seed} {extra}".strip() if extra else seed.strip()
    queries = [base]
    for ch in string.ascii_lowercase:
        queries.append(f"{base} {ch}")
    return queries


def extract_suggestions_from_page(page) -> List[str]:
    """Mengekstrak teks suggestion dari dropdown Play Store."""
    options = page.query_selector_all('[role="listbox"] [role="option"]')
    if not options:
        options = page.query_selector_all('[role="option"]')

    suggestions = []
    for opt in options:
        try:
            if not opt.is_visible():
                continue
            raw_text = opt.inner_text().strip()
            lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
            # Buang teks icon ligature font (biasanya 'search')
            clean_lines = [line for line in lines if line.lower() != "search"]
            text = " ".join(clean_lines).strip()
            if text and text not in suggestions:
                suggestions.append(text)
        except Exception:
            continue
    return suggestions


def fetch_query_suggestions(page, input_locator, query: str, max_retries: int = MAX_RETRIES) -> List[str]:
    """Mengambil suggestion untuk satu query dengan retry dan timeout."""
    for attempt in range(max_retries + 1):
        try:
            input_locator.click(timeout=5000)
            input_locator.fill("")
            page.wait_for_timeout(200)
            input_locator.type(query, delay=40)

            # Tunggu opsi dropdown muncul
            try:
                page.wait_for_selector('[role="listbox"] [role="option"]', state="visible", timeout=3000)
            except Exception:
                pass

            suggs = extract_suggestions_from_page(page)
            if suggs:
                return suggs

            if attempt < max_retries:
                time.sleep(1.0)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.0)
            else:
                print(f"  [Warning] Gagal mengambil suggestion '{query}': {e}")

    return []


def collect_playstore_suggestions(queries: List[str], hl: str = "en", gl: str = "us", headless: bool = True) -> List[str]:
    """Mengumpulkan suggestion dari Play Store memakai satu instance browser Playwright."""
    print(f"\n[1/2] Membuka Playwright browser (headless={headless})...")
    all_suggestions: List[str] = []
    seen: Set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        locale_str = f"{hl}-{gl.upper()}" if gl else hl
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale=locale_str,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        target_url = f"https://play.google.com/store/apps?hl={hl}" + (f"&gl={gl}" if gl else "")
        print(f"      Navigasi ke {target_url} (target: {locale_str})...")
        page.goto(target_url, wait_until="networkidle", timeout=30000)

        # Temukan tombol pencarian dan input
        search_btn = page.query_selector('button[aria-label*="Search" i], button[aria-label*="Telusuri" i], [aria-label*="search" i]')
        if search_btn and search_btn.is_visible():
            search_btn.click()
            page.wait_for_timeout(500)

        input_locator = page.locator('input[type="text"]').first
        input_locator.wait_for(state="visible", timeout=10000)

        total_queries = len(queries)
        print(f"      Menjalankan {total_queries} query...")

        for idx, q in enumerate(queries, 1):
            suggs = fetch_query_suggestions(page, input_locator, q)
            new_count = 0
            for s in suggs:
                if s not in seen:
                    seen.add(s)
                    all_suggestions.append(s)
                    new_count += 1

            print(f"  [{idx}/{total_queries}] Query: '{q}' -> {len(suggs)} saran (+{new_count} baru)")

            # Jeda acak antar query
            if idx < total_queries:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)

        browser.close()

    print(f"[1/2] Pengumpulan suggestion selesai. Total keyword unik: {len(all_suggestions)}\n")
    return all_suggestions


def check_app_count(keyword: str, hl: str = "en", gl: str = "us", max_retries: int = MAX_RETRIES) -> int:
    """Mengecek jumlah aplikasi yang muncul untuk keyword di Play Store."""
    for attempt in range(max_retries + 1):
        try:
            kwargs = {"lang": hl}
            if gl:
                kwargs["country"] = gl
            results = gps.search(keyword, **kwargs)
            return len(results) if results else 0
        except (NotFoundError, TypeError, IndexError):
            # Dataset kosong (0 hasil) pada google-play-scraper
            return 0
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.0)
            else:
                print(f"  [Error] Gagal cek hasil untuk '{keyword}': {e}")
                return -1
    return -1


def load_existing_results(filename: str) -> Dict[str, int]:
    """Membaca file CSV untuk mendukung resume jika sebelumnya terhenti."""
    results = {}
    if os.path.exists(filename):
        try:
            with open(filename, mode="r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and len(row) >= 2:
                        kw = row[0].strip()
                        try:
                            count = int(row[1].strip())
                        except ValueError:
                            count = -1
                        results[kw] = count
        except Exception as e:
            print(f"[Warning] Gagal membaca existing CSV: {e}")
    return results


def append_csv(filename: str, row: List):
    """Menambahkan satu baris ke file CSV dan langsung flush ke disk."""
    file_exists = os.path.exists(filename)
    with open(filename, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(filename) == 0:
            writer.writerow(["keyword", "jumlah_hasil"])
        writer.writerow(row)
        f.flush()


def run_test_mode(seed: str, hl: str, gl: str, headless: bool):
    """Mode tes cepat: hanya uji 1 query untuk memverifikasi alur Playwright & Scraper."""
    print("=" * 60)
    print("ASO-GAP: Mode Tes Cepat (--test)")
    print(f"Seed: '{seed}' | Target: {hl}-{gl} | Headless: {headless}")
    print("=" * 60)

    suggs = collect_playstore_suggestions([seed], hl=hl, gl=gl, headless=headless)
    if not suggs:
        print("[Status: GAGAL] Tidak ada suggestion yang ditemukan.")
        sys.exit(1)

    print(f"[Status: OK] Ditemukan {len(suggs)} saran Play Store:")
    for idx, s in enumerate(suggs, 1):
        print(f"  {idx}. {s}")

    first_kw = suggs[0]
    print(f"\nMemeriksa jumlah aplikasi untuk: '{first_kw}'...")
    count = check_app_count(first_kw, hl=hl, gl=gl)
    print(f"Hasil: {count} aplikasi terdeteksi di Play Store.")
    print("\nTes berhasil! Alur Playwright dan scraper bekerja normal.")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="ASO-GAP: Mencari keyword gap di Google Play Store menggunakan Playwright.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Contoh penggunaan:
  python scrape.py "photo editor"
  python scrape.py "editor foto" --hl id --gl id
  python scrape.py "fitness tracker" --extra "app"
  python scrape.py "photo editor" --test
"""
    )
    parser.add_argument(
        "seed",
        nargs="?",
        default="",
        help="Keyword utama / niche yang dicari (contoh: 'photo editor')."
    )
    parser.add_argument(
        "--extra",
        default="",
        help="Kata tambahan untuk query (contoh: 'app' atau 'aplikasi'). Default: kosong."
    )
    parser.add_argument(
        "--hl",
        default="en",
        help="Bahasa antarmuka Play Store (Host Language). Default: 'en'."
    )
    parser.add_argument(
        "--gl",
        default="us",
        help="Wilayah/Negara katalog Play Store (Geolocation). Default: 'us'."
    )
    parser.add_argument(
        "--max-few",
        type=int,
        default=3,
        help="Batas maksimal jumlah hasil untuk masuk hasil_sedikit.csv. Default: 3."
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Tampilkan jendela browser Playwright (non-headless). Default: headless."
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Jalankan tes cepat 1 query tanpa scraping penuh 27 query."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Validasi Seed Keyword
    seed = args.seed.strip() if args.seed else ""
    if not seed:
        print("\n[Error] Seed keyword tidak boleh kosong!\n")
        print("Penggunaan:")
        print('  python scrape.py "NAMA_KEYWORD" [opsi]\n')
        print("Contoh:")
        print('  python scrape.py "photo editor"')
        print('  python scrape.py "editor foto" --hl id --gl id')
        print('  python scrape.py "photo editor" --test')
        print('\nKetik "python scrape.py --help" untuk melihat seluruh opsi.')
        sys.exit(1)

    headless = not args.headful

    # Jika mode --test dipilih
    if args.test:
        run_test_mode(seed, hl=args.hl, gl=args.gl, headless=headless)
        return

    print("=" * 60)
    print("ASO-GAP: Play Store Keyword Gap Hunter")
    print(f"Seed: '{seed}' | Extra: '{args.extra}' | Target: {args.hl}-{args.gl} | Headless: {headless}")
    print("=" * 60)

    # 1. Kumpulkan suggestion via Playwright
    queries = get_queries(seed, args.extra)
    suggestions = collect_playstore_suggestions(queries, hl=args.hl, gl=args.gl, headless=headless)

    # 2. Cek resume state
    existing = load_existing_results(CSV_ALL)
    if existing:
        print(f"[Resume] Ditemukan {len(existing)} keyword yang sudah diperiksa di {CSV_ALL}.")

    # Pastikan header sudah ada jika file baru
    for path in [CSV_ALL, CSV_ZERO, CSV_FEW]:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["keyword", "jumlah_hasil"])

    print(f"[2/2] Memeriksa jumlah hasil di Play Store untuk {len(suggestions)} keyword...")

    total_checked = 0
    total_zero = 0
    total_few = 0

    for idx, kw in enumerate(suggestions, 1):
        if kw in existing:
            count = existing[kw]
            print(f"  [{idx}/{len(suggestions)}] '{kw}' -> {count} hasil (dari cache/resume)")
        else:
            count = check_app_count(kw, hl=args.hl, gl=args.gl)
            row = [kw, count]
            append_csv(CSV_ALL, row)

            if count == 0:
                append_csv(CSV_ZERO, row)
                total_zero += 1
            if 0 <= count <= args.max_few:
                append_csv(CSV_FEW, row)
                total_few += 1

            existing[kw] = count
            total_checked += 1
            print(f"  [{idx}/{len(suggestions)}] '{kw}' -> {count} hasil")

            # Jeda kecil antar pengecekan API
            time.sleep(random.uniform(0.8, 1.6))

    print("\n" + "=" * 60)
    print("Selesai!")
    print(f"- Total keyword: {len(existing)}")
    print(f"- Disimpan ke: {CSV_ALL}, {CSV_ZERO}, {CSV_FEW}")
    print("=" * 60)


if __name__ == "__main__":
    main()
