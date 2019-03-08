#!/usr/bin/env python3

import argparse
import subprocess
import sys

HTTP_PROXY_PORT = 8888


def setup_http_proxy(host, user):
    """
    Setup the http proxy through ssh. This is useful when the remote machine
    has http and https filtered.
    """

    try:
        print("Starting tinyproxy.service.")
        proc = subprocess.run(
            ["sudo", "systemctl", "start", "tinyproxy.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        proc.check_returncode()
        print(proc.stdout.decode('utf-8'))
    except subprocess.CalledProcessError:
        print(proc.stderr.decode('utf-8'))
        sys.exit(proc.returncode)


def forge_ssh_command(host, http_proxy, user, remote_port_forwarding):
    """
    Forge the ssh command.
    """

    ssh_command = ["ssh", "-4"]

    if http_proxy is not None:
        ssh_command += ["-o", "Controlpath=none"]

    if remote_port_forwarding is not None:
        ssh_command += ["-R", remote_port_forwarding]

    if user is not None:
        ssh_command += ["-l", user]

    ssh_command += [host]

    return ssh_command


def install_python(ssh_command, http_proxy):
    """
    Installs python2 on host.
    """

    if http_proxy:
        sh_command = ["sh -s " + str(HTTP_PROXY_PORT)]
    else:
        sh_command = ["sh -s "]

    # Install python
    with subprocess.Popen(ssh_command + sh_command,
                          stdin=subprocess.PIPE) as process:
        with open('install-python.sh', 'rb') as install_package:
            process.stdin.write(install_package.read())
            process.communicate()


def get_system(ssh_command):
    """
    Get the host system in order set the python interpreter for ansible.
    """

    # Query the system type. This will help in calling ansible
    try:
        proc = subprocess.run(
            ssh_command +
            ["python -c 'import platform ; print(platform.system())'"],
            stdout=subprocess.PIPE)
        proc.check_returncode()
        system = proc.stdout[:-1]
        return system
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        sys.exit(-1)


def forge_ansible_command(ask_pass, host, user, verbosity, system):
    """
    Forge the ansible command. This is mostly used to set the ansible python
    interpreter on BSD systems.
    """

    # Call ansible
    ansible_command = ["ansible-playbook"]

    if ask_pass:
        ansible_command += ["-k"]

    if user is not None:
        if user == "root":
            ansible_command += ["-u", "root"]
        else:
            ansible_command += ["-b", "-u", user]

    ansible_command += ["-i", host + ","]

    if verbosity > 0:
        ansible_command += ["-" + "v" * verbosity]

    if system == b'OpenBSD' or system == b'FreeBSD':
        ansible_command += [
            "-e ansible_python_interpreter='/usr/local/bin/python'"
        ]

    return ansible_command


def run_playbook(ansible_command):
    """
    Runs a playbook on target host.
    """

    try:
        proc = subprocess.run(ansible_command,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        proc.check_returncode()
        print(proc.stdout.decode('utf-8'))
    except subprocess.CalledProcessError:
        # Ansible prints errors on stdout
        print(proc.stdout.decode('utf-8'))
        print(proc.stderr.decode('utf-8'))
        sys.exit(proc.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bootstrap a server.')

    parser.add_argument("host", help="Host to bootstrap")
    parser.add_argument("--clean",
                        help="Remove packages on target host",
                        action='store_true')
    parser.add_argument("--http-proxy",
                        help="Use a local http proxy. Useful when\
                        outgoing ports 80 and 443 and filtered.",
                        action='store_true')
    parser.add_argument("--key",
                        help="Add this ssh key to root authorized_keys")
    parser.add_argument("-k",
                        "--ask-pass",
                        help="Ask for connection password",
                        action='store_true')
    parser.add_argument("-u",
                        "--user",
                        help="Connect as this user (default=None)",
                        nargs='?')
    parser.add_argument("-v",
                        "--verbose",
                        help="Verbose mode (-vvv for\
                        more, -vvvv to enable connection debugging)",
                        action='count',
                        dest='verbosity',
                        default=0)

    args = parser.parse_args()

    # Setup the http proxy first thing if needed
    if args.http_proxy:
        setup_http_proxy(args.host, args.user)
        remote_port_forwarding = str(HTTP_PROXY_PORT) + ":127.0.0.1:" + str(
            HTTP_PROXY_PORT)
    else:
        remote_port_forwarding = None

    ssh_command = forge_ssh_command(args.host, args.http_proxy, args.user,
                                    remote_port_forwarding)

    install_python(ssh_command, args.http_proxy)

    system = get_system(ssh_command)
    ansible_command = forge_ansible_command(args.ask_pass, args.host,
                                            args.user, args.verbosity, system)

    # Bootstraps target host by running a basic Ansible playbook that installs
    # essential packages and configures essential settings.
    run_playbook(ansible_command + ["bootstrap.yml"])

    if args.clean:
        # Clean a host by running a basic Ansible playbook that removes
        # non-essential/duplicate-functionnality packages.
        run_playbook(ansible_command + ["clean.yml"])

    if args.key is not None:
        run_playbook(ansible_command + ["-e", "ssh_key=" + args.key, "key.yml"])
