typedef enum TOKEN_TYPE{
    // Simple Operators
    TOK_PLUS,           // +
    TOK_MINUS,          // - 
    TOK_MULTIPLY,       // *
    TOK_DIVIDE,         // /
    TOK_MODULO,         // %

    TOK_INCREMENT,      // ++
    TOK_DECREMENT,      // --

    TOK_ASSIGN,         // =
    TOK_ADD_ASSIGN,     // +=
    TOK_SUB_ASSIGN,     // -=
    TOK_MUL_ASSIGN,     // *=
    TOK_DIV_ASSIGN,     // /=
    TOK_MOD_ASSIGN,     // %=

    // COMPARISON OPERATORS
    TOK_GREATER_THAN,   // >
    TOK_LESS_THAN,      // <
    TOK_EQUALS,         // ==
    TOK_NOT_EQUAL,      // !=
    TOK_LT_EQUAL,       // >=
    TOK_GT_EQUAL,       // <=

    //LOGICAL OPERATORS
    TOK_AND,            // &&
    TOK_OR,             // ||
    TOK_NOT,            // !


    // Data Types
    TOK_TILE,           // int
    TOK_GLASS,          // float
    TOK_BRICK,          // CHAR
    TOK_BEAM,           // Boolean
    TOK_SPACE,          // VOID
    TOK_WALL,           // STRING
    TOK_HOUSE,          // STRUCT

    // Literals
    IDENTIFIER,         // STRING LIT
    NUMBER,             // int

    // Conditionals
    TOK_IF,             // IF
    TOK_ELSE,           // ELSE
    TOK_ROOM,           // ROOM
    TOK_DOOR,           // DOOR
    TOK_GROUND,         // GROUND

    //LOOPS
    TOK_FOR,            // FOR
    TOK_WHILE,          // WHILE
    TOK_DO,             // DO

    // Others
    TOK_CRACK,          // CRACK
    TOK_BLUEPRINT,      // BLUEPRINT
    TOK_VIEW,           // PRINTF / OUTPUT
    TOK_WRITE,          // SCANF / INPUT
    TOK_HOME,           // RETURN
    TOK_SOLID,          // TRUE
    TOK_FRAGILE,        // FALSE
    TOK_CEMENT,         // CONST
    TOK_ROOF,           // GLOBAL


    // SINGLES
    TOK_SEMICOLON,          // :
    TOK_COLON,              // :
    TOK_COMMA,              // ,
    TOK_PERIOD,             // .
    TOK_AMPERSAND,          // &
    TOK_FRWD_SLASH,         // //COMMENT
    TOK_OP_COMMENT,         // /*
    TOK_CL_COMMENT,         // */
    TOK_OP_BRACE,           // {
    TOK_CL_BRACE,           // }
    TOK_OP_BRACKET,         // [
    TOK_CL_BRACKET,         // ]
    TOK_OP_PARENTHESES,     // (
    TOK_CL_PARENTHESES,     // )
    TOK_SNGL_QUOTE,         // '
    TOK_DBL_QUOTE,          // "
    
    

    // End of File
    TOK_EOF,

    TOK_UNKNOWN

}TOKEN_TYPE;