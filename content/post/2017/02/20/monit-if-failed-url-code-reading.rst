monitのif failed urlのコードリーディング
########################################

:date: 2017-02-20 11:14
:tags: monit, code-reading
:category: blog
:slug: 2017/02/20/monit-if-failed-url-code-reading

はじめに
--------

以下のページで紹介されているような ``if failed url ...`` の挙動をコードリーディングしてみたメモです。

* `HOWTO use monit to monitor sites and alert users · fak3r <https://fak3r.com/2010/04/10/howto-use-monit-to-monitor-sites-and-alert-users/>`_
* `Monit でお手軽に外部のサーバを監視する - akishin999の日記 <http://d.hatena.ne.jp/akishin999/20121030/1351555542>`_

.. code-block:: console

        check host fak3r.com with address fak3r.com
        if failed url http://fak3r.com
        timeout 10 seconds for 1 cycles then alert
        then alert

コードリーディングの対象のmonitのバージョンは5.11.0です。
`monit 5.11.0のソースコード <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/?at=release-5-11-0>`_

if failed urlの設定ファイルの文法
---------------------------------

`src/p.y#L1009-L1029 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-1009:1029>`_

``connection`` の文法定義。

.. code-block:: yacc
        :linenos: table
        :linenostart: 1009

        connection      : IF FAILED host port type protocol urloption nettimeout retry rate1
                          THEN action1 recovery {
                            portset.timeout = $<number>8;
                            portset.retry = $<number>9;
                            /* This is a workaround to support content match without having to create
                             an URL object. 'urloption' creates the Request_T object we need minus the
                             URL object, but with enough information to perform content test. 
                             TODO: Parser is in need of refactoring */
                            portset.url_request = urlrequest;
                            addeventaction(&(portset).action, $<number>12, $<number>13);
                            addport(&portset);
                          }
                        | IF FAILED URL URLOBJECT urloption nettimeout retry rate1
                          THEN action1 recovery {
                            prepare_urlrequest($<url>4);
                            portset.timeout = $<number>6;
                            portset.retry = $<number>7;
                            addeventaction(&(portset).action, $<number>10, $<number>11);
                            addport(&portset);
                          }
                        ;


``nettimeout`` の文法定義。
`src/p.y#L1421-L1427 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-1421:1427>`_

.. code-block:: yacc
        :linenos: table
        :linenostart: 1421

        nettimeout      : /* EMPTY */ {
                           $<number>$ = NET_TIMEOUT; // timeout is in milliseconds
                          }
                        | TIMEOUT NUMBER SECOND {
                           $<number>$ = $2 * 1000; // net timeout is in milliseconds internally
                          }
                        ;

``NET_TIMEOUT`` の定義。
`src/net.h#L40-L44 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/net.h?at=release-5-11-0&fileviewer=file-view-default#net.h-40:44>`_

.. code-block:: c
        :linenos: table
        :linenostart: 40

        /**
         * Standard milliseconds to wait for a socket connection or for socket read
         * i/o before aborting
         */
        #define NET_TIMEOUT 5000

ということで ``if failed url ...`` のデフォルトのタイムアウトは 5秒。


``retry`` の文法定義。
`src/p.y#L1429-L1435 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-1429:1435>`_

.. code-block:: yacc
        :linenos: table
        :linenostart: 1429

        retry           : /* EMPTY */ {
                           $<number>$ = 1;
                          }
                        | RETRY NUMBER {
                           $<number>$ = $2;
                          }
                        ;

デフォルトのリトライ回数は1。


``rate1`` の文法定義。
`src/p.y#L1765-L1780 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-1765:1780>`_

.. code-block:: yacc
        :linenos: table
        :linenostart: 1765

        rate1           : /* EMPTY */
                        | NUMBER CYCLE {
                            rate1.count  = $<number>1;
                            rate1.cycles = $<number>1;
                            if (rate1.cycles < 1 || rate1.cycles > BITMAP_MAX)
                              yyerror2("The number of cycles must be between 1 and %d", BITMAP_MAX);
                          }
                        | NUMBER NUMBER CYCLE {
                            rate1.count  = $<number>1;
                            rate1.cycles = $<number>2;
                            if (rate1.cycles < 1 || rate1.cycles > BITMAP_MAX)
                              yyerror2("The number of cycles must be between 1 and %d", BITMAP_MAX);
                            if (rate1.count < 1 || rate1.count > rate1.cycles)
                              yyerror2("The number of events must be bigger then 0 and less than poll cycles");
                          }
                        ;

