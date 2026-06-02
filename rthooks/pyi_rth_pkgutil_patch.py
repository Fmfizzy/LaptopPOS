try:
    import pyimod02_importers
    if not hasattr(pyimod02_importers, 'PyiFrozenImporter'):
        class _PyiFrozenImporter:
            pass
        pyimod02_importers.PyiFrozenImporter = _PyiFrozenImporter
except Exception:
    pass
