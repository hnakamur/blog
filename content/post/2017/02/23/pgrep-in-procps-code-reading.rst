procpsのpgrepのコードリーディング
#################################

:date: 2017-02-23 18:30
:tags: pgrep, procps, code-reading
:category: blog
:slug: 2017/02/23/pgrep-in-procps-code-reading

はじめに
--------

`procps-ngのpgrepのコードリーディング <blog/2017/02/23/pgrep-in-procps-ng-code-reading/>`_ に続いて CentOS 6 の pgrep についてもコードリーディングしてみました。
``pgrep`` を含むパッケージは ``procps`` でバージョンは3.2.8でした。

.. code-block:: console

    [root@centos6 ~]# rpm -qf `which pgrep`
    procps-3.2.8-36.el6.x86_64

``procps`` のプロジェクトページは `procps - Home Page <http://procps.sourceforge.net/>`_ で、
`SourceForge.net Repository - [procps] Index of / <http://procps.cvs.sourceforge.net/viewvc/procps/>`_ でソースコードが見られます。

一方で以下のコマンドで srpm をダウンロードしてそこから ``pgrep.c`` を取り出しました。

.. code-block:: console

    [root@centos6 ~]# curl -sO http://vault.centos.org/6.8/os/Source/SPackages/procps-3.2.8-36.el6.src.rpm
    [root@centos6 ~]# mkdir procps-srpm
    [root@centos6 ~]# rpm2cpio procps-3.2.8-36.el6.src.rpm | (cd procps-srpm && cpio -idm --quiet)
    [root@centos6 ~]# tar xf procps-srpm/procps-3.2.8.tar.gz -C procps-srpm

`SourceForge.net Repository - [procps] Log of /procps/pgrep.c <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?view=log>`_ の各リビジョンと上記で取り出した ``pgrep.c`` を比較したところ `SourceForge.net Repository - [procps] Contents of /procps/pgrep.c revision 1.29 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?revision=1.29&view=markup>`_ と一致していました。

pgrep.cのコードリーディング
---------------------------

``main`` 関数の実装。
`pgrep.c#L709-#L732 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?revision=1.29&view=markup#l709>`_

.. code-block:: c
    :linenos: table
    :linenostart: 709

    int main (int argc, char *argv[])
    {
    	union el *procs;
    	int num;

    	parse_opts (argc, argv);

    	procs = select_procs (&num);
    	if (i_am_pkill) {
    		int i;
    		for (i = 0; i < num; i++) {
    			if (kill (procs[i].num, opt_signal) != -1) continue;
    			if (errno==ESRCH) continue; // gone now, which is OK
    			fprintf (stderr, "pkill: %ld - %s\n",
    				 procs[i].num, strerror (errno));
    		}
    	} else {
    		if (opt_long)
    			output_strlist(procs,num);
    		else
    			output_numlist(procs,num);
    	}
    	return !num; // exit(EXIT_SUCCESS) if match, otherwise exit(EXIT_FAILURE)
    }



``parse_opts`` 関数の実装。
`pgrep.c#L539-#L706 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?revision=1.29&view=markup#l539>`_

