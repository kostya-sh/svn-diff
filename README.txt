svndiff
=======

What is it?
-----------
svndiff checks subversion repositories at regular interval and notifies
about any changes made to specified email addresses.

svndiff doesn't require access to repository on the server, it uses
only subversion client tools to do the job. 

Configuration
-------------
Configuration is in ini-file format.
 
Have a look at sample configuration file config.sample. Modify it and
copy to ~/.svn-diff/config
