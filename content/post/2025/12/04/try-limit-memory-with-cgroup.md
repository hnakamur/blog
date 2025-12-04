---
title: "Linuxのcgroupでメモリ制限をかけてOOM Killerが動くのを試してみた"
date: 2025-12-04T21:23:50+09:00
---

## はじめに

Linuxのcgroupでメモリ制限をかけてOOM (Out Of Memory) Killerでプロセスが強制終了されるのを試してみたメモです。

## テストプログラム

100Mのバイト列を最大2万個メモリ割り当てしようとするプログラムです。

```go
package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"runtime/metrics"
	"strconv"
	"strings"
)

const cgroupDir = "/sys/fs/cgroup/gomemlimitexperiment"

const filenameMemoryMax = "memory.max"
const filenameMemorySwapMax = "memory.swap.max"
const filenameCgroupProcs = "cgroup.procs"

func setCgroupValue(name, value string) error {
	if err := os.MkdirAll(cgroupDir, 0o700); err != nil {
		return err
	}
	filename := filepath.Join(cgroupDir, name)
	if err := os.WriteFile(filename, []byte(value), 0o600); err != nil {
		return err
	}
	return nil
}

func getCgroupValue(name string) (string, error) {
	filename := filepath.Join(cgroupDir, name)
	content, err := os.ReadFile(filename)
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(content)), nil
}

func main() {
	usesCgroup := flag.Bool("c", false, "use cgroup to limit memory")
	memoryLimit := flag.String("m", "100M", "memory limit in bytes")
	swapMax := flag.String("s", "max", "cgroup swap max bytes")
	arraySize := flag.Uint("a", 100*1024*1024, "array byte length")
	arrayCount := flag.Uint("n", 20000, "array count")
	flag.Parse()

	c := readRuntimeMemConfig()
	fmt.Printf("gcPercent:%d\tmemoryLimit:%d\n", c.GCPercent, c.MemoryLimit)

	if *usesCgroup {
		if err := setCgroupValue(filenameMemoryMax, *memoryLimit); err != nil {
			log.Fatal(err)
		}
		if err := setCgroupValue(filenameMemorySwapMax, *swapMax); err != nil {
			log.Fatal(err)
		}
		if err := setCgroupValue(filenameCgroupProcs,
			strconv.Itoa(os.Getpid())); err != nil {
			log.Fatal(err)
		}

		gotMemMax, err := getCgroupValue(filenameMemoryMax)
		if err != nil {
			log.Fatal(err)
		}
		gotSwapMax, err := getCgroupValue(filenameMemorySwapMax)
		if err != nil {
			log.Fatal(err)
		}
		fmt.Printf("memMax:%s\tswapMax:%s\n", gotMemMax, gotSwapMax)
	}

	arrays := make([][]byte, *arrayCount)
	for i := range *arrayCount {
		p := make([]byte, *arraySize)
		fmt.Printf("\ri=%d ", i)
		arrays = append(arrays, p)
	}
}

type RuntimeMemConfig struct {
	GCPercent   uint64
	MemoryLimit uint64
}

func readRuntimeMemConfig() *RuntimeMemConfig {
	sample := []metrics.Sample{
		{Name: "/gc/gogc:percent"},
		{Name: "/gc/gomemlimit:bytes"},
	}
	metrics.Read(sample)
	for _, metric := range sample {
		if metric.Value.Kind() == metrics.KindBad {
			panic(fmt.Sprintf("metric %q no longer supported", metric.Name))
		}
	}

	return &RuntimeMemConfig{
		GCPercent:   sample[0].Value.Uint64(),
		MemoryLimit: sample[1].Value.Uint64(),
	}
}
```

### ビルド手順
```
go mod init gomemlimitexperiment
go build -trimpath
```

## 検証結果

cgroupなしだと最後まで実行されました。

```
$ ./gomemlimitexperiment
gcPercent:100   memoryLimit:9223372036854775807
i=19999
```

`memory.max`を`100M`、`memory.swap.max`を`max`で試した結果。
```
$ sudo ./gomemlimitexperiment -c
gcPercent:100   memoryLimit:9223372036854775807
memMax:104857600        swapMax:max
i=18870 Killed
```

`memory.max`を`100M`、`memory.swap.max`を`20M`で試した結果。
```
$ sudo ./gomemlimitexperiment -c -s 20M
gcPercent:100   memoryLimit:9223372036854775807
memMax:104857600        swapMax:20971520
i=1022 Killed
```

`memory.max`を`100M`、`memory.swap.max`を`10M`で試した結果。
```
$ sudo ./gomemlimitexperiment -c -s 10M
gcPercent:100   memoryLimit:9223372036854775807
memMax:104857600        swapMax:10485760
i=943 Killed
```

`memory.max`を`100M`、`memory.swap.max`を`0`で試した結果。
```
$ sudo ./gomemlimitexperiment -c -s 0
gcPercent:100   memoryLimit:9223372036854775807
memMax:104857600        swapMax:0
i=856 Killed
```

今回のケースでは`memory.swap.max`が小さくなるにつれて、より早くOOM Killerが発動することがわかりました。

## 余談：GOGCとGOMEMLIMIT環境変数で設定反映した状態の確認

実は上記の実験用コードの`RuntimeMemConfig`と`readRuntimeMemConfig`はcgroupでメモリ制限する話とは無関係です。
GOGCとGOMEMLIMIT環境変数で設定した値を確認する方法がふと気になって調べたので、今後使うかもということで含めてます。

GOGCとGOMEMLIMIT環境変数についてはGo公式ブログ記事[A Guide to the Go Garbage Collector](https://go.dev/doc/gc-guide)を参照してください。

環境変数の他にmetrics/debugパッケージの[SetGCPercent](https://pkg.go.dev/runtime/debug#SetGCPercent)と[SetMemoryLimit](https://pkg.go.dev/runtime/debug#SetMemoryLimit)関数でも設定できるということで、反映先の値を見る方法が気になったという経緯でした。
