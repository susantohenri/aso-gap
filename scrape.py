import argparse
import csv
import os
import random
import re
import string
import sys
import time
from typing import Dict, List, Set, Tuple

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

CSV_HEADER = ["keyword", "total_hasil", "hasil_relevan", "daftar_app_relevan"]

STOP_WORDS = {
    # English
    "a", "an", "the", "and", "or", "for", "of", "in", "on", "at", "to", "with",
    "by", "from", "is", "it", "as", "be", "this", "that", "app", "apps", "free",
    "new", "best", "pro", "online", "game", "games",
    # Indonesian
    "dan", "di", "ke", "dari", "untuk", "yang", "pada", "dengan", "atau", "ini",
    "itu", "aplikasi", "gratis", "terbaru", "terbaik", "cara"
}


def get_clean_tokens(text: str) -> List[str]:
    """Mengambil token/kata bersih tanpa tanda baca dan stop words umum."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    return meaningful if meaningful else words


def is_app_relevant(query: str, app: dict) -> bool:
    """
    Menilai apakah aplikasi relevan dengan query pencarian (bukan filler rekomendasi algoritma).
    Menggunakan kombinasi exact match, token overlap di Judul/AppId, dan snippet deskripsi.
    """
    query_clean = query.lower().strip()
    q_tokens = get_clean_tokens(query)
    if not q_tokens:
        return True

    title = (app.get("title") or "").lower()
    app_id = (app.get("appId") or "").lower()
    desc = (app.get("description") or "").lower()

    # 1. Exact phrase match di title, appId, atau deskripsi
    if query_clean in title or query_clean in app_id or query_clean in desc:
        return True

    # 2. Token matching di Title / App ID (sinyal ASO terkuat)
    title_matches = [t for t in q_tokens if t in title or t in app_id]

    # Jika query hanya 1 kata utama: wajib ada di title atau app_id
    if len(q_tokens) == 1:
        return len(title_matches) >= 1

    # Jika query multi-kata:
    # Setidaknya 50% kata query muncul di title/app_id
    ratio_title = len(title_matches) / len(q_tokens)
    if ratio_title >= 0.5:
        return True

    # Atau minimal 1 kata di title/app_id DAN kata lainnya tersebar di deskripsi (>= 60% token cover)
    if len(title_matches) >= 1:
        desc_matches = [t for t in q_tokens if t in desc]
        all_matched = set(title_matches + desc_matches)
        if (len(all_matched) / len(q_tokens)) >= 0.6:
            return True

    return False


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
        print(f"      Menjalankan {total_queries} query ekspansi alfabet...")

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


def check_keyword_competition(keyword: str, hl: str = "en", gl: str = "us", max_retries: int = MAX_RETRIES) -> Tuple[int, int, List[str]]:
    """
    Mengecek jumlah total aplikasi dan jumlah aplikasi yang relevan di Play Store.
    Mengembalikan: (total_hasil, hasil_relevan, daftar_app_relevan)
    """
    for attempt in range(max_retries + 1):
        try:
            kwargs = {"lang": hl}
            if gl:
                kwargs["country"] = gl
            results = gps.search(keyword, **kwargs)
            if not results:
                return 0, 0, []

            relevant_apps = []
            for app in results:
                if is_app_relevant(keyword, app):
                    title = (app.get("title") or "").strip()
                    app_id = (app.get("appId") or "").strip()
                    relevant_apps.append(f"{title} ({app_id})" if app_id else title)

            return len(results), len(relevant_apps), relevant_apps

        except (NotFoundError, TypeError, IndexError):
            # Dataset kosong (0 hasil) pada google-play-scraper
            return 0, 0, []
        except Exception as e:
            if attempt < max_retries:
                time.sleep(1.0)
            else:
                print(f"  [Error] Gagal cek hasil untuk '{keyword}': {e}")
                return -1, -1, []
    return -1, -1, []


def get_csv_filenames(seed: str, extra: str = "", prefix: str = "") -> Dict[str, str]:
    """Menghasilkan nama file CSV otomatis per seed agar tidak bertabrakan."""
    if prefix:
        base_prefix = prefix
    else:
        full_seed = f"{seed}_{extra}".strip("_") if extra else seed.strip()
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", full_seed.lower()).strip("_")
        base_prefix = f"hasil_{slug}" if slug else "hasil"

    return {
        "all": f"{base_prefix}_semua.csv",
        "zero": f"{base_prefix}_nol.csv",
        "few": f"{base_prefix}_sedikit.csv",
    }


def load_existing_results(filename: str) -> Dict[str, Tuple[int, int, str]]:
    """Membaca file CSV untuk mendukung resume jika sebelumnya terhenti."""
    results = {}
    if os.path.exists(filename):
        try:
            with open(filename, mode="r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and len(row) >= 3:
                        kw = row[0].strip()
                        try:
                            tot = int(row[1].strip())
                        except ValueError:
                            tot = -1
                        try:
                            rel = int(row[2].strip())
                        except ValueError:
                            rel = -1
                        apps = row[3].strip() if len(row) >= 4 else ""
                        results[kw] = (tot, rel, apps)
        except Exception as e:
            print(f"[Warning] Gagal membaca existing CSV: {e}")
    return results


def append_csv(filename: str, row: List, header: List[str] = CSV_HEADER):
    """Menambahkan satu baris ke file CSV dan langsung flush ke disk."""
    file_exists = os.path.exists(filename)
    with open(filename, mode="a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not file_exists or os.path.getsize(filename) == 0:
            writer.writerow(header)
        writer.writerow(row)
        f.flush()


def run_test_mode(seed: str, hl: str, gl: str, headless: bool):
    """Mode tes cepat: hanya uji 1 query untuk memverifikasi alur Playwright, Scraper, & Relevansi."""
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
    print(f"\nMemeriksa relevansi & jumlah aplikasi untuk: '{first_kw}'...")
    total_count, rel_count, rel_apps = check_keyword_competition(first_kw, hl=hl, gl=gl)
    print(f"Hasil: {rel_count} aplikasi relevan dari total {total_count} aplikasi terdeteksi.")
    if rel_apps:
        print(f"Aplikasi relevan ({len(rel_apps)}):")
        for app_str in rel_apps[:5]:
            print(f"  * {app_str}")
        if len(rel_apps) > 5:
            print(f"  ... dan {len(rel_apps) - 5} lainnya (semua dicatat di CSV).")
    else:
        print("Catatan: Tidak ada aplikasi yang relevan (celah kompetisi murni).")

    print("\nTes berhasil! Alur Playwright dan analisis relevansi bekerja normal.")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="ASO-GAP: Mencari keyword gap & relevansi kompetitor di Google Play Store.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Contoh penggunaan:
  python scrape.py "photo editor"
  python scrape.py "editor foto" --hl id --gl id
  python scrape.py "fitness tracker" --extra "app"
  python scrape.py "photo editor" --resume
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
        help="Batas maksimal hasil relevan untuk masuk hasil_<seed>_sedikit.csv. Default: 3."
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Prefix kustom untuk nama file CSV hasil (Default: hasil_<seed>)."
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Lanjutkan proses scraping dari file CSV yang sudah ada tanpa menimpanya."
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

    csv_files = get_csv_filenames(seed, args.extra, args.prefix)

    print("=" * 60)
    print("ASO-GAP: Play Store Keyword Gap & Relevance Hunter")
    print(f"Seed: '{seed}' | Extra: '{args.extra}' | Target: {args.hl}-{args.gl} | Headless: {headless}")
    print(f"Output: {csv_files['all']}, {csv_files['few']}, {csv_files['zero']}")
    print("=" * 60)

    # 1. Kumpulkan suggestion via Playwright
    queries = get_queries(seed, args.extra)
    suggestions = collect_playstore_suggestions(queries, hl=args.hl, gl=args.gl, headless=headless)

    # 2. Cek resume state vs fresh start
    existing = {}
    if args.resume and os.path.exists(csv_files["all"]):
        existing = load_existing_results(csv_files["all"])
        print(f"[Resume] Ditemukan {len(existing)} keyword yang sudah diperiksa di {csv_files['all']}.")
    else:
        # Jika bukan resume, inisialisasi file baru bersih (timpa jika file dengan nama sama sudah ada)
        for key in ["all", "zero", "few"]:
            path = csv_files[key]
            with open(path, mode="w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
        if os.path.exists(csv_files["all"]) and not args.resume:
            print(f"[Fresh Start] Memulai pencarian baru (output bersih di {csv_files['all']}).")

    print(f"[2/2] Memeriksa jumlah & relevansi hasil di Play Store untuk {len(suggestions)} keyword...")

    total_checked = 0
    total_zero = 0
    total_few = 0

    for idx, kw in enumerate(suggestions, 1):
        if kw in existing:
            tot, rel, apps = existing[kw]
            print(f"  [{idx}/{len(suggestions)}] '{kw}' -> {rel} relevan / {tot} total (dari resume)")
        else:
            tot, rel, rel_apps = check_keyword_competition(kw, hl=args.hl, gl=args.gl)
            apps_str = " | ".join(rel_apps)
            row = [kw, tot, rel, apps_str]

            append_csv(csv_files["all"], row, CSV_HEADER)

            # Masuk ke hasil_nol jika HASIL RELEVAN == 0
            if rel == 0:
                append_csv(csv_files["zero"], row, CSV_HEADER)
                total_zero += 1

            # Masuk ke hasil_sedikit jika 0 <= HASIL RELEVAN <= max_few
            if 0 <= rel <= args.max_few:
                append_csv(csv_files["few"], row, CSV_HEADER)
                total_few += 1

            existing[kw] = (tot, rel, apps_str)
            total_checked += 1

            # Cuplikan singkat di console (1-2 nama app)
            preview_apps = f" | Contoh: {rel_apps[0]}" if rel_apps else " | Tidak ada kompetitor relevan"
            print(f"  [{idx}/{len(suggestions)}] '{kw}' -> {rel} relevan / {tot} total{preview_apps}")

            # Jeda kecil antar pengecekan API
            time.sleep(random.uniform(0.8, 1.6))

    print("\n" + "=" * 60)
    print("Selesai!")
    print(f"- Total keyword: {len(existing)}")
    print(f"- Keyword dengan 0 kompetitor relevan: {total_zero}")
    print(f"- Keyword dengan <= {args.max_few} kompetitor relevan: {total_few}")
    print(f"- File tersimpan di: {csv_files['all']}, {csv_files['few']}, {csv_files['zero']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
