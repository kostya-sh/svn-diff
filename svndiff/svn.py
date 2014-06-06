"""
  This module provides wrappers for svn command to perform
  operations required by svn-diff application.
  
  TODO: improve error handling (check exit code of svn)
"""

from __future__ import with_statement

import os
import re
import exceptions

class SubversionException(exceptions.Exception):
    def __init__(self, svn_command, msg):
        self.svn_command = svn_command
        self.message = msg
        
    def __repr__(self):
        return "Eerror running %s: %s" % (self.svn_command, self.message)
    
    def __str__(self):
        return self.__repr__()

class Log:
    def __init__(self, author, timestamp, message):
        self.author = author
        self.author_name = author
        self.timestamp = timestamp
        self.message = message

    def date(self):
        return self.timestamp.split(" ")[0]

class SubversionHelper:
    REVISION_RE = re.compile("Revision: (\d+)")
    LOG_INFO_RE = re.compile(r"r(\d+) \| (\w+) \| (.*) \|")
        
    def __init__(self, repo):
        self.repo = repo
        
    def get_revision(self):
        """
        Returns latest repository revision
        """
        command = 'svn info "%s"' % self.repo
        with os.popen(command) as out:
            for line in out:
                matches = self.REVISION_RE.findall(line)
                if len(matches) > 0:
                    return int(matches[0])
        # error occured
        raise SubversionException(command, "Unable to find the latest revision of '%s'" % self.repo)
        
    def get_log(self, revision):
        """
        Returns log for the given revision as Log object.
        If there is no log for the given revision returns None
        """
        command = 'svn log -r %d "%s"' % (revision, self.repo)
        
        author = timestamp = None
        message = ""

        with os.popen(command) as out:
            for line in out:
                m = self.LOG_INFO_RE.match(line)
                if author is not None and not line.startswith(10 * "-") and not len(line.strip()) == 0:
                    message += line
                if m is not None:
                    author = m.group(2)
                    timestamp = m.group(3)
        
        if author is not None:
            return Log(author, timestamp, message.strip())
        return None
    
    def get_last_diff(self, revision):
        """
        Return output from svn diff for given revision. 
        """
        command = 'svn diff -r %d:%d "%s"' % (revision - 1, revision, self.repo)
        
        with os.popen(command) as out:
            return out.read()
