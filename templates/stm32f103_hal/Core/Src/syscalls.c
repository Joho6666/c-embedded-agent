#include <stddef.h>
void *_sbrk(ptrdiff_t incr) { (void)incr; return (void *)-1; }
int _write(int fd, const void *buf, int count) { (void)fd; (void)buf; return count; }
int _close(int fd) { (void)fd; return -1; }
int _fstat(int fd, void *st) { (void)fd; (void)st; return -1; }
int _isatty(int fd) { (void)fd; return 1; }
int _lseek(int fd, int off, int whence) { (void)fd; (void)off; (void)whence; return 0; }
int _read(int fd, void *buf, int count) { (void)fd; (void)buf; (void)count; return 0; }
