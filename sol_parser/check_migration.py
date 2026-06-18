"""Python 迁移门禁入口（与 TS `npm run check:migration` 中的 discriminator 交叉校验步骤对应）。"""

from __future__ import annotations

import sys

from .u128_parity import run_all_u128_checks
from .verify_discriminators import main as _verify_main
from .event_type_parity import run_event_type_parity_check


def main() -> None:
    if _verify_main() != 0:
        sys.exit(1)
    if run_event_type_parity_check() != 0:
        sys.exit(1)
    sys.exit(run_all_u128_checks())


if __name__ == "__main__":
    main()
