"""
TODO: unused currently by SwiftLauncher, but may still be needed, so keeping
this module for now.
"""


class Runner(object):
    name = None # subclass must set

    def wrap_app_command(self, command_dir, out_name, app_command):
        """
        Given an application command line, return a list of commands to
        run the given line using this runner and in the specified command
        working directory.
        """
        # subclass must implement
        raise NotImplemented()


class RunnerLocal(Runner):
    name = 'local'

    def wrap_app_command(self, command_dir, out_name, app_command):
        """
        Run directly, just at cd before/after to arrange separate working
        dir per run.

        TODO: how to pass runner params?

        NOTE: assumes CWD is batch directory within the experiment output dir.
        """
        return ['cd "%s"' % command_dir,
                'start=$(date +%s)',
                app_command + ' >%s 2>&1' % out_name,
                'end=$(date +%s)',
                'echo $(($end - $start)) > codar.cheetah.walltime.txt',
                'cd ..']


class RunnerCray(Runner):
    name = 'cray'

    def wrap_app_command(self, command_dir, out_name, app_command):
        """
        Run using aprun, and cd before/after to arrange separate working
        dir per run.

        TODO: how to pass aprun params?

        NOTE: assumes CWD is batch directory within the experiment output dir.
        """
        return ['cd "%s"' % command_dir,
                'aprun ' + app_command + ' >%s 2>&1' % out_name,
                'cd ..']
