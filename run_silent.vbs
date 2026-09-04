' 콘솔 창 없이 main.py를 백그라운드로 실행합니다 (Windows 시작프로그램용).
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

pythonw = scriptDir & "\venv\Scripts\pythonw.exe"
mainPy = scriptDir & "\main.py"

shell.CurrentDirectory = scriptDir
shell.Run """" & pythonw & """ """ & mainPy & """", 0, False
