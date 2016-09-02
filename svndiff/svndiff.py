"""
  Main program.
    
  Format of config file::
    [SVN-DIFF]
    interval = default interval in minutes
    subscribers = comma separated list of recipients
    
    [module1]
    repo = url to SVN repo
    interval = interval to check for diffs in minutes (optional, overrides default)
    subscribers = comma separated list of recipients (optional, overrides default)
    diff_dir = directory to store diff files instead of sending emails (optional)

"""

import sys
import os
import os.path
import logging
import smtplib
from email.mime.text import MIMEText
from ConfigParser import ConfigParser
from cgi import escape as escape_html

import template
import diffparser
from scheduler import Scheduler
from svn import SubversionHelper

# files and directories
APP_DIR = os.path.join(os.path.expanduser('~'), '.svn-diff')
CONFIG_FILE = os.path.join(APP_DIR, 'config')
LAST_REVS_DIR = os.path.join(APP_DIR, 'last-revs')
# TODO: make template location configurable
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "../templates/simple.html")

# configuration names
MAIN_CONFIG_SECTION = "SVN-DIFF"
OPT_DEBUG = "debug"
OPT_INTERVAL = "interval"
OPT_SUBSCRIBERS = "subscribers"
OPT_REPO = "repo"
OPT_SMTPSERVER = "smtpserver"
OPT_FROM = "from"
OPT_FROM_DOMAIN = "from_domain"
OPT_MAX_DIFFSIZE = "max_diff_size"
OPT_DIFF_DIR = "diff_dir"
OPT_GROUP_BY_DATE = "group_by_date"
OPT_AUTHOR_NAME = "author_name"

DEFAULT_CONFIG = {
    OPT_DEBUG: "false"
}

def send_diff(cfg, module, revision, log, diff):
    if cfg.has_option(module, OPT_DIFF_DIR):
        send_diff_to_file(cfg, module, revision, log, diff)
    else:
        send_diff_by_email(cfg, module, revision, log, diff)

def send_diff_to_file(cfg, module, revision, log, diff):
    logger = logging.getLogger(module)

    diff_dir = cfg.get(module, OPT_DIFF_DIR)
    if cfg.has_option(module, OPT_GROUP_BY_DATE) and cfg.getboolean(module, OPT_GROUP_BY_DATE):
        diff_dir = os.path.join(diff_dir, log.date())
    if not os.path.exists(diff_dir):
        os.makedirs(diff_dir)

    diff_file = os.path.join(diff_dir, "%s-%d.diff" % (module, revision))
    logger.info("Writing diff for %d to %s", revision, diff_file)
    f = open(diff_file, 'w')
    # make commit message look a bit like a diff
    f.write("Index: commit message\n")
    f.write("===================================================================\n")
    f.write("--- commit message\n")
    f.write("+++ commit message\n")
    f.write("@@ -0,0 +0,0 @@\n\n")
    f.write("Author    : %s\n" % log.author_name)
    f.write("Timestamp : %s\n" % log.timestamp)
    f.write("Message   : %s\n\n" % log.message)
    f.write(diff)
    f.close()

def send_diff_by_email(cfg, module, revision, log, diff):
    logger = logging.getLogger(module)

    subscribers = cfg.get(MAIN_CONFIG_SECTION, OPT_SUBSCRIBERS)
    if cfg.has_option(module, OPT_SUBSCRIBERS):
        subscribers = cfg.get(module, OPT_SUBSCRIBERS)

    # create message
    context = {
        "revision": revision,
        "author": log.author_name,
        "timestamp": log.timestamp,
        "message": escape_html(log.message),
        "diff": escape_html(diff),
        "files": diffparser.get_files(diff, cfg.get(module, OPT_REPO))
    }
    
    msg_str = template.render(open(TEMPLATE_FILE, 'r').read(), context)
    
    # create email message
    from_domain = cfg.get(MAIN_CONFIG_SECTION, OPT_FROM_DOMAIN)
    from_addr = "%s@%s" % (log.author, from_domain)
    msg = MIMEText(msg_str, "html")
    msg['Subject'] = "[svn-diff for %s, r%d] %s" % (module, revision, log.message)
    msg['From'] = from_addr 
    msg['To'] = subscribers
    
    # connect to SMTP server and send message
    smtp_server = cfg.get(MAIN_CONFIG_SECTION, OPT_SMTPSERVER)
    logger.info("Sending mail to %s through %s from %s" , subscribers, smtp_server, from_addr)
    s = smtplib.SMTP(smtp_server)
    #s.connect()
    s.sendmail(from_addr, subscribers.split(','), msg.as_string(False))
    s.close()
    
