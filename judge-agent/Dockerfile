FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    "google-adk[a2a]>=2.6.0" \
    uvicorn>=0.30.0 \
    starlette>=0.38.0

COPY agent.py main.py ./

ENV PORT=8080
ENV HOST=0.0.0.0
EXPOSE 8080

CMD ["python", "main.py"]