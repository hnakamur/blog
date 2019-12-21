+++
title="nginxとshibbolethでSAML2のシングルサインオンを試してみた"
date = "2018-07-04T16:40:00+09:00"
lastmod = "2018-07-13T09:50:00+09:00"
tags = ["saml", "nginx", "single-sign-on", "shibboleth"]
categories = ["blog"]
+++


# はじめに

勤務先でSAML2のシングルサインオンについて調査していたところ
[Is this module compatible with SAML 2 in HTTP POST mode? · Issue #16 · nginx-shib/nginx-http-shibboleth](https://github.com/nginx-shib/nginx-http-shibboleth/issues/16)
というイシューを見つけました。
この nginx-http-shibboleth というモジュールを使えば実現できそうということで、 
nginxとshibbolethでSAML2のシングルサインオンを試してみたメモです。

なお、とりあえず試してみただけで、セキュリティ上問題無い設定になっているかは未確認なのでご注意ください。

SAML認証についての概要は
[SAML認証を勉強せずに理解したい私から勉強せずに理解したい私へ - Qiita](https://qiita.com/khsk/items/10a136bded197272094a)
で紹介されていた
[SAML認証ができるまで - Cybozu Inside Out | サイボウズエンジニアのブログ](http://blog.cybozu.io/entry/4224)
がわかりやすかったです。

登場人物とサービスは以下の3つです。

* エンドユーザ
* 実際に認証を行う Identity Provider (IdP)
* IdPを利用してサービスを提供する Service Provider (SP) 

今回はIdPは勤務先で用意されたテスト用のIdPを使いつつ、SPをnginxと [Shibboleth](https://www.internet2.edu/products-services/trust-identity/shibboleth/) でCentOS7上で構築してみました。

ShibbolethについてはWikipediaの
[シボレス - Wikipedia](https://ja.wikipedia.org/wiki/%E3%82%B7%E3%83%9C%E3%83%AC%E3%82%B9)
のページがわかりやすかったです。

# 自作rpmパッケージ作成

nginx以外に以下のソフトウェアが必要になるので、自作rpmパッケージを作りました。

## nginx-http-shibbolethモジュール

nginxからShibbolethに連携して認証を行うために
[nginx-shib/nginx-http-shibboleth: Shibboleth auth request module for nginx](https://github.com/nginx-shib/nginx-http-shibboleth)
というモジュールを使うので、いつも利用しているnginxの自作rpm
[hnakamur/nginx Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/nginx/)
にこのモジュールを追加してビルドしました。

なお
[nginx-shib/nginx-http-shibboleth](https://github.com/nginx-shib/nginx-http-shibboleth) が依存している
[openresty/headers-more-nginx-module](https://github.com/openresty/headers-more-nginx-module) も必要ですが、これは既に自作rpmに含めていました。


## FastCGIサポートを有効にしたShibboleth SP

[Shibboleth SP with FastCGI Support](https://github.com/nginx-shib/nginx-http-shibboleth/blob/master/CONFIG.rst#shibboleth-sp-with-fastcgi-support) に説明があります。DebianとUbuntuでは shibboleth-sp-utils パッケージがFastCGIサポートを有効にしてビルドされていますが、CentOS 7で使うShibolleth公式レポジトリのrpmパッケージではFastCGIサポートが無効なので、有効にしたものを自分でビルドする必要があります。

[nginx-shib/shibboleth-fastcgi](https://github.com/nginx-shib/shibboleth-fastcgi) にFastCGIサポートを有効にしてrpmをビルドするための説明がありますので、これを参考にして自作rpmをビルドしました。

* FastCGIサポート有りのShibbolethの自作rpmのレポジトリ [hnakamur/shibboleth Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/shibboleth/)
* 上記のrpmのソース [hnakamur/shibboleth-fastcgi-rpm](https://github.com/hnakamur/shibboleth-fastcgi-rpm)

shibbolethのrpmをインストールすると `shibd` というサービスが追加されるのですが、FastCGIを有効にするとさらに `shibauthorizer` と `shibresponder` という2つのサービスが追加されます。

この2つを [Supervisor (supervisord)](http://supervisord.org/) でFastCGIとして実行するための設定が
[Running the FastCGI authorizer and responder](https://github.com/nginx-shib/nginx-http-shibboleth/blob/master/CONFIG.rst#running-the-fastcgi-authorizer-and-responder)
に書かれています。

今回はCentOS 7ということでsystemdを使ってFastCGIとして実行するようにしました。この方法は今回初めて知ったのでメモしておきます。

[Systemd - spawn-fcgi - lighty labs](https://redmine.lighttpd.net/projects/spawn-fcgi/wiki/Systemd)
と
[systemd to FastCGI socket passing compatibility script](https://gist.github.com/stbuehler/439a9849747279a1f0a9#gistcomment-1950602)
を参考にして以下のようにsystemd用の `.socket` ファイルと `.service` を作りました。

`/lib/systemd/system/shibauthorizer.socket`

```text
[Unit]
Description=shibauthorizer socket

[Socket]
SocketUser=shibd
SocketGroup=shibd
SocketMode=0660
ListenStream=/run/shibboleth/shibauthorizer.sock
Accept=false

[Install]
WantedBy=sockets.target
```

`/lib/systemd/system/shibauthorizer.service`

```text
[Unit]
Description=shibauthorizer
After=network.target
Requires=shibauthorizer.socket

[Service]
Type=simple
ExecStart=/usr/lib64/shibboleth/shibauthorizer
User=shibd
Group=shibd
StandardInput=socket
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

`.socket` ファイルの `ListenStream` でUnixドメインソケットを作成し、 `.service` ファイルで `StandardInput=socket` と指定することでそこから入力を読み取るというわけです。

上記の2つは `shibauthorizer` 用ですが、 `shibresponder` 用にも同様に2つ作りました。

## xml-security-c

Shibbolethのrpmをビルドするための `shibboleth.spec` ファイルに

```text
BuildRequires:  libxml-security-c-devel >= 1.7.3
```

という
[行](https://github.com/hnakamur/shibboleth-fastcgi-rpm/blob/3952b09f2670f13ac343210eeb9580ce83d36e07/SPECS/shibboleth.spec#L31)
があり、 `libxml-security-c-devel` というパッケージに依存していることがわかりました。

yumでインストールしようとしたのですが、これはCentOS 7の標準レポジトリやepelにはありませんでした。
検索してみつけた
[Linux @ CERN: /cern/centos/7/cern/x86_64/repoview/libxml-security-c-devel.html](http://linuxsoft.cern.ch/cern/centos/7/cern/x86_64/repoview/libxml-security-c-devel.html)
によると CentOS CERN 7 (CC7) という別のディストリビューションには入っているようです。

[CC7: CERN CentOS 7](http://linux.web.cern.ch/linux/centos7/) を見たところ、CentOS 7用の追加レポジトリというよりは、カスタム版の別ディストリビューションのようなので、これに依存するよりはrpmをリビルドして使うほうが良いと考えてCoprでビルドしました。

* xml-security-cの自作rpmのレポジトリ [hnakamur/xml-security-c Copr](https://copr.fedorainfracloud.org/coprs/hnakamur/xml-security-c/)
* xml-security-cの自作rpmのソース [hnakamur/xml-security-c-rpm](https://github.com/hnakamur/xml-security-c-rpm)

# インストール手順

上記の自作rpmに加えて `xmltooling-schemas` と `opensaml-schemas` パッケージをインストールするためにShibbolethのレポジトリを追加する必要があります。

[NativeSPLinuxRPMInstall - Shibboleth 2 - Shibboleth Wiki](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPLinuxRPMInstall) にrpmのインストール手順が書いてあるのですが、それとは別に
[nginx-shib/shibboleth-fastcgi](https://github.com/nginx-shib/shibboleth-fastcgi) レポジトリに
以下のような [shibboleth.repo](https://github.com/nginx-shib/shibboleth-fastcgi/blob/master/configs/centos-7/shibboleth.repo) ファイルがあったので、これを使わせてもらうことにしました。

```text
[shibboleth]
name=Shibboleth (CentOS_7)
# Please report any problems to https://issues.shibboleth.net
type=rpm-md
mirrorlist=https://shibboleth.net/cgi-bin/mirrorlist.cgi/CentOS_7
gpgcheck=1
gpgkey=https://downloadcontent.opensuse.org/repositories/security:/shibboleth/CentOS_7/repodata/repomd.xml.key
enabled=1
```

以下のコマンドを実行して必要なレポジトリを追加します。

```console
sudo curl -sSL -o /etc/yum.repos.d/shibboleth.repo https://raw.githubusercontent.com/nginx-shib/shibboleth-fastcgi/master/configs/centos-7/shibboleth.repo
sudo curl -sSL -o /etc/yum.repos.d/hnakamur-nginx-epel-7.repo https://copr.fedorainfracloud.org/coprs/hnakamur/nginx/repo/epel-7/hnakamur-nginx-epel-7.repo
sudo curl -sSL -o /etc/yum.repos.d/hnakamur-xml-security-c-epel-7.repo https://copr.fedorainfracloud.org/coprs/hnakamur/xml-security-c/repo/epel-7/hnakamur-xml-security-c-epel-7.repo
sudo curl -sSL -o /etc/yum.repos.d/hnakamur-shibboleth-epel-7.repo https://copr.fedorainfracloud.org/coprs/hnakamur/shibboleth/repo/epel-7/hnakamur-shibboleth-epel-7.repo
```

以下のコマンドを実行して必要なrpmをインストールします。

```console
sudo yum install nginx shibboleth xmltooling-schemas opensaml-schemas
```

2018-07-13 追記。
`nginx` ユーザが `/run/shibboleth/shibauthorizer.socket` と `/run/shibboleth/shibresponder.socket` に読み書きできるようにするため、 `shibd` グループに `nginx` ユーザを追加します。

```console
sudo usermod -a -G shibd nginx
```

# 設定ファイルの編集

## ShibbolethのSP用設定

ShibbolethのSP用の設定については
[NativeSPConfiguration - Shibboleth 2 - Shibboleth Wiki](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPConfiguration)
にドキュメントがあります。

量が多くて読むのが大変なので、私はまだ必要なところだけを拾い読みしただけの状態です。

#### IdPのメタデータのXML

SAMLのメタデータについては
[Metadata for the OASIS Security Assertion Markup Language (SAML) V2.0](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf)
が1次情報のドキュメントのようです（検索して見つけたのでリンク元は不明）。

今回は社内で教えてもらった
[SAML Identity Provider (IdP) XML Metadata Builder | SAMLTool.com](https://www.samltool.com/idp_metadata.php)
というオンラインのツールを使いました。

この後は以下の構成例で説明します。

* IdPのエンティティID: https://idp.example.com/sso-test/idp
* HTTPリダイレクト先のシングルサインオンのエンドポイント: https://idp.example.com/sso-test/idp/sso_redirect
* 署名と暗号化に使う証明書:

```text
-----BEGIN CERTIFICATE-----
MIIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
…（略）…
xxxxxxxxxxxxxxxxxxxTow==
-----END CERTIFICATE-----
```

上記の項目を入力して "BUILD IDP METADATA" ボタンを押すとページの下の方に以下のようなXMLが出力されました。

```xml
<?xml version="1.0"?>
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" validUntil="2018-06-30T08:00:05Z" cacheDuration="PT1530777605S" entityID="https://idp.example.com/sso-test/idp">
  <md:IDPSSODescriptor WantAuthnRequestsSigned="false" protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:KeyDescriptor use="signing">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>MIIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…（略）…xxxxxxxxxxxxxxxxxxxTow==</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:KeyDescriptor use="encryption">
      <ds:KeyInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
        <ds:X509Data>
          <ds:X509Certificate>MIIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx…（略）…xxxxxxxxxxxxxxxxxxxTow==</ds:X509Certificate>
        </ds:X509Data>
      </ds:KeyInfo>
    </md:KeyDescriptor>
    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified</md:NameIDFormat>
    <md:SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="https://idp.example.com/sso-test/idp/sso_redirect"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>
```

`<ds:X509Certificate>` の値は証明書の
`-----BEGIN CERTIFICATE-----` と
`-----END CERTIFICATE-----` の間の行が連結されたものになっていました。

ちょっと脱線しますが、これで週末動作確認した後、週明けに再度確認したらエラーが起きるようになってしまいました。これは上記の `validUntil` の日付を過ぎていたのでこのメタデータが無効として扱われたからとわかりました。

[Metadata for the OASIS Security Assertion Markup Language (SAML) V2.0](https://docs.oasis-open.org/security/saml/v2.0/saml-metadata-2.0-os.pdf)
によると `validUntil` と `cacheDuration` はともに省略可能とのことなので、最終的には省略することにしました。

これを `/etc/shibboleth/idp-metadata.xml` というファイル名で保存しました。

#### アトリビュートのマッピングのXML

当初IdPで認証通った後にアトリビュートは何も返さない設定になっていたのですが、認証後のページに以下のようなエラーが表示されたので、 `mail` という名前でメールアドレスをアトリビュートとして返してもらうように設定してもらいました。

```text
xmltooling::ValidationException
The system encountered an error at Fri Jun 29 02:08:20 2018

To report this problem, please contact the site administrator at hnakamur@localhost.

Please include the following message in any email:

xmltooling::ValidationException at (http://localhost/Shibboleth.sso/SAML2/POST)

AttributeStatement must have at least one child element.
```

その後 [NativeSPAddAttribute - Shibboleth 2 - Shibboleth Wiki](https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPAddAttribute) を読みつつ
`/etc/shibboleth/attribute-map.xml` というファイルを以下のように編集しました。

```xml
<Attributes xmlns="urn:mace:shibboleth:2.0:attribute-map" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Attribute name="mail" id="mail"/>
</Attributes>
```

#### Shibbolethのメイン設定のXML

上記のIdPの設定項目の例に加えて、SPの設定項目として以下の例で説明します。

* SPの管理者のメールアドレス: admin@sp.example.org
* SPのエンティティID: https://sp.example.org/sso

なお、SPでは証明書を使わない構成とし、SPのエンティティIDをIdPの管理者にお願いして登録してもらいました。

`/etc/shibboleth/shibboleth2.xml` を以下のように変更しました。

下記の変更内容は以下のコマンドで表示しました。

```console
diff -u shibboleth-sp-2.6.1/configs/shibboleth2.xml shibboleth2.xml
```

.. code-block:: diff

    --- shibboleth-sp-2.6.1/configs/shibboleth2.xml        2017-11-14 08:29:46.000000000 +0900
    +++ shibboleth2.xml        2018-07-04 10:12:32.283184405 +0900
    @@ -19,8 +19,19 @@
         file, and the https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPRequestMapHowTo topic.
         -->
     
    +    <RequestMapper type="XML">
    +        <RequestMap>
    +            <Host name="localhost"
    +                  authType="shibboleth"
    +                  requireSession="true"
    +                  redirectToSSL="443">
    +                <Path name="/secure" />
    +            </Host>
    +        </RequestMap>
    +    </RequestMapper>
    +
         <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
    -    <ApplicationDefaults entityID="https://sp.example.org/shibboleth"
    +    <ApplicationDefaults entityID="https://sp.example.org/sso"
                              REMOTE_USER="eppn persistent-id targeted-id">
     
             <!--
    @@ -35,14 +46,7 @@
             <Sessions lifetime="28800" timeout="3600" relayState="ss:mem"
                       checkAddress="false" handlerSSL="false" cookieProps="http">
     
    -            <!--
    -            Configures SSO for a default IdP. To allow for >1 IdP, remove
    -            entityID property and adjust discoveryURL to point to discovery service.
    -            (Set discoveryProtocol to "WAYF" for legacy Shibboleth WAYF support.)
    -            You can also override entityID on /Login query string, or in RequestMap/htaccess.
    -            -->
    -            <SSO entityID="https://idp.example.org/idp/shibboleth"
    -                 discoveryProtocol="SAMLDS" discoveryURL="https://ds.example.org/DS/WAYF">
    +                  <SSO entityID="https://idp.example.com/sso-test/idp">
                   SAML2 SAML1
                 </SSO>
     
    @@ -66,53 +70,16 @@
             Allows overriding of error template information/filenames. You can
             also add attributes with values that can be plugged into the templates.
             -->
    -        <Errors supportContact="root@localhost"
    +        <Errors supportContact="admin@sp.example.org"
                 helpLocation="/about.html"
                 styleSheet="/shibboleth-sp/main.css"/>
    -        
    -        <!-- Example of remotely supplied batch of signed metadata. -->
    -        <!--
    -        <MetadataProvider type="XML" validate="true"
    -              uri="http://example.org/federation-metadata.xml"
    -              backingFilePath="federation-metadata.xml" reloadInterval="7200">
    -            <MetadataFilter type="RequireValidUntil" maxValidityInterval="2419200"/>
    -            <MetadataFilter type="Signature" certificate="fedsigner.pem"/>
    -            <DiscoveryFilter type="Blacklist" matcher="EntityAttributes" trimTags="true" 
    -              attributeName="http://macedir.org/entity-category"
    -              attributeNameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:uri"
    -              attributeValue="http://refeds.org/category/hide-from-discovery" />
    -        </MetadataProvider>
    -        -->
     
             <!-- Example of locally maintained metadata. -->
    -        <!--
    -        <MetadataProvider type="XML" validate="true" file="partner-metadata.xml"/>
    -        -->
    +        <MetadataProvider type="XML" validate="true" file="idp-metadata.xml"/>
     
             <!-- Map to extract attributes from SAML assertions. -->
             <AttributeExtractor type="XML" validate="true" reloadChanges="false" path="attribute-map.xml"/>
    -        
    -        <!-- Use a SAML query if no attributes are supplied during SSO. -->
    -        <AttributeResolver type="Query" subjectMatch="true"/>
    -
    -        <!-- Default filtering policy for recognized attributes, lets other data pass. -->
    -        <AttributeFilter type="XML" validate="true" path="attribute-policy.xml"/>
     
    -        <!-- Simple file-based resolver for using a single keypair. -->
    -        <CredentialResolver type="File" key="sp-key.pem" certificate="sp-cert.pem"/>
    -
    -        <!--
    -        The default settings can be overridden by creating ApplicationOverride elements (see
    -        the https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPApplicationOverride topic).
    -        Resource requests are mapped by web server commands, or the RequestMapper, to an
    -        applicationId setting.
    -        
    -        Example of a second application (for a second vhost) that has a different entityID.
    -        Resources on the vhost would map to an applicationId of "admin":
    -        -->
    -        <!--
    -        <ApplicationOverride id="admin" entityID="https://admin.example.org/shibboleth"/>
    -        -->
         </ApplicationDefaults>
         
         <!-- Policies that determine how to process and authenticate runtime messages. -->

変更後の `/etc/shibboleth/shibboleth2.xml` 全体は以下のとおりです。

```xml
<SPConfig xmlns="urn:mace:shibboleth:2.0:native:sp:config"
    xmlns:conf="urn:mace:shibboleth:2.0:native:sp:config"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"    
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    clockSkew="180">

    <!--
    By default, in-memory StorageService, ReplayCache, ArtifactMap, and SessionCache
    are used. See example-shibboleth2.xml for samples of explicitly configuring them.
    -->

    <!--
    To customize behavior for specific resources on Apache, and to link vhosts or
    resources to ApplicationOverride settings below, use web server options/commands.
    See https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPConfigurationElements for help.
    
    For examples with the RequestMap XML syntax instead, see the example-shibboleth2.xml
    file, and the https://wiki.shibboleth.net/confluence/display/SHIB2/NativeSPRequestMapHowTo topic.
    -->

    <RequestMapper type="XML">
        <RequestMap>
            <Host name="localhost"
                  authType="shibboleth"
                  requireSession="true"
                  redirectToSSL="443">
                <Path name="/secure" />
            </Host>
        </RequestMap>
    </RequestMapper>

    <!-- The ApplicationDefaults element is where most of Shibboleth's SAML bits are defined. -->
    <ApplicationDefaults entityID="https://sp.example.org/sso"
                         REMOTE_USER="eppn persistent-id targeted-id">

        <!--
        Controls session lifetimes, address checks, cookie handling, and the protocol handlers.
        You MUST supply an effectively unique handlerURL value for each of your applications.
        The value defaults to /Shibboleth.sso, and should be a relative path, with the SP computing
        a relative value based on the virtual host. Using handlerSSL="true", the default, will force
        the protocol to be https. You should also set cookieProps to "https" for SSL-only sites.
        Note that while we default checkAddress to "false", this has a negative impact on the
        security of your site. Stealing sessions via cookie theft is much easier with this disabled.
        -->
        <Sessions lifetime="28800" timeout="3600" relayState="ss:mem"
                  checkAddress="false" handlerSSL="false" cookieProps="http">

                  <SSO entityID="https://idp.example.com/sso-test/idp">
              SAML2 SAML1
            </SSO>

            <!-- SAML and local-only logout. -->
            <Logout>SAML2 Local</Logout>
            
            <!-- Extension service that generates "approximate" metadata based on SP configuration. -->
            <Handler type="MetadataGenerator" Location="/Metadata" signing="false"/>

            <!-- Status reporting service. -->
            <Handler type="Status" Location="/Status" acl="127.0.0.1 ::1"/>

            <!-- Session diagnostic service. -->
            <Handler type="Session" Location="/Session" showAttributeValues="false"/>

            <!-- JSON feed of discovery information. -->
            <Handler type="DiscoveryFeed" Location="/DiscoFeed"/>
        </Sessions>

        <!--
        Allows overriding of error template information/filenames. You can
        also add attributes with values that can be plugged into the templates.
        -->
        <Errors supportContact="admin@sp.example.org"
            helpLocation="/about.html"
            styleSheet="/shibboleth-sp/main.css"/>

        <!-- Example of locally maintained metadata. -->
        <MetadataProvider type="XML" validate="true" file="idp-metadata.xml"/>

        <!-- Map to extract attributes from SAML assertions. -->
        <AttributeExtractor type="XML" validate="true" reloadChanges="false" path="attribute-map.xml"/>

    </ApplicationDefaults>
    
    <!-- Policies that determine how to process and authenticate runtime messages. -->
    <SecurityPolicyProvider type="XML" validate="true" path="security-policy.xml"/>

    <!-- Low-level configuration about protocols and bindings available for use. -->
    <ProtocolProvider type="XML" validate="true" reloadChanges="false" path="protocols.xml"/>

</SPConfig>
```

`<RequestMapper>` の部分は
[Configuring Shibboleth's shibboleth2.xml to recognise secured paths](https://github.com/nginx-shib/nginx-http-shibboleth/blob/master/CONFIG.rst#configuring-shibboleths-shibboleth2xml-to-recognise-secured-paths)
の例から `<Path name="/secure2/shibboleth" />` の行を消して、ホスト名を `localhost` に変更しました。

後述のnginxの設定例では `/secure` と `/secure2` という2つのロケーションが出てくるのですが、今回は前者しか使っていないので、後者の設定は消しました。

`<Host>` タグの `name` 属性のホスト名を `localhost` にしているのは今回の検証では `localhost` で試したからで、実際の運用ではSPのホスト名（この記事の例では `sp.example.org` ）を設定してください。

## nginxの設定

nginxの自作rpmでは
[nginx-shib/nginx-http-shibboleth: Shibboleth auth request module for nginx](https://github.com/nginx-shib/nginx-http-shibboleth)
を動的モジュールとしてビルドしたので、 `/etc/nginx/nginx.conf` の `events` の行の前に以下のようにモジュール読み込み設定が必要です。

```text
load_module modules/ngx_http_shibboleth_module.so;
```

nginxのserver設定は
[Configure Nginx](https://github.com/nginx-shib/nginx-http-shibboleth/blob/master/CONFIG.rst#configure-nginx)
から `location /secure2` を除いて `server_name` を `localhost` にしたものを使いました。

`/etc/nginx/conf.d/ssl.conf`

```text
server {
    listen 443 ssl;
    server_name localhost;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 5m;
    ssl_ciphers AESGCM:HIGH:!EXP:!RC4:!LOW:!aNULL;
    ssl_prefer_server_ciphers on;
    ssl_protocols TLSv1.2;

    ssl_certificate /etc/pki/tls/certs/localhost.crt;
    ssl_certificate_key /etc/pki/tls/private/localhost.key;

    #FastCGI authorizer for Auth Request module
    location = /shibauthorizer {
        internal;
        include fastcgi_params;
        fastcgi_pass unix:/opt/shibboleth/shibauthorizer.sock;
    }

    #FastCGI responder
    location /Shibboleth.sso {
        include fastcgi_params;
        fastcgi_pass unix:/opt/shibboleth/shibresponder.sock;
    }

    #Resources for the Shibboleth error pages. This can be customised.
    location /shibboleth-sp {
        alias /usr/share/shibboleth/;
    }

    #A secured location.  Here all incoming requests query the
    #FastCGI authorizer.  Watch out for performance issues and spoofing.
    location /secure {
        include shib_clear_headers;
        #Add your attributes here. They get introduced as headers
        #by the FastCGI authorizer so we must prevent spoofing.
        more_clear_input_headers 'displayName' 'mail' 'persistent-id';
        shib_request /shibauthorizer;
        shib_request_use_headers on;
        proxy_pass http://localhost:8080;
    }
}
```

#### httpsの自己証明書作成

以下のようにhttpsの自己証明書を生成しました。

```console
openssl req -new -newkey rsa:2048 -sha1 -x509 -nodes \
    -set_serial 1 \
    -days 365 \
    -subj "/C=JP/ST=Osaka/L=Osaka City/CN=localhost" \
    -out /etc/pki/tls/certs/localhost.crt \
    -keyout /etc/pki/tls/private/localhost.key
```

#### upstreamの設定

上記で `proxy_pass` で指定している http://localhost:8080 では実運用ではSAML認証した状態で使用するアプリケーションを動かすのですが、今回の検証は以下のような設定でnginxで静的なページを表示するだけにしました。

`/etc/nginx/conf.d/upstream.conf`

```text
server {
    listen       8080;
    server_name  localhost;

    access_log /var/log/nginx/upstream.access.log main;
    root /var/www/html-upstream;
}
```

以下のコマンドを実行して `/secure` のURLパスに対応するファイルを作成しておきます。

```console
mkdir -p /var/www/html-upstream/secure
echo 'secure index page' | sudo tee /var/www/html-upstream/secure/index.html
```

# サーバ再起動

以上で設定ができたので、以下のコマンドで関連するサーバを再起動します。

```console
systemctl restart shibd
systemctl restart shibauthorizer
systemctl restart shibrsponder
systemctl restart nginx
```

# 動作確認

これでブラウザで `https://localhost/secure` にアクセスします。
自己証明書なので警告が出ますが無視して進むと
`https://idp.example.com/sso-test/idp/sso_redirect?SAMLRequest=xxx…(略)…&RelayState=…(略)…` といったURLにリダイレクトされます。

## SAMLRequestの確認

ChromeのURL欄からコピーしたSAMLRequestの値は以下のようにしてデコードできました。

```console
python3 -c 'import sys, urllib.parse as ul, base64, zlib; print(zlib.decompress(base64.b64decode(ul.unquote_plus(sys.argv[1])), -15).decode("utf-8"))' 'ブラウザのURL欄からコピーしたSAMLRequestの値'
```

上記のコードはURLデコードを行ってから下記の [python-saml/utils.py](https://github.com/onelogin/python-saml/blob/e2da620897fb78eb2095abe4f37bde87832c7d1d/src/onelogin/saml2/utils.py#L92-L113) の `decode_base64_and_inflate` の処理を行うようにしたものです。

```python
@staticmethod
def decode_base64_and_inflate(value):
    """
    base64 decodes and then inflates according to RFC1951
    :param value: a deflated and encoded string
    :type value: string
    :returns: the string after decoding and inflating
    :rtype: string
    """

    return zlib.decompress(base64.b64decode(value), -15).decode('utf-8')

@staticmethod
def deflate_and_base64_encode(value):
    """
    Deflates and then base64 encodes a string
    :param value: The string to deflate and encode
    :type value: string
    :returns: The deflated and encoded string
    :rtype: string
    """
    return base64.b64encode(zlib.compress(value.encode('utf-8'))[2:-4])
```

デコードした結果の例を以下に示します（なお、実際はIdPとSPのエンティティIDとURLはこの記事と違う値で動作確認していて、以下に貼っているのはデコードした後それらの値を置換しています）。

```xml
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" AssertionConsumerServiceURL="https://localhost/Shibboleth.sso/SAML2/POST" Destination="https://idp.example.com/sso-test/idp/sso_redirect" ID="_fbd5e55b3590bf5c947ce2dd3d9f0053" IssueInstant="2018-07-04T01:53:41Z" ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Version="2.0"><saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">https://sp.example.org/sso</saml:Issuer><samlp:NameIDPolicy AllowCreate="1"/></samlp:AuthnRequest>
```

## SAMLResponseの確認

今回検証したIdPでは二段階認証を行うようになっています。Chromeの開発ツールを開いた状態で二段階目の入力を行うと `https://localhost/Shibboleth.sso/SAML2/POST` にPOSTでリクエストを送っていて FormData に `SAMLResponse` と `RelayState` という項目が含まれていました。

SAMLResponseは以下のようにしてBase64デコードすればXMLを確認できました。

```console
echo 'ブラウザからコピーしたSAMLResponseの値' | base64 --decode
```

デコードしたXMLを機密情報を伏せた上で以下に示します。

```xml
<?xml version="1.0"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_EXAMPLE_SSO_f1756be7-771c-4330-9bd2-568501fdc194" Version="2.0" IssueInstant="2018-07-04T03:22:14Z" Destination="https://localhost/Shibboleth.sso/SAML2/POST" InResponseTo="_fbd5e55b3590bf5c947ce2dd3d9f0053">
  <saml:Issuer>https://idp.example.com/sso-test/idp</saml:Issuer>
  <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
    <ds:SignedInfo>
      <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
      <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>
      <ds:Reference URI="#_EXAMPLE_SSO_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx">
        <ds:Transforms>
          <ds:Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
          <ds:Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        </ds:Transforms>
        <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>
        <ds:DigestValue>xxxxxxxxxxxxxxxxxxxxxxxxxxx=</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxx…(略)…xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxx==</ds:SignatureValue>
    <ds:KeyInfo>
      <ds:X509Data>
        
        
        
      <ds:X509Certificate>xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxx…(略)…xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
xxxxxxxxxxxxxxxxxxxxxx==</ds:X509Certificate>
<ds:X509SubjectName>CN=localhost:5000,OU=sso-test,O=xxxxxxxxxxxxxxxxxxxx,L=Osaka,ST=Osaka,C=JP</ds:X509SubjectName>
<ds:X509IssuerSerial>
<ds:X509IssuerName>CN=localhost:5000,OU=sso-test,O=xxxxxxxxxxxxxxxxxxxx,L=Osaka,ST=Osaka,C=JP</ds:X509IssuerName>
<ds:X509SerialNumber>99999999999999999999</ds:X509SerialNumber>
</ds:X509IssuerSerial>
</ds:X509Data>
    </ds:KeyInfo>
  </ds:Signature>
  <samlp:Status>
    <samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>
  </samlp:Status>
  <saml:Assertion xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" ID="_a_fbd5e55b3590bf5c947ce2dd3d9f0053" Version="2.0" IssueInstant="2018-07-04T03:22:14Z">
    <saml:Issuer>https://idp.example.com/sso-test/idp</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:persistent" NameQualifier="idp.example.com" SPNameQualifier="https://sp.example.org/sso">user1</saml:NameID>
      <saml:SubjectConfirmation Method="urn:oasis:names:tc:SAML:2.0:cm:bearer">
        <saml:SubjectConfirmationData InResponseTo="_fbd5e55b3590bf5c947ce2dd3d9f0053" NotOnOrAfter="2018-07-04T03:27:14Z" Recipient="https://localhost/Shibboleth.sso/SAML2/POST"/>
      </saml:SubjectConfirmation>
    </saml:Subject>
    <saml:Conditions NotBefore="2018-07-04T03:17:14Z" NotOnOrAfter="2018-07-04T03:27:14Z">
      <saml:AudienceRestriction>
        <saml:Audience>https://sp.example.org/sso</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AuthnStatement AuthnInstant="2018-07-04T03:22:14Z" SessionNotOnOrAfter="2018-07-04T04:22:14Z" SessionIndex="_s_fbd5e55b3590bf5c947ce2dd3d9f0053">
      <saml:AuthnContext>
        <saml:AuthnContextClassRef>urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport</saml:AuthnContextClassRef>
      </saml:AuthnContext>
    </saml:AuthnStatement>
    <saml:AttributeStatement>
      
      <saml:Attribute Name="mail" NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified">
        <saml:AttributeValue xsi:type="xs:anyType">user1@example.net</saml:AttributeValue>
      </saml:Attribute>
      
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>
```

`<saml:Subject>` の `<saml:NameID>` の値 `user1` がログインしたときのユーザIDです。
`AttributeStatement` の中に `<saml:Attribute Name="mail">` というタグがあり、その子供の `<saml:AttributeValue>` の値にログインユーザのメールアドレス `user1@example.net` が入っています。

また `https://localhost/Shibboleth.sso/SAML2/POST` のレスポンスヘッダには以下のような `Set-Cookie` ヘッダが含まれていました。

```text
Set-Cookie: _shibsession_64656661756c7468747470733a2f2f61706930312e6465762e776562616363656c2e6a702f61646d696e2f73736f=_d43354cfc784c22b046e22bf1c1d176f; path=/; HttpOnly
```

この後 `https://localhost/secure` →  `https://localhost/secure/` とリダイレクトされて、上記で作成した /var/www/html-upstream/secure/index.html の内容である「secure index page」が無事表示されました。

## 認証後にバックエンドに送られるリクエストヘッダ

また、ポート8080で動かしているバックエンド（に見立てたnginx）へのリクエストヘッダに何が来るのかを確認するため、以下のコマンドを動かした状態で認証を実行しました（ヘッダ名がわかっていればnginxの設定を変えてログ出力すればよいのですが、どういうヘッダが来るかがわからないのでtcpdumpを使いました）。

```console
tcpdump -X -i lo port 8080
```

.. code-block:: text

    …(略)…
    06:41:20.135840 IP localhost.48704 > localhost.webcache: Flags [P.], seq 1:1338, ack 1, win 342, options [nop,nop,TS val 763708778 ecr 763708778], length 1337: HTTP: GET /secure/ HTTP/1.0
            0x0000:  4500 056d 2757 4000 4006 1032 7f00 0001  E..m'W@.@..2....
            0x0010:  7f00 0001 be40 1f90 71ea bb02 c998 0fbf  .....@..q.......
            0x0020:  8018 0156 0362 0000 0101 080a 2d85 456a  ...V.b......-.Ej
            0x0030:  2d85 456a 4745 5420 2f73 6563 7572 652f  -.EjGET./secure/
            0x0040:  2048 5454 502f 312e 300d 0a48 6f73 743a  .HTTP/1.0..Host:
            0x0050:  2031 3237 2e30 2e30 2e31 3a38 3038 300d  .127.0.0.1:8080.
            0x0060:  0a43 6f6e 6e65 6374 696f 6e3a 2063 6c6f  .Connection:.clo
    …(略)…

Shibboleth関連のリクエストヘッダを抜き出して整形したものを以下に示します（日時が前後しているのは上で書いたのより前に動作確認したときのログをコピペしているためです）。

```text
Cookie: _shibsession_64656661756c7468747470733a2f2f61706930312e6465762e776562616363656c2e6a702f61646d696e2f73736f=_d43354cfc784c22b046e22bf1c1d176f
AUTH_TYPE: shibboleth
Shib-Application-ID: default
Shib-Authentication-Instant: 2018-06-29T06:41:19Z
Shib-Authentication-Method: urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
Shib-AuthnContext-Class: urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport
Shib-Handler: http://localhost/Shibboleth.sso
Shib-Identity-Provider: https://idp.example.com/sso-test/idp
Shib-Session-ID: _d43354cfc784c22b046e22bf1c1d176f
Shib-Session-Index: _s_f5f10d110e4c22f0514443f82971c730
mail: user1@example.net
```

上記の `Set-Cookie` で設定されたクッキーのと同じ値が `Shib-Session-ID` というリクエストヘッダに付与されています。
また、 `mail` というリクエストヘッダにログインユーザのメールアドレスが設定されています。

上記のnginxの設定の `location /secure` で `include shib_clear_headers;` と指定して読み込んでいる `/etc/nginx/shib_clear_headers` を確認すると以下のようになっていました（コメントは省略）。

```text
more_clear_input_headers
    Auth-Type
    Shib-Application-Id
    Shib-Authentication-Instant
    Shib-Authentication-Method
    Shib-Authncontext-Class
    Shib-Identity-Provider
    Shib-Session-Id
    Shib-Session-Index
    Remote-User;
```

ということで攻撃の意図を持ってリクエスト時にこれらのリクエストヘッダを指定して上書きしようとしても、一旦クリアしてから Shibboleth が設定するので問題ないです。

`mail` のリクエストヘッダについても以下の行で一旦クリアしているのでこちらも問題ないです。

```text
more_clear_input_headers 'displayName' 'mail' 'persistent-id';
```

## ログアウトの動作確認

今回検証した構成ではIdPにログアウト用のエンドポイント(URL)は無いので、
_shibsession_xxxx
のクッキーを削除することでログアウトとするということにします。

もしこのクッキー名に紐付けてバックエンドのサーバサイドでセッションデータを保持する場合は、そちらの削除も行うようにします。

今回はChromeでクッキーの削除を行いました。

「設定」→「詳細設定」→「コンテンツの設定」→「Cookie」→「すべての Cookie とサイトデータを表示」と進み、「Cookieを検索」の入力欄に「localhost」と入力して絞り込んで、クッキーを削除します。

本来は _shibsession_xxxx のクッキーだけを削除したかったのですが、クッキーの名前が長すぎて削除の☓ボタンが枠内に表示されず押せないため、「localhost」のクッキー全てをまとめて消すことで回避しました。

何度も消す場合は「すべての Cookie とサイトデータ」のページを開いたままにしておいて、再度ログインした後に「すべての Cookie とサイトデータ」の左の「←」をクリックして「Cookie」のページに戻り、再度「すべての Cookie とサイトデータを表示」を押して「すべての Cookie とサイトデータ」に戻ると「localhost」でのフィルタリングが維持されているので、あとは消すだけでOKでした。

システム化する場合は例えば
[openresty/lua-nginx-module](https://github.com/openresty/lua-nginx-module)
と
[cloudflare/lua-resty-cookie](https://github.com/cloudflare/lua-resty-cookie)
を使って、以下のようなコードを書けば良いです。

```text
lua_package_path "/usr/lib/nginx/lua/?.lua;;";

server {
    …(略)…

    location /signout {
        content_by_lua_block {
            ngx.header.content_type = 'text/plain';

            local ck = require "resty.cookie"
            local cookie, err = ck:new()
            if not cookie then
                ngx.log(ngx.ERR, err)
                return
            end
            local fields, err = cookie:get_all()
            if fields then
                local prefix = "_shibsession_"
                for k, v in pairs(fields) do
                    if string.sub(k, 1, #prefix) == prefix then
                        local ok, err = cookie:set({
                            key = k, value = "", path = "/", httponly = true,
                            expires = "Thu Jan 01 1970 00:00:00 GMT"
                        })
                        if not ok then
                            ngx.log(ngx.ERR, err)
                            return
                        end
                    end
                end
            else
                if err ~= "no cookie found in the current request" then
                    ngx.log(ngx.ERR, err)
                    return
                end
            end

            ngx.redirect('/')
        }
    }

    …(略)…
}
```

私のnginxのrpmでは `/usr/lib/nginx/lua/resty/cookie.lua` というパスに lua-resty-cookie のluaファイルを置いているので `lua_package_path "/usr/lib/nginx/lua/?.lua;;";` と `require "resty.cookie"` でアクセスできます。

この例では名前が `_shibsession_` で始まるクッキーの有効期限を過去の日付にしてブラウザがクッキーを削除するようにしています。

既にサインアウト済みの場合とサインアウトした後に `/` にリダイレクトするようにしています。
