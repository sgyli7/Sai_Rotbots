from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sai-agent-001")
except PackageNotFoundError:
    __version__ = "0.1.0a3.dev0"
