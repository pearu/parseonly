from parseonly import grammar as g

def test_grammar():

  class myspec(g.grammar('myspec', ['part', 'another-part'])):
    format = 'myspec says {0} {1}!'
    @g.splitter
    def split(cls, ctx, line):
      p, rest = g.word.split(ctx, line, require='foo', discard='bar')
      a, rest = g.word.split(ctx, rest, require='car')
      if p:
        return cls(p, a), rest

    @classmethod
    def postprocess(cls, ctx, spec, rest):
      if rest.startswith('?'):
        return None
      return spec, rest

  assert issubclass(myspec, tuple)  # grammar derived from namedtuple
  assert issubclass(myspec, g.Grammar)
  assert myspec._fields == ('part', 'another_part')

  ctx = g.Context()

  w, rest = myspec.split(ctx, 'foo car')
  assert w is not None
  assert w[0] == 'foo'
  assert w.part == 'foo'
  assert w[1] == 'car'
  assert w.another_part == 'car'

  assert str(w) == 'myspec says foo car!'

  w, rest = myspec.split(ctx, 'bar car')
  assert w is None

  w, rest = myspec.split(ctx, 'foo bar')
  assert tuple(w) == ('foo', None)
  assert str(w) == 'myspec says foo!'

  w, rest = myspec.split(ctx, 'foo car?')
  assert w is None
  assert rest == 'foo car?'


def test_word():
  ctx = g.Context()
  line = 'Hello there!'
  w, rest = g.word.split(ctx, line)
  assert w == 'Hello'
  w, rest = g.word.split(ctx, rest)
  assert w == 'there'
  assert rest == '!'

  w, rest = g.word.split(ctx, line, require='Hello')
  assert w == 'Hello'

  w, rest = g.word.split(ctx, line, require='Hi')
  assert w is None

  w, rest = g.word.split(ctx, 'Hello there!', require=['Hello', 'Hi'])
  assert w == 'Hello'

  w, rest = g.word.split(ctx, 'Hi there!', require=['Hello', 'Hi'])
  assert w == 'Hi'

  w, rest = g.word.split(ctx, 'Hola there!', require=['Hello', 'Hi'])
  assert w is None


def test_item_sequence():

  class word_seq(g.item_sequence(g.word)):
    pass

  ctx = g.Context()

  lst, rest = word_seq.split(ctx, 'Hello there 123ABC!')
  assert lst.content == ('Hello', 'there')
  assert rest == '123ABC!'
  
  lst, rest = word_seq.split(ctx, 'Hello!')
  assert lst.content == ('Hello',)

  lst, rest = word_seq.split(ctx, '!Hello')
  assert lst is None


def test_pair_or_item():

  class word_list(g.pair_or_item('word_list', ',', g.word)):
    pass

  ctx = g.Context()

  lst, rest = word_list.split(ctx, 'Hello there 123ABC!')
  assert lst == 'Hello'
  lst, rest = word_list.split(ctx, 'Hello, there 123ABC!')
  assert lst.content == ('Hello', ',', 'there')
  lst, rest = word_list.split(ctx, 'Hello, there, 123ABC!')
  assert lst.content == ('Hello', ',', 'there')

  lst, rest = word_list.split(ctx, 'Hello, there, where 123ABC!')
  assert lst.content == ('Hello', ',', 'there', ',', 'where')

  class sentence(g.pair_or_item('sentence', ['and', 'or'], g.word)):
    pass

  lst, rest = sentence.split(ctx, 'car')
  assert lst == 'car'

  lst, rest = sentence.split(ctx, 'car bar')
  assert lst == 'car'

  lst, rest = sentence.split(ctx, 'car and bar')
  assert lst.content == ('car', 'and', 'bar')

  lst, rest = sentence.split(ctx, 'car and bar or foo')
  assert lst.content == ('car', 'and', 'bar', 'or', 'foo')

def test_item_optional_prefix():

  class word_prefix(g.item_optional_prefix(g.word, 'hello')):
    format = 'hi {1}'

  ctx = g.Context()

  m, rest = word_prefix.split(ctx, 'hello there!')
  assert m.prefix == 'hello'
  assert m.content == 'there'
  assert rest == '!'
  assert str(m) == 'hi there'

  m, rest = word_prefix.split(ctx, 'there hello!')
  assert m == 'there'
  assert rest == 'hello!'

  
def test_item_optional_suffix():

  class word_with_dots(g.item_optional_suffix(g.word, '...')):
    format = '{0}...'

  ctx = g.Context()
  m, rest = word_with_dots.split(ctx, 'hello there!')
  assert m == 'hello'
  m, rest = word_with_dots.split(ctx, 'hello... there!')
  assert m.content == 'hello'
  assert m.suffix == '...'

  assert str(m) == 'hello...'


def test_switch():

  class select_words(g.switch('select', 'hi', 'hello')):
    pass

  ctx = g.Context()
  m, rest = select_words.split(ctx, 'hello there!')
  assert m == 'hello'
  m, rest = select_words.split(ctx, 'hi there!')
  assert m == 'hi'
  m, rest = select_words.split(ctx, 'hola there!')
  assert m is None


def test_sequence():

  class full_sentence(g.sequence('select', 'hi', 'there')):
    whitespace_characters = ' '

  ctx = g.Context()
  m, rest = full_sentence.split(ctx, 'hi there!')
  assert rest == '!', rest
  assert m.content == ('hi', 'there')
