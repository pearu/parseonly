import re
from ..grammar import grammar, Context, splitter, word, item_sequence, pair_or_item, item_optional_prefix, item_optional_suffix, switch, keyword, sequence
from .. import utils

# A set of all C++ keywords
keyword_identifiers = {"alignas", "alignof", "and", "and_eq", "asm",
                       "atomic_cancel", "atomic_commit", "atomic_noexcept",
                       "auto", "bitand", "bitor", "bool", "break", "case",
                       "catch", "char", "char8_t", "char16_t", "char32_t",
                       "class", "compl", "concept", "const", "consteval",
                       "constexpr", "constinit", "const_cast", "continue",
                       "co_await", "co_return", "co_yield", "decltype",
                       "default", "delete", "do", "double", "dynamic_cast",
                       "else", "enum", "explicit", "export", "extern", "false",
                       "float", "for", "friend", "goto", "if", "inline", "int",
                       "long", "mutable", "namespace", "new", "noexcept", "not",
                       "not_eq", "nullptr", "operator", "or", "or_eq", "private",
                       "protected", "public", "reflexpr", "register",
                       "reinterpret_cast", "requires", "return", "short",
                       "signed", "sizeof", "static", "static_assert",
                       "static_cast", "struct", "switch", "synchronized",
                       "template", "this", "thread_local", "throw", "true",
                       "try", "typedef", "typeid", "typename", "union",
                       "unsigned", "using", "virtual", "void", "volatile",
                       "wchar_t", "while", "xor", "xor_eq"}

special_identifiers = {'final', 'import', 'module', 'override'}

keyword_and_special_identifiers = keyword_identifiers.union(special_identifiers)

# A set of all C++ operators
operators = {">>=", "<<=", "<=>", "->*", "==", "!=", "<=", ">=",
             "&&", "||", "++", "--", "->", "+=", "-=", "*=", "/=",
             "%=", "^=", "&=", "|=", "<<", ">>", ",", "+", "-", "*",
             "/", "%", "^", "&", "|", "~", "!", "=", "<", ">", "()",
             "[]", "new", "delete", "co_wait"}

def startswith_token(line, token):
  """
preprocessing-operator: one of
#        ##       %:       %:%:
operator-or-punctuator: one of
{        }        [        ]        (        )
<:       :>       <%       %>       ;        :        ...
?        ::       .        .*       ->       ->*      ~
!        +        -        *        /        %        ^        &        |
=        +=       -=       *=       /=       %=       ^=       &=       |=
==       !=       <        >        <=       >=       <=>      &&       ||
<<       >>       <<=      >>=      ++       --       ,
and      or       xor      not      bitand   bitor    compl
and_eq   or_eq    xor_eq   not_eq
  """
  if token == ':':
    return line.startswith(':') and not (line.startswith('::') or line.startswith(':>'))
  elif token == '<:':
    return line.startswith('<:') and not (line.startswith('<::'))
  elif token == '<':
    return line.startswith('<') and not (line.startswith('<<') or startswith_token(line, '<:') or line.startswith('<=') or line.startswith('<%'))
  elif token == '<<':
    return line.startswith('<<') and not (line.startswith('<<='))
  elif token == '>>':
    return line.startswith('>>') and not (line.startswith('>>='))
  elif token == '->':
    return line.startswith('->') and not (line.startswith('->*'))
  elif token == '>':
    return line.startswith('>') and not (line.startswith('>>') or line.startswith('>='))
  elif token == '.':
    return line.startswith('.') and not (line.startswith('..') or line.startswith('.*'))
  elif token == '%':
    return line.startswith('%') and not (line.startswith('%>') or line.startswith('%=') or line.startswith('%:'))
  elif token == '%:':
    return line.startswith('%:') and not (line.startswith('%:%:'))
  elif token == '=':
    return line.startswith('=') and not (line.startswith('=='))
  elif token == '/':
    return line.startswith('/') and not (line.startswith('/='))
  elif token == '^':
    return line.startswith('^') and not (line.startswith('^='))
  elif token == '*':
    return line.startswith('*') and not (line.startswith('*='))
  elif token == '+':
    return line.startswith('+') and not (line.startswith('+=') or line.startswith('++'))
  elif token == '-':
    return line.startswith('-') and not (line.startswith('-=') or line.startswith('--'))
  elif token == '!':
    return line.startswith('!') and not (line.startswith('!='))
  elif token == '&':
    return line.startswith('&') and not (line.startswith('&&') or line.startswith('&='))
  elif token == '|':
    return line.startswith('|') and not (line.startswith('||') or line.startswith('|='))
  elif token == '#':
    return line.startswith('#') and not (line.startswith('##'))
  return line.startswith(token)


class identifier(grammar('identifier')):
  """
  identifier-start
  identifier identifier-continue


  identifier-start:
    nondigit
    an element of the translation character set with the Unicode property XID_Start

  identifier-continue:
    digit
    nondigit
    an element of the translation character set with the Unicode property XID_Continue

  nondigit: one of
a b c d e f g h i j k l m
n o p q r s t u v w x y z
A B C D E F G H I J K L M
N O P Q R S T U V W X Y Z _

  digit: one of
0 1 2 3 4 5 6 7 8 9
  """

  @splitter
  def split(cls, ctx, line):
    return word.split(ctx, line, discard=keyword_and_special_identifiers)

class identifier_with_a_dot(grammar('identifier_with_a_dot')):
  """
  identifier .
  """
  format = '{0}.'
  @splitter
  def split(cls, ctx, line):
    i, rest = identifier.split(ctx, line)
    if i and rest.startswith('.'):
      return cls(i), rest[1:]


class class_key(keyword('class_key', 'class', 'struct', 'union')):
  """
  """

@splitter
def any_integer_literal_split(cls, ctx, line):
  for p in cls._prefixes:
    if line.startswith(p):
      i = len(p)
      if cls._required_digits and (i >= len(line) or str(line[i]) not in cls._required_digits):
        continue
      while i < len(line) and str(line[i]) in cls._digits:
        i += 1
      return cls(line[:i]), line[i:]

class binary_literal(grammar('binary_literal',
                             members=dict(
                                 split = any_integer_literal_split,
                                 _prefixes=['0b', '0B'],
                                 _required_digits='01',
                                 _digits="01'"))):
  """
  0b binary-digit
  0B binary-digit
  binary-literal '? binary-digit

  binary-digit: one of
  0  1
  """


class octal_literal(grammar('octal_literal',
                               members=dict(
                                   split = any_integer_literal_split,
                                   _prefixes=['0'],
                                   _required_digits=None,
                                   _digits="01234567'"))):
  """
  0
  octal-literal '? octal-digit

  octal-digit: one of
  0  1  2  3  4  5  6  7
  """
  def evaluate(self, ctx):
    return int(self.content.replace("'", ''), 8)
  
class decimal_literal(grammar('decimal_literal',
                               members=dict(
                                   split = any_integer_literal_split,
                                   _prefixes=[''],
                                   _required_digits='123456789',
                                   _digits="0123456789'"))):
  """
  nonzero-digit
  decimal-literal '? digit
  """
  def evaluate(self, ctx):
    return int(self.content.replace("'", ''))

  
class hexadecimal_literal(grammar('hexadecimal_literal',
                                  members=dict(
                                      split = any_integer_literal_split,
                                      _prefixes=['0x', '0X'],
                                      _required_digits='0123456789abcdefABCDEF',
                                      _digits="0123456789abcdefABCDEF'"))):
  """
  hexadecimal-prefix hexadecimal-digit-sequence

  hexadecimal-prefix: one of
  0x  0X

  hexadecimal-digit-sequence:
    hexadecimal-digit
    hexadecimal-digit-sequence '? hexadecimal-digit

  hexadecimal-digit: one of
  0 1 2 3 4 5 6 7 8 9
  a b c d e f
  A B C D E F
  """

class any_integer_literal(switch(binary_literal, hexadecimal_literal, octal_literal, decimal_literal)):
  pass

class integer_suffix(keyword('integer_suffix',
                             'llu', 'LLu', 'llU', 'LLU',
                             'ull', 'Ull', 'uLL', 'ULL',
                             'ul', 'Ul', 'uL', 'UL',
                             'uz', 'Uz', 'uZ', 'UZ',
                             'lu', 'Lu', 'lU', 'LU',
                             'zu', 'Zu', 'zU', 'ZU',
                             'll', 'LL',
                             'u', 'U',
                             'l', 'L',
                             'z', 'Z')):
  """
  unsigned-suffix long-suffix?
  unsigned-suffix long-long-suffix?
  unsigned-suffix size-suffix?
  long-suffix unsigned-suffix?
  long-long-suffix unsigned-suffix?
  size-suffix unsigned-suffix?

  unsigned-suffix: one of
  u U
  long-suffix: one of
  l L
  long-long-suffix: one of
  ll LL
  size-suffix: one of
  z  Z
  """

class integer_literal(item_optional_suffix(any_integer_literal, integer_suffix)):
  """
  binary-literal integer-suffix?
  octal-literal integer-suffix?
  decimal-literal integer-suffix?
  hexadecimal-literal integer-suffix?
  """

class hexadecimal_digit_sequence(grammar('hexadecimal_digit_sequence')):
  """
  hexadecimal-digit
  hexadecimal-digit-sequence '? hexadecimal-digit
  """

  @splitter
  def split(cls, ctx, line):
    i = None
    for i_ in range(len(line)):
      if (i_ and line[i_].startswith("'")) or str(line[i_]) in 'abcdefABCDEF0123456789':
        i = i_ + 1
        continue
      break
    if i is not None:
      return cls(line[:i]), line[i:]

class digit_sequence(grammar('digit_sequence')):
  """
  digit
  digit-sequence '? digit
  """
  @splitter
  def split(cls, ctx, line):
    i = None
    for i_ in range(len(line)):
      if line[i_].isdigit() or (i_ and line[i_].startswith("'")):
        i = i_ + 1
        continue
      break
    if i is not None:
      return cls(line[:i]), line[i:]

class fractional_constant(grammar('fractional_constant')):
  """
  digit-sequence? . digit-sequence
  digit-sequence .
  """
  @splitter
  def split(cls, ctx, line):
    s, rest = digit_sequence.split(ctx, line)
    if s:
      if rest.startswith('.'):
        p = rest[0]
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        t, rest = digit_sequence.split(ctx, rest)
        if t:
          return cls(str(s.content) + str(p) + str(t.content)), rest
        return cls(str(s.content) + str(p)), rest
    elif rest.startswith('.'):
      p = rest[0]
      t, rest = digit_sequence.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if t:
        return cls(str(p) + str(t.content)), rest

class hexadecimal_fractional_constant(grammar('hexadecimal_fractional_constant')):
  """
  hexadecimal-digit-sequence? . hexadecimal-digit-sequence
  hexadecimal-digit-sequence .
  """
  @splitter
  def split(cls, ctx, line):
    s, rest = hexadecimal_digit_sequence.split(ctx, line)
    if s:
      if rest.startswith('.'):
        p = rest[0]
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        t, rest = hexadecimal_digit_sequence.split(ctx, rest)
        if t:
          return cls(str(s.content) + str(p) + str(t.content)), rest
        return cls(str(s.content) + str(p)), rest
    elif rest.startswith('.'):
      p = rest[0]
      t, rest = hexadecimal_digit_sequence.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if t:
        return cls(str(p) + str(t.content)), rest

class exponent_part(grammar('exponent_part')):
  """
  e sign? digit-sequence
  E sign? digit-sequence
  """
  @splitter
  def split(cls, ctx, line):
    if line.startswith('e') or line.startswith('E'):
      e = line[0]
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if rest.startswith('+') or rest.startswith('-'):
        s = rest[0]
        rest = rest[1:].lstrip(ctx.whitespace_characters)
      else:
        s = rest[:0]
      d, rest = digit_sequence.split(ctx, rest)
      if d:
        return cls(str(e) + str(s) + str(d.content)), rest

class binary_exponent_part(grammar('binary_exponent_part')):
  """
  p sign? digit-sequence
  P sign? digit-sequence
  """
  @splitter
  def split(cls, ctx, line):
    if line.startswith('p') or line.startswith('P'):
      e = line[0]
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if rest.startswith('+') or rest.startswith('-'):
        s = rest[0]
        rest = rest[1:].lstrip(ctx.whitespace_characters)
      else:
        s = rest[:0]
      d, rest = digit_sequence.split(ctx, rest)
      if d:
        return cls(str(e) + str(s) + str(d.content)), rest

  
