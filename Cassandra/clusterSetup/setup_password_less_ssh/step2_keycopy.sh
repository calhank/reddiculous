#!/usr/bin/expect
spawn ssh-copy-id root@hadoop
expect "password:"
send "PASSWORD\n"
expect eof
spawn ssh-copy-id root@spark1
expect "password:"
send "PASSWORD\n"
expect eof


