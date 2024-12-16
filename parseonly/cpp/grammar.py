
from ..grammar import grammar, word, switch, keyword, splitter, item_sequence, Context, Grammar, pair_or_item
from ..cxx import grammar as cxx
from ..cxx.grammar import (integer_literal, floating_point_literal, character_literal, user_defined_character_literal, string_literal, user_defined_string_literal)
from . import utils

def splitter_set_cpp_depth(mth):

  def wrapper_splitter_set_cpp_depth(cls, ctx, line, *args, **kwargs):
    r = mth(cls, ctx, line, *args, **kwargs)
    if type(r) is tuple and len(r) == 2 and r[0] is not None:
      r[0]._attributes.update(cpp_depth=ctx.cpp_depth)
    return r

  return wrapper_splitter_set_cpp_depth
  

whitespace_without_newline = ' \t\v\r\f'

class import_keyword(keyword('import_keyword', 'import')):
  pass
class module_keyword(keyword('module_keyword', 'module')):
  pass
class export_keyword(keyword('export_keyword', 'export')):
  pass

class placemarker(grammar('placemarker')):
  """
  Helper specification used in evaluating CPP macros per
    https://timsong-cpp.github.io/cppwp/cpp#concat-2
  """
  format = 'PLACEMARKER'

class do_not_replace(grammar('do_not_replace')):
  """
  Helper specification used in evaluating CPP macros per
    https://timsong-cpp.github.io/cppwp/cpp#rescan-3
  """
  format = '{0}'

class comment_label(grammar('comment_label')):
  @splitter
  def split(cls, ctx, line):
    if line.startswith('@@@'):
      i = line.find('@@@', 3)
      if i != -1:
        return cls(line[:i+3]), line[i+3:]
  
class header_name(grammar('header_name', ['lquote', 'char-sequence', 'rquote'])):
  """
  < h-char-sequence >
  " q-char-sequence "
  """
  format = '{0}{1}{2}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('<'):
      i = line.find('>')
      n = line.find('\n')
      n = len(line) if n == -1 else n
      if i != -1 and i < n:
        return cls(line[:1], line[1:i], line[i:i+1]), line[i+1:]
    if line.startswith('"'):
      i = line.find('"', 1)
      n = line.find('\n')
      n = len(line) if n == -1 else n
      if i != -1 and i < n:
        return cls(line[:1], line[1:i], line[i:i+1]), line[i+1:]

class pp_identifier(grammar('pp_identifier')):
  @splitter
  def split(cls, ctx, line):
    i, rest = word.split(ctx, line)
    if i:
      return cls(i), rest

identifier = pp_identifier

class pp_identifier_list(pair_or_item('pp_identifier_list', ',', pp_identifier)):
  """
  identifier
  identifier-list , identifier
  """

class pp_number(switch('pp_number', floating_point_literal, integer_literal)):
  pass

class preprocessing_operator(grammar('preprocessing_operator')):
  @splitter
  def split(cls, ctx, line):
    for op in ['##', '#', '%:%:', '%:']:
      if line.startswith(op):
        return cls(line[:len(op)]), line[len(op):]

class operator_or_punctuator(grammar('operator_or_punctuator')):
  @splitter
  def split(cls, ctx, line):
    for op in ['...', '->*', '<=>', '<<=', '>>=', '<:', ':>', '<%',
               '%>', '::', '.*', '->', '+=', '-=', '*=', '/=', '%=', '^=', '&=',
               '|=', '==', '!=', '<=', '>=', '&&', '||', '<<', '>>', '++', '--',
               '{', '}', '[', ']', '(', ')', ';', ':', '?', '.', '~', '!', '+',
               '-', '*', '/', '%', '^', '&', '|', '=', '<', '>', ',']:
      if line.startswith(op):
        return cls(line[:len(op)]), line[len(op):]
    w, rest = word.split(ctx, line, require=('bitand', 'and_eq', 'xor_eq', 'not_eq', 'bitor', 'compl', 'or_eq', 'and', 'xor', 'not', 'or'))
    if w:
      return cls(w), rest
    
class preprocessing_op_or_punc(switch(
        preprocessing_operator,
        operator_or_punctuator)):
  """
  preprocessing-operator
  operator-or-punctuator
  """

class non_whitespace_character(grammar('non_whitespace_character')):
  @splitter
  def split(cls, ctx, line):
    if line[:1].isspace():
      return
    if len(line) > 0:
      return cls(line[:1]), line[1:]

class preprocessing_token(switch('preprocessing_token',
                                 import_keyword,
                                 module_keyword,
                                 export_keyword,
                                 pp_number,
                                 character_literal,
                                 user_defined_character_literal,
                                 string_literal,
                                 user_defined_string_literal,
                                 header_name,
                                 preprocessing_op_or_punc,
                                 identifier,
                                 non_whitespace_character)):
  """
  header-name
  import-keyword
  module-keyword
  export-keyword
  identifier
  pp-number
  character-literal
  user-defined-character-literal
  string-literal
  user-defined-string-literal
  preprocessing-op-or-punc
  """

  
class pp_tokens(item_sequence('pp_tokens', preprocessing_token, field='pp_tokens')):
  """
  preprocessing-token
  pp-tokens preprocessing-token
  """

  
  
