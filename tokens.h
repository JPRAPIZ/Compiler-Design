typedef enum TOKEN_TYPE{
    // Simple Operators
    TOK_plus,
    TOK_assign, //equals =

    // Data Types
    TOK_tile, //int

    // Literals
    IDENTIFIER,
    NUMBER, // int

    // Semi Colon
    TOK_semicolon,

    // End of File
    TOK_eof,

    TOK_unknown

}TOKEN_TYPE;