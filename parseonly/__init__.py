__all__ = ['cxx', 'cpp']

try:
    from ._version import __version__
except ImportError:
    import importlib.metadata

    try:
        __version__ = importlib.metadata.version("py" + __name__)
    except:
        __version__ = "N/A"

from . import cxx
from . import cpp
