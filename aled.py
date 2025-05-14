#!/usr/bin/env python3

import sys
from itertools import chain
import weakref
import sys

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
        bufptr = buffers[buf]
        if not isinstance(first, Marker):
            first = bufptr.marker(first)
        if not isinstance(last, Marker):
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
        return f"{int(self.first)} - {int(self.last)} @ {self.buf}"

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

def table(aligns,itr):
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
                print(config["tablesep"], end="")
            w = widths[idx]
            a = aligns[idx]
            while len(col) < w:
                if a == 'l':
                    col = col + " "
                else:
                    col = " " + col
            print(col, end="")
        print()

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
    first, r = take_int(r)
    last = selection.last
    if len(first) == 0:
        first = selection.first
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

def exe(cmd: str, args: str):
    global selection
    global last_listed_range

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
                  ))
            odone()
        else:
            b = buffers[int(args) - 1]
    elif cmd == "cfg":
        if len(args) == 0:
            table("ll", ((k, "'"+v+"'") for k,v in config.items()))
            odone()
        else:
            if args[-1] == '$':
                args = args[:-1]
            k,v = args.split("=", 1)
            k = k.strip()
            old = config.get(k,None)
            config[k] = v
            if old is not None:
                print("was '" + old + "'")
                odone()
    elif cmd == "l":
        r = parse_range(args)
        last_listed_range = r
        bf = buffers[r.buf]
        table("rl",
              ((lnum, bf.highl(l)) for lnum, l in r))
        odone()
    elif cmd == "s":
        if len(args) == 0:
            print(str(selection))
            odone()
        else:
            r = parse_range(args)
            selection = r
    elif cmd == "sl":
        assert last_listed_range
        selection = last_listed_range
    elif cmd == "sa":
        buf = 0
        if len(args) > 0:
            buf = int(args) - 1
        selection = select_buf(buf)
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
    elif cmd == "p" or cmd == "a" or cmd == "e":
        old_first = int(selection.first)
        insert_at = int(selection.first) - 1
        if cmd == "a":
            insert_at = int(selection.last)
        elif cmd == "e":
            insert_at = int(selection.first) - 1
            selection.delete()
        lines = [args]
        while True:
            print(config["echo"] + ".", end="")
            ln = input()
            if len(ln) == 0:
                break
            ln = ln[1:]
            lines.append(ln)
        odone()
        buf = buffers[selection.buf]
        buf.insert_many(insert_at, lines)
        if cmd == "p":
            selection.first = buf.marker(int(selection.first) - len(lines))
        elif cmd == "a":
            selection.last = buf.marker(int(selection.last) + len(lines))
        elif cmd == "e":
            selection.first = buf.marker(old_first)
            selection.last = buf.marker(old_first + len(lines) - 1)
    elif cmd == "script":
        run_script(args)
    elif cmd == ":":
        pass # comment
    elif cmd == "#s":
        print(len(selection))
        odone()
    elif cmd == "q":
        print("really quit? (y/n) ", end="")
        yn = raw_read().lower()
        if yn == "y" or yn == "yes":
            exit(0)
    else:
        print("unknown")
        odone()


def exestr(args):
    args = args.strip()
    if len(args) == 0:
        return
    args = args.split(" ", 1)
    cmd = args[0]
    args = args[1] if len(args) > 1 else ""
    exe(cmd,args)


def run_script(path):
    with open(path, "r") as f:
        for idx, line in enumerate(f):
            try:
                exestr(line)
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
        exestr(args)
    except Exception as e:
        print(e)
