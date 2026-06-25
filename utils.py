import shutil
from pathlib import Path
import re
from PIL import Image
 
# decompression bomb protection
Image.MAX_IMAGE_PIXELS = None

# inner width of ticket box
WIDTH = 54  

 
# ─────────────────────────────────────────────
#  Logging helpers
# ─────────────────────────────────────────────
 
def log_pipeline(title: str):
    bar = "═" * 60
    print(f"\n{bar}")
    print(f"  {title}")
    print(f"{bar}\n")
 
 
def log_ticket_start(name: str):
   pad = "─" * max(0, WIDTH - len(name))
   print(f"\n┌─── TICKET: {name} {pad}┐")
 
 
def log_ticket_end(count: int):
   label = f"Done ({count} file(s) collected)"
   pad = "─" * max(0, WIDTH - len(label) + 4)
   print(f"└─── {label} {pad}┘\n")
 
 
# indent levels
def L1(msg: str):               # ticket body
   print(f"    {msg}")
 
def L2(msg: str):               # process section header
   print(f"    {msg}")
 
def L3(msg: str):               # action inside a process
    print(f"        {msg}")
 
def L3_ok(msg: str):
   print(f"        ✔  {msg}")
 
def L3_warn(msg: str):
   print(f"        ⚠  {msg}")
 
def L3_err(msg: str):
   print(f"        ✖  {msg}")
 
def L4(msg: str):               # deeper nesting (version detection inside traversal)
   print(f"            {msg}")
 
# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
 
def normalize(name: str) -> str:
   return re.sub(r"[^a-z0-9]", "", name.lower())
 
 
def find_source_folders(ticket_root: Path) -> list[Path]:
   """Find all Master Files / Deliverables folders inside a ticket."""
   matches = []
   for path in ticket_root.rglob("*"):
      if not path.is_dir():
         continue
      name = normalize(path.name)
      if "masterfiles" in name or "deliverables" in name:
         matches.append(path)
   return matches
 
 
def safe_copy(src: Path, dest_dir: Path) -> Path:
   """Copy src into dest_dir with incremental suffix on collision."""
   dest = dest_dir / src.name
   counter = 1
   while dest.exists():
      dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
      counter += 1
   shutil.copy2(src, dest)
   return dest
   