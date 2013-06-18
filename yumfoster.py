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


def remove_packages(pkgs):
    args = ["rpm", "-evh"] + [str(p) for p in pkgs]
    subprocess.check_call(args)

class YumFoster(yum.YumBase):
    def __init__(self):
        yum.YumBase.__init__(self)

        print "Loading keepers...",
        try:
            f = open(KEEPERSFILE)
            klist = f.readlines()
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            klist = []

        self.keepers = set(s.strip() for s in klist)
        print "done."

        print "Computing package requirements..."
        self.reqpkg = {}
        for pkg in self.rpmdb:
            self.reqpkg[pkg] = set(pkg.requiring_packages())
        self.candidates = set(p for p in self.reqpkg if not self.reqpkg[p])

        self.keeping = {}
        for pkg in self.candidates:
            self.keeping[pkg] = self.keepclose(pkg)
        print "done."


    def keepclose(self, pkg):
        keeping = set((pkg,))
        while True:
            n = len(keeping)
            for p, req in self.reqpkg.items():
                if req and (req <= keeping):
                    keeping.add(p)
            if len(keeping) == n:
                break
        return keeping


    def interact(self):
        droppers = set()
        abort = None

        for pkg in self.candidates:
            n = pname(pkg)

            if n in self.keepers:
                continue

            while True:
                k = self.keeping[pkg]
                if len(k) > 1:
                    sys.stdout.write("%s is keeping %d packages installed: %s\n"
                                     % (str(pkg), len(k) - 1,
                                        ", ".join(str(p) for p in k if p is not pkg)))

                sys.stdout.write("Keep %s [Synixq] ? " % str(pkg))
                act = sys.stdin.read(1).lower()
                sys.stdout.write(act + '\n\n')

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
    

