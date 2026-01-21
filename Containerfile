FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/
COPY config/ /app/config/

ENV PYTHONPATH=/app/src
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "ezansi_platform_core"]