class decimal_floating_point_plain_literal(grammar('decimal_floating_point_plain_literal', ['fractional_part', 'exponent_part'])):
  """
  fractional-constant exponent-part?

  digit-sequence exponent-part
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    f, rest = fractional_constant.split(ctx, line)
    if f:
      e, rest = exponent_part.split(ctx, rest)
      return cls(f, e), rest
    else:
      f, rest = digit_sequence.split(ctx, line)
      if f:
        e, rest = exponent_part.split(ctx, rest)
        if e:
          return cls(f, e), rest

class hexadecimal_floating_point_plain_literal(grammar('hexadecimal_floating_point_plain_literal', ['hexadecimal-prefix', 'hexadecimal-fractional-part', 'binary-exponent-part'])):
  """
  hexadecimal-prefix hexadecimal-fractional-constant binary-exponent-part
  hexadecimal-prefix hexadecimal-digit-sequence      binary-exponent-part
  """
  @splitter
  def split(cls, ctx, line):
    p, rest = hexadecimal_prefix.split(ctx, line)
    if p:
      for hcls in [hexadecimal_fractional_constant, hexadecimal_digit_sequence]:
        f, rest = hcls.split(ctx, rest)
        if f:
          e, rest = binary_exponent_part.split(ctx, rest)
          if e:
            return cls(p, f, e), rest

class floating_point_suffix(keyword('floating_point_suffix',
                                    'f128', 'bf16', 'F128', 'BF16', 'f16', 'f32', 'f64', 'F16', 'F32', 'F64', 'f', 'l', 'F', 'L'
                                    )):
  """
  floating-point-suffix: one of
  """
  
class decimal_floating_point_literal(grammar('decimal_floating_point_literal', ['literal', 'floating_point_suffix'])):
  """
  fractional-constant exponent-part? floating-point-suffix?

  digit-sequence exponent-part floating-point-suffix?
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = decimal_floating_point_plain_literal.split(ctx, line)
    if l:
      s, rest = floating_point_suffix.split(ctx, rest)
      return cls(l, s), rest

class hexadecimal_floating_point_literal(grammar('hexadecimal_floating_point_literal')):
  """
  hexadecimal-prefix hexadecimal-fractional-constant binary-exponent-part floating-point-suffix?
  hexadecimal-prefix hexadecimal-digit-sequence      binary-exponent-part floating-point-suffix?
  """
  @splitter
  def split(cls, ctx, line):
    l, rest = hexadecimal_floating_point_plain_literal.split(ctx, line)
    if l:
      s, rest = floating_point_suffix.split(ctx, rest)
      return cls(l, s), rest
  
class floating_point_literal(switch('floating_point_literal',
                                    decimal_floating_point_literal,
                                    hexadecimal_floating_point_literal)):
  """
  decimal-floating-point-literal
  hexadecimal-floating-point-literal
  """

class hexadecimal_prefix(grammar('hexadecimal_prefix')):
  """
  0x 0X
  """
  @splitter
  def split(cls, ctx, line):
    if line.startswith('0x') or line.startswith('0X'):
      return cls(line[:2]), line[2:]

class encoding_prefix(keyword('encoding_prefix', 'u8', 'u', 'U', 'L')):
  pass

class simple_escape_sequence_char(grammar('simple_escape_sequence_char')):
  r"""
  one of
  '  "  ?  \ a  b  f  n  r  t  v
  """
  whitespace_characters = ''
  @splitter
  def split(cls, ctx, line):
    c = str(line[0])
    if c == "'" or c in r'"?\abfntv':
      return cls(line[0]), line[1:]

class simple_escape_sequence(grammar('simple_escape_sequence')):
  r"""
  \ simple-escape-sequence-char
  """
  format = '\\{0}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('\\'):
      c, rest = simple_escape_sequence_char.split(ctx, line[1:])
      if c:
        return cls(c), rest

class octal_escape_sequence(grammar('octal_escape_sequence')):
  r"""
  \ octal-digit
  \ octal-digit octal-digit
  \ octal-digit octal-digit octal-digit
  \o{ simple-octal-digit-sequence }
  """
  @splitter
  def split(cls, ctx, line):
    if line.startswith('\\'):
      assert 0, line[:30]  # not implemented

class hexadecimal_escape_sequence(grammar('hexadecimal_escape_sequence')):
  r"""
  \x simple-hexadecimal-digit-sequence
  \x{ simple-hexadecimal-digit-sequence }
  """
  @splitter
  def split(cls, ctx, line):
    if line.startswith('\\'):
      assert 0, line[:30]  # not implemented

class numeric_escape_sequence(switch('numeric_escape_sequence',
                                           octal_escape_sequence,
                                           hexadecimal_escape_sequence)):
  """
  octal-escape-sequence
  hexadecimal-escape-sequence
  """

class conditional_escape_sequence_char(grammar('conditional_escape_sequence_char')):
  """
  any member of the basic character set that is not an octal-digit, a simple-escape-sequence-char, or the characters N, o, u, U, or x
  """
  whitespace_characters = ''
  @splitter
  def split(cls, ctx, line):
    assert 0, line[:30]  # not implemented

class conditional_escape_sequence(grammar('conditional_escape_sequence')):
  r"""
  \ conditional-escape-sequence-char
  """
  whitespace_characters = ''
  format = '\\{0}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('\\'):
      c, rest = conditional_escape_sequence_char.split(ctx, line[1:])
      if c:
        return cls(c), rest



class escape_sequence(switch('escape_sequence',
                      simple_escape_sequence,
                      numeric_escape_sequence,
                      conditional_escape_sequence)):
  """
  simple-escape-sequence
  numeric-escape-sequence
  conditional-escape-sequence
  """
  whitespace_characters = ''

class basic_c_char(grammar('basic_c_char')):
  """
  any member of the translation character set except the U+0027 apostrophe,
  U+005c reverse solidus, or new-line character
  """
  whitespace_characters = ''
  @splitter
  def split(cls, ctx, line):
    c = str(line[:1])
    if c == '\n' or c == '\\' or c == "'" or c == '':
      return
    return line[:1], line[1:]

  
class basic_s_char(grammar('basic_s_char')):
  """
  any member of the translation character set except the U+0022
  quotation mark, U+005c reverse solidus, or new-line character
  """
  whitespace_characters = ''
  @splitter
  def split(cls, ctx, line):
    c = str(line[:1])
    if c == '\n' or c == '\\' or c == '"' or c == '':
      return
    return line[:1], line[1:]

class universal_character_name(grammar('universal_character_name')):
  r"""
  \u hex-quad
  \U hex-quad hex-quad
  \u{ simple-hexadecimal-digit-sequence }
  named-universal-character
  """
  whitespace_characters = ''
  @splitter
  def split(cls, ctx, line):
    if line.startswith("\\"):
      assert 0, line[:30]  # not implemented

class c_char(switch('c_char', basic_c_char, escape_sequence, universal_character_name)):
  """
  basic-c-char
  escape-sequence
  universal-character-name
  """
  whitespace_characters = ''

class s_char(switch('s_char',
                    basic_s_char,
                    escape_sequence,
                    universal_character_name)):
  """
  basic-s-char
  escape-sequence
  universal-character-name
  """
  whitespace_characters = ''

class c_char_sequence(item_sequence('c_char_sequence', c_char)):
  """
  c-char
  c-char-sequence c-char
  """
  whitespace_characters = ''
  @classmethod
  def postprocess(cls, ctx, item, rest):
    if item is not None:
      return cls(''.join(item.content)), rest
    return item, rest

class s_char_sequence(item_sequence('s_char_sequence', s_char)):
  """
  s-char
  s-char-sequence s-char
  """
  whitespace_characters = ''
  @classmethod
  def postprocess(cls, ctx, item, rest):
    if item is not None:
      return cls(''.join(item.content)), rest
    return item, rest

class character_literal(grammar('character_literal', ['encoding_prefix', 'c_char_sequence'])):
  """
  encoding-prefix? ' c-char-sequence '
  """
  format = "{0}'{1}'"
  @splitter
  def split(cls, ctx, line):
    e, rest = encoding_prefix.split(ctx, line)
    if rest.startswith("'"):
      seq, rest = c_char_sequence.split(ctx, rest[1:])
      if seq and rest.startswith("'"):
        return cls(e, seq), rest[1:]

class user_defined_string_literal(grammar('user_defined_string_literal', ['string_literal', 'ud_suffix'])):
  """
  string-literal ud-suffix
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = string_literal.split(ctx, line)
    if l:
      s, rest = ud_suffix.split(ctx, line)
      if s:
        return cls(l, s), rest

class user_defined_character_literal(grammar('user_defined_character_literal', ['character-literal', 'ud-suffix'])):
  """
  character-literal ud-suffix
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = character_literal.split(ctx, line)
    if l:
      s, rest = ud_suffix.split(ctx, line)
      if s:
        return cls(l, s), rest
    
class raw_string(grammar("raw_string", ['d-char-sequence-head', 'r-char-sequence', 'd-char-sequence-tail'])):
  '''
  " d-char-sequence? ( r-char-sequence? ) d-char-sequence? "
  '''
  format = '"{0}({1}){2}"'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('"'):
      rest = line[1:]
      h, rest = d_char_sequence.split(ctx, rest)
      if rest.startswith('('):
        rest = rest[1:]
        r, rest = r_char_sequence.split(ctx, rest)
        if rest.startswith(')'):
          rest = rest[1:]
          t, rest = d_char_sequence.split(ctx, rest)
          if rest.startswith('"'):
            return cls(h, r, t), rest[1:]

class ordinary_string_literal_quotes(grammar('ordinary_string_literal_quotes')):
  '''
  " s-char-sequence? "
  '''
  format = '"{0}"'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('"'):
      rest = line[1:]
      if rest.startswith('"'):
        return cls(''), rest[1:]
      s, rest = s_char_sequence.split(ctx, rest)
      if rest.startswith('"'):
        return cls(s), rest[1:]

  @classmethod
  def postprocess(cls, ctx, item, rest):
    if rest.startswith('"'):
      item2, rest = cls.split(ctx, rest)
      if item2:
        return cls(''.join(item.content + item2.content)), rest
    return item, rest

class ordinary_string_literal_raw(grammar('ordinary_string_literal_raw')):
  """
  R raw-string
  """
  format = 'R{0}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('R'):
      rest = line[1:]
      s, rest = raw_string.split(ctx, line)
      if s:
        return cls(s), rest
    
class ordinary_string_literal_variants(switch(ordinary_string_literal_raw, ordinary_string_literal_quotes)):
  '''
  " s-char-sequence? "
  R raw-string
  '''
    
class ordinary_string_literal(item_optional_prefix(ordinary_string_literal_variants, encoding_prefix)):
  pass
    
class string_literal(item_optional_prefix(ordinary_string_literal_variants, encoding_prefix)):
  """
  encoding-prefix? " s-char-sequence? "
  encoding-prefix? R raw-string
  """

class boolean_literal(keyword('boolean_literal', 'false', 'true')):
  """
  false
  true
  """
  def evaluate(self, ctx):
    if self.context == 'false': return False
    elif self.context == 'true': return True
    assert 0  # unreachable
  
class pointer_literal(keyword('pointer_literal', 'nullptr')):
  """
  nullptr
  """

class ud_suffix(switch('ud_suffix', identifier)):
  """
  identifier
  """

class user_defined_integer_literal(grammar('user_defined_integer_literal', ['literal', 'ud_suffix'])):
  """
  decimal-literal ud-suffix
  octal-literal ud-suffix
  hexadecimal-literal ud-suffix
  binary-literal ud-suffix
  """
  @splitter
  def split(cls, ctx, line):
    for lcls in [binary_literal, hexadecimal_literal, octal_literal, decimal_literal]:
      i, rest = lcls.split(ctx, line)
      if i:
        s, rest = ud_suffix.split(ctx, rest)
        if s:
          return cls(i, s), rest

class user_defined_floating_point_literal(grammar('user_defined_floating_point_literal', ['literal', 'ud_suffix'])):
  """
  fractional-constant exponent-part? ud-suffix
  digit-sequence exponent-part ud-suffix
  hexadecimal-prefix hexadecimal-fractional-constant binary-exponent-part ud-suffix
  hexadecimal-prefix hexadecimal-digit-sequence binary-exponent-part ud-suffix
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = decimal_floating_point_plain_literal.split(ctx, line)
    if not l:
      l, rest = hexadecimal_floating_point_plain_literal.split(ctx, line)
    if l:
      s, rest = ud_suffix.split(ctx, rest)
      if s:
        return cls(l, s), rest

class user_defined_string_literal(grammar('user_defined_string_literal', ['string_literal', 'ud_suffix'])):
  """
  string-literal ud-suffix
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = string_literal.split(ctx, line)
    if l:
      s, rest = ud_suffix.split(ctx, line)
      if s:
        return cls(l, s), rest

