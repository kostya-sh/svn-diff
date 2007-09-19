"""
  This module provide functions to parse output of svn diff.
"""

import re
from cgi import escape as escape_html

TYPE_UNMODIFIED="unmod"
TYPE_ADDED="add"
TYPE_REMOVED="rem"
TYPE_MODIFIED="mod"
TYPE_COPIED="cp"
TYPE_MOVED="mv"

class Change:
    def __init__(self, line, type = TYPE_UNMODIFIED):
        self.line = escape_html(line)
        self.type = type
        
    def __repr__(self):
        return "%s: %s" % (self.type, self.line)
    
    def __str__(self):
        return self.__repr__()
    

class File:
    def __init__(self, type, path, url, changes = []):
        self.type = type
        self.path = path
        self.url = url
        self.changes = changes
        self.rev_from = 0
        self.rev_to = 0
        
    def __repr__(self):
        return "File %s (%s)" % (self.path, self.type)
    
    def __str__(self):
        return self.__repr__()

INDEX = "Index: "
REVISION_RE = re.compile ("revision (\d+)")

def get_files(diff, base_url):
    """
    Parses output of svn diff and return list of 
    modified/added/deleted files.
    
    >>> get_files('''Index: srm-pom/pom.xml
    ... ===================================================================
    ... --- srm-pom/pom.xml (revision 3415)
    ... +++ srm-pom/pom.xml (revision 3417)
    ... @@ -24,7 +24,7 @@
    ... 
    ... <properties>
    ...     <scmModule>srm</scmModule>
    ... -   <infrastructure-release>1.113</infrastructure-release>
    ... +   <infrastructure-release>1.115</infrastructure-release>
    ... </properties>
    ...
    ... <dependencies>
    ... Index: test.txt
    ... ===================================================================
    ... --- text.txt (revision 0)
    ... +++ test.txt (revision 3417)
    ... @@ -0,0 +1,3 @@
    ... +1
    ... +2
    ... +3
    ... Index: test2.txt
    ... ===================================================================
    ... --- text2.txt (revision 3410)
    ... +++ test2.txt (revision 3417)
    ... @@ -1,3 +0,0 @@
    ... -3
    ... -2
    ... -1
    ... \ No newline at end of file
    ... Index: psfo-messagekit/pom.xml
    ... ===================================================================
    ... --- psfo-messagekit/pom.xml (revision 3416)
    ... +++ psfo-messagekit/pom.xml (revision 3417)
    ... @@ -5,7 +5,7 @@
    ...      <parent>
    ...          <groupId>com.lehman.psfo</groupId>
    ...          <artifactId>infrastructure-pom</artifactId>
    ... -        <version>1.115</version>
    ... +        <version>1.116-SNAPSHOT</version>
    ...      </parent>''', 'http://svn/')
    [File srm-pom/pom.xml (mod), File test.txt (add), File test2.txt (rem), File psfo-messagekit/pom.xml (mod)]
    """
    
    if base_url.endswith("/"):
        base_url = base_url[:-1]
    
    files = []
    for line in diff.splitlines():
        if line.startswith(INDEX):
            file_path = line[len(INDEX):] 
            
            files.append(File(TYPE_MODIFIED,                   # type 
                              file_path,                       # path
                              "%s/%s" % (base_url, file_path), # url
                              []                               # changes
                        ))
        elif line.startswith("========="):
            # skip seprator line
            pass
        elif line.startswith("---"):
            # parse from revision
            m = REVISION_RE.search(line)
            if m is not None:
                files[-1].rev_from = int(m.group(1))
        elif line.startswith("+++"):
            # parse to revision
            m = REVISION_RE.search(line)
            if m is not None:
                files[-1].rev_to = int(m.group(1))
        elif line.startswith("@@"):
            # information about changed lines: skip it for now
            pass
        elif line.startswith("\\"):
            # "No newline at end of file": skip this for now
            pass
        else:
            # changes
            c = Change(line[1:])
            if line.startswith("+"):
                c.type = TYPE_ADDED
            if line.startswith("-"):
                c.type = TYPE_REMOVED
            files[-1].changes.append(c)

    # do some after pricessing
    for file in files:
        # if from_rev is 0 then file was added
        if file.rev_from == 0:
            file.type = TYPE_ADDED

        # if number of changes with type 'REMOVED' is equal to the 
        # total number of changes the file was removed
        if len(file.changes) == len(filter(lambda c: c.type == TYPE_REMOVED, file.changes)):
            file.type = TYPE_REMOVED

    return files

if __name__ == "__main__":
    import doctest
    doctest.testmod()


########## TODO: remove everything below after extracting useful functionality ######### 
    
