$env:SERIOUS_PYTHON_APP = "C:\ai_development\mobile_project\build\python-app"
$env:SERIOUS_PYTHON_SITE_PACKAGES = "C:\ai_development\mobile_project\build\site-packages"
$env:SERIOUS_PYTHON_ANDROID_EXTRACT_PACKAGES = "matplotlib*,mpl_toolkits*,certifi*"
$env:JAVA_HOME = "C:\Users\huxley\java\17.0.13+11"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$gitCmd = "$env:LOCALAPPDATA\Programs\Git\cmd"
$flutterBin = "C:\Users\huxley\flutter\3.44.8\bin"
$env:PATH = "$flutterBin;$gitCmd;$env:JAVA_HOME\bin;$env:ANDROID_HOME\platform-tools;$env:ANDROID_HOME\cmdline-tools\12.0\bin;$env:PATH"

Set-Location "C:\ai_development\mobile_project\build\flutter"
Write-Host "Starting ARM64 APK build..."
& "$flutterBin\flutter.bat" build apk --target-platform android-arm64

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build succeeded! Copying APK..."
    $apkSrc = "C:\ai_development\mobile_project\build\flutter\build\app\outputs\flutter-apk\app-release.apk"
    Copy-Item -Path $apkSrc -Destination "C:\ai_development\JongJongTrader.apk" -Force
    if (-not (Test-Path "C:\ai_development\dist")) {
        New-Item -ItemType Directory -Path "C:\ai_development\dist" -Force
    }
    Copy-Item -Path $apkSrc -Destination "C:\ai_development\dist\JongJongTrader.apk" -Force
    Write-Host "Copied to C:\ai_development\JongJongTrader.apk and dist\JongJongTrader.apk"
} else {
    Write-Host "Build failed with exit code $LASTEXITCODE"
}
