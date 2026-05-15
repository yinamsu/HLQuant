# HLQuant 서버 로그 다운로드 및 조회 스크립트 (PowerShell 전용)
# 사용법: .\get_server_log.ps1 [-Download]

param (
    [switch]$Download
)

$TMP_KEY_PATH = "deploy_key_fixed"
$REMOTE_USER = "yinamsu"
$REMOTE_HOST = "136.114.144.64"
$REMOTE_LOG_PATH = "~/HLQuant/bot.log"
$LOCAL_LOG_PATH = "server_bot.log"

if (-not (Test-Path $TMP_KEY_PATH)) {
    Write-Error "$TMP_KEY_PATH 파일이 존재하지 않습니다."
    exit
}

# Windows SSH 보안 권한 설정 (icacls)
Write-Host "🛡️ 키 파일 보안 권한 설정 중..." -ForegroundColor Cyan
icacls $TMP_KEY_PATH /inheritance:r | Out-Null
icacls $TMP_KEY_PATH /grant:r "${env:USERNAME}:(R)" | Out-Null

try {
    if ($Download) {
        Write-Host "📥 서버 로그 다운로드 중 ($REMOTE_LOG_PATH -> $LOCAL_LOG_PATH)..." -ForegroundColor Yellow
        scp -i $TMP_KEY_PATH -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_LOG_PATH}" $LOCAL_LOG_PATH
        Write-Host "✅ 다운로드 완료: $LOCAL_LOG_PATH" -ForegroundColor Green
    } else {
        Write-Host "📋 서버 로그 최근 50줄 조회:" -ForegroundColor Yellow
        Write-Host "--------------------------------------------------"
        ssh -i $TMP_KEY_PATH -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "tail -n 50 $REMOTE_LOG_PATH"
        Write-Host "--------------------------------------------------"
    }
} catch {
    Write-Error "서버 접속 중 오류가 발생했습니다: $_"
}
