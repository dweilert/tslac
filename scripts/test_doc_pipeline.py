import os
from doc_pipeline import build_doc_candidates
from doc_sources import GDriveSource, LocalDirSource

from dotenv import load_dotenv
load_dotenv()

def main():
    mode = os.getenv("DOC_INPUT_MODE", "gdrive").lower()
    if mode == "gdrive":
        src = GDriveSource("tslac_input", "tslac_saved")
    else:
        src = LocalDirSource(
            os.environ["LOCAL_INPUT_DIR"],
            os.environ["LOCAL_ARCHIVE_DIR"],
        )

    docs = build_doc_candidates(src)
    print(f"Doc candidates: {len(docs)}")
    for d in docs:
        print("-", d.get("title"), "|", d.get("id"))
        print("  summary:", (d.get("summary") or "")[:160], "...\n")

if __name__ == "__main__":
    main()