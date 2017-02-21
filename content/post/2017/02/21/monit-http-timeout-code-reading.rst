monitのhttpのタイムアウトのコードリーディング
#############################################

:date: 2017-02-21 11:10
:tags: monit, code-reading
:category: blog
:slug: 2017/02/21/monit-http-timeout-code-reading

はじめに
--------

`monitのイベントループのコードリーディング </blog/2017/02/20/monit-event-loop-code-reading/>`_ からの続きです。

socket_create関数からの流れ
---------------------------

`monitのif failed urlのコードリーディング </blog/2017/02/20/monit-if-failed-url-code-reading/>`_ の ``check_connection`` 関数の156行目で呼ばれている ``socket_create`` 関数の実装を追ってみます。

``socket_create`` 関数の実装。
`src/socket.c#L146-#L183 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-146:183>`_

.. code-block:: c
    :linenos: table
    :linenostart: 146

    Socket_T socket_create(void *port) {
            int socket;
            Socket_T S = NULL;
            Port_T p = port;
            ASSERT(port);
            switch (p->family) {
                    case AF_UNIX:
                            socket = create_unix_socket(p->pathname, p->type, p->timeout);
                            break;
                    case AF_INET:
                            socket = create_socket(p->hostname, p->port, p->type, p->timeout);
                            break;
                    default:
                            LogError("Invalid Port Protocol family\n");
                            return NULL;
            }
            if (socket < 0) {
                    LogError("socket_create: Could not create socket -- %s\n", STRERROR);
            } else {
                    NEW(S);
                    S->socket = socket;
                    S->type = p->type;
                    S->port = p->port;
                    S->timeout = p->timeout;
                    S->connection_type = TYPE_LOCAL;
                    if (p->family == AF_UNIX) {
                            S->host = Str_dup(LOCALHOST);
                    } else {
                            S->host = Str_dup(p->hostname);
                    }
                    if (p->SSL.use_ssl && !socket_switch2ssl(S, p->SSL)) {
                            socket_free(&S);
                            return NULL;
                    }
                    S->Port = port;
            }
            return S;
    }

``create_socket`` 関数の実装。
`src/net.c#L267-#L306 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/net.c?at=release-5-11-0&fileviewer=file-view-default#net.c-267:306>`_

.. code-block:: c
    :linenos: table
    :linenostart: 267

    int create_socket(const char *hostname, int port, int type, int timeout) {
            int s, status;
            struct sockaddr_in sin;
            struct sockaddr_in *sa;
            struct addrinfo hints;
            struct addrinfo *result;
            ASSERT(hostname);
            memset(&hints, 0, sizeof(struct addrinfo));
            hints.ai_family = AF_INET;
    
            if((status = getaddrinfo(hostname, NULL, &hints, &result)) != 0) {
                    LogError("Cannot translate '%s' to IP address -- %s\n", hostname, status == EAI_SYSTEM ? STRERROR : gai_strerror(status));
                    return -1;
            }
            if((s = socket(AF_INET, type, 0)) < 0) {
                    LogError("Cannot create socket -- %s\n", STRERROR);
                    freeaddrinfo(result);
                    return -1;
            }
            sa = (struct sockaddr_in *)result->ai_addr;
            memcpy(&sin, sa, result->ai_addrlen);
            sin.sin_family = AF_INET;
            sin.sin_port = htons(port);
            freeaddrinfo(result);
            if(! Net_setNonBlocking(s)) {
                    LogError("Cannot set nonblocking socket -- %s\n", STRERROR);
                    goto error;
            }
            if (fcntl(s, F_SETFD, FD_CLOEXEC) == -1) {
                    LogError("Cannot set socket close on exec -- %s\n", STRERROR);
                    goto error;
            }
            if (do_connect(s, (struct sockaddr *)&sin, sizeof(sin), timeout) < 0) {
                    goto error;
            }
            return s;
    error:
            Net_close(s);
            return -1;
    }

上記の291行目で ``Net_setNonBlocking`` 関数を呼び出してソケットをノンブロッキングにしています。

``Net_setNonBlocking`` 関数の実装。

`libmonit/src/system/Net.c#L72-#L74 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/libmonit/src/system/Net.c?at=release-5-11-0&fileviewer=file-view-default#Net.c-72:74>`_

.. code-block:: c
    :linenos: table
    :linenostart: 72

    int Net_setNonBlocking(int socket) {
            return (fcntl(socket, F_SETFL, fcntl(socket, F_GETFL, 0) | O_NONBLOCK) != -1);
    }

