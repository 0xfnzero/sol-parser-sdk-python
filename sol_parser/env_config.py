"""Environment and CLI helpers aligned with sol-parser-sdk-nodejs (GRPC_URL, .env, flags)."""

from __future__ import annotations

import os
import sys
from typing import Optional, Sequence, Tuple


def load_dotenv_silent(dotenv_path: Optional[str] = None) -> bool:
    """Load ``.env`` from the current working directory (or ``dotenv_path``).

    Does **not** override variables already set in the process environment
    (same idea as ``dotenv`` on Node). Returns ``False`` if ``python-dotenv``
    is not installed.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(dotenv_path, override=False)
    return True


def _first_nonempty(*values: Optional[str]) -> str:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def _parse_grpc_cli(argv: Sequence[str]) -> tuple[Optional[str], Optional[str]]:
    """Parse ``--grpc-url``, ``--grpc-token``, and short aliases from *argv*."""
    url: Optional[str] = None
    token: Optional[str] = None
    i = 0
    n = len(argv)
    while i < n:
        a = argv[i]
        if a in ("--grpc-url", "--grpc-endpoint", "-g") and i + 1 < n:
            url = argv[i + 1].strip()
            i += 2
            continue
        if a.startswith("--grpc-url="):
            url = a.split("=", 1)[1].strip()
            i += 1
            continue
        if a.startswith("--grpc-endpoint="):
            url = a.split("=", 1)[1].strip()
            i += 1
            continue
        if a in ("--grpc-token", "--token", "-t") and i + 1 < n:
            token = argv[i + 1].strip()
            i += 2
            continue
        if a.startswith("--grpc-token="):
            token = a.split("=", 1)[1].strip()
            i += 1
            continue
        if a.startswith("--token="):
            token = a.split("=", 1)[1].strip()
            i += 1
            continue
        i += 1
    return url, token


def parse_grpc_credentials(
    argv: Optional[Sequence[str]] = None,
    *,
    default_endpoint: str = "solana-yellowstone-grpc.publicnode.com:443",
    require_token: bool = False,
) -> Tuple[str, str]:
    """Resolve Yellowstone gRPC URL and x-token.

    **Precedence (each field):** CLI flags > ``GRPC_URL`` / ``GRPC_TOKEN`` >
    legacy ``GEYSER_ENDPOINT`` / ``GEYSER_API_TOKEN`` > *default_endpoint* (URL only).

    Call :func:`load_dotenv_silent` first so a project-local ``.env`` is applied.

    :param require_token: If ``True``, print an error and ``sys.exit(1)`` when the
        token is still empty after resolution.
    """
    load_dotenv_silent()
    cli_url, cli_token = _parse_grpc_cli(list(argv) if argv is not None else [])
    url = _first_nonempty(
        cli_url,
        os.environ.get("GRPC_URL"),
        os.environ.get("GEYSER_ENDPOINT"),
        default_endpoint,
    )
    token = _first_nonempty(
        cli_token,
        os.environ.get("GRPC_TOKEN"),
        os.environ.get("GEYSER_API_TOKEN"),
    )
    if require_token and not token:
        print(
            "Error: GRPC_TOKEN is required (x-token for the gRPC endpoint).\n"
            "  Copy .env.example to .env in the package root and set GRPC_TOKEN, or:\n"
            "  export GRPC_TOKEN=<your_token>\n"
            "  You can also pass: --grpc-token <token>  or  --token=<token>",
            file=sys.stderr,
        )
        sys.exit(1)
    return url, token


def require_grpc_env(argv: Optional[Sequence[str]] = None) -> Tuple[str, str]:
    """Require both gRPC URL and token (same contract as Node ``scripts/grpc_env.ts``).

    No default URL: set ``GRPC_URL`` / ``GEYSER_ENDPOINT`` or ``--grpc-url``.
    """
    load_dotenv_silent()
    argv = list(sys.argv[1:] if argv is None else argv)
    cli_url, cli_token = _parse_grpc_cli(argv)
    url = _first_nonempty(cli_url, os.environ.get("GRPC_URL"), os.environ.get("GEYSER_ENDPOINT"))
    token = _first_nonempty(cli_token, os.environ.get("GRPC_TOKEN"), os.environ.get("GEYSER_API_TOKEN"))
    if not url:
        print(
            "Error: GRPC_URL is required.\n"
            "  Copy .env.example to .env in the package root and set GRPC_URL (and GRPC_TOKEN), or:\n"
            "  export GRPC_URL=https://your-yellowstone-host:443\n"
            "  CLI: --grpc-url <url>  or  -g <url>",
            file=sys.stderr,
        )
        sys.exit(1)
    if not token:
        print(
            "Error: GRPC_TOKEN is required (x-token header for the gRPC endpoint).\n"
            "  Copy .env.example to .env in the package root and set GRPC_TOKEN, or:\n"
            "  export GRPC_TOKEN=<your_token>",
            file=sys.stderr,
        )
        sys.exit(1)
    return url, token


def parse_shredstream_url(
    argv: Optional[Sequence[str]] = None,
    *,
    default_url: str = "http://127.0.0.1:10800",
) -> str:
    """ShredStream HTTP endpoint: ``--url`` / ``-u`` / ``--endpoint=`` > ``SHREDSTREAM_URL`` / ``SHRED_URL`` > default."""
    load_dotenv_silent()
    argv = list(sys.argv[1:] if argv is None else argv)
    for i, a in enumerate(argv):
        if a in ("--url", "-u", "--endpoint") and i + 1 < len(argv):
            v = argv[i + 1].strip()
            if v:
                return v
        if a.startswith("--url="):
            return a[6:].strip()
        if a.startswith("--endpoint="):
            return a[11:].strip()
    env_url = _first_nonempty(os.environ.get("SHREDSTREAM_URL"), os.environ.get("SHRED_URL"))
    return env_url or default_url


def parse_optional_rpc_url(
    argv: Optional[Sequence[str]] = None,
    *,
    default_rpc: str = "https://api.mainnet-beta.solana.com",
) -> str:
    """``--rpc`` / ``-r`` / ``--rpc=`` > ``RPC_URL`` > *default_rpc*."""
    load_dotenv_silent()
    argv = list(sys.argv[1:] if argv is None else argv)
    for i, a in enumerate(argv):
        if a in ("--rpc", "-r") and i + 1 < len(argv):
            v = argv[i + 1].strip()
            if v:
                return v
        if a.startswith("--rpc="):
            return a[6:].strip()
    return _first_nonempty(os.environ.get("RPC_URL")) or default_rpc


def _parse_sig_cli(argv: Sequence[str]) -> Optional[str]:
    for i, a in enumerate(argv):
        if a in ("--sig", "-s") and i + 1 < len(argv):
            v = argv[i + 1].strip()
            if v:
                return v
        if a.startswith("--sig="):
            return a[6:].strip()
    return None


def parse_rpc_and_tx_signature(
    argv: Optional[Sequence[str]] = None,
    *,
    default_signature: str,
) -> Tuple[str, str]:
    """For ``parse_tx_by_signature``-style tools: RPC URL + transaction signature."""
    load_dotenv_silent()
    argv = list(sys.argv[1:] if argv is None else argv)
    rpc = parse_optional_rpc_url(argv)
    sig = _first_nonempty(_parse_sig_cli(argv), os.environ.get("TX_SIGNATURE"), default_signature)
    return rpc, sig