class user_defined_character_literal(grammar('user_defined_character_literal', ['character-literal', 'ud-suffix'])):
  """
  character-literal ud-suffix
  """
  format = '{0}{1}'
  @splitter
  def split(cls, ctx, line):
    l, rest = character_literal.split(ctx, line)
    if l:
      s, rest = ud_suffix.split(ctx, line)
      if s:
        return cls(l, s), rest

class user_defined_literal(switch('user_defined_literal',
                                        user_defined_integer_literal,
                                        user_defined_floating_point_literal,
                                        user_defined_string_literal,
                                        user_defined_character_literal)):
  """
  user-defined-integer-literal
  user-defined-floating-point-literal
  user-defined-string-literal
  user-defined-character-literal
  """

  
class literal(switch('literal', character_literal,
      floating_point_literal,
      integer_literal,
      string_literal,
      boolean_literal,
      pointer_literal,
      user_defined_literal)):
  """
  integer-literal
  character-literal
  floating-point-literal
  string-literal
  boolean-literal
  pointer-literal
  user-defined-literal
  """

class parameters_and_qualifiers(grammar('parameters_and_qualifiers', ['parameter_declaration_clause', 'cv_qualifier_seq', 'ref_qualifier', 'noexcept_specifier', 'attribute_specifier_seq'])):
  """
  ( parameter-declaration-clause ) cv-qualifier-seq? ref-qualifier? noexcept-specifier? attribute-specifier-seq?
  """
  format = '( {0} ) {1} {2} {3} {4}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      c, rest = parameter_declaration_clause.split(ctx, line[1:].lstrip())
      if c:
        if not startswith_token(rest, ')'):
          return
        assert startswith_token(rest, ')'), rest[:50]
        rest = rest[1:].lstrip()
        cv, rest = cv_qualifier_seq.split(ctx, rest)
        q, rest = ref_qualifier.split(ctx, rest)
        s, rest = noexcept_specifier.split(ctx, rest)
        a, rest = attribute_specifier_seq.split(ctx, rest)
        return cls(c, cv, q, s, a), rest

  
class ptr_operator(grammar('ptr_operator', ['nested_name_specifier', 'operator', 'attribute_specifier_seq', 'cv_qualifier_seq'])):
  """
  * attribute-specifier-seq? cv-qualifier-seq?
  & attribute-specifier-seq?
  && attribute-specifier-seq?
  nested-name-specifier * attribute-specifier-seq? cv-qualifier-seq?

  https://timsong-cpp.github.io/cppwp/dcl.decl.general#nt:ptr-operator
  """
  @property
  def format(self):
    if self[0] is not None:
      return '{0} {1} {2} {3}'
    return '{1} {2} {3}'

  @splitter
  def split(cls, ctx, line):
    n, rest = nested_name_specifier.split(ctx, line)
    if n:
      if startswith_token(rest, '*'):
        rest = rest[1:].lstrip()
        a, rest = attribute_specifier_seq.split(ctx, rest)
        cv, rest = cv_qualifier_seq.split(ctx, rest)
        return cls(n, '*', a, cv), rest
    else:
      for op in ['&&', '&', '*']:
        if rest.startswith(op):
          rest = rest[len(op):].lstrip()
          a, rest = attribute_specifier_seq.split(ctx, rest)
          if op == '*':
            cv, rest = cv_qualifier_seq.split(ctx, rest)
          else:
            cv = None
          return cls(None, op, a, cv), rest
  
class noptr_declarator_with_returntype(grammar('noptr_declarator_with_returntype', ['noptr_declarator', 'parameters_and_qualifiers', 'trailing_return_type'])):
  """
  noptr-declarator parameters-and-qualifiers trailing-return-type
  """
  format = '{0} {1} {2}'
  @splitter
  def split(cls, ctx, line):
    decl, rest = noptr_declarator.split(ctx, line)
    if isinstance(decl, noptr_declarator_parameters):
      # noptr_declarator.post_process is greedy
      t, rest = trailing_return_type.split(ctx, rest)
      if t:
        return cls(decl.noptr_declarator, decl.parameters_and_qualifiers, t), rest
    elif decl:
      lst, rest = parameters_and_qualifiers.split(ctx, rest)
      if lst:
        t, rest = trailing_return_type.split(ctx, rest)
        if t:
          return cls(decl, lst, t), rest
  
def declarator_split(ctx, line):
  for dcls in (noptr_declarator_with_returntype, ptr_declarator):
    decl, rest = dcls.split(ctx, line)
    if decl:
      if ctx.enable_abstract_declarator:
        decl = abstract_declarator(decl)
      else:
        decl = declarator(decl)

      if 0 and startswith_token(rest, '('):
        # TODO: there is no function declarator
        decl2, rest2 = function_declarator.split(ctx, rest, head=decl)
        if decl2:
          decl, rest = decl2, rest2

      return decl, rest

class abstract_declarator(grammar('abstract_declarator')):
  """
  ptr-abstract-declarator
  noptr-abstract-declarator parameters-and-qualifiers trailing-return-type
  """
  @splitter
  def split(cls, ctx, line):
    with ctx.abstract_declarator(enable=True):
      return declarator_split(ctx, line)

class declarator(grammar('declarator')):
  """
  ptr-declarator
  noptr-declarator parameters-and-qualifiers trailing-return-type
  """
  @splitter
  def split(cls, ctx, line):
    with ctx.abstract_declarator(enable=False):
      return declarator_split(ctx, line)

