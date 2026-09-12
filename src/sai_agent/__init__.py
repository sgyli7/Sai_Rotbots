from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sai-agent-001")
except PackageNotFoundError:
    __version__ = "0.2.0a1.dev0"
