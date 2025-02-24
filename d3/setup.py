import subprocess
from distutils.command.build import build as _build
import setuptools
class build(_build):
    sub_commands = _build.sub_commands + [('CustomCommands', None)]
class CustomCommands(setuptools.Command):

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def RunCustomCommand(self, command_list):
        print('Running command: %s' % command_list)
        p = subprocess.Popen(
            command_list,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout_data, _ = p.communicate()
        print('Command output: %s' % stdout_data)
        if p.returncode != 0:
            raise RuntimeError(
                'Command %s failed: exit code: %s' % (command_list, p.returncode)
            )

    def run(self):
        for command in CUSTOM_COMMANDS:
            self.RunCustomCommand(command)

# ✅ FIXED the syntax error by ensuring each command is properly comma-separated!
CUSTOM_COMMANDS = [
    ['pip', 'install', 'opencv-python-headless'],
    ['pip', 'install', 'numpy'],
    ['pip', 'install', 'apache-beam[gcp]'],
    ['pip', 'install', 'google-cloud-pubsub'],
    ['pip', 'install', 'google-cloud-storage'],  # ✅ Ensure this is added for GCS access
]

REQUIRED_PACKAGES = [
    'opencv-python-headless',
    'numpy',
    'apache-beam[gcp]',
    'google-cloud-pubsub',
    'google-cloud-storage',
]

setuptools.setup(
    name='pedestrian-detection',
    version='0.1',
    description='Haar cascade-based pedestrian detection pipeline for Google Cloud Dataflow.',
    install_requires=REQUIRED_PACKAGES,
    packages=setuptools.find_packages(),
    cmdclass={'build': build, 'CustomCommands': CustomCommands}
)
