# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN --mount=type=secret,id=pip_conf,target=/root/.pip/pip.conf,required=true \
    pip install --require-hashes --no-cache-dir -r requirements.txt

COPY server.py .

ENV OIDC_ISSUER=http://oidc-provider:8080
ENV PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "server.py"]
