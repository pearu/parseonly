
from parseonly.cxx import grammar as g
from parseonly.cpp.utils import separate_comments, remove_backslashes, reference_comments

def test_reference_comments():
  text = '''
    /*****************************
     FOO
     *****************************/ void foo()
    {
      int \t /* this is i comment */ i;
    }
    // this is A
    class A { //short
      int a;  // this is a
      FOO("See this site http://comment.com that has inline comments /* like this */!")
    }; // end comment'''
  stext, cdict = reference_comments(text, label_format='@@@{direction}{count}@@@')
  assert stext == '\n    @@@>1@@@\n\n                                                                  void foo()\n    {\n      int \t @@@<2@@@                i;\n    }\n    @@@>3@@@    \n    class A { @@@<4@@@\n      int a;  @@@<5@@@    \n      FOO("See this site http://comment.com that has inline comments /* like this */!")\n    }; @@@<6@@@      '
  assert cdict['@@@>1@@@'] == '****************************\n     FOO\n     ****************************'
  assert cdict['@@@<2@@@'] == ' this is i comment '
  assert cdict['@@@>3@@@'] == ' this is A'
  assert cdict['@@@<4@@@'] == 'short'
  assert cdict['@@@<5@@@'] == ' this is a'
  assert cdict['@@@<6@@@'] == ' end comment'
  assert text.count('\n') == stext.count('\n')

  stext2, cdict = reference_comments(text, label_format='[["{direction}"{count}]]')
  assert stext2 == stext.replace('@@@>', '[[">"').replace('@@@<', '[["<"').replace('@@@', ']]')

def test_separate_comments():

  text = '''
    /******************************/ void foo()
    {
      int \t /* this is i comment */ i;
    }
    class A {
      int a;  // this is a
      FOO("See this site http://comment.com that has inline comments /* like this */!")
    };'''

  stext, ctext = separate_comments(text)
  assert stext == '\n                                     void foo()\n    {\n      int \t                         i;\n    }\n    class A {\n      int a;              \n      FOO("See this site http://comment.com that has inline comments /* like this */!")\n    };'
  assert ctext == '\n    /******************************/           \n     \n          \t /* this is i comment */   \n     \n             \n              // this is a\n                                                                                       \n      '

def test_remove_backslashes():
  text = r'''
  a\   
b
  A   \
B
  a \
  b \
  c
  d
  '''
  stext = remove_backslashes(text)
  assert stext == '\n  a\nb\n  A   B\n\n  a   b   c\n\n\n  d\n  '
  assert text.count('\n') == stext.count('\n')

def test_identifier():
  ctx = g.Context()
  w, rest = g.identifier.split(ctx, 'hello there')
  assert w == 'hello'

  w, rest = g.identifier.split(ctx, 'if there')
  assert w is None