class ptr_operator_declarator(grammar('ptr_operator_declarator', ['ptr_operator', 'ptr_declarator'])):
  """
  ptr-operator ptr-declarator
  ptr-operator ptr-abstract-declarator?
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    o, rest = ptr_operator.split(ctx, line)
    if o:
      decl, rest = ptr_declarator.split(ctx, rest)
      if decl or ctx.enable_abstract_declarator:
        return cls(o, decl), rest

class noptr_declarator(grammar('noptr_declarator')):
  """
  declarator-id attribute-specifier-seq?
  noptr-declarator parameters-and-qualifiers
  noptr-declarator [ constant-expression? ] attribute-specifier-seq?
  ( ptr-declarator )

  noptr-abstract-declarator? parameters-and-qualifiers
  noptr-abstract-declarator? [ constant-expression? ] attribute-specifier-seq?
  ( ptr-abstract-declarator )

  https://timsong-cpp.github.io/cppwp/dcl.decl.general#nt:noptr-declarator
  """
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      d, rest = noptr_declarator_parenthesis.split(ctx, line)
      if d:
        return d, rest
    else:
      d =  None
    if ctx.enable_abstract_declarator:
      if startswith_token(line, '('):
        p, rest = parameters_and_qualifiers.split(ctx, line)
        if p:
          return noptr_declarator_parameters(None, p), rest
      elif line.startswith('['):
        rest = line[1:].lstrip()
        if startswith_token(rest, ']'):
          rest = rest[1:].lstrip()
          e = None
        else:
          e, rest = constant_expression.split(ctx, rest)
          if not e:
            return
          assert startswith_token(rest, ']')
          rest = rest[1:].lstrip()
        a, rest = attribute_specifier_seq.split(ctx, rest)
        return noptr_declarator_array(None, e, a), rest        
    else:
      d, rest = declarator_id_with_optional_attribute_specifier_seq.split(ctx, line)
      if d:
        return d, rest

  @classmethod
  def postprocess(cls, ctx, item, rest):

    def worker(item, rest):
      if startswith_token(rest, '('):
        item2, rest2 = noptr_declarator_parameters.split(ctx, rest, decl=item)
        if item2:
          return worker(item2, rest2)
      elif startswith_token(rest, '['):
        item2, rest2 = noptr_declarator_array.split(ctx, rest, decl=item)
        if item2:
          return worker(item2, rest2)
      return item, rest

    return worker(item, rest)

    
class ptr_declarator(switch('ptr_declarator', ptr_operator_declarator, noptr_declarator)):
  """
  noptr-declarator
  ptr-operator ptr-declarator
  """

class noptr_declarator_parameters(sequence('noptr_declarator_parameters', noptr_declarator, parameters_and_qualifiers)):
  """
  noptr-declarator parameters-and-qualifiers
  """
  format = '{0} {1}'
  
class type_id(grammar('type_id', ['type_specifier_seq', 'abstract_declarator'])):
  """
  type-specifier-seq abstract-declarator?
  """
  format = '{0} {1}'

  @splitter
  def split(cls, ctx, line):
    seq, rest = type_specifier_seq.split(ctx, line)
    if seq:
      decl, rest = abstract_declarator.split(ctx, rest)
      return cls(seq, decl), rest

  
class attribute_namespace(switch('attribute_namespace', identifier)):
  """
  identifier
  """

class attribute_using_prefix(grammar('attribute_using_prefix')):
  """
  using attribute-namespace :
  """
  format = 'using {0} :'
  @splitter
  def split(cls, ctx, line):
    using, rest = word.split(ctx, line, require='using')
    if using:
      ns, rest = attribute_namespace.split(ctx, rest)
      if ns and startswith_token(rest, ':'):
        return cls(ns), rest[1:]

class attribute_specifier_with_square_brackets(grammar('attribute_specifier_with_square_brackets', ['attribute_using_prefix', 'attribute_list'])):
  format = '[[ {0} {1} ]]'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('[['):
      raw, rest = split_until(line[2:].lstrip(ctx.whitespace_characters), ']]')
      p, rest2 = attribute_using_prefix.split(ctx, raw)
      lst, rest2 = attribute_list.split(ctx, rest2)
      assert rest2 == '', rest2
      return cls(p, lst), rest

class alignment_specifier(grammar('alignment_specifier', ['type_id_or_constant_expression', 'dots'])):
  """
  alignas ( type-id ...? )
  alignas ( constant-expression ...? )
  """
  format = 'alignas({0} {1})'
  @splitter
  def split(cls, ctx, line):
    a, rest = word.split(ctx, line, require='alignas')
    if a and startswith_token(rest, '('):
      raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), ')')
      i, rest2 = type_id.split(ctx, raw)
      if not i:
        i, rest2 = constant_expression.split(ctx, raw)
      if i:
        if rest2.startswith('...'):
          dots = rest2[:3]
          rest2 = rest2[3:].lstrip(ctx.whitespace_characters)
        else:
          dots = None
        assert rest2 == '', rest2
        return cls(i, dots), rest

  
class attribute_specifier(switch('attribute_specifier', attribute_specifier_with_square_brackets,
            alignment_specifier)):
  """
  [ [ attribute-using-prefix? attribute-list ] ]
  alignment-specifier
  """
  
class attribute_specifier_seq(grammar('attribute_specifier_seq')):
  """
  attribute-specifier-seq? attribute-specifier
  """
  @splitter
  def split(cls, ctx, line):
    if not line:
      return
    a, rest = attribute_specifier.split(ctx, line)
    if a:
      if rest:
        lst, rest = cls.split(ctx, rest)
      else:
        lst = None
      if lst:
        return cls((a,) + lst.content), rest
      return cls((a,)), rest

  
class conditional_expression(grammar('conditional_expression', ['logical_or_expression', 'expression', 'assignment_expression'])):
  """
  logical-or-expression
  logical-or-expression ? expression : assignment-expression
  """
  format = '{0} ? {1} : {2}'
  @splitter
  def split(cls, ctx, line):
    l, rest = logical_or_expression.split(ctx, line)
    if l:
      if rest.startswith('?'):
        e, rest = expression.split(ctx, rest[1:])
        if e:
          if startswith_token(rest, ':'):
            a, rest = assignment_expression.split(ctx, rest[1:])
            if a:
              return cls(l, e, a), rest
      else:
        return l, rest

  def evaluate(self, ctx):
    if isinstance(self.logical_or_expression, (bool, int, float)):
      if self.logical_or_expression:
        return self.expression
      return self.assignment_expression
    return self

class this_expression(keyword('this_expression', 'this')):
  pass

class parenthesis_expression(grammar('parenthesis_expression')):
  """
  ( expression )
  """
  format = '({0})'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      e, rest = expression.split(ctx, line[1:].lstrip(ctx.whitespace_characters))
      if e and startswith_token(rest, ')'):
        return cls(e), rest[1:]

  def evaluate(self, ctx):
    if isinstance(self.content, (int, float)):
      return self.content
    return self

class capture_default(grammar('capture_default')):
  """
  &
  =
  """
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '&') or startswith_token(line, '='):
      return cls(line[0]), line[1:]

class simple_capture(grammar('simple_capture', ['prefix', 'identifier_or_this', 'dots'])):
  """
    identifier ...?
  & identifier ...?
    this
  * this
  """
  format = '{0} {1} {2}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '&'):
      prefix = line[0]
      rest = line[1:].lstrip(ctx.whitespace_characters)
      i, rest = identifier.split(ctx, rest)
      if i:
        if rest.startswith('...'):
          return cls(prefix, i, rest[:3]), rest[3:]
        else:
          return cls(prefix, i, None), rest
    elif startswith_token(line, '*'):
      prefix = line[0]
      rest = line[1:].lstrip(ctx.whitespace_characters)
      this, rest = word.split(ctx, rest, require='this')
      if this:
        return cls(prefix, this, None), rest
    else:
      this, rest = word.split(ctx, line, require='this')
      if this:
        return cls(None, this, None), rest
      i, rest = identifier.split(ctx, rest)
      if i:
        if rest.startswith('...'):
          return cls(None, i, rest[:3]), rest[3:]
        return cls(None, i, None), rest

class init_capture(grammar('init_capture', ['ref', 'dots', 'identifier', 'initializer'])):
  """
    ...? identifier initializer
  & ...? identifier initializer
  """
  format = '{0} {1} {2} {3}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '&'):
      ref = line[0]
      rest = line[1:].lstrip(ctx.whitespace_characters)
    else:
      ref = None
      rest = line
    if rest.startswith('...'):
      dots = rest[:3]
      rest = rest[3:].lstrip(ctx.whitespace_characters)
    else:
      dots = None
    i, rest = identifier.split(ctx, rest)
    if i:
      init, rest = initializer.split(ctx, rest)
      if init:
        return cls(ref, dots, i, init), rest

class capture(switch('capture', init_capture, simple_capture)):
  """
  simple-capture
  init-capture
  """
  
class capture_list(pair_or_item('capture_list', ',', capture)):
  """
  capture
  capture-list , capture
  """

class lambda_capture_default_and_list(grammar('lambda_capture_default_and_list', ['capture-default', 'capture-list'])):
  """
  capture-default , capture-list
  """
  format = '{0}, {1}'
  @splitter
  def split(cls, ctx, line):
    d, rest = capture_default.split(ctx, line)
    if d and rest.startswith(','):
      l, rest = capture_list.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if l:
        return cls(d, l), rest

class lambda_capture(switch('lambda_capture', capture_list, lambda_capture_default_and_list, capture_default)):
  """
  capture-default
  capture-list
  capture-default , capture-list
  """

class lambda_introducer(switch('lambda_introducer')):
  """
  [ lambda-capture? ]
  """
  format = '[{0}]'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('['):
      rest = line[1:].lstrip()
      if startswith_token(rest, ']'):
        return cls(None), rest[1:]
      c, rest = lambda_capture.split(ctx, rest)
      if c:
        assert startswith_token(rest, ']'), rest[:50].tostring()
        return cls(c), rest[1:]

class lambda_introducer_template(grammar('lambda_introducer_template', ['lambda_introducer', 'template-parameter-list', 'requires-clause'])):
  """
  lambda-introducer < template-parameter-list > requires-clause?
  """
  format = '{0} <{1}> {2}'
  @splitter
  def split(cls, ctx, line):
    i, rest = lambda_introducer.split(ctx, line)
    if i and startswith_token(rest, '<'):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      raw, rest = split_until(rest, '>')
      lst, rest2 = template_parameter_list.split(ctx, raw)
      if lst:
        assert rest2 == '', rest2[:50]
        r, rest = requires_clause.split(ctx, rest)
        return cls(i, lst, r), rest
        
class lambda_expression_head(switch('lambda_expression_head', lambda_introducer_template, lambda_introducer)):
  """
  lambda-introducer
  lambda-introducer < template-parameter-list > requires-clause?
  """

class lambda_expression_head_optional_attribute_specifier_seq(item_optional_suffix(lambda_expression_head, attribute_specifier_seq)):
  """
  lambda_expression_head attribute-specifier-seq?
  """

class trailing_return_type(grammar('trailing_return_type')):
  format = '-> {0}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '->'):
      t, rest = type_id.split(ctx, line[2:].lstrip(ctx.whitespace_characters))
      if t:
        return cls(t), rest

  
class lambda_specifier_seq_with_parameter_declaration_clause_and_tails(
    grammar('lambda_specifier_seq_with_parameter_declaration_clause_and_tails',
               ['parameter-declaration-clause', 'lambda-specifier-seq', 'noexcept-specifier', 'attribute-specifier-seq', 'trailing-return-type', 'requires-clause'])):
  """
  ( parameter-declaration-clause ) lambda-specifier-seq? noexcept-specifier? attribute-specifier-seq? trailing-return-type? requires-clause?
  """
  format = '({0}) {1} {2} {3} {4} {5}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      c, rest = parameter_declaration_clause.split(ctx, line[1:].lstrip(ctx.whitespace_characters))
      if startswith_token(rest, ')'):
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        seq, rest =  lambda_specifier_seq.split(ctx, rest)
        noexc, rest =  noexcept_specifier.split(ctx, rest)
        a, rest =  attribute_specifier_seq.split(ctx, rest)
        t, rest =  trailing_return_type.split(ctx, rest)
        r, rest =  requires_clause.split(ctx, rest)
        return cls(c, seq, noexc, a, t, r), rest

class lambda_specifier(keyword('lambda_specifier',
                               'consteval',
                               'constexpr',
                               'mutable',
                               'static')):
  """
  consteval
  constexpr
  mutable
  static
  """

class lambda_specifier_seq(pair_or_item('lambda_specifier_seq', '', lambda_specifier)):
  """
  lambda-specifier
  lambda-specifier lambda-specifier-seq
  """
  
class lambda_specifier_seq_with_tails(grammar('lambda_specifier_seq_with_tails',
                                      ['lambda-specifier-seq', 'noexcept-specifier', 'attribute-specifier-seq', 'trailing-return-type'])):
  """
  lambda-specifier-seq  noexcept-specifier? attribute-specifier-seq? trailing-return-type?
  """
  format = '{0} {1} {2} {3}'
  @splitter
  def split(cls, ctx, line):
    seq, rest =  lambda_specifier_seq.split(ctx, line)
    if seq:
      noexc, rest =  noexcept_specifier.split(ctx, rest)
      a, rest =  attribute_specifier_seq.split(ctx, rest)
      t, rest =  trailing_return_type.split(ctx, rest)
      return cls(seq, noexc, a, t), rest

class noexcept_specifier_with_tails(grammar('noexcept_specifier_with_tails', ['noexcept-specifier', 'attribute-specifier-seq', 'trailing-return-type'])):
  """
  noexcept-specifier attribute-specifier-seq?  trailing-return-type?
  """
  format = '{0} {1} {2}'
  @splitter
  def split(cls, ctx, line):
    noexc, rest =  noexcept_specifier.split(ctx, line)
    if noexc:
      a, rest =  attribute_specifier_seq.split(ctx, rest)
      t, rest =  trailing_return_type.split(ctx, rest)
      return cls(noexc, a, t), rest

class lambda_declarator(switch('lambda_declarator',
                                     lambda_specifier_seq_with_parameter_declaration_clause_and_tails,
                                     lambda_specifier_seq_with_tails,
                                     noexcept_specifier_with_tails,
                                     trailing_return_type
                                     )):
  """
                                   lambda-specifier-seq  noexcept-specifier? attribute-specifier-seq? trailing-return-type?
                                                         noexcept-specifier attribute-specifier-seq?  trailing-return-type?
                                                                                                      trailing-return-type?
  ( parameter-declaration-clause ) lambda-specifier-seq? noexcept-specifier? attribute-specifier-seq? trailing-return-type? requires-clause?
  """

class lambda_declarator_compound_statement(grammar('lambda_declarator_compound_statement', ['lambda_declarator', 'compound_statement'])):
  """
  lambda-declarator? compound-statement

  Note that single `trailing-return-type?` makes lambda-declarator optional.
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    d, rest = lambda_declarator.split(ctx, line)
    s, rest = compound_statement.split(ctx, rest)
    if s:
      return cls(d, s), rest

class lambda_expression(sequence('lambda_expression', lambda_expression_head_optional_attribute_specifier_seq, lambda_declarator_compound_statement)):
  """
  lambda-introducer                                              attribute-specifier-seq? lambda-declarator compound-statement
  lambda-introducer < template-parameter-list > requires-clause? attribute-specifier-seq? lambda-declarator compound-statement
  """

class fold_expression_12(grammar('fold_expression_12', ['cast-expression', 'fold-operator', 'fold-operator2', 'cast-expression2'])):
  """
  ( cast-expression fold-operator ... fold-operator cast-expression )
  """
  format = '({0} {1} ... {2} {3})'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      rest = line[1:].lstrip()
      c1, rest = cast_expression.split(ctx, rest)
      if c1:
        o1, rest = fold_operator.split(ctx, rest)
        if o1 and rest.startswith('...'):
          o2, rest = fold_operator.split(ctx, rest[3:].lstrip(ctx.whitespace_characters))
          if o2:
            c2, rest = cast_expression.split(ctx, rest)
            if c2 and startswith_token(rest, ')'):
              return cls(c1, o1, o2, c2), rest[1:]

class fold_expression_1(grammar('fold_expression_1', ['cast-expression', 'fold-operator'])):
  """
  ( cast-expression fold-operator ... )
  """
  format = '({0} {1} ...)'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      rest = line[1:].lstrip()
      c1, rest = cast_expression.split(ctx, rest)
      if c1:
        o1, rest = fold_operator.split(ctx, rest)
        if o1 and rest.startswith('...'):
          rest = rest[3:].lstrip(ctx.whitespace_characters)
          if startswith_token(rest, ')'):
            return cls(c1, o1), rest[1:]

class fold_expression_2(grammar('fold_expression_2', ['fold-operator2', 'cast-expression2'])):
  """
  ( ... fold-operator cast-expression )
  """
  format = '(... {0} {1})'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if rest.startswith('...'):
        o2, rest = fold_operator.split(ctx, rest[3:].lstrip(ctx.whitespace_characters))
        if o2:
          c2, rest = cast_expression.split(ctx, rest)
          if c2 and startswith_token(rest, ')'):
            return cls(o2, c2), rest[1:]

class fold_operator(grammar('fold_operator')):
  """
  one of
  """
  symbols = sorted('''
  +   -   *   /   %   ^   &   |   <<   >> 
  +=  -=  *=  /=  %=  ^=  &=  |=  <<=  >>=  =
  ==  !=  <   >   <=  >=  &&  ||  ,    .*   ->*
  '''.strip().split(), reverse=True, key=len)
  @splitter
  def split(cls, ctx, line):
    for s in cls.symbols:
      if line.startswith(s):
        return cls(line[:len(s)]), line[len(s):]

class fold_expression(switch('fold_expression', fold_expression_12, fold_expression_2, fold_expression_1)):
  """
  ( cast-expression fold-operator ... )
  ( ... fold-operator cast-expression )
  ( cast-expression fold-operator ... fold-operator cast-expression )
  """

class requires_expression(grammar('requires_expression', ['requirement-parameter-list', 'requirement-body'])):
  """
  requires requirement-parameter-list? requirement-body
  """
  format = 'requires {0} {1}'
  @splitter
  def split(cls, ctx, line):
    requires, rest = word.split(ctx, line, require='requires')
    if requires:
      lst, rest = requirement_parameter_list.split(ctx, line)
      b, rest = requirement_body.split(ctx, line)
      if b:
        return cls(lst, b), rest

class conversion_declarator(grammar('conversion_declarator', ['ptr_operator', 'conversion_declarator'])):
  """
  ptr-operator conversion-declarator?
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    p, rest = ptr_operator.split(ctx, line)
    if p:
      d, rest = conversion_declarator.split(ctx, rest)
      return cls(p, d), rest

class conversion_type_id(grammar('conversion_type_id', ['type_specifier_seq', 'conversion_declarator'])):
  """
  type-specifier-seq conversion-declarator?
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    s, rest = type_specifier_seq.split(ctx, line)
    if s:
      d, rest = conversion_declarator.split(ctx, rest)
      return cls(s, d), rest
  
class conversion_function_id(grammar('conversion_function_id')):
  """
  operator conversion-type-id
  """
  format = 'operator {0}'
  @splitter
  def split(cls, ctx, line):
    op_, rest = word.split(ctx, line, require='operator')
    if op_:
      i, rest = conversion_type_id.split(ctx, rest)
      if i:
        return cls(i), rest

