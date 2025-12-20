# 基础镜像
FROM python:3.11-slim

# 工作目录
WORKDIR /app

# 复制依赖并安装
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制项目代码
COPY app /app/app

# 默认环境变量（可被外部覆盖）
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
