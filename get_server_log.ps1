# HLQuant 서버 로그 다운로드 및 조회 스크립트 (PowerShell 전용)
# 사용법: .\get_server_log.ps1 [-Download]

param (
    [switch]$Download  # 이 옵션을 붙이면 파일을 로컬로 다운로드합니다.
)

$DOTENV_PATH = ".env"
$TMP_KEY_PATH = "deploy_key_tmp"
$REMOTE_USER = "yinamsu"
$REMOTE_HOST = "34.136.45.224"
$REMOTE_LOG_PATH = "~/HLQuant/bot.log"
$LOCAL_LOG_PATH = "server_bot.log"

if (-not (Test-Path $DOTENV_PATH)) {
    Write-Error ".env 파일이 존재하지 않습니다."
    exit
}

# 1. .env에서 SSH_PRIVATE_KEY 추출
Write-Host "🔑 SSH 개인키 추출 중..." -ForegroundColor Cyan
$envContent = Get-Content $DOTENV_PATH -Raw
$keyMatch = [regex]::Match($envContent, 'SSH_PRIVATE_KEY="([\s\S]*?)"')

if (-not $keyMatch.Success) {
    Write-Error ".env 파일에서 SSH_PRIVATE_KEY를 찾을 수 없습니다."
    exit
}

$key = $keyMatch.Groups[1].Value.Trim()
$key | Out-File -FilePath $TMP_KEY_PATH -Encoding ascii

# 2. Windows SSH 보안 권한 설정 (icacls)
Write-Host "🛡️ 키 파일 보안 권한 설정 중..." -ForegroundColor Cyan
icacls $TMP_KEY_PATH /inheritance:r | Out-Null
icacls $TMP_KEY_PATH /grant:r "${env:USERNAME}:(R)" | Out-Null

try {
    if ($Download) {
        # 3-A. 로그 파일 다운로드 (SCP)
        Write-Host "📥 서버 로그 다운로드 중 ($REMOTE_LOG_PATH -> $LOCAL_LOG_PATH)..." -ForegroundColor Yellow
        scp -i $TMP_KEY_PATH -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_LOG_PATH}" $LOCAL_LOG_PATH
        Write-Host "✅ 다운로드 완료: $LOCAL_LOG_PATH" -ForegroundColor Green
    } else {
        # 3-B. 실시간 로그 조회 (SSH tail)
        Write-Host "📋 서버 로그 최근 50줄 조회:" -ForegroundColor Yellow
        Write-Host "--------------------------------------------------"
        ssh -i $TMP_KEY_PATH -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "tail -n 50 $REMOTE_LOG_PATH"
        Write-Host "--------------------------------------------------"
    }
} catch {
    Write-Error "서버 접속 중 오류가 발생했습니다: $_"
} finally {
    # 4. 임시 키 파일 삭제
    if (Test-Path $TMP_KEY_PATH) {
        Remove-Item $TMP_KEY_PATH -Force
        Write-Host "🧹 임시 키 파일 정리 완료." -ForegroundColor Gray
    }
}
