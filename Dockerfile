FROM python:3.14-slim

WORKDIR /app

COPY app.py .

RUN pip install pandas

EXPOSE 8000

CMD ["python", "app.py"]