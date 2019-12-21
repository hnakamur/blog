+++
Categories = []
Description = ""
Tags = ["golang"]
date = "2016-04-23T16:45:09+09:00"
title = "go-daemonとgoのos.StartProcess()のコードを読んでみた"

+++
## 発端: Goでデーモンを書くのは無理と思っていたら実は出来るらしい

Goでデーモンを書くのは無理と以前どこかで読んだ気がします。
ところが、Pythonで書かれた[Graphite Project](https://github.com/graphite-project)の[carbon](https://github.com/graphite-project/carbon)をGo言語で実装した[lomik/go-carbon](https://github.com/lomik/go-carbon)の Features に Run as daemon と書かれていました。どうやって実現しているのか気になって調べてみたのでメモです。

## go-carbonでデーモン化するための設定

[Configuration](https://github.com/lomik/go-carbon#configuration)に書いてありますが、設定ファイルの `[common]` セクションの `user` を指定して、起動オプションに `-daemon` を指定すればデーモンとして起動します。

## コードリーディング

デーモンとして起動するためのコードは以下のようになっています。
https://github.com/lomik/go-carbon/blob/v0.7.1/carbon-agent.go#L103-L137

```
	if *isDaemon {
		runtime.LockOSThread()

		context := new(daemon.Context)
		if *pidfile != "" {
			context.PidFileName = *pidfile
			context.PidFilePerm = 0644
		}

		if runAsUser != nil {
			uid, err := strconv.ParseInt(runAsUser.Uid, 10, 0)
			if err != nil {
				log.Fatal(err)
			}

			gid, err := strconv.ParseInt(runAsUser.Gid, 10, 0)
			if err != nil {
				log.Fatal(err)
			}

			context.Credential = &syscall.Credential{
				Uid: uint32(uid),
				Gid: uint32(gid),
			}
		}

		child, _ := context.Reborn()

		if child != nil {
			return
		}
		defer context.Release()

		runtime.UnlockOSThread()
	}
```

`daemon.Context` は [github.com/sevlyar/go-daemon](https://github.com/sevlyar/go-daemon)のfork版の [github.com/lomik/go-daemon](https://github.com/lomik/go-daemon)で定義されています。

[Contextの定義](https://github.com/lomik/go-daemon/blob/205ceae1aeac90abdbcae9fca16ba44b407c598d/daemon_posix.go#L20-L61)

```
// A Context describes daemon context.
type Context struct {
	// If PidFileName is non-empty, parent process will try to create and lock
	// pid file with given name. Child process writes process id to file.
	PidFileName string
	// Permissions for new pid file.
	PidFilePerm os.FileMode

	// If LogFileName is non-empty, parent process will create file with given name
	// and will link to fd 2 (stderr) for child process.
	LogFileName string
	// Permissions for new log file.
	LogFilePerm os.FileMode

	// If WorkDir is non-empty, the child changes into the directory before
	// creating the process.
	WorkDir string
	// If Chroot is non-empty, the child changes root directory
	Chroot string

	// If Env is non-nil, it gives the environment variables for the
	// daemon-process in the form returned by os.Environ.
	// If it is nil, the result of os.Environ will be used.
	Env []string
	// If Args is non-nil, it gives the command-line args for the
	// daemon-process. If it is nil, the result of os.Args will be used
	// (without program name).
	Args []string

	// Credential holds user and group identities to be assumed by a daemon-process.
	Credential *syscall.Credential
	// If Umask is non-zero, the daemon-process call Umask() func with given value.
	Umask int

	// Struct contains only serializable public fields (!!!)
	abspath  string
	pidFile  *LockFile
	logFile  *os.File
	nullFile *os.File

	rpipe, wpipe *os.File
}
```

go-carbonのcarbon-agent.goから呼び出していた `Context.Reborn()` の定義はこちらです。
[Context.Reborn()](https://github.com/lomik/go-daemon/blob/205ceae1aeac90abdbcae9fca16ba44b407c598d/daemon_posix.go#L63-L76)

```
// Reborn runs second copy of current process in the given context.
// function executes separate parts of code in child process and parent process
// and provides demonization of child process. It look similar as the
// fork-daemonization, but goroutine-safe.
// In success returns *os.Process in parent process and nil in child process.
// Otherwise returns error.
func (d *Context) Reborn() (child *os.Process, err error) {
	if !WasReborn() {
		child, err = d.parent()
	} else {
		err = d.child()
	}
	return
}
```

そしてここで読んでいる `Context.parent()` の定義がこちらです。

[Context.parent()](https://github.com/lomik/go-daemon/blob/205ceae1aeac90abdbcae9fca16ba44b407c598d/daemon_posix.go#L97-L130)

```
func (d *Context) parent() (child *os.Process, err error) {
	if err = d.prepareEnv(); err != nil {
		return
	}

	defer d.closeFiles()
	if err = d.openFiles(); err != nil {
		return
	}

	attr := &os.ProcAttr{
		Dir:   d.WorkDir,
		Env:   d.Env,
		Files: d.files(),
		Sys: &syscall.SysProcAttr{
			//Chroot:     d.Chroot,
			Credential: d.Credential,
			Setsid:     true,
		},
	}

	if child, err = os.StartProcess(d.abspath, d.Args, attr); err != nil {
		if d.pidFile != nil {
			d.pidFile.Remove()
		}
		return
	}

	d.rpipe.Close()
	encoder := json.NewEncoder(d.wpipe)
	err = encoder.Encode(d)

	return
}
```

Goの標準ライブラリで `os.StartProcess()` というのがあったんですね。APIドキュメントはこちらです。[os.StartProcess()](https://golang.org/pkg/os/#StartProcess)

[os.StartProcess()の実装](https://github.com/golang/go/blob/go1.6.2/src/os/doc.go#L20-L29)

```
// StartProcess starts a new process with the program, arguments and attributes
// specified by name, argv and attr.
//
// StartProcess is a low-level interface. The os/exec package provides
// higher-level interfaces.
//
// If there is an error, it will be of type *PathError.
func StartProcess(name string, argv []string, attr *ProcAttr) (*Process, error) {
	return startProcess(name, argv, attr)
}
```

[os.ProcAttrの定義](https://github.com/golang/go/blob/go1.6.2/src/os/exec.go#L34-L56)

```
// ProcAttr holds the attributes that will be applied to a new process
// started by StartProcess.
type ProcAttr struct {
	// If Dir is non-empty, the child changes into the directory before
	// creating the process.
	Dir string
	// If Env is non-nil, it gives the environment variables for the
	// new process in the form returned by Environ.
	// If it is nil, the result of Environ will be used.
	Env []string
	// Files specifies the open files inherited by the new process.  The
	// first three entries correspond to standard input, standard output, and
	// standard error.  An implementation may support additional entries,
	// depending on the underlying operating system.  A nil entry corresponds
	// to that file being closed when the process starts.
	Files []*File

	// Operating system-specific process creation attributes.
	// Note that setting this field means that your program
	// may not execute properly or even compile on some
	// operating systems.
	Sys *syscall.SysProcAttr
}
```

ここからはOS依存になりますが、Linuxの実装を見ていきます。

[SysProcAttrのLinuxでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_linux.go#L21-L41)

```
type SysProcAttr struct {
	Chroot      string         // Chroot.
	Credential  *Credential    // Credential.
	Ptrace      bool           // Enable tracing.
	Setsid      bool           // Create session.
	Setpgid     bool           // Set process group ID to Pgid, or, if Pgid == 0, to new pid.
	Setctty     bool           // Set controlling terminal to fd Ctty (only meaningful if Setsid is set)
	Noctty      bool           // Detach fd 0 from controlling terminal
	Ctty        int            // Controlling TTY fd
	Foreground  bool           // Place child's process group in foreground. (Implies Setpgid. Uses Ctty as fd of controlling TTY)
	Pgid        int            // Child's process group ID if Setpgid.
	Pdeathsig   Signal         // Signal that the process will get when its parent dies (Linux only)
	Cloneflags  uintptr        // Flags for clone calls (Linux only)
	UidMappings []SysProcIDMap // User ID mappings for user namespaces.
	GidMappings []SysProcIDMap // Group ID mappings for user namespaces.
	// GidMappingsEnableSetgroups enabling setgroups syscall.
	// If false, then setgroups syscall will be disabled for the child process.
	// This parameter is no-op if GidMappings == nil. Otherwise for unprivileged
	// users this should be set to false for mappings work.
	GidMappingsEnableSetgroups bool
}
```

[syscall.CredentialのLinuxなどでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_unix.go#L112-L118)

```
// Credential holds user and group identities to be assumed
// by a child process started by StartProcess.
type Credential struct {
	Uid    uint32   // User ID.
	Gid    uint32   // Group ID.
	Groups []uint32 // Supplementary group IDs.
}
```

[os.startProcess()のLinuxなどでの実装](https://github.com/golang/go/blob/go1.6.2/src/os/exec_posix.go#L21-L50)

```
func startProcess(name string, argv []string, attr *ProcAttr) (p *Process, err error) {
	// If there is no SysProcAttr (ie. no Chroot or changed
	// UID/GID), double-check existence of the directory we want
	// to chdir into.  We can make the error clearer this way.
	if attr != nil && attr.Sys == nil && attr.Dir != "" {
		if _, err := Stat(attr.Dir); err != nil {
			pe := err.(*PathError)
			pe.Op = "chdir"
			return nil, pe
		}
	}

	sysattr := &syscall.ProcAttr{
		Dir: attr.Dir,
		Env: attr.Env,
		Sys: attr.Sys,
	}
	if sysattr.Env == nil {
		sysattr.Env = Environ()
	}
	for _, f := range attr.Files {
		sysattr.Files = append(sysattr.Files, f.Fd())
	}

	pid, h, e := syscall.StartProcess(name, argv, sysattr)
	if e != nil {
		return nil, &PathError{"fork/exec", name, e}
	}
	return newProcess(pid, h), nil
}
```

[os.ProcAttrのLinuxなどでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_unix.go#L120-L127)

```
// ProcAttr holds attributes that will be applied to a new process started
// by StartProcess.
type ProcAttr struct {
	Dir   string    // Current working directory.
	Env   []string  // Environment.
	Files []uintptr // File descriptors.
	Sys   *SysProcAttr
}
```

[syscall.StartProcess()のLinuxなどでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_unix.go#L238-L242)

```
// StartProcess wraps ForkExec for package os.
func StartProcess(argv0 string, argv []string, attr *ProcAttr) (pid int, handle uintptr, err error) {
	pid, err = forkExec(argv0, argv, attr)
	return pid, 0, err
}
```

[syscall.forkExec()のLinuxなどでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_unix.go#L132-L231)

```
func forkExec(argv0 string, argv []string, attr *ProcAttr) (pid int, err error) {
	var p [2]int
	var n int
	var err1 Errno
	var wstatus WaitStatus

	if attr == nil {
		attr = &zeroProcAttr
	}
	sys := attr.Sys
	if sys == nil {
		sys = &zeroSysProcAttr
	}

	p[0] = -1
	p[1] = -1

	// Convert args to C form.
	argv0p, err := BytePtrFromString(argv0)
	if err != nil {
		return 0, err
	}
	argvp, err := SlicePtrFromStrings(argv)
	if err != nil {
		return 0, err
	}
	envvp, err := SlicePtrFromStrings(attr.Env)
	if err != nil {
		return 0, err
	}

	if (runtime.GOOS == "freebsd" || runtime.GOOS == "dragonfly") && len(argv[0]) > len(argv0) {
		argvp[0] = argv0p
	}

	var chroot *byte
	if sys.Chroot != "" {
		chroot, err = BytePtrFromString(sys.Chroot)
		if err != nil {
			return 0, err
		}
	}
	var dir *byte
	if attr.Dir != "" {
		dir, err = BytePtrFromString(attr.Dir)
		if err != nil {
			return 0, err
		}
	}

	// Acquire the fork lock so that no other threads
	// create new fds that are not yet close-on-exec
	// before we fork.
	ForkLock.Lock()

	// Allocate child status pipe close on exec.
	if err = forkExecPipe(p[:]); err != nil {
		goto error
	}

	// Kick off child.
	pid, err1 = forkAndExecInChild(argv0p, argvp, envvp, chroot, dir, attr, sys, p[1])
	if err1 != 0 {
		err = Errno(err1)
		goto error
	}
	ForkLock.Unlock()

	// Read child error status from pipe.
	Close(p[1])
	n, err = readlen(p[0], (*byte)(unsafe.Pointer(&err1)), int(unsafe.Sizeof(err1)))
	Close(p[0])
	if err != nil || n != 0 {
		if n == int(unsafe.Sizeof(err1)) {
			err = Errno(err1)
		}
		if err == nil {
			err = EPIPE
		}

		// Child failed; wait for it to exit, to make sure
		// the zombies don't accumulate.
		_, err1 := Wait4(pid, &wstatus, 0, nil)
		for err1 == EINTR {
			_, err1 = Wait4(pid, &wstatus, 0, nil)
		}
		return 0, err
	}

	// Read got EOF, so pipe closed on exec, so exec succeeded.
	return pid, nil

error:
	if p[0] >= 0 {
		Close(p[0])
		Close(p[1])
	}
	ForkLock.Unlock()
	return 0, err
}
```

いよいよ核心に迫ります。
[syscall.forkAndExecInChild()のLinuxでの実装](https://github.com/golang/go/blob/go1.6.2/src/syscall/exec_linux.go#L47-L325)

```
// Fork, dup fd onto 0..len(fd), and exec(argv0, argvv, envv) in child.
// If a dup or exec fails, write the errno error to pipe.
// (Pipe is close-on-exec so if exec succeeds, it will be closed.)
// In the child, this function must not acquire any locks, because
// they might have been locked at the time of the fork.  This means
// no rescheduling, no malloc calls, and no new stack segments.
// For the same reason compiler does not race instrument it.
// The calls to RawSyscall are okay because they are assembly
// functions that do not grow the stack.
//go:norace
func forkAndExecInChild(argv0 *byte, argv, envv []*byte, chroot, dir *byte, attr *ProcAttr, sys *SysProcAttr, pipe int) (pid int, err Errno) {
	// Declare all variables at top in case any
	// declarations require heap allocation (e.g., err1).
	var (
		r1     uintptr
		err1   Errno
		err2   Errno
		nextfd int
		i      int
		p      [2]int
	)

	// Record parent PID so child can test if it has died.
	ppid, _, _ := RawSyscall(SYS_GETPID, 0, 0, 0)

	// Guard against side effects of shuffling fds below.
	// Make sure that nextfd is beyond any currently open files so
	// that we can't run the risk of overwriting any of them.
	fd := make([]int, len(attr.Files))
	nextfd = len(attr.Files)
	for i, ufd := range attr.Files {
		if nextfd < int(ufd) {
			nextfd = int(ufd)
		}
		fd[i] = int(ufd)
	}
	nextfd++

	// Allocate another pipe for parent to child communication for
	// synchronizing writing of User ID/Group ID mappings.
	if sys.UidMappings != nil || sys.GidMappings != nil {
		if err := forkExecPipe(p[:]); err != nil {
			return 0, err.(Errno)
		}
	}

	// About to call fork.
	// No more allocation or calls of non-assembly functions.
	runtime_BeforeFork()
	r1, _, err1 = RawSyscall6(SYS_CLONE, uintptr(SIGCHLD)|sys.Cloneflags, 0, 0, 0, 0, 0)
	if err1 != 0 {
		runtime_AfterFork()
		return 0, err1
	}

	if r1 != 0 {
		// parent; return PID
		runtime_AfterFork()
		pid = int(r1)

		if sys.UidMappings != nil || sys.GidMappings != nil {
			Close(p[0])
			err := writeUidGidMappings(pid, sys)
			if err != nil {
				err2 = err.(Errno)
			}
			RawSyscall(SYS_WRITE, uintptr(p[1]), uintptr(unsafe.Pointer(&err2)), unsafe.Sizeof(err2))
			Close(p[1])
		}

		return pid, 0
	}

	// Fork succeeded, now in child.

	// Wait for User ID/Group ID mappings to be written.
	if sys.UidMappings != nil || sys.GidMappings != nil {
		if _, _, err1 = RawSyscall(SYS_CLOSE, uintptr(p[1]), 0, 0); err1 != 0 {
			goto childerror
		}
		r1, _, err1 = RawSyscall(SYS_READ, uintptr(p[0]), uintptr(unsafe.Pointer(&err2)), unsafe.Sizeof(err2))
		if err1 != 0 {
			goto childerror
		}
		if r1 != unsafe.Sizeof(err2) {
			err1 = EINVAL
			goto childerror
		}
		if err2 != 0 {
			err1 = err2
			goto childerror
		}
	}

	// Enable tracing if requested.
	if sys.Ptrace {
		_, _, err1 = RawSyscall(SYS_PTRACE, uintptr(PTRACE_TRACEME), 0, 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Session ID
	if sys.Setsid {
		_, _, err1 = RawSyscall(SYS_SETSID, 0, 0, 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Set process group
	if sys.Setpgid || sys.Foreground {
		// Place child in process group.
		_, _, err1 = RawSyscall(SYS_SETPGID, 0, uintptr(sys.Pgid), 0)
		if err1 != 0 {
			goto childerror
		}
	}

	if sys.Foreground {
		pgrp := int32(sys.Pgid)
		if pgrp == 0 {
			r1, _, err1 = RawSyscall(SYS_GETPID, 0, 0, 0)
			if err1 != 0 {
				goto childerror
			}

			pgrp = int32(r1)
		}

		// Place process group in foreground.
		_, _, err1 = RawSyscall(SYS_IOCTL, uintptr(sys.Ctty), uintptr(TIOCSPGRP), uintptr(unsafe.Pointer(&pgrp)))
		if err1 != 0 {
			goto childerror
		}
	}

	// Chroot
	if chroot != nil {
		_, _, err1 = RawSyscall(SYS_CHROOT, uintptr(unsafe.Pointer(chroot)), 0, 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// User and groups
	if cred := sys.Credential; cred != nil {
		ngroups := uintptr(len(cred.Groups))
		if ngroups > 0 {
			groups := unsafe.Pointer(&cred.Groups[0])
			_, _, err1 = RawSyscall(SYS_SETGROUPS, ngroups, uintptr(groups), 0)
			if err1 != 0 {
				goto childerror
			}
		}
		_, _, err1 = RawSyscall(SYS_SETGID, uintptr(cred.Gid), 0, 0)
		if err1 != 0 {
			goto childerror
		}
		_, _, err1 = RawSyscall(SYS_SETUID, uintptr(cred.Uid), 0, 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Chdir
	if dir != nil {
		_, _, err1 = RawSyscall(SYS_CHDIR, uintptr(unsafe.Pointer(dir)), 0, 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Parent death signal
	if sys.Pdeathsig != 0 {
		_, _, err1 = RawSyscall6(SYS_PRCTL, PR_SET_PDEATHSIG, uintptr(sys.Pdeathsig), 0, 0, 0, 0)
		if err1 != 0 {
			goto childerror
		}

		// Signal self if parent is already dead. This might cause a
		// duplicate signal in rare cases, but it won't matter when
		// using SIGKILL.
		r1, _, _ = RawSyscall(SYS_GETPPID, 0, 0, 0)
		if r1 != ppid {
			pid, _, _ := RawSyscall(SYS_GETPID, 0, 0, 0)
			_, _, err1 := RawSyscall(SYS_KILL, pid, uintptr(sys.Pdeathsig), 0)
			if err1 != 0 {
				goto childerror
			}
		}
	}

	// Pass 1: look for fd[i] < i and move those up above len(fd)
	// so that pass 2 won't stomp on an fd it needs later.
	if pipe < nextfd {
		_, _, err1 = RawSyscall(_SYS_dup, uintptr(pipe), uintptr(nextfd), 0)
		if err1 != 0 {
			goto childerror
		}
		RawSyscall(SYS_FCNTL, uintptr(nextfd), F_SETFD, FD_CLOEXEC)
		pipe = nextfd
		nextfd++
	}
	for i = 0; i < len(fd); i++ {
		if fd[i] >= 0 && fd[i] < int(i) {
			_, _, err1 = RawSyscall(_SYS_dup, uintptr(fd[i]), uintptr(nextfd), 0)
			if err1 != 0 {
				goto childerror
			}
			RawSyscall(SYS_FCNTL, uintptr(nextfd), F_SETFD, FD_CLOEXEC)
			fd[i] = nextfd
			nextfd++
			if nextfd == pipe { // don't stomp on pipe
				nextfd++
			}
		}
	}

	// Pass 2: dup fd[i] down onto i.
	for i = 0; i < len(fd); i++ {
		if fd[i] == -1 {
			RawSyscall(SYS_CLOSE, uintptr(i), 0, 0)
			continue
		}
		if fd[i] == int(i) {
			// dup2(i, i) won't clear close-on-exec flag on Linux,
			// probably not elsewhere either.
			_, _, err1 = RawSyscall(SYS_FCNTL, uintptr(fd[i]), F_SETFD, 0)
			if err1 != 0 {
				goto childerror
			}
			continue
		}
		// The new fd is created NOT close-on-exec,
		// which is exactly what we want.
		_, _, err1 = RawSyscall(_SYS_dup, uintptr(fd[i]), uintptr(i), 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// By convention, we don't close-on-exec the fds we are
	// started with, so if len(fd) < 3, close 0, 1, 2 as needed.
	// Programs that know they inherit fds >= 3 will need
	// to set them close-on-exec.
	for i = len(fd); i < 3; i++ {
		RawSyscall(SYS_CLOSE, uintptr(i), 0, 0)
	}

	// Detach fd 0 from tty
	if sys.Noctty {
		_, _, err1 = RawSyscall(SYS_IOCTL, 0, uintptr(TIOCNOTTY), 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Set the controlling TTY to Ctty
	if sys.Setctty {
		_, _, err1 = RawSyscall(SYS_IOCTL, uintptr(sys.Ctty), uintptr(TIOCSCTTY), 0)
		if err1 != 0 {
			goto childerror
		}
	}

	// Time to exec.
	_, _, err1 = RawSyscall(SYS_EXECVE,
		uintptr(unsafe.Pointer(argv0)),
		uintptr(unsafe.Pointer(&argv[0])),
		uintptr(unsafe.Pointer(&envv[0])))

childerror:
	// send error code on pipe
	RawSyscall(SYS_WRITE, uintptr(pipe), uintptr(unsafe.Pointer(&err1)), unsafe.Sizeof(err1))
	for {
		RawSyscall(SYS_EXIT, 253, 0, 0)
	}
}
```

Linuxシステムコールの呼び出しのうち気になったところだけをピックアップします。

* [clone(2) - Linux manual page](http://man7.org/linux/man-pages/man2/clone.2.html)
* [setsid(2) - Linux manual page](http://man7.org/linux/man-pages/man2/setsid.2.html)
* [chroot(2) - Linux manual page](http://man7.org/linux/man-pages/man2/chroot.2.html)
* [setgid(2) - Linux manual page](http://man7.org/linux/man-pages/man2/setgid.2.html)
* [setuid(2) - Linux manual page](http://man7.org/linux/man-pages/man2/setuid.2.html)
* [chdir(2) - Linux manual page](http://man7.org/linux/man-pages/man2/chdir.2.html)

[O'Reilly Japan - Linuxプログラミングインタフェース](http://www.oreilly.co.jp/books/9784873115856/)の「デーモン」の章を見ると、デーモン化の手順として7つの項目が上げられていますが、それら全てを行っているわけではないようです。

例えばumaskのクリアは、上のコードをざっと見た感じではやってなさそうな感じです。

また、ファイルディスクリプタ0, 1, 2をクローズはしていますが、 /dev/null をオープンはしていないようです。「通常は /dev/null をオープンする」と書いてあるので問題はなさそうです。

端末デバイスからの切り離しは [ioctl(2) - Linux manual page](http://man7.org/linux/man-pages/man2/ioctl.2.html) に `TIOCNOTTY` を指定して行っています。 `TIOCNOTTY` については [tty(4) - Linux manual page](http://man7.org/linux/man-pages/man4/tty.4.html) に説明がありました。

`syscall.SysProcAttr` の `Setctty` に `true` を指定していた場合は、 [ioctl(2) - Linux manual page](http://man7.org/linux/man-pages/man2/ioctl.2.html) に `TIOCSCTTY` を指定して制御端末の設定を行っています。 `TIOCSCTTY` については [tty(4) - Linux manual page](http://man7.org/linux/man-pages/man4/tty.4.html) に説明がありました。

ということで、[O'Reilly Japan - Linuxプログラミングインタフェース](http://www.oreilly.co.jp/books/9784873115856/)のデーモン化の手順の全てではないですが、かなりの部分は [os - The Go Programming Language](https://golang.org/pkg/os/#StartProcess) で実現できるということがわかりました。
