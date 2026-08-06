FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Create a non-root user and group (same pattern as backtester)
RUN groupadd --gid 1001 mcpgroup && \
    useradd --uid 1001 --gid mcpgroup --no-create-home mcpuser

# Change ownership of the app directory to the non-root user
RUN chown -R mcpuser:mcpgroup /app

# Switch to non-root user
USER mcpuser

EXPOSE 9000

CMD ["python", "server.py"]