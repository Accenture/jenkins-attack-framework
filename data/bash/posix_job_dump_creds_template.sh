#!/bin/bash

echo "@{barrier}" >> "@{file_name}"
#for @cred in @credentials:
echo "@{cred.type}" >> "@{file_name}"
echo "@{cred.description}" >> "@{file_name}"
#if(@{cred.type} == "PASSWORD" || @{cred.type} == "SECRETTEXT")
echo "$@{cred.variable}" >> "@{file_name}"
#elseif(@{cred.type} == "SSHKEY")
echo "$@{cred.username_variable}" >> "@{file_name}"
echo "$@{cred.passphrase_variable}" >> "@{file_name}"
cat "$@{cred.key_file_variable}" >> "@{file_name}"
#elseif(@{cred.type} == "SECRETFILE")
cat "$@{cred.variable}" >> "@{file_name}"
#end
echo "@{barrier}" >> "@{file_name}"
#end
echo "-----BEGIN CERTIFICATE-----" 
cat "@{file_name}" | base64
echo "-----END CERTIFICATE-----"
rm -f "@{file_name}" >/dev/null 2>&1
rm -- "$0" >/dev/null 2>&1
