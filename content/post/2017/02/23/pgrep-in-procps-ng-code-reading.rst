procps-ngのpgrepのコードリーディング
####################################

:date: 2017-02-23 00:20
:tags: pgrep, procps-ng, code-reading
:category: blog
:slug: 2017/02/23/pgrep-in-procps-ng-code-reading

はじめに
--------

CentOS 7の環境でApache Traffic Server 7.0.0のサービスを起動すると ``traffic_cop``, ``traffic_manager``, ``traffic_server`` という3つのプロセスが立ち上がります。

.. code-block:: console

        [root@ats7 ~]# ps auxww | grep traffic
        root     20837  0.0  0.0 143076  6276 ?        Ssl  15:14   0:00 /opt/trafficserver/bin/traffic_cop
        ats      20838  0.0  0.0 448784 11960 ?        Sl   15:14   0:00 /opt/trafficserver/bin/traffic_manager --bind_stdout /opt/trafficserver/var/logs/traffic.out --bind_stderr /opt/trafficserver/var/logs/traffic.out
        ats      20877  0.0  0.3 1047868 55464 ?       Sl   15:14   0:00 /opt/trafficserver/bin/traffic_server -M --bind_stdout /opt/trafficserver/var/logs/traffic.out --bind_stderr /opt/trafficserver/var/logs/traffic.out --httpport 8080:fd=9,8080:fd=10:ipv6
        root     20992  0.0  0.0   9040   852 ?        S+   15:15   0:00 grep --color=auto traffic

しかし ``pgrep -a traffic`` で検索すると ``traffic_cop`` と ``traffic_manager`` のみが表示されました。

.. code-block:: console

        [root@ats7 ~]# pgrep -a traffic
        20837 /opt/trafficserver/bin/traffic_cop
        20838 /opt/trafficserver/bin/traffic_manager --bind_stdout /opt/trafficserver/var/logs/traffic.out --bind_stderr /opt/trafficserver/var/logs/traffic.out

``pgrep`` を含むパッケージは ``procps-ng`` でバージョンは3.3.10でした。

.. code-block:: console

        [root@ats7 ~]# rpm -qf `which pgrep`
        procps-ng-3.3.10-10.el7.x86_64

``procps-ng`` のレポジトリは `procps-ng / procps · GitLab <https://gitlab.com/procps-ng/procps>`_ です。

pgrep.cのコードリーディング
---------------------------

``main`` 関数の実装。
`pgrep.c#L902-#L944 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/pgrep.c#L902-944>`_

.. code-block:: c
    :linenos: table
    :linenostart: 902

    int main (int argc, char **argv)
    {
    	struct el *procs;
    	int num;

    #ifdef HAVE_PROGRAM_INVOCATION_NAME
    	program_invocation_name = program_invocation_short_name;
    #endif
    	setlocale (LC_ALL, "");
    	bindtextdomain(PACKAGE, LOCALEDIR);
    	textdomain(PACKAGE);
    	atexit(close_stdout);

    	parse_opts (argc, argv);

    	procs = select_procs (&num);
    	if (i_am_pkill) {
    		int i;
    		for (i = 0; i < num; i++) {
    			if (kill (procs[i].num, opt_signal) != -1) {
    				if (opt_echo)
    					printf(_("%s killed (pid %lu)\n"), procs[i].str, procs[i].num);
    				continue;
    			}
    			if (errno==ESRCH)
    				 /* gone now, which is OK */
    				continue;
    			xwarn(_("killing pid %ld failed"), procs[i].num);
    		}
    		if (opt_count)
    			fprintf(stdout, "%d\n", num);
    	} else {
    		if (opt_count) {
    			fprintf(stdout, "%d\n", num);
    		} else {
    			if (opt_long || opt_longlong)
    				output_strlist (procs,num);
    			else
    				output_numlist (procs,num);
    		}
    	}
    	return !num; /* exit(EXIT_SUCCESS) if match, otherwise exit(EXIT_FAILURE) */
    }

``parse_opts`` 関数の実装。
`pgrep.c#L677-#L899 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/pgrep.c#L677-899>`_