class operator_function_id(grammar('operator_function_id')):
  """
  operator operator
  """
  format = 'operator {0}'
  @splitter
  def split(cls, ctx, line):
    op_, rest = word.split(ctx, line, require='operator')
    if op_:
      for op in operators:
        if rest.startswith(op):
          rest = rest[len(op):].lstrip(ctx.whitespace_characters)
          if op in {'new', 'delete'}:
            if startswith_token(rest, '['):
              rest = rest[1:].lstrip(ctx.whitespace_characters)
              if startswith_token(rest, ']'):
                rest = rest[1:].lstrip(ctx.whitespace_characters)
                op = op + '[]'
              else:
                assert 0  # unreachable
          return cls(op), rest
      if startswith_token(rest, '('):
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        if startswith_token(rest, ')'):
          return cls('()'), rest[1:]
      if startswith_token(rest, '['):
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        if startswith_token(rest, ']'):
          return cls('[]'), rest[1:]

class literal_operator_id(grammar('literal_operator_id', ['string_or_literal', 'identifier'])):
  """
  operator unevaluated-string identifier
  operator user-defined-string-literal
  """
  format = 'operator {0} {1}'
  @splitter
  def split(cls, ctx, line):
    op_, rest = word.split(ctx, line, require='operator')
    if op_:
      s, rest = string_literal.split(ctx, rest)
      if s:
        i, rest = identifier.split(ctx, rest)
        if i:
          return cls(s, i)
      else:
        s, rest = user_defined_string_literal.split(ctx, rest)
        if s:
          return cls(s, None), rest

class type_name_with_tilde(grammar('type_name_with_tilde')):
  format = '~{0}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('~'):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      n, rest = type_name.split(ctx, rest)
      if n:
        return cls(n), rest

class computed_type_specifier_with_tilde(grammar('computed_type_specifier_with_tilde')):
  format = '~{0}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('~'):
      rest = line[1:].lstrip()
      n, rest = computed_type_specifier.split(ctx, rest)
      if n:
        return cls(n), rest

class simple_template_id(grammar('simple_template_id', ['template_name', 'template_argument_list'])):
  """
  template-name < template-argument-list? >
  """
  format = '{0}<{1}>'
  @splitter
  def split(cls, ctx, line):
    o, rest = template_name.split(ctx, line)
    if o and startswith_token(rest, '<'):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, '>'):
        return cls(o, None), rest[1:]

      # https://timsong-cpp.github.io/cppwp/temp.names#4 : When parsing
      # a template-argument-list, the first non-nested > is taken
      # as the ending delimiter rather than a greater-than operator.
      #raw, rest = split_until(rest, '>')
      raw, rest = utils.split_until_gt(rest)
      if not raw:
        return
      lst, rest2 = template_argument_list.split(ctx, raw)
      if lst:
        if rest2 != '':
          return
        assert rest2 == '', rest2
        return cls(o, lst), rest

class operator_function_template_id(grammar('operator_function_template_id', ['operator_function_id', 'template_argument_list'])):
  format = '{0}<{1}>'
  @splitter
  def split(cls, ctx, line):
    o, rest = operator_function_id.split(ctx, line)
    if o and startswith_token(rest, '<'):
      # https://timsong-cpp.github.io/cppwp/temp.names#4
      raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), '>')
      lst, rest2 = template_argument_list.split(ctx, raw)
      if lst:
        assert rest2 == '', rest2
        return cls(o, lst), rest

class literal_operator_template_id(grammar('literal_operator_template_id', ['literal_operator_id', 'template_argument_list'])):
  format = '{0}<{1}>'
  @splitter
  def split(cls, ctx, line):
    o, rest = literal_operator_id.split(ctx, line)
    if o and startswith_token(rest, '<'):
      # https://timsong-cpp.github.io/cppwp/temp.names#4
      raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), '>')
      lst, rest2 = template_argument_list.split(ctx, raw)
      if lst:
        assert rest2 == '', rest2
        return cls(o, lst), rest

class template_id(switch('template_id', simple_template_id,
            operator_function_template_id,
            literal_operator_template_id)):
  """
  simple-template-id
  operator-function-id < template-argument-list? >
  literal-operator-id < template-argument-list? >
  """
  # TODO: How to avoid matching `bool a = x < 0 && a > y` as `bool a = x<0 && a>` + `y`

class unqualified_id(switch('unqualified_id', conversion_function_id,
      operator_function_id,
      literal_operator_id,
      type_name_with_tilde,
      computed_type_specifier_with_tilde,
      template_id,
      identifier
)):
  """
  identifier
  operator-function-id
  conversion-function-id
  literal-operator-id
  ~ type-name
  ~ computed-type-specifier
  template-id

  https://timsong-cpp.github.io/cppwp/expr.prim.id.unqual#nt:unqualified-id
  """

class namespace_name(grammar('namespace_name')):
  """
  identifier
  namespace-alias
    identifier   # from `namespace identifier = qualified-namespace-specifier ;` statement
  """
  format = '{0}'
  @splitter
  def split(cls, ctx, line):
    i, rest = identifier.split(ctx, line)
    if i:
      # TODO: ensure that i is a namespace name or namespace alias.
      return i, rest

class enum_name(switch('enum_name', identifier)):
  """
  """

class class_name(switch('class_name', simple_template_id, identifier)):
  """
  """

class typedef_name(switch('typedef_name',         simple_template_id,
        identifier)):
  """
  """

class template_name(switch('template_name', identifier, require_language='c++')):
  """
  """
  
class type_name(switch('type_name',
                       class_name,
                       enum_name,
                       typedef_name)):
  pass
  
class nested_name_specifier(grammar('nested_name_specifier')):
  """
  ::
  type-name ::
  namespace-name ::
  computed-type-specifier ::
  nested-name-specifier identifier ::
  nested-name-specifier template? simple-template-id ::

  https://timsong-cpp.github.io/cppwp/expr.prim.id.qual#nt:nested-name-specifier
  """
  def __str__(self):
    lst = []
    for c in map(str, self[0]):
      if lst and lst[-1] == 'template':
        lst[-1] += ' ' + c
      else:
        lst.append(c)
    return '::'.join(lst) + '::'

  @splitter
  def split(cls, ctx, line):
    if line.startswith('::'):
      return cls(('',)), line[2:].lstrip()
    else:
      for scls in [computed_type_specifier, namespace_name, type_name]:
        n, rest2 = scls.split(ctx, line)
        if n and rest2.startswith('::'):
          return cls((n,)), rest2[2:].lstrip()

  @classmethod
  def postprocess(cls, ctx, item, rest):

    for scls in [template_simple_template_id, identifier]:
      i, rest2 = scls.split(ctx, rest)
      if i and rest2.startswith('::'):
        return cls.postprocess(ctx, cls(item.content + (i,)), rest2[2:].lstrip())

    return item, rest


class qualified_id(grammar('qualified_id', ['nested_name_specifier', 'template', 'unqualified_id'])):
  """
  nested-name-specifier template? unqualified-id
  """
  format = '{0}{1} {2}'
  @splitter
  def split(cls, ctx, line):
    s, rest = nested_name_specifier.split(ctx, line)
    if s:
      template, rest = word.split(ctx, rest, require='template')
      i, rest = unqualified_id.split(ctx, rest)
      if i:
        return cls(s, template, i), rest

class pack_index_expression(grammar('pack_index_expression', ['id_expression', 'constant_expression'])):
  """
  id-expression ... [ constant-expression ]
  https://timsong-cpp.github.io/cppwp/expr.prim.pack.index#nt:pack-index-expression
  """
  format = '{0} ...[{1}]'
  @splitter
  def split(cls, ctx, line):
    i, rest = id_expression.split(ctx, line)
    if i and rest.startswith('...'):
      rest = rest[3:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, '['):
        raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), ']')
        if raw == '':
          return cls(i, None), rest
        e, rest2 = constant_expression.split(ctx, raw)
        if e:
          assert rest2 == '', rest2
          return cls(i, e), rest


class id_expression(switch('id_expression',       qualified_id,
      unqualified_id,
      pack_index_expression,
)):
  """
  unqualified-id
  qualified-id
  pack-index-expression
  """

class primary_expression(switch('primary_expression',
                                      parenthesis_expression,
                                      literal,
                                      this_expression,
                                      lambda_expression,
                                      fold_expression,
                                      requires_expression,
                                      id_expression,
                                      )):
  """
  literal
  this
  ( expression )
  id-expression
  lambda-expression
  fold-expression
  requires-expression
  """

class simple_type_specifier_type_name(grammar('simple_type_specifier_type_name', ['nested_name_specifier', 'type_name'])):
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    if not ctx.supports_language('c++'):
      return
    spec, rest = nested_name_specifier.split(ctx, line)
    n, rest = type_name.split(ctx, rest)
    if n:
      return cls(spec, n), rest

class simple_type_specifier_template_name(grammar('simple_type_specifier_template_name', ['nested_name_specifier', 'template_name'])):
  """
  nested-name-specifier? template-name
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    spec, rest = nested_name_specifier.split(ctx, line)
    n, rest = template_name.split(ctx, rest)
    if n:
      return cls(spec, n), rest

class simple_type_specifier_template_id(grammar('simple_type_specifier_template_id', ['nested_name_specifier', 'simple_template_id'])):
  format = '{0}template {1}'
  @splitter
  def split(cls, ctx, line):
    spec, rest = nested_name_specifier.split(ctx, line)
    if spec:
      template, rest = word.split(ctx, rest, require='template')
      if template:
        i, rest = simple_template_id.split(ctx, rest)
        if i:
          return cls(spec, i), rest

class decltype_specifier(grammar('decltype_specifier')):
  """Matches
  decltype ( expression )
  """
  format = 'decltype({0})'

  @splitter
  def split(cls, ctx, line):
    w, rest = word.split(ctx, line, require='decltype')
    if w and startswith_token(rest, '('):
      e, rest = expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if e and startswith_token(rest, ')'):
        return cls(e), rest[1:].lstrip()

      
class pack_index_specifier(grammar('pack_index_specifier')):
  """
  typedef-name ... [ constant-expression ]
  """
  @splitter
  def split(cls, ctx, line):
    n, rest = typedef_name.split(ctx, line)
    if rest.startswith('...'):
      rest = rest[3:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, '['):
        raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), ']')
        if raw:
          return cls(n, constant_expression(raw)), rest


class computed_type_specifier(switch('computed_type_specifier',
                                           decltype_specifier,
                                           pack_index_specifier)):
  """
  decltype-specifier
  pack-index-specifier
  """

class placeholder_type_specifier_auto(grammar('placeholder_type_specifier_auto', ['unused'])):
  """
  auto
  """
  format = 'auto'
  @splitter
  def split(cls, ctx, line):
    auto, rest = word.split(ctx, line, require='auto')
    if auto:
      return cls(None), rest

class placeholder_type_specifier_decltype_auto(grammar('placeholder_type_specifier_decltype_auto')):
  """
  decltype(auto)
  """
  format = 'decltype(auto)'
  @splitter
  def split(cls, ctx, line):
    decltype, rest = word.split(ctx, line, require='decltype')
    if decltype and startswith_token(rest, '('):
      auto, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='auto')
      if auto and startswith_token(rest, ')'):
        return cls(None), rest[1:]

class placeholder_type_specifier_item(switch('placeholder_type_specifier_item',
                                                   placeholder_type_specifier_auto,
                                                   placeholder_type_specifier_decltype_auto,
                                                   )):
  """
  auto
  decltype(auto)
  """

class concept_name(switch('concept_name', identifier, require_language='c++')):
  """
  """

class type_constraint_template_arguments(grammar('type_constraint_template_arguments', ['nested_name_specifier', 'concept_name', 'template_argument_list'])):
  """
  nested-name-specifier? concept-name < template-argument-list? >
  """
  format = '{0} {1} <{2}>'
  @splitter
  def split(cls, ctx, line):
    s, rest = nested_name_specifier.split(ctx, line)
    n, rest = concept_name.split(ctx, rest)
    if n and startswith_token(rest, '<'):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, '>'):
        return cls(s, n, None), rest[1:]
      # https://timsong-cpp.github.io/cppwp/temp.names#4
      raw, rest = split_until(rest[1:].lstrip(ctx.whitespace_characters), '>')
      if raw:
        lst, rest2 = template_argument_list.split(ctx, raw)
        if lst and rest2 == '':
          return cls(s, n, lst), rest

class type_constraint_simple(grammar('type_constraint_simple', ['nested_name_specifier', 'concept_name'])):
  """
  nested-name-specifier? concept-name
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    s, rest = nested_name_specifier.split(ctx, line)
    n, rest = concept_name.split(ctx, rest)
    if n:
      return cls(s, n), rest