``rate1`` の変数定義
`src/p.y#L186 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-186>`_

.. code-block:: c
        :linenos: table
        :linenostart: 186

        static struct myrate rate1 = {1, 1};

``myrate`` 構造体の定義。
`src/p.y#L132-L135 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-132:135>`_

.. code-block:: c
        :linenos: table
        :linenostart: 132

          struct myrate {
            unsigned count;
            unsigned cycles;
          };

``addeventaction`` 関数の実装。
`src/p.y#L3116-L3147 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-3116:3147>`_

.. code-block:: c
        :linenos: table
        :linenostart: 3116

        /*
         * Set EventAction object
         */
        static void addeventaction(EventAction_T *_ea, int failed, int succeeded) {
          EventAction_T ea;

          ASSERT(_ea);

          NEW(ea);
          NEW(ea->failed);
          NEW(ea->succeeded);

          ea->failed->id     = failed;
          ea->failed->count  = rate1.count;
          ea->failed->cycles = rate1.cycles;
          if (failed == ACTION_EXEC) {
            ASSERT(command1);
            ea->failed->exec = command1;
            command1 = NULL;
          }

          ea->succeeded->id     = succeeded;
          ea->succeeded->count  = rate2.count;
          ea->succeeded->cycles = rate2.cycles;
          if (succeeded == ACTION_EXEC) {
            ASSERT(command2);
            ea->succeeded->exec = command2;
            command2 = NULL;
          }
          *_ea = ea;
          reset_rateset();
        }

``addport`` 関数の実装。
`src/p.y#L2543-L2602 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/p.y?at=release-5-11-0&fileviewer=file-view-default#p.y-2543:2602>`_

.. code-block:: c
        :linenos: table
        :linenostart: 2543

        /*
         * Add the given portset to the current service's portlist
         */
        static void addport(Port_T port) {
          Port_T p;

          ASSERT(port);

          NEW(p);
          p->port               = port->port;
          p->type               = port->type;
          p->socket             = port->socket;
          p->family             = port->family;
          p->action             = port->action;
          p->timeout            = port->timeout;
          p->retry              = port->retry;
          p->request            = port->request;
          p->generic            = port->generic;
          p->protocol           = port->protocol;
          p->pathname           = port->pathname;
          p->hostname           = port->hostname;
          p->url_request        = port->url_request;
          p->request_checksum   = port->request_checksum;
          p->request_hostheader = port->request_hostheader;
          p->http_headers       = port->http_headers;
          p->version            = port->version;
          p->operator           = port->operator;
          p->status             = port->status;
          memcpy(&p->ApacheStatus, &port->ApacheStatus, sizeof(struct apache_status));

          if (p->request_checksum) {
            cleanup_hash_string(p->request_checksum);
            if (strlen(p->request_checksum) == 32)
              p->request_hashtype = HASH_MD5;
            else if (strlen(p->request_checksum) == 40)
              p->request_hashtype = HASH_SHA1;
            else
              yyerror2("invalid checksum [%s]", p->request_checksum);
          } else
            p->request_hashtype = 0;

          if (port->SSL.use_ssl == TRUE) {
            if (!have_ssl()) {
              yyerror("ssl check cannot be activated. SSL is not supported");
            } else {
              if (port->SSL.certmd5 != NULL) {
                p->SSL.certmd5 = port->SSL.certmd5;
                cleanup_hash_string(p->SSL.certmd5);
              }
              p->SSL.use_ssl = TRUE;
              p->SSL.version = port->SSL.version;
            }
          }
          p->maxforward = port->maxforward;
          p->next = current->portlist;
          current->portlist = p;

          reset_portset();

        }

``Port_T`` の型定義。
`src/monit.h#L457-L510 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/monit.h?at=release-5-11-0&fileviewer=file-view-default#monit.h-457:510>`_

