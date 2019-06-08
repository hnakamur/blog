Ubuntuのデスクトップ環境でsshのパスフレーズ入力を1回だけにする
##############################################################

:date: 2018-05-21 16:10
:modified: 2019-06-09 05:55
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

一時的にsshは不要というときは、パスフレーズのプロンプトでCtrl+Cを押せばスキップできます。その場合端末を開いてbashを起動する度にプロンプトが出てくるので、一度パスフレーズを入力すれば以降は不要になります。

2018-05-29追記。おもいっきり勘違いしてて「ssh-agentを起動する部分は外して」と書いてるくせに全然外してませんでした。これだとUbuntu Keyringから :code:`/usr/bin/ssh-agent /usr/bin/im-launch mate-session` として起動しているssh-agentともう一つ別に起動してしまいます。

ということで、以下のように修正しました。

.. code-block:: sh

        ssh_private_key_path="$HOME/.ssh/id_rsa"
        if ! ssh-add -l | grep -q "$ssh_private_key_path "; then
          ssh-add "$ssh_private_key_path"
        fi

grepで最後に空白を含めているのは :code:`$HOME/.ssh/id_rsa.foo` のような別の鍵がもしあったときに誤判定しないようにするためです。

:code:`ssh-add -l` の出力が以下のような感じになっていました（SHA256の後は伏せています）。

.. code-block:: console

        $ ssh-add -l
        2048 SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx /home/hnakamur/.ssh/id_rsa (RSA)
        4096 SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx myapp deploy (RSA)
        2048 SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  (RSA)

また今回は関係ないですが :code:`~/.ssh/id_rsa.myapp.deploy` と :code:`~/.ssh/id_rsa.myapp.deploy.pub` のようなパスフレーズ無しの鍵ペアで公開鍵の方にコメントを入れていると、2行目のようにコメントで表示されるようです。

2019-06-09追記。公開鍵にコメント入れると上のスクリプトでは ssh-add を繰り返してしまうので、以下のように修正しました。fingerprintには :code:`+` が入ることがあったので grep には :code:`-F` を指定しています。

.. code-block:: sh

        ssh_private_key_path="$HOME/.ssh/id_ed25519"
        ssh_private_key_fingerprint="SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        if ! ssh-add -l | grep -q -F "$ssh_private_key_fingerprint "; then
          ssh-add "$ssh_private_key_path"
        fi

上記の fingerprint の値は以下のコマンドで調べて指定します。

.. code-block:: sh

        ssh-keygen -l -f ~/.ssh/id_ed25519
