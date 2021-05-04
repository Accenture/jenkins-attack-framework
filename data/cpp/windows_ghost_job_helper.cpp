//cl.exe -nologo -Gm- -GR- -EHa- -Oi -O1 -Os -GS- -kernel -GR- -MT -Gs9999999 windows_ghost_job_helper.cpp -link -subsystem:windows -nodefaultlib kernel32.lib User32.lib advapi32.lib
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <sddl.h>

extern "C"
{
#pragma function(memset)
    void* memset(void* dest, int c, size_t count)
    {
        char* bytes = (char*)dest;
        while (count--)
        {
            *bytes++ = (char)c;
        }
        return dest;
    }

#pragma function(memcpy)
    void* memcpy(void* dest, const void* src, size_t count)
    {
        char* dest8 = (char*)dest;
        const char* src8 = (const char*)src;
        while (count--)
        {
            *dest8++ = *src8++;
        }
        return dest;
    }
}

BOOL DenyAccess()
{
    HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, GetCurrentProcessId());
    
    SECURITY_ATTRIBUTES sa;
    char szSD[4] = "D:P"; // Disable all access (except for privileged users)
    sa.nLength = sizeof(SECURITY_ATTRIBUTES);
    sa.bInheritHandle = FALSE;

    if (!ConvertStringSecurityDescriptorToSecurityDescriptorA(szSD, SDDL_REVISION_1, &(sa.lpSecurityDescriptor), NULL))
        return FALSE;

    if (!SetKernelObjectSecurity(hProcess, DACL_SECURITY_INFORMATION, sa.lpSecurityDescriptor))
        return FALSE;

    return TRUE;
}

BOOL IsElevated() {
    BOOL fRet = FALSE;
    HANDLE hToken = NULL;
    
    if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken)) {
        TOKEN_ELEVATION Elevation;
        DWORD cbSize = sizeof(TOKEN_ELEVATION);
        if (GetTokenInformation(hToken, TokenElevation, &Elevation, sizeof(Elevation), &cbSize)) {
            fRet = Elevation.TokenIsElevated;
        }
    }

    if (hToken) {
        CloseHandle(hToken);
    }
    return fRet;
}

char * GetArgString()
{
    static char *cmd = GetCommandLineA();

    bool flag = false;

    while (*cmd)
    {
        if (*cmd == L' ')
            flag = true;

        if (flag && *cmd != ' ')
            break;

        cmd++;
    }

    return cmd;
}

void CreateRandomString(char* randString, int length)
{
    const char alphabet[] = {
    '0','1','2','3','4',
    '5','6','7','8','9',
    'A','B','C','D','E','F',
    'G','H','I','J','K',
    'L','M','N','O','P',
    'Q','R','S','T','U',
    'V','W','X','Y','Z',
    'a','b','c','d','e','f',
    'g','h','i','j','k',
    'l','m','n','o','p',
    'q','r','s','t','u',
    'v','w','x','y','z'
    };

    char * randomData = (char *) HeapAlloc(GetProcessHeap(), 0, 500);

    int j = 0;
    char r = 0;

    for (int i = 0; i < length; i++)
    {
        while (true)
        {
            r = randomData[j];
            j++;

            if (j == 500)
            {
                HeapFree(GetProcessHeap(), 0, randomData);
                randomData = (char *) HeapAlloc(GetProcessHeap(), 0, 500);
                j = 0;
            }

            if (r != 0) //Whitening since lots of heap is null bytes.
                break;
        }

        randString[i] = alphabet[r % (strlen(alphabet) - 1)];
    }

    HeapFree(GetProcessHeap(), 0, randomData);
}

void LaunchProcess(char *cmd) {
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    GetStartupInfoA(&si);

    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi);
}

void SelfDelete(){
    char self[MAX_PATH];
    DWORD size = 0;

    size = GetModuleFileNameA(NULL, self, MAX_PATH);

    if(size == 0)
        return;

    char *cmd = (char *) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 50 + size);

    strcpy(cmd, "cmd /S /C \"TIMEOUT /T 4 /NOBREAK >NUL & DEL /Q \"");
    strcat(cmd, self);
    strcat(cmd, "\"\"");

    LaunchProcess(cmd);

    HeapFree(GetProcessHeap(), 0, cmd);

    ExitProcess(0);
}

void HandleNonAdmin() {
    //Modify ACL's so that only Admin's can terminate us.
    DenyAccess();

    char *cmd = GetArgString();
    Sleep(20 * 1000); //Sleep long enough that Jenkin's job is terminated and no longer trying to kill us our children.

    LaunchProcess(cmd);
    SelfDelete();
}

bool CreateBatchFile(char *dir, char *cmd, char *&tempBatFile)
{
    HANDLE fileHandle;
    tempBatFile = (char *) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 16 + strlen(dir));
    char *temp = (char*) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 10); 

    int i = 0;

    while (true)
    {
        CreateRandomString(temp, 9);

        strcpy(tempBatFile, dir);
        strcat(tempBatFile, "\\");
        strcat(tempBatFile, temp);
        strcat(tempBatFile, ".bat");

        fileHandle = CreateFileA(tempBatFile, GENERIC_READ | GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);

        if (fileHandle != INVALID_HANDLE_VALUE)
            break;

        i++;

        if (i > 5)
            return false;
    }

    HeapFree(GetProcessHeap(), 0, temp);

    if (!WriteFile(fileHandle, "@echo off\r\nPUSHD \"%~f0\\..\\\"\r\nCALL ", 34, NULL, NULL))
        goto errorclose;

    if (!WriteFile(fileHandle, cmd, strlen(cmd), NULL, NULL))
        goto errorclose;

    if (!WriteFile(fileHandle, "\r\nDEL /Q \"%~f0\" >NUL 2>NUL", 26, NULL, NULL))
        goto errorclose;

    return CloseHandle(fileHandle);

errorclose:
    CloseHandle(fileHandle);
    return false;
}

void HandleAdmin() {
    char dir[MAX_PATH];
    
    if (GetCurrentDirectoryA(MAX_PATH, dir) == 0)
        return;

    char* cmd = GetArgString();

    char* tempBatchFile = nullptr;

    if (!CreateBatchFile(dir, cmd, tempBatchFile))
        return;

    char* wmic_cmd = (char*)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, 57 + strlen(tempBatchFile));
    
    strcpy(wmic_cmd, "C:\\Windows\\System32\\wbem\\WMIC.exe process call create \"");
    strcat(wmic_cmd, tempBatchFile);
    strcat(wmic_cmd, "\"");

    LaunchProcess(wmic_cmd);
    
    Sleep(2 * 1000);

    DeleteFileA(tempBatchFile);

    HeapFree(GetProcessHeap(), 0, wmic_cmd);
    HeapFree(GetProcessHeap(), 0, tempBatchFile);

    SelfDelete();
}

void WinMainCRTStartup()
{
    DWORD dwMode = SetErrorMode(SEM_NOGPFAULTERRORBOX);
    SetErrorMode(dwMode | SEM_NOGPFAULTERRORBOX);

    if (IsElevated())
        HandleAdmin();
    else
        HandleNonAdmin();

    ExitProcess(0);
}