.. code-block:: c
    :linenos: table
    :linenostart: 539

    static void parse_opts (int argc, char **argv)
    {
    	char opts[32] = "";
    	int opt;
    	int criteria_count = 0;

    	if (strstr (argv[0], "pkill")) {
    		i_am_pkill = 1;
    		progname = "pkill";
    		/* Look for a signal name or number as first argument */
    		if (argc > 1 && argv[1][0] == '-') {
    			int sig;
    			sig = signal_name_to_number (argv[1] + 1);
    			if (sig == -1 && isdigit (argv[1][1]))
    				sig = atoi (argv[1] + 1);
    			if (sig != -1) {
    				int i;
    				for (i = 2; i < argc; i++)
    					argv[i-1] = argv[i];
    				--argc;
    				opt_signal = sig;
    			}
    		}
    	} else {
    		/* These options are for pgrep only */
    		strcat (opts, "ld:");
    	}
    			
    	strcat (opts, "LF:fnovxP:g:s:u:U:G:t:?V");
    	
    	while ((opt = getopt (argc, argv, opts)) != -1) {
    		switch (opt) {
    //		case 'D':   // FreeBSD: print info about non-matches for debugging
    //			break;
    		case 'F':   // FreeBSD: the arg is a file containing a PID to match
    			opt_pidfile = strdup (optarg);
    			++criteria_count;
    			break;
    		case 'G':   // Solaris: match rgid/rgroup
    	  		opt_rgid = split_list (optarg, conv_gid);
    			if (opt_rgid == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    //		case 'I':   // FreeBSD: require confirmation before killing
    //			break;
    //		case 'J':   // Solaris: match by project ID (name or number)
    //			break;
    		case 'L':   // FreeBSD: fail if pidfile (see -F) not locked
    			opt_lock++;
    			break;
    //		case 'M':   // FreeBSD: specify core (OS crash dump) file
    //			break;
    //		case 'N':   // FreeBSD: specify alternate namelist file (for us, System.map -- but we don't need it)
    //			break;
    		case 'P':   // Solaris: match by PPID
    	  		opt_ppid = split_list (optarg, conv_num);
    			if (opt_ppid == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    //		case 'S':   // FreeBSD: don't ignore the built-in kernel tasks
    //			break;
    //		case 'T':   // Solaris: match by "task ID" (probably not a Linux task)
    //			break;
    		case 'U':   // Solaris: match by ruid/rgroup
    	  		opt_ruid = split_list (optarg, conv_uid);
    			if (opt_ruid == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    		case 'V':
    			fprintf(stdout, "%s (%s)\n", progname, procps_version);
    			exit(EXIT_SUCCESS);
    //		case 'c':   // Solaris: match by contract ID
    //			break;
    		case 'd':   // Solaris: change the delimiter
    			opt_delim = strdup (optarg);
    			break;
    		case 'f':   // Solaris: match full process name (as in "ps -f")
    			opt_full = 1;
    			break;
    		case 'g':   // Solaris: match pgrp
    	  		opt_pgrp = split_list (optarg, conv_pgrp);
    			if (opt_pgrp == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    //		case 'i':   // FreeBSD: ignore case. OpenBSD: withdrawn. See -I. This sucks.
    //			if (opt_case)
    //				usage (opt);
    //			opt_case = REG_ICASE;
    //			break;
    //		case 'j':   // FreeBSD: restricted to the given jail ID
    //			break;
    		case 'l':   // Solaris: long output format (pgrep only) Should require -f for beyond argv[0] maybe?
    			opt_long = 1;
    			break;
    		case 'n':   // Solaris: match only the newest
    			if (opt_oldest|opt_negate|opt_newest)
    				usage (opt);
    			opt_newest = 1;
    			++criteria_count;
    			break;
    		case 'o':   // Solaris: match only the oldest
    			if (opt_oldest|opt_negate|opt_newest)
    				usage (opt);
    			opt_oldest = 1;
    			++criteria_count;
    			break;
    		case 's':   // Solaris: match by session ID -- zero means self
    	  		opt_sid = split_list (optarg, conv_sid);
    			if (opt_sid == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    		case 't':   // Solaris: match by tty
    	  		opt_term = split_list (optarg, conv_str);
    			if (opt_term == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    		case 'u':   // Solaris: match by euid/egroup
    	  		opt_euid = split_list (optarg, conv_uid);
    			if (opt_euid == NULL)
    				usage (opt);
    			++criteria_count;
    			break;
    		case 'v':   // Solaris: as in grep, invert the matching (uh... applied after selection I think)
    			if (opt_oldest|opt_negate|opt_newest)
    				usage (opt);
    	  		opt_negate = 1;
    			break;
    		// OpenBSD -x, being broken, does a plain string
    		case 'x':   // Solaris: use ^(regexp)$ in place of regexp (FreeBSD too)
    			opt_exact = 1;
    			break;
    //		case 'z':   // Solaris: match by zone ID
    //			break;
    		case '?':
    			usage (opt);
    			break;
    		}
    	}

    	if(opt_lock && !opt_pidfile){
    		fprintf(stderr, "%s: -L without -F makes no sense\n",progname);
    		usage(0);
    	}

    	if(opt_pidfile){
    		opt_pid = read_pidfile();
    		if(!opt_pid){
    			fprintf(stderr, "%s: pidfile not valid\n",progname);
    			usage(0);
    		}
    	}

            if (argc - optind == 1)
    		opt_pattern = argv[optind];
    	else if (argc - optind > 1)
    		usage (0);
    	else if (criteria_count == 0) {
    		fprintf (stderr, "%s: No matching criteria specified\n",
    			 progname);
    		usage (0);
    	}
    }

``-f`` オプションで ``opt_full = 1;`` が実行され ``-l`` オプションで ``opt_long = 1;`` が実行されます。


``output_strlist`` 関数の実装。
`pgrep.c#L343-#L353 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?revision=1.29&view=markup#l343>`_

.. code-block:: c
    :linenos: table
    :linenostart: 343

    static void output_strlist (const union el *restrict list, int num)
    {
    // FIXME: escape codes
    	int i;
    	const char *delim = opt_delim;
    	for (i = 0; i < num; i++) {
    		if(i+1==num)
    			delim = "\n";
    		printf ("%s%s", list[i].str, delim);
    	}
    }

``select_procs`` 関数の実装。
`pgrep.c#L416-#L536 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/pgrep.c?revision=1.29&view=markup#l416>`_

.. code-block:: c
    :linenos: table
    :linenostart: 416

    static union el * select_procs (int *num)
    {
    	PROCTAB *ptp;
    	proc_t task;
    	unsigned long long saved_start_time;      // for new/old support
    	pid_t saved_pid = 0;                      // for new/old support
    	int matches = 0;
    	int size = 0;
    	regex_t *preg;
    	pid_t myself = getpid();
    	union el *list = NULL;
    	char cmd[4096];

    	ptp = do_openproc();
    	preg = do_regcomp();

    	if (opt_newest) saved_start_time =  0ULL;
    	if (opt_oldest) saved_start_time = ~0ULL;
    	if (opt_newest) saved_pid = 0;
    	if (opt_oldest) saved_pid = INT_MAX;
    	
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
    		if (opt_long || (match && opt_pattern)) {
    			if (opt_full && task.cmdline) {
    				int i = 0;
    				int bytes = sizeof (cmd) - 1;

    				/* make sure it is always NUL-terminated */
    				cmd[bytes] = 0;
    				/* make room for SPC in loop below */
    				--bytes;

    				strncpy (cmd, task.cmdline[i], bytes);
    				bytes -= strlen (task.cmdline[i++]);
    				while (task.cmdline[i] && bytes > 0) {
    					strncat (cmd, " ", bytes);
    					strncat (cmd, task.cmdline[i], bytes);
    					bytes -= strlen (task.cmdline[i++]) + 1;
    				}
    			} else {
    				strcpy (cmd, task.cmd);
    			}
    		}

    		if (match && opt_pattern) {
    			if (regexec (preg, cmd, 0, NULL, 0) != 0)
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
    				list = realloc(list, size * sizeof *list);
    				if (list == NULL)
    					exit (EXIT_FATAL);
    			}
    			if (opt_long) {
    				char buff[5096];  // FIXME
    				sprintf (buff, "%d %s", task.XXXID, cmd);
    				list[matches++].str = strdup (buff);
    			} else {
    				list[matches++].num = task.XXXID;
    			}
    		}
    		
    		memset (&task, 0, sizeof (task));
    	}
    	closeproc (ptp);

    	*num = matches;
    	return list;
    }

``stat2proc`` 関数の実装。
`proc/readproc.c#L336-#L356 <http://procps.cvs.sourceforge.net/viewvc/procps/procps/proc/readproc.c?revision=1.56&view=markup#l336>`_

.. code-block:: c
    :linenos: table
    :linenostart: 336

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
        S = tmp + 2;                 // skip ") "

ということで ``/proc/${PID}/stat`` の出力の ``(`` と ``)`` の間が ``task.cmd`` に設定され、 ``-f`` を指定しない場合はこれがマッチの対象になります。
``-f`` を設定した場合はコマンドライン全体がマッチの対象になります。
