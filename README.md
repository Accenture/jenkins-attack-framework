Jenkins Attack Framework
============================

## Description

This project can currently perform the following tasks:

* **AccessCheck:** Test credentials and provide a rough overview of their access levels

* **ConsoleOutput:** Dump the console output of the last build of every job on the server (Can be Gigabytes of data, but good for finding credentials)

* **CreateAPIToken:** Creates an API Token for the current user (Or another user if you have administrative credentials)

* **DeleteAPIToken:** Deletes an API Token for the current user (Or another user if you have administrative credentials. Lists existing ones if no token supplied)

* **DeleteJob:** Delete a Job, or failing that, attempt a number of follow-up mitigations from most-to-least effective.

* **DumpCreds:** Dump credentials (Uses administrative credentials to dump credentials via Jenkins Console)

* **DumpCredsViaJob:** Dump credentials via job creation and explicit enumeration (User needs at least Add Job permissions)

* **ListAPITokens:** List existing API tokens for the current user (Or another user if you have administrative credentials)

* **ListJobs:** List existing Jenkins Jobs (Good For finding specific jobs)

* **RunCommand:** Run system command and get output/errors back (Uses administrative credentials and Jenkins Console)

* **RunJob:** Upload a script and run it as a job.  Also run "Ghost Jobs" that don't terminate or show up in Jenkins (after launch)

* **RunScript:** Run Groovy scripts (Uses administrative credentials to run a Groovy Script via Jenkins Console)

* **UploadFile:** Upload a file (Uses administrative credentials and chunked uploading via Jenkins Console)

* **WhoAmI:** Get the credentialed user's Jenkins groups (Usually contains their domain groups)

* More things are in the works...

## Installing

Run the following commands: 

	git clone git@github.com:Accenture/jenkins-attack-framework.git 
	cd jaf
	chmod +x jaf
	sudo ./jaf --install
	./jaf --install

Before you can use the RunJob "ghost job" feature against Windows Jenkins Slaves, you will need to compile the following file `data/cpp/windows_ghost_job_helper.cpp` using Visual Studio's cl tool (see compile arguments in comment at the top of that file), and then drop the compiled file in `data/exe/windows_ghost_job_helper.exe`.

## Command Line Help

The commandline help should be pretty straight forward, but is provided here with additional notes:

	usage: jaf.py <Command> [-h]

	Jenkins Attack Framework

	positional arguments:
	<Command>   Subcommand to run (pass sub command for more detailed help):
				AccessCheck ConsoleOutput CreateAPIToken DeleteAPIToken
				DeleteJob DumpCreds DumpCredsViaJob ListAPITokens ListJobs
				RunCommand RunJob RunScript UploadFile WhoAmI

	optional arguments:
	-h, --help  show this help message and exit

### Common Usage Notes

For every subcommand, you can get more detailed help by calling JAF with the subcommand and no additional options (or the `-h` option).

#### Server URL	

For every command (other than requesting help), the `-s` command is required. This should be the full, base URL to the Jenkins instance.

#### User Agent

