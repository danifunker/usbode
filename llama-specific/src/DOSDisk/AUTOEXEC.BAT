@ECHO OFF
set EXPAND=YES
SET DIRCMD=/O:N
cls
set temp=c:\
set tmp=c:\
path=a:\

IF "%config%"=="NOCD" GOTO QUIT
LH MSCDEX.EXE /D:usbcd001 /L:D

echo.
IF "%config%"=="SETUP_CD" goto AUTOSETUP
IF "%config%"=="LLAMA_SETUP" goto LLAMA_SETUP
GOTO QUIT

:AUTOSETUP
set CDROM=FOO23
FINDCD.EXE
if "%CDROM%"=="FOO23" goto NOCDROM
path=a:\;%CDROM%\
%CDROM%
cd \WIN98
echo.
OEMSETUP.EXE /K "/IE /NF"
goto QUIT

:LLAMA_SETUP
set CDROM=FOO23
FINDCD.EXE
if "%CDROM%"=="FOO23" goto NOCDROM
path=a:\;%CDROM%\
%CDROM%
echo "Enter the full path of the destination where Windows 98 was installed to:
set /P windestdir="(eg. C:\WINDOWS):"
echo "Running TBPLUS with WinDir set to %windestdir%"
cd \drivers\itxllama\tbplus
install "%windestdir%"
echo "Please review any errors from above (there should be none), then reboot and continue Windows 98 Installation from HDD"
pause
goto QUIT

:NOCDROM
echo.
echo The Windows 98 Setup files were not found.
echo.

:QUIT