.. code-block:: c
        :linenos: table
        :linenostart: 457

        /** Defines a port object */
        typedef struct myport {
                char *hostname;                                     /**< Hostname to check */
                List_T http_headers; /**< Optional list of HTTP headers to send with request */
                char *request;                              /**< Specific protocol request */
                char *request_checksum;     /**< The optional checksum for a req. document */
                char *request_hostheader;            /**< The optional Host: header to use. Deprecated */
                char *pathname;                   /**< Pathname, in case of an UNIX socket */
                Generic_T generic;                                /**< Generic test handle */
                volatile int socket;                       /**< Socket used for connection */
                int type;                   /**< Socket type used for connection (UDP/TCP) */
                int family;             /**< Socket family used for connection (INET/UNIX) */
                int port;                                                  /**< Portnumber */
                int request_hashtype;   /**< The optional type of hash for a req. document */
                int maxforward;            /**< Optional max forward for protocol checking */
                int timeout; /**< The timeout in millseconds to wait for connect or read i/o */
                int retry;       /**< Number of connection retry before reporting an error */
                int is_available;                /**< TRUE if the server/port is available */
                int version;                                         /**< Protocol version */
                Operator_Type operator;                           /**< Comparison operator */
                int status;                                           /**< Protocol status */
                double response;                      /**< Socket connection response time */
                EventAction_T action;  /**< Description of the action upon event occurence */
                /** Apache-status specific parameters */
                struct apache_status {
                        short loglimit;                  /**< Max percentage of logging processes */
                        short loglimitOP;                                  /**< loglimit operator */
                        short closelimit;             /**< Max percentage of closinging processes */
                        short closelimitOP;                              /**< closelimit operator */
                        short dnslimit;         /**< Max percentage of processes doing DNS lookup */
                        short dnslimitOP;                                  /**< dnslimit operator */
                        short keepalivelimit;          /**< Max percentage of keepalive processes */
                        short keepalivelimitOP;                      /**< keepalivelimit operator */
                        short replylimit;               /**< Max percentage of replying processes */
                        short replylimitOP;                              /**< replylimit operator */
                        short requestlimit;     /**< Max percentage of processes reading requests */
                        short requestlimitOP;                          /**< requestlimit operator */
                        short startlimit;            /**< Max percentage of processes starting up */
                        short startlimitOP;                              /**< startlimit operator */
                        short waitlimit;  /**< Min percentage of processes waiting for connection */
                        short waitlimitOP;                                /**< waitlimit operator */
                        short gracefullimit;/**< Max percentage of processes gracefully finishing */
                        short gracefullimitOP;                        /**< gracefullimit operator */
                        short cleanuplimit;      /**< Max percentage of processes in idle cleanup */
                        short cleanuplimitOP;                          /**< cleanuplimit operator */
                } ApacheStatus;

                Ssl_T SSL;                                             /**< SSL definition */
                Protocol_T protocol;     /**< Protocol object for testing a port's service */
                Request_T url_request;             /**< Optional url client request object */

                /** For internal use */
                struct myport *next;                               /**< next port in chain */
        } *Port_T;


check_process 関数の実装
------------------------

``check_process`` 関数の実装。
`src/validate.c#L989-L1037 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/validate.c?at=release-5-11-0&fileviewer=file-view-default#validate.c-989:1037>`_