JAF will use the following user agent with each request: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36`. This was chosen, at least at the time of this release to fit in. If you wish to use a different user-agent, one can be specified with the `-u` option.

#### Output Redirection

For every command, you may pass the `-o` option with a file path. If passed, JAF will write all output (with the exception of some fatal or critical errors) to the file instead of stdout. This option is particularly useful on Windows where console redirection tends to break on random bytes unless you change the code page.

#### Credentials

If no credentials are provided, JAF will attempt to connect with anonymous credentials.
Credentials can be provided via two methods. To provide a single set of credentials use the `-a` option.
Credentials can take three forms: `user:password`, `user:apitoken`, or a Cookie string. 

In the case of the latter option, the cookie should include the entire cookie (everthing after "Cookie: " in the browser header).
Cookie authentication is particularly useful when the Jenkin server uses federation with another Jenkins server for authentication.
In this scenario, normal `user:password` auth will not work. API tokens _may_ still work. If not, authenticate in your browser, then pass the cookie.
Cookie authentication can also include a `Jenkins Crumb`, which should be concatenated to the end of the cookie string to look something like: `JSESSIONID.9922756a=node0rhre4wjrdcjz9m4tbqx0qwqn1567.node0|Jenkins-Crumb=f5cb5472851aad76fc45568ef1e4160928d075376fd78c436a58d39b99aae09a`

Though JAF can usually determine your authentication type by parsing the string, you can also hint the correct type by prepending your credential string with one of the following (self-explanatory) tags: `{USERPASS}`, `{APITOKEN}`, `{COOKIE}` 

For the following two commands, you may pass a single set of credentials using the `-a` option or you may pass multiple credentials with the `-c` option: `AccessCheck` and `WhoAmI`.
The `-c` option takes either the path to a file which contains one of the aforementioned credential forms per line, or `-`. If `-` is passed, JAF will take credentials via stdin instead of from a file (formatting remains the same).

#### Timeouts, Threads, and Waiting

HTTP Request Timeouts default to 30 seconds. If you would like a shorter or longer timeout, one can be configured with the `-n` option.

For certain multi-request methods (`ConsoleOutput`, `AccessCheck`, or `WhoAmI`), the number of threads (and thus number of simultaneous requests) can be configured. By default 4 threads are used. To specify a different number of threads pass the `-t` option.

For the `RunCommand`, `RunJob`, and `RunScript` methods, in addition to setting a total request timeout, you may pass the `-x` option to explicitly not wait for the request to return. This can be valuable when starting a SOCKS Proxy or similar long running task.


### AccessCheck

This method provides a number of heuristic checks for access levels which are useful for an attacker. A negative result should be accurate. A positive result means that the user potentially has the access, but you will need to perform additonal validation. There are simply too many ways to restrict access in Jenkins and no API for determining granular access levels, so results are not always prefectly accurate.  Currently this method checks for the following access: `Basic Read Access (read)`, `Create Job Access (build)`, `Some level of Admin Access (admin)`, `Script Console Access (script)`, `Scriptler Groovy Script Plugin Access (scriptler)`

	usage: jaf.py AccessCheck [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-t <Threads>]
				[-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-c <Credential File>]

	Jenkins Attack Framework

	positional arguments:
	AccessCheck           Get Users Rough Level of Access on Jenkins Server

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-t <Threads>, --threads <Threads>
							Number of max concurrent HTTP requests. Defaults to: 4
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-c <Credential File>, --credentialfile <Credential File>
							Credential File ("-" for stdin). Creds in form
							"<User>:<Password>" or "<User>:<API Token>"
	-b <Number>, --builds <Number>
                        	Number of recent builds to try if the last build fails (default: 3)
  	-f, --failed          	Include console output from failed builds (default: only successful builds)


### ConsoleOutput

This method dumps the console output for the last build of every job that the user can see. You need at least job viewing privileges which is not always possible to determine. This can and often does result in gigabytes (or even terabytes) of output.

	usage: jaf.py ConsoleOutput [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-t <Threads>]
				[-a [<User>:[<Password>|<API Token>]|<Cookie>]]

	Jenkins Attack Framework

	positional arguments:
	ConsoleOutput         Get Latest Console Output from All Jenkins Jobs

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-t <Threads>, --threads <Threads>
							Number of max concurrent HTTP requests. Defaults to: 4
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string


### CreateAPIToken

Used to create an API Token for the user who's credentials are supplied. If the `--user` option is passed, this command will instead create an API token for the supplied user (but you must have administrative `/script` console access to do this). 

`Token Name` is entirely optional and can be anything even a duplicate of an existing token name. Tokens are shown under the user's `configure` page (`/user/<username>/configure`), so pick a name that will blend in (or no name). If no `Token Name` is specified and you are creating the token for the current user, Jenkins will pick the name `Token Created on <Date>`. If creating a token with no `Token Name` as an admin for another user (or even yourself while using the `--user` option, the name will actually be blank, and the Jenkins API actually makes this kind of difficult to notice). 

On successful token creation, the new API Token will be printed to the screen. You should capture this, as this token can never be viewed again.

	usage: jaf.py CreateAPIToken [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-U <User Name>] [<Token Name>]

	Jenkins Attack Framework

	positional arguments:
	CreateAPIToken        Create an API Token for your user
	<Token Name>          Token Name which is shown under the user's
							configuration page (so pick something that is not too
							suspicious). Can be duplicated (There do not appear to
							be any restrictions on token names). If not provided,
							only token creation date will be shown on user's page.

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-U <User Name>, --user <User Name>
							If provided, will use Jenkins Script Console to add
							token for this user. (Requires Admin "/script"
							permissions)


### DeleteAPIToken

Used to delete an API Token for the user who's credentials are supplied. If the `--user` option is passed, this command will instead delete the API token for the supplied user (but you must have administrative `/script` console access to do this). 

Token Name or UUID is required to actually delete a token. If not supplied, this function effectively acts like `ListAPITokens` and returns a list of existing tokens. If a `Token Name` is supplied this command will try to delete that token and alert you on success or failure. If the name matches multiple tokens, no token will be deleted, and you will receive an error message. In that case, you should instead list tokens (either by calling `DeleteAPIToken` with no additional arguments, or via calling `ListAPITokens`), then try again with a `Token UUID`. Deleted tokens cannot be restored, so make sure you are certain before attempting.

	usage: jaf.py DeleteAPIToken [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
              [-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
              [-U <User Name>] [<Token Name or UUID>]

	Jenkins Attack Framework

	positional arguments:
	DeleteAPIToken        Delete an API Token for your user
	<Token Name or UUID>  If not specified, command will return list of tokens
							for subsequent calls.

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-U <User Name>, --user <User Name>
							If provided, will use Jenkins Script Console to delete
							token for this user. (Requires Admin "/script"
							permissions)


### DeleteJob

Attempts to delete a Jenkins job. If the user does not have the rights, this will instead, attempt to delete all build logs, overwrite the job with a blank job, and then disable the job. 

	usage: jaf.py DeleteJob [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				<Task Name>

	Jenkins Attack Framework

	positional arguments:
	DeleteJob             Delete Jenkins Jobs
	<Task Name>           Task to Delete

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string


### DumpCreds

Should be self explanatory, but this does require administrative credentials with `/script` access.

	usage: jaf.py DumpCreds [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
              [-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
              [-N <Node>]

	Jenkins Attack Framework

	positional arguments:
	DumpCreds             Dump all Stored Credentials on Jenkins

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-N <Node>, --node <Node>
							Node (Slave) to execute against. Executes against
							"master" if not specified.

### DumpCredsViaJob

Dump credentials by creating a Job and explicitly enumerating echoing out all the credentials that are
stored and accessible to the user. These credentials are then Base64 encoded so as to prevent Jenkins from
redacting them.  The credentials are retrieved and formatted. User must have at least Job creation privileges.

	usage: jaf.py DumpCredsViaJob [-h] -s <Server> [-u <User-Agent>]
				[-n <Timeout>] [-o Output File]
				[-a [<User>:[<Password>|<API Token>]|<Cookie>]] [-N <Node>]
				[-T <Node Type>] <Task Name>


	Jenkins Attack Framework

	positional arguments:
	DumpCredsViaJob       Dump credentials via explicit enumeration of shared
							credentials in a job (Only requires job creation
							permissions and some shared credentials)
	<Task Name>           Task to Create, must be unique (may not be deleted if
							user doesn't have job deletion permissions, so pick
							something that blends in)

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-N <Node>, --node <Node>
							Node to execute against. If specified, you must also
							pass -T
	-T <Node Type>, --nodetype <Node Type>
							Node Type, either: "posix" or "windows". If specified,
							you must also pass -N


### ListAPITokens

Method simply lists all existing API Tokens for the user who's creds you supplied. If the `--user` option is passed, this command will instead list the API tokens for the supplied user (but you must have administrative `/script` console access to do this).

The actual API Tokens cannot be recovered as only a hash is stored, and only Admin users can even access these hashes. So this method is really only useful for getting a list before trying to use `CreateAPIToken` or `DeleteAPIToken`.

	usage: jaf.py ListAPITokens [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-U <User Name>]

	Jenkins Attack Framework

	positional arguments:
	ListAPITokens         List API Tokens for your user

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-U <User Name>, --user <User Name>
							If provided, will use Jenkins Script Console to query
							tokens for this user. (Requires Admin "/script"
							permissions)


### ListJobs

Method simply lists all jobs on the server, recursively.

	usage: jaf.py ListJobs [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]

	Jenkins Attack Framework

	positional arguments:
	ListJobs              Get List of All Jenkins Job Names

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string


### RunCommand

This method wraps passed system commands to capture stdout and stderr and return it. Requires administrative credentials with `/script` access.

	usage: jaf.py RunCommand [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-x] [-N <Node>] <System Command> 

	Jenkins Attack Framework

	positional arguments:
	RunCommand            Run System Command on Jenkins via Jenkins Console
	<System Command>      System Command To Run

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-x, --no_wait         Do not wait for Output
	-N <Node>, --node <Node>
							Node (Slave) to execute against. Executes against
							"master" if not specified.


### RunJob

Allows you to run jobs via Jenkins. The command will upload your script or executable and then execute it. The `-e` option allows you to specify what program is called to execute your uploaded script, otherwise the script is executed by the default handler. The `-A` allows you to specify an argument string to pass to your script or executable. For exmple, if both the `-e` and `-A` option were passed, your file would be executed in this fashion: `<executor> <payload name> <argument string>`.

The `-g` option allows you to run "Ghost Jobs". Ghost jobs are jobs which are launched then terminated and deleted so that they do not continue to show up in Jenkins. Due to some clever hackery with this feature, Jenkins does not terminate these jobs (or mark an executor as in-use), and the jobs can run indefinitely on the executing system.  This is an excellent way to upload a SOCKS5 server to a slave and run it on a high port to tunnel traffic with only Create Job permissions.

**GHOSTJOB OPSEC WARNING 1:** In the case of running a GHOST job on a Windows slave, a helper executable is uploaded. If the slave is running as an administrative user, `wmic process call create` is used as part of the job termination bypass. You should not use this technique if the Windows Slaves are running EDR.

**GHOSTJOB OPSEC WARNING 2:** You should ensure that your payloads are designed in such a way as to handle deleting themselves upon completion as in the case of Windows slaves, JAF cannot automatically do this.

	usage: jaf.py RunJob [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-x] [-g] [-N <Node>] [-T <Node Type>] [-e <Executor String>]
				[-A <Additional Arguments String>] <Task Name> <Executable File>

	Jenkins Attack Framework

	positional arguments:
	RunJob                Run Jenkins Jobs
	<Task Name>           Task to Create, must be unique (may not be deleted if
							user doesn't have job deletion permissions, so pick
							something that blends in)
	<Executable File>     Local path to script to upload and run. Should be
							compatible with OS and with expected extension.

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-x, --no_wait         Do not wait for Job. Cannot be specified if -g is
							passed
	-g, --ghost           Launch "ghost job", does not show up as a running job
							after initial launch, does not tie up executors, and
							runs indefinitely. Cannot be specified with the -x
							option.
	-N <Node>, --node <Node>
							Node (Slave) to execute against. Executes against any
							available node if not specified.
	-T <Node Type>, --nodetype <Node Type>
							Node Type, either: "posix" or "windows". If specified,
							you must also pass -N
	-e <Executor String>, --executor <Executor String>
							If passed, this command string will be prepended to
							command string ([<Executor String>] <Executable File>
							[<Additional Arguments String>]).
	-A <Additional Arguments String>, --args <Additional Arguments String>
							If passed, this will be concatonated to the end of the
							command string ([<Executor String>] <Executable File>
							[<Additional Arguments String>]).


### RunScript

Should be self explanatory, but this does require administrative credentials with `/script` access.

	usage: jaf.py RunScript [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
              [-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
              [-x] [-N <Node>] <Groovy File Path> 

	Jenkins Attack Framework

	positional arguments:
	RunScript             Run Specified Groovy Script via Jenkins Console
	<Groovy File Path>    Groovy File Path to Run via Script Console

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-x, --no_wait         Do not wait for Output
	-N <Node>, --node <Node>
							Node (Slave) to execute against. Executes against
							"master" if not specified.


### UploadFile

This method requires administrative credentials with `/script` access.
This method works by chunking files into pieces small enough to post to the Jenkins server as base64 encoded chunks that are decoded via groovy commands in the console and appended to a file.  For this to work, you should ensure that the upload file path is:

1) a full path (no `~` or other expansion will be done, nor folders created).

2) write-able by the jenkin's system user.

3) In the path format for the OS in use.

In addition, it is critical that the file does not already exist. Due to the mulitiple chunk nature, this process is additive. An existing file will result in the upload file being appended to the existing file.


	usage: jaf.py UploadFile [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
              [-o Output File] [-a [<User>:[<Password>|<API Token>]|<Cookie>]]
              [-N <Node>] <Upload File> <Upload File Path> 

	Jenkins Attack Framework

	positional arguments:
	UploadFile            Upload file to Jenkins Server via chunked upload
							through Jenkins Console (slow for large files)
	<Upload File>         Local Path to File to Upload
	<Upload File Path>    Remote Full File Path to Upload To. SHOULD NOT ALREADY
							EXIST! (Upload is appended to existing file)

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-N <Node>, --node <Node>
							Node (Slave) to execute against. Executes against
							"master" if not specified.


### WhoAmI

This method is basically a useability wrapper around `/api/whoAmI`. This page shows the current logged-in users all the Jenkins groups they are in.
In the case of a LDAP/Domain-Connected Jenkins, this also includes all domain groups for the user (recursively or not depends on admin settings).

	usage: jaf.py WhoAmI [-h] -s <Server> [-u <User-Agent>] [-n <Timeout>]
				[-o Output File] [-t <Threads>]
				[-a [<User>:[<Password>|<API Token>]|<Cookie>]]
				[-c <Credential File>]

	Jenkins Attack Framework

	positional arguments:
	WhoAmI                Get Users Roles and Possibly Domain Groups

	optional arguments:
	-h, --help            show this help message and exit
	-s <Server>, --server <Server>
							Jenkins Server
	-u <User-Agent>, --useragent <User-Agent>
							JAF User-Agent. Defaults to: Mozilla/5.0 (Windows NT
							10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like
							Gecko) Chrome/80.0.3987.149 Safari/537.36
	-n <Timeout>, --timeout <Timeout>
							HTTP Request Timeout (in seconds). Defaults to: 30
	-o Output File, --output Output File
							Write Output to File
	-t <Threads>, --threads <Threads>
							Number of max concurrent HTTP requests. Defaults to: 4
	-a [<User>:[<Password>|<API Token>]|<Cookie>], --authentication [<User>:[<Password>|<API Token>]|<Cookie>]
							User + Password or API Token, or full JSESSIONID
							cookie string
	-c <Credential File>, --credentialfile <Credential File>
							Credential File ("-" for stdin). Creds in form
							"<User>:<Password>" or "<User>:<API Token>"


## Version Info:

This should be kept up to date with the lastest version info at the top.

###    1.5.2

Added a bit more postive confirmation when using `RunJob` with the `-g` or `-x` options.

###    1.5.1

Added the `DeleteJob` feature to complement `RunJob` and `ListJob`.

###    1.5

Added the `RunJob` feature including the very powerful `GhostJob` feature.

Other minor bug fixes, more unit tests, and templating updates.

###    1.4.1

More code improvements and clean ups.

Added `--user` option for these commands: `CreateAPIToken`, `DeleteAPIToken`, `ListAPITokens`

###    1.4

More code improvements and clean ups.

Added three new API Token Commands (and corresponding unit tests): `CreateAPIToken`, `DeleteAPIToken`, `ListAPITokens`

###    1.3

Fixed a bunch of little bugs.

Wrote a Unit Test Framework for this tool.

Many minor code clean-ups.

Pulled the `install_dependencies.sh` script into the main `jaf` wrapper script.

###    1.2

Major Code Refactor with Plugin Framework.

Added new "DumpCredsViaJob" method.

Added node/slave specification for many of the commands: DumpCreds, DumpCredsViaJob, RunCommand, RunScript, UploadFile

Fixed a bug in UploadFile where back slashes were not being properly escaped in paths.

Updated Credential Dumping Script to dump more types of credentials and domain and ldap binding credentials.

###    1.1

Fixed some authentication bugs.

###	   1.0

Due to the full re-write/rebranding of Jenkins Miner, this is now version 1.0 of the Jenkins Attack Framework.

Credit
======

This project was originally developed by Shelby Spencer (@shellster) with the gracious support, funding, and resources of Accenture.  The project is wholly owned by Accenture, but is licensed under the MIT license (see LICENSE file).
