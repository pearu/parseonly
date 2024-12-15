"""
Utilities for describing grammar.
"""
import sys
import contextlib
import collections

class _REQUIRED(object):
  """A singleton object representing a required argument in namedtuple
  subclasses.
  """
REQUIRED = _REQUIRED()


class _UNEXPECTED(object):
  """A singleton object representing an unexpeted event in parsing C++
  that parser will report as debug messages to the user.
  """
UNEXPECTED = _UNEXPECTED()


class _TBD(object):
  """A singleton object representing a to-be-defined attribute in
  namedtuple subclasses.
  """
  def tostring(self, tab=''):
    return 'TBD'
TBD = _TBD()

class _MISSING_KEY(object):
  """A singleton object representing missing key in split cache.
  """
MISSING_KEY = _MISSING_KEY()


class Context:
  """
  Holds a set of states of a parsing process.
  """
  def __init__(self, source=None, debug=False, enable_debug_rerun=False,
               whitespace = ' \t\v\r\f\n',
               trace=False):
    # TODO: move this out
    sys.setrecursionlimit(5000)

    # when true, stop parsing
    self.stop = False
    self.debug = debug

    self._unique_counter = 0

    self.detect_recurrence = dict()  # holds pairs (cls name, line)
    self.enable_abstract_declarator = False

    # Language standard/dialect-version
    self.language = 'unspecified'

    # For preprocessing CPP
    self.cpp_depth = 0
    
    # For tracing splitter process:
    self.enable_splitter_trace = trace
    self.splitter_depth = 0

    # For applying lstrip() to rest part of the splitter result:
    self.whitespace_characters = whitespace

    # Cache of splitting results:
    self.splitter_cache = dict()  # holds pairs (key, cls.split(ctx, line))

  @property
  def tab(self):
    return ' ' * self.split_depth

  def abstract_declarator(self, enable=True):
    class context(contextlib.ContextDecorator):
      def __init__(self, ctx, desired_state):
        self.ctx = ctx
        self.saved_state = None
        self.desired_state = desired_state
      def __enter__(self):
        assert self.saved_state is None
        self.saved_state = self.ctx.enable_abstract_declarator
        self.ctx.enable_abstract_declarator = self.desired_state
      def __exit__(self, exc_type, exc, exc_tb):
        assert self.saved_state is not None
        self.ctx.enable_abstract_declarator = self.saved_state
        self.saved_state = None
    return context(self, enable)

  def increase_cpp_depth(self):
    class context(contextlib.ContextDecorator):
      def __init__(self, ctx, desired_state):
        self.ctx = ctx
        self.saved_state = None
        self.desired_state = desired_state
      def __enter__(self):          
        assert self.saved_state is None
        self.saved_state = self.ctx.cpp_depth
        self.ctx.cpp_depth = self.desired_state
      def __exit__(self, exc_type, exc, exc_tb):
        assert self.saved_state is not None
        self.ctx.cpp_depth = self.saved_state
        self.saved_state = None
    return context(self, self.cpp_depth + 1)

  def uses_language(self, language):
    class context(contextlib.ContextDecorator):
      def __init__(self, ctx, desired_state):
        self.ctx = ctx
        self.saved_state = None
        self.desired_state = desired_state
      def __enter__(self):          
        assert self.saved_state is None
        self.saved_state = self.ctx.cpp_depth
        self.ctx.language = self.desired_state
      def __exit__(self, exc_type, exc, exc_tb):
        assert self.saved_state is not None
        self.ctx.language = self.saved_state
        self.saved_state = None
    return context(self, language)

  def supports_language(self, language):
    """Check if parser context language is a superset of specified language.

    For example, if context language is `cpp`, then

      context.supports_language('c++') -> False

    because cpp constant-expression (always evaluates as int) is a
    subset of c++ constant-expression. This allows to skip parsing C++
    specifications (such as template-id) that are not defined in CPP.

    On the other hand, if context language is `c++`, then

      context.supports_language('cpp') -> False

    because cpp directives, for instance, are not a part of C++ language.

    context.supports_language is meant to be used in splitter methods
    to skip parsing parts that make sense only for a given context
    language. For example, if context language is `cpp`, then inserting

      if ctx.supports_language('c++'):
        return

    into, say, simple_template_id.split method will skip parsing the
    input line with simple-template-id specification.
    """
    if language is None:
      return True

    if self.language.startswith('cpp') and language.startswith('c++'):
      return False
    if self.language.startswith('c++') and language.startswith('cpp'):
      return False
    return True

  def splitter_preprocess_line(self, cls, line):
    """Return splitter preprocessed line and a dictionary that
    will be passed to splitter_preprocess_rest call.
    """
    whitespace = getattr(cls, "whitespace_characters", self.whitespace_characters)
    if whitespace:
      return line.lstrip(whitespace), {}
    return line, {}

  def splitter_postprocess_rest(self, attrs, item, rest):
    """Extract suffix attributes from splitter line and apply to item.
    """
    if isinstance(item, str):
      return item, rest
    whitespace = getattr(type(item), "whitespace_characters", self.whitespace_characters)
    if whitespace:
      return item, rest.lstrip(whitespace)
    return item, rest

  def rewrite(self, original, new):
    """Default rewrite implementation that is called after applying
    rewrite to the original field values.
    """
    return new

