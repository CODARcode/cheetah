#!/usr/bin/env python3
"""
Python program to estimate the value of Euler's Number e (base of the
natural logarithm). The purpose of this program is to provide an easy
to understand example of using Cheetah to run an application, without
having to set up an out of tree C program with many dependencies.

If the third argument is passed, uses the Decimal module with the
specified precision, otherwise uses built-in Python floating point.

This is not a rigorous example. Error is calculated using a 1000 digit
value of E.

See https://www.mathsisfun.com/numbers/e-eulers-number.html
"""

import time
import sys
from decimal import Decimal, getcontext


# From https://www.miniwebtool.com/first-n-digits-of-e/?number=1000
E_str = '2.7182818284590452353602874713526624977572470936999595749669676277240766303535475945713821785251664274274663919320030599218174135966290435729003342952605956307381323286279434907632338298807531952510190115738341879307021540891499348841675092447614606680822648001684774118537423454424371075390777449920695517027618386062613313845830007520449338265602976067371132007093287091274437470472306969772093101416928368190255151086574637721112523897844250569536967707854499699679468644549059879316368892300987931277361782154249992295763514822082698951936680331825288693984964651058209392398294887933203625094431173012381970684161403970198376793206832823764648042953118023287825098194558153017567173613320698112509961818815930416903515988885193458072738667385894228792284998920868058257492796104841984443634632449684875602336248270419786232090021609902353043699418491463140934317381436405462531520961836908887070167683964243781405927145635490613031072085103837505101157477041718986106873969655212671546889570350354'


def estimate_e_pow(n, use_decimal=False):
    """Estimate e using (1 + 1/n)^n"""
    if use_decimal:
        num = Decimal('1.0')
        denom = Decimal(n)
    else:
        num = 1.0
        denom = n
    return (1 + num/denom)**n


def estimate_e_factorial(n, use_decimal=False):
    """Estimate e using 1/0! + 1/1! + 1/2! + .. + 1/n!"""
    if use_decimal:
        e = Decimal('1.0')
        fact = 1
        one = Decimal(1)
    else:
        e = 1.0
        fact = 1
        one = 1
    for i in range(1, n):
        fact *= i
        # use one to force Decimal arithmatic if set
        e += one/fact
    return e


def print_usage(arg0):
    print('Usage: %s pow|factorial n [precision]' % arg0)


def main():
    if len(sys.argv) not in (3, 4):
        print_usage(sys.argv[0])
        sys.exit(1)

    method = sys.argv[1]
    try:
        n = int(sys.argv[2])
    except ValueError:
        print_usage(sys.argv[0])
        sys.exit(2)

    if len(sys.argv) > 3:
        try:
            precision = int(sys.argv[3])
            getcontext().prec = precision
        except ValueError:
            print_usage(sys.argv[0])
            sys.exit(2)
    else:
        # use built in floating point
        precision = None

    use_decimal = bool(precision)

    if method == 'pow':
        start = time.time()
        v = estimate_e_pow(n, use_decimal)
        end = time.time()
    elif method == 'factorial':
        start = time.time()
        v = estimate_e_factorial(n, use_decimal)
        end = time.time()
    else:
        print_usage(sys.argv[0])
        sys.exit(2)

    # calculate error using a 1000 decimal precision value of E
    getcontext().prec = 1000

    print('method      ', method)
    print('use_decimal ', use_decimal)
    print('estimate    ', v)
    print('error       ', Decimal(E_str) - Decimal(v))
    print('time(s)     ', end-start)


if __name__ == '__main__':
    main()
