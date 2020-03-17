---
title: "XMLSecでの証明書検証のコードリーディング"
date: 2020-03-17T20:01:08+09:00
---
## はじめに

[nginx luaでSAMLのService Providerを作ってみた · hnakamur's blog](/blog/2018/07/31/saml-service-provider-with-nginx-lua/) の [hnakamur/nginx-lua-saml-service-provider](https://github.com/hnakamur/nginx-lua-saml-service-provider) ですがレスポンスのXMLを検証する処理は非同期ではなく同期的に実行される実装としていました。 詳しくは [Caveats](https://github.com/hnakamur/nginx-lua-saml-service-provider/blob/90b79233bfc28dd48ad8f2d38a8d547d182f1a62/README.md#caveats) に書いています。

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

## XML 署名を検証するサンプル `examples/verify4.c`

`xmlSecCryptoAppKeyLoad` の参照箇所の 1 つにこのサンプルがありました。
XML 署名の検証に特化しているので、こちらのほうが内容を把握しやすいです。

[examples/verify4.c](https://github.com/lsh123/xmlsec/blob/xmlsec-1_2_25/examples/verify4.c)

ただし、コードを見たり動かして試してみた感じでは

```console
xmlsec1 --verify --pubkey-cert-pem idp.crt \
  --id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response
  response.xml
```

のコマンドの `--id-attr:ID urn:oasis:names:tc:SAML:2.0:protocol:Response` 相当の処理は
verify4 のサンプルには含まれてないようです。

と、中途半端ですが、今回はこの辺で。
