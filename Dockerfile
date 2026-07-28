FROM python:3.14-slim

WORKDIR /app

COPY app.py .

RUN pip install pandas psycopg2-binary

EXPOSE 8000

CMD ["python", "app.py"]