class type_constraint(switch('type_constraint', type_constraint_template_arguments,
      type_constraint_simple)):
  """
  nested-name-specifier? concept-name
  nested-name-specifier? concept-name < template-argument-list? >
  """
    
class placeholder_type_specifier(item_optional_prefix(placeholder_type_specifier_item, type_constraint)):
  """
  type-constraint ﻿? auto
  type-constraint ﻿? decltype(auto)
  """

class keyword_type_specifier(grammar('keyword_type_specifier')):

  keyword_types = [
    ('bool',),
    ('char',),
    ('char8_t',),
    ('char16_t',),
    ('char32_t',),
    ('wchar_t',),
    ('signed',),
    ('signed', 'char'),
    ('signed', 'long'),
    ('signed', 'long', 'long'),
    ('signed', 'long', 'long', 'int'),
    ('signed', 'int'),
    ('signed', 'short'),
    ('signed', 'short', 'int'),
    ('unsigned',),
    ('unsigned', 'char'),
    ('unsigned', 'long'),
    ('unsigned', 'long', 'long'),
    ('unsigned', 'long', 'long', 'int'),
    ('unsigned', 'int'),
    ('unsigned', 'short'),
    ('unsigned', 'short', 'int'),
    ('short',),
    ('short', 'int'),
    ('short', 'unsigned'),
    ('short', 'signed'),
    ('short', 'unsigned', 'int'),
    ('short', 'signed', 'int'),
    ('long',),
    ('long', 'int'),
    ('long', 'unsigned'),
    ('long', 'signed'),
    ('long', 'unsigned', 'int'),
    ('long', 'signed', 'int'),
    ('long', 'double'),
    ('long', 'long'),
    ('long', 'long', 'int'),
    ('long', 'long', 'unsigned'),
    ('long', 'long', 'signed'),
    ('long', 'long', 'unsigned', 'int'),
    ('long', 'long', 'signed', 'int'),
    ('int',),
    ('float',),
    ('double',),
    ('void',),
  ]
    
  @splitter
  def split(cls, ctx, line):
    tname, rest = word.split(ctx, line)
    if tname:
      t = (tname,)
      if t in cls.keyword_types:
        while True:
          tname2, rest2 = word.split(ctx, rest)
          t2 = t + (tname2,)
          if tname2 and t2 in cls.keyword_types:
            t, rest = t2, rest2
          else:
            break
        return cls(t), rest

  
class simple_type_specifier(switch('simple_type_specifier',  # was maxalternative
                                         simple_type_specifier_template_name,
                                         simple_type_specifier_template_id,
                                         placeholder_type_specifier,
                                         computed_type_specifier,
                                         keyword_type_specifier,
                                         simple_type_specifier_type_name,
                                         )):
  """
  nested-name-specifier? type-name
  nested-name-specifier template simple-template-id
  computed-type-specifier
  placeholder-type-specifier
  nested-name-specifier? template-name

  keyword-type-specifier
    char
    char8_t
    char16_t
    char32_t
    wchar_t
    bool
    short
    int
    long
    signed
    unsigned
    float
    double
    void
  """



  
class postfix_expression_getitem(grammar('postfix_expression_getitem', ['postfix_expression', 'expression_list'])):
  """
  postfix-expression [ expression-list? ]
  """
  format = '{0}[{1}]'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      return
      head, rest = postfix_expression.split(ctx, line)
    else:
      rest = line

    if head and startswith_token(rest, '['):
      rest = rest[1:].lstrip()
      if startswith_token(rest, ']'):
        return cls(head, None), rest[1:]

      lst, rest = expression_list.split(ctx, rest)
      if lst:
        if not startswith_token(rest, ']'):
          #assert 0, rest
          return
        assert startswith_token(rest, ']'), rest
        return cls(head, lst), rest[1:]

class postfix_expression_call(grammar('postfix_expression_call', ['postfix_expression', 'expression_list'])):
  """
  postfix-expression ( expression-list? )
  """
  format = '{0}({1})'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      return
      head, rest = postfix_expression.split(ctx, line)
    else:
      rest = line

    if head and startswith_token(rest, '('):
      rest = rest[1:].lstrip()
      if startswith_token(rest, ')'):
        return cls(head, None), rest[1:]

      lst, rest = expression_list.split(ctx, rest)
      if lst:
        if not startswith_token(rest, ')'):
          #assert 0, rest
          return
        assert startswith_token(rest, ')'), rest
        return cls(head, lst), rest[1:]


    
class postfix_expression_proto(grammar('postfix_expression_init', ['simple_type_specifier', 'expression_list'])):
  """
  simple-type-specifier ( expression-list? )
  """
  format = '{0} ({1})'
  @splitter
  def split(cls, ctx, line):
    s, rest = simple_type_specifier.split(ctx, line)
    if s and startswith_token(rest, '('):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, ')'):
        return cls(s, None), rest[1:]
      lst, rest = expression_list.split(ctx, rest)

      if lst and startswith_token(rest, ')'):
        return cls(s, lst), rest[1:]

class typename_specifier_identifier(grammar('typename_specifier_identifier', ['nested-name-specifier', 'identifier'])):
  """
  typename nested-name-specifier identifier
  """
  format = 'typename {0}{1}'
  @splitter
  def split(cls, ctx, line):
    typename, rest = word.split(ctx, line, require='typename')
    if typename:
      ns, rest = nested_name_specifier.split(ctx, rest)
      if ns:
        i, rest = identifier.split(ctx, rest)
        if i:
          return cls(ns, i), rest

class typename_specifier_template_id(grammar('typename_specifier_template_id', ['nested-name-specifier', 'template', 'simple-template-id'])):
  """
  typename nested-name-specifier template? simple-template-id
  """
  format = 'typename {0}{1} {2}'
  @splitter
  def split(cls, ctx, line):
    typename, rest = word.split(ctx, line, require='typename')
    if typename:
      ns, rest = nested_name_specifier.split(ctx, rest)
      if ns:
        template, rest = word.split(ctx, rest, require='template')
        i, rest = simple_template_id.split(ctx, rest)
        if i:
          return cls(ns, template, i), rest

class typename_specifier(switch('typename_specifier', typename_specifier_template_id, typename_specifier_identifier)):
  """
  typename nested-name-specifier identifier
  typename nested-name-specifier template? simple-template-id
  """


class postfix_expression_construct(grammar('postfix_expression_construct', ['typename_specifier', 'expression_list'])):
  """
  typename-specifier ( expression-list? )
  """
  format = '{0} ({1})'
  @splitter
  def split(cls, ctx, line):
    s, rest = typename_specifier.split(ctx, line)
    if s and startswith_token(rest, '('):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, ')'):
        return cls(s, None), rest[1:]
      lst, rest = expression_list.split(ctx, rest)
      if startswith_token(rest, ')'):
        return cls(s, lst), rest[1:]

class braced_init_list(grammar('braced_init_list')):
  """
  { initializer-list ,? }
  { designated-initializer-list ,? }
  { }
  """
  format = '{{ {0} }}'

  @splitter
  def split(cls, ctx, line):
    if line.startswith('{'):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, '}'):
        return cls(None), rest[1:]
      for lcls in [initializer_list, designated_initializer_list]:
        lst, rest2 = lcls.split(ctx, rest)
        if lst:
          if rest2.startswith(','):
            rest2 = rest2[1:].lstrip(ctx.whitespace_characters)
          if not rest2.startswith('}'):
            continue
          assert rest2.startswith('}'), rest2
          return cls(lst), rest2[1:]

    
class postfix_expression_braced_init(sequence('postfix_expression_braced_init', simple_type_specifier, braced_init_list)):
  """
  simple-type-specifier braced-init-list
  """
  
class postfix_expression_member(grammar('postfix_expression_member', ['postfix-expression', 'template', 'id-expression'])):
  """
  postfix-expression . template? id-expression
  """
  format = '{0}.{1} {2}'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      return
      head, rest = postfix_expression.split(ctx, line)
    else:
      rest = line
    if head and startswith_token(rest, '.'):
      t, rest = word.split(ctx, rest[1:].lstrip(ctx.whitespace_characters), require='template')
      e, rest = id_expression.split(ctx, rest)
      if e:
        return cls(head, t, e), rest

class postfix_expression_ptrmember(grammar('postfix_expression_ptrmember', ['postfix-expression', 'template', 'id-expression'])):
  """
  postfix-expression -> template? id-expression
  """
  format = '{0}->{1} {2}'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      # avoid recurrsion, ptrmember is parsed in postprocess
      return
    rest = line
    if head and startswith_token(rest, '->'):
      t, rest = word.split(ctx, rest[2:].lstrip(ctx.whitespace_characters), require='template')
      e, rest = id_expression.split(ctx, rest)
      if e:
        return cls(head, t, e), rest

  
class postfix_expression_incr(grammar('postfix_expression_incr')):
  """
  postfix-expression ++
  """
  format = '{0} ++'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      # avoid recurrsion, ptrmember is parsed in postprocess
      return
    rest = line
    if head and rest.startswith('++'):
      return cls(head), rest[2:]

class postfix_expression_decr(grammar('postfix_expression_decr')):
  """
  postfix-expression --
  """
  format = '{0} --'
  @splitter
  def split(cls, ctx, line, head=None):
    if head is None:
      # avoid recurrsion, ptrmember is parsed in postprocess
      return
    rest = line
    if head and rest.startswith('--'):
      return cls(head), rest[2:]

class pointer_cast_expression(grammar('cast_expression', ['kind', 'type_id', 'expression'])):
  """
  dynamic_cast < type-id > ( expression )
  static_cast < type-id > ( expression )
  reinterpret_cast < type-id > ( expression )
  const_cast < type-id > ( expression )
  """
  @splitter
  def split(cls, ctx, line):
    for k_ in ['dynamic_cast', 'static_cast', 'reinterpret_cast', 'const_cast']:
      k, rest = word.split(ctx, line, require=k_)
      if k:
        break
    else:
      return
    if startswith_token(rest, '<'):
      rest = rest[1:].lstrip()
      raw, rest = split_until(rest, '>')
      t, rest2 = type_id.split(ctx, raw)
      if t:
        if rest2:
          return
        assert rest2 == '', rest2[:100]
        if startswith_token(rest, '('):
          e, rest = expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
          if e:
            assert startswith_token(rest, ')'), rest[:100]
            return cls(k, t, e), rest[1:]

class typeid_expression(grammar('typeid_expression')):
  """
  typeid ( expression )
  typeid ( type-id )
  """
  @splitter
  def split(cls, ctx, line):
    typeid, rest = word.split(ctx, line, require='typeid')
    if typeid and startswith_token(rest, '('):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      for ecls in (type_id, expression):
        a, rest = ecls.split(ctx, rest)
        if a:
          assert startswith_token(rest, ')'), rest[:100]
          return cls(a), rest[1:]

class postfix_expression(switch('postfix_expression',
                                      postfix_expression_braced_init,
                                      postfix_expression_getitem,
                                      postfix_expression_call,
                                      postfix_expression_construct,
                                      postfix_expression_proto,
                                      postfix_expression_member,
                                      postfix_expression_ptrmember,
                                      postfix_expression_incr,
                                      postfix_expression_decr,
                                      pointer_cast_expression,
                                      typeid_expression,
                                      primary_expression,
                                      )):
  """
  primary-expression
  postfix-expression [ expression-list? ]
  postfix-expression ( expression-list? )
  simple-type-specifier ( expression-list? )
  typename-specifier ( expression-list? )
  simple-type-specifier braced-init-list
  typename-specifier braced-init-list
  postfix-expression . template? id-expression
  postfix-expression -> template? id-expression
  postfix-expression ++
  postfix-expression --
  dynamic_cast < type-id > ( expression )
  static_cast < type-id > ( expression )
  reinterpret_cast < type-id > ( expression )
  const_cast < type-id > ( expression )
  typeid ( expression )
  typeid ( type-id )
  """

  @classmethod
  def postprocess(cls, ctx, item, rest):
    if startswith_token(rest, '('):
      item2, rest2 = postfix_expression_call.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)

    elif startswith_token(rest, '['):
      item2, rest2 = postfix_expression_getitem.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)

    elif startswith_token(rest, '.'):
      item2, rest2 = postfix_expression_member.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)

    elif startswith_token(rest, '->'):
      item2, rest2 = postfix_expression_ptrmember.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)

    elif rest.startswith('++'):
      item2, rest2 = postfix_expression_incr.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)

    elif rest.startswith('--'):
      item2, rest2 = postfix_expression_decr.split(ctx, rest, head=item)
      if item2:
        return cls.postprocess(ctx, item2, rest2)
      
    return item, rest
  
