
def require_and_drop_semicolon(split):
  """Splitter for
  spec ;
  """
  def _require_and_drop_semicolon(cls, ctx, line, *args, **kwargs):
    result = split(cls, ctx, line, *args, **kwargs)
    if type(result) is tuple and len(result) == 2:
      item, rest = result
      if item:
        if rest.startswith(';'):
          return item, rest[1:].lstrip()
        return
    return result
  return _require_and_drop_semicolon

def report_unexpected_block_end(cls, head_lines, rest):
  print(f'{cls.__name__}: unexpected return when parsing the following block:')
  print('v'*120)
  print(head_lines.rstrip())
  print('...... <SNIP LINES> ......')
  #raw, rest_ = split_until(rest, '}', keep_mark=True, require_mark=False)
  if '}' in raw:
    raw = rest[:raw.index('}') + 1]
  else:
    raw = rest
  lines = str(raw).splitlines()
  if len(lines) > 25:
    lines = lines[:15] + [f'...... <SNIP {len(lines) - 25} LINES> ......'] + lines[-5:]
  print('\n'.join(lines))
  print('^'*120)

def split_until_gt(text):
  """Assuming that the preceding character of text was `<` (lt), split
  the text at the matching `>` (gt) position and exclude '>' from the
  return value. If the matching `>` was not found, return (None,
  text).

  Warning: if text contains shift operations (`<<`, '>>'), the result
  will be most likely inaccurate.
  """
  stack = []
  pmap = {'<': '>', '(': ')', '{': '}', '[': ']'}
  n = len(text)
  i = 0
  string_sequence = None
  slash_counts = 0
  while i < n:
    if string_sequence:
      if text[i] == '\\':
        slash_counts += 1
      elif text[i] == string_sequence and slash_counts % 2 == 0:
        string_sequence = None
        slash_counts = 0
      else:
        slash_counts = 0
    elif text[i] == '"':
      string_sequence = '"'
      slash_counts = 0
    elif text[i] == "'":
      string_sequence = "'"
      slash_counts = 0
    elif not stack and text[i] == '>':
      return text[:i], text[i+1:]
    elif text[i] in pmap:
      stack.append(pmap[text[i]])

    elif stack and text[i] == stack[-1]:
      stack.pop()
    i += 1
  return None, text
