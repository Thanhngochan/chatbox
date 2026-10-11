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
GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "server"))
sys.path.insert(0, str(GOC / "tests"))

import fake_anthropic  # noqa: E402


def _cong_trong():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _cho(url, giay=20):
    het_han = time.time() + giay
    while time.time() < het_han:
        try:
            if httpx.get(url, timeout=1).status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"Không khởi động được {url}")


@pytest.fixture(scope="session")
def claude_gia():
    cong = _cong_trong()
    server = uvicorn.Server(uvicorn.Config(fake_anthropic.app, port=cong, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{cong}"
    _cho(url + "/docs")
    yield url
    server.should_exit = True


def chay_server(claude_url, **env_them):
    cong = _cong_trong()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ANTHROPIC_", "CLAUDE_"))}
    env.update({
        "ANTHROPIC_BASE_URL": claude_url or "http://127.0.0.1:9",
        "ANTHROPIC_API_KEY": "sk-ant-gia",
        "RATE_LIMIT_PER_MINUTE": "1000",
        "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
        **env_them,
    })
    if env.get("ANTHROPIC_API_KEY") == "":
        del env["ANTHROPIC_API_KEY"]
    p = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(cong)],
        cwd=GOC / "server", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    url = f"http://127.0.0.1:{cong}"
    try:
        _cho(url + "/api/health")
    except RuntimeError:
        p.kill()
        raise RuntimeError(p.stdout.read())
    return p, url


@pytest.fixture(scope="session")
def server(claude_gia):
    p, url = chay_server(claude_gia)
    yield url
    p.terminate()


@pytest.fixture
def yeu_cau_claude():
    fake_anthropic.YEU_CAU.clear()
    return fake_anthropic.YEU_CAU
