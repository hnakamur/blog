---
title: "xmllintコマンドでのXMLスキーマを使ったバリデーションのコードリーディング"
date: 2020-04-12T11:40:04+09:00
---

## はじめに

[SAML Security · OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html) の [Validate Signatures](https://cheatsheetseries.owasp.org/cheatsheets/SAML_Security_Cheat_Sheet.html#validate-signatures) を見ると、SAMLのXMLはローカルに置いた信頼できるスキーマファイルでバリデートせよと書かれています。

そこで実際に試してみてサンプルを [hnakamur/saml-response-sign-validate-verify-example](https://github.com/hnakamur/saml-response-sign-validate-verify-example) に置きました。

このサンプルでは `xmllint` コマンドの `--schema` オプションを使ってバリデートしています。
次は libxml2 の関数を使ってバリデートするのを実装したいので `xmllint` コマンドの `--schema` オプションの処理をコードリーディングします。

今回の対象は以下のコミットにしました。
https://github.com/GNOME/libxml2/tree/e4fb36841800038c289997432ca547c9bfef9db1

## `"--schema"` オプションの処理

まずは `"--schema"` で検索してみました。

main 関数内の
[xmllint.c#L3425-L3429](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmllint.c#L3425-L3429)
で `schema` という変数にファイル名をセットしています。

```c
  } else if ((!strcmp(argv[i], "-schema")) ||
	   (!strcmp(argv[i], "--schema"))) {
      i++;
      schema = argv[i];
      noent++;
```

`schema` は
[xmllint.c#L136](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmllint.c#L136)
で定義されている static 変数です。

```c
static char * schema = NULL;
```

## XML スキーマの読み込み

[xmllint.c#L3593-L3610](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmllint.c#L3593-L3610)
で XML スキーマをパーズしています。

```c
	xmlSchemaParserCtxtPtr ctxt;

	if (timing) {
	    startTimer();
	}
	ctxt = xmlSchemaNewParserCtxt(schema);
	xmlSchemaSetParserErrors(ctxt, xmlGenericError, xmlGenericError, NULL);
	wxschemas = xmlSchemaParse(ctxt);
	if (wxschemas == NULL) {
	    xmlGenericError(xmlGenericErrorContext,
		    "WXS schema %s failed to compile\n", schema);
	    progresult = XMLLINT_ERR_SCHEMACOMP;
	    schema = NULL;
	}
	xmlSchemaFreeParserCtxt(ctxt);
	if (timing) {
	    endTimer("Compiling the schemas");
	}
```

`wxschemas` 変数は
[xmllint.c#L137](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmllint.c#L137)
で定義されている static 変数です。

```c
static xmlSchemaPtr wxschemas = NULL;
```

## XML のバリデーション処理

[libxml2#L1651-L1672](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmllint.c#L1651-L1672)
でスキーマを使って XML をバリデートしていました。

```c
	int ret;
	xmlSchemaValidCtxtPtr vctxt;

	vctxt = xmlSchemaNewValidCtxt(wxschemas);
	xmlSchemaSetValidErrors(vctxt, xmlGenericError, xmlGenericError, NULL);
	xmlSchemaValidateSetFilename(vctxt, filename);

	ret = xmlSchemaValidateStream(vctxt, buf, 0, handler,
				      (void *)user_data);
	if (repeat == 0) {
	    if (ret == 0) {
		fprintf(stderr, "%s validates\n", filename);
	    } else if (ret > 0) {
		fprintf(stderr, "%s fails to validate\n", filename);
		progresult = XMLLINT_ERR_VALID;
	    } else {
		fprintf(stderr, "%s validation generated an internal error\n",
		       filename);
		progresult = XMLLINT_ERR_VALID;
	    }
	}
	xmlSchemaFreeValidCtxt(vctxt);
```

`buf` はこの少し上で `xmlParserInputBufferCreateFilename` 関数を使って作成していました。これはファイル名を引数に渡してファイルから読んで作る版ですが、
`xmlParserInputBufferCreateStatic` というメモリ上の XML データから作る版もありました。

[xmlIO.c#L2976-L3019](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2976-L3019)

```c
/**
 * xmlParserInputBufferCreateStatic:
 * @mem:  the memory input
 * @size:  the length of the memory block
 * @enc:  the charset encoding if known
 *
 * Create a buffered parser input for the progressive parsing for the input
 * from an immutable memory area. This will not copy the memory area to
 * the buffer, but the memory is expected to be available until the end of
 * the parsing, this is useful for example when using mmap'ed file.
 *
 * Returns the new parser input or NULL
 */
xmlParserInputBufferPtr
xmlParserInputBufferCreateStatic(const char *mem, int size,
                                 xmlCharEncoding enc) {
    xmlParserInputBufferPtr ret;

    if (size < 0) return(NULL);
    if (mem == NULL) return(NULL);

    ret = (xmlParserInputBufferPtr) xmlMalloc(sizeof(xmlParserInputBuffer));
    if (ret == NULL) {
	xmlIOErrMemory("creating input buffer");
	return(NULL);
    }
    memset(ret, 0, (size_t) sizeof(xmlParserInputBuffer));
    ret->buffer = xmlBufCreateStatic((void *)mem, (size_t) size);
    if (ret->buffer == NULL) {
        xmlFree(ret);
	return(NULL);
    }
    ret->encoder = xmlGetCharEncodingHandler(enc);
    if (ret->encoder != NULL)
        ret->raw = xmlBufCreateSize(2 * xmlDefaultBufferSize);
    else
        ret->raw = NULL;
    ret->compressed = -1;
    ret->context = (void *) mem;
    ret->readcallback = NULL;
    ret->closecallback = NULL;

    return(ret);
}
```

`buf` の解放は `xmlFreeParserInputBuffer` 関数で行います。
[xmlIO.c#L2487-L2513](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2487-L2513)

```c
/**
 * xmlFreeParserInputBuffer:
 * @in:  a buffered parser input
 *
 * Free up the memory used by a buffered parser input
 */
void
xmlFreeParserInputBuffer(xmlParserInputBufferPtr in) {
    if (in == NULL) return;

    if (in->raw) {
        xmlBufFree(in->raw);
	in->raw = NULL;
    }
    if (in->encoder != NULL) {
        xmlCharEncCloseFunc(in->encoder);
    }
    if (in->closecallback != NULL) {
	in->closecallback(in->context);
    }
    if (in->buffer != NULL) {
        xmlBufFree(in->buffer);
	in->buffer = NULL;
    }

    xmlFree(in);
}
```

## XML スキーマの読み込み `xmlSchemaNewParserCtxt` の実装

[xmlschemas.c#L12459-L12482](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L12459-L12482)

```c
/**
 * xmlSchemaNewParserCtxt:
 * @URL:  the location of the schema
 *
 * Create an XML Schemas parse context for that file/resource expected
 * to contain an XML Schemas file.
 *
 * Returns the parser context or NULL in case of error
 */
xmlSchemaParserCtxtPtr
xmlSchemaNewParserCtxt(const char *URL)
{
    xmlSchemaParserCtxtPtr ret;

    if (URL == NULL)
	return (NULL);

    ret = xmlSchemaParserCtxtCreate();
    if (ret == NULL)
	return(NULL);
    ret->dict = xmlDictCreate();
    ret->URL = xmlDictLookup(ret->dict, (const xmlChar *) URL, -1);
    return (ret);
}
```

`xmlDictLookup` 関数
[dict.c#L854-L992](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/dict.c#L854-L992)

```c
/**
 * xmlDictLookup:
 * @dict: the dictionary
 * @name: the name of the userdata
 * @len: the length of the name, if -1 it is recomputed
 *
 * Add the @name to the dictionary @dict if not present.
 *
 * Returns the internal copy of the name or NULL in case of internal error
 */
const xmlChar *
xmlDictLookup(xmlDictPtr dict, const xmlChar *name, int len) {
    unsigned long key, okey, nbi = 0;
    xmlDictEntryPtr entry;
    xmlDictEntryPtr insert;
    const xmlChar *ret;
    unsigned int l;

    if ((dict == NULL) || (name == NULL))
	return(NULL);

    if (len < 0)
	l = strlen((const char *) name);
    else
	l = len;

    if (((dict->limit > 0) && (l >= dict->limit)) ||
	(l > INT_MAX / 2))
	return(NULL);

    /*
     * Check for duplicate and insertion location.
     */
    okey = xmlDictComputeKey(dict, name, l);
    key = okey % dict->size;
    if (dict->dict[key].valid == 0) {
	insert = NULL;
    } else {
	for (insert = &(dict->dict[key]); insert->next != NULL;
	     insert = insert->next) {
#ifdef __GNUC__
	    if ((insert->okey == okey) && (insert->len == l)) {
		if (!memcmp(insert->name, name, l))
		    return(insert->name);
	    }
#else
	    if ((insert->okey == okey) && (insert->len == l) &&
		(!xmlStrncmp(insert->name, name, l)))
		return(insert->name);
#endif
	    nbi++;
	}
#ifdef __GNUC__
	if ((insert->okey == okey) && (insert->len == l)) {
	    if (!memcmp(insert->name, name, l))
		return(insert->name);
	}
#else
	if ((insert->okey == okey) && (insert->len == l) &&
	    (!xmlStrncmp(insert->name, name, l)))
	    return(insert->name);
#endif
    }

    if (dict->subdict) {
	unsigned long skey;

	/* we cannot always reuse the same okey for the subdict */
	if (((dict->size == MIN_DICT_SIZE) &&
	     (dict->subdict->size != MIN_DICT_SIZE)) ||
	    ((dict->size != MIN_DICT_SIZE) &&
	     (dict->subdict->size == MIN_DICT_SIZE)))
	    skey = xmlDictComputeKey(dict->subdict, name, l);
	else
	    skey = okey;

	key = skey % dict->subdict->size;
	if (dict->subdict->dict[key].valid != 0) {
	    xmlDictEntryPtr tmp;

	    for (tmp = &(dict->subdict->dict[key]); tmp->next != NULL;
		 tmp = tmp->next) {
#ifdef __GNUC__
		if ((tmp->okey == skey) && (tmp->len == l)) {
		    if (!memcmp(tmp->name, name, l))
			return(tmp->name);
		}
#else
		if ((tmp->okey == skey) && (tmp->len == l) &&
		    (!xmlStrncmp(tmp->name, name, l)))
		    return(tmp->name);
#endif
		nbi++;
	    }
#ifdef __GNUC__
	    if ((tmp->okey == skey) && (tmp->len == l)) {
		if (!memcmp(tmp->name, name, l))
		    return(tmp->name);
	    }
#else
	    if ((tmp->okey == skey) && (tmp->len == l) &&
		(!xmlStrncmp(tmp->name, name, l)))
		return(tmp->name);
#endif
	}
	key = okey % dict->size;
    }

    ret = xmlDictAddString(dict, name, l);
    if (ret == NULL)
	return(NULL);
    if (insert == NULL) {
	entry = &(dict->dict[key]);
    } else {
	entry = xmlMalloc(sizeof(xmlDictEntry));
	if (entry == NULL)
	     return(NULL);
    }
    entry->name = ret;
    entry->len = l;
    entry->next = NULL;
    entry->valid = 1;
    entry->okey = okey;


    if (insert != NULL)
	insert->next = entry;

    dict->nbElems++;

    if ((nbi > MAX_HASH_LEN) &&
	(dict->size <= ((MAX_DICT_HASH / 2) / MAX_HASH_LEN))) {
	if (xmlDictGrow(dict, MAX_HASH_LEN * 2 * dict->size) != 0)
	    return(NULL);
    }
    /* Note that entry may have been freed at this point by xmlDictGrow */

    return(ret);
}
```

`xmlDictComputeKey` 関数
[dict.c#L65-L88](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/dict.c#L65-L88)

```c
#define MAX_HASH_LEN 3
#define MIN_DICT_SIZE 128
#define MAX_DICT_HASH 8 * 2048
#define WITH_BIG_KEY

#ifdef WITH_BIG_KEY
#define xmlDictComputeKey(dict, name, len)                              \
    (((dict)->size == MIN_DICT_SIZE) ?                                  \
     xmlDictComputeFastKey(name, len, (dict)->seed) :                   \
     xmlDictComputeBigKey(name, len, (dict)->seed))

#define xmlDictComputeQKey(dict, prefix, plen, name, len)               \
    (((prefix) == NULL) ?                                               \
      (xmlDictComputeKey(dict, name, len)) :                             \
      (((dict)->size == MIN_DICT_SIZE) ?                                \
       xmlDictComputeFastQKey(prefix, plen, name, len, (dict)->seed) :	\
       xmlDictComputeBigQKey(prefix, plen, name, len, (dict)->seed)))

#else /* !WITH_BIG_KEY */
#define xmlDictComputeKey(dict, name, len)                              \
        xmlDictComputeFastKey(name, len, (dict)->seed)
#define xmlDictComputeQKey(dict, prefix, plen, name, len)               \
        xmlDictComputeFastQKey(prefix, plen, name, len, (dict)->seed)
#endif /* WITH_BIG_KEY */
```

`xmlDictAddString` 関数
[dict.c#L231-L291](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/dict.c#L231-L291)

```c
/*
 * xmlDictAddString:
 * @dict: the dictionary
 * @name: the name of the userdata
 * @len: the length of the name
 *
 * Add the string to the array[s]
 *
 * Returns the pointer of the local string, or NULL in case of error.
 */
static const xmlChar *
xmlDictAddString(xmlDictPtr dict, const xmlChar *name, unsigned int namelen) {
    xmlDictStringsPtr pool;
    const xmlChar *ret;
    size_t size = 0; /* + sizeof(_xmlDictStrings) == 1024 */
    size_t limit = 0;

#ifdef DICT_DEBUG_PATTERNS
    fprintf(stderr, "-");
#endif
    pool = dict->strings;
    while (pool != NULL) {
	if ((size_t)(pool->end - pool->free) > namelen)
	    goto found_pool;
	if (pool->size > size) size = pool->size;
        limit += pool->size;
	pool = pool->next;
    }
    /*
     * Not found, need to allocate
     */
    if (pool == NULL) {
        if ((dict->limit > 0) && (limit > dict->limit)) {
            return(NULL);
        }

        if (size == 0) size = 1000;
	else size *= 4; /* exponential growth */
        if (size < 4 * namelen)
	    size = 4 * namelen; /* just in case ! */
	pool = (xmlDictStringsPtr) xmlMalloc(sizeof(xmlDictStrings) + size);
	if (pool == NULL)
	    return(NULL);
	pool->size = size;
	pool->nbStrings = 0;
	pool->free = &pool->array[0];
	pool->end = &pool->array[size];
	pool->next = dict->strings;
	dict->strings = pool;
#ifdef DICT_DEBUG_PATTERNS
        fprintf(stderr, "+");
#endif
    }
found_pool:
    ret = pool->free;
    memcpy(pool->free, name, namelen);
    pool->free += namelen;
    *(pool->free++) = 0;
    pool->nbStrings++;
    return(ret);
}
```

## `xmlSchemaParse` 関数

`xmlSchemaParse` 関数
[xmlschemas.c#L21304-L21426](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L21304-L21426)

```c
/**
 * xmlSchemaParse:
 * @ctxt:  a schema validation context
 *
 * parse a schema definition resource and build an internal
 * XML Schema structure which can be used to validate instances.
 *
 * Returns the internal XML Schema structure built from the resource or
 *         NULL in case of error
 */
xmlSchemaPtr
xmlSchemaParse(xmlSchemaParserCtxtPtr ctxt)
{
    xmlSchemaPtr mainSchema = NULL;
    xmlSchemaBucketPtr bucket = NULL;
    int res;

    /*
    * This one is used if the schema to be parsed was specified via
    * the API; i.e. not automatically by the validated instance document.
    */

    xmlSchemaInitTypes();

    if (ctxt == NULL)
        return (NULL);

    /* TODO: Init the context. Is this all we need?*/
    ctxt->nberrors = 0;
    ctxt->err = 0;
    ctxt->counter = 0;

    /* Create the *main* schema. */
    mainSchema = xmlSchemaNewSchema(ctxt);
    if (mainSchema == NULL)
	goto exit_failure;
    /*
    * Create the schema constructor.
    */
    if (ctxt->constructor == NULL) {
	ctxt->constructor = xmlSchemaConstructionCtxtCreate(ctxt->dict);
	if (ctxt->constructor == NULL)
	    return(NULL);
	/* Take ownership of the constructor to be able to free it. */
	ctxt->ownsConstructor = 1;
    }
    ctxt->constructor->mainSchema = mainSchema;
    /*
    * Locate and add the schema document.
    */
    res = xmlSchemaAddSchemaDoc(ctxt, XML_SCHEMA_SCHEMA_MAIN,
	ctxt->URL, ctxt->doc, ctxt->buffer, ctxt->size, NULL,
	NULL, NULL, &bucket);
    if (res == -1)
	goto exit_failure;
    if (res != 0)
	goto exit;

    if (bucket == NULL) {
	/* TODO: Error code, actually we failed to *locate* the schema. */
	if (ctxt->URL)
	    xmlSchemaCustomErr(ACTXT_CAST ctxt, XML_SCHEMAP_FAILED_LOAD,
		NULL, NULL,
		"Failed to locate the main schema resource at '%s'",
		ctxt->URL, NULL);
	else
	    xmlSchemaCustomErr(ACTXT_CAST ctxt, XML_SCHEMAP_FAILED_LOAD,
		NULL, NULL,
		"Failed to locate the main schema resource",
		    NULL, NULL);
	goto exit;
    }
    /* Then do the parsing for good. */
    if (xmlSchemaParseNewDocWithContext(ctxt, mainSchema, bucket) == -1)
	goto exit_failure;
    if (ctxt->nberrors != 0)
	goto exit;

    mainSchema->doc = bucket->doc;
    mainSchema->preserve = ctxt->preserve;

    ctxt->schema = mainSchema;

    if (xmlSchemaFixupComponents(ctxt, WXS_CONSTRUCTOR(ctxt)->mainBucket) == -1)
	goto exit_failure;

    /*
    * TODO: This is not nice, since we cannot distinguish from the
    * result if there was an internal error or not.
    */
exit:
    if (ctxt->nberrors != 0) {
	if (mainSchema) {
	    xmlSchemaFree(mainSchema);
	    mainSchema = NULL;
	}
	if (ctxt->constructor) {
	    xmlSchemaConstructionCtxtFree(ctxt->constructor);
	    ctxt->constructor = NULL;
	    ctxt->ownsConstructor = 0;
	}
    }
    ctxt->schema = NULL;
    return(mainSchema);
exit_failure:
    /*
    * Quite verbose, but should catch internal errors, which were
    * not communicated.
    */
    if (mainSchema) {
        xmlSchemaFree(mainSchema);
	mainSchema = NULL;
    }
    if (ctxt->constructor) {
	xmlSchemaConstructionCtxtFree(ctxt->constructor);
	ctxt->constructor = NULL;
	ctxt->ownsConstructor = 0;
    }
    PERROR_INT2("xmlSchemaParse",
	"An internal error occurred");
    ctxt->schema = NULL;
    return(NULL);
}
```

`xmlSchemaAddSchemaDoc`
[xmlschemas.c#L10292-L10714](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L10292-L10714)

```c
/**
 * xmlSchemaAddSchemaDoc:
 * @pctxt:  a schema validation context
 * @schema:  the schema being built
 * @node:  a subtree containing XML Schema information
 *
 * Parse an included (and to-be-redefined) XML schema document.
 *
 * Returns 0 on success, a positive error code on errors and
 *         -1 in case of an internal or API error.
 */

static int
xmlSchemaAddSchemaDoc(xmlSchemaParserCtxtPtr pctxt,
		int type, /* import or include or redefine */
		const xmlChar *schemaLocation,
		xmlDocPtr schemaDoc,
		const char *schemaBuffer,
		int schemaBufferLen,
		xmlNodePtr invokingNode,
		const xmlChar *sourceTargetNamespace,
		const xmlChar *importNamespace,
		xmlSchemaBucketPtr *bucket)
{
    const xmlChar *targetNamespace = NULL;
    xmlSchemaSchemaRelationPtr relation = NULL;
    xmlDocPtr doc = NULL;
    int res = 0, err = 0, located = 0, preserveDoc = 0;
    xmlSchemaBucketPtr bkt = NULL;

    if (bucket != NULL)
	*bucket = NULL;

    switch (type) {
	case XML_SCHEMA_SCHEMA_IMPORT:
	case XML_SCHEMA_SCHEMA_MAIN:
	    err = XML_SCHEMAP_SRC_IMPORT;
	    break;
	case XML_SCHEMA_SCHEMA_INCLUDE:
	    err = XML_SCHEMAP_SRC_INCLUDE;
	    break;
	case XML_SCHEMA_SCHEMA_REDEFINE:
	    err = XML_SCHEMAP_SRC_REDEFINE;
	    break;
    }


    /* Special handling for the main schema:
    * skip the location and relation logic and just parse the doc.
    * We need just a bucket to be returned in this case.
    */
    if ((type == XML_SCHEMA_SCHEMA_MAIN) || (! WXS_HAS_BUCKETS(pctxt)))
	goto doc_load;

    /* Note that we expect the location to be an absolute URI. */
    if (schemaLocation != NULL) {
	bkt = xmlSchemaGetSchemaBucket(pctxt, schemaLocation);
	if ((bkt != NULL) &&
	    (pctxt->constructor->bucket == bkt)) {
	    /* Report self-imports/inclusions/redefinitions. */

	    xmlSchemaCustomErr(ACTXT_CAST pctxt, err,
		invokingNode, NULL,
		"The schema must not import/include/redefine itself",
		NULL, NULL);
	    goto exit;
	}
    }
    /*
    * Create a relation for the graph of schemas.
    */
    relation = xmlSchemaSchemaRelationCreate();
    if (relation == NULL)
	return(-1);
    xmlSchemaSchemaRelationAddChild(pctxt->constructor->bucket,
	relation);
    relation->type = type;

    /*
    * Save the namespace import information.
    */
    if (WXS_IS_BUCKET_IMPMAIN(type)) {
	relation->importNamespace = importNamespace;
	if (schemaLocation == NULL) {
	    /*
	    * No location; this is just an import of the namespace.
	    * Note that we don't assign a bucket to the relation
	    * in this case.
	    */
	    goto exit;
	}
	targetNamespace = importNamespace;
    }

    /* Did we already fetch the doc? */
    if (bkt != NULL) {
	if ((WXS_IS_BUCKET_IMPMAIN(type)) && (! bkt->imported)) {
	    /*
	    * We included/redefined and then try to import a schema,
	    * but the new location provided for import was different.
	    */
	    if (schemaLocation == NULL)
		schemaLocation = BAD_CAST "in_memory_buffer";
	    if (!xmlStrEqual(schemaLocation,
		bkt->schemaLocation)) {
		xmlSchemaCustomErr(ACTXT_CAST pctxt, err,
		    invokingNode, NULL,
		    "The schema document '%s' cannot be imported, since "
		    "it was already included or redefined",
		    schemaLocation, NULL);
		goto exit;
	    }
	} else if ((! WXS_IS_BUCKET_IMPMAIN(type)) && (bkt->imported)) {
	    /*
	    * We imported and then try to include/redefine a schema,
	    * but the new location provided for the include/redefine
	    * was different.
	    */
	    if (schemaLocation == NULL)
		schemaLocation = BAD_CAST "in_memory_buffer";
	    if (!xmlStrEqual(schemaLocation,
		bkt->schemaLocation)) {
		xmlSchemaCustomErr(ACTXT_CAST pctxt, err,
		    invokingNode, NULL,
		    "The schema document '%s' cannot be included or "
		    "redefined, since it was already imported",
		    schemaLocation, NULL);
		goto exit;
	    }
	}
    }

    if (WXS_IS_BUCKET_IMPMAIN(type)) {
	/*
	* Given that the schemaLocation [attribute] is only a hint, it is open
	* to applications to ignore all but the first <import> for a given
	* namespace, regardless of the `actual value` of schemaLocation, but
	* such a strategy risks missing useful information when new
	* schemaLocations are offered.
	*
	* We will use the first <import> that comes with a location.
	* Further <import>s *with* a location, will result in an error.
	* TODO: Better would be to just report a warning here, but
	* we'll try it this way until someone complains.
	*
	* Schema Document Location Strategy:
	* 3 Based on the namespace name, identify an existing schema document,
	* either as a resource which is an XML document or a <schema> element
	* information item, in some local schema repository;
	* 5 Attempt to resolve the namespace name to locate such a resource.
	*
	* NOTE: (3) and (5) are not supported.
	*/
	if (bkt != NULL) {
	    relation->bucket = bkt;
	    goto exit;
	}
	bkt = xmlSchemaGetSchemaBucketByTNS(pctxt,
	    importNamespace, 1);

	if (bkt != NULL) {
	    relation->bucket = bkt;
	    if (bkt->schemaLocation == NULL) {
		/* First given location of the schema; load the doc. */
		bkt->schemaLocation = schemaLocation;
	    } else {
		if (!xmlStrEqual(schemaLocation,
		    bkt->schemaLocation)) {
		    /*
		    * Additional location given; just skip it.
		    * URGENT TODO: We should report a warning here.
		    * res = XML_SCHEMAP_SRC_IMPORT;
		    */
		    if (schemaLocation == NULL)
			schemaLocation = BAD_CAST "in_memory_buffer";

		    xmlSchemaCustomWarning(ACTXT_CAST pctxt,
			XML_SCHEMAP_WARN_SKIP_SCHEMA,
			invokingNode, NULL,
			"Skipping import of schema located at '%s' for the "
			"namespace '%s', since this namespace was already "
			"imported with the schema located at '%s'",
			schemaLocation, importNamespace, bkt->schemaLocation);
		}
		goto exit;
	    }
	}
	/*
	* No bucket + first location: load the doc and create a
	* bucket.
	*/
    } else {
	/* <include> and <redefine> */
	if (bkt != NULL) {

	    if ((bkt->origTargetNamespace == NULL) &&
		(bkt->targetNamespace != sourceTargetNamespace)) {
		xmlSchemaBucketPtr chamel;

		/*
		* Chameleon include/redefine: skip loading only if it was
		* already build for the targetNamespace of the including
		* schema.
		*/
		/*
		* URGENT TODO: If the schema is a chameleon-include then copy
		* the components into the including schema and modify the
		* targetNamespace of those components, do nothing otherwise.
		* NOTE: This is currently worked-around by compiling the
		* chameleon for every distinct including targetNamespace; thus
		* not performant at the moment.
		* TODO: Check when the namespace in wildcards for chameleons
		* needs to be converted: before we built wildcard intersections
		* or after.
		*   Answer: after!
		*/
		chamel = xmlSchemaGetChameleonSchemaBucket(pctxt,
		    schemaLocation, sourceTargetNamespace);
		if (chamel != NULL) {
		    /* A fitting chameleon was already parsed; NOP. */
		    relation->bucket = chamel;
		    goto exit;
		}
		/*
		* We need to parse the chameleon again for a different
		* targetNamespace.
		* CHAMELEON TODO: Optimize this by only parsing the
		* chameleon once, and then copying the components to
		* the new targetNamespace.
		*/
		bkt = NULL;
	    } else {
		relation->bucket = bkt;
		goto exit;
	    }
	}
    }
    if ((bkt != NULL) && (bkt->doc != NULL)) {
	PERROR_INT("xmlSchemaAddSchemaDoc",
	    "trying to load a schema doc, but a doc is already "
	    "assigned to the schema bucket");
	goto exit_failure;
    }

doc_load:
    /*
    * Load the document.
    */
    if (schemaDoc != NULL) {
	doc = schemaDoc;
	/* Don' free this one, since it was provided by the caller. */
	preserveDoc = 1;
	/* TODO: Does the context or the doc hold the location? */
	if (schemaDoc->URL != NULL)
	    schemaLocation = xmlDictLookup(pctxt->dict,
		schemaDoc->URL, -1);
        else
	    schemaLocation = BAD_CAST "in_memory_buffer";
    } else if ((schemaLocation != NULL) || (schemaBuffer != NULL)) {
	xmlParserCtxtPtr parserCtxt;

	parserCtxt = xmlNewParserCtxt();
	if (parserCtxt == NULL) {
	    xmlSchemaPErrMemory(NULL, "xmlSchemaGetDoc, "
		"allocating a parser context", NULL);
	    goto exit_failure;
	}
	if ((pctxt->dict != NULL) && (parserCtxt->dict != NULL)) {
	    /*
	    * TODO: Do we have to burden the schema parser dict with all
	    * the content of the schema doc?
	    */
	    xmlDictFree(parserCtxt->dict);
	    parserCtxt->dict = pctxt->dict;
	    xmlDictReference(parserCtxt->dict);
	}
	if (schemaLocation != NULL) {
	    /* Parse from file. */
	    doc = xmlCtxtReadFile(parserCtxt, (const char *) schemaLocation,
		NULL, SCHEMAS_PARSE_OPTIONS);
	} else if (schemaBuffer != NULL) {
	    /* Parse from memory buffer. */
	    doc = xmlCtxtReadMemory(parserCtxt, schemaBuffer, schemaBufferLen,
		NULL, NULL, SCHEMAS_PARSE_OPTIONS);
	    schemaLocation = BAD_CAST "in_memory_buffer";
	    if (doc != NULL)
		doc->URL = xmlStrdup(schemaLocation);
	}
	/*
	* For <import>:
	* 2.1 The referent is (a fragment of) a resource which is an
	* XML document (see clause 1.1), which in turn corresponds to
	* a <schema> element information item in a well-formed information
	* set, which in turn corresponds to a valid schema.
	* TODO: (2.1) fragments of XML documents are not supported.
	*
	* 2.2 The referent is a <schema> element information item in
	* a well-formed information set, which in turn corresponds
	* to a valid schema.
	* TODO: (2.2) is not supported.
	*/
	if (doc == NULL) {
	    xmlErrorPtr lerr;
	    lerr = xmlGetLastError();
	    /*
	    * Check if this a parser error, or if the document could
	    * just not be located.
	    * TODO: Try to find specific error codes to react only on
	    * localisation failures.
	    */
	    if ((lerr == NULL) || (lerr->domain != XML_FROM_IO)) {
		/*
		* We assume a parser error here.
		*/
		located = 1;
		/* TODO: Error code ?? */
		res = XML_SCHEMAP_SRC_IMPORT_2_1;
		xmlSchemaCustomErr(ACTXT_CAST pctxt, res,
		    invokingNode, NULL,
		    "Failed to parse the XML resource '%s'",
		    schemaLocation, NULL);
	    }
	}
	xmlFreeParserCtxt(parserCtxt);
	if ((doc == NULL) && located)
	    goto exit_error;
    } else {
	xmlSchemaPErr(pctxt, NULL,
	    XML_SCHEMAP_NOTHING_TO_PARSE,
	    "No information for parsing was provided with the "
	    "given schema parser context.\n",
	    NULL, NULL);
	goto exit_failure;
    }
    /*
    * Preprocess the document.
    */
    if (doc != NULL) {
	xmlNodePtr docElem = NULL;

	located = 1;
	docElem = xmlDocGetRootElement(doc);
	if (docElem == NULL) {
	    xmlSchemaCustomErr(ACTXT_CAST pctxt, XML_SCHEMAP_NOROOT,
		invokingNode, NULL,
		"The document '%s' has no document element",
		schemaLocation, NULL);
	    goto exit_error;
	}
	/*
	* Remove all the blank text nodes.
	*/
	xmlSchemaCleanupDoc(pctxt, docElem);
	/*
	* Check the schema's top level element.
	*/
	if (!IS_SCHEMA(docElem, "schema")) {
	    xmlSchemaCustomErr(ACTXT_CAST pctxt, XML_SCHEMAP_NOT_SCHEMA,
		invokingNode, NULL,
		"The XML document '%s' is not a schema document",
		schemaLocation, NULL);
	    goto exit_error;
	}
	/*
	* Note that we don't apply a type check for the
	* targetNamespace value here.
	*/
	targetNamespace = xmlSchemaGetProp(pctxt, docElem,
	    "targetNamespace");
    }

/* after_doc_loading: */
    if ((bkt == NULL) && located) {
	/* Only create a bucket if the schema was located. */
        bkt = xmlSchemaBucketCreate(pctxt, type,
	    targetNamespace);
	if (bkt == NULL)
	    goto exit_failure;
    }
    if (bkt != NULL) {
	bkt->schemaLocation = schemaLocation;
	bkt->located = located;
	if (doc != NULL) {
	    bkt->doc = doc;
	    bkt->targetNamespace = targetNamespace;
	    bkt->origTargetNamespace = targetNamespace;
	    if (preserveDoc)
		bkt->preserveDoc = 1;
	}
	if (WXS_IS_BUCKET_IMPMAIN(type))
	    bkt->imported++;
	    /*
	    * Add it to the graph of schemas.
	    */
	if (relation != NULL)
	    relation->bucket = bkt;
    }

exit:
    /*
    * Return the bucket explicitly; this is needed for the
    * main schema.
    */
    if (bucket != NULL)
	*bucket = bkt;
    return (0);

exit_error:
    if ((doc != NULL) && (! preserveDoc)) {
	xmlFreeDoc(doc);
	if (bkt != NULL)
	    bkt->doc = NULL;
    }
    return(pctxt->err);

exit_failure:
    if ((doc != NULL) && (! preserveDoc)) {
	xmlFreeDoc(doc);
	if (bkt != NULL)
	    bkt->doc = NULL;
    }
    return (-1);
}
```

上記のうち以下の部分で `xmlCtxtReadFile` 関数で `schemaLocation` のファイルからスキーマを読み込んでいます。
その下を見ると `schemaLocation` を `NULL` にして `schemaBuffer` を設定して呼び出せば `xmlCtxtReadMemory` 関数でメモリ上のスキーマを読み込めることが分かります。

```c
	if (schemaLocation != NULL) {
	    /* Parse from file. */
	    doc = xmlCtxtReadFile(parserCtxt, (const char *) schemaLocation,
		NULL, SCHEMAS_PARSE_OPTIONS);
	} else if (schemaBuffer != NULL) {
	    /* Parse from memory buffer. */
	    doc = xmlCtxtReadMemory(parserCtxt, schemaBuffer, schemaBufferLen,
		NULL, NULL, SCHEMAS_PARSE_OPTIONS);
	    schemaLocation = BAD_CAST "in_memory_buffer";
	    if (doc != NULL)
		doc->URL = xmlStrdup(schemaLocation);
	}
```

## `xmlSchemaParserCtxtPtr` 型の定義

`xmlSchemaParserCtxtPtr` 型の定義

[xmlschemas.h#L112-L113](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/include/libxml/xmlschemas.h#L112-L113)

```c
typedef struct _xmlSchemaParserCtxt xmlSchemaParserCtxt;
typedef xmlSchemaParserCtxt *xmlSchemaParserCtxtPtr;
```

`struct _xmlSchemaParserCtxt`
[xmlschemas.c#L595-L642](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L595-L642)

```c
struct _xmlSchemaParserCtxt {
    int type;
    void *errCtxt;             /* user specific error context */
    xmlSchemaValidityErrorFunc error;   /* the callback in case of errors */
    xmlSchemaValidityWarningFunc warning;       /* the callback in case of warning */
    int err;
    int nberrors;
    xmlStructuredErrorFunc serror;

    xmlSchemaConstructionCtxtPtr constructor;
    int ownsConstructor; /* TODO: Move this to parser *flags*. */

    /* xmlSchemaPtr topschema;	*/
    /* xmlHashTablePtr namespaces;  */

    xmlSchemaPtr schema;        /* The main schema in use */
    int counter;

    const xmlChar *URL;
    xmlDocPtr doc;
    int preserve;		/* Whether the doc should be freed  */

    const char *buffer;
    int size;

    /*
     * Used to build complex element content models
     */
    xmlAutomataPtr am;
    xmlAutomataStatePtr start;
    xmlAutomataStatePtr end;
    xmlAutomataStatePtr state;

    xmlDictPtr dict;		/* dictionary for interned string names */
    xmlSchemaTypePtr ctxtType; /* The current context simple/complex type */
    int options;
    xmlSchemaValidCtxtPtr vctxt;
    int isS4S;
    int isRedefine;
    int xsiAssemble;
    int stop; /* If the parser should stop; i.e. a critical error. */
    const xmlChar *targetNamespace;
    xmlSchemaBucketPtr redefined; /* The schema to be redefined. */

    xmlSchemaRedefPtr redef; /* Used for redefinitions. */
    int redefCounter; /* Used for redefinitions. */
    xmlSchemaItemListPtr attrProhibs;
};
```

`xmlSchemaParseNewDocWithContext` 関数
[xmlschemas.c#L10117-L10184](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L10117-L10184)

```c
static int
xmlSchemaParseNewDocWithContext(xmlSchemaParserCtxtPtr pctxt,
		     xmlSchemaPtr schema,
		     xmlSchemaBucketPtr bucket)
{
    int oldFlags;
    xmlDocPtr oldDoc;
    xmlNodePtr node;
    int ret, oldErrs;
    xmlSchemaBucketPtr oldbucket = pctxt->constructor->bucket;

    /*
    * Save old values; reset the *main* schema.
    * URGENT TODO: This is not good; move the per-document information
    * to the parser. Get rid of passing the main schema to the
    * parsing functions.
    */
    oldFlags = schema->flags;
    oldDoc = schema->doc;
    if (schema->flags != 0)
	xmlSchemaClearSchemaDefaults(schema);
    schema->doc = bucket->doc;
    pctxt->schema = schema;
    /*
    * Keep the current target namespace on the parser *not* on the
    * main schema.
    */
    pctxt->targetNamespace = bucket->targetNamespace;
    WXS_CONSTRUCTOR(pctxt)->bucket = bucket;

    if ((bucket->targetNamespace != NULL) &&
	xmlStrEqual(bucket->targetNamespace, xmlSchemaNs)) {
	/*
	* We are parsing the schema for schemas!
	*/
	pctxt->isS4S = 1;
    }
    /* Mark it as parsed, even if parsing fails. */
    bucket->parsed++;
    /* Compile the schema doc. */
    node = xmlDocGetRootElement(bucket->doc);
    ret = xmlSchemaParseSchemaElement(pctxt, schema, node);
    if (ret != 0)
	goto exit;
    /* An empty schema; just get out. */
    if (node->children == NULL)
	goto exit;
    oldErrs = pctxt->nberrors;
    ret = xmlSchemaParseSchemaTopLevel(pctxt, schema, node->children);
    if (ret != 0)
	goto exit;
    /*
    * TODO: Not nice, but I'm not 100% sure we will get always an error
    * as a result of the above functions; so better rely on pctxt->err
    * as well.
    */
    if ((ret == 0) && (oldErrs != pctxt->nberrors)) {
	ret = pctxt->err;
	goto exit;
    }

exit:
    WXS_CONSTRUCTOR(pctxt)->bucket = oldbucket;
    /* Restore schema values. */
    schema->doc = oldDoc;
    schema->flags = oldFlags;
    return(ret);
}
```

## `xmlParserInputBufferCreateFilename` 関数

[xmlIO.c#L2629-L2648](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2629-L2648)

```c
/**
 * xmlParserInputBufferCreateFilename:
 * @URI:  a C string containing the URI or filename
 * @enc:  the charset encoding if known
 *
 * Create a buffered parser input for the progressive parsing of a file
 * If filename is "-' then we use stdin as the input.
 * Automatic support for ZLIB/Compress compressed document is provided
 * by default if found at compile-time.
 * Do an encoding check if enc == XML_CHAR_ENCODING_NONE
 *
 * Returns the new parser input or NULL
 */
xmlParserInputBufferPtr
xmlParserInputBufferCreateFilename(const char *URI, xmlCharEncoding enc) {
    if ((xmlParserInputBufferCreateFilenameValue)) {
		return xmlParserInputBufferCreateFilenameValue(URI, enc);
	}
	return __xmlParserInputBufferCreateFilename(URI, enc);
}
```

`__xmlParserInputBufferCreateFilename` 関数
[xmlIO.c#L2558-L2627](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2558-L2627)

```c
xmlParserInputBufferPtr
__xmlParserInputBufferCreateFilename(const char *URI, xmlCharEncoding enc) {
    xmlParserInputBufferPtr ret;
    int i = 0;
    void *context = NULL;

    if (xmlInputCallbackInitialized == 0)
	xmlRegisterDefaultInputCallbacks();

    if (URI == NULL) return(NULL);

    /*
     * Try to find one of the input accept method accepting that scheme
     * Go in reverse to give precedence to user defined handlers.
     */
    if (context == NULL) {
	for (i = xmlInputCallbackNr - 1;i >= 0;i--) {
	    if ((xmlInputCallbackTable[i].matchcallback != NULL) &&
		(xmlInputCallbackTable[i].matchcallback(URI) != 0)) {
		context = xmlInputCallbackTable[i].opencallback(URI);
		if (context != NULL) {
		    break;
		}
	    }
	}
    }
    if (context == NULL) {
	return(NULL);
    }

    /*
     * Allocate the Input buffer front-end.
     */
    ret = xmlAllocParserInputBuffer(enc);
    if (ret != NULL) {
	ret->context = context;
	ret->readcallback = xmlInputCallbackTable[i].readcallback;
	ret->closecallback = xmlInputCallbackTable[i].closecallback;
#ifdef LIBXML_ZLIB_ENABLED
	if ((xmlInputCallbackTable[i].opencallback == xmlGzfileOpen) &&
		(strcmp(URI, "-") != 0)) {
#if defined(ZLIB_VERNUM) && ZLIB_VERNUM >= 0x1230
            ret->compressed = !gzdirect(context);
#else
	    if (((z_stream *)context)->avail_in > 4) {
	        char *cptr, buff4[4];
		cptr = (char *) ((z_stream *)context)->next_in;
		if (gzread(context, buff4, 4) == 4) {
		    if (strncmp(buff4, cptr, 4) == 0)
		        ret->compressed = 0;
		    else
		        ret->compressed = 1;
		    gzrewind(context);
		}
	    }
#endif
	}
#endif
#ifdef LIBXML_LZMA_ENABLED
	if ((xmlInputCallbackTable[i].opencallback == xmlXzfileOpen) &&
		(strcmp(URI, "-") != 0)) {
            ret->compressed = __libxml2_xzcompressed(context);
	}
#endif
    }
    else
      xmlInputCallbackTable[i].closecallback (context);

    return(ret);
}
```

`xmlInputCallbackTable` 変数
[xmlIO.c#L90-L104](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L90-L104)

```c
/*
 * Input I/O callback sets
 */
typedef struct _xmlInputCallback {
    xmlInputMatchCallback matchcallback;
    xmlInputOpenCallback opencallback;
    xmlInputReadCallback readcallback;
    xmlInputCloseCallback closecallback;
} xmlInputCallback;

#define MAX_INPUT_CALLBACK 15

static xmlInputCallback xmlInputCallbackTable[MAX_INPUT_CALLBACK];
static int xmlInputCallbackNr = 0;
static int xmlInputCallbackInitialized = 0;
```

`xmlInputMatchCallback` 型など
[xmlIO.h#L20-L63](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/include/libxml/xmlIO.h#L20-L63)

```c
/*
 * Those are the functions and datatypes for the parser input
 * I/O structures.
 */

/**
 * xmlInputMatchCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Input API to detect if the current handler
 * can provide input functionality for this resource.
 *
 * Returns 1 if yes and 0 if another Input module should be used
 */
typedef int (XMLCALL *xmlInputMatchCallback) (char const *filename);
/**
 * xmlInputOpenCallback:
 * @filename: the filename or URI
 *
 * Callback used in the I/O Input API to open the resource
 *
 * Returns an Input context or NULL in case or error
 */
typedef void * (XMLCALL *xmlInputOpenCallback) (char const *filename);
/**
 * xmlInputReadCallback:
 * @context:  an Input context
 * @buffer:  the buffer to store data read
 * @len:  the length of the buffer in bytes
 *
 * Callback used in the I/O Input API to read the resource
 *
 * Returns the number of bytes read or -1 in case of error
 */
typedef int (XMLCALL *xmlInputReadCallback) (void * context, char * buffer, int len);
/**
 * xmlInputCloseCallback:
 * @context:  an Input context
 *
 * Callback used in the I/O Input API to close the resource
 *
 * Returns 0 or -1 in case of error
 */
typedef int (XMLCALL *xmlInputCloseCallback) (void * context);
```

`xmlRegisterDefaultInputCallbacks` 関数
[xmlIO.c#L2247-L2278](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2247-L2278)

```c
/**
 * xmlRegisterDefaultInputCallbacks:
 *
 * Registers the default compiled-in I/O handlers.
 */
void
xmlRegisterDefaultInputCallbacks(void) {
    if (xmlInputCallbackInitialized)
	return;

    xmlRegisterInputCallbacks(xmlFileMatch, xmlFileOpen,
	                      xmlFileRead, xmlFileClose);
#ifdef LIBXML_ZLIB_ENABLED
    xmlRegisterInputCallbacks(xmlGzfileMatch, xmlGzfileOpen,
	                      xmlGzfileRead, xmlGzfileClose);
#endif /* LIBXML_ZLIB_ENABLED */
#ifdef LIBXML_LZMA_ENABLED
    xmlRegisterInputCallbacks(xmlXzfileMatch, xmlXzfileOpen,
	                      xmlXzfileRead, xmlXzfileClose);
#endif /* LIBXML_LZMA_ENABLED */

#ifdef LIBXML_HTTP_ENABLED
    xmlRegisterInputCallbacks(xmlIOHTTPMatch, xmlIOHTTPOpen,
	                      xmlIOHTTPRead, xmlIOHTTPClose);
#endif /* LIBXML_HTTP_ENABLED */

#ifdef LIBXML_FTP_ENABLED
    xmlRegisterInputCallbacks(xmlIOFTPMatch, xmlIOFTPOpen,
	                      xmlIOFTPRead, xmlIOFTPClose);
#endif /* LIBXML_FTP_ENABLED */
    xmlInputCallbackInitialized = 1;
}
```

`xmlFileMatch` 関数
[xmlIO.c#L804-L815](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L804-L815)

`xmlInputCallbackTable` を最後から最初にマッチしていき、 0 番目の要素は常にマッチとさせるため、常に 1 を返す。

```c
/**
 * xmlFileMatch:
 * @filename:  the URI for matching
 *
 * input from FILE *
 *
 * Returns 1 if matches, 0 otherwise
 */
int
xmlFileMatch (const char *filename ATTRIBUTE_UNUSED) {
    return(1);
}
```

`xmlFileOpen` 関数
[xmlIO.c#L875-L899](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L875-L899)

```c
/**
 * xmlFileOpen:
 * @filename:  the URI for matching
 *
 * Wrapper around xmlFileOpen_real that try it with an unescaped
 * version of @filename, if this fails fallback to @filename
 *
 * Returns a handler or NULL in case or failure
 */
void *
xmlFileOpen (const char *filename) {
    char *unescaped;
    void *retval;

    retval = xmlFileOpen_real(filename);
    if (retval == NULL) {
	unescaped = xmlURIUnescapeString(filename, 0, NULL);
	if (unescaped != NULL) {
	    retval = xmlFileOpen_real(unescaped);
	    xmlFree(unescaped);
	}
    }

    return retval;
}
```

`xmlFileOpen_real` 関数
[xmlIO.c#L817-L873](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L817-L873)

```c
/**
 * xmlFileOpen_real:
 * @filename:  the URI for matching
 *
 * input from FILE *, supports compressed input
 * if @filename is " " then the standard input is used
 *
 * Returns an I/O context or NULL in case of error
 */
static void *
xmlFileOpen_real (const char *filename) {
    const char *path = filename;
    FILE *fd;

    if (filename == NULL)
        return(NULL);

    if (!strcmp(filename, "-")) {
	fd = stdin;
	return((void *) fd);
    }

    if (!xmlStrncasecmp(BAD_CAST filename, BAD_CAST "file://localhost/", 17)) {
#if defined (_WIN32) || defined (__DJGPP__) && !defined(__CYGWIN__)
	path = &filename[17];
#else
	path = &filename[16];
#endif
    } else if (!xmlStrncasecmp(BAD_CAST filename, BAD_CAST "file:///", 8)) {
#if defined (_WIN32) || defined (__DJGPP__) && !defined(__CYGWIN__)
	path = &filename[8];
#else
	path = &filename[7];
#endif
    } else if (!xmlStrncasecmp(BAD_CAST filename, BAD_CAST "file:/", 6)) {
        /* lots of generators seems to lazy to read RFC 1738 */
#if defined (_WIN32) || defined (__DJGPP__) && !defined(__CYGWIN__)
	path = &filename[6];
#else
	path = &filename[5];
#endif
    }

    /* Do not check DDNAME on zOS ! */
#if !defined(__MVS__)
    if (!xmlCheckFilename(path))
        return(NULL);
#endif

#if defined(_WIN32) || defined (__DJGPP__) && !defined (__CYGWIN__)
    fd = xmlWrapOpenUtf8(path, 0);
#else
    fd = fopen(path, "r");
#endif /* WIN32 */
    if (fd == NULL) xmlIOErr(0, path);
    return((void *) fd);
}
```

`xmlFileRead` 関数
[xmlIO.c#L952-L970](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L952-L970)

```c
/**
 * xmlFileRead:
 * @context:  the I/O context
 * @buffer:  where to drop data
 * @len:  number of bytes to write
 *
 * Read @len bytes to @buffer from the I/O channel.
 *
 * Returns the number of bytes written or < 0 in case of failure
 */
int
xmlFileRead (void * context, char * buffer, int len) {
    int ret;
    if ((context == NULL) || (buffer == NULL))
        return(-1);
    ret = fread(&buffer[0], 1,  len, (FILE *) context);
    if (ret < 0) xmlIOErr(0, "fread()");
    return(ret);
}
```

`xmlAllocParserInputBuffer` 関数
[xmlIO.c#L2342-L2378](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlIO.c#L2342-L2378)

```c
/**
 * xmlAllocParserInputBuffer:
 * @enc:  the charset encoding if known
 *
 * Create a buffered parser input for progressive parsing
 *
 * Returns the new parser input or NULL
 */
xmlParserInputBufferPtr
xmlAllocParserInputBuffer(xmlCharEncoding enc) {
    xmlParserInputBufferPtr ret;

    ret = (xmlParserInputBufferPtr) xmlMalloc(sizeof(xmlParserInputBuffer));
    if (ret == NULL) {
	xmlIOErrMemory("creating input buffer");
	return(NULL);
    }
    memset(ret, 0, (size_t) sizeof(xmlParserInputBuffer));
    ret->buffer = xmlBufCreateSize(2 * xmlDefaultBufferSize);
    if (ret->buffer == NULL) {
        xmlFree(ret);
	return(NULL);
    }
    xmlBufSetAllocationScheme(ret->buffer, XML_BUFFER_ALLOC_DOUBLEIT);
    ret->encoder = xmlGetCharEncodingHandler(enc);
    if (ret->encoder != NULL)
        ret->raw = xmlBufCreateSize(2 * xmlDefaultBufferSize);
    else
        ret->raw = NULL;
    ret->readcallback = NULL;
    ret->closecallback = NULL;
    ret->context = NULL;
    ret->compressed = -1;
    ret->rawconsumed = 0;

    return(ret);
}
```

## `xmlSchemaValidateDoc` 関数

[xmlschemas.c#L28220-L28247](https://github.com/GNOME/libxml2/blob/e4fb36841800038c289997432ca547c9bfef9db1/xmlschemas.c#L28220-L28247)

`xmlSchemaValidateStream` とは別に `xmlSchemaValidateDoc` 関数というのもありました。
メモリ上の XML をバリデートするならこちらのほうが使いやすいかもしれません。

```c
/**
 * xmlSchemaValidateDoc:
 * @ctxt:  a schema validation context
 * @doc:  a parsed document tree
 *
 * Validate a document tree in memory.
 *
 * Returns 0 if the document is schemas valid, a positive error code
 *     number otherwise and -1 in case of internal or API error.
 */
int
xmlSchemaValidateDoc(xmlSchemaValidCtxtPtr ctxt, xmlDocPtr doc)
{
    if ((ctxt == NULL) || (doc == NULL))
        return (-1);

    ctxt->doc = doc;
    ctxt->node = xmlDocGetRootElement(doc);
    if (ctxt->node == NULL) {
        xmlSchemaCustomErr(ACTXT_CAST ctxt,
	    XML_SCHEMAV_DOCUMENT_ELEMENT_MISSING,
	    (xmlNodePtr) doc, NULL,
	    "The document has no document element", NULL, NULL);
        return (ctxt->err);
    }
    ctxt->validationRoot = ctxt->node;
    return (xmlSchemaVStart(ctxt));
}
```
