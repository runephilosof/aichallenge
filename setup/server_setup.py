#!/usr/bin/python
#
# Sets up a contest main server.
#
#

import getpass
import os
import os.path
import pwd
import sys
from optparse import OptionParser

import create_worker_archive
from install_tools import CD, Environ, install_apt_packages, run_cmd, CmdError, check_ubuntu_version
from install_tools import get_choice, get_password
from socket import getfqdn

TEMPLATE_DIR = os.path.dirname(os.path.abspath(__file__))

def install_manager_packages():
    """ Install basic system packages required for the manager """
    pkg_list = ["python-mysqldb", "make", "git", "cron", "unzip", "sudo"]
    install_apt_packages(pkg_list)

def install_website_packages():
    """ Install system packages required for the website """
    pkg_list = ["memcached", "php-memcache", "zip", "nodejs",
            "cvs", "openjdk-11-jdk", "ant",
            "python-setuptools", "dvipng", "texlive-latex-base"]
    run_cmd("curl -sL https://deb.nodesource.com/setup_12.x | sudo -E bash -")
    install_apt_packages(pkg_list)

def setup_base_files(opts):
    """ Setup all the contest specific files and directories """
    if not os.path.exists(opts.upload_dir):
        os.mkdir(opts.upload_dir)
        run_cmd("chown {0}:www-data {1}".format(opts.username, opts.upload_dir))
        os.chmod(opts.upload_dir, 0775)
    if not os.path.exists(opts.map_dir):
        os.mkdir(opts.map_dir)
        run_cmd("chown {0}:www-data {1}".format(opts.username, opts.map_dir))
    if not os.path.exists(opts.replay_dir):
        os.mkdir(opts.replay_dir)
        run_cmd("chown {0}:www-data {1}".format(opts.username, opts.replay_dir))
        os.chmod(opts.replay_dir, 0775)
    if not os.path.exists(opts.log_dir):
        os.mkdir(opts.log_dir)
        run_cmd("chown {0}:www-data {1}".format(opts.username, opts.log_dir))
        os.chmod(opts.log_dir, 0775)
    si_filename = os.path.join(TEMPLATE_DIR, "server_info.py.template")
    with open(si_filename, 'r') as si_file:
        si_template = si_file.read()
    si_contents = si_template.format(contest_root=opts.root_dir,
            database_user=opts.database_user,
            database_password=opts.database_password,
            database_name=opts.database_name,
            map_dir=opts.map_dir, upload_dir=opts.upload_dir,
            log_dir=opts.log_dir)
    manager_dir = os.path.join(opts.local_repo, "manager")
    with CD(manager_dir):
        if not os.path.exists("server_info.py"):
            with open("server_info.py", "w") as si_file:
                si_file.write(si_contents)
            run_cmd("chown {0}:{0} server_info.py".format(opts.username))
    if os.stat(opts.local_repo).st_uid != pwd.getpwnam(opts.username).pw_uid:
        run_cmd("chown -R {0}:{0} {1}".format(opts.username, opts.local_repo))

def setup_language_repo(opts):
    """ Download languages not part of OS distribution locally for workers """
    download_dir = os.path.join(opts.local_repo, "website/langs")
    try:
        os.mkdir(download_dir)
    except OSError:
        if not os.path.isdir(download_dir):
            raise
    retrieve_cmd = os.path.join(opts.local_repo, "setup/retrieve_languages.py")
    run_cmd("%s %s" % (retrieve_cmd, download_dir))

def setup_website(opts):
    """ Configure apache to serve the website and set a server_info.php """
    website_root = os.path.join(opts.local_repo, "website")
    #si_filename = os.path.join(TEMPLATE_DIR, "server_info.php.template")
    #with open(si_filename, 'r') as si_file:
    #    si_template = si_file.read()
    #si_contents = si_template.format(upload_dir=opts.upload_dir,
    #       map_dir=opts.map_dir, replay_dir=opts.replay_dir,
    #       log_dir=opts.log_dir, repo_dir=opts.local_repo,
    #       database_user=opts.database_user,
    #       database_password=opts.database_password,
    #       database_name=opts.database_name,
    #       api_url=opts.website_hostname
    #       )
    #with CD(website_root):
    #   if not os.path.exists("server_info.php"):
    #       with open("server_info.php", "w") as si_file:
    #           si_file.write(si_contents)
    with CD(website_root):
        # setup pygments flavored markdown
        #run_cmd("easy_install ElementTree")
        #run_cmd("easy_install Markdown")
        run_cmd("easy_install Pygments")
        if not os.path.exists("aichallenge.wiki"):
            run_cmd("git clone git://github.com/aichallenge/aichallenge.wiki.git")
        #    run_cmd("python setup.py")
    with CD(os.path.join(opts.local_repo, "ants/dist/starter_bots")):
        run_cmd("make")
        run_cmd("make install")
    if not os.path.exists(os.path.join(website_root, "worker-src.tgz")):
        create_worker_archive.main(website_root)
    visualizer_path = os.path.join(opts.local_repo, "ants/visualizer")
    plugin_path = "/usr/share/icedtea-web/plugin.jar"
    if not os.path.exists(os.path.join(website_root, "visualizer")):
        with CD(visualizer_path):
            run_cmd("ant deploy -Djava.plugin=%s -Ddeploy.path=%s"
                    % (plugin_path, website_root))
    setup_language_repo(opts)
    run_cmd("chown -R {0}:{0} {1}".format(opts.username, website_root))

