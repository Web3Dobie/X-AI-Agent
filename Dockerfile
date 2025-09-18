FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

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

COPY . .
RUN mkdir -p ta_posts posts logs data

EXPOSE 3001
CMD ["python", "scheduler.py"]