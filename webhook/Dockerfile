# Webhook de aprovisionamiento midPoint -> FreePBX (Fase 3)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY webhook_provisioner.py test_webhook_provisioner.py ./

# Los tests corren en build: si fallan, la imagen no se construye (CI básico)
RUN python -m unittest test_webhook_provisioner

EXPOSE 5000
CMD ["python", "webhook_provisioner.py"]
