FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN sed -i '/pandas_ta/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Manually install pandas_ta from Azure backup (complete with metadata)
COPY pandas_ta_complete.tar.gz /tmp/
RUN cd /tmp && \
    tar -xzf pandas_ta_complete.tar.gz && \
    cp -r pandas_ta /usr/local/lib/python3.11/site-packages/ && \
    cp -r pandas_ta-0.3.14b0.dist-info /usr/local/lib/python3.11/site-packages/ && \
    rm -rf /tmp/pandas_ta_complete.tar.gz /tmp/pandas_ta /tmp/pandas_ta-0.3.14b0.dist-info

# Copy application code
COPY . .

# Create all required directories with proper permissions
RUN mkdir -p ta_posts posts logs data charts backup && \
    chmod 755 ta_posts posts logs data charts backup && \
    # Create subdirectories for posts
    mkdir -p posts/ta posts/explainer && \
    chmod 755 posts/ta posts/explainer

# Ensure logs directory has write permissions
RUN chmod 777 logs

# Create a non-root user for enhanced security (optional)
# RUN adduser --disabled-password --gecos '' appuser && \
#     chown -R appuser:appuser /app
# USER appuser

EXPOSE 3001

# Add healthcheck for container monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

CMD ["python", "scheduler.py"]