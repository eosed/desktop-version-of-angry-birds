"""Desktop Angry Birds entry point.

Run without arguments to open the toolbar.  `--watchdog` is the crash-recovery
child spawned by the running game; it restores the hidden desktop icons if the
game process dies unexpectedly.
"""
import sys


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == '--watchdog':
        from dab.watchdog import main as watchdog_main
        watchdog_main(sys.argv[2:])
        return
    from dab.ui import main as ui_main
    ui_main()


if __name__ == '__main__':
    main()
