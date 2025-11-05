@echo off
chcp 65001 > nul 

:: 변수 설정
set "TARGET_DIR=%~dp0MabinogiMobile_Data\Plugins\x86_64\ToyWebView"
set "ORIGINAL_FILE=cefhelper.exe"
set "DISABLED_FILE=cefhelper_.exe"

:: 폴더 존재 여부 확인
if not exist "%TARGET_DIR%" goto ERROR_FOLDER

:: 패치된 파일 복구
if exist "%TARGET_DIR%\%DISABLED_FILE%" (
    
    ren "%TARGET_DIR%\%DISABLED_FILE%" "%ORIGINAL_FILE%"
    echo 파일 복구 완료
    goto END
)

:: 공지 비활성화 패치
if exist "%TARGET_DIR%\%ORIGINAL_FILE%" (
    
    ren "%TARGET_DIR%\%ORIGINAL_FILE%" "%DISABLED_FILE%"
    echo 공지 비활성화 패치 완료
    goto END
)

:: 예외 처리
goto ERROR_FILE_NOT_FOUND

:ERROR_FOLDER
echo 오류: 플러그인 폴더를 찾을 수 없습니다. 경로를 확인해 주세요.
echo 경로: "%TARGET_DIR%"
goto END

:ERROR_FILE_NOT_FOUND
echo 오류: 플러그인 경로에서 필요한 파일 %ORIGINAL_FILE% 또는 %DISABLED_FILE% 을 찾을 수 없습니다.
echo 경로: "%TARGET_DIR%"
goto END

:: 종료
:END
echo.
pause
