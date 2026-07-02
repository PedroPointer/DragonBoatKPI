FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache

COPY src/ ./src/
COPY run.py ./

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["python", "run.py"]