``do_connect`` 関数の実装。
`src/net.c#L161-#L199 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/net.c?at=release-5-11-0&fileviewer=file-view-default#net.c-161:199>`_

.. code-block:: c
    :linenos: table
    :linenostart: 161

    /*
     * Do a non blocking connect, timeout if not connected within timeout milliseconds
     */
    static int do_connect(int s, const struct sockaddr *addr, socklen_t addrlen, int timeout) {
            int error = 0;
            struct pollfd fds[1];
            error = connect(s, addr, addrlen);
            if (error == 0) {
                    return 0;
            } else if (errno != EINPROGRESS) {
                    LogError("Connection failed -- %s\n", STRERROR);
                    return -1;
            }
            fds[0].fd = s;
            fds[0].events = POLLIN|POLLOUT;
            error = poll(fds, 1, timeout);
            if (error == 0) {
                    LogError("Connection timed out\n");
                    return -1;
            } else if (error == -1) {
                    LogError("Poll failed -- %s\n", STRERROR);
                    return -1;
            }
            if (fds[0].events & POLLIN || fds[0].events & POLLOUT) {
                    socklen_t len = sizeof(error);
                    if (getsockopt(s, SOL_SOCKET, SO_ERROR, &error, &len) < 0) {
                            LogError("Cannot get socket error -- %s\n", STRERROR);
                            return -1;
                    } else if (error) {
                            errno = error;
                            LogError("Socket error -- %s\n", STRERROR);
                            return -1;
                    }
            } else {
                    LogError("Socket not ready for I/O\n");
                    return -1;
            }
            return 0;
    }

上記の176行目の ``epoll`` でタイムアウトした場合は 177行目の ``if (error == 0)`` が成立してエラーで抜けることになります。

socket_write関数からの流れ
--------------------------

`monitのif failed urlのコードリーディング </blog/2017/02/20/monit-if-failed-url-code-reading/>`_ の ``check_http`` 関数の313行目で呼ばれている ``socket_write`` 関数の実装を追ってみます。

``socket_write`` 関数の実装。
`src/socket.c#L406-#L429 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-406:429>`_

.. code-block:: c
    :linenos: table
    :linenostart: 406

    int socket_write(Socket_T S, void *b, size_t size) {
            ssize_t n = 0;
            void *p = b;
            ASSERT(S);
            while (size > 0) {
                    if (S->ssl) {
                            n = send_ssl_socket(S->ssl, p, size, S->timeout);
                    } else {
                            if (S->type == SOCK_DGRAM)
                                    n = udp_write(S->socket,  p, size, S->timeout);
                            else
                                    n = sock_write(S->socket,  p, size, S->timeout);
                    }
                    if (n <= 0) break;
                    p += n;
                    size -= n;
    
            }
            if (n < 0) {
                    /* No write or a partial write is an error */
                    return -1;
            }
            return  (int)(p - b);
    }

上記の417行目で呼んでいる ``sock_write`` 関数の実装。
`src/net.c#L393-#L395 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/net.c?at=release-5-11-0&fileviewer=file-view-default#net.c-393:395>`_

.. code-block:: c
    :linenos: table
    :linenostart: 393

    ssize_t sock_write(int socket, const void *buffer, size_t size, int timeout) {
            return Net_write(socket, buffer, size, timeout);
    }

``Net_write`` 関数の実装。
`libmonit/src/system/Net.c#L124-#L139 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/libmonit/src/system/Net.c?at=release-5-11-0&fileviewer=file-view-default#Net.c-124:139>`_

.. code-block:: c
    :linenos: table
    :linenostart: 124

    ssize_t Net_write(int socket, const void *buffer, size_t size, time_t timeout) {
    	ssize_t n = 0;
            if (size > 0) {
                    do {
                            n = write(socket, buffer, size);
                    } while (n == -1 && errno == EINTR);
                    if (n == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
                            if ((timeout == 0) || (Net_canWrite(socket, timeout) == false))
                                    return 0;
                            do {
                                    n = write(socket, buffer, size);
                            } while (n == -1 && errno == EINTR);
                    }
            }
    	return n;
    }

``Net_canWrite`` 関数の実装。
`libmonit/src/system/Net.c#L94-#L103 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/libmonit/src/system/Net.c?at=release-5-11-0&fileviewer=file-view-default#Net.c-94:103>`_

