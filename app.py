from __future__ import annotations

import sys

from ghost_builder.ui import GhostApp


def main() -> int:
    smoke = "--smoke-test" in sys.argv
    app = GhostApp(smoke_test=smoke)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