def splitter_trace(mth):

  def wrapper_splitter_trace(cls, ctx, line, *args, **kwargs):
    if not ctx.enable_splitter_trace:
      return mth(cls, ctx, line, *args, **kwargs)
    verbose = cls.__name__ not in {'word'}
    tab = ctx.splitter_depth * ' '
    if verbose:
      input_line = line[:40].tostring() if not isinstance(line, str) else line[:40]
      print(f'>{tab}<{cls.__name__}({input_line=})')
    ctx.splitter_depth += 1
    r = mth(cls, ctx, line, *args, **kwargs)
    ctx.splitter_depth -= 1
    if verbose:
      if r is not None and r[0] is not None:
        rest_line = r[1][:40]
        print(f'!{tab}{cls.__name__}>item=`{r[0]}` {rest_line=}')
        #assert isinstance(r[1], spanstr), r[1]
      else:
        print(f' {tab}{cls.__name__}>')
    return r

  return wrapper_splitter_trace

def splitter_process_line_and_rest(mth):
  def wrapper_splitter_process_line_and_rest(cls, ctx, line, *args, **kwargs):
    line, attrs = ctx.splitter_preprocess_line(cls, line)
    r = mth(cls, ctx, line, *args, **kwargs)
    if type(r) is tuple and len(r) == 2 and r[0] is not None:
      return ctx.splitter_postprocess_rest(attrs, r[0], r[1])
    return r
  return wrapper_splitter_process_line_and_rest

def splitter_cache(mth):
  def wrapper_splitter_cache(cls, ctx, line, *args, **kwargs):
    if args or kwargs:
      return mth(cls, ctx, line, *args, **kwargs)

    # TODO: holding the whole line in cache could be wasteful,
    # consider hashing or len but be aware that some parts of the
    # parser may use substrings as line argument.
    key = (cls.__name__, line)
    r = ctx.splitter_cache.get(key, MISSING_KEY)
    if r is not MISSING_KEY:
      return r

    r = mth(cls, ctx, line, *args, **kwargs)

    if type(r) is tuple and len(r) == 2 and r[0] is not None:
      ctx.splitter_cache[key] = r
    return r

  return wrapper_splitter_cache

def splitter(mth):
  """Decorator of a classmethod split that a grammar specification type
  may define.

  The class method split is an entry point to parsing a string
  containing C++ grammar specifications.

  When a class method split is applied to a string `line`, it may
  return

  - a pair `(grammar_specification, rest)` where grammar
    specification is constructed by consuming the content of the head
    part of the `line` string and `rest` is the tail part of the line.
  - a pair `(None, line)` when the head of the line does not match
    the grammar specification
  - `None`, equivalent to `(None, line)`
  - `UNEXPECTED`, equivalent to `(None, line)` but with a warning
    message about unexpected mismatch.
  - `NotImplemented`, equivalent to `(None, line)` but with a warning
    message about unimplemented grammar specification support.
  - Anything else will raise a ValueError about unexpected return value.

  """

  @splitter_cache
  @splitter_trace
  @splitter_process_line_and_rest
  def wrapper(cls, ctx, line, *args, **kwargs):
    # sanity checks:
    assert isinstance(ctx, Context)
    assert line is not None

    if ctx.stop:
      return None, line

    last_line = ctx.detect_recurrence.get(cls.__name__)
    if last_line is not None and last_line == line:
      return None, line
    ctx.detect_recurrence[cls.__name__] = line

    r = mth(cls, ctx, line, *args, **kwargs)

    ctx.detect_recurrence.pop(cls.__name__, None)

    if r is UNEXPECTED:
      print(f'{cls.__name__} unexpected mismatch')
      return (None, line)
    
    if r is None:
      # normal mismatch
      return (None, line)

    if r is NotImplemented:
      print(f'{cls.__name__} match not implemented')
      return (None, line)

    if not (type(r) is tuple and len(r) == 2):
      raise ValueError(f'{cls.__name__}.split is expected to return None, UNEXPECTED, NotImplemented, or 2-tuple, but got {type(r).__name__}.')
  
    result, rest = r

    # postprocessing may continue parsing or undo parsing result
    r = cls.postprocess(ctx, result, rest)
    if r is None:
      return None, line

    if not (type(r) is tuple and len(r) == 2):
      raise ValueError(f'{cls.__name__}.postprocess is expected to return None or 2-tuple, but got {type(r).__name__}.')

    return r

  return classmethod(wrapper)


