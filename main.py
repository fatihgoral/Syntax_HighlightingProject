import tkinter as tk
import re

THEME = {
    "bg": "#1e1e1e",
    "line_bg": "#2e2e2e",
    "keyword": "#a020f0",
    "identifier": "#ffff66",
    "number": "#00cc66",
    "string": "#d69d85",
    "comment": "#6a9955",
    "preprocessor": "#ff8800",
    "operator": "#d4d4d4",
    "punctuation": "#ffffff",
    "stdfunc": "#ffff66",
    "valid_syntax": "#00ff00",
    "invalid_syntax": "#ff0000"
}

C_KEYWORDS = [
    'int', 'char', 'float', 'double', 'void', 'if', 'else', 'for', 'while',
    'do', 'return', 'break', 'continue', 'switch', 'case', 'default',
    'struct', 'union', 'enum', 'typedef', 'const', 'sizeof', 'static',
    'extern', 'goto'
]

C_STD_FUNCTIONS = ['printf', 'scanf', 'puts']

TOKEN_PATTERNS = [
    ('comment', r'/\*[\s\S]*?\*/|//.*'),
    ('preprocessor', r'#\s*include\s*<[^>]+>'),
    ('string', r'"([^"\\]|\\.)*"'),
    ('number', r'\b\d+(\.\d+)?\b'),
    ('keyword', r'\b(?:' + '|'.join(C_KEYWORDS) + r')\b'),
    ('stdfunc', r'\b(?:' + '|'.join(C_STD_FUNCTIONS) + r')\b'),
    ('operator', r'[+\-*/=<>!&|]+'),
    ('identifier', r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('punctuation', r'[;{}()]'),
    ('invalid_syntax', r'[^\s]')  # sadece geçersiz karakterler
]

root = tk.Tk()
root.title("C Syntax Highlighter")
root.geometry("920x580")

frame = tk.Frame(root)
frame.pack(fill="both", expand=True)

scrollbar = tk.Scrollbar(frame)
scrollbar.pack(side="right", fill="y")

line_numbers = tk.Text(frame, width=4, padx=6, pady=4, spacing1=4, takefocus=0, border=0,
                       background=THEME["line_bg"], foreground="#aaaaaa", wrap="none",
                       font=("Courier New", 13))
line_numbers.pack(side="left", fill="y")

text = tk.Text(frame, wrap="none", undo=True, font=("Courier New", 13),
               background=THEME["bg"], foreground="#ffffff", insertbackground="white",
               spacing1=4)
text.pack(side="right", fill="both", expand=True)

def sync_scroll(*args):
    text.yview(*args)
    line_numbers.yview_moveto(text.yview()[0])

text.config(yscrollcommand=sync_scroll)
scrollbar.config(command=text.yview)

for tag, color in THEME.items():
    if tag not in ("bg", "line_bg"):
        text.tag_configure(tag, foreground=color)

for tag in THEME:
    if tag not in ("bg", "line_bg"):
        text.tag_raise(tag)

def tokenize(code):
    tokens = []
    lines = code.splitlines()
    for line_num, line in enumerate(lines):
        pos = 0
        while pos < len(line):
            if line[pos].isspace():
                pos += 1
                continue
            matched = False
            for token_type, pattern in TOKEN_PATTERNS:
                match = re.match(pattern, line[pos:])
                if match:
                    value = match.group()
                    # Sadece invalid_syntax'lar kırmızı olacak şekilde öncelik veriyoruz
                    if token_type == "invalid_syntax":
                        tokens.append(("invalid_syntax", value, line_num, pos))
                    else:
                        tokens.append((token_type, value, line_num, pos))
                    pos += len(value)
                    matched = True
                    break
            if not matched:
                tokens.append(("invalid_syntax", line[pos], line_num, pos))
                pos += 1
    return tokens

def parse(tokens):
    index = 0
    def match(expected_type=None, expected_val=None):
        nonlocal index
        if index >= len(tokens): return False
        typ, val = tokens[index][0], tokens[index][1]
        if (expected_type and typ != expected_type) or (expected_val and val != expected_val):
            return False
        index += 1
        return True

    def mark_tokens(start, end):
        for i in range(start, end):
            line, col = tokens[i][2], tokens[i][3]
            tag_start = f"{line + 1}.{col}"
            tag_end = f"{line + 1}.{col + len(tokens[i][1])}"
            text.tag_add("valid_syntax", tag_start, tag_end)

    def parse_expression():
        nonlocal index
        if index >= len(tokens): return False
        if tokens[index][0] in {'identifier', 'number'}:
            index += 1
            if index < len(tokens) and tokens[index][0] == 'operator':
                index += 1
                if index < len(tokens) and tokens[index][0] in {'identifier', 'number'}:
                    index += 1
                    return True
        return False

    def parse_expr_stmt():
        start = index
        if parse_expression() and match("punctuation", ";"):
            mark_tokens(start, index)
            return True
        index = start
        return False

    def parse_declaration():
        start = index
        if match("keyword") and match("identifier") and match("operator", "=") and \
           (match("number") or match("string") or match("identifier")) and match("punctuation", ";"):
            mark_tokens(start, index)
            return True
        index = start
        return False

    def parse_return():
        start = index
        if match("keyword", "return") and (match("number") or match("identifier") or match("string")) and match("punctuation", ";"):
            mark_tokens(start, index)
            return True
        index = start
        return False

    def parse_if():
        start = index
        if match("keyword", "if") and match("punctuation", "(") and parse_expression() and match("punctuation", ")"):
            if parse_block():
                mark_tokens(start, index)
                return True
        index = start
        return False

    def parse_else():
        start = index
        if match("keyword", "else"):
            if parse_block():
                mark_tokens(start, index)
                return True
        index = start
        return False

    def parse_for():
        start = index
        if match("keyword", "for") and match("punctuation", "("):
            while index < len(tokens) and tokens[index][1] != ")":
                index += 1
            if match("punctuation", ")") and parse_block():
                mark_tokens(start, index)
                return True
        index = start
        return False

    def parse_while():
        start = index
        if match("keyword", "while") and match("punctuation", "(") and parse_expression() and match("punctuation", ")"):
            if parse_block():
                mark_tokens(start, index)
                return True
        index = start
        return False

    def parse_block():
        if not match("punctuation", "{"): return False
        while index < len(tokens) and tokens[index][1] != "}":
            if not (parse_declaration() or parse_expr_stmt() or parse_return() or parse_if() or parse_else() or parse_for() or parse_while()):
                index += 1
        return match("punctuation", "}")

    while index < len(tokens):
        if not (parse_declaration() or parse_expr_stmt() or parse_return() or parse_if() or parse_else() or parse_for() or parse_while()):
            index += 1

def update_line_numbers(event=None):
    lines = text.get("1.0", "end-1c").split("\n")
    nums = "\n".join(str(i+1) for i in range(len(lines)))
    line_numbers.config(state="normal")
    line_numbers.delete("1.0", "end")
    line_numbers.insert("1.0", nums)
    line_numbers.config(state="disabled")

def highlight_and_parse():
    content = text.get("1.0", "end-1c")
    for tag, _ in TOKEN_PATTERNS:
        text.tag_remove(tag, "1.0", "end")
    text.tag_remove("valid_syntax", "1.0", "end")
    text.tag_remove("invalid_syntax", "1.0", "end")

    tokens = tokenize(content)
    for token_type, value, line, col in tokens:
        tag_start = f"{line + 1}.{col}"
        tag_end = f"{line + 1}.{col + len(value)}"
        text.tag_add(token_type, tag_start, tag_end)

    parse(tokens)

def on_key_release(event=None):
    update_line_numbers()
    highlight_and_parse()

text.bind("<KeyRelease>", on_key_release)
text.bind("<MouseWheel>", lambda e: sync_scroll("scroll", int(-1*(e.delta/120)), "units"))
text.bind("<Button-4>", lambda e: sync_scroll("scroll", -1, "units"))
text.bind("<Button-5>", lambda e: sync_scroll("scroll", 1, "units"))

update_line_numbers()
highlight_and_parse()
root.mainloop()
