# Copyright 2021 DeepMind Technologies Limited
# ... (라이선스 주석 동일) ...

ARG CUDA=12.2.2
FROM nvidia/cuda:${CUDA}-cudnn8-runtime-ubuntu20.04
ARG CUDA
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update --quiet \
    && apt-get install --no-install-recommends --yes --quiet \
        build-essential \
        cmake \
        cuda-command-line-tools-$(cut -f1,2 -d- <<< ${CUDA//./-}) \
        curl \
        ca-certificates \
        git \
        hmmer \
        kalign \
        tzdata \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove --yes \
    && apt-get clean

# Compile HHsuite from source.
RUN git clone --branch v3.3.0 --single-branch https://github.com/soedinglab/hh-suite.git /tmp/hh-suite \
    && mkdir /tmp/hh-suite/build \
    && pushd /tmp/hh-suite/build \
    && cmake -DCMAKE_INSTALL_PREFIX=/opt/hhsuite .. \
    && make -j && make install \
    && ln -s /opt/hhsuite/bin/* /usr/bin \
    && popd \
    && rm -rf /tmp/hh-suite

# Install Miniconda package manager.
RUN wget -q -P /tmp \
  https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda \
    && rm /tmp/Miniconda3-latest-Linux-x86_64.sh

# Install Conda packages.
ENV PATH="/opt/conda/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/conda/lib:$LD_LIBRARY_PATH"
ENV CONDA_PLUGINS_AUTO_ACCEPT_TOS="yes"
RUN conda install --quiet --yes conda==24.11.1 pip python=3.11 \
    && conda install --quiet --yes --channel nvidia cuda=${CUDA_VERSION} \
    && conda clean --all --force-pkgs-dirs --yes

# pip 패키지 설치 — requirements.txt만 먼저 복사해서 캐시 활용
COPY requirements.txt /app/alphafold/requirements.txt
RUN wget -q -P /app/alphafold/alphafold/common/ \
  https://git.scicore.unibas.ch/schwede/openstructure/-/raw/7102c63615b64735c4941278d92b554ec94415f8/modules/mol/alg/src/stereo_chemical_props.txt
RUN pip3 install --upgrade pip --no-cache-dir \
    && pip3 install -r /app/alphafold/requirements.txt --no-cache-dir \
    && pip3 install --upgrade --no-cache-dir \
      jax==0.4.26 \
      jaxlib==0.4.26+cuda12.cudnn89 \
      -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

# ── ColabFold 추가 ──────────────────────────────
RUN pip3 install --no-cache-dir \
      "colabfold[alphafold,openmm]" \
      "openmm[cuda12]" \
    && pip3 install --no-cache-dir --force-reinstall \
      "jax[cuda12]==0.4.26"   # colabfold가 건드린 jax 버전 다시 고정

RUN chmod u+s /sbin/ldconfig.real
RUN ln -sf /usr/lib/x86_64-linux-gnu/libffi.so.7 /opt/conda/lib/libffi.so.7

# Node.js + OpenCode 설치 (무거운 설치, 자주 안 바뀜)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g opencode-ai@1.17.12 opencode-codex-usage@1.0.0

# ── 여기부터 자주 바뀌는 것들: 맨 마지막에 배치 ──────────────
COPY . /app/alphafold
COPY docker/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

WORKDIR /app/alphafold
EXPOSE 22
ENTRYPOINT ["/app/startup.sh"]