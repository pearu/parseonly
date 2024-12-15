from parseonly.grammar import Context
from parseonly.cpp import grammar as cpp
from parseonly.cxx import grammar as cxx

def test_preprocessing_token():
  ctx = Context()
  split = lambda line: cpp.preprocessing_token.split(ctx, line)

  n, rest = split('name!')
  assert isinstance(n, cpp.identifier)
  assert str(n) == 'name'

  n, rest = split('1.2!')
  assert isinstance(n, cxx.decimal_floating_point_literal)
  assert str(n) == '1.2'
  
  n, rest = split('123!')
  assert isinstance(n, cxx.decimal_literal)
  assert str(n) == '123'

  n, rest = split('<string>!')
  assert isinstance(n, cpp.header_name)
  assert str(n) == '<string>'

  n, rest = cpp.header_name.split(ctx, '"string"!')
  assert isinstance(n, cpp.header_name)
  assert str(n) == '"string"'

  n, rest = split('"string"!')
  assert isinstance(n, cxx.ordinary_string_literal_quotes)
  assert str(n) == '"string"'

  n, rest = split("'string'!")
  assert isinstance(n, cxx.character_literal)
  assert str(n) == "'string'"

  n, rest = split("...!")
  assert isinstance(n, cpp.operator_or_punctuator)
  assert str(n) == "..."

  n, rest = split("<!")
  assert isinstance(n, cpp.operator_or_punctuator)
  assert str(n) == "<"

  n, rest = split("bitor!")
  assert isinstance(n, cpp.operator_or_punctuator)
  assert str(n) == "bitor"

  n, rest = split("import!")
  assert isinstance(n, cpp.import_keyword)
  assert str(n) == "import"

  n, rest = split("@!")
  assert isinstance(n, cpp.non_whitespace_character)
  assert str(n) == "@"
  
def test_pp_tokens():

  ctx = Context()
  split = lambda line: cpp.pp_tokens.split(ctx, line)

  n, rest = split('#   include    <string>')
  assert isinstance(n, cpp.pp_tokens)
  assert str(n) == '# include <string>'

  n, rest = split('#   include    "mystring"')
  assert isinstance(n, cpp.pp_tokens)
  assert str(n) == '# include "mystring"'

def test_preprocessing_file():
  ctx = Context(
      whitespace=cpp.whitespace_without_newline,
      trace=not True)
  split = lambda text: cpp.preprocessing_file.split(ctx, text)

  text = '''
#define FOO 1

#  define    BAR   A
'''
  with ctx.uses_language('cpp'):
    pp, rest = split(text)
  assert rest == '', rest
  assert str(pp) == '\n#define FOO 1\n\n#define BAR A\n'

  text = '''
int foo() {
#ifdef BAR
#define HAVE_BAR
  return 1;
#elifdef CAR
  int b;
#ifndef FOO
#if defined(FOO100)
  return 2;
#endif
#else
  return 20;
#endif
#else
  return 3;
#endif
}
'''
  with ctx.uses_language('cpp'):
    pp, rest = split(text)
  print(pp.tostring())
  assert str(pp) == '\nint foo ( ) {\n#if defined(BAR)\n#\tdefine HAVE_BAR\nreturn 1 ;\n#elif defined(CAR)\nint b ;\n#\tif ! defined(FOO)\n#\t\tif defined(FOO100)\nreturn 2 ;\n#\t\tendif\n#\telse\n\nreturn 20 ;\n#\tendif\n#else\n\nreturn 3 ;\n#endif\n}\n'

  assert rest == '', rest

def test_preprocess_basic():
  text = '''
#define BAR FOO
#define FOO foo
#define ARGS(T,X) T& X
void BAR(ARGS(const int, x)) {}
'''
  assert str(cpp.preprocess(text)) == '''



void foo ( const int & x ) { }
'''

def test_preprocess_ex00():
  
  text = '''
#define F(...)           f(0 __VA_OPT__(,) __VA_ARGS__)
#define G(X, ...)        f(0, X __VA_OPT__(,) __VA_ARGS__)
#define SDEF(sname, ...) S sname __VA_OPT__(= { __VA_ARGS__ })
#define EMP
F(a, b, c)
F()
F(EMP)

G(a, b, c)
G(a, )
G(a)

SDEF(foo);
SDEF(bar, 1, 2);
'''
  assert str(cpp.preprocess(text)) == '''




f ( 0 , a , b , c )
f ( 0 )
f ( 0 )

f ( 0 , a , b , c )
f ( 0 , a )
f ( 0 , a )

S foo ;
S bar = { 1 , 2 } ;
'''

def test_preprocess_ex00_1():
  
  text = '''
#define F(...)           f(0 __VA_OPT__(,) __VA_ARGS__)
#define EMP
F(EMP)
'''
  assert str(cpp.preprocess(text)) == '''


f ( 0 )
'''

