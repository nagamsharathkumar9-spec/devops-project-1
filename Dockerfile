FROM python:3.14-slim
WORKDIR /app
COPY generate_data.py .
COPY backtester.py .
RUN pip install pandas
CMD ["sh", "-c", "python generate_data.py && python backtester.py"]