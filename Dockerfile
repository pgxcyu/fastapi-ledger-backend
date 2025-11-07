FROM python:3.13.9

LABEL authors="pgxcyu"

WORKDIR /code

# 安装OpenCV所需的系统依赖
RUN apt-get update && apt-get install -y \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic

EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]