#
#
#def render(self, context, mimetype, content, filename=None, rev=None):
#    req = context.req
#    from trac.web.chrome import Chrome
#
#    content = content_to_unicode(self.env, content, mimetype)
#    changes = self._diff_to_hdf(content.splitlines(),
#                                Mimeview(self.env).tab_width)
#    if not changes:
#        raise TracError, 'Invalid unified diff content'
#    data = {'diff': {'style': 'inline'}, 'no_id': True,
#            'changes': changes, 'longcol': 'File', 'shortcol': ''}
#
#    add_script(req, 'common/js/diff.js')
#    add_stylesheet(req, 'common/css/diff.css')
#    return Chrome(self.env).render_template(req, 'diff_div.html',
#                                            data, fragment=True)
#
# Internal methods
#
# FIXME: This function should probably share more code with the
#        trac.versioncontrol.diff module
#def _diff_to_hdf(self, difflines, tabwidth):
#    """
#    Translate a diff file into something suitable for inclusion in HDF.
#    The result is [(filename, revname_old, revname_new, changes)],
#    where changes has the same format as the result of
#    `trac.versioncontrol.diff.hdf_diff`.
#
#    If the diff cannot be parsed, this method returns None.
#    """
#
#    import re
#    space_re = re.compile(' ( +)|^ ')
#    def htmlify(match):
#        div, mod = divmod(len(match.group(0)), 2)
#        return div * '&nbsp; ' + mod * '&nbsp;'
#
#    comments = []
#    changes = []
#    lines = iter(difflines)
#    try:
#        line = lines.next()
#        while True:
#            if not line.startswith('--- '):
#                if not line.startswith('Index: ') and line != '='*67:
#                    comments.append(line)
#                line = lines.next()
#                continue
#
#            oldpath = oldrev = newpath = newrev = ''
#
#             Base filename/version
#            oldinfo = line.split(None, 2)
#            if len(oldinfo) > 1:
#                oldpath = oldinfo[1]
#                if len(oldinfo) > 2:
#                    oldrev = oldinfo[2]
#
#             Changed filename/version
#            line = lines.next()
#            if not line.startswith('+++ '):
#                return None
#
#            newinfo = line.split(None, 2)
#            if len(newinfo) > 1:
#                newpath = newinfo[1]
#                if len(newinfo) > 2:
#                    newrev = newinfo[2]
#
#            shortrev = ('old', 'new')
#            if oldpath or newpath:
#                sep = re.compile(r'([/.~])')
#                commonprefix = ''.join(os.path.commonprefix(
#                    [sep.split(newpath), sep.split(oldpath)]))
#                commonsuffix = ''.join(os.path.commonprefix(
#                    [sep.split(newpath)[::-1],
#                     sep.split(oldpath)[::-1]])[::-1])
#                if len(commonprefix) > len(commonsuffix):
#                    common = commonprefix
#                elif commonsuffix:
#                    common = commonsuffix.lstrip('/')
#                    a = oldpath[:-len(commonsuffix)]
#                    b = newpath[:-len(commonsuffix)]
#                    if len(a) < 4 and len(b) < 4:
#                        shortrev = (a, b)
#                else:
#                    common = '(a) %s vs. (b) %s' % (oldpath, newpath)
#                    shortrev = ('a', 'b')
#            else:
#                common = ''
#
#            groups = []
#            changes.append({'change': 'edit', 'props': [],
#                            'comments': '\n'.join(comments),
#                            'diffs': groups,
#                            'old': {'path': common,
#                                    'rev': ' '.join(oldinfo[1:]),
#                                    'shortrev': shortrev[0]},
#                            'new': {'path': common,
#                                    'rev': ' '.join(newinfo[1:]),
#                                    'shortrev': shortrev[1]}})
#            comments = []
#            line = lines.next()
#            while line:
#                 "@@ -333,10 +329,8 @@" or "@@ -1 +1 @@"
#                r = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',
#                             line)
#                if not r:
#                    break
#                blocks = []
#                groups.append(blocks)
#                fromline, fromend, toline, toend = [int(x or 1)
#                                                    for x in r.groups()]
#                last_type = last_change = extra = None
#
#                fromend += fromline
#                toend += toline
#                line = lines.next()
#                while fromline < fromend or toline < toend or extra:
#
#                     First character is the command
#                    command = ' '
#                    if line:
#                        command, line = line[0], line[1:]
#                     Make a new block?
#                    if (command == ' ') != last_type:
#                        last_type = command == ' '
#                        kind = last_type and 'unmod' or 'mod'
#                        blocks.append({'type': kind,
#                                       'base': {'offset': fromline - 1,
#                                                'lines': []},
#                                       'changed': {'offset': toline - 1,
#                                                   'lines': []}})
#                    if command == ' ':
#                        sides = ['base', 'changed']
#                    elif command == '+':
#                        last_side = 'changed'
#                        sides = [last_side]
#                    elif command == '-':
#                        last_side = 'base'
#                        sides = [last_side]
#                    elif command == '\\' and last_side:
#                        sides = [last_side]
#                    else:
#                        return None
#                    for side in sides:
#                        if side == 'base':
#                            fromline += 1
#                        else:
#                            toline += 1
#                        blocks[-1][side]['lines'].append(line)
#                    line = lines.next()
#                    extra = line and line[0] == '\\'
#    except StopIteration:
#        pass
#
#     Go through all groups/blocks and mark up intraline changes, and
#     convert to html
#    for o in changes:
#        for group in o['diffs']:
#            for b in group:
#                f, t = b['base']['lines'], b['changed']['lines']
#                if b['type'] == 'mod':
#                    if len(f) == 0:
#                        b['type'] = 'add'
#                    elif len(t) == 0:
#                        b['type'] = 'rem'
#                    elif len(f) == len(t):
#                        _markup_intraline_change(f, t)
#                for i in xrange(len(f)):
#                    line = expandtabs(f[i], tabwidth, '\0\1')
#                    line = escape(line, quotes=False)
#                    line = '<del>'.join([space_re.sub(htmlify, seg)
#                                         for seg in line.split('\0')])
#                    line = line.replace('\1', '</del>')
#                    f[i] = Markup(line)
#                for i in xrange(len(t)):
#                    line = expandtabs(t[i], tabwidth, '\0\1')
#                    line = escape(line, quotes=False)
#                    line = '<ins>'.join([space_re.sub(htmlify, seg)
#                                         for seg in line.split('\0')])
#                    line = line.replace('\1', '</ins>')
#                    t[i] = Markup(line)
#
#    return changes
