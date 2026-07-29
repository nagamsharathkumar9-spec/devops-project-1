# ============================================================
# Stage 1: Builder — install dependencies
# ============================================================
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS builder

# Install dependencies in a virtual environment
# This keeps the final image clean
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================
# Stage 2: Runtime — lean final image
# ============================================================
FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS runtime

# Image metadata labels (production best practice)
LABEL maintainer="Sharath <nagamsharathkumar9@gmail.com>"
LABEL description="EMA Crossover Backtester — production web API"
LABEL version="3.0"

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only the application files (not the whole repo — .dockerignore handles this)
COPY app.py .
COPY backtester.py .
COPY generate_data.py .

# Create a non-root user and group
# Running as root inside a container is a security risk
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --no-create-home appuser

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

EXPOSE 8000

CMD ["python", "app.py"]