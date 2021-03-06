# IMPORTANT: The purpose of this script is to update the astropy-helpers
# submodule in all affiliated packages (and a few other packages) that make use
# of the astropy-helpers. This script is not intended to be run by affiliated
# package maintainers, and should only be run with approval of both the
# astropy-helpers and package-template lead maintainers, once an
# astropy-helpers release has been made.

import os
import sys
import netrc
import shutil
import tempfile
import subprocess

import requests
from github import Github

try:
    HELPERS_TAG = sys.argv[1]
except IndexError:
    raise IndexError("Please specify the helpers version as argument")

BRANCH = 'update-helpers-{0}'.format(HELPERS_TAG)

GITHUB_API_HOST = 'api.github.com'
my_netrc = netrc.netrc()
username, _, password = my_netrc.authenticators(GITHUB_API_HOST)[:3]
gh = Github(username, password)
user = gh.get_user()


def run_command(command):
    print('-' * 72)
    print("Running '{0}'".format(command))
    ret = subprocess.call(command, shell=True)
    if ret != 0:
        raise Exception("Command '{0}' failed".format(command))


def ensure_fork_exists(repo):
    if repo.owner.login != user.login:
        return user.create_fork(repo)
    else:
        return repo


def open_pull_request(fork, repo):

    # Set up temporary directory
    tmpdir = tempfile.mkdtemp()
    os.chdir(tmpdir)

    # Clone the repository
    run_command('git clone {0}'.format(fork.ssh_url))
    os.chdir(repo.name)

    # Make sure the branch doesn't already exist
    try:
        run_command('git checkout origin/{0}'.format(BRANCH))
    except:
        pass
    else:
        print("Branch {0} already exists".format(BRANCH))
        return

    # Update to the latest upstream master
    run_command('git remote add upstream {0}'.format(repo.clone_url))
    run_command('git fetch upstream')
    run_command('git checkout upstream/master')
    run_command('git checkout -b {0}'.format(BRANCH))

    # Initialize submodule
    run_command('git submodule init')
    run_command('git submodule update')

    # Check that the repo uses astropy-helpers
    if not os.path.exists('astropy_helpers'):
        print("Repository {0} does not use astropy-helpers".format(repo.name))
        return

    # Update the helpers
    os.chdir('astropy_helpers')
    rev_prev = subprocess.check_output('git rev-list HEAD', shell=True).splitlines()
    run_command('git fetch origin')

    run_command('git checkout {0}'.format(HELPERS_TAG))
    rev_new = subprocess.check_output('git rev-list HEAD', shell=True).splitlines()
    if len(rev_new) <= len(rev_prev):
        print("Repository {0} already has an up-to-date astropy-helpers".format(repo.name))
        return
    os.chdir('..')
    shutil.copy('astropy_helpers/ah_bootstrap.py', 'ah_bootstrap.py')

    run_command('git add astropy_helpers')
    run_command('git add ah_bootstrap.py')
    run_command('git commit -m "Updated astropy-helpers to {0}"'.format(HELPERS_TAG))

    run_command('git push origin {0}'.format(BRANCH))

    print(tmpdir)

    report_user = '@astrofrog'

    if username != 'astrofrog':
        report_user = '@{} or @astrofrog'.format(username)

    repo.create_pull(title='Update astropy-helpers to {0}'.format(HELPERS_TAG),
                     body='This is an automated update of the astropy-helpers '
                          'submodule to {0}. This includes both the update of '
                          'the astropy-helpers sub-module, and the '
                          '``ah_bootstrap.py`` file, if needed.\n\n*This is '
                          'intended to be helpful, but if you would prefer to '
                          'manage these updates yourself, or if you notice any '
                          'issues with this automated update, please let '
                          '{1} know!*'.format(HELPERS_TAG, report_user),
                     base='master',
                     head='{0}:{1}'.format(fork.owner.login, BRANCH))

START_DIR = os.path.abspath('.')

registry = requests.get("http://astropy.org/affiliated/registry.json").json()

repositories = []
for package in registry['packages']:
    if 'github' not in package['repo_url']:
        continue
    owner, repository = package['repo_url'].split('/')[-2:]
    if '.git' in repository:
        repository = repository.replace('.git', '')
    repositories.append((owner, repository))

# Add a few repositories manually on request
repositories.extend([('chandra-marx', 'marxs'),
                     ('hamogu', 'astrospec'),
                     ('hamogu', 'psfsubtraction'),
                     ('astropy', 'regions'),
                     ('astropy', 'astropy-healpix'),
                     ('astropy', 'saba'),
                     ('sunpy', 'sunpy'),
                     ('chianti-atomic', 'ChiantiPy'),
                     ('pyspeckit', 'pyspeckit'),
                     ('spacetelescope', 'astroimtools'),
                     ('spacetelescope', 'synphot_refactor'),
                     ('spacetelescope', 'stsynphot_refactor'),
                     ('spacetelescope', 'stginga'),
                     ('stsci-jwst', 'wss_tools'),
                     ('StingraySoftware', 'HENDRICS'),
                     ('StingraySoftware', 'stingray'),
                     ('hipspy', 'hips'),
                     ('desihub', 'specsim'),
                     ('dkirkby', 'speclite')])

# Remove duplicates
repositories = sorted(set(repositories))

for owner, repository in repositories:
    repo = gh.get_repo("{0}/{1}".format(owner, repository))
    fork = ensure_fork_exists(repo)
    try:
        open_pull_request(fork, repo)
    except:
        pass
    finally:
        os.chdir(START_DIR)
