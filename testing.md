##Test scripts

### Test g-drive access
python -c "import os,sys; print('cwd=',os.getcwd()); print('sys.path[0]=',sys.path[0]); print('has gdrive?', os.path.exists('gdrive_service.py'))"
cwd= /Users/bob/tslac
