#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>
#include "tokens.h"

typedef struct {
    TOKEN_TYPE type;
    char lexeme[20];
    int line;
}Token;

typedef struct {
    const char* src;
    size_t pos;
}Lexer;

void skip_whitespace(Lexer* lexer) {
    while (isspace(lexer->src[lexer->pos])) {
        lexer->pos++;
    }
}

int is_keyword(const char* str) {
    return strcmp(str, "tile") == 0; // only 'int' is a keyword for now
}

Token next_token(Lexer* lexer) {
    skip_whitespace(lexer);

    Token token = {TOK_unknown, ""};
    char c = lexer->src[lexer->pos];

    // End of input
    if (c == '\0') {
        token.type = TOK_eof;
        return token;
    }

    // Identifiers and Keywords
    if (isalpha(c) || c == '_') {
        size_t start = lexer->pos;
        while (isalnum(lexer->src[lexer->pos]) || lexer->src[lexer->pos] == '_') {
            lexer->pos++;
        }
        size_t len = lexer->pos - start;
        strncpy(token.lexeme, lexer->src + start, len);
        token.lexeme[len] = '\0';

        if (is_keyword(token.lexeme)) {
            token.type = TOK_tile;
        } else {
            token.type = IDENTIFIER;
        }
        return token;
    }

    // Numbers
    if (isdigit(c)) {
        size_t start = lexer->pos;
        while (isdigit(lexer->src[lexer->pos])) {
            lexer->pos++;
        }
        size_t len = lexer->pos - start;
        strncpy(token.lexeme, lexer->src + start, len);
        token.lexeme[len] = '\0';
        token.type = NUMBER;
        return token;
    }

    // Single-character tokens
    lexer->pos++;
    switch (c) {
        case '=':
            token.type = TOK_assign;
            strcpy(token.lexeme, "=");
            break;
        case '+':
            token.type = TOK_plus;
            strcpy(token.lexeme, "+");
            break;
        case ';':
            token.type = TOK_semicolon;
            strcpy(token.lexeme, ";");
            break;
        default:
            token.type = TOK_unknown;
            snprintf(token.lexeme, sizeof(token.lexeme), "%c", c);
    }
    return token;
}

int main() {
    // Test input
    const char* input = "tile num = 50 + 20;";
    Lexer lexer = {input, 0};
    Token token;

    printf("Lexing: %s\n", input);
    do {
        token = next_token(&lexer);
        printf("Token: %-15s Lexeme: %s\n",
            (token.type == TOK_tile) ? "TOK_tile" :
            (token.type == IDENTIFIER) ? "IDENTIFIER" :
            (token.type == NUMBER) ? "NUMBER" :
            (token.type == TOK_assign) ? "TOK_assign" :
            (token.type == TOK_plus) ? "TOK_plus" :
            (token.type == TOK_semicolon) ? "TOK_semicolon" :
            (token.type == TOK_eof) ? "TOK_eof" :
            "TOKEN_UNKNOWN",
            token.lexeme
        );
    } while (token.type != TOK_eof);

    return 0;
}