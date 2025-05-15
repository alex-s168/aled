#!/usr/bin/env python3

import sys
from itertools import chain
import weakref
import sys
import re

buffers = []
config = {
    "tablesep": " ",
    "endline":  "1",
    "echo":     "  ",
}
selection = None

# all line numbers used anywhere are 1-indexed

# if the refd line gets deleted, Marker.line becomes None
# one-indexed
class Marker:
    def __init__(self, line:int):
        assert isinstance(line, int)
        self.line = line

    def __int__(self):
        assert self.line is not None
        return self.line

def boolconf(key:str) -> bool:
    v = config[key].strip().lower()
    if v == "0":
        return False
    if v == "1":
        return True
    if v == "false":
        return False
    if v == "true":
        return True
    if v == "no":
        return False
    if v == "yes":
        return True
    raise ValueError("invalid config value " + v + " for " + key)

class Buffer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.markers = weakref.WeakSet()
        try:
            with open(file_path, "r") as f:
                self.lines = [line.rstrip("\n") for line in f]
        except:
            self.lines = [""]

    # one-indexed
    def marker(self, line:int) -> Marker:
        line = int(line)
        assert line <= len(self.lines)
        m = Marker(line)
        self.markers.add(m)
        return m

    def highl(self, line:str) -> str:
        return line

    def save(self):
        with open(self.file_path, "w") as f:
            f.writelines((l + "\n" for l in self.lines))

    # one-indexed
    def delete(self, line):
        line = int(line)
        for m in self.markers:
            if m.line == line:
                m.line = None
            elif m.line and m.line > line:
                m.line -= 1
        self.lines.pop(line - 1)

    # one-indexed. after can be 0 to insert at beginning
    def insert_many(self, after, text):
        after = int(after)
        ntxt = len(text)
        for m in self.markers:
            if m.line is not None:
                if m.line >= after:
                    m.line += ntxt
        self.lines[after:after] = text


# one-indexed
class Range:
    def __init__(self, first, last, buf):
        first = int(first)
        last = int(last)
        if first < 0:
            first = 1
        if last < 0:
            last = 1

        bufptr = buffers[buf]
        first = bufptr.marker(first)
        last = bufptr.marker(last)
        if int(last) < int(first):
            last, first = first, last
        self.first = first
        self.last = last
        self.buf = buf

    def __iter__(self):
        n = int(self.first)
        b = buffers[self.buf].lines
        la = int(self.last) + 1
        while n < la:
            yield (n, b[n-1])
            n += 1

    def __str__(self):
        if self.first.line is None or self.last.line is None:
            return "invalid"
        return f"{int(self.first)}-{int(self.last)}@{self.buf}"

    def __contains__(self, line):
        line = int(line)
        return line >= int(self.first) and line <= int(self.last)

    def __len__(self):
        return int(self.last) - int(self.first) + 1

    def delete(self):
        global buffers
        idx = int(self.first)
        num = len(self)
        b = buffers[self.buf]
        for _ in range(num):
            b.delete(idx)

def table(aligns, itr, out):
    widths = []
    values = []
    for row in itr:
        row = [str(x) for x in row]
        while len(widths) < len(row):
            widths.append(0)
        for idx,col in enumerate(row):
            widths[idx] = max(widths[idx], len(col))
        values.append(row)
    for row in values:
        for idx,col in enumerate(row):
            if idx != 0:
                out(config["tablesep"], end="")
            w = widths[idx]
            a = aligns[idx]
            while len(col) < w:
                if a == 'l':
                    col = col + " "
                else:
                    col = " " + col
            out(col, end="")
        out()

def head(s: str):
    if len(s) == 0:
        return '\0'
    return s[0]

def take_int(s: str):
    oint = ""
    while head(s).isdigit():
        oint += s[0]
        s = s[1:]
    return oint, s

def parse_range(r: str):
    global selection

    r = r.strip()
    every = head(r) == '*'
    if every:
        r = r[1:]

    first, r = take_int(r)
    last = len(buffers[selection.buf].lines) if every else int(selection.last)
    if len(first) == 0:
        first = 1 if every else int(selection.first)
    else:
        first = int(first)
        last = first
    if head(r) == '-':
        r = r[1:]
        last, r = take_int(r)
        if len(last) == 0:
            last = None
        else:
            last = int(last)
    if head(r) == '+':
        r = r[1:]
        n, r = take_int(r)
        last = first + int(n)
    if head(r) == '~':
        r = r[1:]
        n, r = take_int(r)
        if len(n) == 0:
            n = 10
        else:
            n = int(n)
        n = int(n / 2)
        last = first + n
        first -= n

    bufid = selection.buf
    if head(r) == '@':
        bufid = int(r[1]) - 1
    buf = buffers[bufid]
    if last == None:
        last = len(buf.lines)
    return Range(buf.marker(first), buf.marker(last), bufid)

def odone():
    if boolconf("endline"):
        print()

def select_buf(idx):
    global buffers
    buf = buffers[idx]
    return Range(buf.marker(1), buf.marker(len(buffers[idx].lines)), idx)

last_listed_range = None

def macro_val_tostr(v):
    if v is None:
        return ""
    return str(v)

