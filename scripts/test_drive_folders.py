from gdrive_service import get_drive_service, find_folder_id, list_files_in_folder

svc = get_drive_service()
in_id = find_folder_id(svc, "tslac_input")
sv_id = find_folder_id(svc, "tslac_saved")

print("input id:", in_id)
print("saved id:", sv_id)

files = list_files_in_folder(svc, in_id)
for f in files:
    print(f["name"], f["mimeType"], f["id"])