#!/usr/bin/env python
# encoding: utf-8
'''
integrationtest.testrunner -- shortdesc

'''
import sys
import os
import pytest
import inspect
import faulthandler
from optparse import OptionParser
__all__ = []
__version__ = 0.1
__updated__ = ''
# Get root dir
THIS_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = THIS_DIR


class MyPlugin(object):
    def pytest_sessionfinish(self):
        print("####### test run reporting finishing")

class Main(object):
    def _enable_faulthandler(self):
        """ Enable faulthandler (if we can), so that we get tracebacks
        on segfaults.
        """
        try:
            import faulthandler
            faulthandler.enable()
            print('Faulthandler enabled')
        except Exception:
            print('Could not enable faulthandler')
    
    def run_tests(self):
        """ Run test from testrunner
        """
        local_vars = inspect.currentframe().f_back.f_locals
        if not (local_vars.get('__name__', '') == '__main__' or __name__ == '__main__'):
            return
        # we are in a "__main__"
        os.chdir(ROOT_DIR)
        #fname = str(local_vars['__file__'])
        self._enable_faulthandler()
        pytest.main(['-v', '-x', 'path'])
    

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.1"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''''' # optional - give further explanation about what the program does
    program_license = "Copyright Seagate"

    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")

        # process options
        (opts, args) = parser.parse_args(argv)

        if opts.verbose > 0:
            print("verbosity level = %d" % opts.verbose)
        Main().run_tests()

    except Exception as e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    sys.exit(main())