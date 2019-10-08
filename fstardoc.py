def remove_common_whitespace(a):
    v = None
    for i, l in enumerate(a):
        if len(l.strip()) == 0:
            a[i] = ''
            continue
        j = 0
        while j < len(l):
            if l[j] not in ' \t':
                break
            else:
                j += 1
        if v is None or j < v:
            v = j
    for i, l in enumerate(a):
        if len(l) != 0:
            a[i] = a[i][v:]
    return a


def cleanup_array(a):
    i = 0
    j = len(a)
    while i < len(a) and a[i] == '':
        i += 1
    while j >= 1 and a[j - 1] == '':
        j -= 1
    return remove_common_whitespace(a[i:j])


def split_array_at_empty(a):
    if '' in a:
        return a[:a.index('')], a[a.index('') + 1:]
    else:
        return a, []


class fst_parsed:

    def __init__(self):
        self.comment_nest_level = 0
        self.current_comment = []
        self.current_code = []
        self.current_comment_type = None
        self.output = []

    def _state(self):
        state = {
            'comment_nest_level': self.comment_nest_level,
            'current_comment': self.current_comment,
            'current_code': self.current_code,
            'current_comment_type': self.current_comment_type,
            'output': self.output,
        }
        return state

    def error(self, err, line=None):
        from pprint import pformat
        if line is not None:
            err += '\nLine: ' + repr(line)
        err += '\nState: ' + pformat(self._state())
        assert False, err

    def _flush_code(self):
        if len(self.current_code) > 0:
            self.output.append('```fstar')
            self.output.extend(self.current_code)
            self.output.append('```')
            self.current_code = []

    def _get_code_name(self):
        code = ' '.join(self.current_code)
        if 'val ' in code:
            return code[code.index('val ') + len('val '):].split(' ')[0]
        elif 'let ' in code:
            return code[code.index('let ') + len('let '):].split(' ')[0]
        else:
            return None

    def flush(self):
        self.current_comment = cleanup_array(self.current_comment)
        self.current_code = cleanup_array(self.current_code)
        if self.comment_nest_level != 0:
            self.error("Invalid nesting")
        if self.current_comment_type is None:
            if len(self.current_comment) > 0:
                self.error("Non empty None comment")
        elif self.current_comment_type == 'fsdoc':
            name = self._get_code_name()
            if name is not None:
                self.output.extend(['#### ' + self._get_code_name(), ''])
            cmt1, cmt2 = split_array_at_empty(self.current_comment)
            self.output.extend(cmt1)
            if len(cmt2) > 0:
                self.output.append('')
                self._flush_code()
                self.output.append('')
                self.output.extend(cleanup_array(cmt2))
        elif self.current_comment_type == 'fslit':
            self.output.extend(('> ' + x) for x in self.current_comment)
        elif self.current_comment_type == 'h1':
            self.output.extend(
                '# ' + x for x in
                self.current_comment)
        elif self.current_comment_type == 'h2':
            self.output.extend(
                '## ' + x for x in
                self.current_comment)
        elif self.current_comment_type == 'h3':
            self.output.extend(
                '### ' + x for x in
                self.current_comment)
        elif self.current_comment_type == 'normal':
            self.output.extend(self.current_comment)
        else:
            self.error("Unknown comment type.")
        self.output.append('\n')
        self.comment_nest_level = 0
        self.current_comment = []
        self._flush_code()
        self.current_comment_type = None

    def flush_if_not_and_set(self, typ):
        if self.current_comment_type != typ:
            self.flush()
            self.current_comment_type = typ

    def add_line(self, line):
        if '\n' in line:
            self.error("Newline in line", line)
        if self.comment_nest_level > 0:
            nest_level = self.comment_nest_level - line.count('*)')
            if nest_level > 0:
                self.current_comment.append(line)
            elif nest_level == 0:
                self.current_comment.append(
                    line[:line.rindex('*)')].rstrip())
            else:
                self.error("More close comments than opened", line)
            self.comment_nest_level = nest_level
            return
        elif self.comment_nest_level < 0:
            self.error("More close comments than opened", line)
        # Now we are at 0 nesting
        if line.strip() == '':
            self.current_code.append('')
            self.flush()
            return
        if line.startswith('/// '):
            self.flush_if_not_and_set('fslit')
            self.current_comment.append(line[len('/// '):])
            return
        if line == '///':
            self.flush_if_not_and_set('fslit')
            self.current_comment.append('')
            return
        lstripped = line.strip(' \t')
        if lstripped.startswith('(***** '):
            # heading 3
            self.flush_if_not_and_set('h3')
            if lstripped.count('(*') == lstripped.count('*)'):
                self.current_comment.append(
                    lstripped[len('(***** '):-len('*)')])
                self.flush()
            else:
                self.error("Unsupported multiline heading", line)
            return
        if lstripped.startswith('(**** '):
            # heading 2
            self.flush_if_not_and_set('h2')
            if lstripped.count('(*') == lstripped.count('*)'):
                self.current_comment.append(
                    lstripped[len('(**** '):-len('*)')])
                self.flush()
            else:
                self.error("Unsupported multiline heading", line)
            return
        if lstripped.startswith('(*** '):
            # heading 1
            self.flush_if_not_and_set('h3')
            if lstripped.count('(*') == lstripped.count('*)'):
                self.current_comment.append(
                    lstripped[len('(*** '):-len('*)')])
                self.flush()
            else:
                self.error("Unsupported multiline heading", line)
            return
        if lstripped.startswith('(** '):
            # fsdoc comment
            self.flush_if_not_and_set('fsdoc')
            if lstripped.count('(*') == lstripped.count('*)'):
                self.current_comment.append(
                    lstripped[len('(** '):-len('*)')])
            else:
                self.current_comment.append(
                    lstripped[len('(** '):])
                self.comment_nest_level = (
                    lstripped.count('(*') - lstripped.count('*)'))
            return
        if lstripped == '(**':
            # fsdoc comment start, but rest of comment is on further lines
            self.flush_if_not_and_set('fsdoc')
            self.comment_nest_level = 1
            return
        if lstripped.startswith('(*'):
            # normal comment
            self.flush_if_not_and_set('normal')
            if lstripped.count('(*') == lstripped.count('*)'):
                self.current_comment.append(
                    lstripped[len('(*'):-len('*)')])
                self.flush()
            else:
                self.current_comment.append(
                    lstripped[len('(*'):])
                self.comment_nest_level = (
                    lstripped.count('(*') - lstripped.count('*)'))
            return
        if lstripped.startswith('//'):
            # normal comment
            self.flush_if_not_and_set('normal')
            self.current_comment.append(lstripped[len('//'):])
            return
        # not comment
        if self.comment_nest_level == 0:
            if line.count('(*') == line.count('*)'):
                self.current_code.append(line)
            elif line.count('(*') > line.count('*)'):
                self.current_code.append(line[:line.index('(*')])
                self.add_line(line[:line.index('(*')])
            else:
                self.error("More closes than opens", line)
            return
        self.error("Impossible to reach", line)

    def generate_output(self):
        self.flush()
        out = '\n'.join(self.output)
        while '\n\n\n' in out:
            out = out.replace('\n\n\n', '\n\n')
        return out.strip()


def fst2md(fst):
    fst = fst.split('\n')
    fstp = fst_parsed()

    for line in fst:
        fstp.add_line(line)

    return fstp.generate_output()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input",
                        type=argparse.FileType('r'),
                        help="Input F* file")
    args = parser.parse_args()

    fst = args.input.read()
    args.input.close()
    print(fst2md(fst))


if __name__ == '__main__':
    main()
