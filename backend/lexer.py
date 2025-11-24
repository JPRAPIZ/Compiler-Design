
from typing import List
from tokens import Token, formatToken

KEYWORDS = {
    "tile", "glass", "brick", "wall", "beam", "field", "house",
    "if", "else", "room", "door", "ground",
    "for", "while", "do",
    "crack", "mend", "home",
    "blueprint", "view", "write",
    "solid", "fragile", "cement", "roof",
}

OPERATORS = {
    "+", "-", "*", "/", "%",
    "++", "--",
    "=", "+=", "-=", "*=", "/=", "%=",
    "<", ">", "==", "!=", "<=", ">=",
    "&&", "||", "!",
}

SYMBOLS = {
    "{", "}", "(", ")", "[", "]",
    ":", ";", ",", ".", "&",
}

def isNumberChar(ch: str) -> bool:
    return ch in {'0','1','2','3','4','5','6','7','8','9'}

def isAlphaIdChar(ch: str) -> bool:
    return (ch.isalpha() and ch.isascii()) or ch == '_'

def isAlphaNumChar(ch: str) -> bool:
    return isNumberChar(ch) or isAlphaIdChar(ch)

def isWhitespaceChar(ch: str) -> bool:
    return ch == ' ' or ch == '\t' or ch == '\n'

def isOperatorChar(ch: str) -> bool:
    return ch in {'+','-','*','/','%','<','>','=','!','&','|'}

def isAscii3(ch: str) -> bool:
    if not ch or len(ch) != 1:
        return False
    o = ord(ch)
    return 32 <= o <= 126

# Tokens wit delimiter whitespace
whitespace = {
    "beam", "brick", "cement", "door", "field",
    "glass", "home", "house", "roof", "tile", "wall", ":"
}

# Tokens wit delimiter alpha_id
alpha_id = {"&", "."}

delim1  = {"blueprint", "for", "if", "room", "view", "while", "write"}
delim2  = {"crack", "mend"}
delim3  = {"do", "else"}
delim4  = {"fragile", "solid"}
delim5  = {"ground"}
delim6  = {"="}
delim7  = {"==", ">", ">=", "<", "<=", "!", "!=", "&&", "||"}
delim8  = {"+"}
delim9  = {"++", "--"}
delim10 = {"+=", "-=", "*", "*=", "/", "/=", "%", "%="}
delim11 = {"-"}
delim12 = {"{"}
delim13 = {"}"}
delim14 = {"("}
delim15 = {")"}
delim16 = {"["}
delim17 = {"]"}
delim18 = {","}
delim19 = {";"}
delim20 = {"id"}
delim21 = {"tile_lit"}
delim22 = {"glass_lit"}
delim23 = {"brick_lit"}
delim24 = {"wall_lit"}
delim25 = {"Multi-Line Comment"}

newline = {"Single-Line Comment"}


