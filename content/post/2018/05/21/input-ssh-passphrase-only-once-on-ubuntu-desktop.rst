Ubuntuのデスクトップ環境でsshのパスフレーズ入力を1回だけにする
##############################################################

:date: 2018-05-21 16:10
:tags: ubuntu, ssh-agent
:category: blog
:slug: 2018/05/21/input-ssh-passphrase-only-once-on-ubuntu-desktop

Ubuntuのデスクトップ環境でssh-agentを使ってsshのパスフレーズ入力を1回だけで良いようにするための設定メモです。

といっても、
`Windows 10のWindows Subsystem for Linux（WSL）を日常的に活用する - ククログ(2017-11-08) <http://www.clear-code.com/blog/2017/11/8.html>`_
に書かれていたスクリプトをほぼそのまま頂いただけです。

ただしUbuntuのデスクトップ環境では「自動起動するプログラム」の「SSH鍵エージェント」で
:code:`/usr/bin/gnome-keyring-daemon --start --components=ssh` というコマンドでssh-agentが起動されるので、ssh-agentを起動する部分は外して以下のようにしました。

ssh-add の後のファイル名は適宜変更してください。

.. code-block:: sh

        SSH_AGENT_FILE=$HOME/.ssh-agent
        test -f $SSH_AGENT_FILE && source $SSH_AGENT_FILE
        if ! ssh-add -l > /dev/null 2>&1; then
          ssh-agent > $SSH_AGENT_FILE
          source $SSH_AGENT_FILE
          ssh-add $HOME/.ssh/id_rsa
        fi

この内容を :code:`~/.bashrc` に追加しておけばターミナルを開いたときに一度だけパスフレーズを入力すれば良くなります。
