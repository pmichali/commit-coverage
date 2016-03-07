commit-coverage
===============

This allows you to assess the coverage of changes you have in a repo. It
is intended for use, when preparing to push code up for review upstream.

Usage
-----

As a prerequisite to using this script, run coverage in the repo, to
produce coverage report files in a 'cover' directory at the root of the
repo's tree. This coverage should be done on the code that will be
upstreamed (either what is in the working directory, or what has been
committed to the local repo).

Behavior
--------

Assuming you have a repo with uncommitted changes, you can run the command
as follows::

    commit_coverage /opt/stack/networking-cisco

The argument must be the root of a git repo that has coverage data in a
'cover' subdirectory.

By default, this will create diffs comparing the working directory, to the
latest commit (HEAD), with (up to) three lines of context. That output will
be checked against coverage data and a report produced. Here's what the
output looks like::

    devstack/csr1kv/cisco_neutron (No coverage data)

    networking_cisco/apps/saf/agent/dfa_agent.py (No added/changed lines)

    networking_cisco/apps/saf/server/dfa_server.py (run=1, mis=1, par=0, ign=0) 47%
       32 run  import time
       33      
       34      
       35 run +from networking_cisco._i18n import _LE, _LI, _LW
       36 run  from oslo_serialization import jsonutils
       37      
       38      
    
      382              # it is created by openstack.
      383 run          part_name = self.cfg.dcnm.default_partition_name
      384 par          if len(':'.join((proj_name, part_name))) > 32:
      385 mis +            LOG.error(_LE('Invalid project name length: %s. The length of '
      386                                'org:part name is greater than 32'),
      387                            len(':'.join((proj_name, part_name))))
      388 mis              return

Each file from the diff will be reported. If the file was not processed
by the coverage test, or there were no added or changed lines in the
diff for the file, this will be reported, as shown in the first two files.

For files with coverage data and added/changes lines, the output will
look like the third file. Each line number from the diff is shown, with
the coverage status, which can be:

* 'run'  The line was invoked as part of coverage run
* 'mis'  The line was not invoked during coverage
* 'par'  The line was partially covered
* '   '  The line was not considered for coverage (e.g. blank, non-executable)

Next, if the line was added/changed, a '+' is shown. If it was a context line
for the diff region, a ' ' is shown. Deleted lines are not shown. After that,
the source code is show.

Next to the filename is summary information, ONLY for lines that were added
or changed. In the example, there was one line run and one missing in the
change set (lines with a plus sign). At the end, we can see the overall
coverage report for the FILE - 47% in this example.

There are a few knobs that you can use with this script. First, you can change
the number of context lines shown by using the --context argument. The default
is three, and can be zero or more. Note: if a diff region is at the start or
end of a file, there may be fewer or no context lines.

Second, you can select which commits are used for the diff calculation, by
specifying the --which argument. The default is 'working', which will do a
diff between the working directory and latest commit (HEAD). Instead, you can
provide 'committed', which will compare the current commit against the
previous commit (HEAD^..HEAD). Otherwise, you can provide the commit versions
to use for the diff, just make sure that the most recent corresponds to the
coverage report. For example, you can do::

    cd /opt/stack/neutron
    commit_coverage --context 5 --which HEAD~5..HEAD~ .

This runs the tool on a neutron repo, shows more context lines, and will
do a diff between HEAD~5 and HEAD~ commits.

You can use the -h option to see what the arguments are for this script.
