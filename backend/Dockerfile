FROM python:3.11-slim
RUN apt-get update && apt-get install -y gcc libmariadb-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
# Install torch CPU-only first (smaller download, faster build)
RUN pip install --no-cache-dir --default-timeout=300 torch==2.5.0+cpu torchvision==0.20.0+cpu --index-url https://download.pytorch.org/whl/cpu
# Install remaining dependencies
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
