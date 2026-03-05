# Smoke tests (manual)

- GET /                        main page loads
- GET /refresh                 redirects back with status
- POST /save                   saves selection and redirects

- GET /curate/0                loads curate page for first candidate
- POST /curate/save            saves blurb and redirects
- POST /curate/select_image    selects image and redirects
- GET /img?...                 image proxy returns image bytes
- POST /curate/save_crop        crop persists and redirects

- GET /watch                   watch page loads
- POST /watch/save             saves watch config
- GET /watch/status            returns JSON

- GET /preview                 preview loads