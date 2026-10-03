# 分析ジョブ用の使い捨てコンテナ(開発専用・検証段階)。PMのソース・.env・秘密情報は一切含めない。
# ベースイメージはダイジェストで固定する(2026-10-03に取得したpython:3.12-slim)。
FROM python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

# duckdbは固定版。導入後はpipも削除し、コンテナ内でパッケージを追加できないようにする。
RUN pip install --no-cache-dir duckdb==1.4.4 \
    && pip uninstall -y pip \
    && groupadd --gid 10001 analysis \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin analysis

COPY job_main.py runtime.py /job/

USER 10001:10001
WORKDIR /tmp
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# -I: 環境変数・カレントディレクトリ由来のモジュール読込を無効にする
ENTRYPOINT ["python", "-I", "/job/job_main.py"]