class Grammar:

  _join_separator = ' '
  
  def __eq__(self, other):
    return type(self) is type(other) and tuple(self) == tuple(other)

  def __str__(self):
    fmt = getattr(self, 'format', None)

    if self._fields == ('content',) or self._fields == (type(self).__name__,):
      if isinstance(self[0], list):
        return ', '.join(map(str, self[0]))
      elif type(self[0]) is tuple:
        return self._join_separator.join(map(str, self[0]))
      if fmt is None:
        fmt = '{0}'

    if fmt is not None:
      lst = []
      for i in range(len(self._fields)):
        if self[i] is None:
          s = ''
        else:
          s = str(self[i])
        lst.append(s)
        if not s:
          fmt = fmt.replace(f'{{{i}}} ', '').replace(f' {{{i}}}', '').replace(f'{{{i}}}', '')
      return fmt.format(*lst)
    return ' '.join([str(v) for k, v in self._asdict().items() if v is not None])

  def tostring(self, tab=''):

    def worker(obj, tab=''):
      if isinstance(obj, str):
        return tab + repr(obj)
      #elif isinstance(obj, spanstr):
      #  return obj.tostring(with_location=True)
      elif type(obj) is tuple:
        s = ',\n'.join([worker(item, tab=tab + ' ') for item in obj])
        if len(obj) == 1:
          s += ','
        return f'({s.lstrip()})'
      elif type(obj) is list:
        s = ',\n'.join([worker(item, tab=tab + ' ') for item in obj])
        return f'[{s.lstrip()}]'
      elif obj is None:
        return 'N/A'
      elif hasattr(obj, 'tostring'):
        return obj.tostring(tab=tab)
      return f'{tab}{obj}'

    def prefix(obj):
      if hasattr(obj, '_alt_path'):
        p = '->'.join(obj._alt_path)
        if p:
          p += '->'
      else:
        p = ''
      return p

    # p = prefix(self)
    p = ''
    lines = [f'{tab}{p}{type(self).__name__}{{']
    c = 0
    nitems = len([k for k, v in self._asdict().items() if v is not None])
    suf = ';' if nitems > 1 else ''
    for i, n in enumerate(self._fields):
      if self[i] is None:
        continue
      s = worker(self[i], tab=tab + '  ').lstrip()
      c += len(s)
      if n == type(self[i]).__name__ or n == type(self).__name__:
        s = f'{tab}  {s}{suf}'
      else:
        s = f'{tab}  {n}:{s}{suf}'
      lines.append(s)
    lines.append(f'{tab}}}')

    if c < 80 and nitems < 2:
      lines = [lines[0] + ' '.join(map(str.strip, lines[1:-1])) + lines[-1].lstrip()]
    return '\n'.join(lines)

  @splitter
  def split(cls, ctx, line, *args, **kwargs):
    keywords = cls.split_keywords()
    if keywords is not None:
      w, rest = word.split(ctx, line)
      if w and w in keywords:
        return cls(w), rest
      return
    return NotImplemented

  @classmethod
  def postprocess(cls, ctx, spec, rest):
    return spec, rest

  def rewrite(self, ctx):
    """Default implementation applies ctx.rewrite to its field values and
    returns a new instance with updated values.
    """

    def worker(obj):
      if isinstance(obj, Grammar):
        return obj.rewrite(ctx)
      elif isinstance(obj, (tuple, list)):
        return type(obj)(item.rewrite(ctx) if isinstance(item, Grammar) else ctx.rewrite(item, item) for item in obj)
      return ctx.rewrite(obj, obj)

    updates = dict()
    for k, v in self._asdict().items():
      w = worker(v)
      if w is not v and w != v:
        updates[k] = w
    new = self._replace(**updates) if updates else self
    return ctx.rewrite(self, new)

  def evaluate(self, ctx):
    return self

  @property
  def _attributes(self):
    if not hasattr(self, '_attributes_'):
      self._attributes_ = {}
    return self._attributes_

  def _replace(self, *args, **kwargs):
    new = super()._replace(*args, **kwargs)
    new._attributes.update(self._attributes)
    return new

