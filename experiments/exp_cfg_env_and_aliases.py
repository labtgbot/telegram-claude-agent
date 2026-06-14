"""
EXPERIMENT 2 (subprocess-isolated): With the REAL project Settings class
(bot.config.Settings), verify end-to-end in clean child processes:
  (a) uppercase env vars map to lowercase fields (case_sensitive=False)
  (b) a .env file in cwd is actually read (fills required fields)
  (c) process env overrides .env (precedence)

Each case runs in its own `python -c` subprocess so the module-level
`settings = Settings()` in bot/config.py does not interfere.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def run_child(code: str, *, cwd: Path, extra_env: dict, drop: list) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    for d in drop:
        env.pop(d, None)
    env.update(extra_env)
    env["PYTHONPATH"] = str(REPO)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )


DROP = ["FREE_CLAUDE_BASE_URL", "FREE_CLAUDE_AUTH_TOKEN",
        "FREE_CLAUDE_DEFAULT_MODEL", "TELEGRAM_BOT_TOKEN",
        "RATE_LIMIT_REQUESTS_PER_MINUTE", "LOG_LEVEL"]

PRINT_CODE = (
    "from bot.config import Settings;"
    "s=Settings();"
    "print('BASE', s.free_claude_base_url);"
    "print('RATE', s.rate_limit_requests_per_minute)"
)


def test_a():
    print("\n=== (a) UPPERCASE env vars -> lowercase fields ===")
    r = run_child(
        PRINT_CODE, cwd=REPO,
        extra_env={
            "FREE_CLAUDE_BASE_URL": "http://env.example",
            "FREE_CLAUDE_AUTH_TOKEN": "env_auth",
            "FREE_CLAUDE_DEFAULT_MODEL": "env_model",
            "TELEGRAM_BOT_TOKEN": "123456:ENVtoken_abcdefghijklmnopqrstuvw",
            "RATE_LIMIT_REQUESTS_PER_MINUTE": "42",
        },
        drop=DROP,
    )
    print(r.stdout.strip() or r.stderr.strip()[:400])
    ok = "BASE http://env.example" in r.stdout and "RATE 42" in r.stdout
    print(f"  RESULT: uppercase env mapping works = {ok}")
    return ok


def test_b():
    print("\n=== (b) .env in cwd is read (no process env for required fields) ===")
    tmp = Path(tempfile.mkdtemp(prefix="exp_cfg_b_"))
    (tmp / ".env").write_text(
        "FREE_CLAUDE_BASE_URL=http://dotenv-b.example\n"
        "FREE_CLAUDE_AUTH_TOKEN=dotenv_auth\n"
        "FREE_CLAUDE_DEFAULT_MODEL=dotenv_model\n"
        "TELEGRAM_BOT_TOKEN=123456:DOTENVtoken_abcdefghijklmnopqrstuv\n"
        "RATE_LIMIT_REQUESTS_PER_MINUTE=7\n"
    )
    r = run_child(PRINT_CODE, cwd=tmp, extra_env={}, drop=DROP)
    print(r.stdout.strip() or r.stderr.strip()[:400])
    ok = "BASE http://dotenv-b.example" in r.stdout and "RATE 7" in r.stdout
    print(f"  RESULT: .env actually read from cwd = {ok}")
    return ok


def test_b2_other_cwd():
    print("\n=== (b2) .env NOT read if cwd differs (relative path pitfall) ===")
    tmp_env = Path(tempfile.mkdtemp(prefix="exp_cfg_b2env_"))
    (tmp_env / ".env").write_text(
        "FREE_CLAUDE_BASE_URL=http://dotenv-elsewhere.example\n"
        "FREE_CLAUDE_AUTH_TOKEN=dotenv_auth\n"
        "FREE_CLAUDE_DEFAULT_MODEL=dotenv_model\n"
        "TELEGRAM_BOT_TOKEN=123456:DOTENVtoken_abcdefghijklmnopqrstuv\n"
    )
    other = Path(tempfile.mkdtemp(prefix="exp_cfg_b2cwd_"))  # no .env here
    r = run_child(PRINT_CODE, cwd=other, extra_env={}, drop=DROP)
    crashed = r.returncode != 0
    print(f"  cwd has .env? {(other / '.env').exists()} ; child exit={r.returncode}")
    print("  stderr head:", (r.stderr.strip().splitlines() or ["<none>"])[-1][:200])
    print(f"  RESULT: missing-cwd-.env -> crash on import = {crashed}")
    return crashed


def test_c():
    print("\n=== (c) process env overrides .env ===")
    tmp = Path(tempfile.mkdtemp(prefix="exp_cfg_c_"))
    (tmp / ".env").write_text(
        "FREE_CLAUDE_BASE_URL=http://dotenv-c.example\n"
        "FREE_CLAUDE_AUTH_TOKEN=dotenv_auth\n"
        "FREE_CLAUDE_DEFAULT_MODEL=dotenv_model\n"
        "TELEGRAM_BOT_TOKEN=123456:DOTENVtoken_abcdefghijklmnopqrstuv\n"
    )
    r = run_child(
        PRINT_CODE, cwd=tmp,
        extra_env={"FREE_CLAUDE_BASE_URL": "http://process-env.example"},
        drop=DROP,
    )
    print(r.stdout.strip() or r.stderr.strip()[:400])
    ok = "BASE http://process-env.example" in r.stdout
    print(f"  RESULT: process env wins over .env = {ok}")
    return ok


def main():
    results = {
        "uppercase_env": test_a(),
        "dotenv_read": test_b(),
        "dotenv_relative_pitfall_crash": test_b2_other_cwd(),
        "precedence": test_c(),
    }
    print("\n=== SUMMARY ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
