# 基础镜像
FROM python:3.11-slim

# 工作目录
WORKDIR /app

# 复制项目配置与代码并安装依赖
COPY pyproject.toml /app/pyproject.toml
COPY app /app/app
RUN pip install --no-cache-dir .

# （代码已复制于上方）

# 默认环境变量（可被外部覆盖）
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
