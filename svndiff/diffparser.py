"""
  This module provide functions to parse output of svn diff.
"""

import re
import logging
from cgi import escape as escape_html

TYPE_UNMODIFIED="unmod"
TYPE_ADDED="add"
TYPE_REMOVED="rem"
TYPE_MODIFIED="mod"
TYPE_COPIED="cp"
TYPE_MOVED="mv"
TYPE_INFO="info"

LOG = logging.getLogger("diffparser")

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
            # information about changed lines
            files[-1].changes.append(Change(line, TYPE_INFO))
        elif line.startswith("\\"):
            # "No newline at end of file"
            files[-1].changes.append(Change(line, TYPE_INFO))
        elif len(files) != 0:
            # changes
            c = Change(line[1:])
            if line.startswith("+"):
                c.type = TYPE_ADDED
            if line.startswith("-"):
                c.type = TYPE_REMOVED
            files[-1].changes.append(c)
        else:
            # TODO: handle properties changes
            # Exmaple of svn diff:
            #
            #Property changes on: srm-admin-ui
            #___________________________________________________________________
            #Name: svn:ignore
            #   - target
            #
            #   + target
            #.classpath
            #.project
            #.settings
            LOG.warn("Unexpected line: %s" % line)
            LOG.debug("Diff\n: %s" % diff)

    # do some after pricessing
    for file in files:
        # if from_rev is 0 then file was added
        if file.rev_from == 0:
            file.type = TYPE_ADDED

        # if number of changes with type 'REMOVED' is equal to the 
        # total number of changes the file was removed
        if len(filter(lambda c: c.type != TYPE_INFO, file.changes)) == len(filter(lambda c: c.type == TYPE_REMOVED, file.changes)):
            file.type = TYPE_REMOVED

    return files

if __name__ == "__main__":
    import doctest
    doctest.testmod()
