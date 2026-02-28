from gdrive_service import get_drive_service

svc = get_drive_service()

res = (
    svc.files()
    .list(
        pageSize=10,
        q="trashed=false",
        fields="files(id,name,mimeType,modifiedTime)",
    )
    .execute()
)

for f in res.get("files", []):
    print(f"{f['name']}  ({f['mimeType']})  id={f['id']}")