.. code-block:: c
    :linenos: table
    :linenostart: 677

    static void parse_opts (int argc, char **argv)
    {
    	char opts[32] = "";
    	int opt;
    	int criteria_count = 0;

    	enum {
    		SIGNAL_OPTION = CHAR_MAX + 1,
    		NS_OPTION,
    		NSLIST_OPTION,
    	};
    	static const struct option longopts[] = {
    		{"signal", required_argument, NULL, SIGNAL_OPTION},
    		{"count", no_argument, NULL, 'c'},
    		{"delimiter", required_argument, NULL, 'd'},
    		{"list-name", no_argument, NULL, 'l'},
    		{"list-full", no_argument, NULL, 'a'},
    		{"full", no_argument, NULL, 'f'},
    		{"pgroup", required_argument, NULL, 'g'},
    		{"group", required_argument, NULL, 'G'},
    		{"newest", no_argument, NULL, 'n'},
    		{"oldest", no_argument, NULL, 'o'},
    		{"parent", required_argument, NULL, 'P'},
    		{"session", required_argument, NULL, 's'},
    		{"terminal", required_argument, NULL, 't'},
    		{"euid", required_argument, NULL, 'u'},
    		{"uid", required_argument, NULL, 'U'},
    		{"inverse", no_argument, NULL, 'v'},
    		{"lightweight", no_argument, NULL, 'w'},
    		{"exact", no_argument, NULL, 'x'},
    		{"pidfile", required_argument, NULL, 'F'},
    		{"logpidfile", no_argument, NULL, 'L'},
    		{"echo", no_argument, NULL, 'e'},
    		{"ns", required_argument, NULL, NS_OPTION},
    		{"nslist", required_argument, NULL, NSLIST_OPTION},
    		{"help", no_argument, NULL, 'h'},
    		{"version", no_argument, NULL, 'V'},
    		{NULL, 0, NULL, 0}
    	};

    	if (strstr (program_invocation_short_name, "pkill")) {
    		int sig;
    		i_am_pkill = 1;
    		sig = signal_option(&argc, argv);
    		if (-1 < sig)
    			opt_signal = sig;
    		/* These options are for pkill only */
    		strcat (opts, "e");
    	} else {
    		/* These options are for pgrep only */
    		strcat (opts, "lad:vw");
    	}

    	strcat (opts, "LF:cfnoxP:g:s:u:U:G:t:?Vh");

    	while ((opt = getopt_long (argc, argv, opts, longopts, NULL)) != -1) {
    		switch (opt) {
    		case SIGNAL_OPTION:
    			opt_signal = signal_name_to_number (optarg);
    			if (opt_signal == -1 && isdigit (optarg[0]))
    				opt_signal = atoi (optarg);
    			break;
    		case 'e':
    			opt_echo = 1;
    			break;
    /*		case 'D':   / * FreeBSD: print info about non-matches for debugging * /
     *			break; */
    		case 'F':   /* FreeBSD: the arg is a file containing a PID to match */
    			opt_pidfile = xstrdup (optarg);
    			++criteria_count;
    			break;
    		case 'G':   /* Solaris: match rgid/rgroup */
    			opt_rgid = split_list (optarg, conv_gid);
    			if (opt_rgid == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    /*		case 'I':   / * FreeBSD: require confirmation before killing * /
     *			break; */
    /*		case 'J':   / * Solaris: match by project ID (name or number) * /
     *			break; */
    		case 'L':   /* FreeBSD: fail if pidfile (see -F) not locked */
    			opt_lock++;
    			break;
    /*		case 'M':   / * FreeBSD: specify core (OS crash dump) file * /
     *			break; */
    /*		case 'N':   / * FreeBSD: specify alternate namelist file (for us, System.map -- but we don't need it) * /
     *			break; */
    		case 'P':   /* Solaris: match by PPID */
    			opt_ppid = split_list (optarg, conv_num);
    			if (opt_ppid == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    /*		case 'S':   / * FreeBSD: don't ignore the built-in kernel tasks * /
     *			break; */
    /*		case 'T':   / * Solaris: match by "task ID" (probably not a Linux task) * /
     *			break; */
    		case 'U':   /* Solaris: match by ruid/rgroup */
    			opt_ruid = split_list (optarg, conv_uid);
    			if (opt_ruid == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    		case 'V':
    			printf(PROCPS_NG_VERSION);
    			exit(EXIT_SUCCESS);
    /*		case 'c':   / * Solaris: match by contract ID * /
     *			break; */
    		case 'c':
    			opt_count = 1;
    			break;
    		case 'd':   /* Solaris: change the delimiter */
    			opt_delim = xstrdup (optarg);
    			break;
    		case 'f':   /* Solaris: match full process name (as in "ps -f") */
    			opt_full = 1;
    			break;
    		case 'g':   /* Solaris: match pgrp */
    			opt_pgrp = split_list (optarg, conv_pgrp);
    			if (opt_pgrp == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    /*		case 'i':   / * FreeBSD: ignore case. OpenBSD: withdrawn. See -I. This sucks. * /
     *			if (opt_case)
     *				usage (opt);
     *			opt_case = REG_ICASE;
     *			break; */
    /*		case 'j':   / * FreeBSD: restricted to the given jail ID * /
     *			break; */
    		case 'l':   /* Solaris: long output format (pgrep only) Should require -f for beyond argv[0] maybe? */
    			opt_long = 1;
    			break;
    		case 'a':
    			opt_longlong = 1;
    			break;
    		case 'n':   /* Solaris: match only the newest */
    			if (opt_oldest|opt_negate|opt_newest)
    				usage ('?');
    			opt_newest = 1;
    			++criteria_count;
    			break;
    		case 'o':   /* Solaris: match only the oldest */
    			if (opt_oldest|opt_negate|opt_newest)
    				usage ('?');
    			opt_oldest = 1;
    			++criteria_count;
    			break;
    		case 's':   /* Solaris: match by session ID -- zero means self */
    			opt_sid = split_list (optarg, conv_sid);
    			if (opt_sid == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    		case 't':   /* Solaris: match by tty */
    			opt_term = split_list (optarg, conv_str);
    			if (opt_term == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    		case 'u':   /* Solaris: match by euid/egroup */
    			opt_euid = split_list (optarg, conv_uid);
    			if (opt_euid == NULL)
    				usage ('?');
    			++criteria_count;
    			break;
    		case 'v':   /* Solaris: as in grep, invert the matching (uh... applied after selection I think) */
    			if (opt_oldest|opt_negate|opt_newest)
    				usage ('?');
    			opt_negate = 1;
    			break;
    		case 'w':   // Linux: show threads (lightweight process) too
    			opt_threads = 1;
    			break;
    		/* OpenBSD -x, being broken, does a plain string */
    		case 'x':   /* Solaris: use ^(regexp)$ in place of regexp (FreeBSD too) */
    			opt_exact = 1;
    			break;
    /*		case 'z':   / * Solaris: match by zone ID * /
     *			break; */
    		case NS_OPTION:
    			opt_ns_pid = atoi(optarg);
    			if (opt_ns_pid == 0)
    				usage ('?');
    			++criteria_count;
    			break;
    		case NSLIST_OPTION:
    			opt_nslist = split_list (optarg, conv_ns);
    			if (opt_nslist == NULL)
    				usage ('?');
    			break;
    		case 'h':
    		case '?':
    			usage (opt);
    			break;
    		}
    	}

    	if(opt_lock && !opt_pidfile)
    		xerrx(EXIT_USAGE, _("-L without -F makes no sense\n"
    				     "Try `%s --help' for more information."),
    				     program_invocation_short_name);

    	if(opt_pidfile){
    		opt_pid = read_pidfile();
    		if(!opt_pid)
    			xerrx(EXIT_FAILURE, _("pidfile not valid\n"
    					     "Try `%s --help' for more information."),
    					     program_invocation_short_name);
    	}

    	if (argc - optind == 1)
    		opt_pattern = argv[optind];
    	else if (argc - optind > 1)
    		xerrx(EXIT_USAGE, _("only one pattern can be provided\n"
    				     "Try `%s --help' for more information."),
    				     program_invocation_short_name);
    	else if (criteria_count == 0)
    		xerrx(EXIT_USAGE, _("no matching criteria specified\n"
    				     "Try `%s --help' for more information."),
    				     program_invocation_short_name);
    }

``parse_opts`` 関数の811〜812行目で ``-a`` を指定すると ``opt_longlong = 1`` と設定されることがわかります。
``main`` 関数を見ると ``pgrep`` で ``-a`` を指定した場合は ``opt_count`` は 0 で ``opt_longlong`` が 1なので、938行目の ``output_strlist`` が呼ばれます。

``output_strlist`` 関数の実装。
`pgrep.c#L410-#L420 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/pgrep.c#L410-420>`_

.. code-block:: c
    :linenos: table
    :linenostart: 410

    static void output_strlist (const struct el *restrict list, int num)
    {
    /* FIXME: escape codes */
    	int i;
    	const char *delim = opt_delim;
    	for (i = 0; i < num; i++) {
    		if(i+1==num)
    			delim = "\n";
    		printf ("%lu %s%s", list[i].num, list[i].str, delim);
    	}
    }

ここは単に出力しているだけでした。

``struct el`` の定義。
`pgrep.c#L60-#L63 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/pgrep.c#L60-63>`_

.. code-block:: c
    :linenos: table
    :linenostart: 60

    struct el {
    	long	num;
    	char *	str;
    };

``main`` 関数の917行目の ``select_procs`` 関数が中核です。

``select_procs`` 関数の実装。
`pgrep.c#L482-#L655 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/pgrep.c#L482-655>`_

.. code-block:: c
    :linenos: table
    :linenostart: 482

    static struct el * select_procs (int *num)
    {
    	PROCTAB *ptp;
    	proc_t task;
    	unsigned long long saved_start_time;      /* for new/old support */
    	pid_t saved_pid = 0;                      /* for new/old support */
    	int matches = 0;
    	int size = 0;
    	regex_t *preg;
    	pid_t myself = getpid();
    	struct el *list = NULL;
    	char cmdline[CMDSTRSIZE];
    	char cmdsearch[CMDSTRSIZE];
    	char cmdoutput[CMDSTRSIZE];
    	proc_t ns_task;

    	ptp = do_openproc();
    	preg = do_regcomp();

    	if (opt_newest) saved_start_time =  0ULL;
    	else saved_start_time = ~0ULL;

    	if (opt_newest) saved_pid = 0;
    	if (opt_oldest) saved_pid = INT_MAX;
    	if (opt_ns_pid && ns_read(opt_ns_pid, &ns_task)) {
    		fputs(_("Error reading reference namespace information\n"),
    		      stderr);
    		exit (EXIT_FATAL);
    	}

    	memset(&task, 0, sizeof (task));
    	while(readproc(ptp, &task)) {
    		int match = 1;

    		if (task.XXXID == myself)
    			continue;
    		else if (opt_newest && task.start_time < saved_start_time)
    			match = 0;
    		else if (opt_oldest && task.start_time > saved_start_time)
    			match = 0;
    		else if (opt_ppid && ! match_numlist (task.ppid, opt_ppid))
    			match = 0;
    		else if (opt_pid && ! match_numlist (task.tgid, opt_pid))
    			match = 0;
    		else if (opt_pgrp && ! match_numlist (task.pgrp, opt_pgrp))
    			match = 0;
    		else if (opt_euid && ! match_numlist (task.euid, opt_euid))
    			match = 0;
    		else if (opt_ruid && ! match_numlist (task.ruid, opt_ruid))
    			match = 0;
    		else if (opt_rgid && ! match_numlist (task.rgid, opt_rgid))
    			match = 0;
    		else if (opt_sid && ! match_numlist (task.session, opt_sid))
    			match = 0;
    		else if (opt_ns_pid && ! match_ns (&task, &ns_task))
    			match = 0;
    		else if (opt_term) {
    			if (task.tty == 0) {
    				match = 0;
    			} else {
    				char tty[256];
    				dev_to_tty (tty, sizeof(tty) - 1,
    					    task.tty, task.XXXID, ABBREV_DEV);
    				match = match_strlist (tty, opt_term);
    			}
    		}
    		if (task.cmdline && (opt_longlong || opt_full) ) {
    			int i = 0;
    			int bytes = sizeof (cmdline) - 1;

    			/* make sure it is always NUL-terminated */
    			cmdline[bytes] = 0;
    			/* make room for SPC in loop below */
    			--bytes;

    			strncpy (cmdline, task.cmdline[i], bytes);
    			bytes -= strlen (task.cmdline[i++]);
    			while (task.cmdline[i] && bytes > 0) {
    				strncat (cmdline, " ", bytes);
    				strncat (cmdline, task.cmdline[i], bytes);
    				bytes -= strlen (task.cmdline[i++]) + 1;
    			}
    		}

    		if (opt_long || opt_longlong || (match && opt_pattern)) {
    			if (opt_longlong && task.cmdline)
    				strncpy (cmdoutput, cmdline, CMDSTRSIZE);
    			else
    				strncpy (cmdoutput, task.cmd, CMDSTRSIZE);
    		}

    		if (match && opt_pattern) {
    			if (opt_full && task.cmdline)
    				strncpy (cmdsearch, cmdline, CMDSTRSIZE);
    			else
    				strncpy (cmdsearch, task.cmd, CMDSTRSIZE);

    			if (regexec (preg, cmdsearch, 0, NULL, 0) != 0)
    				match = 0;
    		}

    		if (match ^ opt_negate) {	/* Exclusive OR is neat */
    			if (opt_newest) {
    				if (saved_start_time == task.start_time &&
    				    saved_pid > task.XXXID)
    					continue;
    				saved_start_time = task.start_time;
    				saved_pid = task.XXXID;
    				matches = 0;
    			}
    			if (opt_oldest) {
    				if (saved_start_time == task.start_time &&
    				    saved_pid < task.XXXID)
    					continue;
    				saved_start_time = task.start_time;
    				saved_pid = task.XXXID;
    				matches = 0;
    			}
    			if (matches == size) {
    				size = size * 5 / 4 + 4;
    				list = xrealloc(list, size * sizeof *list);
    			}
    			if (list && (opt_long || opt_longlong || opt_echo)) {
    				list[matches].num = task.XXXID;
    				list[matches++].str = xstrdup (cmdoutput);
    			} else if (list) {
    				list[matches++].num = task.XXXID;
    			} else {
    				xerrx(EXIT_FAILURE, _("internal error"));
    			}

    			// pkill does not need subtasks!
    			// this control is still done at
    			// argparse time, but a further
    			// control is free
    			if (opt_threads && !i_am_pkill) {
    				proc_t subtask;
    				memset(&subtask, 0, sizeof (subtask));
    				while (readtask(ptp, &task, &subtask)){
    					// don't add redundand tasks
    					if (task.XXXID == subtask.XXXID)
    						continue;

    					// eventually grow output buffer
    					if (matches == size) {
    						size = size * 5 / 4 + 4;
    						list = realloc(list, size * sizeof *list);
    						if (list == NULL)
    							exit (EXIT_FATAL);
    					}
    					if (opt_long) {
    						list[matches].str = xstrdup (cmdoutput);
    						list[matches++].num = subtask.XXXID;
    					} else {
    						list[matches++].num = subtask.XXXID;
    					}
    					memset(&subtask, 0, sizeof (subtask));
    				}
    			}



    		}





    		memset (&task, 0, sizeof (task));
    	}
    	closeproc (ptp);
    	*num = matches;
    	return list;
    }

574〜580行目で ``opt_full`` が0以外かつ ``task.cmdline`` がNULL以外なら ``cmdline`` が、そうでなければ ``task.cmd`` が検索対象になることがわかりました。

呼び出しの途中は省略しますが、 ``stat2proc`` 関数の実装（抜粋）
`proc/readproc.c#L548-#L567 <https://gitlab.com/procps-ng/procps/blob/v3.3.10/proc/readproc.c#L548-567>`_
を見ると ``task.cmd`` は ``/proc/*/stat`` の ``(`` と ``)`` の間の部分になることがわかりました。

.. code-block:: c
    :linenos: table
    :linenostart: 548

    // Reads /proc/*/stat files, being careful not to trip over processes with
    // names like ":-) 1 2 3 4 5 6".
    static void stat2proc(const char* S, proc_t *restrict P) {
        unsigned num;
        char* tmp;

    ENTER(0x160);

        /* fill in default values for older kernels */
        P->processor = 0;
        P->rtprio = -1;
        P->sched = -1;
        P->nlwp = 0;

        S = strchr(S, '(') + 1;
        tmp = strrchr(S, ')');
        num = tmp - S;
        if(unlikely(num >= sizeof P->cmd)) num = sizeof P->cmd - 1;
        memcpy(P->cmd, S, num);
        P->cmd[num] = '\0';

``ps auxww | grep traffic`` と ``cat /proc/${PID}/stat`` の結果を比べてみました。

.. code-block:: console
    :linenos: table

    [root@ats7 ~]# cat /proc/20837/stat
    20837 (traffic_cop) S 1 20837 20837 0 -1 1077936384 489 0 6 0 4 24 0 0 20 0 2 0 553918400 146509824 1569 18446744073709551615 94079978950656 94079979051376 140726768039552 140726768030720 140350454315997 0 0 3674113 91342 0 0 0 17 0 0 0 9 0 0 94079981152352 94079981203568 94079988858880 140726768041851 140726768041886 140726768041886 140726768041941 0
    [root@ats7 ~]# cat /proc/20838/stat
    20838 (traffic_manager) S 20837 20837 20837 0 -1 4194560 1461 0 1 0 472 63 0 0 20 0 6 0 553918413 459685888 2990 18446744073709551615 94657453907968 94657455120371 140723571977072 140723571830272 139779374492579 0 2147193488 3670016 93263 0 0 0 17 1 0 0 0 0 0 94657457217984 94657457272704 94657464983552 140723571982087 140723571982234 140723571982234 140723571982289 0
    [root@ats7 ~]# cat /proc/20877/stat
    20877 ([TS_MAIN]) S 20838 20837 20837 0 -1 1077936384 26656 0 0 0 1108 3458 0 0 20 0 20 0 553918517 1140125696 13869 18446744073709551615 94103198183424 94103202477292 140734131727600 140734131721984 46982532413037 0 0 3674113 20222 0 0 0 17 0 0 0 1 0 0 94103204576832 94103204684656 94103237705728 140734131732164 140734131732350 140734131732350 140734131732434 0
    [root@ats7 ~]# cat /proc/20878/stat
    20878 (traffic_server) S 20838 20837 20837 0 -1 1077936448 26787 0 0 0 1115 3478 0 0 20 0 20 0 553918520 1140125696 13870 18446744073709551615 94103198183424 94103202477292 140734131727600 46982562638768 46982532413037 0 2147193488 3674113 20222 0 0 0 -1 1 0 0 0 0 0 94103204576832 94103204684656 94103237705728 140734131732164 140734131732350 140734131732350 140734131732434 0

20877 のプロセスは ``ps auxww`` で見るとコマンドラインのコマンド部分は ``/opt/trafficserver/bin/traffic_server`` となっていますが、
``/proc/20877/stat`` の ``(`` と ``)`` の間は ``[TS_MAIN]`` となっているので ``pgrep`` では検索がマッチせず出力されないんですね。

試しに ``/proc/20878/stat`` を見るとそちらは ``(`` と ``)`` の間が ``traffic_server`` となっていました。
が、 ``ps auxww`` で見ると PID=20878 のプロセスは存在していませんでした。

以下のように ``pgrep -fa traffic`` にすれば ``traffic_server`` もマッチしました。コマンドライン全体でマッチするので指定した文字列が引数に含まれる場合もマッチになる点が要注意ですが、必要なものがマッチしないよりはこちらのほうが良いと思います。

.. code-block:: console
    :linenos: table

    [root@ats7 ~]# pgrep -fa traffic
    20837 /opt/trafficserver/bin/traffic_cop
    20838 /opt/trafficserver/bin/traffic_manager --bind_stdout /opt/trafficserver/var/logs/traffic.out --bind_stderr /opt/trafficserver/var/logs/traffic.out
    20877 /opt/trafficserver/bin/traffic_server -M --bind_stdout /opt/trafficserver/var/logs/traffic.out --bind_stderr /opt/trafficserver/var/logs/traffic.out --httpport 8080:fd=9,8080:fd=10:ipv6

