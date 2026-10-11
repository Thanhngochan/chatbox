"""Backend cho chat box tư vấn bất động sản.

Chạy:  uvicorn app:app --reload --port 8000   (trong thư mục server/)
"""

import json
import os
import time
from collections import defaultdict, deque
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from du_lieu import doc_tai_lieu, doc_tin_dang, tim_tin_dang

GOC = Path(__file__).resolve().parent.parent

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
EFFORT = os.environ.get("CLAUDE_EFFORT", "low")  # chat ngắn nên để low cho nhanh, rẻ
# Website nào được phép nhúng chat box, cách nhau bằng dấu phẩy. "*" = mọi website.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
SO_TIN_NHAN_TOI_DA = 20       # chỉ gửi 20 tin gần nhất cho Claude
DO_DAI_TIN_NHAN_TOI_DA = 2000  # ký tự
GIOI_HAN_MOI_PHUT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "15"))
SO_VONG_CONG_CU_TOI_DA = 4

TAI_LIEU = doc_tai_lieu()
CAC_TIN = doc_tin_dang()

CHI_DAN = f"""Bạn là trợ lý tư vấn bất động sản trên website cá nhân của một môi giới.
Nhiệm vụ: giúp khách tìm căn phù hợp, giải đáp về dự án và thủ tục mua nhà.

Quy tắc:
- Thông tin dự án và hỏi đáp thủ tục: chỉ dựa trên các thẻ <tai_lieu> bên dưới.
- Tin đăng đang bán: luôn dùng công cụ tim_tin_dang, không tự bịa căn hay giá.
- Nếu không có thông tin, nói rõ là bạn chưa có thông tin đó và gợi ý khách để lại số điện thoại để môi giới liên hệ.
- Khi giới thiệu tin đăng, nêu mã tin (ví dụ T001), giá, diện tích, số phòng ngủ và pháp lý.
- Không đưa ra tư vấn pháp lý hay tài chính mang tính cam kết.
- Trả lời ngắn gọn, thân thiện, bằng ngôn ngữ khách dùng (mặc định tiếng Việt). Có thể dùng **in đậm** và gạch đầu dòng.

{TAI_LIEU}"""

CONG_CU = [{
    "name": "tim_tin_dang",
    "description": (
        "Tìm tin đăng bất động sản đang bán theo điều kiện. Mọi tham số đều không bắt buộc; "
        "chỉ truyền những điều kiện khách đã nói. Trả về danh sách tin, sắp theo giá tăng dần."
    ),
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "loai": {"type": "string", "enum": ["can_ho", "nha_pho", "dat_nen"],
                     "description": "Loại bất động sản"},
            "khu_vuc": {"type": "string", "description": "Quận/huyện, ví dụ 'Quận 7', 'Thủ Đức'"},
            "du_an": {"type": "string", "description": "Tên dự án, ví dụ 'An Lạc Garden'"},
            "gia_toi_thieu_ty": {"type": "number", "description": "Giá thấp nhất, đơn vị tỷ đồng"},
            "gia_toi_da_ty": {"type": "number", "description": "Giá cao nhất, đơn vị tỷ đồng"},
            "phong_ngu_toi_thieu": {"type": "integer", "description": "Số phòng ngủ tối thiểu"},
            "dien_tich_toi_thieu_m2": {"type": "number", "description": "Diện tích tối thiểu (m2)"},
            "chi_co_so_hong": {"type": "boolean", "description": "Chỉ lấy căn đã có sổ hồng"},
        },
        "additionalProperties": False,
    },
}]

KIEU_THAM_SO = {
    "loai": str, "khu_vuc": str, "du_an": str,
    "gia_toi_thieu_ty": (int, float), "gia_toi_da_ty": (int, float),
    "phong_ngu_toi_thieu": int, "dien_tich_toi_thieu_m2": (int, float),
    "chi_co_so_hong": bool,
}

claude = anthropic.AsyncAnthropic()
app = FastAPI(title="Property Chat")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


# ---------- Giới hạn số lượt hỏi để tránh bị spam tốn tiền API ----------
_lich_su_goi = defaultdict(deque)


def kiem_tra_gioi_han(ip):
    bay_gio = time.monotonic()
    hang_doi = _lich_su_goi[ip]
    while hang_doi and bay_gio - hang_doi[0] > 60:
        hang_doi.popleft()
    if len(hang_doi) >= GIOI_HAN_MOI_PHUT:
        raise HTTPException(429, "Bạn hỏi hơi nhanh, vui lòng đợi một chút rồi thử lại.")
    hang_doi.append(bay_gio)


# ---------- API ----------
class TinNhan(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=DO_DAI_TIN_NHAN_TOI_DA)


class YeuCauChat(BaseModel):
    messages: list[TinNhan] = Field(min_length=1)


def su_kien(loai, du_lieu):
    """Định dạng một sự kiện Server-Sent Events."""
    return f"event: {loai}\ndata: {json.dumps(du_lieu, ensure_ascii=False)}\n\n"


