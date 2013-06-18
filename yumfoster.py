#! /usr/bin/env python

import yum
import yum.rpmtrans
import os
import errno
import sys
import subprocess
import tty
import termios

KEEPERSFILE="/var/lib/yumfoster/keepers"

def pname(pkg):
    return "%s.%s" % (pkg.name, pkg.arch)


def fname(pkg):
    return "%s-%s-%s.%s" % (pkg.name, pkg.version,
                            pkg.release, pkg.arch)


def remove_packages(pkgs):
    args = ["rpm", "-evh"] + [fname(p) for p in pkgs]
    subprocess.check_call(args)

class YumFoster(yum.YumBase):
    def __init__(self):
        yum.YumBase.__init__(self)

        try:
            f = open(KEEPERSFILE)
            klist = f.readlines()
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            klist = []

        self.keepers = set(s.strip() for s in klist)

    def interact(self):
        droppers = set()
        abort = None

        for pkg in self.rpmdb:
            n = pname(pkg)

            if pkg.requiring_packages():
                continue
            if n in self.keepers:
                continue

            while True:
                sys.stdout.write("Keep %s [Synixq]? " % n)
                act = sys.stdin.read(1).lower()
                sys.stdout.write(act + '\n')

                if (act == 's') or (not act):
                    break
                elif act == 'y':
                    self.keepers.add(n)
                    break
                elif act == 'n':
                    droppers.add(pkg)
                    break
                elif act == 'i':
                    print pkg.description
                elif act == 'x':
                    abort = False
                    break
                elif act == 'q':
                    abort = True
                    break

            if abort is not None:
                break

        if not abort:
            # Update keepers file
            f = open(KEEPERSFILE, "w")
            for n in sorted(self.keepers):
                f.write(n + '\n')
            f.close()

            if os.geteuid() != 0:
                print "Error: Cannot remove packages as a user, must be root"
                sys.exit(1)

            remove_packages(droppers)

oldtermios = None
try:
    if sys.stdin.isatty():
        oldtermios = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)

    yf = YumFoster()
    yf.interact()
finally:
    if oldtermios is not None:
        termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, oldtermios)
    

