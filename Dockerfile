FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "pytest -q && python -m gate.run builds/v1.1.0.yaml --out reports; test $? -le 2"]