def grammar(name, field_names=None, *, defaults=None, members={}, split=None):
  """An enhanced namedtuple function.

  Returns a new Python type representing a grammar specification.
  """
  if field_names is None:
    field_names = ['content']
    if defaults is None:
      defaults = [REQUIRED]
  field_names = [name.replace('-', '_').strip() for name in field_names]

  bases = (Grammar, collections.namedtuple(name, field_names, defaults=defaults))
  return type(name, bases, members)

def _resolve_name_and_specs(args):
  if isinstance(args[0], str) and args[0].isidentifier():
    name = args[0]
    specs = args[1:]
  else:
    specs = args
    smap = {',': 'comma', ':': 'colon'}
    name = '_'.join(smap.get(a, a) if isinstance(a, str) else (f'lambda_{id(a)}' if a.__name__ == '<lambda>' else a.__name__) for a in args)
  return name, specs

def _spec_iter(specs):
  for spec in specs:
    if callable(spec) and spec.__name__ == '<lambda>':
      spec = spec()
    if type(spec) is not tuple:
      spec = spec,
    for s in spec:
      yield s

def _str_split(ctx, prefix, line):
  line, attrs = ctx.splitter_preprocess_line(str, line)
  if line.startswith(prefix):
    item, rest = line[:len(prefix)], line[len(prefix):]
  else:
    item, rest = None, line
  return ctx.splitter_postprocess_rest(attrs, item, rest)
    
def item_sequence(*args, **kwargs):
  """
  item
  spec item
  """
  join_separator = kwargs.get('join_separator', ' ')
  field = kwargs.get('field', 'content')
  name, (item,) = _resolve_name_and_specs(args)
  if name != args[0]:
    name += '_seq'
    
  def item_sequence_split(cls, ctx, line):
    i, rest = cls._item.split(ctx, line)
    if i:
      j, rest_ = item_sequence_split(cls, ctx, rest)
      if j:
        return cls((i,) + j[0]), rest_
      return cls((i,)), rest
    return None, line

  return grammar(name, [field],
                 members=dict(
                     _join_separator = join_separator,
                     _item=item, split=splitter(item_sequence_split)))

def pair_or_item(*args):
  """
  item
  spec separator item
  """
  name, (separators, item) = _resolve_name_and_specs(args)
  if name != args[0]:
    name += '_seq'
  
  separators = (separators,) if isinstance(separators, str) else separators
  recursive = True
  def pair_or_item_split(cls, ctx, line, left=None):
    if left is None:
      left, rest = cls._item.split(ctx, line)
    else:
      rest = line
    if left:
      for sep in cls._separators:
        if isinstance(sep, str):
          s, rest_ = _str_split(ctx, sep, rest)
        else:
          s, rest_ = sep.split(ctx, rest)
        if s is None:
          continue
        right, rest_ = cls._item.split(ctx, rest_)
        if right:
          item = cls((left.content if type(left) is cls else (left,)) + (s, right))
          if recursive:
            r = pair_or_item_split(cls, ctx, rest_, left=item)
            if r is not None:
              return r
          return item, rest_              
      return left, rest

  return grammar(name, ['content'],
                 members=dict(_item=item, _separators=separators,
                              split=splitter(pair_or_item_split)))

def item_optional_suffix(item, suffix):
  """
  item suffix?
  """
  sname = suffix if isinstance(suffix, str) else suffix.__name__
  sname = sname.replace('...', 'dots').replace('.', 'dot').replace(':', 'colon')
  name = f'{item.__name__}_optional_{sname}'
  @splitter
  def item_optional_suffix_split(cls, ctx, line):
    i, rest = cls._item.split(ctx, line)
    if i:
      if isinstance(cls._suffix, str):
        t, rest = _str_split(ctx, cls._suffix, rest)
      else:
        t, rest = cls._suffix.split(ctx, rest)
      if t is not None:
        return cls(i, t), rest
      return i, rest
  return grammar(name, ['content', 'suffix'],
                 members=dict(_item=item, _suffix=suffix, split=item_optional_suffix_split))

