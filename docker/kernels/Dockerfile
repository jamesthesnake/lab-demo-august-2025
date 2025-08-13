FROM jupyter/scipy-notebook:latest

USER root

RUN pip install --no-cache-dir \
    pandas matplotlib seaborn scikit-learn plotly

RUN mkdir -p /workspace && \
    chown -R ${NB_UID}:${NB_GID} /workspace

USER ${NB_UID}

WORKDIR /workspace

ENV JUPYTER_ENABLE_LAB=no
ENV JUPYTER_TOKEN=disabled

CMD ["jupyter", "kernel", "--kernel", "python3"]
