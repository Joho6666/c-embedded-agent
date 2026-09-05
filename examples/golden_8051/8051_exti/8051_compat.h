#ifndef __8051_COMPAT_H__
#define __8051_COMPAT_H__

#if defined(SDCC) || defined(__SDCC)
    #include <8051.h>
    #define SFR(name, addr)   __sfr __at(addr) name
    #define SBIT(name, addr)  __sbit __at(addr) name
    #define INTERRUPT(num)    __interrupt(num)
#else
    #include <reg52.h>
    #define SFR(name, addr)   sfr name = addr
    #define SBIT(name, addr)  sbit name = addr
    #define INTERRUPT(num)    interrupt num
#endif

#endif