class header_name_tokens(switch(header_name, string_literal)):
  """
  string-literal
  < h-pp-tokens >
  """

class pp_import(grammar('pp_import', ['export', 'header-name-opt-tokens', 'pp-tokens'])):
  """
  export? import header-name        pp-tokens? ; new-line
  export? import header-name-tokens pp-tokens? ; new-line
  export? import                    pp-tokens  ; new-line
  """
  format = '{0} import {1} {2};\n'
  @splitter
  def split(cls, ctx, line):
    e, rest = export_keyword.split(ctx, line)
    i, rest = import_keyword.split(ctx, rest)
    if i:
      n, rest_ = header_name_tokens.split(ctx, rest)
      if n:
        t, rest_ = pp_tokens.split(ctx, rest_)
        if rest_.startswith(';\n'):
          return cls(e, n, t), rest_[2:]
      n, rest_ = header_name.split(ctx, rest)
      if n:
        t, rest_ = pp_tokens.split(ctx, rest_)
        if rest_.startswith(';\n'):
          return cls(e, n, t), rest_[2:]
      t, rest_ = pp_tokens.split(ctx, rest_)
      if t and rest_.startswith(';\n'):
        return cls(e, n, t), rest_[2:]

  def evaluate(self, ctx):
    print(f"TODO: evaluate {type(self).__name__}: {repr(str(self))}")
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

class replacement_list(grammar('replacement_list', ['pp_tokens'])):
  """
  pp-tokens?
  """
  @splitter
  def split(cls, ctx, line):
    t, rest = pp_tokens.split(ctx, line)
    if t:
      return cls(t), rest  # no lstrip!
    return cls(pp_tokens(())), line

class sharp_include(grammar('sharp_include', ['pp_tokens'])):
  """
# include pp-tokens new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'include {0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='include')
      if d:
        t, rest = pp_tokens.split(ctx, rest)
        if t and rest.startswith('\n'):
          return cls(t), rest[1:]

  def evaluate(self, ctx):
    content = ctx.apply_defines(self[0])

    if 0:
      print(f'Warning: include `{content}` not evaluated')

    return self._replace(pp_tokens=content).resolve(True)

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_define_identifier(grammar('sharp_define_identifier', ['identifier', 'replacement-list'])):
  """
# define  identifier                                replacement-list new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'define {0} {1}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      d, rest = word.split(ctx, rest, require='define')
      if d:
        i, rest = identifier.split(ctx, rest)
        if i and not rest.startswith('('):
          lst, rest = replacement_list.split(ctx, rest)
          if lst and rest.startswith('\n'):
            # identifier is saved here as string because identifier
            # instances will be evaluated:
            return cls(i.content, lst), rest[1:]
          assert 0, rest

  def evaluate(self, ctx):
    # Macros content cannot be evaluated until these are materialized.
    # We can only register/unregister macros.
    pp_tokens = self.replacement_list.pp_tokens
    if pp_tokens is None:
      pp_tokens = ()
    else:
      pp_tokens = pp_tokens.pp_tokens
    ctx.register_define(self.identifier, None, pp_tokens)
    # Since this macro definition is registered, we'll remove the
    # directive. Notice that this preserves the newline count.
    return self.resolve(False)

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class tripledot(grammar('tripledot')):
  @splitter
  def split(cls, ctx, line):
    if line.startswith('...'):
      return cls(line[:3]), line[3:]

class sharp_define_macro(grammar('sharp_define_macro', ['identifier', 'identifier-list', 'dots', 'replacement-list'])):
  """
# define  identifier lparen identifier-list?      ) replacement-list new-line
# define  identifier lparen                   ... ) replacement-list new-line
# define  identifier lparen identifier-list , ... ) replacement-list new-line
  """
  @property
  def format(self):
    tab = '#' + '\t' * self._attributes.get('cpp_depth', 0)      
    if self.identifier_list is None:
      if self.dots is None:
        return tab + 'define {0}() {3}\n'
      return tab + 'define {0}({2}) {3}\n'
    elif self.dots is None:
      return tab + 'define {0}({1}) {3}\n'
    return tab + 'define {0}({1}, {2}) {3}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:], require='define')
      if d:
        i, rest = identifier.split(ctx, rest)
        if i and rest.startswith('('):
          rest = rest[1:].lstrip(ctx.whitespace_characters)
          if rest.startswith(')'):
            lst, rest = replacement_list.split(ctx, rest[1:])
            if lst and rest.startswith('\n'):
              return cls(i.content, None, None, lst), rest[1:]
            return
          dots, rest = tripledot.split(ctx, rest)
          if dots and rest.startswith(')'):
            lst, rest = replacement_list.split(ctx, rest[1:])
            if lst and rest.startswith('\n'):
              return cls(i.content, None, dots, lst), rest[1:]
            return
          args, rest = pp_identifier_list.split(ctx, rest)
          if args:
            dots = None
            if rest.startswith(','):
              dots, rest = tripledot.split(ctx, rest[1:])
              if not dots:
                return
            if rest.startswith(')'):
              lst, rest = replacement_list.split(ctx, rest[1:])
              if lst and rest.startswith('\n'):
                return cls(i.content, args, dots, lst), rest[1:]

  def evaluate(self, ctx):
    # Macros content cannot be evaluated until these are materialized.
    # We can only register/unregister macros.

    #args = tuple(map(str.strip, self.identifier_list.content.split(','))) if self.identifier_list else ()
    #if self.dots is not None:
    #  args += (dots,)

    if self.identifier_list is None:
      args = []
    elif isinstance(self.identifier_list, pp_identifier_list):
      # eliminate commas
      args = list((self.identifier_list[0][0],) + self.identifier_list[0][2::2])
    else:
      args = [self.identifier_list]
    if self.dots is not None:
      args.append(pp_identifier('__VA_ARGS__'))
    # args is list because in apply_defines we'll use args.find(...)

    if self.replacement_list.pp_tokens:
      ctx.register_define(self.identifier, args, self.replacement_list.pp_tokens.pp_tokens)
    else:
      print(f'FAILED TO REGISTER: {self=}')
    # Since this macro definition is registered, we'll remove the
    # directive. Notice that this preserves the newline count.
    return self.resolve(False)

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_undef(grammar('sharp_undef')):
  """
# undef   identifier new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'undef {0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='undef')
      if d:
        i, rest = identifier.split(ctx, rest)
        if i and rest.startswith('\n'):
          return cls(i.content), rest[1:]

  def evaluate(self, ctx):
    # Macros content cannot be evaluated until these are materialized.
    # We can only register/unregister macros.
    ctx.unregister_define(self.content)
    return self.resolve(False)

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_line(grammar('sharp_line')):
  """
