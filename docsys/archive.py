import os

from .sources import GDriveSource, LocalDirSource


def archive_docs() -> int:
    """
    Archives all documents from the active input source.
    - gdrive: move tslac_input -> tslac_saved
    - local:  move LOCAL_INPUT_DIR -> LOCAL_ARCHIVE_DIR
    Returns number of docs moved.
    """
    mode = os.getenv("DOC_INPUT_MODE", "gdrive").lower()

    if mode == "gdrive":
        src = GDriveSource(
            os.getenv("GDRIVE_INPUT_FOLDER_NAME", "tslac_input"),
            os.getenv("GDRIVE_ARCHIVE_FOLDER_NAME", "tslac_saved"),
        )
    elif mode == "local":
        src = LocalDirSource(
            os.environ["LOCAL_INPUT_DIR"],
            os.environ["LOCAL_ARCHIVE_DIR"],
        )
    else:
        raise RuntimeError(f"Unknown DOC_INPUT_MODE: {mode}")

    return src.archive_all()