def check_module(cfg, module, repo):
    max_diff_size = cfg.getint(MAIN_CONFIG_SECTION, OPT_MAX_DIFFSIZE)

    logger = logging.getLogger(module)
    
    logger.info("Checking %s" % module)
    
    # read the latest revision from the file
    last_rev_file = os.path.join(LAST_REVS_DIR, module)
    last_checked_rev = -1
    if os.path.exists(last_rev_file):
        last_checked_rev = int(open(last_rev_file, 'r').read())
    logger.debug("Last checked revision %d" % last_checked_rev)
    
    # find the latest revision from svn
    sh = SubversionHelper(repo)
    latest_rev = sh.get_revision()
    logger.debug("Latest remote revision %d" % latest_rev)
    
    # find diffs and send them
    changed = False
    if last_checked_rev > 0 and last_checked_rev < latest_rev:
        for rev in range(last_checked_rev + 1, latest_rev + 1):
            logger.debug("Checking log for revision %d" % rev)
            log = sh.get_log(rev)

            # if there are some changes send diff
            if log is not None:
                changed = True
                logger.info("Getting log for revision %d" % rev)
                diff = sh.get_last_diff(rev)

                if max_diff_size is not None and len(diff) > max_diff_size:
                    logger.info("Diff size %d is more than configured max diff size %d.", len(diff), max_diff_size)
                    diff = diff[:max_diff_size]

                # author mapping
                opt_author_name = OPT_AUTHOR_NAME + "." + log.author
                if cfg.has_option(module, opt_author_name):
                    log.author_name = cfg.get(module, opt_author_name)

                try:
                    send_diff(cfg, module, rev, log, diff)
                except Exception:
                    logger.exception("Failed to send diff for module %s, revision %d: " % (module, rev))
                    return

            # write last checked revision to the file
            open(last_rev_file, 'w').write(str(rev))
   
    if last_checked_rev < 0:
        if not os.path.exists(LAST_REVS_DIR):
            os.makedirs(LAST_REVS_DIR)
        open(last_rev_file, 'w').write(str(latest_rev))

    if not changed:
        logger.info("No changes in %s since last check" % module)
        

if __name__ == "__main__":
    if not os.path.isfile(CONFIG_FILE):
        print >> sys.stderr, "No config file found, please create " + CONFIG_FILE
        sys.exit(23)

    cfg = ConfigParser(DEFAULT_CONFIG)
    cfg.read([CONFIG_FILE])

    level = logging.INFO
    if cfg.getboolean(MAIN_CONFIG_SECTION, OPT_DEBUG):
        level=logging.DEBUG
    logging.basicConfig(level=level, format='%(asctime)s %(name)s %(levelname)s %(message)s')

    logging.info("Parsed config file")

    default_interval = cfg.getint(MAIN_CONFIG_SECTION, OPT_INTERVAL)
    logging.info("Default interval: %d" % default_interval)
    
    for section in cfg.sections():
        if MAIN_CONFIG_SECTION != section:
            interval = default_interval
            if cfg.has_option(section, OPT_INTERVAL):
                interval = cfg.getint(section, OPT_INTERVAL)
                
            repo = cfg.get(section, OPT_REPO)

            logging.info(("Starting check thread for module %s (%s)," +
                          "checking for changes every %d minutes") % (section, repo, interval))
            s = Scheduler(interval * 60, check_module, args = (cfg, section, repo))
            s.start()
    
#    sh = SubversionHelper("http://svng/SVG/repos/PSFO-FINESSE/fcm")
#    print sh.get_revision()
#    print sh.get_last_diff(2997)
#    for r in range(2997, 2990, -1):
#        print sh.get_log(r)
