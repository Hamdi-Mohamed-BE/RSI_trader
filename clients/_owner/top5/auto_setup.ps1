function Get-OnlyActiveTarget($Candidates,$Processes) {
    $active=@($Candidates | Where-Object Running)
    if (@($Processes).Count -ne 1 -or $active.Count -ne 1) { throw 'Keep exactly ONE supported MT5 terminal open and logged in, then run this installer again. No terminal was changed.' }
    $target=$active[0]
    $p=@($Processes)[0]
    if (!$p.Path -or $p.Path -ine $target.Exe) { throw 'Cannot identify the active MT5 safely.' }
    $info=Get-CimInstance Win32_Process -Filter ("ProcessId="+$p.Id)
    if (!$info.CommandLine) { throw 'Cannot inspect MT5 startup settings safely.' }
    if ($info.CommandLine -match '(?i)/portable|/tester') { throw 'Portable and tester terminals are not supported. Open your normal MT5 terminal.' }
    if ($info.CommandLine -match '(?i)/config:') {
        if(!(Test-CalyxRecoveryConfig $info.CommandLine $target.Data)){throw 'MT5 is using an unrelated custom configuration. Close it normally and reopen it from its usual shortcut before setup.'}
        Write-Host 'Recognized the previous Calyx detector startup. Continuing with manual symbols; the detector will not be run again.'
    }
    return $target
}
function Test-CalyxRecoveryConfig([string]$CommandLine,[string]$DataDir) {
    $argsFound=[regex]::Matches($CommandLine,'(?i)(?:^|\s)/config:(?:"([^"]+)"|([^\s"]+))')
    if($argsFound.Count -ne 1){return $false}
    $m=$argsFound[0];$path=if($m.Groups[1].Success){$m.Groups[1].Value}else{$m.Groups[2].Value}
    try {
        $full=[IO.Path]::GetFullPath($path)
        $expected=[IO.Path]::GetFullPath((Join-Path $DataDir 'MQL5\Files\CalyxTop5'))
        if([IO.Path]::GetDirectoryName($full) -ine $expected -or [IO.Path]::GetFileName($full) -notmatch '^startup-[a-f0-9]{32}\.ini$'){return $false}
        if(!(Test-Path -LiteralPath $full -PathType Leaf)){return $false}
        $profile=Safe-Line (Ini-Value $full 'Charts' 'ProfileLast') 'recovery profile'
        $symbol=Safe-Line (Ini-Value $full 'StartUp' 'Symbol') 'recovery symbol'
        $saved=Ini-Value (Join-Path $DataDir 'config\common.ini') 'Charts' 'ProfileLast'
        if($profile -cne $saved){return $false}
        # Accept only our exact read-only detector config, without any account,
        # credential, tester, Expert or global AutoTrading overrides.
        $expectedText="[Charts]`nProfileLast=$profile`n[StartUp]`nScript=CalyxTop5\Detect Broker Symbols`nSymbol=$symbol`nPeriod=M1`nShutdownTerminal=0"
        return ([IO.File]::ReadAllText($full).Replace("`r`n","`n").Trim() -ceq $expectedText)
    } catch {return $false}
}
function Close-SelectedTerminal([string]$Exe) {
    $processes=@(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -ieq $Exe })
    if($processes.Count -ne 1){throw 'Selected MT5 process changed. Setup stopped.'}
    if(!$processes[0].CloseMainWindow()){throw 'MT5 did not accept a normal close request. No forced termination will be used.'}
    if(!$processes[0].WaitForExit(30000)){throw 'MT5 is waiting on a dialog or did not close. Setup stopped without force-killing it.'}
}
function Start-SelectedTerminal([string]$Exe,[string]$Arguments='') {
    if(Test-Running $Exe){throw 'MT5 is already running; refusing a conflicting startup.'}
    if($Arguments){Start-Process -FilePath $Exe -ArgumentList $Arguments -WindowStyle Hidden | Out-Null}
    else{Start-Process -FilePath $Exe -WindowStyle Hidden | Out-Null}
}
function Read-SavedContext($Target) {
    $ini=Join-Path $Target.Data 'config\common.ini'
    $login=0L;$raw=Ini-Value $ini 'Common' 'Login'
    if(![long]::TryParse($raw,[ref]$login) -or $login -le 0){throw 'The active account could not be read from saved MT5 settings.'}
    $server=Safe-Line (Ini-Value $ini 'Common' 'Server') 'saved broker server'
    $profile=Safe-Line (Ini-Value $ini 'Charts' 'ProfileLast') 'saved active profile'
    if($profile -in @('.','..')){throw 'Invalid saved chart profile'}
    $folder=Join-Path $Target.Data ('MQL5\Profiles\Charts\'+$profile)
    $charts=@(Get-ChildItem -LiteralPath $folder -Filter '*.chr' -File)
    if(!$charts.Count){throw 'Open at least one chart in MT5 before setup.'}
    $anchor=''
    foreach($chart in $charts){$body=[IO.File]::ReadAllText($chart.FullName);if($body -match '(?m)^symbol=([^\r\n]+)'){$anchor=Safe-Line $Matches[1] 'chart symbol';break}}
    if(!$anchor){throw 'No saved chart symbol found for automatic discovery.'}
    return [pscustomobject]@{Login=$login;Server=$server;Profile=$profile;Anchor=$anchor}
}
function Select-AutomaticSymbols($Rows) {
    $map=@{}
    foreach($canonical in @($Package.entries.symbol | Select-Object -Unique)) {
        $matches=@(Find-SymbolCandidates $Rows $canonical)
        if($matches.Count -gt 1){
            $selected=@($matches | Where-Object { $_.selected -eq '1' })
            if($selected.Count -eq 1){$matches=$selected}
        }
        if($matches.Count -ne 1){throw "Cannot safely auto-map $canonical. Keep just the desired compatible contract in Market Watch, then retry. No five-EA profile will be activated."}
        $map[$canonical]=[string]$matches[0].name
    }
    return $map
}
function Discover-Automatically($Target,$Context) {
    $scriptDir=Join-Path $Target.Data 'MQL5\Scripts\CalyxTop5'
    $fileDir=Join-Path $Target.Data 'MQL5\Files\CalyxTop5'
    $null=New-Item -ItemType Directory -Path $scriptDir -Force
    $null=New-Item -ItemType Directory -Path $fileDir -Force
    $scriptPath=Join-Path $scriptDir 'Detect Broker Symbols.ex5'
    [IO.File]::WriteAllBytes($scriptPath,[Convert]::FromBase64String('__DETECTOR_B64__'))
    if((File-Hash $scriptPath) -cne '__DETECTOR_SHA256__'){throw 'Detector verification failed'}
    $nonce=[Guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllLines((Join-Path $fileDir 'discovery-request.txt'),@($nonce,[string]$Context.Login,$Context.Server),[Text.Encoding]::Unicode)
    $config=Join-Path $fileDir ("startup-$nonce.ini")
    # No login/password override, no global Experts settings. An extra temporary chart
    # avoids replacing any existing EA/script and is not saved by the startup mechanism.
    $text="[Charts]`r`nProfileLast=$($Context.Profile)`r`n[StartUp]`r`nScript=CalyxTop5\Detect Broker Symbols`r`nSymbol=$($Context.Anchor)`r`nPeriod=M1`r`nShutdownTerminal=0`r`n"
    [IO.File]::WriteAllText($config,$text,[Text.Encoding]::Unicode)
    Start-SelectedTerminal $Target.Exe ('/config:"'+$config+'"')
    $snapshot=Join-Path $fileDir ("symbols-$nonce.tsv")
    # MT5 may update itself and load chart history before it initializes a Script.
    # The previous 90-second budget included that work and could kill initialization.
    $deadline=[DateTime]::UtcNow.AddSeconds(300)
    $nextNotice=[DateTime]::UtcNow.AddSeconds(15)
    $errorPath=Join-Path $fileDir ("symbols-$nonce.error")
    $startedPath=Join-Path $fileDir ("symbols-$nonce.started")
    while(!(Test-Path -LiteralPath $snapshot)){
        if(Test-Path -LiteralPath $errorPath){throw ([IO.File]::ReadAllText($errorPath))}
        if([DateTime]::UtcNow -ge $deadline){
            if(Test-Path -LiteralPath $startedPath){throw 'Detector started but did not finish within five minutes. Check MT5 Experts log. No client bots were attached.'}
            throw 'MT5 did not initialize the detector within five minutes. Let terminal updates/history loading finish, then retry. No client bots were attached.'
        }
        if([DateTime]::UtcNow -ge $nextNotice){
            if(Test-Path -LiteralPath $startedPath){Write-Host 'Detector running; checking broker connection and symbols...'}
            else{Write-Host 'Waiting for MT5 startup, chart history and detector initialization...'}
            $nextNotice=[DateTime]::UtcNow.AddSeconds(15)
        }
        Start-Sleep -Milliseconds 500
    }
    $rows=Read-BrokerCatalog $snapshot $nonce $Context.Login $Context.Server
    $map=Select-AutomaticSymbols $rows
    Close-SelectedTerminal $Target.Exe
    return $map
}