# line    pp-tokens new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'line {0}\n'
  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='line')
      if d:
        t, rest = pp_tokens.split(ctx, rest)
        if t and rest.startswith('\n'):
          return cls(t), rest[1:]

  def evaluate(self, ctx):
    print(f"TODO: evaluate {type(self).__name__}: {repr(str(self))}")
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_error(grammar('sharp_error')):
  """
# error    pp-tokens? new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'error {0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='error')
      if d:
        t, rest = pp_tokens.split(ctx, rest)
        if rest.startswith('\n'):
          return cls(t), rest[1:]

  def evaluate(self, ctx):
    print(f"TODO: evaluate {type(self).__name__}: {repr(str(self))}")
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_warning(grammar('sharp_warning')):
  """
# warning    pp-tokens? new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'warning {0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='warning')
      if d:
        t, rest = pp_tokens.split(ctx, rest)
        if rest.startswith('\n'):
          return cls(t), rest[1:]

  def evaluate(self, ctx):
    print(f"TODO: evaluate {type(self).__name__}: {repr(str(self))}")
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_pragma(grammar('sharp_pragma')):
  """
# pragma    pp-tokens? new-line
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'pragma {0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      d, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='pragma')
      if d:
        t, rest = pp_tokens.split(ctx, rest)
        if rest.startswith('\n'):
          return cls(t), rest[1:]

  def evaluate(self, ctx):
    print(f"TODO: evaluate {type(self).__name__}: {repr(str(self))}")
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_newline(grammar('sharp_newline')):
  """
# new-line
  """
  format = '#\n'
  @splitter
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#\n'):
      return cls(''), rest[2:]

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class control_line(switch(pp_import, sharp_include, sharp_define_macro, sharp_define_identifier, sharp_undef, sharp_line, sharp_error, sharp_warning, sharp_pragma, sharp_newline)):
  """
# include pp-tokens new-line
pp-import
# define  identifier                                replacement-list new-line
# define  identifier lparen identifier-list? )      replacement-list new-line
# define  identifier lparen ... )                   replacement-list new-line
# define  identifier lparen identifier-list , ... ) replacement-list new-line
# undef   identifier new-line
# line    pp-tokens new-line
# error   pp-tokens? new-line
# warning pp-tokens? new-line
# pragma  pp-tokens? new-line
# new-line
  """
  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

def _if_group_split(cls, kinds, ctx, line):
  rest = line#.lstrip(ctx.whitespace_characters)
  if rest.startswith('#'):
    kind, rest = word.split(ctx, rest[1:], require=kinds)
    if kind:
      if kind in ['if', 'elif']:
        i = rest.find('\n')
        if i != -1:
          raw = rest[:i]

          k = raw.rfind('@@@')
          label = None
          if k != -1 and raw[k+3:].strip() == '':
            n = raw.rfind('@@@', 0, k-1)
            if n != -1:
              label = raw[n:k+3]
              raw = raw[:n].rstrip()
              print(f'{label=}')
            else:
              assert 0, raw[-100:]  # unreachable

          
          rest = rest[i+1:].lstrip(ctx.whitespace_characters)

          # rewrite `#if defined FOO` as `#if defined(FOO)`
          d, rest_ = word.split(ctx, raw, require='defined')
          rest_ = rest_.lstrip(ctx.whitespace_characters)
          if d and not rest_.startswith('('):
            raw = f'{d}({rest_})'

          e, rest_ = cxx.constant_expression.split(ctx, raw)
          if e:
            if rest_ == '':
              g, rest = group.split(ctx, rest)
              return cls(kind, e, label, g), rest
            assert rest_ == '', rest_
        assert 0, line
      else:
        e, rest = identifier.split(ctx, rest)
        label, rest = comment_label.split(ctx, rest)
        if e and rest.startswith('\n'):
          with ctx.increase_cpp_depth():
            g, rest = group.split(ctx, rest[1:])
            return cls(kind, e, label, g), rest
        assert 0, line
  
class if_group(grammar('if_group', ['kind', 'expression', 'comment-label', 'group'])):
  """
