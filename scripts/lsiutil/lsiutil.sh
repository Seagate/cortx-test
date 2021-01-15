#!/bin/sh

if [[ $1 == "disable" ]]
then
   echo "Disabling all phys"
   ./lsiutil_1_71_x86_64 -p1 -a e,80,1,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,2,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,3,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,4,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,5,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,6,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,7,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,8,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,9,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,a,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,b,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,c,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,d,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,e,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,f,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,80,10,0,0 >/dev/null
elif [[ $1 == "enable" ]]
then
   echo "Enabling all phys"
   ./lsiutil_1_71_x86_64 -p1 -a e,81,1,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,2,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,3,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,4,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,5,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,6,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,7,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,8,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,9,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,a,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,b,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,c,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,d,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,e,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,f,0,0 >/dev/null
   ./lsiutil_1_71_x86_64 -p1 -a e,81,10,0,0 >/dev/null
else
   echo "Invalid argument"
   echo "  Usage: >./lsiutil.sh <argument>"
   echo "  argument:"
   echo "    disable: To disable all the phys"
   echo "    enable: To enable all the phys"
fi
