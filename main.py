import shutil
from pathlib import Path
from PIL import Image
import pypdfium2 as pdfium
import re
from utils import find_source_folders, safe_copy, log_ticket_end, log_pipeline, log_ticket_start, L1, L2, L3,L3_err,L3_ok,L3_warn,L4
from resize import resize_images, resize_videos
import time


# Matches version patterns like: v1, ver1, version1, ver 1, version 1, Ver_2, etc.
VERSION_PATTERN = re.compile(r'v(?:er(?:sion)?)?\s*[_\-]?\s*(\d+)', re.IGNORECASE)

OUTPUT_DIR = Path("./output")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp4", ".avi", ".mov"}


# ═════════════════════════════════════════════════════════════
#  Traversal
# ═════════════════════════════════════════════════════════════
 
def collect_recursive(
    current_dir: Path,
    dest_dir: Path,
    extensions: set[str],
    inside_version: bool = False,
    traversal_root: Path | None = None,
) -> int:
    """
    Recursively collect files from current_dir into dest_dir (flat).
    Returns the number of files copied.
    """
    if traversal_root is None:
        traversal_root = current_dir
 
    copied = 0
    version_folders: dict[int, Path] = {}
 
    for item in current_dir.iterdir():
 
        if item.is_file() and item.suffix.lower() in extensions:
            if item.suffix.lower() == ".mov":
                L4(f"⚠  SKIPPED .mov: {item.name}")
                continue
 
            safe_copy(item, dest_dir)
            L4(f"Copied: {item.name}")
            copied += 1
 
        elif item.is_dir() and not inside_version:
            match = VERSION_PATTERN.search(item.name)
            if match:
                version_num = int(match.group(1))
                rel = item.relative_to(traversal_root.parent)
                L4(f"Version folder detected: {rel}  (v{version_num})")
                version_folders[version_num] = item
 
    if version_folders and not inside_version:
        latest_num = max(version_folders)
        latest_folder = version_folders[latest_num]
        L4(f"Using latest version folder: {latest_folder.name}")
        copied += collect_recursive(
            latest_folder, dest_dir, extensions,
            inside_version=True, traversal_root=traversal_root
        )
    else:
        for item in current_dir.iterdir():
            if item.is_dir():
                if not inside_version and VERSION_PATTERN.search(item.name):
                    continue
                copied += collect_recursive(
                    item, dest_dir, extensions,
                    inside_version, traversal_root
                )
 
    return copied
 
 
# ═════════════════════════════════════════════════════════════
#  PDF conversion
# ═════════════════════════════════════════════════════════════
 
def convert_pdfs(folder: Path, scale: int = 2, remove_pdf: bool = True):
    L2("CONVERT PDFs")
    count = 0
 
    for pdf_file in folder.iterdir():
        if not (pdf_file.is_file() and pdf_file.suffix.lower() == ".pdf"):
            continue
        try:
            pdf = pdfium.PdfDocument(pdf_file)
            page = pdf[0]
            bitmap = page.render(scale=scale)
            img = bitmap.to_pil()
 
            output_path = pdf_file.with_suffix(".png")
            img.save(output_path)
            pdf.close()
 
            L3_ok(f"Converted: {pdf_file.name}")
            count += 1
 
            if remove_pdf:
                pdf_file.unlink()
                L3(f"Removed original PDF: {pdf_file.name}")
 
        except Exception as e:
            L3_err(f"Failed to convert {pdf_file.name}: {e}")
 
    L3(f"PDFs converted: {count}")
    print()
 

 
 
# ═════════════════════════════════════════════════════════════
#  Main entry point
# ═════════════════════════════════════════════════════════════
 
def process_all(root: str = "./all-tickets"):
    root_path = Path(root)
 
    ticket_folders = sorted([p for p in root_path.iterdir() if p.is_dir()])
 
    log_pipeline(f"PIPELINE START  —  {len(ticket_folders)} ticket(s) found")
 
    for ticket_folder in ticket_folders:
        log_ticket_start(ticket_folder.name)
 
        # Per-ticket output directory
        ticket_output = OUTPUT_DIR / ticket_folder.name
        if ticket_output.exists():
            shutil.rmtree(ticket_output)
        ticket_output.mkdir(parents=True, exist_ok=True)
        L1(f"Output dir: {ticket_output.resolve()}")
        print()
 
        try:
            # ── 1. COLLECT FILES ──────────────────────────────────
            L2("COLLECT FILES")
 
            source_folders = find_source_folders(ticket_folder)
 
            if not source_folders:
                L3_warn("No 'Master Files' or 'Deliverables' folders found — skipping.")
                print()
                log_ticket_end(0)
                continue
 
            total_copied = 0
            for source_dir in source_folders:
                L3(f"Traversing: {source_dir.relative_to(ticket_folder)}")
                total_copied += collect_recursive(
                    source_dir, ticket_output, EXTENSIONS,
                    traversal_root=source_dir
                )
                print()
 
            # ── 2. CONVERT PDFs ───────────────────────────────────
            convert_pdfs(ticket_output)
 
            # ── 3. RESIZE IMAGES ──────────────────────────────────
            resize_images(ticket_output)
 
            # ── 4. RESIZE VIDEOS ──────────────────────────────────
            resize_videos(ticket_output)
 
        except Exception as e:
            L3_err(f"Unexpected error: {e}")
            L3("Skipping to next ticket.")
            print()
 
        log_ticket_end(total_copied if 'total_copied' in dir() else 0)
 
    log_pipeline("PIPELINE COMPLETE")
 
 
if __name__ == "__main__":
    # Start the stopwatch
    start_time = time.perf_counter()

    process_all()

    # Calculate total elapsed time
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    
    print(f"Total execution time: {execution_time:.6f} seconds")