def exe(cmd: str, args: str, out=print):
    global selection
    global last_listed_range

    code_val = None

    commands = cmd.split(".")
    if len(commands) > 1:
        for cmd in commands:
            exe(cmd, args)
        return

    if cmd == "buf":
        if len(args) == 0:
            table("rll",
                  chain(
                      [("id", "path", "#lines")],
                      ((str(idx+1) + ("<" if selection and idx == selection.buf else ""), buf.file_path, len(buf.lines))
                       for idx, buf in enumerate(buffers))
                  ), out=out)
            odone()
        else:
            selection = select_buf(int(args) - 1)
            out(selection)
        code_val = selection.buf
    elif cmd == "rs":
        macroname, regx = args.split(" ", 1)
        for linenum, line in selection:
            for match in re.finditer(regex, line):
                args = list(match.groups())
                args.insert(0, match.group(0))
                args.insert(0, linenum)
                run_macro(macroname, args)
    elif cmd == "cfg":
        if len(args) == 0:
            table("ll", ((k, "'"+v+"'") for k,v in config.items()), out=out)
            odone()
        else:
            if args[-1] == '$':
                args = args[:-1]
            if "=" in args:
                k,v = args.split("=", 1)
                k = k.strip()
                config[k] = v
            else:
                val = config.get(args.strip(), None)
                if val is None:
                    out("unset")
                else:
                    out(f"'{val}'")
                code_val = val
                odone()
    elif cmd == "l":
        r = parse_range(args)
        last_listed_range = r
        bf = buffers[r.buf]
        table("rl",
              ((lnum, bf.highl(l)) for lnum, l in r), out=out)
        odone()
    elif cmd == "s":
        code_val = selection
        if len(args) == 0:
            out(str(selection))
            odone()
        else:
            r = parse_range(args)
            selection = r
    elif cmd == "sl":
        assert last_listed_range
        selection = last_listed_range
        code_val = selection
    elif cmd == "sa":
        buf = 0
        if len(args) > 0:
            buf = int(args) - 1
        selection = select_buf(buf)
        code_val = selection
    elif cmd == "w":
        buffers[selection.buf].save()
    elif cmd == "wa":
        for buf in buffers:
            buf.save()
    elif cmd == "d":
        r = parse_range(args)
        r.delete()
    elif cmd == "n":
        last = int(selection.last)
        num = len(selection)
        selection = Range(last + 1,
                          last + num,
                          selection.buf)
    elif any(cmd.startswith(x) for x in ["p", "a", "e"]):
        inplen = len(cmd)
        flags = cmd[1:]
        cmd = cmd[0:1]

        r = selection
        if 's' in flags:
            vli = args.split(" ", 1)
            inplen += 1
            inplen += len(vli[0])
            r = parse_range(vli[0])
            args = vli[1] if len(vli) > 1 else ""

        src_range = None
        if 'b' in flags:
            vli = args.split(" ", 1)
            inplen += 1
            inplen += len(vli[0])
            src_range = parse_range(vli[0])
            args = vli[1] if len(vli) > 1 else ""

        if 'm' in flags:
            assert 'b' in flags

        old_first = int(r.first)
        insert_at = None
        if cmd == "p":
            insert_at = int(r.first) - 1
        elif cmd == "a":
            insert_at = int(r.last)
        elif cmd == "e":
            insert_at = int(r.first) - 1
            r.delete()

        lines = []
        if src_range is None:
            lines.append(args)
            while True:
                out(config["echo"], end="")
                for i in range(inplen - 1):
                    out(" ", end="")
                out(".", end="")
                ln = input()
                if len(ln) == 0:
                    break
                ln = ln[1:]
                lines.append(ln)
            odone()
        else:
            lines = [x for _, x in src_range]
            if 'm' in flags:
                src_range.delete()

        buf = buffers[r.buf]
        buf.insert_many(insert_at, lines)
        if not 'q' in flags:
            if cmd == "p":
                selection.first = buf.marker(int(r.first) - len(lines))
            elif cmd == "a":
                selection.last = buf.marker(int(r.last) + len(lines))
            elif cmd == "e":
                selection.first = buf.marker(old_first)
                selection.last = buf.marker(old_first + len(lines) - 1)
    elif cmd == "script":
        run_script(args)
    elif cmd == ":":
        pass # comment
    elif cmd == "#l":
        r = parse_range(args)
        code_val = len(r)
        out(len(r))
        odone()
    elif cmd == "mm":
        v = exestr(args, macromode=True)
        out(macro_val_tostr(v))
    elif cmd == "q":
        print("really quit? (y/n) ", end="")
        yn = raw_read().lower()
        if yn == "y" or yn == "yes":
            exit(0)
    else:
        print("unknown")
        odone()

    return code_val


def noprint(*args, **kwargs):
    pass


def exestr(args:str, macromode:bool, out=print):
    if macromode:
        ind = False
        oargs = []
        exeargs = []
        for c in args:
            if ind:
                if c == '}':
                    ind = False
                    v = exestr(''.join(exeargs), macromode=True, out=noprint)
                    oargs.extend(macro_val_tostr(v))
                else:
                    exeargs.append(c)
            else:
                if c == '{':
                    ind = True
                    exeargs = []
                else:
                    oargs.append(c)
        args = ''.join(oargs)

    args = args.strip()
    if len(args) == 0:
        return
    args = args.split(" ", 1)
    cmd = args[0]
    args = args[1] if len(args) > 1 else ""
    return exe(cmd, args, out=out)


def run_script(path):
    with open(path, "r") as f:
        for idx, line in enumerate(f):
            try:
                exestr(line, macromode=False)
            except Exception as e:
                print(f"in {path}:{line+1}   {e}")
                raise e


def raw_read():
    sys.stdout.flush()
    out = []
    while True:
        ch = sys.stdin.read(1)
        if ch == '\r' or ch == '\n':
            break
        out.append(ch)
    return ''.join(out)


for file in sys.argv[1:]:
    buffers.append(Buffer(file))

if len(buffers) > 0:
    selection = select_buf(0)

while True:
    print(config["echo"], end="")
    args = raw_read()
    try:
        exestr(args, macromode=False)
    except Exception as e:
        print(e)
