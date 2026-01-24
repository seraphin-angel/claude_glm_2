
FROM node:22

# タイムゾーンをビルド引数で受け取り（例: Asia/Tokyo）
ARG TZ=Asia/Tokyo
ENV TZ="${TZ}" \
    DEBIAN_FRONTEND=noninteractive \
    LANG=ja_JP.UTF-8 \
    LC_ALL=ja_JP.UTF-8 \
    SHELL=/bin/bash

# root で必要パッケージを導入
USER root

# Install basic development tools and iptables/ipset
RUN apt-get update && \
    # First, update keyring packages to avoid signature verification errors (bookworm new signing keys)
    apt-get install -y --no-install-recommends \
      debian-archive-keyring \
      debian-keyring && \
    # Refresh package lists after new keys are installed
    apt-get update && \
    # Install basic development tools and network utilities
    apt-get install -y --no-install-recommends \
      less \
      git \
      procps \
      sudo \
      fzf \
      zsh \
      man-db \
      unzip \
      gnupg2 \
      gh \
      iptables \
      ipset \
      iproute2 \
      dnsutils \
      aggregate \
      nano \
      jq \
      ca-certificates \
      curl \
      wget \
      git-lfs \
      zip \
      bash-completion \
      vim \
      ripgrep \
      fd-find \
      openssh-client \
      locales \
      tzdata \
      iputils-ping \
      netcat-openbsd && \
    # ロケール（日本語+英語）を有効化
    sed -i 's/^# *ja_JP.UTF-8/ja_JP.UTF-8/' /etc/locale.gen && \
    sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && \
    locale-gen && \
    # Clean up apt cache to reduce image size
    apt-get clean && rm -rf /var/lib/apt/lists/*

# chrome 用の依存 + Chrome stable をインストール（アーキテクチャ対応）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates apt-transport-https \
    libxshmfence1 libgbm1 libgtk-3-0 libnss3 libasound2 \
    fonts-noto-color-emoji fonts-noto-cjk && \
    # アーキテクチャを検出
    ARCH=$(dpkg --print-architecture) && \
    case ${ARCH} in \
        amd64) \
            # x86_64環境ではGoogle Chromeをインストール
            install -d /usr/share/keyrings && \
            wget -qO- https://dl.google.com/linux/linux_signing_key.pub \
              | gpg --dearmor -o /usr/share/keyrings/google-linux-signing-keyring.gpg && \
            echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
              > /etc/apt/sources.list.d/google-chrome.list && \
            apt-get update && apt-get install -y --no-install-recommends google-chrome-stable ;; \
        arm64|aarch64) \
            # ARM64環境ではChromiumをインストール（Google ChromeはARM64をサポートしていない）
            apt-get update && apt-get install -y --no-install-recommends chromium \
            # Chromiumをchromeとしてシンボリックリンクを作成
            && ln -sf /usr/bin/chromium /usr/bin/google-chrome-stable ;; \
        *) \
            echo "Unsupported architecture: ${ARCH}" && exit 1 ;; \
    esac && \
    rm -rf /var/lib/apt/lists/*

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
chown -R node:node /usr/local/share

ARG USERNAME=node

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
&& mkdir /commandhistory \
&& touch /commandhistory/.bash_history \
&& chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# Create workspace and config directories and set permissions
RUN mkdir -p /workspace /home/node/.claude && \
chown -R node:node /workspace /home/node/.claude


# タイムゾーン設定とsudo権限設定
RUN ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo "${TZ}" > /etc/timezone && \
    # node ユーザーに sudo 権限（パスワード無し）
    echo "node ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/90-node && \
    chmod 0440 /etc/sudoers.d/90-node && \
    # Codex の設定/ログ保管ディレクトリを先に作成（ホスト側にバインドする想定）
    mkdir -p /home/node/.codex && \
    chown -R node:node /home/node/.codex

# 作業ディレクトリ
WORKDIR /workspace

# Install git-delta with proper architecture detection
RUN ARCH=$(dpkg --print-architecture) && \
    case ${ARCH} in \
        amd64) ARCH="amd64" ;; \
        arm64) ARCH="arm64" ;; \
        armhf) ARCH="armhf" ;; \
        *) echo "Unsupported architecture: ${ARCH}" && exit 1 ;; \
    esac && \
    wget -O git-delta.deb "https://github.com/dandavison/delta/releases/download/0.18.2/git-delta_0.18.2_${ARCH}.deb" && \
    dpkg -i git-delta.deb || apt-get install -f -y && \
    rm git-delta.deb

# Codex CLI will be installed via postCreateCommand in devcontainer.json

# node ユーザーで動作（devcontainer.json の "remoteUser": "node" と一致）
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Default powerline10k theme
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.2.0/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  -x

# Install Claude Code (native installation - recommended)
# インストール先: ~/.local/bin/claude
RUN curl -fsSL https://claude.ai/install.sh | bash
ENV PATH="/home/node/.local/bin:${PATH}"

# Install uv (Python package manager)
# uvをClaude Codeと同じ ~/.local/bin にインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# PATHは既に /home/node/.local/bin が含まれているため追加不要

# Install Playwright and required browsers (root privileges needed)
USER root
RUN mkdir -p /home/node/.cache && \
    chown -R node:node /home/node/.cache && \
    npm i -g playwright@1.53.0 && \
    npx playwright install --with-deps chromium && \
    chown -R node:node /home/node/.cache
USER node

# シェルは bash （必要なら zsh に切替可）
SHELL ["/bin/bash", "-lc"]

# 便利設定（Git の safe.directory）
RUN git config --global --add safe.directory /workspace

# 既定のコマンドは何もしない（Dev Containers 側で管理）
CMD [ "sleep", "infinity" ]