.. code-block:: c
    :linenos: table
    :linenostart: 94

    int Net_canWrite(int socket, time_t milliseconds) {
            int r = 0;
            struct pollfd fds[1];
            fds[0].fd = socket;
            fds[0].events = POLLOUT;
            do {
                    r = poll(fds, 1, (int)milliseconds);
            } while (r == -1 && errno == EINTR);
            return (r > 0);
    }

socket_readln関数からの流れ
---------------------------

`monitのif failed urlのコードリーディング </blog/2017/02/20/monit-if-failed-url-code-reading/>`_ の ``check_request`` 関数の208行目と222行目で呼ばれている ``socket_readln`` 関数の実装を追ってみます。

``socket_readln`` 関数の実装。
`src/socket.c#L453-#L466 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-453:466>`_

.. code-block:: c
    :linenos: table
    :linenostart: 453

    char *socket_readln(Socket_T S, char *s, int size) {
            int c;
            unsigned char *p = (unsigned char *)s;
            ASSERT(S);
            while (--size && ((c = socket_read_byte(S)) > 0)) { // Stop when \0 is read
                    *p++ = c;
                    if (c == '\n')
                            break;
            }
            *p = 0;
            if (*s)
                    return s;
            return NULL;
    }

``socket_read_byte`` 関数の実装。
`src/socket.c#L432-#L439 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-432:439>`_

.. code-block:: c
    :linenos: table
    :linenostart: 432

    int socket_read_byte(Socket_T S) {
            ASSERT(S);
            if (S->offset >= S->length) {
                    if (fill(S, S->timeout) <= 0)
                            return -1;
            }
            return S->buffer[S->offset++];
    }

``fill`` 関数の実装。
`src/socket.c#L109-#L134 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-109:134>`_

.. code-block:: c
    :linenos: table
    :linenostart: 109

    /*
     * Fill the internal buffer. If an error occurs or if the read
     * operation timed out -1 is returned.
     * @param S A Socket object
     * @param timeout The number of milliseconds to wait for data to be read
     * @return TRUE (the length of data read) or -1 if an error occured
     */
    static int fill(Socket_T S, int timeout) {
            int n;
            S->offset = 0;
            S->length = 0;
            if (S->type == SOCK_DGRAM)
                    timeout = 500;
            if (S->ssl) {
                    n = recv_ssl_socket(S->ssl, S->buffer + S->length, RBUFFER_SIZE-S->length, timeout);
            } else {
                    n = (int)sock_read(S->socket, S->buffer + S->length,  RBUFFER_SIZE-S->length, timeout);
            }
            if (n > 0) {
                    S->length += n;
            }  else if (n < 0) {
                    return -1;
            } else if (! (errno == EAGAIN || errno == EWOULDBLOCK)) // Peer closed connection
                    return -1;
            return n;
    }

``sock_read`` 関数の実装。
`src/net.c#L398-#L400 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/net.c?at=release-5-11-0&fileviewer=file-view-default#net.c-398:400>`_

.. code-block:: c
    :linenos: table
    :linenostart: 398

    ssize_t sock_read(int socket, void *buffer, int size, int timeout) {
            return Net_read(socket, buffer, size, timeout);
    }

``Net_read`` 関数の実装。
`libmonit/src/system/Net.c#L106-#L121 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/libmonit/src/system/Net.c?at=release-5-11-0&fileviewer=file-view-default#Net.c-106:121>`_

.. code-block:: c
    :linenos: table
    :linenostart: 106

    ssize_t Net_read(int socket, void *buffer, size_t size, time_t timeout) {
    	ssize_t n = 0;
            if (size > 0) {
                    do {
                            n = read(socket, buffer, size);
                    } while (n == -1 && errno == EINTR);
                    if (n == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
                            if ((timeout == 0) || (Net_canRead(socket, timeout) == false))
                                    return 0;
                            do {
                                    n = read(socket, buffer, size);
                            } while (n == -1 && errno == EINTR);
                    }
            }
    	return n;
    }

``Net_canRead`` 関数の実装。
`libmonit/src/system/Net.c#L82-#L91 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/libmonit/src/system/Net.c?at=release-5-11-0&fileviewer=file-view-default#Net.c-82:91>`_

.. code-block:: c
    :linenos: table
    :linenostart: 82

    int Net_canRead(int socket, time_t milliseconds) {
            int r = 0;
            struct pollfd fds[1];
            fds[0].fd = socket;
            fds[0].events = POLLIN;
            do {
                    r = poll(fds, 1, (int)milliseconds);
            } while (r == -1 && errno == EINTR);
            return (r > 0);
    }
