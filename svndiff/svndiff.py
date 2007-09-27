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
      
"""

import sys
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
OPT_INTERVAL = "interval"
OPT_SUBSCRIBERS = "subscribers"
OPT_REPO = "repo"
OPT_SMTPSERVER = "smtpserver"
OPT_FROM = "from"

def send_diff(cfg, subscribers, module, revision, log, diff):
    logger = logging.getLogger(module)
    
    # create message
    context = {
        "revision": revision,
        "author": log[0],
        "timestamp": log[1],
        "message": escape_html(log[2]),
        "diff": escape_html(diff),
        "files": diffparser.get_files(diff, cfg.get(module, OPT_REPO))
    }
    
    msg_str = template.render(open(TEMPLATE_FILE, 'r').read(), context)
    
    # create email message
    #from_addr = cfg.get(MAIN_CONFIG_SECTION, OPT_FROM)
    from_addr = "%s@lehman.com" % log[0]
    msg = MIMEText(msg_str, "html")
    msg['Subject'] = "[svn-diff for %s, r%d] %s" % (module, revision, log[2])
    msg['From'] = from_addr 
    msg['To'] = subscribers
    
    # connect to SMTP server and send message
    smtp_server = cfg.get(MAIN_CONFIG_SECTION, OPT_SMTPSERVER)
    logger.debug("Sending mail to %s through %s" % (subscribers, smtp_server))
    s = smtplib.SMTP(smtp_server)
    #s.connect()
    s.sendmail(from_addr, subscribers.split(','), msg.as_string(False))
    s.close()
    
def check_module(cfg, module, repo, subscribers):
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
                logger.info("Sending log for revision %d" % rev)
                diff = sh.get_last_diff(rev)
                
                send_diff(cfg, subscribers, module, rev, log, diff)

            # write last checked revision to the file
            open(last_rev_file, 'w').write(str(rev))
    
    if last_checked_rev < 0:
        if not os.path.exists(LAST_REVS_DIR):
            os.makedirs(LAST_REVS_DIR)
        open(last_rev_file, 'w').write(str(latest_rev))

    if not changed:
        logger.info("No changes in %s since last check" % module)
        

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(name)s %(levelname)s %(message)s')
    
    if not os.path.isfile(CONFIG_FILE):
        print >> sys.stderr, "No config file found, please create " + CONFIG_FILE
        sys.exit(23)
    
    cfg = ConfigParser()
    cfg.read([CONFIG_FILE])
    logging.info("Parsed config file")
    
    default_interval = cfg.getint(MAIN_CONFIG_SECTION, OPT_INTERVAL)
    default_subscribers = cfg.get(MAIN_CONFIG_SECTION, OPT_SUBSCRIBERS)
    
    logging.info("Default interval: %d, default subscribers: %s" % 
            (default_interval, default_subscribers))
    
    for section in cfg.sections():
        if MAIN_CONFIG_SECTION != section:
            interval = default_interval
            if cfg.has_option(section, OPT_INTERVAL):
                interval = cfg.getint(section, OPT_INTERVAL)
                
            subscribers = default_subscribers
            if cfg.has_option(section, OPT_SUBSCRIBERS):
                subscribers = cfg.get(section, OPT_SUBSCRIBERS)
                
            repo = cfg.get(section, OPT_REPO)

            logging.info(("Starting check thread for module %s (%s)," +
                         "checking for changes every %d minutes," +
                         "subscribers: %s") % (section, repo, interval, subscribers))
            s = Scheduler(interval * 60, check_module, args = (cfg, section, repo, subscribers))
            s.start()
    
#    sh = SubversionHelper("http://svng/SVG/repos/PSFO-FINESSE/fcm")
#    print sh.get_revision()
#    print sh.get_last_diff(2997)
#    for r in range(2997, 2990, -1):
#        print sh.get_log(r)