class unary_operator_expression(grammar('unary_operator_expression', ['uop', 'cast_expression'])):
  """
  unary-operator cast-expression
  ++ cast-expression
  -- cast-expression

  unary-operator: one of
  *  &  +  -  !  ~
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):

    for uop in ['++', '--', '*', '&', '+', '-', '!', '~']:
      if line.startswith(uop):
        e, rest = cast_expression.split(ctx, line[len(uop):].lstrip(ctx.whitespace_characters))
        if e:
          return cls(line[:len(uop)], e), rest

  def evaluate(self, ctx):
    if isinstance(self.cast_expression, (int, float, bool)):
      if self.uop == '+':
        return self.cast_expression
      elif self.uop == '-':
        return -self.cast_expression
      elif self.uop == '!':
        return not self.cast_expression
      elif self.uop == '~':
        return ~self.cast_expression
    return self

class await_expression(grammar('await_expression')):
  """
  co_await cast-expression
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    a, rest = word.split(ctx, line, require='co_await')
    if a:
      e, rest = cast_expression.split(ctx, rest)
      if e:
        return cls(e), rest

class sizeof_unary_expression(grammar('sizeof_unary_expression')):
  """
  sizeof unary-expression
  """
  format = 'sizeof {0}'
  @splitter
  def split(cls, ctx, line):
    sizeof, rest = word.split(ctx, line, require='sizeof')
    if sizeof:
      e, rest = unary_expression.split(ctx, rest)
      if e:
        return cls(e), rest

class sizeof_expression_typeid(grammar('sizeof_expression_typeid')):
  """
  sizeof ( type-id )
  """
  format = 'sizeof({0})'
  @splitter
  def split(cls, ctx, line):
    sizeof, rest = word.split(ctx, line, require='sizeof')
    if sizeof and startswith_token(rest, '('):
      t, rest = type_id.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
      if t and startswith_token(rest, ')'):
        return cls(t), rest[1:]

class sizeof_expression_identifier(grammar('sizeof_expression_identifier')):
  """
  sizeof ... ( identifier )
  """
  format = 'sizeof ... ({0})'
  @splitter
  def split(cls, ctx, line):
    sizeof, rest = word.split(ctx, line, require='sizeof')
    if sizeof and rest.startswith('...'):
      rest = rest[3:].lstrip()
      if startswith_token(rest, '('):
        t, rest = identifier.split(ctx, rest[1:].lstrip())
        if t and startswith_token(rest, ')'):
          return cls(t), rest[1:].lstrip()

class sizeof_expression(switch('sizeof_expression', sizeof_expression_typeid, sizeof_expression_identifier, sizeof_unary_expression)):
  """
  sizeof unary-expression
  sizeof ( type-id )
  sizeof ... ( identifier )
  """
        
class alignof_expression(grammar('alignof_expression')):
  """
  alignof ( type-id )
  """
  format = 'alignof({0})'
  @splitter
  def split(cls, ctx, line):
    a, rest = word.split(ctx, line, require='alignof')
    if a:
      if startswith_token(rest, '('):
        e, rest = type_id.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
        if e and startswith_token(rest, ')'):
          return cls(e), rest[1:]

class noexcept_expression(grammar('noexcept_expression')):
  """
  noexcept ( expression )
  """
  format = 'noexpect({0})'
  @splitter
  def split(cls, ctx, line):
    a, rest = word.split(ctx, line, require='noexpect')
    if a:
      if startswith_token(rest, '('):
        e, rest = expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
        if e and startswith_token(rest, ')'):
          return cls(e), rest[1:]

class new_placement(grammar('new_placement')):
  """
  ( expression-list )
  """
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      lst, rest = expression_list.split(ctx, line[1:].lstrip(ctx.whitespace_characters))
      if lst and startswith_token(rest, ')'):
        return cls(lst), rest[1:]


    
class noptr_new_declarator_1(grammar('noptr_new_declarator_1')):
  """
  [ expression? ]
  """
  formar = '[{0}]'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('['):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, ']'):
        return cls(None), rest[1:]
      e, rest = expression.split(ctx, rest)
      if e and startswith_token(rest, ']'):
        return cls(e), rest[1:]
 
class noptr_new_declarator_2(grammar('noptr_new_declarator_2', ['noptr-new-declarator', 'constant-expression'])):
  """
  noptr-new-declarator [ constant-expression ]
  """
  formar = '{0} [{1}]'
  @splitter
  def split(cls, ctx, line):
    d, rest = noptr_new_declarator.split(ctx, line)
    if d and startswith_token(rest, '['):
      e, rest = constant_expression.split(ctx, rest[1:])
      if e and startswith_token(rest, ']'):
        return cls(e), rest[1:]

class noptr_new_declarator_head(switch('noptr_new_declarator_head', noptr_new_declarator_1, noptr_new_declarator_2)):
  """
  [ expression? ]
  noptr-new-declarator [ constant-expression ]
  """
  
class noptr_new_declarator(item_optional_suffix(noptr_new_declarator_head, attribute_specifier_seq)):
  """
  [ expression? ] attribute-specifier-seq?
  noptr-new-declarator [ constant-expression ] attribute-specifier-seq?
  """

class new_declarator(switch('new_declarator', lambda: ptr_operator_optional_new_declarator, noptr_new_declarator)):
  """
  ptr-operator new-declarator?
  noptr-new-declarator
  """

class ptr_operator(grammar('ptr_operator', ['nested_name_specifier', 'operator', 'attribute_specifier_seq', 'cv_qualifier_seq'])):
  """
  * attribute-specifier-seq? cv-qualifier-seq?
  & attribute-specifier-seq?
  && attribute-specifier-seq?
  nested-name-specifier * attribute-specifier-seq? cv-qualifier-seq?

  https://timsong-cpp.github.io/cppwp/dcl.decl.general#nt:ptr-operator
  """
  @property
  def format(self):
    if self[0] is not None:
      return '{0} {1} {2} {3}'
    return '{1} {2} {3}'

  @splitter
  def split(cls, ctx, line):
    n, rest = nested_name_specifier.split(ctx, line)
    if n:
      if startswith_token(rest, '*'):
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        a, rest = attribute_specifier_seq.split(ctx, rest)
        cv, rest = cv_qualifier_seq.split(ctx, rest)
        return cls(n, '*', a, cv), rest
    else:
      for op in ['&&', '&', '*']:
        if rest.startswith(op):
          rest = rest[len(op):].lstrip(ctx.whitespace_characters)
          a, rest = attribute_specifier_seq.split(ctx, rest)
          if op == '*':
            cv, rest = cv_qualifier_seq.split(ctx, rest)
          else:
            cv = None
          return cls(None, op, a, cv), rest
  
class ptr_operator_optional_new_declarator(item_optional_suffix(ptr_operator, new_declarator)):
  """
  ptr-operator new-declarator?
  """

def specifier_seq_split(cls, ctx, type_specifier, specifier, line, has_type_specifier = False):
  """
  specifier attribute-specifier-seq?
  specifier specifier-seq
  """
  rest = line
  lst = []
  # https://timsong-cpp.github.io/cppwp/dcl.type.general#2
  #   at most one type-specifier (that is not a cv_qualifier) is allowed in a type-specifier-seq
  while True:
    t, rest_ = specifier.split(ctx, rest)
    if t:
      if isinstance(t, type_specifier):
        if has_type_specifier:
          break
        has_type_specifier = True
      rest = rest_
      lst.append(t)
      a, rest = attribute_specifier_seq.split(ctx, rest)
      if a:
        lst.append(a)
    else:
      break
  if lst:
    return cls(tuple(lst)), rest

class cv_qualifier(keyword('cv_qualifier', 'volatile', 'const')):
  """
  """

class elaborated_type_specifier_class_identifier(grammar('elaborated_type_specifier_class_identifier',
                                                            ['class-key', 'attribute-specifier-seq', 'nested-name-specifier', 'identifier'])):
  """
  class-key attribute-specifier-seq? nested-name-specifier?          identifier
  """
  format = '{0} {1} {2} {3}'
  @splitter
  def split(cls, ctx, line):
    key, rest = class_key.split(ctx, line)
    if key:
      a, rest = attribute_specifier_seq.split(ctx, rest)
      s, rest = nested_name_specifier.split(ctx, rest)
      i, rest = identifier.split(ctx, rest)
      if i:
        return cls(key, a, s, i), rest

class elaborated_type_specifier_class_template_id(grammar('elaborated_type_specifier_class_template_id', ['class-key','simple-template-id'])):
  """
  class-key                                                          simple-template-id
  """
  format = '{0} {1}'
  @splitter
  def split(cls, ctx, line):
    key, rest = class_key.split(ctx, line)
    if key:
      i, rest = simple_template_id.split(ctx, rest)
      if i:
        return cls(key, i), rest
  
class elaborated_type_specifier_class_nested_template_id(grammar('elaborated_type_specifier_class_nested_template_id',
                                                                    ['class-key', 'nested-name-specifier', 'template', 'simple-template-id'])):
  """
  class-key                          nested-name-specifier template? simple-template-id
  """
  format = '{0} {1}{2} {3}'
  @splitter
  def split(cls, ctx, line):
    key, rest = class_key.split(ctx, line)
    if key:
      s, rest = nested_name_specifier.split(ctx, rest)
      if s:
        template, rest = word.split(ctx, line, require='template')
        i, rest = simple_template_id.split(ctx, rest)
        if i:
          return cls(key, s, template, i), rest

class elaborated_type_specifier_enum_identifier(grammar('elaborated_type_specifier_enum_identifier', ['nested-name-specifier', 'identifier'])):
  """
  enum                               nested-name-specifier?          identifier
  """
  format = 'enum {0} {1}'
  @splitter
  def split(cls, ctx, line):
    enum, rest = word.split(ctx, line, require='enum')
    if enum:
      s, rest = nested_name_specifier.split(ctx, rest)
      i, rest = identifier.split(ctx, rest)
      if i:
        return cls(s, i), rest

class elaborated_type_specifier(switch('elaborated_type_specifier',
    elaborated_type_specifier_class_template_id,
    elaborated_type_specifier_class_nested_template_id,
    elaborated_type_specifier_class_identifier,
    elaborated_type_specifier_enum_identifier)):
  """
  class-key attribute-specifier-seq? nested-name-specifier?          identifier
  class-key                                                          simple-template-id
  class-key                          nested-name-specifier template? simple-template-id
  enum                               nested-name-specifier?          identifier
  """

  
class type_specifier(switch('type_specifier',
                                  cv_qualifier,
                                  simple_type_specifier,
                                  typename_specifier,
                                  elaborated_type_specifier,
                                  )):
  """
  simple-type-specifier
  elaborated-type-specifier
  typename-specifier
  cv-qualifier
  """
  @classmethod
  def postprocess(cls, ctx, item, rest):
    if not isinstance(item, cv_qualifier) and item:
      item = cls(item)
    return item, rest


class type_specifier_seq(grammar('type_specifier_seq')):
  """
  type-specifier attribute-specifier-seq?
  type-specifier type-specifier-seq
  """

  @splitter
  def split(cls, ctx, line):
    return specifier_seq_split(cls, ctx, type_specifier, type_specifier, line)

  
class new_type_id(item_optional_suffix(type_specifier_seq, new_declarator)):
  """
  type-specifier-seq new-declarator?
  """

class type_id_with_parenthesis(grammar('type_id_with_parenthesis')):
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      t, rest = type_id.split(ctx, line[1:].lstrip(ctx.whitespace_characters))
      if t and startswith_token(rest, ')'):
        return cls(lst), rest[1:]

class new_type_id_or_parenthesis(switch('new_type_id_or_parenthesis', type_id_with_parenthesis, new_type_id)):
  pass

class expression_list_with_parenthesis(grammar('expression_list_with_parenthesis')):
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      if startswith_token(rest, ')'):
        return cls(None), rest[1:]
      e, rest = expression_list.split(ctx, rest)
      if e:
        assert startswith_token(rest, ')'), rest
        return cls(e), rest[1:]

class new_initializer(switch('new_initializer', expression_list_with_parenthesis, braced_init_list)):
  """
  ( expression-list? )
  braced-init-list
  """

