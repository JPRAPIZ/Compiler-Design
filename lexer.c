    #include <stdio.h>
    #include <stdlib.h>
    #include <ctype.h>
    #include <string.h>
    #include "tokens.h"

    typedef struct {
        TOKEN_TYPE type;
        char lexeme[15];
        int line;
    }Token;

typedef struct {
    const char* src;
    size_t pos;
    int line;
} Lexer;

// Helper to peek at the next character without advancing
char peek(Lexer* lexer) {
    if (lexer->src[lexer->pos] == '\0') return '\0';
    return lexer->src[lexer->pos + 1];
}

// Helper to advance the position and return the consumed character
char advance(Lexer* lexer) {
    return lexer->src[lexer->pos++];
}

// Skips whitespace and all comments
void skip_whitespace_and_comments(Lexer* lexer) {
    while (1) {
        char c = lexer->src[lexer->pos];
        switch (c) {
            case ' ':
            case '\r':
            case '\t':
                lexer->pos++;
                break;
            case '\n':
                lexer->line++;
                lexer->pos++;
                break;
            case '/':
                if (peek(lexer) == '/') { // Single-line comment
                    while (lexer->src[lexer->pos] != '\n' && lexer->src[lexer->pos] != '\0') {
                        lexer->pos++;
                    }
                } else if (peek(lexer) == '*') { // Multi-line comment
                    lexer->pos += 2; // Skip '/*'
                    while (!(lexer->src[lexer->pos] == '*' && peek(lexer) == '/') && lexer->src[lexer->pos] != '\0') {
                        if (lexer->src[lexer->pos] == '\n') lexer->line++;
                        lexer->pos++;
                    }
                    if (lexer->src[lexer->pos] != '\0') {
                        lexer->pos += 2; // Skip '*/'
                    }
                } else {
                    return; // It's a division operator, not a comment
                }
                break;
            default:
                return; // Not whitespace or a comment, so we stop
        }
    }
}

// Checks if a string is a keyword and returns the correct token type
TOKEN_TYPE keyword_type(const char* str) {
    if (!strcmp(str, "tile")) return TOK_TILE;
    if (!strcmp(str, "glass")) return TOK_GLASS;
    if (!strcmp(str, "brick")) return TOK_BRICK;
    if (!strcmp(str, "beam")) return TOK_BEAM;
    if (!strcmp(str, "space")) return TOK_SPACE;
    if (!strcmp(str, "wall")) return TOK_WALL;
    if (!strcmp(str, "house")) return TOK_HOUSE;
    if (!strcmp(str, "if")) return TOK_IF;
    if (!strcmp(str, "else")) return TOK_ELSE;
    if (!strcmp(str, "room")) return TOK_ROOM;
    if (!strcmp(str, "door")) return TOK_DOOR;
    if (!strcmp(str, "ground")) return TOK_GROUND;
    if (!strcmp(str, "for")) return TOK_FOR;
    if (!strcmp(str, "while")) return TOK_WHILE;
    if (!strcmp(str, "do")) return TOK_DO;
    if (!strcmp(str, "crack")) return TOK_CRACK;
    if (!strcmp(str, "blueprint")) return TOK_BLUEPRINT;
    if (!strcmp(str, "view")) return TOK_VIEW;
    if (!strcmp(str, "write")) return TOK_WRITE;
    if (!strcmp(str, "home")) return TOK_HOME;
    if (!strcmp(str, "solid")) return TOK_SOLID;
    if (!strcmp(str, "fragile")) return TOK_FRAGILE;
    if (!strcmp(str, "cement")) return TOK_CEMENT;
    if (!strcmp(str, "roof")) return TOK_ROOF;

    return IDENTIFIER;
}

// Helper function to create a token
Token make_token(Lexer* lexer, TOKEN_TYPE type, const char* lexeme) {
    Token token;
    token.type = type;
    token.line = lexer->line;
    strncpy(token.lexeme, lexeme, sizeof(token.lexeme) - 1);
    token.lexeme[sizeof(token.lexeme) - 1] = '\0';
    return token;
}

