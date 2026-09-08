FROM python:3.11-slim
WORKDIR /app

RUN pip install --no-cache-dir \
    fastmcp \
    starlette \
    uvicorn \
    google-cloud-dataplex

# Copies your exact file from the file tree
COPY catalog-mcp-server.py server.py

ENV PORT=8080
ENV HOST=0.0.0.0
EXPOSE 8080

CMD ["python", "server.py"]