def chay_cong_cu(khoi):
    """Chạy công cụ Claude yêu cầu. Trả về (nội dung tool_result, danh sách tin, có lỗi?)."""
    tham_so = khoi.input
    hop_le = (
        khoi.name == "tim_tin_dang"
        and isinstance(tham_so, dict)
        and all(k in KIEU_THAM_SO and isinstance(v, KIEU_THAM_SO[k]) for k, v in tham_so.items())
    )
    if not hop_le:
        return json.dumps({"loi": "Tham số không hợp lệ", "nhan_duoc": tham_so}, ensure_ascii=False), [], True
    tim_duoc = tim_tin_dang(CAC_TIN, tham_so)
    return json.dumps({"so_tin": len(tim_duoc), "tin_dang": tim_duoc}, ensure_ascii=False), tim_duoc, False


async def tra_loi(cac_tin_nhan):
    """Vòng lặp: gọi Claude, chạy công cụ nếu cần, stream chữ về trình duyệt."""
    messages = [{"role": m.role, "content": m.content} for m in cac_tin_nhan]
    da_gui_chu = False
    try:
        for _ in range(SO_VONG_CONG_CU_TOI_DA):
            async with claude.beta.messages.stream(
                model=MODEL,
                max_tokens=8000,
                system=[{"type": "text", "text": CHI_DAN, "cache_control": {"type": "ephemeral"}}],
                tools=CONG_CU,
                messages=messages,
                output_config={"effort": EFFORT},
                # Nếu bộ lọc an toàn từ chối nhầm, API tự chuyển sang model dự phòng
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                async for ev in stream:
                    if ev.type == "text":
                        if da_gui_chu is None:  # tách đoạn giữa hai lượt trả lời
                            yield su_kien("text", {"text": "\n\n"})
                        da_gui_chu = True
                        yield su_kien("text", {"text": ev.text})
                phan_hoi = await stream.get_final_message()

            if phan_hoi.stop_reason == "refusal":
                yield su_kien("error", {"message": "Xin lỗi, mình không thể hỗ trợ yêu cầu này."})
                return

            cac_lenh = [b for b in phan_hoi.content if b.type == "tool_use"]
            if not cac_lenh:
                yield su_kien("done", {})
                return
            if phan_hoi.stop_reason == "max_tokens":
                yield su_kien("error", {"message": "Câu trả lời quá dài, vui lòng hỏi cụ thể hơn."})
                return

            ket_qua = []
            for khoi in cac_lenh:
                noi_dung, tim_duoc, loi = chay_cong_cu(khoi)
                if tim_duoc:
                    yield su_kien("listings", {"items": tim_duoc[:6]})
                ket_qua.append({"type": "tool_result", "tool_use_id": khoi.id,
                                "content": noi_dung, "is_error": loi})
            messages.append({"role": "assistant", "content": phan_hoi.content})
            messages.append({"role": "user", "content": ket_qua})
            if da_gui_chu:
                da_gui_chu = None  # lượt sau có chữ thì chèn dòng trống trước

        yield su_kien("done", {})
    except anthropic.RateLimitError:
        yield su_kien("error", {"message": "Hệ thống đang bận, vui lòng thử lại sau ít phút."})
    except anthropic.APIStatusError as e:
        print(f"Lỗi API Claude {e.status_code}: {e.message}")
        yield su_kien("error", {"message": "Có lỗi khi kết nối trợ lý, vui lòng thử lại."})
    except anthropic.APIConnectionError:
        yield su_kien("error", {"message": "Không kết nối được tới trợ lý, vui lòng thử lại."})
    except ValueError:
        # SDK không đọc được tham số công cụ Claude gửi về
        yield su_kien("error", {"message": "Có lỗi khi xử lý câu hỏi, vui lòng thử lại."})


@app.post("/api/chat")
async def chat(yeu_cau: YeuCauChat, request: Request):
    kiem_tra_gioi_han(request.client.host if request.client else "?")
    cac_tin_nhan = yeu_cau.messages[-SO_TIN_NHAN_TOI_DA:]
    # API yêu cầu tin đầu tiên là của khách và tin cuối cùng cũng là của khách
    while cac_tin_nhan and cac_tin_nhan[0].role != "user":
        cac_tin_nhan = cac_tin_nhan[1:]
    if not cac_tin_nhan or cac_tin_nhan[-1].role != "user":
        raise HTTPException(400, "Tin nhắn cuối phải là câu hỏi của khách.")
    return StreamingResponse(
        tra_loi(cac_tin_nhan),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
def health():
    return {"ok": True, "model": MODEL, "so_tin_dang": len(CAC_TIN)}


@app.get("/widget.js")
def widget():
    return FileResponse(GOC / "widget" / "property-chat.js", media_type="application/javascript")


@app.get("/")
def demo():
    return FileResponse(GOC / "demo" / "index.html")
