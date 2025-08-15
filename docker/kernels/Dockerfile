FROM jupyter/scipy-notebook:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    vim \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch back to jovyan user
USER $NB_UID

# Install Python packages for data science
RUN pip install --no-cache-dir \
    pandas==2.0.3 \
    numpy==1.24.3 \
    matplotlib==3.7.2 \
    seaborn==0.12.2 \
    scikit-learn==1.3.0 \
    scipy==1.11.1 \
    statsmodels==0.14.0 \
    plotly==5.15.0 \
    networkx==3.1 \
    biopython==1.81 \
    rdkit==2023.3.2 \
    lifelines==0.27.7 \
    xgboost==1.7.6 \
    lightgbm==4.0.0 \
    tensorflow==2.13.0 \
    torch==2.0.1 \
    transformers==4.31.0 \
    ipywidgets==8.1.0 \
    tqdm==4.65.0 \
    joblib==1.3.1 \
    openpyxl==3.1.2 \
    xlrd==2.0.1 \
    pyarrow==12.0.1 \
    fastparquet==2023.7.0 \
    h5py==3.9.0

# Enable extensions
RUN jupyter labextension install @jupyter-widgets/jupyterlab-manager

# Configure IPython kernel
RUN ipython profile create
RUN echo "c.InteractiveShellApp.matplotlib = 'inline'" >> ~/.ipython/profile_default/ipython_config.py

WORKDIR /home/jovyan/work

# Expose Jupyter port
EXPOSE 8888

CMD ["start.sh", "jupyter", "lab", "--NotebookApp.token=''", "--NotebookApp.password=''"]
