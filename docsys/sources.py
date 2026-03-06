from __future__ import annotations

import mimetypes
import os
import pathlib
import shutil
from abc import ABC, abstractmethod

from gdrive_service import find_folder_id, get_drive_service, list_files_in_folder
from logutil import debug, info

from .types import DocRef

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"


class DocumentSourceError(RuntimeError):
    """Base error for document source failures."""


class DocumentNotFoundError(DocumentSourceError):
    """Raised when a DocRef/doc_id can't be found in the source."""


class DocumentSource(ABC):
    """
    Abstract base class for a pluggable document provider.

    Implementations:
      - GDriveSource: documents from a Google Drive folder
      - LocalDirSource: documents from a local directory
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Short identifier used in logs/UI: e.g. 'gdrive' or 'local'."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source_name={self.source_name!r}>"

    @abstractmethod
    def list_docs(self) -> list[DocRef]:
        raise NotImplementedError

    @abstractmethod
    def fetch_bytes(self, doc: DocRef) -> tuple[bytes, str]:
        raise NotImplementedError

    @abstractmethod
    def archive_all(self) -> int:
        raise NotImplementedError

    # Optional helpers
    def list_doc_ids(self) -> list[str]:
        return [d.doc_id for d in self.list_docs()]

    def list_doc_names(self) -> list[str]:
        return [d.display_name for d in self.list_docs()]

    def get_doc_by_id(self, doc_id: str) -> DocRef:
        for d in self.list_docs():
            if d.doc_id == doc_id:
                return d
        raise DocumentNotFoundError(f"Document not found in {self.source_name}: {doc_id}")

    def fetch_bytes_by_id(self, doc_id: str) -> tuple[bytes, str, DocRef]:
        doc = self.get_doc_by_id(doc_id)
        data, filename = self.fetch_bytes(doc)
        return data, filename, doc


class LocalDirSource(DocumentSource):
    def __init__(self, input_dir: str, archive_dir: str):
        self.input_dir = os.path.abspath(input_dir)
        self.archive_dir = os.path.abspath(archive_dir)

    @property
    def source_name(self) -> str:
        return "local"

    def list_docs(self) -> list[DocRef]:
        debug(f"Local: scanning {self.input_dir}")
        p = pathlib.Path(self.input_dir)
        if not p.exists():
            info("Local: input directory does not exist")
            return []

        docs: list[DocRef] = []
        for f in sorted(p.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext not in [".docx", ".pdf", ".txt", ".html", ".htm", ".rtf"]:
                continue

            mime, _ = mimetypes.guess_type(str(f))
            stat = f.stat()

            debug(f"Local: doc {f.name} mime={mime} size={stat.st_size}")

            docs.append(
                DocRef(
                    doc_id=f"local:{str(f)}",
                    display_name=f.name,
                    source="local",
                    mime_type=mime,
                    modified_ts=str(int(stat.st_mtime)),
                    size=stat.st_size,
                    extra={"path": str(f)},
                )
            )

        debug(f"Local: found {len(docs)} supported file(s)")
        return docs

    def fetch_bytes(self, doc: DocRef) -> tuple[bytes, str]:
        path = doc.extra["path"]
        debug(f"Local: reading bytes for {path}")
        with open(path, "rb") as f:
            data = f.read()
        debug(f"Local: read {len(data)} bytes for {os.path.basename(path)}")
        return data, os.path.basename(path)

    def archive_all(self) -> int:
        os.makedirs(self.archive_dir, exist_ok=True)
        count = 0
        for doc in self.list_docs():
            src = doc.extra["path"]
            dst = os.path.join(self.archive_dir, os.path.basename(src))

            # avoid overwrite
            if os.path.exists(dst):
                base, ext = os.path.splitext(dst)
                i = 1
                while os.path.exists(f"{base}_{i}{ext}"):
                    i += 1
                dst = f"{base}_{i}{ext}"

            shutil.move(src, dst)
            debug(f"Local: archived {os.path.basename(src)} -> {dst}")
            count += 1

        debug(f"Local: archived {count} file(s)")
        return count


class GDriveSource(DocumentSource):
    def __init__(self, input_folder_name: str, archive_folder_name: str):
        self.svc = get_drive_service()
        self.input_folder_id = find_folder_id(self.svc, input_folder_name)
        self.archive_folder_id = find_folder_id(self.svc, archive_folder_name)

    @property
    def source_name(self) -> str:
        return "gdrive"

    def list_docs(self) -> list[DocRef]:
        files = list_files_in_folder(self.svc, self.input_folder_id)
        debug(f"GDrive: found {len(files)} file(s) in input folder")

        docs: list[DocRef] = []
        for f in files:
            debug(f"GDrive: doc {f['name']} mime={f.get('mimeType')} id={f['id']}")
            docs.append(
                DocRef(
                    doc_id=f"gdrive:{f['id']}",
                    display_name=f["name"],
                    source="gdrive",
                    mime_type=f.get("mimeType"),
                    modified_ts=f.get("modifiedTime"),
                    size=int(f["size"]) if "size" in f else None,
                    extra={"file_id": f["id"]},
                )
            )
        return docs

    def fetch_bytes(self, doc: DocRef) -> tuple[bytes, str]:
        debug(f"GDrive: fetching '{doc.display_name}' mime={doc.mime_type}")
        file_id = doc.extra["file_id"]
        mime_type = doc.mime_type or ""

        # Export Google Workspace files
        if mime_type == GOOGLE_DOC_MIME:
            debug(f"GDrive: exporting Google Doc -> text/plain: {doc.display_name}")
            data = self.svc.files().export(fileId=file_id, mimeType="text/plain").execute()
            debug(f"GDrive: fetched {len(data)} bytes (export) for {doc.display_name}")
            return data, doc.display_name + ".txt"

        if mime_type == GOOGLE_SHEET_MIME:
            debug(f"GDrive: exporting Google Sheet -> text/csv: {doc.display_name}")
            data = self.svc.files().export(fileId=file_id, mimeType="text/csv").execute()
            debug(f"GDrive: fetched {len(data)} bytes (export) for {doc.display_name}")
            return data, doc.display_name + ".csv"

        if mime_type == GOOGLE_SLIDES_MIME:
            debug(f"GDrive: exporting Google Slides -> text/plain: {doc.display_name}")
            data = self.svc.files().export(fileId=file_id, mimeType="text/plain").execute()
            debug(f"GDrive: fetched {len(data)} bytes (export) for {doc.display_name}")
            return data, doc.display_name + ".txt"

        # Download binary files
        data = self.svc.files().get_media(fileId=file_id).execute()
        debug(f"GDrive: fetched {len(data)} bytes for {doc.display_name}")
        return data, doc.display_name

    def archive_all(self) -> int:
        files = list_files_in_folder(self.svc, self.input_folder_id)
        count = 0
        for f in files:
            file_id = f["id"]
            self.svc.files().update(
                fileId=file_id,
                addParents=self.archive_folder_id,
                removeParents=self.input_folder_id,
                fields="id, parents",
            ).execute()
            debug(f"GDrive: archived {f['name']} id={file_id}")
            count += 1

        debug(f"GDrive: archived {count} file(s)")
        return count




def from_env() -> DocumentSource:
    """
    Build the appropriate DocumentSource based on environment configuration.

    DOC_INPUT_MODE:
        gdrive  -> Google Drive folder
        local   -> Local filesystem directory
    """

    mode = os.getenv("DOC_INPUT_MODE", "gdrive").strip().lower()

    if mode == "local":
        root = os.getenv("DOC_LOCAL_PATH", "./docs")
        return LocalDirSource(root)

    # ---- Google Drive mode ----
    folder_name = os.getenv("GDRIVE_INPUT_FOLDER_NAME", "tslac_input")
    archive_folder_name = os.getenv("GDRIVE_ARCHIVE_FOLDER_NAME", "tslac_saved")

    return GDriveSource(folder_name, archive_folder_name)