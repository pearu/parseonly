
import os

from .spanstr import spanstr

def iter_sources(source, file_exts=None, root_path=None, dtype=str):
  """Iterator of pairs (filename, content) from the given path.

  Filenames are return relative to root_path. Only filenames that
  extensions are in file_exts (when specified) are returned.

  Content parts are spanstr instances that wrap the content of files.
  """
  if root_path is None:
    root_path = os.getcwd()

  if os.path.isfile(source):
    filename = os.path.relpath(source, root_path)
    content = open(source, 'r', encoding='utf-8-sig').read()
    yield filename, dtype(content)
  elif os.path.isdir(source):
    for dirpath, dnames, fnames in os.walk(source):
      for f in fnames:
        if file_exts is None or os.path.splitext(f)[1] in file_exts:
          fn = os.path.join(dirpath, f)
          yield from iter_sources(fn, file_exts=file_exts, root_path=root_path, dtype=dtype)
  else:
    yield '<string>', spanstr(source)