def interactive_options(options):
    print "Warning: This script is meant to be run as root and will make changes to the configuration of the machine it is run on."
    resp = raw_input("Are you sure you want to continue (yes/no)? [no] ")
    if resp != "yes":
        sys.exit(1)
    pkg_only = get_choice("Only install system packages?")
    options.packages_only = pkg_only
    if pkg_only:
        print "Only system packages will be installed, no further setup will be done."
        return
    user = options.username
    user = raw_input("Contest username? [%s] " % (user,))
    options.username = user if user else options.username
    options.database_root_password = get_password("database root")
    db_user = options.username
    db_user = raw_input("Contest database username? [%s] " % (db_user,))
    options.database_user = db_user if db_user else options.username
    options.database_password = get_password("contest database")
    db_name = options.database_name
    db_name = raw_input("Name of contest database? [%s] " % (db_name,))
    options.database_name = db_name if db_name else options.database_name
    root_dir = options.root_dir
    root_dir = raw_input("Contest root directory? [%s] " % (root_dir,))
    options.root_dir = root_dir if root_dir else options.root_dir
    repo_dir = options.local_repo
    repo_dir = raw_input("Directory of source repository? [%s] " % (repo_dir,))
    options.local_repo = repo_dir if repo_dir else options.local_repo
    upload_dir = options.upload_dir
    upload_dir = raw_input("Directory of uploaded submissions? [%s] " % (upload_dir,))
    options.upload_dir = upload_dir if upload_dir else options.upload_dir
    map_dir = options.map_dir
    map_dir = raw_input("Directory of game maps? [%s] " % (map_dir,))
    options.map_dir = map_dir if map_dir else options.map_dir
    replay_dir = options.replay_dir
    replay_dir = raw_input("Directory of game replays? [%s] " % (replay_dir,))
    options.replay_dir = replay_dir if replay_dir else options.replay_dir
    webname = options.website_hostname
    webname = raw_input("Website hostname? [%s] " % (webname,))
    options.website_hostname = webname if webname else options.website_hostname
    default = options.website_as_default
    default = get_choice("Make contest site the default website?", default)
    options.website_as_default = default

def get_options(argv):
    """ Get all the options required for the installation """
    current_username = os.environ.get("SUDO_USER", getpass.getuser())
    # find default paths
    top_level = os.path.abspath(os.path.join(TEMPLATE_DIR, ".."))
    root_dir = os.path.split(top_level)[0]
    map_dir = os.path.join(root_dir, 'maps')
    replay_dir = os.path.join(root_dir, 'games')
    upload_dir = os.path.join(root_dir, 'uploads')
    compiled_dir = os.path.join(root_dir, 'compiled')
    log_dir = os.path.join(root_dir, 'logs')
    default_install = {
        "installs": set([install_manager_packages, install_website_packages]),
        "packages_only": False,
        "username": current_username,
        "database_root_password": "",
        "database_user": current_username, "database_password": "",
        "database_name": "aichallenge",
        "root_dir": root_dir,
        "map_dir": map_dir,
        "replay_dir": replay_dir,
        "upload_dir": upload_dir,
        "compiled_dir": compiled_dir,
        "log_dir": log_dir,
        "local_repo": top_level,
        "website_as_default": False,
        "website_hostname": '.'.join(getfqdn().split('.')[1:]),
        "interactive": True,
    }
    full_install = {
        "website_as_default": True,
        "interactive": False,
    }

    def replace_options(option, opt_str, value, parser, replacements):
        for option, value in replacements.items():
            setattr(parser.values, option, value)

    parser = OptionParser()
    parser.set_defaults(**default_install)
    parser.add_option("--take-over-server", action="callback",
            callback=replace_options, callback_args = (full_install,),
            help="Do a complete install as used for the contest")
    parser.add_option("-r", "--contest_root", action="store", type="string",
            dest="root_dir",
            help="Set the directory where all contest files live")
    parser.add_option("--packages-only", action="store_true",
            dest="packages_only",
            help="Only install required packages and exit")
    parser.add_option("-u", "--username", action="store", dest="username",
            help="User account for the contest")
    options, args = parser.parse_args(argv)
    if options.interactive:
        interactive_options(options)
        confirm = raw_input("Run setup as configured above (yes/no)? [no] ")
        if confirm != "yes":
            sys.exit(1)
    return options

def main(argv=["server_setup.py"]):
    opts = get_options(argv)
    with Environ("DEBIAN_FRONTEND", "noninteractive"):
        for install in opts.installs:
            install()
    if opts.packages_only:
        return
    setup_base_files(opts)
    setup_website(opts)

if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        print('Setup Aborted')
