# ---- member-assistant ----
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MEMBER_ASSISTANT_HOST=0.0.0.0 \
    MEMBER_ASSISTANT_PORT=8001

WORKDIR /srv/member-assistant
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# build the vector index and sample db at image build time
RUN python scripts/init_db.py && python scripts/build_index.py

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
