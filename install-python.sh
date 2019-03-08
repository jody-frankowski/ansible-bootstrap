#!/bin/sh

if [ ! -z $1 ] ; then
    export http_proxy=http://127.0.0.1:$1/
    export https_proxy=http://127.0.0.1:$1/
fi

if [ `id -u` -ne 0 ] ; then
    if command -v doas > /dev/null 2>&1 ; then
        prefix="doas"
    elif command -v sudo > /dev/null 2>&1 ; then
        prefix="sudo"
    else
        echo "Neither doas no sudo exist."
        exit 1
    fi
else
    prefix=""
fi

if command -v python > /dev/null 2>&1 ; then
    if [ $(python -V 2>&1 | cut -d' ' -f 2 | cut -d. -f 1) -ne 2 ] ; then
        echo "Python exists but doesn't point to python2."
        exit 1
    else
        exit 0
    fi
fi

# Try all the possible installers and if one succeeds exit right away.
$prefix dnf install python 2>/dev/null && exit 0
$prefix pacman install python2 2>/dev/null && exit 0
$prefix yum install python 2>/dev/null && exit 0

if [ -f /etc/debian_version ] ; then
    $prefix apt-get install python > /dev/null 2>&1 && exit 0
fi

if [ $(uname -s) = "FreeBSD" ]; then
    version=$(uname -r | cut -d- -f 1)

    case $version in
        9.0)
            export PACKAGESITE=http://ftp-archive.freebsd.org/pub/FreeBSD-Archive/old-releases/$(uname -m)/$(uname -r|cut -d'-' -f1)-RELEASE/packages/Latest/
            $prefix pkg_add -r python27
            ;;
        *)
            $prefix pkg install -y python27
            ;;
    esac

    if [ ! -e /usr/local/bin/python  ] ; then
        $prefix ln -sf /usr/local/bin/python2.7 /usr/local/bin/python > /dev/null
    fi

    exit 0
fi

if [ $(uname -s) = "OpenBSD" ]; then
    export PKG_PATH="http://ftp.eu.openbsd.org/pub/OpenBSD/$(uname -r)/packages/$(uname -m)/"
    package_name=$(pkg_info -Q python-- | grep -- '-2.7' | awk '{print $1}')

    $prefix pkg_add "$package_name"

    if [ ! -e /usr/local/bin/python  ] ; then
        $prefix ln -sf /usr/local/bin/python2.7 /usr/local/bin/python > /dev/null
    fi

    exit 0
fi

exit 1
