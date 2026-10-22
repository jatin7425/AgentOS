import importlib
import pkgutil
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/v1")

# Find every .py file next to this one
for module in sorted(pkgutil.iter_modules([str(Path(__file__).parent)]), key=lambda m: m.name):
    name = module.name

    # Skip private files like __init__.py or _helpers.py
    if name.startswith("_"):
        continue

    # Load the module, e.g. api.v1.health
    file = importlib.import_module(f"{__name__}.{name}")

    # Take its "router" (if it has one)
    file_router = getattr(file, "router", None)
    if isinstance(file_router, APIRouter):
        # health.py → /health, user_profile.py → /user-profile
        router.include_router(
            file_router,
            prefix=f"/{name.replace('_', '-')}",
            tags=[name],
        )
