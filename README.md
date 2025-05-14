# A Line EDitor
fun fact: this whole file was written using aled.

## Concepts
### Line
lines are 1-indexed.

### Buffer
A place where multiple lines are stored.
Has a buffer ID, which is 1-based.

Example: a opened file

### Range
A range of lines in a specific buffer.

A range consits of a start and an end marker.

### Marker
a "safe" reference to a specific line, not just the line number.
this means that the marker will still point to the same line after some deletes or inserts have been done in the buffer.

### Selection
A range that is beeing operated on

### Macro
A (sequence) of commands that can be executed with arguments.


## Range Syntax
Examples:
| range expression | meaning |
| - | - |
| `*` | all lines in the currently selected buffer |
| `*@3` | all lines in buffer with ID 3 |
| `-3`  | from the first line of the current selection to line 3 |
| `1-3` | from line 1 to line 3 |
| `+3`  | from the last line of the current selection to two lines after that |
| `22+3` | from line 22 to line 25 |
| `22+3@2` | from line 22 to line 25 in buffer with ID 2 |
| `22~10` | 10 lines arround line 22: from line 17 to line 27 |
| `22~`   | if no number after the tilde, defaults to 10: from line 17 to line 27 |


## Commands
### `buf`
list opened buffers (also indicating the selected buffer)

in macro mode, returns the ID of the currently selected buffer.

Example:
```
  buf
id path #lines
1< file 41
```

### `buf bufid`
switch selection to all lines in given buffer.

in macro mode, returns the ID of the newly selected buffer.

Example:
```
  buf 1
1-41@1
```

### `cfg`
List all configured values.

Example:
```
  cfg
tablesep ' '
endline  '1'
echo     '  '
```

### `cfg key`
print the value of a configuration key.

in macro mode, returns the value (as string)

Example:
```
  cfg echo
'  '
```

### `cfg key=value`
set a config value.

Example:
```
  cfg endline=no
```

### `cfg key=value$`
also sets a config value, but removes the trailing dollar sign.
this is used to configure values that end with trailing spaces.

Example:
```
  cfg echo=    $
```

### `l`
print out all lines in the selection

### `l range`
print all lines in the given range

Example:
```
  l 5-9
5 some
6 example
7 text
8 
9 .
```

### `s`
print the selected range.

in macro mode, returns the current range.

Example:
```
  s
1-90@1
```

### `s range`
set the selection to the given range.

in code mode, returns the OLD range.

Example:
```
  s 5-9
```

### `sl`
set the selection to the range used in the previous `l` command.

in code mode, returns the new range.

Example:
```
  l 5-9
5 some
6 example
7 text
8 
9 .

  sl
  s
5-9@1
```

### `sa`
select all lines in the current buffer.

in macro mode, returns the new selection.

### `w`
write the current buffer to the original source file.

### `wa`
write all original buffers to the corresponding source files.

### `d`
delete all lines in the current selection.

### `d range`
delete all lines in the given selection.

### `n`
selects the next chunk of lines.
if the current selection is `1-5`, this will set the selection to `6-10` for example.

this can be used to simulate a pager like `less` or `more`.

Example:
```
  s 1-5
  s
1-5
  n
  s
6-10
  n
  s
11-15
```

### `script file`
execute each command in the given file

### `: comment`
will be ignored.

this can be used as a comment.

### `#l`
prints the number of lines in the current selection.

in macro mode, returns the number of lines.

### `#l range`
prints the number of lines in the given selection.

in macro mode, retuns the number of lines.

### `mm command`
runs the given command in macro mode, and prints the macro result.

### `q`
quit the editor.
this command will ask for conformation (in form of `y` / `yes` / no)

### `a`, `e`, and `p`
- `p` means "prepend", and will insert the text before the first line in the selection.
- `a` means "append", and will insert the text after the last line in the selection.
- `e` means "edit", and will replace the lines in the selection with the text.

directly after the name of the command (`p`, `a`, or `e`), you can add multiple "flags", like `q`, `s` and `b`.

If the `s` flag is specified, the first "argument" is used as range instead of the current selection.
Note that even if the `s` flag is specified, it will overwrite the current selection, unless the `q` flag is specified too.

If the `b` flag is specified, the second "argument" is used as source range.
With this flag, the command will not ask you for input lines, but instead use the given source as text.

The remaining arguments are used as the first line of the text, unless the `q` flag is specified.
After pressing enter, it will ask you to input more lines.
If you want to input an additional line, first input a space to indicate that that line is valid,
and then input the text.
If you do not input a space, and instead direclty press enter, it will end the mutli-line input.

If the `m` flag is specified, you also have to specify the `b` flag.
With the `m` flag, the lines are moved from the given text source to the insert location.

Unless the `q` flag is specified,
for all commands, the selection will be changed to contain the previous selection, including the added text, or for `e`, it will set the selection to the new text.


## Planned Features
- line word wrap command, to make writing markdown nicer
- named markers
- `rs`: regex search: call a macro with the values of all capture groups for all matches in the selection
- `rr`: regex replace: call a macro with the values of all capture groups that returns the new replace string for a specified capture group for all matches in the selection
- `!` flag to `a`/`e`/`p`: use the remaining arguments as shell command to execute, and use input text selection (via `b` flag) as stdin if set, and then insert stdout of shell command
