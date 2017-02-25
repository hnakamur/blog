iptables-restoreのコードリーディング
####################################

:date: 2017-02-24 00:25
:tags: iptables, code-reading
:category: blog
:slug: 2017/02/24/iptables-restore-code-reading

はじめに
--------

``iptables-restore`` のコードリーディングをしてみました。
対象バージョンは CentOS 7 のパッケージに合わせて 1.4.21 です。

.. code-block:: console

    $ rpm -qf `which iptables-restore`
    iptables-1.4.21-17.el7.x86_64

プロジェクトページは `netfilter/iptables project homepage - The netfilter.org project <http://www.netfilter.org/>`_ で、
ブラウザで見られるレポジトリは `iptables - iptables tree <https://git.netfilter.org/iptables/>`_ です。

main関数からの流れ
------------------

``main`` 関数の定義。
`xtables-multi.c#L16-#L41 <https://git.netfilter.org/iptables/tree/xtables-multi.c?id=482c6d3731e2681cb4baae835c294840300197e6#n16>`_

.. code-block:: c
    :linenos: table
    :linenostart: 16

    static const struct subcommand multi_subcommands[] = {
    #ifdef ENABLE_IPV4
    	{"iptables",            iptables_main},
    	{"main4",               iptables_main},
    	{"iptables-save",       iptables_save_main},
    	{"save4",               iptables_save_main},
    	{"iptables-restore",    iptables_restore_main},
    	{"restore4",            iptables_restore_main},
    #endif
    	{"iptables-xml",        iptables_xml_main},
    	{"xml",                 iptables_xml_main},
    #ifdef ENABLE_IPV6
    	{"ip6tables",           ip6tables_main},
    	{"main6",               ip6tables_main},
    	{"ip6tables-save",      ip6tables_save_main},
    	{"save6",               ip6tables_save_main},
    	{"ip6tables-restore",   ip6tables_restore_main},
    	{"restore6",            ip6tables_restore_main},
    #endif
    	{NULL},
    };

    int main(int argc, char **argv)
    {
    	return subcmd_main(argc, argv, multi_subcommands);
    }

``subcmd_main`` 関数の実装。
`xshared.c#L191-#L214 <https://git.netfilter.org/iptables/tree/xshared.c?id=482c6d3731e2681cb4baae835c294840300197e6#n191>`_

.. code-block:: c
    :linenos: table
    :linenostart: 191

    int subcmd_main(int argc, char **argv, const struct subcommand *cb)
    {
    	const char *cmd = basename(*argv);
    	mainfunc_t f = subcmd_get(cmd, cb);

    	if (f == NULL && argc > 1) {
    		/*
    		 * Unable to find a main method for our command name?
    		 * Let's try again with the first argument!
    		 */
    		++argv;
    		--argc;
    		f = subcmd_get(*argv, cb);
    	}

    	/* now we should have a valid function pointer */
    	if (f != NULL)
    		return f(argc, argv);

    	fprintf(stderr, "ERROR: No valid subcommand given.\nValid subcommands:\n");
    	for (; cb->name != NULL; ++cb)
    		fprintf(stderr, " * %s\n", cb->name);
    	exit(EXIT_FAILURE);
    }

``subcmd_get`` 関数の実装。
`xshared.c#L183-#L189 <https://git.netfilter.org/iptables/tree/xshared.c?id=482c6d3731e2681cb4baae835c294840300197e6#n183>`_

.. code-block:: c
    :linenos: table
    :linenostart: 183

    static mainfunc_t subcmd_get(const char *cmd, const struct subcommand *cb)
    {
    	for (; cb->name != NULL; ++cb)
    		if (strcmp(cb->name, cmd) == 0)
    			return cb->main;
    	return NULL;
    }

``iptables_restore_main`` 関数の実装。
`iptables-restore.c#L180-#L462 <https://git.netfilter.org/iptables/tree/iptables-restore.c?id=482c6d3731e2681cb4baae835c294840300197e6#n180>`_

