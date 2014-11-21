from IPython.utils.traitlets import Unicode, List
from IPython.core.application import BaseIPythonApplication
from IPython.core.application import base_aliases, base_flags
from IPython.config.application import catch_config_error
from IPython.core.profiledir import ProfileDir

import os
import shutil
import tempfile
import datetime
import tarfile
import glob

from textwrap import dedent

aliases = {}
aliases.update(base_aliases)
aliases.update({
    "assignment-dir": "SubmitApp.assignment_directory",
    "assignment": "SubmitApp.assignment_name",
    "submit-dir": "SubmitApp.submissions_directory"
})

flags = {}
flags.update(base_flags)
flags.update({
})

examples = """
nbgrader submit "Problem Set 1"
"""

class SubmitApp(BaseIPythonApplication):

    name = Unicode(u'nbgrader-submit')
    description = Unicode(u'Submit a completed assignment')
    aliases = aliases
    flags = flags
    examples = examples

    student = Unicode(os.environ['USER'])
    assignment_directory = Unicode(
        '.', config=True, 
        help=dedent(
            """
            The directory containing the assignment to be submitted.
            """
        )
    )
    assignment_name = Unicode(
        '', config=True, 
        help=dedent(
            """
            The name of the assignment. Defaults to the name of the assignment
            directory.
            """
        )
    )
    submissions_directory = Unicode(
        "{}/.submissions".format(os.environ['HOME']), config=True, 
        help=dedent(
            """
            The directory where the submission will be saved.
            """
        )
    )

    ignore = List(
        [
            ".ipynb_checkpoints",
            "*.pyc"
        ], 
        config=True,
        help=dedent(
            """
            List of file names or file globs to be ignored when creating the
            submission.
            """
        )
    )

    # The classes added here determine how configuration will be documented
    classes = List()
    def _classes_default(self):
        """This has to be in a method, for TerminalIPythonApp to be available."""
        return [
            ProfileDir
        ]

    @catch_config_error
    def initialize(self, argv=None):
        if not os.path.exists(self.ipython_dir):
            self.log.warning("Creating IPython directory: {}".format(self.ipython_dir))
            os.mkdir(self.ipython_dir)
        super(SubmitApp, self).initialize(argv)
        self.stage_default_config_file()

        self.assignment_directory = os.path.abspath(self.assignment_directory)
        if self.assignment_name == '':
            self.assignment_name = os.path.basename(self.assignment_directory)

    def _is_ignored(self, filename):
        dirname = os.path.dirname(filename)
        for expr in self.ignore:
            globs = glob.glob(os.path.join(dirname, expr))
            if filename in globs:
                self.log.debug("Ignoring file: {}".format(filename))
                return True
        return False

    def start(self):
        super(SubmitApp, self).start()
        tmpdir = tempfile.mkdtemp()
        
        try:
            # copy everything to a temporary directory
            shutil.copytree(self.assignment_directory, os.path.join(tmpdir, self.assignment_name))
            os.chdir(tmpdir)

            # get the user name, write it to file
            with open(os.path.join(self.assignment_name, "user.txt"), "w") as fh:
                fh.write(self.student)

            # save the submission time
            timestamp = str(datetime.datetime.now())
            with open(os.path.join(self.assignment_name, "timestamp.txt"), "w") as fh:
                fh.write(timestamp)

            # get the path to where we will save the archive
            archive = os.path.join(
                self.submissions_directory, 
                "{}.tar.gz".format(self.assignment_name))
            if not os.path.exists(os.path.dirname(archive)):
                os.makedirs(os.path.dirname(archive))
            if os.path.exists(archive):
                shutil.copy(archive, "{}.bak".format(archive))
                os.remove(archive)

            # create a tarball with the assignment files
            tf = tarfile.open(archive, "w:gz")

            for (dirname, dirnames, filenames) in os.walk(self.assignment_name):
                if self._is_ignored(dirname):
                    continue

                for filename in filenames:
                    pth = os.path.join(dirname, filename)
                    if not self._is_ignored(pth):
                        self.log.debug("Adding '{}' to submission".format(pth))
                        tf.add(pth)
    
            tf.close()
            
        except:
            raise
            
        else:
            self.log.info("'{}' submitted by {} at {}".format(
                self.assignment_name, self.student, timestamp))
            
        finally:
            shutil.rmtree(tmpdir)
