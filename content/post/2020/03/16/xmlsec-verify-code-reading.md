---
title: "XMLSecでの証明書検証のコードリーディング"
date: 2020-03-16T19:01:08+09:00
---
## はじめに

[nginx luaでSAMLのService Providerを作ってみた · hnakamur's blog](https://hnakamur.github.io/blog/2018/07/31/saml-service-provider-with-nginx-lua/) の [hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider) ですがレスポンスのXMLを検証する処理は非同期ではなく同期的に実行される実装としていました。 詳しくは [Caveats](https://github.com/hnakamur/nginx-lua-saml-service-provider/blob/90b79233bfc28dd48ad8f2d38a8d547d182f1a62/README.md#caveats) に書いています。

当時は利用者数が数人の想定だったので、これでも十分と考えていました。その後 SAML ではなく Keycloak を使うことになったので、このライブラリは使っていなかったのですが、再度使うかもしれない状況になりました。

その際、レスポンスのXMLの検証を xmlsec コマンドで外部実行するのではなく、 libxmlsec の関数を呼んでオンメモリで実行したいということで、まずは xml コマンドで行っている処理をコードリーディングしてみることにしました。

## 今回コードリーディングの対象

対象のバージョンは Ubuntu 18.04 LTS の libxmlsec1 パッケージのバージョンに合わせて 1.2.25 です。

今回対象とするコマンドは `xmlsec --verify` コマンドで、以下の特定のオプションのパターンのみです。

[hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider) から xmlsec コマンドを呼び出している個所は以下の部分です。

[lib/saml/service_provider/response.lua#L36-L37](https://github.com/hnakamur/nginx-lua-saml-service-provider/blob/90b79233bfc28dd48ad8f2d38a8d547d182f1a62/lib/saml/service_provider/response.lua#L36-L37)
```lua
    local cmd = string.format("%s --verify --pubkey-cert-pem %s --id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response %s",
        self.xmlsec_command, self.idp_cert_filename, tmpfilename)
```

コマンドとしては以下のようになります。

```console
xmlsec1 --verify --pubkey-cert-pem idp.crt \
  --id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response
  response.xml
```

## `--verify` オプションの処理を読む
### `xmlSecAppVerifyFile` 関数

[apps/xmlsec.c#L1077](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L1077) から呼び出されています。

[apps/xmlsec.c#L1213-L1315](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L1213-L1315)

```c
static int 
xmlSecAppVerifyFile(const char* filename) {
    xmlSecAppXmlDataPtr data = NULL;
    xmlSecDSigCtx dsigCtx;
    clock_t start_time;
    int res = -1;
    
    if(filename == NULL) {
        return(-1);
    }

    if(xmlSecDSigCtxInitialize(&dsigCtx, gKeysMngr) < 0) {
        fprintf(stderr, "Error: dsig context initialization failed\n");
        return(-1);
    }
    if(xmlSecAppPrepareDSigCtx(&dsigCtx) < 0) {
        fprintf(stderr, "Error: dsig context preparation failed\n");
        goto done;
    }
    
    /* parse template and select start node */
    data = xmlSecAppXmlDataCreate(filename, xmlSecNodeSignature, xmlSecDSigNs);
    if(data == NULL) {
        fprintf(stderr, "Error: failed to load document \"%s\"\n", filename);
        goto done;
    }

    /* sign */
    start_time = clock();
    if(xmlSecDSigCtxVerify(&dsigCtx, data->startNode) < 0) {
        fprintf(stderr,"Error: signature failed \n");
        goto done;
    }
    total_time += clock() - start_time;    

    if((repeats <= 1) && (dsigCtx.status != xmlSecDSigStatusSucceeded)){ 
        /* return an error if signature does not match */
        goto done;
    }

    res = 0;
done:
    /* print debug info if requested */
/* …(略)… */
    xmlSecDSigCtxFinalize(&dsigCtx);
    if(data != NULL) {
        xmlSecAppXmlDataDestroy(data);
    }
    return(res);
}
```

`gKeysMngr` グローバル変数
[apps/xmlsec.c#L924](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L924)
```c
xmlSecKeysMngrPtr gKeysMngr = NULL;
```

`xmlSecNodeSignature` 定数
[src/strings.c#L36](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/strings.c#L36)
```c
const xmlChar xmlSecNodeSignature[]             = "Signature";
```

`xmlSecDSigNs` 定数
[src/strings.c#L23](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/strings.c#L23)
```c
const xmlChar xmlSecDSigNs[]                    = "http://www.w3.org/2000/09/xmldsig#";
```

### `xmlSecAppXmlDataCreate` 関数
[apps/xmlsec.c#L2283-L2490](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L2283-L2490)

```c
static xmlSecAppXmlDataPtr 
xmlSecAppXmlDataCreate(const char* filename, const xmlChar* defStartNodeName, const xmlChar* defStartNodeNs) {
    xmlSecAppCmdLineValuePtr value;
    xmlSecAppXmlDataPtr data;
    xmlNodePtr cur = NULL;
        
/* …(略)… */
    
    /* create object */
    data = (xmlSecAppXmlDataPtr) xmlMalloc(sizeof(xmlSecAppXmlData));
    if(data == NULL) {
/* …(略)… */
        return(NULL);
    }
    memset(data, 0, sizeof(xmlSecAppXmlData));
    
    /* parse doc */
    data->doc = xmlSecParseFile(filename);
    if(data->doc == NULL) {
/* …(略)… */
        return(NULL);    
    }
    
    /* load dtd and set default attrs and ids */
/* …(略)… */
    
    /* set ID attributes from command line */
    for(value = idAttrParam.value; value != NULL; value = value->next) {
        if(value->strValue == NULL) {
/* …(略)… */
            return(NULL);
        }
        xmlChar* attrName = (value->paramNameValue != NULL) ? BAD_CAST value->paramNameValue : BAD_CAST "id";
        xmlChar* nodeName;
        xmlChar* nsHref;
        xmlChar* buf;

        buf = xmlStrdup(BAD_CAST value->strValue);
        if(buf == NULL) {
/* …(略)… */
            return(NULL);
        }
        nodeName = (xmlChar*)strrchr((char*)buf, ':');
        if(nodeName != NULL) {
            (*(nodeName++)) = '\0';
            nsHref = buf;
        } else {
/* …(略)… */
        }

        /* process children first because it does not matter much but does simplify code */
        cur = xmlSecGetNextElementNode(data->doc->children);
        while(cur != NULL) {
            if(xmlSecAppAddIDAttr(cur, attrName, nodeName, nsHref) < 0) {
                fprintf(stderr, "Error: failed to add ID attribute \"%s\" for node \"%s\"\n", attrName, value->strValue);
                xmlFree(buf);
                xmlSecAppXmlDataDestroy(data);
                return(NULL);    
            }
            cur = xmlSecGetNextElementNode(cur->next);
        }

        xmlFree(buf);
    }


    /* now find the start node */
    if(xmlSecAppCmdLineParamGetString(&nodeIdParam) != NULL) {
/* …(略)… */
    } else if(xmlSecAppCmdLineParamGetString(&nodeNameParam) != NULL) {
/* …(略)… */
    } else if(xmlSecAppCmdLineParamGetString(&nodeXPathParam) != NULL) {
/* …(略)… */
    } else {
        cur = xmlDocGetRootElement(data->doc);
        if(cur == NULL) {
            fprintf(stderr, "Error: failed to get root element\n"); 
            xmlSecAppXmlDataDestroy(data);
            return(NULL);    
        }
    }
    
    if(defStartNodeName != NULL) {
        data->startNode = xmlSecFindNode(cur, defStartNodeName, defStartNodeNs);
        if(data->startNode == NULL) {
            fprintf(stderr, "Error: failed to find default node with name=\"%s\"\n", 
                    defStartNodeName);
            xmlSecAppXmlDataDestroy(data);
            return(NULL);    
        }
    } else {
/* …(略)… */
    }
    
    return(data);
}
```

### `--id-attr` オプション

`idAttrParam` 変数。上記の `xmlSecAppXmlDataCreate` 関数内で参照されています。
[apps/xmlsec.c#L498-L513](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L498-L513)
```c
static xmlSecAppCmdLineParam idAttrParam = { 
    xmlSecAppCmdLineTopicDSigCommon | 
    xmlSecAppCmdLineTopicEncCommon,
    "--id-attr",
    NULL,   
    "--id-attr[:<attr-name>] [<node-namespace-uri>:]<node-name>"
    "\n\tadds attributes <attr-name> (default value \"id\") from all nodes"
    "\n\twith<node-name> and namespace <node-namespace-uri> to the list of"
    "\n\tknown ID attributes; this is a hack and if you can use DTD or schema"
    "\n\tto declare ID attributes instead (see \"--dtd-file\" option),"
    "\n\tI don't know what else might be broken in your application when"
    "\n\tyou use this hack",
    xmlSecAppCmdLineParamTypeString,
    xmlSecAppCmdLineParamFlagParamNameValue | xmlSecAppCmdLineParamFlagMultipleValues,
    NULL
}; 
```

`xmlSecAppCmdLineParam` 型の定義
[apps/cmdline.h#L19-L20](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/cmdline.h#L19-L20)
```c
typedef struct _xmlSecAppCmdLineParam           xmlSecAppCmdLineParam,
                                                *xmlSecAppCmdLineParamPtr;
```

`struct _xmlSecAppCmdLineParam` の定義
[apps/cmdline.h#L39-L47](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/cmdline.h#L39-L47)
```c
struct _xmlSecAppCmdLineParam {
    xmlSecAppCmdLineParamTopic  topics;
    const char*                 fullName;
    const char*                 shortName;
    const char*                 help;
    xmlSecAppCmdLineParamType   type;
    int                         flags;
    xmlSecAppCmdLineValuePtr    value;
};
```

`--id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response` と指定した場合は、 `xmlSecAppXmlDataCreate` 関数内の `attrName` が `"ID"`, `nodeName` が `"urn:oasis:names:tc:SAML:2.0:protocol:Response"` となります。

### `--pubkey-cert-pem` オプション

`pubkeyCertParam` 変数
[apps/xmlsec.c#L659-L668](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L659-L668)
```c
static xmlSecAppCmdLineParam pubkeyCertParam = { 
    xmlSecAppCmdLineTopicKeysMngr,
    "--pubkey-cert-pem",
    "--pubkey-cert",
    "--pubkey-cert-pem[:<name>] <file>"
    "\n\tload public key from PEM cert file",
    xmlSecAppCmdLineParamTypeStringList,
    xmlSecAppCmdLineParamFlagParamNameValue | xmlSecAppCmdLineParamFlagMultipleValues,
    NULL
};
```

`--pubkey-cert-pem` オプションをパースしている個所
[apps/xmlsec.c#L2130-L2145](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/xmlsec.c#L2130-L2145)
```c
    /* read all public keys in certs */
    for(value = pubkeyCertParam.value; value != NULL; value = value->next) {
        if(value->strValue == NULL) {
            fprintf(stderr, "Error: invalid value for option \"%s\".\n", 
                    pubkeyCertParam.fullName);
            return(-1);
        } else if(xmlSecAppCryptoSimpleKeysMngrKeyAndCertsLoad(gKeysMngr, 
                    value->strListValue, 
                    xmlSecAppCmdLineParamGetString(&pwdParam),
                    value->paramNameValue,
                    xmlSecKeyDataFormatCertPem) < 0) {
            fprintf(stderr, "Error: failed to load public key from \"%s\".\n", 
                    value->strListValue);
            return(-1);
        }
    }
```

`xmlSecAppCryptoSimpleKeysMngrKeyAndCertsLoad` 関数
[apps/crypto.c#L87-L143](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/apps/crypto.c#L87-L143)
```c
int 
xmlSecAppCryptoSimpleKeysMngrKeyAndCertsLoad(xmlSecKeysMngrPtr mngr, 
                                             const char* files, const char* pwd, 
                                             const char* name, 
                                             xmlSecKeyDataFormat format) {
    xmlSecKeyPtr key;
    int ret;

    xmlSecAssert2(mngr != NULL, -1);
    xmlSecAssert2(files != NULL, -1);

    /* first is the key file */
    key = xmlSecCryptoAppKeyLoad(files, format, pwd, 
                xmlSecCryptoAppGetDefaultPwdCallback(), (void*)files);
    if(key == NULL) {
        fprintf(stderr, "Error: xmlSecCryptoAppKeyLoad failed: file=%s\n",
                xmlSecErrorsSafeString(files));
        return(-1);
    }
    
    if(name != NULL) {
        ret = xmlSecKeySetName(key, BAD_CAST name);
        if(ret < 0) {
            fprintf(stderr, "Error: xmlSecKeySetName failed: name=%s\n",
                    xmlSecErrorsSafeString(name));
            xmlSecKeyDestroy(key);
            return(-1);
        }
    }

#ifndef XMLSEC_NO_X509     
    for(files += strlen(files) + 1; (files[0] != '\0'); files += strlen(files) + 1) {
        ret = xmlSecCryptoAppKeyCertLoad(key, files, format);
        if(ret < 0) {
            fprintf(stderr, "Error: xmlSecCryptoAppKeyCertLoad failed: file=%s\n",
                    xmlSecErrorsSafeString(files));
            xmlSecKeyDestroy(key);
            return(-1);
        }
    }
#else /* XMLSEC_NO_X509 */
/* …(略)… */
#endif /* XMLSEC_NO_X509 */        

    ret = xmlSecCryptoAppDefaultKeysMngrAdoptKey(mngr, key);
    if(ret < 0) {
        fprintf(stderr, "Error: xmlSecCryptoAppDefaultKeysMngrAdoptKey failed\n");
        xmlSecKeyDestroy(key);
        return(-1);
    }
    
    return(0);
}
```

`xmlSecCryptoAppKeyLoad` 関数
[src/app.c#L1343-L1364](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/app.c#L1343-L1364)
```c
/**
 * xmlSecCryptoAppKeyLoad:
 * @filename:           the key filename.
 * @format:             the key file format.
 * @pwd:                the key file password.
 * @pwdCallback:        the key password callback.
 * @pwdCallbackCtx:     the user context for password callback.
 *
 * Reads key from the a file.
 *
 * Returns: pointer to the key or NULL if an error occurs.
 /
xmlSecKeyPtr
xmlSecCryptoAppKeyLoad(const char *filename, xmlSecKeyDataFormat format,
                       const char *pwd, void* pwdCallback, void* pwdCallbackCtx) {
    if((xmlSecCryptoDLGetFunctions() == NULL) || (xmlSecCryptoDLGetFunctions()->cryptoAppKeyLoad == NULL)) {
        xmlSecNotImplementedError("cryptoAppKeyLoad");
        return(NULL);
    }

    return(xmlSecCryptoDLGetFunctions()->cryptoAppKeyLoad(filename, format, pwd, pwdCallback, pwdCallbackCtx));
}
```

`xmlSecCryptoDLGetFunctions` 関数
[src/dl.c#L507-L517](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/dl.c#L507-L517)
```c
/**
 * xmlSecCryptoDLGetFunctions:
 *
 * Gets global crypto functions/transforms/keys data/keys store table.
 *
 * Returns: the table.
 */
xmlSecCryptoDLFunctionsPtr
xmlSecCryptoDLGetFunctions(void) {
    return(gXmlSecCryptoDLFunctions);
}
```

この上にグローバル変数 `gXmlSecCryptoDLFunctions` を設定する `xmlSecCryptoDLSetFunctions` 関数があります。
[src/dl.c#L490-L505](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/dl.c#L490-L505)
```c

/**
 * xmlSecCryptoDLSetFunctions:
 * @functions:          the new table
 *
 * Sets global crypto functions/transforms/keys data/keys store table.
 *
 * Returns: 0 on success or a negative value if an error occurs.
 */
int
xmlSecCryptoDLSetFunctions(xmlSecCryptoDLFunctionsPtr functions) {
    xmlSecAssert2(functions != NULL, -1);

    gXmlSecCryptoDLFunctions = functions;

    return(0);
}
```

`xmlSecCryptoDLFunctionsPtr` 型
[include/xmlsec/dl.h#L17-L18](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/include/xmlsec/dl.h#L17-L18)
```c
typedef struct _xmlSecCryptoDLFunctions         xmlSecCryptoDLFunctions,
                                                *xmlSecCryptoDLFunctionsPtr;
```

`struct _xmlSecCryptoDLFunctions` の定義
[include/xmlsec/private.h#L329-L492](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/include/xmlsec/private.h#L329-L492)
```c
/**
 * xmlSecCryptoDLFunctions:
 * @cryptoInit:                 the xmlsec-crypto library initialization method.
 * @cryptoShutdown:             the xmlsec-crypto library shutdown method.
 * @cryptoKeysMngrInit:         the xmlsec-crypto library keys manager init method.
…(略)…
 * @cryptoAppInit:              the default crypto engine initialization method.
 * @cryptoAppShutdown:          the default crypto engine shutdown method.
 * @cryptoAppDefaultKeysMngrInit:       the default keys manager init method.
 * @cryptoAppDefaultKeysMngrAdoptKey:   the default keys manager adopt key method.
 * @cryptoAppDefaultKeysMngrLoad:       the default keys manager load method.
 * @cryptoAppDefaultKeysMngrSave:       the default keys manager save method.
 * @cryptoAppKeysMngrCertLoad:          the default keys manager file cert load method.
 * @cryptoAppKeysMngrCertLoadMemory:    the default keys manager memory cert load method.
 * @cryptoAppKeyLoad:           the key file load method.
 * @cryptoAppKeyLoadMemory:     the meory key load method.
 * @cryptoAppPkcs12Load:        the pkcs12 file load method.
 * @cryptoAppPkcs12LoadMemory:  the memory pkcs12 load method.
 * @cryptoAppKeyCertLoad:       the cert file load method.
 * @cryptoAppKeyCertLoadMemory: the memory cert load method.
 * @cryptoAppDefaultPwdCallback:the default password callback.
 *
 * The list of crypto engine functions, key data and transform classes.
 */
struct _xmlSecCryptoDLFunctions {
    /* Crypto Init/shutdown */
    xmlSecCryptoInitMethod                       cryptoInit;
    xmlSecCryptoShutdownMethod                   cryptoShutdown;
    xmlSecCryptoKeysMngrInitMethod               cryptoKeysMngrInit;

    /* Key data ids */
/* …(略)… */

    /* Key data store ids */
/* …(略)… */

    /* Crypto transforms ids */
/* …(略)… */

    /* High level routines form xmlsec command line utility */
    xmlSecCryptoAppInitMethod                    cryptoAppInit;
    xmlSecCryptoAppShutdownMethod                cryptoAppShutdown;
    xmlSecCryptoAppDefaultKeysMngrInitMethod     cryptoAppDefaultKeysMngrInit;
    xmlSecCryptoAppDefaultKeysMngrAdoptKeyMethod cryptoAppDefaultKeysMngrAdoptKey;
    xmlSecCryptoAppDefaultKeysMngrLoadMethod     cryptoAppDefaultKeysMngrLoad;
    xmlSecCryptoAppDefaultKeysMngrSaveMethod     cryptoAppDefaultKeysMngrSave;
    xmlSecCryptoAppKeysMngrCertLoadMethod        cryptoAppKeysMngrCertLoad;
    xmlSecCryptoAppKeysMngrCertLoadMemoryMethod  cryptoAppKeysMngrCertLoadMemory;
    xmlSecCryptoAppKeyLoadMethod                 cryptoAppKeyLoad;
    xmlSecCryptoAppKeyLoadMemoryMethod           cryptoAppKeyLoadMemory;
    xmlSecCryptoAppPkcs12LoadMethod              cryptoAppPkcs12Load;
    xmlSecCryptoAppPkcs12LoadMemoryMethod        cryptoAppPkcs12LoadMemory;
    xmlSecCryptoAppKeyCertLoadMethod             cryptoAppKeyCertLoad;
    xmlSecCryptoAppKeyCertLoadMemoryMethod       cryptoAppKeyCertLoadMemory;
    void*                                        cryptoAppDefaultPwdCallback;
};
```

`xmlSecCryptoDLFunctionsPtr` の参照箇所を調べると `src/*/crypto.c` で `*` が `gcrypt`, `gnutls`, `mscrypto`, `nss`, `openssl`, `skelton` という 6 つがあります。

`src/openssl/crypto.c` を見てみると `xmlSecCryptoGetFunctions_openssl` 関数があります。
[src/openssl/crypto.c#L33-L308](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/openssl/crypto.c#L33-L308)
```c
/**
 * xmlSecCryptoGetFunctions_openssl:
 *
 * Gets the pointer to xmlsec-openssl functions table.
 *
 * Returns: the xmlsec-openssl functions table or NULL if an error occurs.
 */
xmlSecCryptoDLFunctionsPtr
xmlSecCryptoGetFunctions_openssl(void) {
    static xmlSecCryptoDLFunctions functions;

    if(gXmlSecOpenSSLFunctions != NULL) {
        return(gXmlSecOpenSSLFunctions);
    }

    memset(&functions, 0, sizeof(functions));
    gXmlSecOpenSSLFunctions = &functions;

    /********************************************************************
     *
     * Crypto Init/shutdown
     *
     ********************************************************************/
    gXmlSecOpenSSLFunctions->cryptoInit                 = xmlSecOpenSSLInit;
    gXmlSecOpenSSLFunctions->cryptoShutdown             = xmlSecOpenSSLShutdown;
    gXmlSecOpenSSLFunctions->cryptoKeysMngrInit         = xmlSecOpenSSLKeysMngrInit;

    /********************************************************************
     *
     * Key data ids
     *
     ********************************************************************/
/* …(略)… */

    /********************************************************************
     *
     * Key data store ids
     *
     ********************************************************************/
/* …(略)… */

    /********************************************************************
     *
     * Crypto transforms ids
     *
     ********************************************************************/
/* …(略)… */

    /********************************************************************
     *
     * High level routines form xmlsec command line utility
     *
     ********************************************************************/
    gXmlSecOpenSSLFunctions->cryptoAppInit                      = xmlSecOpenSSLAppInit;
    gXmlSecOpenSSLFunctions->cryptoAppShutdown                  = xmlSecOpenSSLAppShutdown;
    gXmlSecOpenSSLFunctions->cryptoAppDefaultKeysMngrInit       = xmlSecOpenSSLAppDefaultKeysMngrInit;
    gXmlSecOpenSSLFunctions->cryptoAppDefaultKeysMngrAdoptKey   = xmlSecOpenSSLAppDefaultKeysMngrAdoptKey;
    gXmlSecOpenSSLFunctions->cryptoAppDefaultKeysMngrLoad       = xmlSecOpenSSLAppDefaultKeysMngrLoad;
    gXmlSecOpenSSLFunctions->cryptoAppDefaultKeysMngrSave       = xmlSecOpenSSLAppDefaultKeysMngrSave;
#ifndef XMLSEC_NO_X509
    gXmlSecOpenSSLFunctions->cryptoAppKeysMngrCertLoad          = xmlSecOpenSSLAppKeysMngrCertLoad;
    gXmlSecOpenSSLFunctions->cryptoAppKeysMngrCertLoadMemory    = xmlSecOpenSSLAppKeysMngrCertLoadMemory;
    gXmlSecOpenSSLFunctions->cryptoAppPkcs12Load                = xmlSecOpenSSLAppPkcs12Load;
    gXmlSecOpenSSLFunctions->cryptoAppPkcs12LoadMemory          = xmlSecOpenSSLAppPkcs12LoadMemory;
    gXmlSecOpenSSLFunctions->cryptoAppKeyCertLoad               = xmlSecOpenSSLAppKeyCertLoad;
    gXmlSecOpenSSLFunctions->cryptoAppKeyCertLoadMemory         = xmlSecOpenSSLAppKeyCertLoadMemory;
#endif /* XMLSEC_NO_X509 */
    gXmlSecOpenSSLFunctions->cryptoAppKeyLoad                   = xmlSecOpenSSLAppKeyLoad;
    gXmlSecOpenSSLFunctions->cryptoAppKeyLoadMemory             = xmlSecOpenSSLAppKeyLoadMemory;
    gXmlSecOpenSSLFunctions->cryptoAppDefaultPwdCallback        = (void*)xmlSecOpenSSLAppGetDefaultPwdCallback();

    return(gXmlSecOpenSSLFunctions);
}
```

`xmlSecOpenSSLAppKeyLoad` 関数
[src/openssl/app.c#L133-L172](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/openssl/app.c#L133-L172)
```c
/**
 * xmlSecOpenSSLAppKeyLoad:
 * @filename:           the key filename.
 * @format:             the key file format.
 * @pwd:                the key file password.
 * @pwdCallback:        the key password callback.
 * @pwdCallbackCtx:     the user context for password callback.
 *
 * Reads key from the a file.
 *
 * Returns: pointer to the key or NULL if an error occurs.
 */
xmlSecKeyPtr
xmlSecOpenSSLAppKeyLoad(const char *filename, xmlSecKeyDataFormat format,
                        const char *pwd, void* pwdCallback,
                        void* pwdCallbackCtx) {
    BIO* bio;
    xmlSecKeyPtr key;

    xmlSecAssert2(filename != NULL, NULL);
    xmlSecAssert2(format != xmlSecKeyDataFormatUnknown, NULL);

    bio = BIO_new_file(filename, "rb");
    if(bio == NULL) {
        xmlSecOpenSSLError2("BIO_new_file", NULL,
                            "filename=%s", xmlSecErrorsSafeString(filename));
        return(NULL);
    }

    key = xmlSecOpenSSLAppKeyLoadBIO (bio, format, pwd, pwdCallback, pwdCallbackCtx);
    if(key == NULL) {
        xmlSecInternalError2("xmlSecOpenSSLAppKeyLoadBIO", NULL,
                            "filename=%s", xmlSecErrorsSafeString(filename));
        BIO_free(bio);
        return(NULL);
    }

    BIO_free(bio);
    return(key);
}
```

`xmlSecOpenSSLAppKeyLoadBIO` 関数
[src/openssl/app.c#L217-L349](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/src/openssl/app.c#L217-L349)
`format` 引数が上記の `xmlSecAppCryptoSimpleKeysMngrKeyAndCertsLoad` 関数に渡していた `xmlSecKeyDataFormatCertPem` の場合を見てみます。
```c
/**
 * xmlSecOpenSSLAppKeyLoadBIO:
 * @bio:                the key BIO.
 * @format:             the key file format.
 * @pwd:                the key file password.
 * @pwdCallback:        the key password callback.
 * @pwdCallbackCtx:     the user context for password callback.
 *
 * Reads key from the an OpenSSL BIO object.
 *
 * Returns: pointer to the key or NULL if an error occurs.
 */
xmlSecKeyPtr
xmlSecOpenSSLAppKeyLoadBIO(BIO* bio, xmlSecKeyDataFormat format,
                        const char *pwd, void* pwdCallback,
                        void* pwdCallbackCtx) {

    xmlSecKeyPtr key = NULL;
    xmlSecKeyDataPtr data;
    EVP_PKEY* pKey = NULL;
    int ret;

    xmlSecAssert2(bio != NULL, NULL);
    xmlSecAssert2(format != xmlSecKeyDataFormatUnknown, NULL);

    switch(format) {
/* …(略)… */
    case xmlSecKeyDataFormatCertPem:
    case xmlSecKeyDataFormatCertDer:
        key = xmlSecOpenSSLAppKeyFromCertLoadBIO(bio, format);
        if(key == NULL) {
            xmlSecInternalError("xmlSecOpenSSLAppKeyFromCertLoadBIO", NULL);
            return(NULL);
        }
        return(key);
/* …(略)… */
    }

/* …(略)… */
}
```

## XML 署名を検証するサンプル `examples/verify1.c`

`xmlSecCryptoAppKeyLoad` の参照箇所の 1 つにこのサンプルがありました。
XML 署名の検証に特化しているので、こちらのほうが内容を把握しやすいです。

### `verify_file` 関数

[examples/verify1.c#L134-L213](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/examples/verify1.c#L134-L213)
```c
/** 
 * verify_file:
 * @xml_file:           the signed XML file name.
 * @key_file:           the PEM public key file name.
 *
 * Verifies XML signature in #xml_file using public key from #key_file.
 *
 * Returns 0 on success or a negative value if an error occurs.
 */
int 
verify_file(const char* xml_file, const char* key_file) {
    xmlDocPtr doc = NULL;
    xmlNodePtr node = NULL;
    xmlSecDSigCtxPtr dsigCtx = NULL;
    int res = -1;
    
    assert(xml_file);
    assert(key_file);

    /* load file */
    doc = xmlParseFile(xml_file);
    if ((doc == NULL) || (xmlDocGetRootElement(doc) == NULL)){
        fprintf(stderr, "Error: unable to parse file \"%s\"\n", xml_file);
        goto done;      
    }
    
    /* find start node */
    node = xmlSecFindNode(xmlDocGetRootElement(doc), xmlSecNodeSignature, xmlSecDSigNs);
    if(node == NULL) {
        fprintf(stderr, "Error: start node not found in \"%s\"\n", xml_file);
        goto done;      
    }

    /* create signature context, we don't need keys manager in this example */
    dsigCtx = xmlSecDSigCtxCreate(NULL);
    if(dsigCtx == NULL) {
        fprintf(stderr,"Error: failed to create signature context\n");
        goto done;
    }

    /* load public key */
    dsigCtx->signKey = xmlSecCryptoAppKeyLoad(key_file, xmlSecKeyDataFormatPem, NULL, NULL, NULL);
    if(dsigCtx->signKey == NULL) {
        fprintf(stderr,"Error: failed to load public pem key from \"%s\"\n", key_file);
        goto done;
    }

    /* set key name to the file name, this is just an example! */
    if(xmlSecKeySetName(dsigCtx->signKey, key_file) < 0) {
        fprintf(stderr,"Error: failed to set key name for key from \"%s\"\n", key_file);
        goto done;
    }

    /* Verify signature */
    if(xmlSecDSigCtxVerify(dsigCtx, node) < 0) {
        fprintf(stderr,"Error: signature verify\n");
        goto done;
    }
        
    /* print verification result to stdout */
    if(dsigCtx->status == xmlSecDSigStatusSucceeded) {
        fprintf(stdout, "Signature is OK\n");
    } else {
        fprintf(stdout, "Signature is INVALID\n");
    }    

    /* success */
    res = 0;

done:    
    /* cleanup */
    if(dsigCtx != NULL) {
        xmlSecDSigCtxDestroy(dsigCtx);
    }
    
    if(doc != NULL) {
        xmlFreeDoc(doc); 
    }
    return(res);
}
```

検証する xml のファイル名 `xml_file` と公開鍵のファイル名 `key_file` を引数に取ります。
コメントにこの例では keys manager は不要と書かれています。

### `verify_file` 関数を呼び出している `main` 関数

[examples/verify1.c#L38-L132](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/examples/verify1.c#L38-L132)

```c
int 
main(int argc, char **argv) {
#ifndef XMLSEC_NO_XSLT
    xsltSecurityPrefsPtr xsltSecPrefs = NULL;
#endif /* XMLSEC_NO_XSLT */

    assert(argv);

    if(argc != 3) {
        fprintf(stderr, "Error: wrong number of arguments.\n");
        fprintf(stderr, "Usage: %s <xml-file> <key-file>\n", argv[0]);
        return(1);
    }

    /* Init libxml and libxslt libraries */
    xmlInitParser();
    LIBXML_TEST_VERSION
    xmlLoadExtDtdDefaultValue = XML_DETECT_IDS | XML_COMPLETE_ATTRS;
    xmlSubstituteEntitiesDefault(1);
#ifndef XMLSEC_NO_XSLT
    xmlIndentTreeOutput = 1; 
#endif /* XMLSEC_NO_XSLT */

    /* Init libxslt */
#ifndef XMLSEC_NO_XSLT
    /* disable everything */
    xsltSecPrefs = xsltNewSecurityPrefs(); 
    xsltSetSecurityPrefs(xsltSecPrefs,  XSLT_SECPREF_READ_FILE,        xsltSecurityForbid);
    xsltSetSecurityPrefs(xsltSecPrefs,  XSLT_SECPREF_WRITE_FILE,       xsltSecurityForbid);
    xsltSetSecurityPrefs(xsltSecPrefs,  XSLT_SECPREF_CREATE_DIRECTORY, xsltSecurityForbid);
    xsltSetSecurityPrefs(xsltSecPrefs,  XSLT_SECPREF_READ_NETWORK,     xsltSecurityForbid);
    xsltSetSecurityPrefs(xsltSecPrefs,  XSLT_SECPREF_WRITE_NETWORK,    xsltSecurityForbid);
    xsltSetDefaultSecurityPrefs(xsltSecPrefs); 
#endif /* XMLSEC_NO_XSLT */
                
    /* Init xmlsec library */
    if(xmlSecInit() < 0) {
        fprintf(stderr, "Error: xmlsec initialization failed.\n");
        return(-1);
    }

    /* Check loaded library version */
    if(xmlSecCheckVersion() != 1) {
        fprintf(stderr, "Error: loaded xmlsec library version is not compatible.\n");
        return(-1);
    }

    /* Load default crypto engine if we are supporting dynamic
     * loading for xmlsec-crypto libraries. Use the crypto library
     * name ("openssl", "nss", etc.) to load corresponding 
     * xmlsec-crypto library.
     */
#ifdef XMLSEC_CRYPTO_DYNAMIC_LOADING
    if(xmlSecCryptoDLLoadLibrary(NULL) < 0) {
        fprintf(stderr, "Error: unable to load default xmlsec-crypto library. Make sure\n"
                        "that you have it installed and check shared libraries path\n"
                        "(LD_LIBRARY_PATH and/or LTDL_LIBRARY_PATH) envornment variables.\n");
        return(-1);     
    }
#endif /* XMLSEC_CRYPTO_DYNAMIC_LOADING */

    /* Init crypto library */
    if(xmlSecCryptoAppInit(NULL) < 0) {
        fprintf(stderr, "Error: crypto initialization failed.\n");
        return(-1);
    }

    /* Init xmlsec-crypto library */
    if(xmlSecCryptoInit() < 0) {
        fprintf(stderr, "Error: xmlsec-crypto initialization failed.\n");
        return(-1);
    }

    if(verify_file(argv[1], argv[2]) < 0) {
        return(-1);
    }    
    
    /* Shutdown xmlsec-crypto library */
    xmlSecCryptoShutdown();
    
    /* Shutdown crypto library */
    xmlSecCryptoAppShutdown();
    
    /* Shutdown xmlsec library */
    xmlSecShutdown();

    /* Shutdown libxslt/libxml */
#ifndef XMLSEC_NO_XSLT
    xsltFreeSecurityPrefs(xsltSecPrefs);
    xsltCleanupGlobals();            
#endif /* XMLSEC_NO_XSLT */
    xmlCleanupParser();
    
    return(0);
}
```

`Makefile`
[examples/Makefile](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/examples/Makefile)

```make
#
#
#
PROGRAMS = \
	sign1 sign2 sign3 \
	verify1 verify2 verify3 verify4 \
	encrypt1 encrypt2 encrypt3 \
	decrypt1 decrypt2 decrypt3 \
	xmldsigverify

CC	= gcc
CFLAGS	+= -g $(shell xmlsec1-config --cflags) -DUNIX_SOCKETS
LDLIBS	+= -g $(shell xmlsec1-config --libs)

all: $(PROGRAMS)

clean:
	@rm -rf $(PROGRAMS)

check: $(PROGRAMS)
	./sign1    sign1-tmpl.xml    rsakey.pem
	./sign2    sign2-doc.xml     rsakey.pem
	./sign3    sign3-doc.xml     rsakey.pem rsacert.pem
	./verify1  sign1-res.xml     rsapub.pem
	./verify1  sign2-res.xml     rsapub.pem
	./verify2  sign1-res.xml     rsapub.pem
	./verify2  sign2-res.xml     rsapub.pem
	./verify3  sign3-res.xml     ca2cert.pem cacert.pem
	./verify4  verify4-res.xml   ca2cert.pem cacert.pem
	./encrypt1 encrypt1-tmpl.xml deskey.bin
	./encrypt2 encrypt2-doc.xml  deskey.bin 
	./encrypt3 encrypt3-doc.xml  rsakey.pem
	./decrypt1 encrypt1-res.xml  deskey.bin
	./decrypt1 encrypt2-res.xml  deskey.bin
	./decrypt2 encrypt1-res.xml  deskey.bin
	./decrypt2 encrypt2-res.xml  deskey.bin
	./decrypt3 encrypt1-res.xml
	./decrypt3 encrypt2-res.xml
	./decrypt3 encrypt3-res.xml
```

## 署名された SAML Response の例

https://www.samltool.com/generic_sso_res.php の "SAML Response with Signed Message" からコピーし、 `saml1-res.xml` というファイル名で保存しました。
```xml
<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="pfx360ab10b-52ba-ceb3-ea47-5411cba02d9f" Version="2.0" IssueInstant="2014-07-17T01:01:48Z" Destination="http://sp.example.com/demo1/index.php?acs" InResponseTo="ONELOGIN_4fee3b046395c4e751011e97f8900b5273d56685">
  <saml:Issuer>http://idp.example.com/metadata.php</saml:Issuer><ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <ds:SignedInfo><ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
    <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
  <ds:Reference URI="#pfx360ab10b-52ba-ceb3-ea47-5411cba02d9f"><ds:Transforms><ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/><ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/></ds:Transforms><ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/><ds:DigestValue>wrEJfBXjfGWHF4oPIyUrnX52Rlw=</ds:DigestValue></ds:Reference></ds:SignedInfo><ds:SignatureValue>Ax3cMXm08CXUwhIfd/2zVnqG85V5XOXxsgl0vGoQ2yn3OxX4u/KsN1fisKuZxKfBH53JULPIxmREE3+1L1Nv227TLTxzWCw3z8ohjjWZ8+CvCnj/XgR6A4ExorFrmKZqBsC30pBZ+STPEoufToHkPlAWDHw7z7dY17XfAzfGAYI=</ds:SignatureValue>
<ds:KeyInfo><ds:X509Data><ds:X509Certificate>MIICajCCAdOgAwIBAgIBADANBgkqhkiG9w0BAQ0FADBSMQswCQYDVQQGEwJ1czETMBEGA1UECAwKQ2FsaWZvcm5pYTEVMBMGA1UECgwMT25lbG9naW4gSW5jMRcwFQYDVQQDDA5zcC5leGFtcGxlLmNvbTAeFw0xNDA3MTcxNDEyNTZaFw0xNTA3MTcxNDEyNTZaMFIxCzAJBgNVBAYTAnVzMRMwEQYDVQQIDApDYWxpZm9ybmlhMRUwEwYDVQQKDAxPbmVsb2dpbiBJbmMxFzAVBgNVBAMMDnNwLmV4YW1wbGUuY29tMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDZx+ON4IUoIWxgukTb1tOiX3bMYzYQiwWPUNMp+Fq82xoNogso2bykZG0yiJm5o8zv/sd6pGouayMgkx/2FSOdc36T0jGbCHuRSbtia0PEzNIRtmViMrt3AeoWBidRXmZsxCNLwgIV6dn2WpuE5Az0bHgpZnQxTKFek0BMKU/d8wIDAQABo1AwTjAdBgNVHQ4EFgQUGHxYqZYyX7cTxKVODVgZwSTdCnwwHwYDVR0jBBgwFoAUGHxYqZYyX7cTxKVODVgZwSTdCnwwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQ0FAAOBgQByFOl+hMFICbd3DJfnp2Rgd/dqttsZG/tyhILWvErbio/DEe98mXpowhTkC04ENprOyXi7ZbUqiicF89uAGyt1oqgTUCD1VsLahqIcmrzgumNyTwLGWo17WDAa1/usDhetWAMhgzF/Cnf5ek0nK00m0YZGyc4LzgD0CROMASTWNg==</ds:X509Certificate></ds:X509Data></ds:KeyInfo></ds:Signature>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" ID="_d71a3a8e9fcc45c9e9d248ef7049393fc8f04e5f75" Version="2.0" IssueInstant="2014-07-17T01:01:48Z">
    <saml:Issuer>http://idp.example.com/metadata.php</saml:Issuer>
    <saml:Subject>
      <saml:NameID SPNameQualifier="http://sp.example.com/demo1/metadata.php" Format="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">_ce3d2948b4cf20146dee0a0b3dd6f69b6cf86f62d7</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData NotOnOrAfter="2024-01-18T06:21:48Z" Recipient="http://sp.example.com/demo1/index.php?acs" InResponseTo="ONELOGIN_4fee3b046395c4e751011e97f8900b5273d56685"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="2014-07-17T01:01:18Z" NotOnOrAfter="2024-01-18T06:21:48Z">
      <saml:AudienceRestriction>
        <saml:Audience>http://sp.example.com/demo1/metadata.php</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AuthnStatement AuthnInstant="2014-07-17T01:01:48Z" SessionNotOnOrAfter="2024-07-17T09:01:48Z" SessionIndex="_be9967abd904ddcae3c0eb4189adbe3f71e327cf93">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:Password</saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>
    <saml:AttributeStatement>
      <saml:Attribute Name="uid" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
        <saml:AttributeValue xsi:type="xs:string">test</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="mail" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
        <saml:AttributeValue xsi:type="xs:string">test@example.com</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="eduPersonAffiliation" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:basic">
        <saml:AttributeValue xsi:type="xs:string">users</saml:AttributeValue>
        <saml:AttributeValue xsi:type="xs:string">examplerole1</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>
```

証明書は上記のレスポンスの `<ds:X509Certificate>` の値を証明書の開始と終了マーカーで挟んで作成し、 `saml1-idp-cert.pem` というファイル名で保存しました。
```text
-----BEGIN CERTIFICATE-----
MIICajCCAdOgAwIBAgIBADANBgkqhkiG9w0BAQ0FADBSMQswCQYDVQQGEwJ1czETMBEGA1UECAwKQ2FsaWZvcm5pYTEVMBMGA1UECgwMT25lbG9naW4gSW5jMRcwFQYDVQQDDA5zcC5leGFtcGxlLmNvbTAeFw0xNDA3MTcxNDEyNTZaFw0xNTA3MTcxNDEyNTZaMFIxCzAJBgNVBAYTAnVzMRMwEQYDVQQIDApDYWxpZm9ybmlhMRUwEwYDVQQKDAxPbmVsb2dpbiBJbmMxFzAVBgNVBAMMDnNwLmV4YW1wbGUuY29tMIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDZx+ON4IUoIWxgukTb1tOiX3bMYzYQiwWPUNMp+Fq82xoNogso2bykZG0yiJm5o8zv/sd6pGouayMgkx/2FSOdc36T0jGbCHuRSbtia0PEzNIRtmViMrt3AeoWBidRXmZsxCNLwgIV6dn2WpuE5Az0bHgpZnQxTKFek0BMKU/d8wIDAQABo1AwTjAdBgNVHQ4EFgQUGHxYqZYyX7cTxKVODVgZwSTdCnwwHwYDVR0jBBgwFoAUGHxYqZYyX7cTxKVODVgZwSTdCnwwDAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQ0FAAOBgQByFOl+hMFICbd3DJfnp2Rgd/dqttsZG/tyhILWvErbio/DEe98mXpowhTkC04ENprOyXi7ZbUqiicF89uAGyt1oqgTUCD1VsLahqIcmrzgumNyTwLGWo17WDAa1/usDhetWAMhgzF/Cnf5ek0nK00m0YZGyc4LzgD0CROMASTWNg==
-----END CERTIFICATE-----
```

`xmlsec1` コマンドでは以下のように検証に成功しました。

```console
$ xmlsec1 --verify --pubkey-cert-pem saml1-idp-cert.pem --id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response saml1-res.xml

func=xmlSecOpenSSLX509StoreVerify:file=x509vfy.c:line=341:obj=x509-store:subj=unknown:error=71:certificate verification failed:X509_verify_cert: subject=/C=us/ST=California/O=Onelogin Inc/CN=sp.example.com; issuer=/C=us/ST=California/O=Onelogin Inc/CN=sp.example.com; err=18; msg=self signed certificate
func=xmlSecOpenSSLX509StoreVerify:file=x509vfy.c:line=380:obj=x509-store:subj=unknown:error=71:certificate verification failed:subject=/C=us/ST=California/O=Onelogin Inc/CN=sp.example.com; issuer=/C=us/ST=California/O=Onelogin Inc/CN=sp.example.com; err=18; msg=self signed certificate
OK
SignedInfo References (ok/all): 1/1
Manifests References (ok/all): 0/0
```

一方、上記の verify1 サンプルは以下のように失敗します。ここで気づいたのですが、 verify1 サンプルは公開鍵を受け取るようになっていて証明書を受け取るわけではありませんでした。

```console
$ ./verify1 saml1-res.xml saml1-idp-cert.pem
func=xmlSecOpenSSLAppKeyLoadBIO:file=app.c:line=261:obj=unknown:subj=PEM_read_bio_PrivateKey and PEM_read_bio_PUBKEY:error=4:crypto library function failed:openssl error: 151584876: PEM routines: get_name no start line
func=xmlSecOpenSSLAppKeyLoad:file=app.c:line=165:obj=unknown:subj=xmlSecOpenSSLAppKeyLoadBIO:error=1:xmlsec library function failed:filename=saml1-idp-cert.pem
Error: failed to load public pem key from "saml1-idp-cert.pem"
```