# if      constant-expression comment-label? new-line group?
# ifdef   identifier          comment-label? new-line group?
# ifndef  identifier          comment-label? new-line group?
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}{{0}} {{1}}\n{{3}}'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    return _if_group_split(cls, ['ifdef', 'ifndef', 'if'], ctx, line)

  @classmethod
  def postprocess(cls, ctx, item, rest):

    if isinstance(item, cls):
      if item.kind == 'ifdef':
        # rewrite `#ifdef i` as `#if defined(i)`
        expr = cxx.postfix_expression_call(cxx.identifier('defined'), item.expression)
      elif item.kind == 'ifndef':
        # rewrite `#ifndef i` as `#if !defined(i)`
        expr = cxx.unary_operator_expression('!', cxx.postfix_expression_call(cxx.identifier('defined'), item.expression))
      else:
        expr = None
      if expr is not None:
        item = item._replace(kind='if', expression=expr)

    return item, rest

  @property
  def is_invalid(self):
    if self.kind == 'if' and isinstance(self.expression, (int, bool)) and self.expression == 0:
      return True

  @property
  def is_valid(self):
    if self.kind == 'if' and isinstance(self.expression, (int, bool)) and self.expression != 0:
      return True

  def evaluate(self, ctx):
    assert self.kind == 'if'
    v = self.expression
    if isinstance(v, Grammar):
      v = v.evaluate(ctx)
    return self._replace(expression=v).resolve(v)

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return group((text_line(''), (self.group and self.group.resolve(enable)) or None))
    return self

class elif_group(grammar('elif_group', ['kind', 'expression', 'comment-label', 'group'])):
  """
# elif      constant-expression comment-label? new-line group?
# elifdef   identifier          comment-label? new-line group?
# elifndef  identifier          comment-label? new-line group?
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + '{0} {1}\n{3}'
  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    return _if_group_split(cls, ['elifdef', 'elifndef', 'elif'], ctx, line)

  @classmethod
  def postprocess(cls, ctx, item, rest):
    if isinstance(item, cls):
      if item.kind == 'elifdef':
        # rewrite `#ifdef i` as `#elif defined(i)`
        expr = cxx.postfix_expression_call(cxx.identifier('defined'), item.expression)
      elif item.kind == 'elifndef':
        # rewrite `#ifndef i` as `#elif !defined(i)`
        expr = cxx.unary_operator_expression('!', cxx.postfix_expression_call(cxx.identifier('defined'), item.expression))
      else:
        expr = None
      if expr is not None:
        item = item._replace(kind='elif', expression=expr)
    return item, rest

  @property
  def is_invalid(self):
    if self.kind == 'elif' and isinstance(self.expression, (int, bool)) and self.expression == 0:
      return True

  @property
  def is_valid(self):
    if self.kind == 'elif' and isinstance(self.expression, (int, bool)) and self.expression != 0:
      return True

  def evaluate(self, ctx):
    assert self.kind == 'elif'
    v = self.expression
    if isinstance(v, Grammar):
      v = v.evaluate(ctx)
    return self._replace(expression=v).resolve(v)

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return group((text_line(''), self.group.resolve(enable)))
    return self

  
class elif_groups(item_sequence('elif_groups', elif_group)):
  """
  elif-group
  elif-groups elif-group
  """

  @property
  def is_invalid(self):
    for g in self.content:
      if g.is_valid:
        return False
      if g.is_invalid:
        continue
      break
    else:
      return True

  @property
  def is_valid(self):
    for g in self.content:
      if g.is_valid:
        return True
      if g.is_invalid:
        continue
      break
    else:
      return False

  def resolve(self, enable):
    return type(self)(tuple(item.resolve(enable) for item in self.content))

  
class else_group(grammar('else_group', ['comment-label', 'group'])):
  """
# else comment-label?  new-line group?
  """
  @property
  def format(self):
      tab = '\t' * self._attributes.get('cpp_depth', 0)
      return f'#{tab}' + 'else\n{1}'
  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      kind, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='else')
      if kind:
        label, rest = comment_label.split(ctx, rest)
        if rest.startswith('\n'):
          with ctx.increase_cpp_depth():
            g, rest = group.split(ctx, rest)
            return cls(label, g), rest  

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return group((text_line(''), self.group.resolve(enable)))
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class endif_line(grammar('endif_line')):
  """
