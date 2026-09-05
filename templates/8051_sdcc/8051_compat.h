#ifndef __8051_COMPAT_H__
#define __8051_COMPAT_H__

/**
 * @file 8051_compat.h
 * @brief Portability compatibility layer for SDCC and Keil C51 compilers.
 */

#if defined(SDCC) || defined(__SDCC)
    #include <8051.h>
    #define SFR(name, addr)   __sfr __at(addr) name
    #define SBIT(name, addr)  __sbit __at(addr) name
    #define INTERRUPT(num)    __interrupt(num)
    #define BIT               __bit
    #define DATA              __data
    #define IDATA             __idata
    #define XDATA             __xdata
    #define CODE              __code
#else
    #include <reg52.h>
    #define SFR(name, addr)   sfr name = addr
    #define SBIT(name, addr)  sbit name = addr
    #define INTERRUPT(num)    interrupt num
    #define BIT               bit
    #define DATA              data
    #define IDATA             idata
    #define XDATA             xdata
    #define CODE              code
#endif

#endif /* __8051_COMPAT_H__ */