// The main lexer function that returns the next token
Token next_token(Lexer* lexer) {
    skip_whitespace_and_comments(lexer);

    char c = lexer->src[lexer->pos];
    size_t start = lexer->pos;

    // End of file
    if (c == '\0') {
        return make_token(lexer, TOK_EOF, "EOF");
    }

    // Identifiers and Keywords
    if (isalpha(c) || c == '_') {
        while (isalnum(lexer->src[lexer->pos]) || lexer->src[lexer->pos] == '_') {
            lexer->pos++;
        }
        size_t len = lexer->pos - start;
        char lexeme[len + 1];
        strncpy(lexeme, lexer->src + start, len);
        lexeme[len] = '\0';
        return make_token(lexer, keyword_type(lexeme), lexeme);
    }

    // Numbers (Integer literals)
    if (isdigit(c)) {
        while (isdigit(lexer->src[lexer->pos])) {
            lexer->pos++;
        }
        size_t len = lexer->pos - start;
        char lexeme[len + 1];
        strncpy(lexeme, lexer->src + start, len);
        lexeme[len] = '\0';
        return make_token(lexer, NUMBER, lexeme);
    }

    // --- NEW: ALL OPERATORS AND SYMBOLS ---
    advance(lexer); // Consume the current character
    switch (c) {
        // Single characters
        case '(': return make_token(lexer, TOK_OP_PARENTHESES, "(");
        case ')': return make_token(lexer, TOK_CL_PARENTHESES, ")");
        case '{': return make_token(lexer, TOK_OP_BRACE, "{");
        case '}': return make_token(lexer, TOK_CL_BRACE, "}");
        case '[': return make_token(lexer, TOK_OP_BRACKET, "[");
        case ']': return make_token(lexer, TOK_CL_BRACKET, "]");
        case ';': return make_token(lexer, TOK_SEMICOLON, ";");
        case ':': return make_token(lexer, TOK_COLON, ":");
        case ',': return make_token(lexer, TOK_COMMA, ",");
        case '.': return make_token(lexer, TOK_PERIOD, ".");
        case '%': return make_token(lexer, TOK_MODULO, "%");
        case '\'': return make_token(lexer, TOK_SNGL_QUOTE, "'");
        case '"': return make_token(lexer, TOK_DBL_QUOTE, "\"");

        // Single or double characters
        case '!': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_NOT_EQUAL, "!=")) : make_token(lexer, TOK_NOT, "!");
        case '=': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_EQUALS, "==")) : make_token(lexer, TOK_ASSIGN, "=");
        case '+': return peek(lexer) == '+' ? (advance(lexer), make_token(lexer, TOK_INCREMENT, "++")) : (peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_ADD_ASSIGN, "+=")) : make_token(lexer, TOK_PLUS, "+"));
        case '-': return peek(lexer) == '-' ? (advance(lexer), make_token(lexer, TOK_DECREMENT, "--")) : (peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_SUB_ASSIGN, "-=")) : make_token(lexer, TOK_MINUS, "-"));
        case '*': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_MUL_ASSIGN, "*=")) : make_token(lexer, TOK_MULTIPLY, "*");
        case '/': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_DIV_ASSIGN, "/=")) : make_token(lexer, TOK_DIVIDE, "/");
        case '<': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_LT_EQUAL, "<=")) : make_token(lexer, TOK_LESS_THAN, "<");
        case '>': return peek(lexer) == '=' ? (advance(lexer), make_token(lexer, TOK_GT_EQUAL, ">=")) : make_token(lexer, TOK_GREATER_THAN, ">");
        
        // Logical operators
        case '&': return peek(lexer) == '&' ? (advance(lexer), make_token(lexer, TOK_AND, "&&")) : make_token(lexer, TOK_AMPERSAND, "&");
        case '|': return peek(lexer) == '|' ? (advance(lexer), make_token(lexer, TOK_OR, "||")) : make_token(lexer, TOK_UNKNOWN, "|");
    }

    // If no match is found
    char unknown[2] = {c, '\0'};
    return make_token(lexer, TOK_UNKNOWN, unknown);
}


// A helper to print token types cleanly
const char* token_type_to_string(TOKEN_TYPE type) {
    // This function can be expanded to include all token types for nice printing
    switch (type) {
        case TOK_PLUS: return "TOK_PLUS";
        case TOK_MINUS: return "TOK_MINUS";
        case TOK_MULTIPLY: return "TOK_MULTIPLY";
        case TOK_DIVIDE: return "TOK_DIVIDE";
        case TOK_MODULO: return "TOK_MODULO";
        case TOK_INCREMENT: return "TOK_INCREMENT";
        case TOK_DECREMENT: return "TOK_DECREMENT";
        case TOK_ASSIGN: return "TOK_ASSIGN";
        case TOK_ADD_ASSIGN: return "TOK_ADD_ASSIGN";
        case TOK_SUB_ASSIGN: return "TOK_SUB_ASSIGN";
        case TOK_MUL_ASSIGN: return "TOK_MUL_ASSIGN";
        case TOK_DIV_ASSIGN: return "TOK_DIV_ASSIGN";
        case TOK_GREATER_THAN: return "TOK_GREATER_THAN";
        case TOK_LESS_THAN: return "TOK_LESS_THAN";
        case TOK_EQUALS: return "TOK_EQUALS";
        case TOK_NOT_EQUAL: return "TOK_NOT_EQUAL";
        case TOK_GT_EQUAL: return "TOK_GT_EQUAL";
        case TOK_LT_EQUAL: return "TOK_LT_EQUAL";
        case TOK_AND: return "TOK_AND";
        case TOK_OR: return "TOK_OR";
        case TOK_NOT: return "TOK_NOT";
        case TOK_TILE: return "TOK_TILE";
        case TOK_GLASS: return "TOK_GLASS";
        case TOK_BRICK: return "TOK_BRICK";
        case TOK_BEAM: return "TOK_BEAM";
        case IDENTIFIER: return "IDENTIFIER";
        case NUMBER: return "NUMBER";
        case TOK_IF: return "TOK_IF";
        case TOK_SEMICOLON: return "TOK_SEMICOLON";
        case TOK_OP_BRACE: return "TOK_OP_BRACE";
        case TOK_CL_BRACE: return "TOK_CL_BRACE";
        case TOK_OP_PARENTHESES: return "TOK_OP_PARENTHESES";
        case TOK_CL_PARENTHESES: return "TOK_CL_PARENTHESES";
        case TOK_EOF: return "TOK_EOF";
        default: return "TOK_UNKNOWN";
    }
}

    int main() {
        // Test input
        const char* input = "beam num = 50 + 20;";
        Lexer lexer = {input, 0, 1}; // Initialize lexer, starting at line 1
    Token token;

    printf("--- Lexing Input ---\n%s\n--------------------\n", input);
    do {
        token = next_token(&lexer);
        printf("Type: %-20s Lexeme: '%s'\t(Line: %d)\n",
            token_type_to_string(token.type),
            token.lexeme,
            token.line
        );
    } while (token.type != TOK_EOF);

    return 0;
}