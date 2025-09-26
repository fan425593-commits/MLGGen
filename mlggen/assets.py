import os

DEFAULT_ASSETS = {
    "airhorn": "assets/airhorn.mp3",
    "mtndew": "assets/mtndew.mp3",
    "doritos": "assets/doritos.png",
    "lensflare": "assets/lensflare.png",
    "hitmarker": "assets/hitmarker.mp3",
}

def resolve_assets(custom_paths=None):
    """
    Return a dict of asset paths. custom_paths may override DEFAULT_ASSETS keys.
    """
    assets = DEFAULT_ASSETS.copy()
    if custom_paths:
        assets.update(custom_paths)
    # Expand to absolute paths and validate existence where possible
    for k, p in list(assets.items()):
        if not os.path.isabs(p):
            p = os.path.abspath(p)
        assets[k] = p
    return assets