.. code-block:: c
    :linenos: table
    :linenostart: 180

    int
    iptables_restore_main(int argc, char *argv[])
    {
    	struct xtc_handle *handle = NULL;
    	char buffer[10240];
    	int c;
    	char curtable[XT_TABLE_MAXNAMELEN + 1];
    	FILE *in;
    	int in_table = 0, testing = 0;
    	const char *tablename = NULL;
    	const struct xtc_ops *ops = &iptc_ops;

    	line = 0;

    	iptables_globals.program_name = "iptables-restore";
    	c = xtables_init_all(&iptables_globals, NFPROTO_IPV4);
    	if (c < 0) {
    		fprintf(stderr, "%s/%s Failed to initialize xtables\n",
    				iptables_globals.program_name,
    				iptables_globals.program_version);
    		exit(1);
    	}
    #if defined(ALL_INCLUSIVE) || defined(NO_SHARED_LIBS)
    	init_extensions();
    	init_extensions4();
    #endif

    	while ((c = getopt_long(argc, argv, "bcvthnM:T:", options, NULL)) != -1) {
    		switch (c) {
    			case 'b':
    				binary = 1;
    				break;
    			case 'c':
    				counters = 1;
    				break;
    			case 'v':
    				verbose = 1;
    				break;
    			case 't':
    				testing = 1;
    				break;
    			case 'h':
    				print_usage("iptables-restore",
    					    IPTABLES_VERSION);
    				break;
    			case 'n':
    				noflush = 1;
    				break;
    			case 'M':
    				xtables_modprobe_program = optarg;
    				break;
    			case 'T':
    				tablename = optarg;
    				break;
    		}
    	}

    	if (optind == argc - 1) {
    		in = fopen(argv[optind], "re");
    		if (!in) {
    			fprintf(stderr, "Can't open %s: %s\n", argv[optind],
    				strerror(errno));
    			exit(1);
    		}
    	}
    	else if (optind < argc) {
    		fprintf(stderr, "Unknown arguments found on commandline\n");
    		exit(1);
    	}
    	else in = stdin;

    	/* Grab standard input. */
    	while (fgets(buffer, sizeof(buffer), in)) {
    		int ret = 0;

    		line++;
    		if (buffer[0] == '\n')
    			continue;
    		else if (buffer[0] == '#') {
    			if (verbose)
    				fputs(buffer, stdout);
    			continue;
    		} else if ((strcmp(buffer, "COMMIT\n") == 0) && (in_table)) {
    			if (!testing) {
    				DEBUGP("Calling commit\n");
    				ret = ops->commit(handle);
    				ops->free(handle);
    				handle = NULL;
    			} else {
    				DEBUGP("Not calling commit, testing\n");
    				ret = 1;
    			}
    			in_table = 0;
    		} else if ((buffer[0] == '*') && (!in_table)) {
    			/* New table */
    			char *table;

    			table = strtok(buffer+1, " \t\n");
    			DEBUGP("line %u, table '%s'\n", line, table);
    			if (!table) {
    				xtables_error(PARAMETER_PROBLEM,
    					"%s: line %u table name invalid\n",
    					xt_params->program_name, line);
    				exit(1);
    			}
    			strncpy(curtable, table, XT_TABLE_MAXNAMELEN);
    			curtable[XT_TABLE_MAXNAMELEN] = '\0';

    			if (tablename && (strcmp(tablename, table) != 0))
    				continue;
    			if (handle)
    				ops->free(handle);

    			handle = create_handle(table);
    			if (noflush == 0) {
    				DEBUGP("Cleaning all chains of table '%s'\n",
    					table);
    				for_each_chain4(flush_entries4, verbose, 1,
    						handle);

    				DEBUGP("Deleting all user-defined chains "
    				       "of table '%s'\n", table);
    				for_each_chain4(delete_chain4, verbose, 0,
    						handle);
    			}

    			ret = 1;
    			in_table = 1;

    		} else if ((buffer[0] == ':') && (in_table)) {
    			/* New chain. */
    			char *policy, *chain;

    			chain = strtok(buffer+1, " \t\n");
    			DEBUGP("line %u, chain '%s'\n", line, chain);
    			if (!chain) {
    				xtables_error(PARAMETER_PROBLEM,
    					   "%s: line %u chain name invalid\n",
    					   xt_params->program_name, line);
    				exit(1);
    			}

    			if (strlen(chain) >= XT_EXTENSION_MAXNAMELEN)
    				xtables_error(PARAMETER_PROBLEM,
    					   "Invalid chain name `%s' "
    					   "(%u chars max)",
    					   chain, XT_EXTENSION_MAXNAMELEN - 1);

    			if (ops->builtin(chain, handle) <= 0) {
    				if (noflush && ops->is_chain(chain, handle)) {
    					DEBUGP("Flushing existing user defined chain '%s'\n", chain);
    					if (!ops->flush_entries(chain, handle))
    						xtables_error(PARAMETER_PROBLEM,
    							   "error flushing chain "
    							   "'%s':%s\n", chain,
    							   strerror(errno));
    				} else {
    					DEBUGP("Creating new chain '%s'\n", chain);
    					if (!ops->create_chain(chain, handle))
    						xtables_error(PARAMETER_PROBLEM,
    							   "error creating chain "
    							   "'%s':%s\n", chain,
    							   strerror(errno));
    				}
    			}

    			policy = strtok(NULL, " \t\n");
    			DEBUGP("line %u, policy '%s'\n", line, policy);
    			if (!policy) {
    				xtables_error(PARAMETER_PROBLEM,
    					   "%s: line %u policy invalid\n",
    					   xt_params->program_name, line);
    				exit(1);
    			}

    			if (strcmp(policy, "-") != 0) {
    				struct xt_counters count;

    				if (counters) {
    					char *ctrs;
    					ctrs = strtok(NULL, " \t\n");

    					if (!ctrs || !parse_counters(ctrs, &count))
    						xtables_error(PARAMETER_PROBLEM,
    							   "invalid policy counters "
    							   "for chain '%s'\n", chain);

    				} else {
    					memset(&count, 0, sizeof(count));
    				}

    				DEBUGP("Setting policy of chain %s to %s\n",
    					chain, policy);

    				if (!ops->set_policy(chain, policy, &count,
    						     handle))
    					xtables_error(OTHER_PROBLEM,
    						"Can't set policy `%s'"
    						" on `%s' line %u: %s\n",
    						policy, chain, line,
    						ops->strerror(errno));
    			}

    			ret = 1;

    		} else if (in_table) {
    			int a;
    			char *ptr = buffer;
    			char *pcnt = NULL;
    			char *bcnt = NULL;
    			char *parsestart;

    			/* reset the newargv */
    			newargc = 0;

    			if (buffer[0] == '[') {
    				/* we have counters in our input */
    				ptr = strchr(buffer, ']');
    				if (!ptr)
    					xtables_error(PARAMETER_PROBLEM,
    						   "Bad line %u: need ]\n",
    						   line);

    				pcnt = strtok(buffer+1, ":");
    				if (!pcnt)
    					xtables_error(PARAMETER_PROBLEM,
    						   "Bad line %u: need :\n",
    						   line);

    				bcnt = strtok(NULL, "]");
    				if (!bcnt)
    					xtables_error(PARAMETER_PROBLEM,
    						   "Bad line %u: need ]\n",
    						   line);

    				/* start command parsing after counter */
    				parsestart = ptr + 1;
    			} else {
    				/* start command parsing at start of line */
    				parsestart = buffer;
    			}

    			add_argv(argv[0]);
    			add_argv("-t");
    			add_argv(curtable);

    			if (counters && pcnt && bcnt) {
    				add_argv("--set-counters");
    				add_argv((char *) pcnt);
    				add_argv((char *) bcnt);
    			}

    			add_param_to_argv(parsestart);

    			DEBUGP("calling do_command4(%u, argv, &%s, handle):\n",
    				newargc, curtable);

    			for (a = 0; a < newargc; a++)
    				DEBUGP("argv[%u]: %s\n", a, newargv[a]);

    			ret = do_command4(newargc, newargv,
    					 &newargv[2], &handle, true);

    			free_argv();
    			fflush(stdout);
    		}
    		if (tablename && (strcmp(tablename, curtable) != 0))
    			continue;
    		if (!ret) {
    			fprintf(stderr, "%s: line %u failed\n",
    					xt_params->program_name, line);
    			exit(1);
    		}
    	}
    	if (in_table) {
    		fprintf(stderr, "%s: COMMIT expected at line %u\n",
    				xt_params->program_name, line + 1);
    		exit(1);
    	}

    	fclose(in);
    	return 0;
    }

* 256行目: 空行はスキップ。
* 258行目: ``#`` で始まる行はスキップ(コメント)。
* 262行目: テーブル内を処理中に ``COMMIT`` の行が来たらコミット処理を行い、テーブル終了。
* 273行目: テーブルの外にいるときに行頭が ``*`` のときはテーブル開始。

  * ``*`` の後 ``' '``, ``'\t'``, ``'\n'`` のどれかの手前までをテーブル名と解釈。

