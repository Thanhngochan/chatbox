import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn

os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tests"))

import fake_anthropic  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_until_up(url, seconds=20):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Could not start {url}")


@pytest.fixture(scope="session")
def fake_claude():
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(fake_anthropic.app, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    _wait_until_up(url + "/docs")
    yield url
    server.should_exit = True


def start_server(claude_url, **extra_env):
    """Start the real chat server in a subprocess, pointed at `claude_url`."""
    port = free_port()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "CLAUDE_"))}
    env.update({
        "ANTHROPIC_BASE_URL": claude_url or "http://127.0.0.1:9",
        "ANTHROPIC_API_KEY": "sk-ant-fake",
        "RATE_LIMIT_PER_MINUTE": "1000",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        **extra_env,
    })
    if env.get("ANTHROPIC_API_KEY") == "":
        del env["ANTHROPIC_API_KEY"]
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port)],
        cwd=ROOT / "server", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_up(url + "/api/health")
    except RuntimeError:
        proc.kill()
        raise RuntimeError(proc.stdout.read())
    return proc, url


@pytest.fixture(scope="session")
def server(fake_claude):
    proc, url = start_server(fake_claude)
    yield url
    proc.terminate()


@pytest.fixture
def claude_requests():
    fake_anthropic.REQUESTS.clear()
    return fake_anthropic.REQUESTS