.. code-block:: c
        :linenos: table
        :linenostart: 989

        /**
         * Validate a given process service s. Events are posted according to
         * its configuration. In case of a fatal event FALSE is returned.
         */
        int check_process(Service_T s) {
                pid_t  pid = -1;
                Port_T pp = NULL;
                Resource_T pr = NULL;
                ASSERT(s);
                /* Test for running process */
                if (!(pid = Util_isProcessRunning(s, FALSE))) {
                        Event_post(s, Event_Nonexist, STATE_FAILED, s->action_NONEXIST, "process is not running");
                        return FALSE;
                } else {
                        Event_post(s, Event_Nonexist, STATE_SUCCEEDED, s->action_NONEXIST, "process is running with pid %d", (int)pid);
                }
                /* Reset the exec and timeout errors if active ... the process is running (most probably after manual intervention) */
                if (IS_EVENT_SET(s->error, Event_Exec))
                        Event_post(s, Event_Exec, STATE_SUCCEEDED, s->action_EXEC, "process is running after previous exec error (slow starting or manually recovered?)");
                if (IS_EVENT_SET(s->error, Event_Timeout))
                        for (ActionRate_T ar = s->actionratelist; ar; ar = ar->next)
                                Event_post(s, Event_Timeout, STATE_SUCCEEDED, ar->action, "process is running after previous restart timeout (manually recovered?)");
                if (Run.doprocess) {
                        if (update_process_data(s, ptree, ptreesize, pid)) {
                                check_process_state(s);
                                check_process_pid(s);
                                check_process_ppid(s);
                                if (s->uid)
                                        check_uid(s);
                                if (s->euid)
                                        check_euid(s);
                                if (s->gid)
                                        check_gid(s);
                                if (s->uptimelist)
                                        check_uptime(s);
                                for (pr = s->resourcelist; pr; pr = pr->next)
                                        check_process_resources(s, pr);
                        } else
                                LogError("'%s' failed to get service data\n", s->name);
                }
                /* Test each host:port and protocol in the service's portlist */
                if (s->portlist)
                        /* skip further tests during startup timeout */
                        if (s->start)
                                if (s->inf->priv.process.uptime < s->start->timeout) return TRUE;
                        for (pp = s->portlist; pp; pp = pp->next)
                                check_connection(s, pp);
                return TRUE;
        }


``check_connection`` 関数の実装。
`src/validate.c#L138-L206 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/validate.c?at=release-5-11-0&fileviewer=file-view-default#validate.c-138:206>`_

.. code-block:: c
        :linenos: table
        :linenostart: 138

        /**
         * Test the connection and protocol
         */
        static void check_connection(Service_T s, Port_T p) {
                Socket_T socket;
                volatile int retry_count = p->retry;
                volatile int rv = TRUE;
                char buf[STRLEN];
                char report[STRLEN] = {};
                struct timeval t1;
                struct timeval t2;
                
                ASSERT(s && p);
        retry:
                /* Get time of connection attempt beginning */
                gettimeofday(&t1, NULL);
                
                /* Open a socket to the destination INET[hostname:port] or UNIX[pathname] */
                socket = socket_create(p);
                if (!socket) {
                        snprintf(report, STRLEN, "failed, cannot open a connection to %s", Util_portDescription(p, buf, sizeof(buf)));
                        rv = FALSE;
                        goto error;
                } else {
                        DEBUG("'%s' succeeded connecting to %s\n", s->name, Util_portDescription(p, buf, sizeof(buf)));
                }

                if (p->protocol->check == check_default) {
                        if (socket_is_udp(socket)) {
                                // Only test "connected" UDP sockets without protocol, TCP connect is verified on create
                                if (! socket_is_ready(socket)) {
                                        snprintf(report, STRLEN, "connection failed, %s is not ready for i|o -- %s", Util_portDescription(p, buf, sizeof(buf)), STRERROR);
                                        rv = FALSE;
                                        goto error;
                                }
                        }
                }
                /* Run the protocol verification routine through the socket */
                if (! p->protocol->check(socket)) {
                        snprintf(report, STRLEN, "failed protocol test [%s] at %s -- %s", p->protocol->name, Util_portDescription(p, buf, sizeof(buf)), socket_getError(socket));
                        rv = FALSE;
                        goto error;
                } else {
                        DEBUG("'%s' succeeded testing protocol [%s] at %s\n", s->name, p->protocol->name, Util_portDescription(p, buf, sizeof(buf)));
                }
                
                /* Get time of connection attempt finish */
                gettimeofday(&t2, NULL);
                
                /* Get the response time */
                p->response = (double)(t2.tv_sec - t1.tv_sec) + (double)(t2.tv_usec - t1.tv_usec)/1000000;
                
        error:
                if (socket)
                        socket_free(&socket);
                if (!rv) {
                        if (retry_count-- > 1) {
                                DEBUG("'%s' %s (attempt %d/%d)\n", s->name, report, p->retry - retry_count, p->retry);
                                goto retry;
                        }
                        p->response = -1;
                        p->is_available = FALSE;
                        Event_post(s, Event_Connection, STATE_FAILED, p->action, "%s", report);
                } else {
                        p->is_available = TRUE;
                        Event_post(s, Event_Connection, STATE_SUCCEEDED, p->action, "connection succeeded to %s", Util_portDescription(p, buf, sizeof(buf)));
                }
                
        }