def item_optional_prefix(item, prefix):
  """
  prefix? item
  """
  pname = prefix if isinstance(prefix, str) else prefix.__name__
  pname = pname.replace('...', 'dots').replace('.', 'dot').replace(':', 'colon')
  name = f'optional_{pname}_{item.__name__}'
  @splitter
  def item_optional_prefix_split(cls, ctx, line):
    if isinstance(cls._prefix, str):
      t, rest = _str_split(ctx, cls._prefix, line)
    else:
      t, rest = cls._prefix.split(ctx, line)
    i, rest = cls._item.split(ctx, rest)
    if i:
      if t is not None:
        return cls(t, i), rest
      return i, rest
  return grammar(name, ['prefix', 'content'],
                    members=dict(_item=item, _prefix=prefix,
                                 split=item_optional_prefix_split))

def switch(*args, **kwargs):
  """
  spec1
  spec2
  ...
  """
  name, specs = _resolve_name_and_specs(args)
  require_language = kwargs.get('require_language', None)
  
  @splitter
  def switch_split(cls, ctx, line):
    if not ctx.supports_language(cls._require_language):
      return
    specs = cls._grammar_specs
    rest = line
    for spec in _spec_iter(specs):
      if isinstance(spec, str):
        item, rest = _str_split(ctx, spec, line)
      else:
        item, rest = spec.split(ctx, line)
      if item is not None:
        return item, rest

  return grammar(name, ['unused'], members=dict(_grammar_specs=specs, split=switch_split,
                                                _require_language=require_language))


def sequence(*args):
  """
  spec1 spec2 ...
  """
  name, specs = _resolve_name_and_specs(args)

  @splitter
  def sequence_split(cls, ctx, line):
    print(f'{line=}')
    rest = line
    lst = []
    for i, spec in enumerate(_spec_iter(cls._grammar_specs)):
      if isinstance(spec, str):
        item, rest = _str_split(ctx, spec, rest)
      else:
        item, rest = spec.split(ctx, rest)
      if item:
        lst.append(item)
      else:
        return
    return cls(tuple(lst)), rest
      
  return grammar(name, ['content'],
                 members=dict(_grammar_specs=specs, split=sequence_split,))

def keyword(*args):
  """
  keyword1
  keyword2
  ...
  """
  name, specs = _resolve_name_and_specs(args)
  if name != args[0]:
    name += '_'

  @splitter
  def keyword_split(cls, ctx, line):
    specs = cls._grammar_specs
    rest = line
    for spec in _spec_iter(specs):
      item, rest = _str_split(ctx, spec, line)
      if item is not None:
        return cls(item), rest

  return grammar(name, ['unused'], members=dict(_grammar_specs=specs, split=keyword_split))
  
class word(grammar('word')):
  """Matches
  [a-zA-Z_][a-zA-Z_0-9]*
  """

  @staticmethod
  def startswith_identifier(s):
    # TODO: XID_Continue
    return s and (s[0].isalnum() or s[0] == '_')

  @staticmethod
  def startswith_identifier0(s):
    # TODO: XID_Start
    return s and (s[0].isalpha() or s[0] == '_')

  @splitter
  def split(cls, ctx, line, strip=True, require=None, discard=None):
    """Return a pair (word, rest) such that
      line = word + rest
    where word is maximal.
    """
    # TODO: use re for faster processing
    if line and cls.startswith_identifier0(line):
      word, rest = line, line[len(line):]
      for i in range(1, len(line)):
        if not cls.startswith_identifier(line[i]):
          word = line[:i]
          rest = line[i:]
          break
      if strip:
        rest = rest.lstrip(ctx.whitespace_characters)
      if isinstance(require, str):
        if word != require:
          return
      elif isinstance(require, (tuple, list, set)):
        if word not in require:
          return
      elif isinstance(discard, str):
        if word == discard:
          return
      elif isinstance(discard, (tuple, list, set)):
        if word in discard:
          return
      elif discard is None and require is None:
        pass
      else:
        assert 0, (type(require), type(discard))  # unreachable     
      return word, rest
