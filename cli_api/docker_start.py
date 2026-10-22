"""Copy login files from read-only host mounts into writable runtime storage."""
from pathlib import Path
import shutil
import uvicorn

def copy_credentials():
    for source, destination in (
        ('/host-auth/claude/.credentials.json', Path.home() / '.claude/.credentials.json'),
        ('/host-auth/codex/auth.json', Path.home() / '.codex/auth.json'),
    ):
        origin = Path(source)
        if origin.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, destination)
            destination.chmod(0o600)

if __name__ == '__main__':
    copy_credentials()
    uvicorn.run('cli_api.app:app', host='0.0.0.0', port=8088)