* 309行目: テーブル内で行頭が ``:`` のときはチェーン開始。 

  * ``:`` の後 ``' '``, ``'\t'``, ``'\n'``  のどれかの手前までをチェーン名と解釈。
  * その後次の ``' '``, ``'\t'``, ``'\n'``  のどれかの手前までをポリシーと解釈。
  * ポリシーが ``-`` 以外の場合は ``-c`` オプションを指定していた場合はその後のカウンター部分を解釈。

* 385行目: テーブル内で行頭が ``:`` 以外の時

  * 行頭が ``[`` の時はカウンタ( ``[整数:整数]`` 形式)とコマンドを処理。
  * 行頭が ``[`` でない時はコマンドを処理。

* 454行目: ファイルの終端まで来てテーブル内のままの時は ``COMMIT`` の呼び忘れとみなしてエラーで終了。

``parse_counters`` 関数の定義。
`iptables-restore.c#L79-#L88 <https://git.netfilter.org/iptables/tree/iptables-restore.c?id=482c6d3731e2681cb4baae835c294840300197e6#n79>`_

.. code-block:: c
    :linenos: table
    :linenostart: 79

    static int parse_counters(char *string, struct xt_counters *ctr)
    {
    	unsigned long long pcnt, bcnt;
    	int ret;

    	ret = sscanf(string, "[%llu:%llu]", &pcnt, &bcnt);
    	ctr->pcnt = pcnt;
    	ctr->bcnt = bcnt;
    	return ret == 2;
    }

set_policy関連
--------------

`libiptc/libiptc.c#L2747-#L2756 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n2747>`_

.. code-block:: c
    :linenos: table
    :linenostart: 2747

    const struct xtc_ops TC_OPS = {
    	.commit        = TC_COMMIT,
    	.free          = TC_FREE,
    	.builtin       = TC_BUILTIN,
    	.is_chain      = TC_IS_CHAIN,
    	.flush_entries = TC_FLUSH_ENTRIES,
    	.create_chain  = TC_CREATE_CHAIN,
    	.set_policy    = TC_SET_POLICY,
    	.strerror      = TC_STRERROR,
    };


`libiptc/libip4tc.c#L85 <https://git.netfilter.org/iptables/tree/libiptc/libip4tc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n85>`_

.. code-block:: c
    :linenos: table
    :linenostart: 85

    #define TC_SET_POLICY		iptc_set_policy

`libiptc/libiptc.c#L2406-#L2449 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n2406>`_

.. code-block:: c
    :linenos: table
    :linenostart: 2406

    /* Sets the policy on a built-in chain. */
    int
    TC_SET_POLICY(const IPT_CHAINLABEL chain,
    	      const IPT_CHAINLABEL policy,
    	      STRUCT_COUNTERS *counters,
    	      struct xtc_handle *handle)
    {
    	struct chain_head *c;

    	iptc_fn = TC_SET_POLICY;

    	if (!(c = iptcc_find_label(chain, handle))) {
    		DEBUGP("cannot find chain `%s'\n", chain);
    		errno = ENOENT;
    		return 0;
    	}

    	if (!iptcc_is_builtin(c)) {
    		DEBUGP("cannot set policy of userdefinedchain `%s'\n", chain);
    		errno = ENOENT;
    		return 0;
    	}

    	if (strcmp(policy, LABEL_ACCEPT) == 0)
    		c->verdict = -NF_ACCEPT - 1;
    	else if (strcmp(policy, LABEL_DROP) == 0)
    		c->verdict = -NF_DROP - 1;
    	else {
    		errno = EINVAL;
    		return 0;
    	}

    	if (counters) {
    		/* set byte and packet counters */
    		memcpy(&c->counters, counters, sizeof(STRUCT_COUNTERS));
    		c->counter_map.maptype = COUNTER_MAP_SET;
    	} else {
    		c->counter_map.maptype = COUNTER_MAP_NOMAP;
    	}

    	set_changed(handle);

    	return 1;
    }

`libiptc/libiptc.c#L107-#L125 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n107>`_

.. code-block:: c
    :linenos: table
    :linenostart: 107

    struct chain_head
    {
    	struct list_head list;
    	char name[TABLE_MAXNAMELEN];
    	unsigned int hooknum;		/* hook number+1 if builtin */
    	unsigned int references;	/* how many jumps reference us */
    	int verdict;			/* verdict if builtin */

    	STRUCT_COUNTERS counters;	/* per-chain counters */
    	struct counter_map counter_map;

    	unsigned int num_rules;		/* number of rules in list */
    	struct list_head rules;		/* list of rules */

    	unsigned int index;		/* index (needed for jump resolval) */
    	unsigned int head_offset;	/* offset in rule blob */
    	unsigned int foot_index;	/* index (needed for counter_map) */
    	unsigned int foot_offset;	/* offset in rule blob */
    };

`libiptc/linux_list.h#L43-#L55 <https://git.netfilter.org/iptables/tree/libiptc/linux_list.h?id=482c6d3731e2681cb4baae835c294840300197e6#n43>`_

.. code-block:: c
    :linenos: table
    :linenostart: 43

    /*
     * Simple doubly linked list implementation.
     *
     * Some of the internal functions ("__xxx") are useful when
     * manipulating whole lists rather than single entries, as
     * sometimes we already know the next/prev entries and we can
     * generate better code by using them directly rather than
     * using the generic single-entry routines.
     */

    struct list_head {
    	struct list_head *next, *prev;
    };


`libiptc/libiptc.c#L710-#L785 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n710>`_

.. code-block:: c
    :linenos: table
    :linenostart: 710

    /* Returns chain head if found, otherwise NULL. */
    static struct chain_head *
    iptcc_find_label(const char *name, struct xtc_handle *handle)
    {
    	struct list_head *pos;
    	struct list_head *list_start_pos;
    	unsigned int i=0;
    	int res;

    	if (list_empty(&handle->chains))
    		return NULL;

    	/* First look at builtin chains */
    	list_for_each(pos, &handle->chains) {
    		struct chain_head *c = list_entry(pos, struct chain_head, list);
    		if (!iptcc_is_builtin(c))
    			break;
    		if (!strcmp(c->name, name))
    			return c;
    	}

    	/* Find a smart place to start the search via chain index */
      	//list_start_pos = iptcc_linearly_search_chain_index(name, handle);
      	list_start_pos = iptcc_bsearch_chain_index(name, &i, handle);

    	/* Handel if bsearch bails out early */
    	if (list_start_pos == &handle->chains) {
    		list_start_pos = pos;
    	}
    #ifdef DEBUG
    	else {
    		/* Verify result of bsearch against linearly index search */
    		struct list_head *test_pos;
    		struct chain_head *test_c, *tmp_c;
    		test_pos = iptcc_linearly_search_chain_index(name, handle);
    		if (list_start_pos != test_pos) {
    			debug("BUG in chain_index search\n");
    			test_c=list_entry(test_pos,      struct chain_head,list);
    			tmp_c =list_entry(list_start_pos,struct chain_head,list);
    			debug("Verify search found:\n");
    			debug(" Chain:%s\n", test_c->name);
    			debug("BSearch found:\n");
    			debug(" Chain:%s\n", tmp_c->name);
    			exit(42);
    		}
    	}
    #endif

    	/* Initial/special case, no user defined chains */
    	if (handle->num_chains == 0)
    		return NULL;

    	/* Start searching through the chain list */
    	list_for_each(pos, list_start_pos->prev) {
    		struct chain_head *c = list_entry(pos, struct chain_head, list);
    		res = strcmp(c->name, name);
    		debug("List search name:%s == %s res:%d\n", name, c->name, res);
    		if (res==0)
    			return c;

    		/* We can stop earlier as we know list is sorted */
    		if (res>0 && !iptcc_is_builtin(c)) { /* Walked too far*/
    			debug(" Not in list, walked too far, sorted list\n");
    			return NULL;
    		}

    		/* Stop on wrap around, if list head is reached */
    		if (pos == &handle->chains) {
    			debug("Stop, list head reached\n");
    			return NULL;
    		}
    	}

    	debug("List search NOT found name:%s\n", name);
    	return NULL;
    }

`libiptc/libiptc.c#L642-#L646 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n642>`_

.. code-block:: c
    :linenos: table
    :linenostart: 642

    /* Is the given chain builtin (1) or user-defined (0) */
    static inline unsigned int iptcc_is_builtin(struct chain_head *c)
    {
    	return (c->hooknum ? 1 : 0);
    }


`libiptc/linux_list.h#L324-#L331 <https://git.netfilter.org/iptables/tree/libiptc/linux_list.h?id=482c6d3731e2681cb4baae835c294840300197e6#n324>`_

.. code-block:: c
    :linenos: table
    :linenostart: 324

    /**
     * list_entry - get the struct for this entry
     * @ptr:	the &struct list_head pointer.
     * @type:	the type of the struct this is embedded in.
     * @member:	the name of the list_struct within the struct.
     */
    #define list_entry(ptr, type, member) \
    	container_of(ptr, type, member)


`libiptc/linux_list.h#L7-#L17 <https://git.netfilter.org/iptables/tree/libiptc/linux_list.h?id=482c6d3731e2681cb4baae835c294840300197e6#n7>`_

.. code-block:: c
    :linenos: table
    :linenostart: 7

    /**
     * container_of - cast a member of a structure out to the containing structure
     *
     * @ptr:	the pointer to the member.
     * @type:	the type of the container struct this is embedded in.
     * @member:	the name of the member within the struct.
     *
     */
    #define container_of(ptr, type, member) ({			\
            const typeof( ((type *)0)->member ) *__mptr = (ptr);	\
            (type *)( (char *)__mptr - offsetof(type,member) );})