上記の200行と203行で呼んでいる ``Event_post`` 関数やイベントループの処理も気になりますが、この記事が長くなりすぎるので別記事にします。

``Protocol_T`` の型定義。
`src/monit.h#L438-L442 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/monit.h?at=release-5-11-0&fileviewer=file-view-default#monit.h-438:442>`_

.. code-block:: c
        :linenos: table
        :linenostart: 438

        /** Defines a protocol object with protocol functions */
        typedef struct Protocol_T {
                const char *name;                                       /**< Protocol name */
                int(*check)(Socket_T);                 /**< Protocol verification function */
        } *Protocol_T;

``Protocol_T`` 型の配列の値定義。monitで扱うプロトコル一覧。
`src/protocols/protocol.c#L41-L83 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/protocols/protocol.c?at=release-5-11-0&fileviewer=file-view-default#protocol.c-41:83>`_

.. code-block:: c
        :linenos: table
        :linenostart: 41

        static Protocol_T protocols[] = {
                &(struct Protocol_T){"DEFAULT",         check_default},
                &(struct Protocol_T){"HTTP",            check_http},
                &(struct Protocol_T){"FTP",             check_ftp},
                &(struct Protocol_T){"SMTP",            check_smtp},
                &(struct Protocol_T){"POP",             check_pop},
                &(struct Protocol_T){"IMAP",            check_imap},
                &(struct Protocol_T){"NNTP",            check_nntp},
                &(struct Protocol_T){"SSH",             check_ssh},
                &(struct Protocol_T){"DWP",             check_dwp},
                &(struct Protocol_T){"LDAP2",           check_ldap2},
                &(struct Protocol_T){"LDAP3",           check_ldap3},
                &(struct Protocol_T){"RDATE",           check_rdate},
                &(struct Protocol_T){"RSYNC",           check_rsync},
                &(struct Protocol_T){"generic",         check_generic},
                &(struct Protocol_T){"APACHESTATUS",    check_apache_status},
                &(struct Protocol_T){"NTP3",            check_ntp3},
                &(struct Protocol_T){"MYSQL",           check_mysql},
                &(struct Protocol_T){"DNS",             check_dns},
                &(struct Protocol_T){"POSTFIX-POLICY",  check_postfix_policy},
                &(struct Protocol_T){"TNS",             check_tns},
                &(struct Protocol_T){"PGSQL",           check_pgsql},
                &(struct Protocol_T){"CLAMAV",          check_clamav},
                &(struct Protocol_T){"SIP",             check_sip},
                &(struct Protocol_T){"LMTP",            check_lmtp},
                &(struct Protocol_T){"GPS",             check_gps},
                &(struct Protocol_T){"RADIUS",          check_radius},
                &(struct Protocol_T){"MEMCACHE",        check_memcache},
                &(struct Protocol_T){"WEBSOCKET",       check_websocket},
                &(struct Protocol_T){"REDIS",           check_redis},
                &(struct Protocol_T){"MONGODB",         check_mongodb},
                &(struct Protocol_T){"SIEVE",           check_sieve}
        };


        /* ------------------------------------------------------------------ Public */


        Protocol_T Protocol_get(Protocol_Type type) {
                if (type >= sizeof(protocols)/sizeof(protocols[0]))
                        return protocols[0];
                return protocols[type];
        }


check_http 関数の実装
---------------------

``check_http`` 関数の実装。
`src/protocols/http.c#L276-L321 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/protocols/http.c?at=release-5-11-0&fileviewer=file-view-default#http.c-276:321>`_

