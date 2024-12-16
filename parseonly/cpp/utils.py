
def remove_backslashes(text):
  """Return text with backslashes followed by white space till the end
  of a line removed.

  This operation corresponds to the first part of Stage 2 of lex
  translation phases.

  The splicing of physical source lines to logical source lines is
  performed by preserving the number of new lines. This is different
  from the Stage 2 but it will produce still legal input to Stage 3.
  """
  n = len(text)
  stext = [' '] * n
  if text.startswith('\ufeff'):
    stest[0] = ''
    i = 1
  else:
    i = 0
  count = 0  # to preserve newline count
  while i < n:
    if text[i] == '\\':
      k = text.find('\n', i)
      if k == -1:  # end of text
        stext[i] = ''
        i += 1
      elif k == i + 1:
        # backslash followed by new line is removed
        count += 1
        stext[i] = stext[k] = ''
        i = k + 1
      elif text[i + 1:k].isspace():
        # remove backslash and any whitespace but keep newline 
        stext[i:k] = [''] * (k - i)
        i = k
      else:
        # just remove backslash
        stext[i] = ''
        i += 1
    elif text[i] == '\n':
      stext[i] = text[i] + ('\n' * count)
      r = text[i] + ('\n' * count)
      count = 0
      i += 1
    else:
      k = text.find('\\', i)
      m = text.find('\n', i)
      if m != -1 and m < k:
        stext[i:m] = text[i:m]
        i = m
      elif k == -1:
        if count == 0:
          stext[i:] = text[i:]
          break
        else:
          stext[i] = text[i]
          i += 1
      else:
        stext[i:k] = text[i:k]
        i = k

  return ''.join(stext)

def reference_comments(text, label_format='@@@{direction}{count}@@@'):
  """Reference C++ comments in source text.

  For example, if

    text  = '// comment 1\nclass A { int a; /* comment 2 */ };'

  then return a pair (stext, cdict) that contain

    stext  = '@@@>1@@@ class A { @@@<2@@@ };'
    cdict = {'@@@>1@@@': ' comment 1', '@@@<2@@@': ' comment 2 '}

  where symbols < and > indicate if the comment applies to left and
  right tokens, respectively. The following rule applies:

    If the text between the comment and the preceeding new line or
    start of the text contains only whitespace characters, the comment
    applies to right. Otherwise, to the left.

  The newline counts of text and stext are equal.
  """
  n = len(text)
  stext = [' '] * n
  cdict = dict()
  string_sequence = None
  i = 0
  slash_counts = 0
  comment_count = 0
  while i < n:
    if string_sequence:
      if text[i] == '\\':
        slash_counts += 1
      elif text[i] == string_sequence and slash_counts % 2 == 0:
        string_sequence = None
        slash_counts = 0
      else:
        slash_counts = 0
      stext[i] = text[i]
      i += 1
    else:
      if text[i:i+2] == '//':
        m = text.rfind('\n', 0, i)
        if m == -1:
          m = len(text)
        d = '>' if text[m:i].isspace() else '<'
        comment_count += 1
        label = label_format.format(direction=d, count=comment_count)
        k = text.find('\n', i)
        if k == -1:
          k = len(text)
        cdict[label] = text[i + 2:k]
        if k < n:
          stext[k] = text[k]  # newline
        m = min(len(label), k - i)
        stext[i:i + m] = [''] * m
        stext[i] = label
        i = k + 1
        continue
      elif text[i:i+2] == '/*':
        m = text.rfind('\n', 0, i)
        if m == -1:
          d = '>' if text[:i].isspace() else '<'
        else:
          d = '>' if text[m:i].isspace() else '<'
        comment_count += 1
        label = label_format.format(direction=d, count=comment_count)
        k = text.find('*/', i)
        if k == -1:
          k = len(text)
        cdict[label] = text[i + 2:k]
        c = cdict[label].count('\n')
        m = min(len(label) + c, k - i)
        stext[i:i + m] = [''] * (m)
        stext[i] = label
        stext[i + 1] = '\n' * c
        i = k + 2
        continue
      elif text[i] == '"':
        string_sequence = '"'
        slash_counts = 0
      elif text[i] == "'":
        string_sequence = "'"
        slash_counts = 0
      stext[i] = text[i]
      i += 1
  
  stext = ''.join(stext)
  # sanity test: preserving the newline count enables computing the
  # source line numbers correctly.
  c1 = text.count('\n')
  c2 = stext.count('\n')
  if c1 != c2:
    import difflib
    s1 = text.splitlines(keepends=True)
    s2 = stext.splitlines(keepends=True)
    print(''.join(difflib.context_diff(s1, s2, fromfile='input', tofile='output')))
    print('FIXME: the newline count of input and output differ: expected {c1} newlines, the output has {c2}')
  return stext, cdict

def separate_comments(text):
  """Separate C++ comments from source text.

  For example, if

    text  = 'class A { /* comment */ };'

  then return a pair of strings (stext, ctext) that contain

    stext = 'class A {               };'
    ctext = '          /* comment */   '

  that is, the locations of source code tokens and the locations of
  comment blocks are preserved in this separation. Also, stext and
  ctext will share the same white space characters.

  This operation corresponds to Stage 3 of lex translation phases.
  """
  n = len(text)
  stext = [' '] * n
  ctext = [' '] * n
  string_sequence = None
  i = 0
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
      stext[i] = text[i]
      i += 1
    else:
      if text[i:i+2] == '//':
        k = text.find('\n', i)
        if k == -1:  # end of text
          ctext[i:] = text[i:]
          break
        else:
          ctext[i:k + 1] = text[i:k + 1]
          stext[k] = text[k]
        i = k + 1
        continue
      elif text[i:i+2] == '/*':
        k = text.find('*/', i)
        if k == -1:  # end of text
          ctext[i:] = text[i:]
          break
        else:
          ctext[i:k + 2] = text[i:k + 2]
        i = k + 3
        continue
      elif text[i] == '"':
        string_sequence = '"'
        slash_counts = 0
      elif text[i] == "'":
        string_sequence = "'"
        slash_counts = 0
      stext[i] = text[i]
      if text[i].isspace():
        ctext[i] = text[i]
      i += 1
  return ''.join(stext), ''.join(ctext)