class LexerError(Exception):
    pass

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokenList: List[Token] = []

        self.startIndex = 0
        self.currentIndex = 0

        self.line = 1
        self.column = 1

        self.errors: list[dict] = []

        self.tokenStartLine = 1
        self.tokenStartColumn = 1

        self.errorStartLine = None
        self.errorStartColumn = None

        # Pending token (for delimiter errors)
        self.pendingToken = None

        self.idCounter = 0
        self.idMap = {}


    def getIdTokenType(self, lexeme: str) -> str:
        if lexeme not in self.idMap:
            self.idCounter += 1
            self.idMap[lexeme] = f"id{self.idCounter}"
        return self.idMap[lexeme]

    def scanTokens(self) -> List[Token]:
        while not self.isAtEnd():
            self.startIndex = self.currentIndex
            self.tokenStartLine = self.line
            self.tokenStartColumn = self.column
            self.errorStartLine = None
            self.errorStartColumn = None

            try:
                self.scanToken()
            except LexerError as e:
                start_line = self.tokenStartLine
                start_col  = self.tokenStartColumn

                # Base length = chars consumed for this token
                lexeme_len = max(1, self.currentIndex - self.startIndex)

                # Some errors (like invalid delimiters) explicitly set an error start
                if self.errorStartLine is not None:
                    start_line = self.errorStartLine
                    start_col  = self.errorStartColumn
                    lexeme_len = 1

                end_line = start_line
                end_col  = start_col + lexeme_len

                self.errors.append({
                    "message": str(e),
                    "line": start_line,
                    "col": start_col,
                    "start_line": start_line,
                    "start_col": start_col,
                    "end_line": end_line,
                    "end_col": end_col,
                })

                # If a token was pending when the error occurred (e.g., delimiter error),
                # still add it to the token list so it appears in the Tokens panel.
                if self.pendingToken is not None:
                    self.tokenList.append(self.pendingToken)
                    self.pendingToken = None

        # EOF token
        eof_token = Token("$", "EOF", self.line, self.column)
        self.tokenList.append(eof_token)

        return self.tokenList


    def isAtEnd(self) -> bool:
        return self.currentIndex >= len(self.source)

    def advanceChar(self) -> str:
        ch = self.source[self.currentIndex]
        self.currentIndex += 1

        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return ch

    def peekChar(self) -> str:
        if self.isAtEnd():
            return '\0'
        return self.source[self.currentIndex]

    def peekNextChar(self) -> str:
        if self.currentIndex + 1 >= len(self.source):
            return '\0'
        return self.source[self.currentIndex + 1]

    def matchChar(self, expected: str) -> bool:
        if self.isAtEnd():
            return False
        if self.source[self.currentIndex] != expected:
            return False
        self.currentIndex += 1
        self.column += 1
        return True

    def addToken(self, tokenType: str, lexeme: str | None = None):
            if lexeme is None:
                lexeme = self.source[self.startIndex:self.currentIndex]

            line = self.tokenStartLine
            col = self.tokenStartColumn

            # Store as pending in case delimiter validation fails
            self.pendingToken = Token(tokenType, lexeme, line, col)

            # This may raise a LexerError (e.g., invalid delimiter)
            self.checkDelimiter(tokenType)

            # If we reach here, delimiter is valid -> finalize the token
            self.tokenList.append(self.pendingToken)
            self.pendingToken = None


    def scanToken(self):
        ch = self.advanceChar()

        # 1. Whitespace
        if ch == ' ':
            self.addToken("space", " ")
            return
        if ch == '\t':
            self.addToken("tab", "\t")
            return
        if ch == '\n':
            self.tokenList.append(Token("newline", "\n", self.line - 1, 1))
            return

        # 2. Multi-character operators and '&' symbol
        if ch == '+':
            if self.matchChar('+'):
                self.addToken("++")
            elif self.matchChar('='):
                self.addToken("+=")
            else:
                self.addToken("+")
            return

        if ch == '-':
            # --, -=, negative numbers, or '-'
            if self.matchChar('-'):
                self.addToken("--")
            elif self.matchChar('='):
                self.addToken("-=")
            elif self.peekChar().isdigit():
                # Negative number literal (tile or glass)
                self.scanNumberLiteral(isNegative=True)
            else:
                self.addToken("-")
            return

        if ch == '*':
            if self.matchChar('='):
                self.addToken("*=")
            else:
                self.addToken("*")
            return

        if ch == '%':
            if self.matchChar('='):
                self.addToken("%=")
            else:
                self.addToken("%")
            return

        if ch == '=':
            if self.matchChar('='):
                self.addToken("==")
            else:
                self.addToken("=")
            return

        if ch == '!':
            if self.matchChar('='):
                self.addToken("!=")
            else:
                self.addToken("!")
            return

        if ch == '<':
            if self.matchChar('='):
                self.addToken("<=")
            else:
                self.addToken("<")
            return

        if ch == '>':
            if self.matchChar('='):
                self.addToken(">=")
            else:
                self.addToken(">")
            return

        if ch == '&':
            if self.matchChar('&'):
                self.addToken("&&")
            else:
                self.addToken("&")
            return

        if ch == '|':
            if self.matchChar('|'):
                self.addToken("||")
            else:
                raise LexerError(f"Unexpected '|' at {self.line}:{self.column}")
            return

        # 3. Divide, comments, or "/="
        if ch == '/':
            if self.matchChar('/'):
                self.scanSingleLineComment()
            elif self.matchChar('*'):
                self.scanMultiLineComment()
            elif self.matchChar('='):
                self.addToken("/=")
            else:
                self.addToken("/")
            return

        # 4. Dot handling
        if ch == '.':
            # dot MUST be followed by identifier start
            next_ch = self.peekChar()
            
            if not isAlphaIdChar(next_ch):
                raise LexerError(
                    f"Invalid structure access '.' at {self.line}:{self.column}. "
                    f"Expected identifier after '.'"
                )
            
            if not self.tokenList or not self.tokenList[-1].tokenType.startswith("id"):
                raise LexerError(
                    f"'.' can only appear after an identifier (line {self.line})"
                )
            
            self.addToken(".")
            return


        # 4. Simple one-char symbols
        if ch in "{}()[]:;,.":
            self.addToken(ch)
            return

        if ch == '"':
            self.scanWallLiteral()
            return

        # 5. Brick literal
        if ch == "'":
            self.scanBrickLiteral()
            return

        # 6. Number literal: tile_lit or glass_lit
        if ch.isdigit():
            self.scanNumberLiteral(isNegative=False)
            return

        # 7. Identifier or keyword (ASCII letter or underscore)
        if isAlphaIdChar(ch):
            self.scanIdentifier()
            return

        # 8. Anything else = error
        raise LexerError(f"Unexpected character {ch!r} at {self.line}:{self.column}")

    def scanSingleLineComment(self):
        while not self.isAtEnd() and self.peekChar() != '\n':
            self.advanceChar()
        lexeme = self.source[self.startIndex:self.currentIndex]
        self.addToken("Single-Line Comment", lexeme)

    def scanMultiLineComment(self):
        # NOTES
        # Multi-line comment rules:
        # - Starts with /* and ends with */
        # - Can span multiple lines.
        # - Cannot be nested.
        # - If never closed, everything until EOF is treated as comment.

        while not self.isAtEnd():
            if self.peekChar() == '*' and self.peekNextChar() == '/':
                self.advanceChar()
                self.advanceChar()  
                break
            else:
                self.advanceChar()

        lexeme = self.source[self.startIndex:self.currentIndex]
        self.addToken("Multi-Line Comment", lexeme)


    def scanWallLiteral(self):
        
        # wall literal rules:
        # - Written inside double quotes: "..."
        # - Can be empty: ""
        # - Accept any printable ASCII characters
        # - Valid escapes: \n, \t, \\, \', \", \0
        # - A single backslash '\' is not allowed.
        # - '//' or '/*' inside a wall are just text, not comments.

        while not self.isAtEnd():
            ch = self.advanceChar()

            if ch == '"':
                lexeme = self.source[self.startIndex:self.currentIndex]
                self.addToken("wall_lit", lexeme)
                return

            if ch == '\n':
                raise LexerError(f"Unterminated wall literal: missing closing '\"' before end of line {self.line - 1}")

            if ch == '\\':
                if self.isAtEnd():
                    raise LexerError(f"Incomplete escape at end of wall literal (line {self.line})")

                esc = self.advanceChar()
                validEscapes = {'n', 't', '\\', '\'', '"', '0'}
                if esc not in validEscapes:
                    raise LexerError(f"Invalid escape '\\{esc}' in wall literal at line {self.line}")
                continue

            # Any other character must be printable ASCII 32–126
            if not isAscii3(ch):
                raise LexerError(
                    f"wall literal must contain printable ASCII characters (got {ch!r}) at line {self.line}"
                )

        raise LexerError(f"Unterminated wall literal starting at line {self.line}")


    def scanNumberLiteral(self, isNegative: bool = False):
        # TILE (integer):
        # - Optional single leading '-' (handled by caller, isNegative=True).
        # - Digits only (0–9).
        # - No '.' → tile_lit.
        # - Leading zeros allowed.
        # - No letters/special chars inside the same lexeme.

        # GLASS (floating):
        # - Optional single leading '-' (isNegative=True).
        # - At least one digit before '.'.
        # - Exactly one '.'.
        # - At least one digit after '.'.
        # - No letters/special chars inside the same lexeme.
        # - No scientific notation.

        # Range
        # - tile: up to 15 digits in the integer magnitude.
        # - glass: up to 15 digits in integer part, 7 in fractional part.

        # Read integer part digits
        while self.peekChar().isdigit():
            self.advanceChar()

        isGlass = False

        # Check for decimal point (glass literal)
        if self.peekChar() == '.':
            isGlass = True
            self.advanceChar()

            # at least one digit after '.'
            if not self.peekChar().isdigit():
                raise LexerError(f"glass literal must have digits after '.' at line {self.line}")

            while self.peekChar().isdigit():
                self.advanceChar()

            # two or more decimal points are not allowed"
            if self.peekChar() == '.':
                raise LexerError(f"glass literal cannot contain more than one '.' at line {self.line}")

        lexeme = self.source[self.startIndex:self.currentIndex]

        if isGlass:
            # GLASS RULES: max 15 digits integer, 7 digits fractional

            # Remove sign
            body = lexeme[1:] if lexeme.startswith('-') else lexeme
            intPart, fracPart = body.split('.')

            # Ignore leading zeros in integer, trailing zeros in fractional
            intDigits = intPart.lstrip('0')
            fracDigits = fracPart.rstrip('0')

            # Special case: all zeros treat as "0" / "0.0" logically
            if intDigits == '':
                intDigits = '0'
            if fracDigits == '':
                fracDigits = '0'

            # LENGTH OF DIGITS CHANGE INTO VARIABLE FOR EASIER CHANGING - PLACEHOLDER |APPLE|
            if len(intDigits) > 15:
                raise LexerError(
                    f"glass literal integer part exceeds 15 digits at line {self.line}"
                )

            if len(fracDigits) > 7:
                raise LexerError(
                    f"glass literal fractional part exceeds 7 digits at line {self.line}"
                )

            tokenType = "glass_lit"

        else:
            # TILE RULES: no '.', integer only, up to 15 digits in magnitude
            body = lexeme[1:] if lexeme.startswith('-') else lexeme

            # Ignore leading zeros for magnitude counting
            magDigits = body.lstrip('0')
            if magDigits == '':
                magDigits = '0'

            if len(magDigits) > 15:
                raise LexerError(
                    f"tile literal exceeds 15 digits at line {self.line}"
                )

            tokenType = "tile_lit"

        self.addToken(tokenType, lexeme)


    def scanBrickLiteral(self):

        # brick literal rules:
        # - Written inside single quotes: 'x'
        # - Exactly one character OR one valid escape sequence.
        # - No empty character: '' is invalid.
        # - Valid escapes: \n, \t, \\, \', \", \0
        # - Whitespace counts as a valid character.

        if self.isAtEnd():
            raise LexerError(f"Unterminated brick literal at line {self.line}")

        ch = self.advanceChar()

        # Empty character: '' not allowed
        if ch == "'":
            raise LexerError(f"Empty brick literal is not allowed at line {self.line}")

        if not isAscii3(ch):
            raise LexerError(f"brick literal must be printable ASCII (got {ch!r}) at line {self.line}")


        # Escape sequence
        if ch == '\\':
            if self.isAtEnd():
                raise LexerError(f"Incomplete escape in brick literal at line {self.line}")

            esc = self.advanceChar()
            validEscapes = {'n', 't', '\\', '\'', '"', '0'}
            if esc not in validEscapes:
                raise LexerError(f"Invalid escape '\\{esc}' in brick literal at line {self.line}")

            if not self.matchChar("'"):
                raise LexerError(f"brick literal must contain exactly one escape sequence at line {self.line}")
        else:
            # Normal character case: must be exactly one char, then closing quote
            if ch == '\n':
                raise LexerError(f"brick literal cannot contain newline at line {self.line}")

            # printable ASCII only (codes 32–126)
            if not isAscii3(ch):
                raise LexerError(
                    f"brick literal must be a printable ASCII character (got {ch!r}) at line {self.line}"
                )

            if not self.matchChar("'"):
                raise LexerError(f"brick literal must contain exactly one character at line {self.line}")


        lexeme = self.source[self.startIndex:self.currentIndex]
        self.addToken("brick_lit", lexeme)


    def scanIdentifier(self):
        # First char consumed and is ASCII letter or '_'
        while isAlphaNumChar(self.peekChar()) or self.peekChar() == '_':
            self.advanceChar()

        lexeme = self.source[self.startIndex:self.currentIndex]

        # IDENTIFIER LENGTH PLACEHOLDER |Bravo|
        # Max length 20
        if len(lexeme) > 20:
            raise LexerError(
                f"Identifier '{lexeme}' exceeds maximum length (20 chars) at line {self.line}"
            )

        # Keywords vs identifiers
        if lexeme in KEYWORDS:
            self.addToken(lexeme, lexeme)
        else:
            tokenType = self.getIdTokenType(lexeme)
            self.addToken(tokenType, lexeme)


    def checkDelimiter(self, tokenType: str):

        # After reading a token, ensure the next character belongs
        # to the correct delimiter set for that tokenType.

        ch = self.peekChar()

        if ch == '\0':
            return

        # ------------- category "whitespace" -------------
        if tokenType in whitespace:
            if not isWhitespaceChar(ch):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' at line {self.line}"
                )
            return

        # ------------- category "alpha_id" (&, .) -------------
        if tokenType in alpha_id:
            if not isAlphaIdChar(ch):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' at line {self.line}. "
                    "Expected an identifier start (letter or underscore)."
                )
            return

        # ------------- newline for single-line comment -------------
        if tokenType in newline:
            # newline or EOF
            if ch != '\n' and ch != '\0':
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Single-line comment must end at newline (found '{ch}') at line {self.line}"
                )
            return

        # ------------- delim1: ( , whitespace -------------
        if tokenType in delim1:
            if not (ch == '(' or isWhitespaceChar(ch)):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (expected '(' or whitespace) at line {self.line}"
                )
            return

        # ------------- delim2: ; , whitespace -------------
        if tokenType in delim2:
            if not (ch == ';' or isWhitespaceChar(ch)):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (expected ';' or whitespace) at line {self.line}"
                )
            return

        # ------------- delim3: { , whitespace -------------
        if tokenType in delim3:
            if not (ch == '{' or isWhitespaceChar(ch)):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (expected '{{' or whitespace) at line {self.line}"
                )
            return

        # ------------- delim4: operators , } , ) , ] , : , ; , , , whitespace -------------
        if tokenType in delim4:
            if not (
                isOperatorChar(ch) or
                ch in {'}', ')', ']', ':', ';', ','} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (delim4) at line {self.line}"
                )
            return

        # ------------- delim5: : , whitespace -------------
        if tokenType in delim5:
            if not (ch == ':' or isWhitespaceChar(ch)):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (expected ':' or whitespace) at line {self.line}"
                )
            return

        # ------------- delim6: alpha_num , + , - , ! , { , ( , ' , " , whitespace -------------
        if tokenType in delim6:
            if not (
                isAlphaNumChar(ch) or
                ch in {'+', '-', '!', '{', '(', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '=' (delim6) at line {self.line}"
                )
            return

        # ------------- delim7: alpha_num , + , - , ! , ( , ' , " , whitespace -------------
        if tokenType in delim7:
            if not (
                isAlphaNumChar(ch) or
                ch in {'+', '-', '!', '(', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (delim7) at line {self.line}"
                )
            return

        # ------------- delim8: alpha_num , - , ! , ( , ' , " , whitespace -------------
        if tokenType in delim8:
            if not (
                isAlphaNumChar(ch) or
                ch in {'-', '!', '(', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '+' (delim8) at line {self.line}"
                )
            return

        # ------------- delim9: alpha_id , ) , ] , , , ; , whitespace -------------
        if tokenType in delim9:
            if not (
                isAlphaIdChar(ch) or
                ch in {')', ']', ',', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (delim9) at line {self.line}"
                )
            return

        # ------------- delim10: alpha_num , + , - , ! , ' , whitespace -------------
        if tokenType in delim10:
            if not (
                isAlphaNumChar(ch) or
                ch in {'+', '-', '!', '\'', '(',} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (delim10) at line {self.line}"
                )
            return

        # ------------- delim11: alpha_id , + , ! , ( , ' , whitespace -------------
        if tokenType in delim11:
            if not (
                isAlphaIdChar(ch) or
                ch in {'+', '!', '(', '\'',} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '-' (delim11) at line {self.line}"
                )
            return

        # ------------- delim12: alpha_num , - , { , ' , " , whitespace -------------
        if tokenType in delim12:
            if not (
                isAlphaNumChar(ch) or
                ch in {'-', '{', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '{tokenType}' (delim12) at line {self.line}"
                )
            return

        # ------------- delim13: alpha_id , } , ; , , , whitespace -------------
        if tokenType in delim13:
            if not (
                isAlphaIdChar(ch) or
                ch in {'}', ';', ','} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '}}' (delim13) at line {self.line}"
                )
            return

        # ------------- delim14: alpha_num , - , + , ! , ( , ) , ' , " , whitespace -------------
        if tokenType in delim14:
            if not (
                isAlphaNumChar(ch) or
                ch in {'-', '+', '!', '(', ')', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '(' (delim14) at line {self.line}"
                )
            return

        # ------------- delim15: operators , { , ) , ] , ; , whitespace -------------
        if tokenType in delim15:
            if not (
                isOperatorChar(ch) or
                ch in {'{', ')', ']', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after ')' (delim15) at line {self.line}"
                )
            return

        # ------------- delim16: alpha_num , + , - , ! , ( , ] , ' , whitespace -------------
        if tokenType in delim16:
            if not (
                isAlphaNumChar(ch) or
                ch in {'+', '-', '!', '(', ']', '\'',} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after '[' (delim16) at line {self.line}"
                )
            return

        # ------------- delim17: operators , ) , [ , ; , whitespace -------------
        if tokenType in delim17:
            if not (
                isOperatorChar(ch) or
                ch in {')', '[', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after ']' (delim17) at line {self.line}"
                )
            return

        # ------------- delim18: alpha_num , - , & , ' , " , whitespace -------------
        if tokenType in delim18:
            if not (
                isAlphaNumChar(ch) or
                ch in {'-', '&', '\'', '"'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after ',' (delim18) at line {self.line}"
                )
            return

        # ------------- delim19: alpha_num , + , - , whitespace -------------
        if tokenType in delim19:
            if not (
                isAlphaNumChar(ch) or
                ch in {'+', '-'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after ';' (delim19) at line {self.line}"
                )
            return

        # ------------- delim20: operators , ( , ) , [ , ] , . , , , ; , whitespace -------------
        if tokenType in delim20:
            if not (
                isOperatorChar(ch) or
                ch in {'(', ')', '[', ']', '.', ',', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after identifier (delim20) at line {self.line}"
                )
            return

        # ------------- delim21: operators , ) , ] , } , , , : , ; , whitespace -------------
        if tokenType in delim21:
            if not (
                isOperatorChar(ch) or
                ch in {')', ']', '}', ',', ':', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after tile_lit (delim21) at line {self.line}"
                )
            return

        # ------------- delim22: operators , ) , ] , } , , , ; , whitespace -------------
        if tokenType in delim22:
            if not (
                isOperatorChar(ch) or
                ch in {')', ']', '}', ',', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after glass_lit (delim22) at line {self.line}"
                )
            return

        # ------------- delim23: operators , ) , ] , } , , , : , ; , whitespace -------------
        if tokenType in delim23:
            if not (
                isOperatorChar(ch) or
                ch in {')', ']', '}', ',', ':', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after brick_lit (delim23) at line {self.line}"
                )
            return

        # ------------- delim24: + , > , < , = , ! , & , | , ) , , , ; , whitespace -------------
        if tokenType in delim24:
            if not (
                ch in {'+', '>', '<', '=', '!', '&', '|', ')', ',', ';'} or
                isWhitespaceChar(ch)
            ):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column 
                raise LexerError(
                    f"Invalid delimiter '{ch}' after wall_lit (delim24) at line {self.line}"
                )
            return

        # ------------- delim25: ascii3 , whitespace (multi-line comment) -------------
        if tokenType in delim25:
            if not (isAscii3(ch) or isWhitespaceChar(ch)):
                self.errorStartLine = self.line
                self.errorStartColumn = self.column
                raise LexerError(
                    f"Invalid delimiter '{ch}' after multi-line comment (delim25) at line {self.line}"
                )
            return

        return
