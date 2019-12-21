+++
title="go-whisperをコードリーディングしてみた"
date = "2017-04-29T17:05:00+09:00"
tags = ["go", "go-carbon"]
categories = ["blog"]
+++


## はじめに

[go-carbonのTCPレシーバについてコードリーディングしてみた](/blog/2017/04/29/go-carbon-tcp-receiver-code-reading/) の続きです。

go-whisperのレポジトリは
[lomik/go-whisper: A Go port of Graphite's Whisper timeseries database](https://github.com/lomik/go-whisper/)
で、
対象のコミットは
https://github.com/lomik/go-whisper/tree/6de93631b9853148a7e1a659f7805a89451368bf
です。

## 既存のwhisperファイルを開く

`whisper.Open` の実装は以下の通りです。

[whisper.go#L260-L322](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L260-L322)

```go {linenos=table,linenostart=260}
/*
  Open an existing Whisper database and read it's header
*/
func Open(path string) (whisper *Whisper, err error) {
    file, err := os.OpenFile(path, os.O_RDWR, 0666)
    if err != nil {
        return
    }

    defer func() {
        if err != nil {
            whisper = nil
            file.Close()
        }
    }()

    whisper = new(Whisper)
    whisper.file = file

    offset := 0

    // read the metadata
    b := make([]byte, MetadataSize)
    readed, err := file.Read(b)

    if err != nil {
        err = fmt.Errorf("Unable to read header: %s", err.Error())
        return
    }
    if readed != MetadataSize {
        err = fmt.Errorf("Unable to read header: EOF")
        return
    }

    a := unpackInt(b[offset : offset+IntSize])
    if a > 1024 { // support very old format. File starts with lastUpdate and has only average aggregation method
        whisper.aggregationMethod = Average
    } else {
        whisper.aggregationMethod = AggregationMethod(a)
    }
    offset += IntSize
    whisper.maxRetention = unpackInt(b[offset : offset+IntSize])
    offset += IntSize
    whisper.xFilesFactor = unpackFloat32(b[offset : offset+FloatSize])
    offset += FloatSize
    archiveCount := unpackInt(b[offset : offset+IntSize])
    offset += IntSize

    // read the archive info
    b = make([]byte, ArchiveInfoSize)

    whisper.archives = make([]*archiveInfo, 0)
    for i := 0; i < archiveCount; i++ {
        readed, err = file.Read(b)
        if err != nil || readed != ArchiveInfoSize {
            err = fmt.Errorf("Unable to read archive %d metadata", i)
            return
        }
        whisper.archives = append(whisper.archives, unpackArchiveInfo(b))
    }

    return whisper, nil
}
```

## Whisper構造体

`Whisper` 構造体の定義です。

[whisper.go#L128-L139](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L128-L139)

```go {linenos=table,linenostart=128}
/*
    Represents a Whisper database file.
*/
type Whisper struct {
    file *os.File

    // Metadata
    aggregationMethod AggregationMethod
    maxRetention      int
    xFilesFactor      float32
    archives          []*archiveInfo
}
```

`AggregationMethod` の型と定数の定義です。

[whisper.go#L37-L45](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L37-L45)

```go {linenos=table,linenostart=37}
type AggregationMethod int

const (
    Average AggregationMethod = iota + 1
    Sum
    Last
    Max
    Min
)
```

`archiveInfo` 構造体の定義です。

[go-whisper/whisper.go#L840-L849](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L840-L849)

```go {linenos=table,linenostart=840}
/*
  Describes a time series in a file.
  The only addition this type has over a Retention is the offset at which it exists within the
  whisper file.
*/
type archiveInfo struct {
    Retention
    offset int
}
```

`Retention` 構造体の定義です。

[whisper.go#L790-L799](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L790-L799)

```go {linenos=table,linenostart=790}
/*
  A retention level.
  Retention levels describe a given archive in the database. How detailed it is and how far back
  it records.
*/
type Retention struct {
    secondsPerPoint int
    numberOfPoints  int
}
```

## UpdateManyメソッド

[whisper.go#L464-L496](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L464-L496)

```go {linenos=table,linenostart=464}
func (whisper *Whisper) UpdateMany(points []*TimeSeriesPoint) (err error) {
    // recover panics and return as error
    defer func() {
        if e := recover(); e != nil {
            err = errors.New(e.(string))
        }
    }()

    // sort the points, newest first
    reversePoints(points)
    sort.Stable(timeSeriesPointsNewestFirst{points})

    now := int(time.Now().Unix()) // TODO: danger of 2030 something overflow

    var currentPoints []*TimeSeriesPoint
    for _, archive := range whisper.archives {
        currentPoints, points = extractPoints(points, now, archive.MaxRetention())
        if len(currentPoints) == 0 {
            continue
        }
        // reverse currentPoints
        reversePoints(currentPoints)
        err = whisper.archiveUpdateMany(archive, currentPoints)
        if err != nil {
            return
        }

        if len(points) == 0 { // nothing left to do
            break
        }
    }
    return
}
```

`TimeSeriesPoint` 構造体の定義です。

[whisper.go#L907-L910](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L907-L910)

```go {linenos=table,linenostart=907}
type TimeSeriesPoint struct {
    Time  int
    Value float64
}
```

`reversePoints` 関数の実装です。渡されたスライスのバックストアを上書きして逆順にしています。

[SliceTricks · golang/go Wiki](https://github.com/golang/go/wiki/SliceTricks#reversing)
の
[Reversing](https://github.com/golang/go/wiki/SliceTricks#reversing)
で書かれているのとほぼ同じ手法です。

[whisper.go#L455-L462](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L455-L462)

```go {linenos=table,linenostart=455}
func reversePoints(points []*TimeSeriesPoint) {
    size := len(points)
    end := size / 2

    for i := 0; i < end; i++ {
        points[i], points[size-i-1] = points[size-i-1], points[i]
    }
}
```

`timeSeriesPointsNewestFirst` は名前の通りポイントを時刻の新しい順に並べるための構造体です。

[whisper.go#L912-L928](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L912-L928)

```go {linenos=table,linenostart=912}
type timeSeriesPoints []*TimeSeriesPoint

func (p timeSeriesPoints) Len() int {
    return len(p)
}

func (p timeSeriesPoints) Swap(i, j int) {
    p[i], p[j] = p[j], p[i]
}

type timeSeriesPointsNewestFirst struct {
    timeSeriesPoints
}

func (p timeSeriesPointsNewestFirst) Less(i, j int) bool {
    return p.timeSeriesPoints[i].Time > p.timeSeriesPoints[j].Time
}
```

[whisper.go#L552-L564](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L552-L564)

```go {linenos=table,linenostart=552}
func extractPoints(points []*TimeSeriesPoint, now int, maxRetention int) (currentPoints []*TimeSeriesPoint, remainingPoints []*TimeSeriesPoint) {
    maxAge := now - maxRetention
    for i, point := range points {
        if point.Time < maxAge {
            if i > 0 {
                return points[:i-1], points[i-1:]
            } else {
                return []*TimeSeriesPoint{}, points
            }
        }
    }
    return points, remainingPoints
}
```

`Whisper` の `archiveUpdateMany` メソッドの実装です。

[whisper.go#L498-L550](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L498-L550)

```go {linenos=table,linenostart=498}
func (whisper *Whisper) archiveUpdateMany(archive *archiveInfo, points []*TimeSeriesPoint) error {
    alignedPoints := alignPoints(archive, points)
    intervals, packedBlocks := packSequences(archive, alignedPoints)

    baseInterval := whisper.getBaseInterval(archive)
    if baseInterval == 0 {
        baseInterval = intervals[0]
    }

    for i := range intervals {
        myOffset := archive.PointOffset(baseInterval, intervals[i])
        bytesBeyond := int(myOffset-archive.End()) + len(packedBlocks[i])
        if bytesBeyond > 0 {
            pos := len(packedBlocks[i]) - bytesBeyond
            err := whisper.fileWriteAt(packedBlocks[i][:pos], myOffset)
            if err != nil {
                return err
            }
            err = whisper.fileWriteAt(packedBlocks[i][pos:], archive.Offset())
            if err != nil {
                return err
            }
        } else {
            err := whisper.fileWriteAt(packedBlocks[i], myOffset)
            if err != nil {
                return err
            }
        }
    }

    higher := archive
    lowerArchives := whisper.lowerArchives(archive)

    for _, lower := range lowerArchives {
        seen := make(map[int]bool)
        propagateFurther := false
        for _, point := range alignedPoints {
            interval := point.interval - mod(point.interval, lower.secondsPerPoint)
            if !seen[interval] {
                if propagated, err := whisper.propagate(interval, higher, lower); err != nil {
                    panic("Failed to propagate")
                } else if propagated {
                    propagateFurther = true
                }
            }
        }
        if !propagateFurther {
            break
        }
        higher = lower
    }
    return nil
}
```

[whisper.go#L566-L579](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L566-L579)

```go {linenos=table,linenostart=566}
func alignPoints(archive *archiveInfo, points []*TimeSeriesPoint) []dataPoint {
    alignedPoints := make([]dataPoint, 0, len(points))
    positions := make(map[int]int)
    for _, point := range points {
        dPoint := dataPoint{point.Time - mod(point.Time, archive.secondsPerPoint), point.Value}
        if p, ok := positions[dPoint.interval]; ok {
            alignedPoints[p] = dPoint
        } else {
            alignedPoints = append(alignedPoints, dPoint)
            positions[dPoint.interval] = len(alignedPoints) - 1
        }
    }
    return alignedPoints
}
```

[whisper.go#L930-L933](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L930-L933)

```go {linenos=table,linenostart=930}
type dataPoint struct {
    interval int
    value    float64
}
```

[whisper.go#L1021-L1027](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L1021-L1027)

```go {linenos=table,linenostart=1021}
/*
    Implementation of modulo that works like Python
    Thanks @timmow for this
*/
func mod(a, b int) int {
    return a - (b * int(math.Floor(float64(a)/float64(b))))
}
```

[whisper.go#L581-L593](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L581-L593)

```go {linenos=table,linenostart=581}
func packSequences(archive *archiveInfo, points []dataPoint) (intervals []int, packedBlocks [][]byte) {
    intervals = make([]int, 0)
    packedBlocks = make([][]byte, 0)
    for i, point := range points {
        if i == 0 || point.interval != intervals[len(intervals)-1]+archive.secondsPerPoint {
            intervals = append(intervals, point.interval)
            packedBlocks = append(packedBlocks, point.Bytes())
        } else {
            packedBlocks[len(packedBlocks)-1] = append(packedBlocks[len(packedBlocks)-1], point.Bytes()...)
        }
    }
    return
}
```

[whisper.go#L935-L940](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L935-L940)

```go {linenos=table,linenostart=935}
func (point *dataPoint) Bytes() []byte {
    b := make([]byte, PointSize)
    packInt(b, point.interval, 0)
    packFloat64(b, point.value, IntSize)
    return b
}
```

[whisper.go#L141-L145](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L141-L145)

```go {linenos=table,linenostart=141}
// Wrappers for whisper.file operations
func (whisper *Whisper) fileWriteAt(b []byte, off int64) error {
    _, err := whisper.file.WriteAt(b, off)
    return err
}
```

[whisper.go#L616-L623](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L616-L623)

```go {linenos=table,linenostart=616}
func (whisper *Whisper) lowerArchives(archive *archiveInfo) (lowerArchives []*archiveInfo) {
    for i, lower := range whisper.archives {
        if lower.secondsPerPoint > archive.secondsPerPoint {
            return whisper.archives[i:]
        }
    }
    return
}
```

[whisper.go#L670-L692](https://github.com/lomik/go-whisper/blob/6de93631b9853148a7e1a659f7805a89451368bf/whisper.go#L670-L692)

```go {linenos=table,linenostart=670}
func (whisper *Whisper) readSeries(start, end int64, archive *archiveInfo) ([]dataPoint, error) {
    var b []byte
    if start < end {
        b = make([]byte, end-start)
        err := whisper.fileReadAt(b, start)
        if err != nil {
            return nil, err
        }
    } else {
        b = make([]byte, archive.End()-start)
        err := whisper.fileReadAt(b, start)
        if err != nil {
            return nil, err
        }
        b2 := make([]byte, end-archive.Offset())
        err = whisper.fileReadAt(b2, archive.Offset())
        if err != nil {
            return nil, err
        }
        b = append(b, b2...)
    }
    return unpackDataPoints(b), nil
}
