[CmdletBinding()]
param(
    [string] $SkillsDir = (Join-Path $HOME '.agents/skills')
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$skillName = 'hanwu-crocodile'
$archiveUrl = 'https://github.com/gutianniao/hanwu-crocodile-skill/releases/download/v1.0.0/hanwu-crocodile-skill.zip'
$expectedHash = 'E74107D2542204102DF0D2D4823A6A3A23BA5F99CD4084D4EE76B067D7740C27'
$destination = Join-Path $SkillsDir $skillName
$existingInstall = Join-Path $destination 'SKILL.md'

if (Test-Path -LiteralPath $existingInstall -PathType Leaf) {
    Write-Output "Already installed at $destination"
    return
}
if (Test-Path -LiteralPath $destination) {
    throw "Installation path already exists: $destination"
}

if (-not $PSBoundParameters.ContainsKey('SkillsDir')) {
    $codexDirectory = Join-Path $HOME '.codex'
    if ($env:CODEX_HOME) {
        $codexDirectory = $env:CODEX_HOME
    }
    $legacyDirectory = Join-Path $codexDirectory "skills/$skillName"
    if (Test-Path -LiteralPath (Join-Path $legacyDirectory 'SKILL.md') -PathType Leaf) {
        Write-Output "Already installed at $legacyDirectory"
        return
    }
}

$skillsPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SkillsDir)
[void][System.IO.Directory]::CreateDirectory($skillsPath)
$skillsRoot = Get-Item -LiteralPath $SkillsDir
$destination = Join-Path $skillsRoot.FullName $skillName
$staging = $skillsRoot.CreateSubdirectory(".$skillName-install-$([guid]::NewGuid())")

try {
    $archive = Join-Path $staging.FullName 'skill.zip'
    Invoke-WebRequest -Uri $archiveUrl -UseBasicParsing -TimeoutSec 60 -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'The downloaded ZIP did not match the published SHA-256.'
    }

    Expand-Archive -LiteralPath $archive -DestinationPath $staging.FullName
    $source = Join-Path $staging.FullName $skillName
    if (-not (Test-Path -LiteralPath (Join-Path $source 'SKILL.md') -PathType Leaf)) {
        throw 'The downloaded ZIP does not contain the expected skill directory.'
    }

    [System.IO.Directory]::Move($source, $destination)
} finally {
    if ($staging.Parent.FullName -eq $skillsRoot.FullName) {
        Remove-Item -LiteralPath $staging.FullName -Recurse -Force
    }
}

Write-Output "Installed $skillName at $destination"
Write-Output 'Open a new Codex chat and enter $hanwu-crocodile.'
