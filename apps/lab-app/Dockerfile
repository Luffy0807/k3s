FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/data \
    READY_DELAY=3

# создаём пользователя
RUN useradd -r -u 10001 -g nogroup app \
 && mkdir -p /app /data \
 && chown -R app:nogroup /app /data

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8080
VOLUME ["/data"]

USER app
CMD ["python","-u","/app/app.py"]