def test_preprocess_ex01():
  
  text = '''
#define F(...)           f(0 __VA_OPT__(,) __VA_ARGS__)
#define G(X, ...)        f(0, X __VA_OPT__(,) __VA_ARGS__)
#define SDEF(sname, ...) S sname __VA_OPT__(= { __VA_ARGS__ })
#define EMP
G(a)
'''
  assert str(cpp.preprocess(text)) == '''




f ( 0 , a )
'''
  
def test_preprocess_ex02():
  
  text = '''
#define LPAREN() (
#define G(Q) 42
#define F(R, X, ...)  __VA_OPT__(G R X) )
int x = F(LPAREN(), 0, <:-);
'''
  assert str(cpp.preprocess(text)) == '''



int x = 42 ;
'''

def test_preprocess_ex03():
  text = '''
#define glue(x, y) x ## y
glue(a, b)
glue(a, 1)
glue(1, b)
glue(1, 2)
'''

  assert str(cpp.preprocess(text)) == '''

ab
a1
1b
12
'''

def test_preprocess_ex04():
  text = '''
#define INCFILE(n)  vers ## n
#define glue(a, b)  a ## b
#define xglue(a, b) glue(a, b)
#define HIGHLOW     "hello"
#define LOW         LOW ", world"
glue(HIGH, LOW);
xglue(HIGH, LOW)
'''
  assert str(cpp.preprocess(text)) == '''





"hello" ;
"hello" ", world"
'''

def test_preprocess_ex05():
  text = '''
#define str(s)      # s
#define xstr(xs)     str(xs)
#define debug(s, t) printf("x" # s "= %d, x" # t "= %s", \
               x ## s, x ## t)
#define INCFILE(n)  vers ## n
str(A)
xstr(INCFILE(2).h)
debug(1, 2);
fputs(str(strncmp("abc\\0d", "abc", '\\4')==0) // this goes away
str(:@\\n), s);
'''
  assert str(cpp.preprocess(text)) == '''




"A"
"vers2.h"
printf ( "x" "1" "= %d, x" "2" "= %s" , x1 , x2 ) ;
fputs ( "strncmp(\\"abc0d\\",\\"abc\\",'4')==0" @ @ @ < 1 @ @ @
":@n" , s ) ;
'''

def test_preprocess_ex06():
  text = '''
#define str(s)      # s
#define xstr(xs)     str(xs)
#define INCFILE(n)  vers ## n
#include xstr(INCFILE(2).h)
'''
  assert str(cpp.preprocess(text)) == '''



#include "vers2.h"
'''

def _test_preprocess_ex07():
  text = '''
#define hash_hash # ## #
#define mkstr(a) # a
#define in_between(a) mkstr(a)
#define join(c, d) in_between(c hash_hash d)
char p[] = join(x, y);
'''
  # TODO: fix me
  assert str(cpp.preprocess(text)) == '''




char p [ ] = "x ## y" ;
'''

def test_preprocess_ex08():
  text = '''
#define t(x,y,z) x ## y ## z
int j[] = { t(1,2,3), t(,4,5), t(6,,7), t(8,9,),
  t(10,,), t(,11,), t(,,12), t(,,) };
'''

  assert str(cpp.preprocess(text)) == '''

int j [ ] = { 123 , 45 , 67 , 89 ,
10 , 11 , 12 , } ;
'''

def test_preprocess_ex09():
  text = '''
#define x       3
#define f(a)    f(x * (a))
#undef  x
#define x       2
#define g       f
#define z       z[0]
#define h       g(~
#define m(a)    a(w)
#define w       0,1
#define t(a)    a
#define p()     int
#define q(x)    x
#define r(x,y)  x ## y
#define str(x)  # x
f(y+1) + f(f(z)) % t(t(g)(0) + t)(1);
g(x+(3,4)-w) | h 5) & m    (f)^m(m);
p() i[q()] = { q(1), r(2,3), r(4,), r(,5), r(,) };
char c[2][6] = { str(hello), str() };
'''
  assert str(cpp.preprocess(text)) == '''














f ( 2 * ( y + 1 ) ) + f ( 2 * ( f ( 2 * ( z [ 0 ] ) ) ) ) % f ( 2 * ( 0 ) ) + t ( 1 ) ;
f ( 2 * ( 2 + ( 3 , 4 ) - 0 , 1 ) ) | f ( 2 * ( ~ 5 ) ) & f ( 2 * ( 0 , 1 ) ) ^ m ( 0 , 1 ) ;
int i [ ] = { 1 , 23 , 4 , 5 , } ;
char c [ 2 ] [ 6 ] = { "hello" , "" } ;
'''

def test_preprocess_ex11():
  text = '''
#define str(s)      # s # s # 123
#define xstr(xs)     str(xs)
str(1)
'''
  assert str(cpp.preprocess(text)) == '''


"1" "1" "123"
'''