# endif comment-label?  new-line
  """
  @property
  def format(self):
    tab = '\t' * self._attributes.get('cpp_depth', 0)
    return f'#{tab}' + 'endif\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      kind, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='endif')
      if kind:
        label, rest = comment_label.split(ctx, rest)
        if rest.startswith('\n'):
          return cls(label), rest[1:]

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return text_line('')
    return self

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class if_section(grammar('if_section', ['if-group', 'elif-groups', 'else-group', 'endif-line'])):
  """
  if-group elif-groups? else-group? endif-line
  """
  format = '{0}{1}{2}{3}'
  @splitter
  def split(cls, ctx, line):
    ifg, rest = if_group.split(ctx, line)
    if ifg:
      elifg, rest = elif_groups.split(ctx, rest)
      elseg, rest = else_group.split(ctx, rest)
      endif, rest = endif_line.split(ctx, rest)
      if endif:
        return cls(ifg, elifg, elseg, endif), rest

  def evaluate(self, ctx):
    ifg, elifg, elseg, endif = self
    ifg = ifg.evaluate(ctx)
    elifg = elifg and elifg.evaluate(ctx)
    elseg = elseg and elseg.evaluate(ctx)
    endif = endif.evaluate(ctx)
    if ifg.is_valid:
      return self._replace(if_group=ifg.resolve(True),
                           elif_groups=elifg and elifg.resolve(False),
                           else_group=elseg and elseg.resolve(False),
                           endif_line=endif.resolve(False))
    if ifg.is_invalid:
      if elifg:
        if elifg.is_valid:
          return self._replace(if_group=ifg.resolve(False),
                           elif_groups=elifg and elifg.resolve(True),
                           else_group=elseg and elseg.resolve(False),
                           endif_line=endif.resolve(False))
        if elifg.is_invalid:
          if elseg:
            return self._replace(if_group=ifg.resolve(False),
                                 elif_groups=elifg and elifg.resolve(False),
                                 else_group=elseg and elseg.resolve(True),
                                 endif_line=endif.resolve(False))
    return self.resolve(True)

  def resolve(self, enable):
    ifg, elifg, elseg, endif = self
    return self._replace(if_group=ifg.resolve(enable),
                         elif_groups=elifg and elifg.resolve(enable),
                         else_group=elseg and elseg.resolve(enable),
                         endif_line=endif.resolve(enable))

  @property
  def is_valid(self):
    return True

  @property
  def is_invalid(self):
    return False

class sharp_conditionally_supported_directive(grammar('sharp_conditionally_supported_directive')):
  """
# conditionally-supported-directive

  conditionally-supported-directive:
    pp-tokens new-line
  """
  @property
  def format(self):
    tab = '\t' * self._attributes.get('cpp_depth', 0)
    return f'#{tab}' + '{0}\n'

  @splitter
  @splitter_set_cpp_depth
  def split(cls, ctx, line):
    rest = line.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      t, rest = pp_tokens.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if t and rest.startswith('\n'):
        return cls(t), rest[1:]

  @classmethod
  def postprocess(cls, ctx, item, rest):
    head = item.content.pp_tokens[0]
    if isinstance(head, identifier) and head.content in {
            'if', 'ifdef', 'ifndef', 'elif', 'elifdef', 'elifndef', 'else', 'endif', 'pragma', 'line', 'warning', 'error', 'undef', 'define', 'include'}:
      return
    return item, rest

  def evaluate(self, ctx):
    # TODO: report
    return self

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self


class text_line(grammar('text_line', ['pp_tokens'])):
  """