class new_expression(grammar('new_expression', ['scope', 'new_placement', 'type_id_part', 'new_initializer'])):
  """
  ::? new new-placement? new-type-id new-initializer?
  ::? new new-placement? ( type-id ) new-initializer?
  """
  format = '{0} new {1} {2} {3}'
  @splitter
  def split(cls, ctx, line):
    s = None
    if line.startswith('::'):
      s = line[:2]
      rest = line[2:].lstrip(ctx.whitespace_characters)
    else:
      rest = line
    new, rest = word.split(ctx, rest, require='new')
    if new:
      p, rest = new_placement.split(ctx, rest)
      t, rest = new_type_id_or_parenthesis.split(ctx, rest)
      if t:
        i, rest = new_initializer.split(ctx, rest)
        return cls(s, p, t, i), rest

class delete_expression(grammar('delete_expression', ['scope', 'braces', 'cast_expression'])):
  """
  ::? delete cast-expression
  ::? delete [ ] cast-expression
  """
  format = '{0} delete {1} {2}'
  @splitter
  def split(cls, ctx, line):
    if line.startswith('::'):
      s = line[:2]
      rest = line[2:].lstrip(ctx.whitespace_characters)
    else:
      s = None
      rest = line
    delete, rest = word.split(ctx, rest, require='delete')
    if delete:
      if startswith_token(rest, '['):
        rest = rest[1:].lstrip(ctx.whitespace_characters)
        if startswith_token(rest, ']'):
          rest = rest[1:].lstrip(ctx.whitespace_characters)
          e, rest = cast_expression.split(ctx, rest)
          if e:
            return cls(s, '[]', e), rest
      else:
        e, rest = cast_expression.split(ctx, rest)
        if e:
          return cls(s, None, e), rest      

class unary_expression(switch('unary_expression',
                                    unary_operator_expression,
                                    await_expression,
                                    sizeof_expression,
                                    alignof_expression,
                                    noexcept_expression,
                                    new_expression,
                                    delete_expression,
                                    postfix_expression,)):
  """
  postfix-expression
  unary-operator cast-expression
  ++ cast-expression
  -- cast-expression
  await-expression
  sizeof unary-expression
  sizeof ( type-id )
  sizeof ... ( identifier )
  alignof ( type-id )
  noexcept-expression
  new-expression
  delete-expression
  """


class cast_expression(grammar('cast_expression', ['type_id', 'cast_expression'])):
  """
  unary-expression
  ( type-id ) cast-expression
  """
  format = '( {0} ) {1}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, '('):
      t, rest = type_id.split(ctx, line[1:].lstrip(ctx.whitespace_characters))
      if t and startswith_token(rest, ')'):
        e, rest = cast_expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
        if e:
          return cls(t, e), rest
    e, rest = unary_expression.split(ctx, line)
    if e:
      return e, rest

def evaluate_left_to_right(unevaluated, operands_and_operations, operations):
  left = operands_and_operations[0]
  if isinstance(left, (int, float, bool)):
    for op, right in zip(operands_and_operations[1::2], operands_and_operations[2::2]):
      if isinstance(right, (int, float, bool)):
        opdef = operations.get(op)
        if opdef is not None:
          left = opdef(left, right)
          continue
      break
    else:
      return left
  return unevaluated
  
class pm_expression(pair_or_item('pm_expression', ['.*', '->*'], cast_expression)):
  """
  cast-expression
  pm-expression .* cast-expression
  pm-expression ->* cast-expression
  """

class multiplicative_expression(pair_or_item('multiplicative_expression', ['*', '/', '%'], pm_expression)):
  """
  pm-expression
  multiplicative-expression * pm-expression
  multiplicative-expression / pm-expression
  multiplicative-expression % pm-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content,
                                  {'*': lambda x, y: x * y,
                                   '/': lambda x, y: x // y if isinstance(x, int) and isinstance(y, int) else x / y,
                                   '%': lambda x, y: x % y})

class additive_expression(pair_or_item('additive_expression', ['+', '-'], multiplicative_expression)):
  """
  multiplicative-expression
  additive-expression + multiplicative-expression
  additive-expression - multiplicative-expression
  """

  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'+': lambda x, y: x + y,
                                              '-': lambda x, y: x - y})
  
class shift_expression(pair_or_item('shift_expression', ['<<', '>>'], additive_expression)):
  """
  additive-expression
  shift-expression << additive-expression
  shift-expression >> additive-expression
  """

  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'<<': lambda x, y: x << y,
                                              '>>': lambda x, y: x >> y})
  
class compare_expression(pair_or_item('compare_expression', ['<=>'], shift_expression)):
  """
  shift-expression
  compare-expression <=> shift-expression
  """

class relational_expression(pair_or_item('relational_expression', ['<=', '>=', '<', '>'], compare_expression)):
  """
  compare-expression
  relational-expression < compare-expression
  relational-expression > compare-expression
  relational-expression <= compare-expression
  relational-expression >= compare-expression
  """

  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'<': lambda x, y: x < y,
                                                 '<=': lambda x, y: x <= y,
                                                 '>': lambda x, y: x > y,
                                                 '>=': lambda x, y: x >= y})
  
class equality_expression(pair_or_item('equality_expression', ['==', '!='], relational_expression)):
  """
  relational-expression
  equality-expression == relational-expression
  equality-expression != relational-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'==': lambda x, y: x == y,
                                                       '!=': lambda x, y: x != y})
  
class and_expression(pair_or_item('and_expression', '&', equality_expression)):
  """
  equality-expression
  and-expression & equality-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'&': lambda x, y: x & y})

class exlucive_or_expression(pair_or_item('exlucive_or_expression', '^', and_expression)):
  """
  and-expression
  exclusive-or-expression ^ and-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'^': lambda x, y: x ^ y})

class inclusive_or_expression(pair_or_item('inclusive_or_expression', '|', exlucive_or_expression)):
  """
  exclusive-or-expression
  inclusive-or-expression | exclusive-or-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'|': lambda x, y: x | y})

class logical_and_expression(pair_or_item('logical_and_expression', '&&', inclusive_or_expression)):
  """
  inclusive-or-expression
  logical-and-expression && inclusive-or-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'&&': lambda x, y: bool(x and y)})
  
class logical_or_expression(pair_or_item('logical_or_expression', '||', logical_and_expression)):
  """
  logical-and-expression
  logical-or-expression || logical-and-expression
  """
  def evaluate(self, ctx):
    return evaluate_left_to_right(self, self.content, {'||': lambda x, y: bool(x or y)})

class assignment_operator(grammar('assignment_operator')):
  @splitter
  def split(cls, ctx, line):
    for aop in ['>>=', '<<=', '*=',  '/=',  '%=',   '+=',  '-=', '&=',  '^=',  '|=', '=']:
      if line.startswith(aop):
        return line[:len(aop)], line[len(aop):]

class assignment_expression_assignment(sequence('assignment_expression_assignment', logical_or_expression, assignment_operator, lambda: initializer_clause)):
  """
  logical-or-expression assignment-operator initializer-clause

  assignment-operator: one of
  =  *=  /=  %=   +=  -=  >>=  <<=  &=  ^=  |=
  """
  
class conditional_expression(grammar('conditional_expression', ['logical_or_expression', 'expression', 'assignment_expression'])):
  """
  logical-or-expression
  logical-or-expression ? expression : assignment-expression
  """
  format = '{0} ? {1} : {2}'
  @splitter
  def split(cls, ctx, line):
    l, rest = logical_or_expression.split(ctx, line)
    if l:
      if rest.startswith('?'):
        e, rest = expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
        if e:
          if startswith_token(rest, ':'):
            a, rest = assignment_expression.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
            if a:
              return cls(l, e, a), rest
      else:
        return l, rest

class yield_expression(grammar('yield_expression')):
  """
  co_yield assignment-expression
  co_yield braced-init-list
  """
  format = 'co_yield {0}'
  @splitter
  def split(cls, ctx, line):
    co_yield, rest = word.split(ctx, line, require='co_yield')
    if co_yield:
      lst, rest = braced_init_list.split(ctx, rest)
      if lst:
        return cls(lst), rest
      a, rest = assignment_expression.split(ctx, rest)
      if a:
        return cls(a), rest

class throw_expression(grammar('throw_expression')):
  """
  throw assignment-expression?
  """
  format = 'throw {0}'
  @splitter
  def split(cls, ctx, line):
    throw, rest = word.split(ctx, line, require='throw')
    if throw:
      a, rest = assignment_expression.split(ctx, rest)
      return cls(a), rest

class assignment_expression(switch('assignment_expression',
                                         yield_expression,
                                         throw_expression,
                                         assignment_expression_assignment,
                                         conditional_expression,
                                         )):
  """
  conditional-expression
  yield-expression
  throw-expression
  logical-or-expression assignment-operator initializer-clause
  """

class expression(pair_or_item('expression', ',', assignment_expression)):
  """
  assignment-expression
  expression , assignment-expression
  """

class constant_expression(switch('constant_expression', conditional_expression)):
  """
  conditional-expression
  """

class initializer_clause(switch('initializer_clause', braced_init_list, assignment_expression)):
  """
  assignment-expression
  braced-init-list
  """
  
class initializer_clause_dots(grammar('initializer_clause_dots')):
  """
  initializer-clause ...?
  """
  format = '{0} ...'
  @splitter
  def split(cls, ctx, line):
    i, rest = initializer_clause.split(ctx, line)
    if i:
      if rest.startswith('...'):
        return cls(i), rest[3:].lstrip()
      return i, rest

class initializer_list(pair_or_item('initializer_list', ',', initializer_clause_dots)):
  """
  initializer-clause ...?
  initializer-list , initializer-clause ...?
  """

class expression_list(switch('expression_list', initializer_list)):
  pass

  
class module_name_qualifier(item_sequence("module_name_qualifier", identifier_with_a_dot)):
  """
  identifier .
  module-name-qualifier identifier .
  """

class module_name(item_optional_prefix(identifier, module_name_qualifier)):
  """
  module-name-qualifier? identifier
  """

class module_partition(grammar('module_partition', ['module-name-qualifier', 'identifier'])):
  """
  : module-name-qualifier? identifier
  """
  format = ': {0} {1}'
  @splitter
  def split(cls, ctx, line):
    if startswith_token(line, ':'):
      rest = line[1:].lstrip(ctx.whitespace_characters)
      q, rest = module_name_qualifier.split(ctx, rest)
      i, rest = identifier.split(ctx, rest)
      if i:
        return cls(q, i), rest

class module_declaration(grammar('module_declaration')):
  """
  export-keyword? module-keyword module-name module-partition? attribute-specifier-seq? ;
  """
  format = '{0} module {2} {3} {4};'
  @splitter
  @utils.require_and_drop_semicolon
  def split(cls, ctx, line):
    e, rest = word.split(ctx, line, require='export')
    module, rest = word.split(ctx, rest, require='module')
    if module:
      n, rest = module_name.split(ctx, rest)
      if n:
        p, rest = module_partition.split(ctx, rest)
        a, rest = attribute_specifier_seq.split(ctx, rest)
        return cls(e, n, p, a), rest


class private_module_fragment(grammar('private_module_fragment')):
  """
  module-keyword : private ; declaration-seq?
  """
  format = 'module:private; {0}'
  @splitter
  @utils.require_and_drop_semicolon
  def split(cls, ctx, line):
    module, rest = word.split(ctx, line, require='module')
    if module and startswith_token(rest, ':'):
      rest = rest[1:].lstrip(ctx.whitespace_characters)
      private, rest = word.split(ctx, rest, require='private')
      if private and rest.startswith(';'):
        s, rest = declaration_seq.split(ctx, rest[1:].lstrip(ctx.whitespace_characters))
        return cls(s), rest


class translation_unit(grammar('translation_unit', ['global-module-fragment', 'module-declaration', 'declaration-seq', 'private-module-fragment'])):
  """
                                             declaration-seq?
  global-module-fragment? module-declaration declaration-seq? private-module-fragment?
  """
  format = '{0} {1} {2} {3}'
  @splitter
  def split(cls, ctx, line):
    gf, rest = global_module_fragment.split(ctx, line)
    m, rest = module_declaration.split(ctx, rest)

    head_lines = line[:len(line) - len(rest)]
    s, rest = declaration_seq.split(ctx, rest)
    pf, rest = private_module_fragment.split(ctx, rest)

    if rest:
      utils.report_unexpected_block_end(cls, head_lines, rest)
      raise RuntimeError(f'unexpected return when parsing {cls.__name__} (see output above)')
    if (gf or pf and m) or not (gf or pf or m):
      return cls(gf, m, s, pf), rest
