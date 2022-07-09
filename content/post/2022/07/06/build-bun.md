---
title: "Bunをビルドしてみる"
date: 2022-07-06T20:51:04+09:00
---

## README の手順でビルドしてみるとエラー

```
root@bun-dev:~/bun# npm install -g @vscode/dev-container-cli
npm notice
npm notice New minor version of npm available! 8.12.1 -> 8.13.2
npm notice Changelog: https://github.com/npm/cli/releases/tag/v8.13.2
npm notice Run npm install -g npm@8.13.2 to update!
npm notice
npm ERR! code 127
npm ERR! path /root/.nvm/versions/node/v18.4.0/lib/node_modules/@vscode/dev-container-cli/node_modules/node-pty
npm ERR! command failed
npm ERR! command sh -c node scripts/install.js
npm ERR! sh: 1: node: Permission denied

npm ERR! A complete log of this run can be found in:
npm ERR!     /root/.npm/_logs/2022-07-06T12_23_46_404Z-debug-0.log
root@bun-dev:~/bun# node --version
v18.4.0
root@bun-dev:~/bun# less /root/.npm/_logs/2022-07-06T12_23_46_404Z-debug-0.log
root@bun-dev:~/bun# npm install -g npm@8.13.2

changed 24 packages, and audited 202 packages in 2s

11 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
```

* https://discord.com/channels/876711213126520882/887787428973281300/983932555617259540
* https://discord.com/channels/876711213126520882/887787428973281300/983948200195022908


```
nvm_repo_url=https://github.com/nvm-sh/nvm
nvm_version=$(curl -sS -w '%{redirect_url}' -o /dev/null "$nvm_repo_url/releases/latest" | sed 's|.*/tag/||')
curl -sSo- https://raw.githubusercontent.com/nvm-sh/nvm/$nvm_version/install.sh | bash
exec $SHELL -l
nvm install 18
```

```
git clone https://github.com/Jarred-Sumner/bun
cd bun
```

```
npm install -g @vscode/dev-container-cli
```

```
root@bun-dev:~/bun# npm install -g @vscode/dev-container-cli
npm notice
npm notice New minor version of npm available! 8.12.1 -> 8.13.2
npm notice Changelog: https://github.com/npm/cli/releases/tag/v8.13.2
npm notice Run npm install -g npm@8.13.2 to update!
npm notice
npm ERR! code 127
npm ERR! path /root/.nvm/versions/node/v18.4.0/lib/node_modules/@vscode/dev-container-cli/node_modules/node-pty
npm ERR! command failed
npm ERR! command sh -c node scripts/install.js
npm ERR! sh: 1: node: Permission denied

npm ERR! A complete log of this run can be found in:
npm ERR!     /root/.npm/_logs/2022-07-06T12_23_46_404Z-debug-0.log
root@bun-dev:~/bun# node --version
v18.4.0
root@bun-dev:~/bun# less /root/.npm/_logs/2022-07-06T12_23_46_404Z-debug-0.log
root@bun-dev:~/bun# npm install -g npm@8.13.2

changed 24 packages, and audited 202 packages in 2s

11 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
```

local/bun-base-with-zig-and-webkit

DOCKER_BUILDARCH=amd64
BUILDKIT=1 docker build -f Dockerfile.base --build-arg GITHUB_WORKSPACE=/build --platform=linux/${DOCKER_BUILDARCH} --tag local/bun-base --target bun-base .
BUILDKIT=1 docker build -f Dockerfile.base --build-arg GITHUB_WORKSPACE=/build --platform=linux/${DOCKER_BUILDARCH} --tag local/bun-base-with-zig-and-webkit --target bun-base-with-zig-and-webkit .


make devcontainer

```
clang: error: no such file or directory: '/build/bun-deps/libbacktrace.a'
clang: error: no such file or directory: '/build/bun-deps/libuwsockets.o'
clang: error: no such file or directory: '/build/bun-deps/sqlite3.o'
make: *** [Makefile:719: jsc-bindings-headers] Error 1
```

devcontainer: clone-submodules mimalloc zlib libarchive boringssl picohttp identifier-cache node-fallbacks jsc-bindings-headers api analytics bun_error fallback_decoder jsc-bindings-mac dev runtime_js_dev libarchive
devcontainer: clone-submodules mimalloc zlib libarchive boringssl picohttp identifier-cache node-fallbacks jsc-bindings-headers api analytics bun_error fallback_decoder jsc-bindings-mac dev runtime_js_dev libarchive libbacktrace lolhtml usockets uws base64 tinycc

make libbacktrace
make uws
make sqlite
make devcontainer

```
/build/zig/zig translate-c src/bun.js/bindings/headers.h > src/bun.js/bindings/headers.zig
/usr/bin/node misctools/headers-cleaner.js
Writing to /build/bun/src/bun.js/bindings/headers.zig
/build/bun/misctools/headers-cleaner.js:33
input = input.replaceAll("*WebCore__", "*bindings.");
              ^

TypeError: input.replaceAll is not a function
    at Object.<anonymous> (/build/bun/misctools/headers-cleaner.js:33:15)
    at Module._compile (internal/modules/cjs/loader.js:778:30)
    at Object.Module._extensions..js (internal/modules/cjs/loader.js:789:10)
    at Module.load (internal/modules/cjs/loader.js:653:32)
    at tryModuleLoad (internal/modules/cjs/loader.js:593:12)
    at Function.Module._load (internal/modules/cjs/loader.js:585:3)
    at Function.Module.runMain (internal/modules/cjs/loader.js:831:12)
    at startup (internal/bootstrap/node.js:283:19)
    at bootstrapNodeJSCore (internal/bootstrap/node.js:623:3)
make: *** [Makefile:722: jsc-bindings-headers] Error 1
```

```
root@focal:~# node --version
v10.19.0
root@focal:~# echo "console.log(''.replace)" | node
[Function: replace]
root@focal:~# echo "console.log(''.replaceAll)" | node
undefined
```

```
root@focal:~# dpkg -l nodejs
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name           Version               Architecture Description
+++-==============-=====================-============-==================================================
ii  nodejs         10.19.0~dfsg-3ubuntu1 amd64        evented I/O for V8 javascript - runtime executable
```

 libarchive libbacktrace lolhtml usockets uws base64 tinycc
