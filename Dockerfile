FROM python:3.12-slim
WORKDIR /app
COPY server/requirements.txt server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt
COPY server server
COPY widget widget
COPY demo demo
COPY du_an.md hoi_dap_mua_nha.md tin_dang.csv ./
COPY tai_lieu tai_lieu
WORKDIR /app/server
ENV DATA_DIR=/app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