`libiptc/libiptc.c#L184-#L189 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n184>`_

.. code-block:: c
    :linenos: table
    :linenostart: 184

    /* notify us that the ruleset has been modified by the user */
    static inline void
    set_changed(struct xtc_handle *h)
    {
    	h->changed = 1;
    }

do_command4
-----------

`iptables/iptables.c#L1311-#L1955 <https://git.netfilter.org/iptables/tree/iptables/iptables.c?id=482c6d3731e2681cb4baae835c294840300197e6#n1311>`_

.. code-block:: c
    :linenos: table
    :linenostart: 1311

    int do_command4(int argc, char *argv[], char **table,
    		struct xtc_handle **handle, bool restore)
    {
    	struct iptables_command_state cs;
    	struct ipt_entry *e = NULL;
    	unsigned int nsaddrs = 0, ndaddrs = 0;
    	struct in_addr *saddrs = NULL, *smasks = NULL;
    	struct in_addr *daddrs = NULL, *dmasks = NULL;

    	int verbose = 0;
    	bool wait = false;
    	const char *chain = NULL;
    	const char *shostnetworkmask = NULL, *dhostnetworkmask = NULL;
    	const char *policy = NULL, *newname = NULL;
    	unsigned int rulenum = 0, command = 0;
    	const char *pcnt = NULL, *bcnt = NULL;
    	int ret = 1;
    	struct xtables_match *m;
    	struct xtables_rule_match *matchp;
    	struct xtables_target *t;
    	unsigned long long cnt;

    	memset(&cs, 0, sizeof(cs));
    	cs.jumpto = "";
    	cs.argv = argv;

    	/* re-set optind to 0 in case do_command4 gets called
    	 * a second time */
    	optind = 0;

    	/* clear mflags in case do_command4 gets called a second time
    	 * (we clear the global list of all matches for security)*/
    	for (m = xtables_matches; m; m = m->next)
    		m->mflags = 0;

    	for (t = xtables_targets; t; t = t->next) {
    		t->tflags = 0;
    		t->used = 0;
    	}

    	/* Suppress error messages: we may add new options if we
               demand-load a protocol. */
    	opterr = 0;

    	opts = xt_params->orig_opts;
    	while ((cs.c = getopt_long(argc, argv,
    	   "-:A:C:D:R:I:L::S::M:F::Z::N:X::E:P:Vh::o:p:s:d:j:i:fbvwnt:m:xc:g:46",
    					   opts, NULL)) != -1) {
    		switch (cs.c) {
    			/*
    			 * Command selection
    			 */
    		case 'A':
    			add_command(&command, CMD_APPEND, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			break;

    		case 'C':
    			add_command(&command, CMD_CHECK, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			break;

    		case 'D':
    			add_command(&command, CMD_DELETE, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!') {
    				rulenum = parse_rulenumber(argv[optind++]);
    				command = CMD_DELETE_NUM;
    			}
    			break;

    		case 'R':
    			add_command(&command, CMD_REPLACE, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				rulenum = parse_rulenumber(argv[optind++]);
    			else
    				xtables_error(PARAMETER_PROBLEM,
    					   "-%c requires a rule number",
    					   cmd2char(CMD_REPLACE));
    			break;

    		case 'I':
    			add_command(&command, CMD_INSERT, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				rulenum = parse_rulenumber(argv[optind++]);
    			else rulenum = 1;
    			break;

    		case 'L':
    			add_command(&command, CMD_LIST,
    				    CMD_ZERO | CMD_ZERO_NUM, cs.invert);
    			if (optarg) chain = optarg;
    			else if (optind < argc && argv[optind][0] != '-'
    				 && argv[optind][0] != '!')
    				chain = argv[optind++];
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				rulenum = parse_rulenumber(argv[optind++]);
    			break;

    		case 'S':
    			add_command(&command, CMD_LIST_RULES,
    				    CMD_ZERO|CMD_ZERO_NUM, cs.invert);
    			if (optarg) chain = optarg;
    			else if (optind < argc && argv[optind][0] != '-'
    				 && argv[optind][0] != '!')
    				chain = argv[optind++];
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				rulenum = parse_rulenumber(argv[optind++]);
    			break;

    		case 'F':
    			add_command(&command, CMD_FLUSH, CMD_NONE,
    				    cs.invert);
    			if (optarg) chain = optarg;
    			else if (optind < argc && argv[optind][0] != '-'
    				 && argv[optind][0] != '!')
    				chain = argv[optind++];
    			break;

    		case 'Z':
    			add_command(&command, CMD_ZERO, CMD_LIST|CMD_LIST_RULES,
    				    cs.invert);
    			if (optarg) chain = optarg;
    			else if (optind < argc && argv[optind][0] != '-'
    				&& argv[optind][0] != '!')
    				chain = argv[optind++];
    			if (optind < argc && argv[optind][0] != '-'
    				&& argv[optind][0] != '!') {
    				rulenum = parse_rulenumber(argv[optind++]);
    				command = CMD_ZERO_NUM;
    			}
    			break;

    		case 'N':
    			parse_chain(optarg);
    			add_command(&command, CMD_NEW_CHAIN, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			break;

    		case 'X':
    			add_command(&command, CMD_DELETE_CHAIN, CMD_NONE,
    				    cs.invert);
    			if (optarg) chain = optarg;
    			else if (optind < argc && argv[optind][0] != '-'
    				 && argv[optind][0] != '!')
    				chain = argv[optind++];
    			break;

    		case 'E':
    			add_command(&command, CMD_RENAME_CHAIN, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				newname = argv[optind++];
    			else
    				xtables_error(PARAMETER_PROBLEM,
    					   "-%c requires old-chain-name and "
    					   "new-chain-name",
    					    cmd2char(CMD_RENAME_CHAIN));
    			break;

    		case 'P':
    			add_command(&command, CMD_SET_POLICY, CMD_NONE,
    				    cs.invert);
    			chain = optarg;
    			if (optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				policy = argv[optind++];
    			else
    				xtables_error(PARAMETER_PROBLEM,
    					   "-%c requires a chain and a policy",
    					   cmd2char(CMD_SET_POLICY));
    			break;

    		case 'h':
    			if (!optarg)
    				optarg = argv[optind];

    			/* iptables -p icmp -h */
    			if (!cs.matches && cs.protocol)
    				xtables_find_match(cs.protocol,
    					XTF_TRY_LOAD, &cs.matches);

    			exit_printhelp(cs.matches);

    			/*
    			 * Option selection
    			 */
    		case 'p':
    			set_option(&cs.options, OPT_PROTOCOL, &cs.fw.ip.invflags,
    				   cs.invert);

    			/* Canonicalize into lower case */
    			for (cs.protocol = optarg; *cs.protocol; cs.protocol++)
    				*cs.protocol = tolower(*cs.protocol);

    			cs.protocol = optarg;
    			cs.fw.ip.proto = xtables_parse_protocol(cs.protocol);

    			if (cs.fw.ip.proto == 0
    			    && (cs.fw.ip.invflags & XT_INV_PROTO))
    				xtables_error(PARAMETER_PROBLEM,
    					   "rule would never match protocol");
    			break;

    		case 's':
    			set_option(&cs.options, OPT_SOURCE, &cs.fw.ip.invflags,
    				   cs.invert);
    			shostnetworkmask = optarg;
    			break;

    		case 'd':
    			set_option(&cs.options, OPT_DESTINATION, &cs.fw.ip.invflags,
    				   cs.invert);
    			dhostnetworkmask = optarg;
    			break;

    #ifdef IPT_F_GOTO
    		case 'g':
    			set_option(&cs.options, OPT_JUMP, &cs.fw.ip.invflags,
    				   cs.invert);
    			cs.fw.ip.flags |= IPT_F_GOTO;
    			cs.jumpto = parse_target(optarg);
    			break;
    #endif

    		case 'j':
    			command_jump(&cs);
    			break;


    		case 'i':
    			if (*optarg == '\0')
    				xtables_error(PARAMETER_PROBLEM,
    					"Empty interface is likely to be "
    					"undesired");
    			set_option(&cs.options, OPT_VIANAMEIN, &cs.fw.ip.invflags,
    				   cs.invert);
    			xtables_parse_interface(optarg,
    					cs.fw.ip.iniface,
    					cs.fw.ip.iniface_mask);
    			break;

    		case 'o':
    			if (*optarg == '\0')
    				xtables_error(PARAMETER_PROBLEM,
    					"Empty interface is likely to be "
    					"undesired");
    			set_option(&cs.options, OPT_VIANAMEOUT, &cs.fw.ip.invflags,
    				   cs.invert);
    			xtables_parse_interface(optarg,
    					cs.fw.ip.outiface,
    					cs.fw.ip.outiface_mask);
    			break;

    		case 'f':
    			set_option(&cs.options, OPT_FRAGMENT, &cs.fw.ip.invflags,
    				   cs.invert);
    			cs.fw.ip.flags |= IPT_F_FRAG;
    			break;

    		case 'v':
    			if (!verbose)
    				set_option(&cs.options, OPT_VERBOSE,
    					   &cs.fw.ip.invflags, cs.invert);
    			verbose++;
    			break;

    		case 'w':
    			if (restore) {
    				xtables_error(PARAMETER_PROBLEM,
    					      "You cannot use `-w' from "
    					      "iptables-restore");
    			}
    			wait = true;
    			break;

    		case 'm':
    			command_match(&cs);
    			break;

    		case 'n':
    			set_option(&cs.options, OPT_NUMERIC, &cs.fw.ip.invflags,
    				   cs.invert);
    			break;

    		case 't':
    			if (cs.invert)
    				xtables_error(PARAMETER_PROBLEM,
    					   "unexpected ! flag before --table");
    			*table = optarg;
    			break;

    		case 'x':
    			set_option(&cs.options, OPT_EXPANDED, &cs.fw.ip.invflags,
    				   cs.invert);
    			break;

    		case 'V':
    			if (cs.invert)
    				printf("Not %s ;-)\n", prog_vers);
    			else
    				printf("%s v%s\n",
    				       prog_name, prog_vers);
    			exit(0);

    		case '0':
    			set_option(&cs.options, OPT_LINENUMBERS, &cs.fw.ip.invflags,
    				   cs.invert);
    			break;

    		case 'M':
    			xtables_modprobe_program = optarg;
    			break;

    		case 'c':

    			set_option(&cs.options, OPT_COUNTERS, &cs.fw.ip.invflags,
    				   cs.invert);
    			pcnt = optarg;
    			bcnt = strchr(pcnt + 1, ',');
    			if (bcnt)
    			    bcnt++;
    			if (!bcnt && optind < argc && argv[optind][0] != '-'
    			    && argv[optind][0] != '!')
    				bcnt = argv[optind++];
    			if (!bcnt)
    				xtables_error(PARAMETER_PROBLEM,
    					"-%c requires packet and byte counter",
    					opt2char(OPT_COUNTERS));

    			if (sscanf(pcnt, "%llu", &cnt) != 1)
    				xtables_error(PARAMETER_PROBLEM,
    					"-%c packet counter not numeric",
    					opt2char(OPT_COUNTERS));
    			cs.fw.counters.pcnt = cnt;

    			if (sscanf(bcnt, "%llu", &cnt) != 1)
    				xtables_error(PARAMETER_PROBLEM,
    					"-%c byte counter not numeric",
    					opt2char(OPT_COUNTERS));
    			cs.fw.counters.bcnt = cnt;
    			break;

    		case '4':
    			/* This is indeed the IPv4 iptables */
    			break;

    		case '6':
    			/* This is not the IPv6 ip6tables */
    			if (line != -1)
    				return 1; /* success: line ignored */
    			fprintf(stderr, "This is the IPv4 version of iptables.\n");
    			exit_tryhelp(2);

    		case 1: /* non option */
    			if (optarg[0] == '!' && optarg[1] == '\0') {
    				if (cs.invert)
    					xtables_error(PARAMETER_PROBLEM,
    						   "multiple consecutive ! not"
    						   " allowed");
    				cs.invert = TRUE;
    				optarg[0] = '\0';
    				continue;
    			}
    			fprintf(stderr, "Bad argument `%s'\n", optarg);
    			exit_tryhelp(2);

    		default:
    			if (command_default(&cs, &iptables_globals) == 1)
    				/* cf. ip6tables.c */
    				continue;
    			break;
    		}
    		cs.invert = FALSE;
    	}

    	if (strcmp(*table, "nat") == 0 &&
    	    ((policy != NULL && strcmp(policy, "DROP") == 0) ||
    	    (cs.jumpto != NULL && strcmp(cs.jumpto, "DROP") == 0)))
    		xtables_error(PARAMETER_PROBLEM,
    			"\nThe \"nat\" table is not intended for filtering, "
    		        "the use of DROP is therefore inhibited.\n\n");

    	for (matchp = cs.matches; matchp; matchp = matchp->next)
    		xtables_option_mfcall(matchp->match);
    	if (cs.target != NULL)
    		xtables_option_tfcall(cs.target);

    	/* Fix me: must put inverse options checking here --MN */

    	if (optind < argc)
    		xtables_error(PARAMETER_PROBLEM,
    			   "unknown arguments found on commandline");
    	if (!command)
    		xtables_error(PARAMETER_PROBLEM, "no command specified");
    	if (cs.invert)
    		xtables_error(PARAMETER_PROBLEM,
    			   "nothing appropriate following !");

    	if (command & (CMD_REPLACE | CMD_INSERT | CMD_DELETE | CMD_APPEND | CMD_CHECK)) {
    		if (!(cs.options & OPT_DESTINATION))
    			dhostnetworkmask = "0.0.0.0/0";
    		if (!(cs.options & OPT_SOURCE))
    			shostnetworkmask = "0.0.0.0/0";
    	}

    	if (shostnetworkmask)
    		xtables_ipparse_multiple(shostnetworkmask, &saddrs,
    					 &smasks, &nsaddrs);

    	if (dhostnetworkmask)
    		xtables_ipparse_multiple(dhostnetworkmask, &daddrs,
    					 &dmasks, &ndaddrs);

    	if ((nsaddrs > 1 || ndaddrs > 1) &&
    	    (cs.fw.ip.invflags & (IPT_INV_SRCIP | IPT_INV_DSTIP)))
    		xtables_error(PARAMETER_PROBLEM, "! not allowed with multiple"
    			   " source or destination IP addresses");

    	if (command == CMD_REPLACE && (nsaddrs != 1 || ndaddrs != 1))
    		xtables_error(PARAMETER_PROBLEM, "Replacement rule does not "
    			   "specify a unique address");

    	generic_opt_check(command, cs.options);

    	/* Attempt to acquire the xtables lock */
    	if (!restore && !xtables_lock(wait)) {
    		fprintf(stderr, "Another app is currently holding the xtables lock. "
    			"Perhaps you want to use the -w option?\n");
    		xtables_free_opts(1);
    		exit(RESOURCE_PROBLEM);
    	}

    	/* only allocate handle if we weren't called with a handle */
    	if (!*handle)
    		*handle = iptc_init(*table);

    	/* try to insmod the module if iptc_init failed */
    	if (!*handle && xtables_load_ko(xtables_modprobe_program, false) != -1)
    		*handle = iptc_init(*table);

    	if (!*handle)
    		xtables_error(VERSION_PROBLEM,
    			   "can't initialize iptables table `%s': %s",
    			   *table, iptc_strerror(errno));

    	if (command == CMD_APPEND
    	    || command == CMD_DELETE
    	    || command == CMD_CHECK
    	    || command == CMD_INSERT
    	    || command == CMD_REPLACE) {
    		if (strcmp(chain, "PREROUTING") == 0
    		    || strcmp(chain, "INPUT") == 0) {
    			/* -o not valid with incoming packets. */
    			if (cs.options & OPT_VIANAMEOUT)
    				xtables_error(PARAMETER_PROBLEM,
    					   "Can't use -%c with %s\n",
    					   opt2char(OPT_VIANAMEOUT),
    					   chain);
    		}

    		if (strcmp(chain, "POSTROUTING") == 0
    		    || strcmp(chain, "OUTPUT") == 0) {
    			/* -i not valid with outgoing packets */
    			if (cs.options & OPT_VIANAMEIN)
    				xtables_error(PARAMETER_PROBLEM,
    					   "Can't use -%c with %s\n",
    					   opt2char(OPT_VIANAMEIN),
    					   chain);
    		}

    		if (cs.target && iptc_is_chain(cs.jumpto, *handle)) {
    			fprintf(stderr,
    				"Warning: using chain %s, not extension\n",
    				cs.jumpto);

    			if (cs.target->t)
    				free(cs.target->t);

    			cs.target = NULL;
    		}

    		/* If they didn't specify a target, or it's a chain
    		   name, use standard. */
    		if (!cs.target
    		    && (strlen(cs.jumpto) == 0
    			|| iptc_is_chain(cs.jumpto, *handle))) {
    			size_t size;

    			cs.target = xtables_find_target(XT_STANDARD_TARGET,
    					 XTF_LOAD_MUST_SUCCEED);

    			size = sizeof(struct xt_entry_target)
    				+ cs.target->size;
    			cs.target->t = xtables_calloc(1, size);
    			cs.target->t->u.target_size = size;
    			strcpy(cs.target->t->u.user.name, cs.jumpto);
    			if (!iptc_is_chain(cs.jumpto, *handle))
    				cs.target->t->u.user.revision = cs.target->revision;
    			xs_init_target(cs.target);
    		}

    		if (!cs.target) {
    			/* it is no chain, and we can't load a plugin.
    			 * We cannot know if the plugin is corrupt, non
    			 * existant OR if the user just misspelled a
    			 * chain. */
    #ifdef IPT_F_GOTO
    			if (cs.fw.ip.flags & IPT_F_GOTO)
    				xtables_error(PARAMETER_PROBLEM,
    					   "goto '%s' is not a chain\n",
    					   cs.jumpto);
    #endif
    			xtables_find_target(cs.jumpto, XTF_LOAD_MUST_SUCCEED);
    		} else {
    			e = generate_entry(&cs.fw, cs.matches, cs.target->t);
    			free(cs.target->t);
    		}
    	}

    	switch (command) {
    	case CMD_APPEND:
    		ret = append_entry(chain, e,
    				   nsaddrs, saddrs, smasks,
    				   ndaddrs, daddrs, dmasks,
    				   cs.options&OPT_VERBOSE,
    				   *handle);
    		break;
    	case CMD_DELETE:
    		ret = delete_entry(chain, e,
    				   nsaddrs, saddrs, smasks,
    				   ndaddrs, daddrs, dmasks,
    				   cs.options&OPT_VERBOSE,
    				   *handle, cs.matches, cs.target);
    		break;
    	case CMD_DELETE_NUM:
    		ret = iptc_delete_num_entry(chain, rulenum - 1, *handle);
    		break;
    	case CMD_CHECK:
    		ret = check_entry(chain, e,
    				   nsaddrs, saddrs, smasks,
    				   ndaddrs, daddrs, dmasks,
    				   cs.options&OPT_VERBOSE,
    				   *handle, cs.matches, cs.target);
    		break;
    	case CMD_REPLACE:
    		ret = replace_entry(chain, e, rulenum - 1,
    				    saddrs, smasks, daddrs, dmasks,
    				    cs.options&OPT_VERBOSE, *handle);
    		break;
    	case CMD_INSERT:
    		ret = insert_entry(chain, e, rulenum - 1,
    				   nsaddrs, saddrs, smasks,
    				   ndaddrs, daddrs, dmasks,
    				   cs.options&OPT_VERBOSE,
    				   *handle);
    		break;
    	case CMD_FLUSH:
    		ret = flush_entries4(chain, cs.options&OPT_VERBOSE, *handle);
    		break;
    	case CMD_ZERO:
    		ret = zero_entries(chain, cs.options&OPT_VERBOSE, *handle);
    		break;
    	case CMD_ZERO_NUM:
    		ret = iptc_zero_counter(chain, rulenum, *handle);
    		break;
    	case CMD_LIST:
    	case CMD_LIST|CMD_ZERO:
    	case CMD_LIST|CMD_ZERO_NUM:
    		ret = list_entries(chain,
    				   rulenum,
    				   cs.options&OPT_VERBOSE,
    				   cs.options&OPT_NUMERIC,
    				   cs.options&OPT_EXPANDED,
    				   cs.options&OPT_LINENUMBERS,
    				   *handle);
    		if (ret && (command & CMD_ZERO))
    			ret = zero_entries(chain,
    					   cs.options&OPT_VERBOSE, *handle);
    		if (ret && (command & CMD_ZERO_NUM))
    			ret = iptc_zero_counter(chain, rulenum, *handle);
    		break;
    	case CMD_LIST_RULES:
    	case CMD_LIST_RULES|CMD_ZERO:
    	case CMD_LIST_RULES|CMD_ZERO_NUM:
    		ret = list_rules(chain,
    				   rulenum,
    				   cs.options&OPT_VERBOSE,
    				   *handle);
    		if (ret && (command & CMD_ZERO))
    			ret = zero_entries(chain,
    					   cs.options&OPT_VERBOSE, *handle);
    		if (ret && (command & CMD_ZERO_NUM))
    			ret = iptc_zero_counter(chain, rulenum, *handle);
    		break;
    	case CMD_NEW_CHAIN:
    		ret = iptc_create_chain(chain, *handle);
    		break;
    	case CMD_DELETE_CHAIN:
    		ret = delete_chain4(chain, cs.options&OPT_VERBOSE, *handle);
    		break;
    	case CMD_RENAME_CHAIN:
    		ret = iptc_rename_chain(chain, newname,	*handle);
    		break;
    	case CMD_SET_POLICY:
    		ret = iptc_set_policy(chain, policy, cs.options&OPT_COUNTERS ? &cs.fw.counters : NULL, *handle);
    		break;
    	default:
    		/* We should never reach this... */
    		exit_tryhelp(2);
    	}

    	if (verbose > 1)
    		dump_entries(*handle);

    	xtables_rule_matches_free(&cs.matches);

    	if (e != NULL) {
    		free(e);
    		e = NULL;
    	}

    	free(saddrs);
    	free(smasks);
    	free(daddrs);
    	free(dmasks);
    	xtables_free_opts(1);

    	return ret;
    }

`iptables/iptables.c#L341-#L351 <https://git.netfilter.org/iptables/tree/iptables/iptables.c?id=482c6d3731e2681cb4baae835c294840300197e6#n341>`_

.. code-block:: c
    :linenos: table
    :linenostart: 341

    static void
    add_command(unsigned int *cmd, const int newcmd, const int othercmds, 
    	    int invert)
    {
    	if (invert)
    		xtables_error(PARAMETER_PROBLEM, "unexpected ! flag");
    	if (*cmd & (~othercmds))
    		xtables_error(PARAMETER_PROBLEM, "Cannot use -%c with -%c\n",
    			   cmd2char(newcmd), cmd2char(*cmd & (~othercmds)));
    	*cmd |= newcmd;
    }

commit
------


`libiptc/libiptc.c#L2517-#L2695 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n2517>`_

.. code-block:: c
    :linenos: table
    :linenostart: 2517

    int
    TC_COMMIT(struct xtc_handle *handle)
    {
    	/* Replace, then map back the counters. */
    	STRUCT_REPLACE *repl;
    	STRUCT_COUNTERS_INFO *newcounters;
    	struct chain_head *c;
    	int ret;
    	size_t counterlen;
    	int new_number;
    	unsigned int new_size;

    	iptc_fn = TC_COMMIT;
    	CHECK(*handle);

    	/* Don't commit if nothing changed. */
    	if (!handle->changed)
    		goto finished;

    	new_number = iptcc_compile_table_prep(handle, &new_size);
    	if (new_number < 0) {
    		errno = ENOMEM;
    		goto out_zero;
    	}

    	repl = malloc(sizeof(*repl) + new_size);
    	if (!repl) {
    		errno = ENOMEM;
    		goto out_zero;
    	}
    	memset(repl, 0, sizeof(*repl) + new_size);

    #if 0
    	TC_DUMP_ENTRIES(*handle);
    #endif

    	counterlen = sizeof(STRUCT_COUNTERS_INFO)
    			+ sizeof(STRUCT_COUNTERS) * new_number;

    	/* These are the old counters we will get from kernel */
    	repl->counters = malloc(sizeof(STRUCT_COUNTERS)
    				* handle->info.num_entries);
    	if (!repl->counters) {
    		errno = ENOMEM;
    		goto out_free_repl;
    	}
    	/* These are the counters we're going to put back, later. */
    	newcounters = malloc(counterlen);
    	if (!newcounters) {
    		errno = ENOMEM;
    		goto out_free_repl_counters;
    	}
    	memset(newcounters, 0, counterlen);

    	strcpy(repl->name, handle->info.name);
    	repl->num_entries = new_number;
    	repl->size = new_size;

    	repl->num_counters = handle->info.num_entries;
    	repl->valid_hooks  = handle->info.valid_hooks;

    	DEBUGP("num_entries=%u, size=%u, num_counters=%u\n",
    		repl->num_entries, repl->size, repl->num_counters);

    	ret = iptcc_compile_table(handle, repl);
    	if (ret < 0) {
    		errno = ret;
    		goto out_free_newcounters;
    	}


    #ifdef IPTC_DEBUG2
    	{
    		int fd = open("/tmp/libiptc-so_set_replace.blob",
    				O_CREAT|O_WRONLY);
    		if (fd >= 0) {
    			write(fd, repl, sizeof(*repl) + repl->size);
    			close(fd);
    		}
    	}
    #endif

    	ret = setsockopt(handle->sockfd, TC_IPPROTO, SO_SET_REPLACE, repl,
    			 sizeof(*repl) + repl->size);
    	if (ret < 0)
    		goto out_free_newcounters;

    	/* Put counters back. */
    	strcpy(newcounters->name, handle->info.name);
    	newcounters->num_counters = new_number;

    	list_for_each_entry(c, &handle->chains, list) {
    		struct rule_head *r;

    		/* Builtin chains have their own counters */
    		if (iptcc_is_builtin(c)) {
    			DEBUGP("counter for chain-index %u: ", c->foot_index);
    			switch(c->counter_map.maptype) {
    			case COUNTER_MAP_NOMAP:
    				counters_nomap(newcounters, c->foot_index);
    				break;
    			case COUNTER_MAP_NORMAL_MAP:
    				counters_normal_map(newcounters, repl,
    						    c->foot_index,
    						    c->counter_map.mappos);
    				break;
    			case COUNTER_MAP_ZEROED:
    				counters_map_zeroed(newcounters, repl,
    						    c->foot_index,
    						    c->counter_map.mappos,
    						    &c->counters);
    				break;
    			case COUNTER_MAP_SET:
    				counters_map_set(newcounters, c->foot_index,
    						 &c->counters);
    				break;
    			}
    		}

    		list_for_each_entry(r, &c->rules, list) {
    			DEBUGP("counter for index %u: ", r->index);
    			switch (r->counter_map.maptype) {
    			case COUNTER_MAP_NOMAP:
    				counters_nomap(newcounters, r->index);
    				break;

    			case COUNTER_MAP_NORMAL_MAP:
    				counters_normal_map(newcounters, repl,
    						    r->index,
    						    r->counter_map.mappos);
    				break;

    			case COUNTER_MAP_ZEROED:
    				counters_map_zeroed(newcounters, repl,
    						    r->index,
    						    r->counter_map.mappos,
    						    &r->entry->counters);
    				break;

    			case COUNTER_MAP_SET:
    				counters_map_set(newcounters, r->index,
    						 &r->entry->counters);
    				break;
    			}
    		}
    	}

    #ifdef IPTC_DEBUG2
    	{
    		int fd = open("/tmp/libiptc-so_set_add_counters.blob",
    				O_CREAT|O_WRONLY);
    		if (fd >= 0) {
    			write(fd, newcounters, counterlen);
    			close(fd);
    		}
    	}
    #endif

    	ret = setsockopt(handle->sockfd, TC_IPPROTO, SO_SET_ADD_COUNTERS,
    			 newcounters, counterlen);
    	if (ret < 0)
    		goto out_free_newcounters;

    	free(repl->counters);
    	free(repl);
    	free(newcounters);

    finished:
    	return 1;

    out_free_newcounters:
    	free(newcounters);
    out_free_repl_counters:
    	free(repl->counters);
    out_free_repl:
    	free(repl);
    out_zero:
    	return 0;
    }


`libiptc/libiptc.c#L2467-#L2471 <https://git.netfilter.org/iptables/tree/libiptc/libiptc.c?id=482c6d3731e2681cb4baae835c294840300197e6#n2467>`_

.. code-block:: c
    :linenos: table
    :linenostart: 2467

    static void counters_nomap(STRUCT_COUNTERS_INFO *newcounters, unsigned int idx)
    {
    	newcounters->counters[idx] = ((STRUCT_COUNTERS) { 0, 0});
    	DEBUGP_C("NOMAP => zero\n");
    }
