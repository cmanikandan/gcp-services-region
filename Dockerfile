FROM python:3.12-slim

WORKDIR /app
COPY harvester.py generator.py cli.py server.py README.md ./

# Pre-create cache & dist directories
RUN mkdir -p data/cache dist

EXPOSE 8080

CMD ["python3", "server.py", "--host", "0.0.0.0", "--port", "8080"]