pp-tokens? new-line
  """
  format = '{0}\n'
  @splitter
  def split(cls, ctx, line):
    rest = line #.lstrip(ctx.whitespace_characters)
    if rest.startswith('#'):
      return
    if rest.startswith('\n'):
      return cls(''), rest[1:]
    #assert 0, line
    t, rest = pp_tokens.split(ctx, rest)
    if rest.startswith('\n'):
      return cls(t), rest[1:]

  def evaluate(self, ctx):
    if not self[0]:
      return self

    content = ctx.apply_defines(self[0])

    for t in content.pp_tokens:
      if isinstance(t, pp_identifier):
        n = t.content
        if n == n.upper():
          ctx.unevaluated_macros.add(n)
    return self._replace(pp_tokens=content)

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

  @property
  def is_valid(self):
    return True
  @property
  def is_invalid(self):
    return False

class group_part(switch('group_part', control_line, if_section, sharp_conditionally_supported_directive, text_line)):
  """
  control-line
  if-section
  text-line
  # conditionally-supported-directive
  """
  def resolve(self, enable):
    return self.content.resolve(enable)


class group(item_sequence('group', group_part, join_separator='', field='group')):
  """
  group-part
  group group-part
  """
  @classmethod
  def postprocess(cls, ctx, item, rest):
    if item is not None:
      lst = []
      flag = False
      for part in item.group:
        if lst and isinstance(lst[-1], text_line) and isinstance(part, text_line):
          tokens = lst[-1].pp_tokens
          if tokens and isinstance(tokens.pp_tokens[-1], operator_or_punctuator):
            if tokens.pp_tokens[-1].content==',':
              flag= True
              lst.insert(-1, text_line(''))  # to preserve line count
              lst[-1] = lst[-1]._replace(pp_tokens=pp_tokens(tokens + part.pp_tokens))

              continue
        lst.append(part)
      if flag:
        item = item._replace(group=tuple(lst))
    return item, rest

  def resolve(self, enable):
    return type(self)(tuple((item.resolve(enable) if item is not None else item) for item in self.group))

  @property
  def is_valid(self):
    for item in self.group:
      if item is None:
        return
      if item.is_valid:
        continue

      return item.is_valid
    return True

  @property
  def is_invalid(self):
    for item in self.group:
      if item is None:
        return
      if item.is_invalid:
        return True
      if item.is_valid:
        continue
      return item.is_valid
    return False
        

class pp_module(grammar('pp_module', ['export', 'pp-tokens'])):
  """

  export? module pp-tokens? ; new-line
  """
  format = '{0} module {1};\n'
  @splitter
  def split(cls, ctx, line):
    e, rest = export_keyword.split(ctx, line)
    m, rest = module_keyword.split(ctx, rest)
    if m:
      t, rest = pp_tokens.split(ctx, rest)
      if rest.startswith(';\n'):
        return cls(e, t), rest[2:]

  def resolve(self, enable):
    if isinstance(enable, (int, float)):
      if not enable:
        return text_line('')
    return self

class pp_global_module_fragment(grammar('pp_global_module_fragment')):
  """
  module ; new-line group?
  """
  format = 'module;\n{0}'
  @splitter
  def split(cls, ctx, line):
    m, rest = module_keyword.split(ctx, line)
    if m and rest.startswith(';\n'):
      g, rest = group.split(ctx, rest[2:].lstrip(ctx.whitespace_characters))
      return cls(g), rest

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return group((text_line(''), self.group.resolve(enable)))
    return self
  
class pp_private_module_fragment(grammar('pp_private_module_fragment')):
  """
  module : private ; new-line group?
  """
  format = 'module:private;\n{0}'
  @splitter
  def split(cls, ctx, line):
    m, rest = module_keyword.split(ctx, line)
    if m and rest.startswith(':'):
      p, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='private')
      if p and rest.startswith(';\n'):
        g, rest = group.split(ctx, rest[2:].lstrip(ctx.whitespace_characters))
        return cls(g), rest

  def resolve(self, enable):
    if isinstance(enable, (bool, int)):
      return group((text_line(''), self.group.resolve(enable)))
    return self

class module_file(grammar('module_file', ['pp-global-module-fragment', 'pp-module', 'group', 'pp-private-module-fragment'])):
  """
  pp-global-module-fragment? pp-module group? pp-private-module-fragment?
  """
  @splitter
  def split(cls, ctx, line):
    gf, rest = pp_global_module_fragment.split(ctx, line)
    m, rest = pp_module.split(ctx, rest)
    if m:
      g, rest = group.split(ctx, rest)
      pf, rest = pp_private_module_fragment.split(ctx, rest)
      return cls(gf, m, g, pf), rest
  def resolve(self, enable):
    gmf, m, g, pmf = self
    return self._replace(pp_global_module_fragment=gmf and gmf.resolve(enable),
                         pp_module=m.resolve(enable),
                         group=g and g.resolve(enable),
                         pp_private_module_fragment=pmf and pmf.resolve(enable))
  
class preprocessing_file(grammar('preprocessing_file')):
  """
  group?
  module-file
  """
  @splitter
  def split(cls, ctx, line):
    if len(line) == 0:
      return cls(line), line
    m, rest = module_file.split(ctx, line)
    if m:
      return cls(m), rest
    g, rest = group.split(ctx, line)
    if g:
      return cls(g), rest
  def resolve(self, enable):
    return self._replace(content=self.content.resolve(enable))

class CPPContext(Context):
  """Implements CPP macro expansion support.
  """

  def __init__(self, *args, **kwargs):
    if 'whitespace' not in kwargs:
        kwargs.update(whitespace=whitespace_without_newline)
    super().__init__(*args, **kwargs)
    self.defines = dict() # pairs (define name, define value)
    self.unevaluated_macros = set()
    self.smallest_matching_rest_length = 2**63
    self.smallest_non_matching_rest_length = 2**64
    
  def unregister_define(self, name):
    if name in self.defines:
      self.defines.pop(name)
    else:
      print(f'Warning: skipping to undefine of a non-defined CPP macro `{name}`')

  def register_define(self, name, args, body):
    # args is None corresponds to `#define name body`
    sargs = '' if args is None else ('(' + ', '.join(map(str, args)) + ')')
    if name in self.defines:
      print(f'Warning: overriding the definition of CPP macro `{name}{sargs}`')
    else:
      print(f'register CPP macro `{name}{sargs}`: `{" ".join(map(str, body))}`')
    self.defines[name] = (args, body)

  def apply_defines(self, pp_tokens, defines=None):
    if defines is None:
      defines = self.defines

    tmp = placemarker(None)
    va_opt = pp_identifier('__VA_OPT__')
    va_arg = pp_identifier('__VA_ARGS__')
    lparen = operator_or_punctuator('(')
    comma = operator_or_punctuator(',')
    rparen = operator_or_punctuator(')')
    hashhash = preprocessing_operator('##')
    hash = preprocessing_operator('#')

    def get_arguments_list(seq, i, keep_comma=False):
      """Return a list of tokens enclosed in parenthesis and separated by commas:

      ['(', x, a, ',', ..., ')', y, ...] -> [(x, a), ...], seq.index(y, i)
      """
      nn = len(seq)
      assert seq[i] == lparen, (seq[i], lparen)
      save_i = i
      i += 1
      if seq[i] == rparen:
        return [], i + 1
      lst = []      
      stack = []
      arg = []
      while i < nn:
        t = seq[i]
        if stack and t == stack[-1]:
          stack.pop()
        elif not stack and t == rparen:
          lst.append(tuple(arg))
          arg = None  # mark that closing rparen is found
          i += 1
          break
        elif t == lparen:
          stack.append(rparen)
        elif not stack and t == comma:
          if keep_comma:
            arg.append(t)
          lst.append(tuple(arg))
          arg = []  # clean up for the next argument
          i += 1
          continue
        arg.append(t)
        i += 1
      else:
        raise RuntimeError(f'no closing rparen found: `{" ".join(map(str, seq[save_i:500]))}`')
      assert arg is None  # sanity check

      return lst, i

    def adjust_arguments(lst, params):
      """Adjust arguments list to parameters
      """
      if len(lst) == len(params):
        return lst
      if len(lst) > len(params):
        n = len(params)
        va_args = []
        for a in lst[n - 1:]:
          if va_args:
            va_args.append(comma)
          va_args.extend(a)
        lst = lst[:n-1] + [tuple(va_args)]

      if len(lst) <= len(params):
        lst = lst + ([()] * (len(params) - len(lst)))
      else:
        print(f'{lst=} {params=}')
        assert 0  # unreachable, nof parameters is less that nof arguments
      return lst

    def concat(x, y):
      # TODO: this is likely incomplete
      if isinstance(x, placemarker):
        return y
      if isinstance(y, placemarker):
        return x
      if isinstance(x, pp_identifier):
        if isinstance(y, pp_identifier):
          return pp_identifier(x.content + y.content)
        elif isinstance(y, cxx.decimal_literal):
          return pp_identifier(x.content + y.content)
      elif isinstance(x, cxx.decimal_literal):
        if isinstance(y, pp_identifier):
          # invalid that further macro application may resolve
          return pp_identifier(x.content + y.content)
        elif isinstance(y, cxx.decimal_literal):
          return cxx.decimal_literal(x.content + y.content)
      elif isinstance(x, preprocessing_operator) or isinstance(y, preprocessing_operator):
        assert 0  # unreachable
      elif type(x) is tuple:
        if type(y) is tuple:
          r = concat(x[-1], y[0])
          if type(r) is not tuple:
            r = r,
          return x[:-1] + r + y[1:]
      raise NotImplementedError(f'concat({type(x)}, {type(y)})')

    def replace(seq, params, args):
      """
      Replace all occurances of parameters with the corresponding argument values.
      """
      new_seq = []
      for t1 in seq:
        try:
          k = params.index(t1)
        except ValueError:
          new_seq.append(t1)
          continue
        new_seq.extend(args[k])
      return tuple(new_seq)
  
    def expand(tokens):
      new_tokens = []
      skip_k = 0
      for k, t1 in enumerate(tokens):
        if k < skip_k:
          continue
        if isinstance(t1, pp_identifier) and t1.content in defines:
          params1, repl1 = defines[t1.content]
          if params1 is None:
            new_tokens.extend(repl1)
          else:
            if k + 1 >= len(tokens):
              new_tokens.append(t1)
              continue
            args1, skip_k = get_arguments_list(tokens, k + 1)
            args1 = adjust_arguments(args1, params1)
            new_tokens.extend(replace(repl1, params1, args1))
        else:
          new_tokens.append(t1)
      return tuple(new_tokens)

    def token_is_parameter(t, params):
      try:
        params.index(t)
      except ValueError:
        return False
      return True
        
    def as_pp_tokens(a, params, args):
      try:
        k = params.index(a)
      except ValueError:
        return (a,)
      return args[k] or (tmp,)

    def stringize(seq):
      # todo: preserve backslashes
      return cxx.ordinary_string_literal_quotes(''.join([str(item).replace('"', '\\"') for item in seq if item != tmp]))

    def concat_with_expand(seq1, seq2):
      return concat(expand(seq1[:-1]) + (seq1[-1],),  (seq2[0],) + expand(seq2[1:]))

    def worker(seq, defines):

      count = 0
      new_seq = []
      i = 0
      while i < len(seq):
        t = seq[i]
        i += 1
        if not isinstance(t, pp_identifier) or t.content not in defines:
          new_seq.append(t)
          continue

        params, repl_lst = defines[t.content]
        count += 1
        if params is None:
          # object-like macro invocation
          repl_lst = [(do_not_replace(item) if item == t else item) for item in repl_lst if not isinstance(item, placemarker)]
          new_seq.extend(repl_lst)
          continue

        # function-like macro invocation
        nofargs = len(params)
        # Collect arguments to function-like macro call. If macros
        # parameter list ends with `,...`, collect the last arguments
        # into a single sequence that corresponds to __VA_ARGS__
        # parameter:
        assert seq[i] == lparen, seq[:i+1]
        args, i = get_arguments_list(seq, i)
        args = adjust_arguments(args, params)

        # Scan replacement list for parameters and apply concat and
        # stringizing to parameter values. Arguments to parameters
        # that don't participate in concat/stringizing operations,
        # will be expanded.
        lst = []
        skip_j = 0
        keep_va_opt = True
        for j, r in enumerate(repl_lst):
          if j < skip_j:
            # skip tokens consumed by `#` or `##` operatos
            pass
          elif isinstance(r, do_not_replace):
            lst.append(r)
          elif r == hashhash:
            # Concat prev and next token provided that one of these is
            # a parameter
            #  `P`  `##` `P` -> `AA`
            #  `P` `##` `T` -> `AT`
            #  `T`  `##` `P` -> `TA`
            #  `T`  `##` `T` -> `TT`
            # where `A` is argument to in parameter's `P` position. `A` is not expanded.
            a1, a2 = lst.pop(), repl_lst[j + 1]
            lst.extend(concat_with_expand(as_pp_tokens(a1, params, args), as_pp_tokens(a2, params, args)))
            skip_j = j + 2
          elif r == hash:
            # stringize parameters:
            #   `#` `P1` `P2` -> `"` `A1` `"` `E2`
            # where `A` is argument to parameter `P` and `E` is expanded argument.
            a = repl_lst[j + 1]
            # Warning: hash not followed by parameter is
            # illegal. However, here we will allow it.
            lst.append(stringize(expand(as_pp_tokens(a, params, args))))
            skip_j = j + 2
          elif r == va_arg:
            e = expand(as_pp_tokens(r, params, args))
            keep_va_opt = bool([itm for itm in e if not isinstance(itm, placemarker)])
            lst.extend(e)
          elif token_is_parameter(r, params):
            #  `P` -> `A`
            lst.extend(expand(as_pp_tokens(r, params, args)))
          else:
            lst.append(r)

        # Resolve __VA_OPT__ and remaining concat in replacement list.
        j = 0
        m = len(lst)
        new_lst = []
        while j < m:
          r = lst[j]
          j += 1
          if r == va_opt:
            assert lst[j] == lparen
            va_opt_args, j = get_arguments_list(lst, j, keep_comma=True)
            if keep_va_opt:
              new_lst.extend(sum(va_opt_args, ()))
          elif r == hashhash:
            rl = new_lst[-1]
            rr = lst[j]
            new_lst[-1] = concat(rl, rr)
            j += 1
          else:
            assert r != hash  # all hash ops ought to be resolved here
            new_lst.append(r)

        new_seq.extend([(do_not_replace(item) if item == t else item) for item in new_lst if not isinstance(item, placemarker)])

      return new_seq, count
  
    seq = pp_tokens.pp_tokens
    mx = 500  # that should be plenty
    while mx > 0:
      seq_prev = seq
      seq, count = worker(seq, defines)
      if count == 0:
        seq = seq_prev
        break
      mx -= 1

    if seq is pp_tokens.pp_tokens:
      return pp_tokens
    seq = [(item.content if isinstance(item, do_not_replace) else item) for item in seq]
    return pp_tokens._replace(pp_tokens=tuple(seq))

  def rewrite(self, original, new):
    if isinstance(new, Grammar) and 0:
        new = new.evaluate(self)
        # print(f'{original=} -> {new=}')

    if isinstance(new, (sharp_define_identifier, sharp_define_macro, sharp_undef,
                        text_line,
                        sharp_include,
                        if_group, elif_group,
                        if_section)):
      new = new.evaluate(self)

    if isinstance(new, (str, int, float, bool)):
      pass
    elif isinstance(new, cxx.postfix_expression_call):
      if isinstance(new.postfix_expression, str):
        d = new.postfix_expression
      else:
        d = new.postfix_expression.content
      if d == 'defined':
        name = new.expression_list if isinstance(new.expression_list, str) else new.expression_list.content
        if isinstance(name, str):
          return name in self.defines
      print(f'failed to evaluate `{new}`: unknown symbol `{d}`')
    else:
      pass
      # print(type(new))
    return new


  def splitter_postprocess_rest(self, attrs, item, rest):
    if item is None:
      self.smallest_non_matching_rest_length = min(self.smallest_non_matching_rest_length, len(rest))
    else:
      self.smallest_matching_rest_length = min(self.smallest_matching_rest_length, len(rest))
    return super().splitter_postprocess_rest(attrs, item, rest)


def preprocess(text):
  """Return a tree of CPP procession result.

  The count of newline characters is preserved.
  """
  text = utils.remove_backslashes(text)  # Stage 2
  text, ctext = utils.reference_comments(text)  # Stage 3, with comment reference hooks

  ctx = CPPContext(trace=not True)

  with ctx.uses_language('cpp'):
    r, rest = preprocessing_file.split(ctx, text)


  if rest != '':
    print(text)
    print(f'{ctx.smallest_non_matching_rest_length=}')
    print(f'{ctx.smallest_matching_rest_length=}')
    i = len(text) - ctx.smallest_matching_rest_length
    last_matching_line = text[:i]
    k = last_matching_line.rindex('\n') + 1
    last_matching_line = last_matching_line[k:]
    next_non_matching_line = text[i:].lstrip()
    k = next_non_matching_line.find('\n')
    if k == -1:
      k = len(next_non_matching_line)
    next_non_matching_line = next_non_matching_line[:k]
    print(f'{last_matching_line=}')
    print(f'{next_non_matching_line=}')

    print('FAILED TO CPP PARSE')
    return

  r = r.rewrite(ctx)
  r._ctx = ctx

  if ctx.unevaluated_macros:
    print('CPP preprocessor discover the following undefined CPP macros:')
    print('  ', ', '.join(ctx.unevaluated_macros))

  return r