.. code-block:: c
        :linenos: table
        :linenostart: 276

        int check_http(Socket_T socket) {
                Port_T P;
                char host[STRLEN];
                char auth[STRLEN] = {};
                const char *request = NULL;
                const char *hostheader = NULL;

                ASSERT(socket);

                P = socket_get_Port(socket);

                ASSERT(P);

                request = P->request ? P->request : "/";

                hostheader = _findHostHeaderIn(P->http_headers);
                hostheader = hostheader ? hostheader : P->request_hostheader
                                        ? P->request_hostheader : Util_getHTTPHostHeader(socket, host, STRLEN); // Otherwise use deprecated request_hostheader or default host
                StringBuffer_T sb = StringBuffer_create(168);
                StringBuffer_append(sb,
                                    "GET %s HTTP/1.1\r\n"
                                    "Host: %s\r\n"
                                    "Accept: */*\r\n"
                                    "User-Agent: Monit/%s\r\n"
                                    "%s",
                                    request, hostheader, VERSION,
                                    get_auth_header(P, auth, STRLEN));
                // Add headers if we have them
                if (P->http_headers) {
                        for (list_t p = P->http_headers->head; p; p = p->next) {
                                char *header = p->e;
                                if (Str_startsWith(header, "Host")) // Already set contrived above
                                        continue;
                                StringBuffer_append(sb, "%s\r\n", header);
                        }
                }
                StringBuffer_append(sb, "\r\n");
                int send_status = socket_write(socket, (void*)StringBuffer_toString(sb), StringBuffer_length(sb));
                StringBuffer_free(&sb);
                if (send_status < 0) {
                        socket_setError(socket, "HTTP: error sending data -- %s", STRERROR);
                        return FALSE;
                }

                return check_request(socket, P);
        }


``Socket_T`` の型定義。
`src/socket.c#L85-L103 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/socket.c?at=release-5-11-0&fileviewer=file-view-default#socket.c-85:103>`_

.. code-block:: c
        :linenos: table
        :linenostart: 85

        #define TYPE_LOCAL   0
        #define TYPE_ACCEPT  1
        // One TCP frame data size
        #define RBUFFER_SIZE 1500

        struct Socket_T {
                int port;
                int type;
                int socket;
                char *host;
                Port_T Port;
                int timeout; // milliseconds
                int connection_type;
                ssl_connection *ssl;
                ssl_server_connection *sslserver;
                int length;
                int offset;
                unsigned char buffer[RBUFFER_SIZE + 1];
        };

``check_request`` 関数の実装。
`src/protocols/http.c#L199-L242 <https://bitbucket.org/tildeslash/monit/src/97641b51c99226fbf8862797c8f5ec16ac68a18b/src/protocols/http.c?at=release-5-11-0&fileviewer=file-view-default#http.c-199:242>`_

.. code-block:: c
        :linenos: table
        :linenostart: 199

        /**
         * Check that the server returns a valid HTTP response as well as checksum
         * or content regex if required
         * @param s A socket
         * @return TRUE if the response is valid otherwise FALSE
         */
        static int check_request(Socket_T socket, Port_T P) {
                int status, content_length = -1;
                char buf[LINE_SIZE];
                if (! socket_readln(socket, buf, LINE_SIZE)) {
                        socket_setError(socket, "HTTP: Error receiving data -- %s", STRERROR);
                        return FALSE;
                }
                Str_chomp(buf);
                if (! sscanf(buf, "%*s %d", &status)) {
                        socket_setError(socket, "HTTP error: Cannot parse HTTP status in response: %s", buf);
                        return FALSE;
                }
                if (! Util_evalQExpression(P->operator, status, P->status)) {
                        socket_setError(socket, "HTTP error: Server returned status %d", status);
                        return FALSE;
                }
                /* Get Content-Length header value */
                while (socket_readln(socket, buf, LINE_SIZE)) {
                        if ((buf[0] == '\r' && buf[1] == '\n') || (buf[0] == '\n'))
                                break;
                        Str_chomp(buf);
                        if (Str_startsWith(buf, "Content-Length")) {
                                if (! sscanf(buf, "%*s%*[: ]%d", &content_length)) {
                                        socket_setError(socket, "HTTP error: Parsing Content-Length response header '%s'", buf);
                                        return FALSE;
                                }
                                if (content_length < 0) {
                                        socket_setError(socket, "HTTP error: Illegal Content-Length response header '%s'", buf);
                                        return FALSE;
                                }
                        }
                }
                if (P->url_request && P->url_request->regex && ! do_regex(socket, content_length, P->url_request))
                        return FALSE;
                if (P->request_checksum)
                        return check_request_checksum(socket, content_length, P->request_checksum, P->request_hashtype);
                return TRUE;
        }

`monitのイベントループのコードリーディング </blog/2017/02/20/monit-event-loop-code-reading/>`_ に続きます。
