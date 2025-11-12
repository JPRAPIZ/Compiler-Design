
from lexer import Lexer

demo = r"""tile x = 10;
glass g = -5.25;
wall s = "He\tllo";
brick c = '\n';
if (solid && x >= 10) {
  // line
  view("#d", s);
  g /= 2.0;  a123   // number then ident not allowed
  c = 'AB';        // error
  do { write("ok"); } while (0);
  FRAGILE;         // IDENTIFIER (case-sensitive)
  1x;              // error
  12.3abc;         // error
  -5y;             // error
  a = 1..2;        // error
  a = 1.|2;        // error
  a = 1.&2;        // error
}
"""

L = Lexer(demo)
tokens = L.tokenize_all()

for t in tokens:
    print(t.type, repr(t.lexeme), f"@{t.line}:{t.col}")
    # Backend can read t.trace if needed:
    # print("  trace:", t.trace)

if L.errors:
    print("\nErrors:")
    for e in L.errors:
        print(e)
