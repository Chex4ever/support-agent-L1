param(
    [string]$Email = "ab@vimedia.ru",
    [string]$EnvFile = ".env",
    [int]$MaxObjects = 0,
    [switch]$SummaryOnly,
    [switch]$SkipPanelDates,
    [switch]$ShowAllUmc
)

$envContent = Get-Content $EnvFile -ErrorAction SilentlyContinue
$login = ""; $password = ""; $baseUrl = "https://iridi.com"

foreach ($line in $envContent) {
    if ($line -match '^SUPPORT_TOOLS_LOGIN=(.*)') { $login = $matches[1] }
    if ($line -match '^SUPPORT_TOOLS_PASSWORD=(.*)') { $password = $matches[1] }
}
if ([string]::IsNullOrEmpty($login) -or [string]::IsNullOrEmpty($password)) {
    Write-Error "Credentials not found in $EnvFile"; exit 1
}

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$body = @{USER_LOGIN=$login;USER_PASSWORD=$password;AUTH_FORM="Y";TYPE="AUTH";dologin="1";USER_REMEMBER="Y"} -as [hashtable]
try {
    $resp1 = Invoke-WebRequest -Uri "$baseUrl/admincenter/support_tools.php" -Method POST -Body $body -WebSession $session -UseBasicParsing -MaximumRedirection 0 -ErrorAction SilentlyContinue
    $resp2 = Invoke-WebRequest -Uri "$baseUrl/admincenter/support_tools.php" -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue
} catch { Write-Error "Login failed: $_"; exit 1 }

$content = $resp2.Content
$match = [regex]::Match($content, "sessid['`"]?[:=]['`"]?([a-z0-9]+)")
if (!$match.Success) { Write-Error "Could not extract sessid"; exit 1 }
$sessid = $match.Groups[1].Value
$ajaxUrl = "$baseUrl/bitrix/services/main/ajax.php"

function Call-Ajax($Action, $Data) {
    $url = $ajaxUrl + "?c=iridium:iridium.admincenter_support&action=" + $Action + "&mode=class"
    $allData = @{}; foreach ($key in $Data.Keys) { $allData[$key] = $Data[$key] }
    $allData["SITE_ID"] = "s1"; $allData["sessid"] = $sessid
    $resp = Invoke-WebRequest -Uri $url -Method POST -Body $allData -WebSession $session -UseBasicParsing -ErrorAction SilentlyContinue
    return ($resp.Content | ConvertFrom-Json)
}

Write-Output "=== Searching user: $Email ==="
$userResult = Call-Ajax "getUserInfo" @{email=$Email}
if ($userResult.status -ne "success" -or $userResult.data.err) { Write-Error "User not found"; exit 1 }

$userRow = $userResult.data.content[0]
$userId = ""; $bitrixId = ""
if ($userRow[0] -match "ENTITY_API_ID: (\d+)") { $userId = $matches[1] }
if ($userRow[0] -match "BITRIX_ID:.*?(\d+)") { $bitrixId = $matches[1] }
Write-Output "User: $($userRow[1]) ($Email) | Type: $($userRow[3]) | ID: $userId (Bitrix: $bitrixId)"

Write-Output "`n=== Loading objects... ==="
$objResult = Call-Ajax "getObjectList" @{user_id=$userId}
if ($objResult.status -ne "success" -or $objResult.data.err) {
    Write-Error "Could not get object list with API_ID $userId"; exit 1
}

$objects = @()
foreach ($row in $objResult.data.content) {
    $nameHtml = $row[2]
    $nameMatch = [regex]::Match($nameHtml, ">(.*?)<")
    $name = if ($nameMatch.Success) { $nameMatch.Groups[1].Value } else { $nameHtml }
    $objects += @{id=$row[0]; folderId=$row[1]; name=$name}
}

Write-Output "Total objects found: $($objects.Count)"

if ($MaxObjects -gt 0) { $objects = $objects | Select-Object -First $MaxObjects }

$allLicenses = @()
$licenseCache = @{}
$deviceCache = @{}
$count = 0
$total = $objects.Count
$objWithServers = 0
$objWithUMC = 0
$deviceCalls = 0

foreach ($obj in $objects) {
    $count++
    if (!$SummaryOnly) {
        Write-Output ("  [$count/$total] Checking object $($obj.id): $($obj.name)")
    }

    $objDetail = Call-Ajax "getObject" @{object_id=$obj.id}
    if ($objDetail.status -ne "success" -or $objDetail.data.err) { continue }

    $objRow = $objDetail.data.content[0]

    $licenseHtml = $objRow[4] -replace '^"|"$', ''
    $licMatches = [regex]::Matches($licenseHtml, 'data-license=[''"]([^''"]+)')
    $idMatches = [regex]::Matches($licenseHtml, 'data-id=[''"]([^''"]+)')

    $objLicenses = @()
    for ($i = 0; $i -lt $licMatches.Count; $i++) {
        $objLicenses += @{code=$licMatches[$i].Groups[1].Value; id=$idMatches[$i].Groups[1].Value}
    }

    $serversHtml = $objRow[9] -replace '^"|"$', ''
    $serverCount = 0
    $serverNames = @()
    if (![string]::IsNullOrEmpty($serversHtml)) {
        $srvMatches = [regex]::Matches($serversHtml, '>(.*?)<')
        foreach ($m in $srvMatches) {
            $srvName = $m.Groups[1].Value.Trim()
            if ($srvName.Length -gt 0 -and $srvName -ne "Grafana") {
                $serverNames += $srvName
            }
        }
        $serverCount = ($serverNames | Select-Object -Unique).Count
    }
    if ($serverCount -gt 0) { $objWithServers++ }

    $panelsHtml = $objRow[8] -replace '^"|"$', ''
    $panelCount = 0
    $panelDeviceNames = @()
    $panelHwids = @()
    if (![string]::IsNullOrEmpty($panelsHtml)) {
        $pnMatches = [regex]::Matches($panelsHtml, '>(.*?)<')
        foreach ($m in $pnMatches) {
            $pn = $m.Groups[1].Value.Trim()
            if ($pn.Length -gt 0 -and $pn -ne "Grafana") {
                $panelCount++
                $panelDeviceNames += $pn
            }
        }
        # Extract HWIDs (36-char hex hashes in Grafana URL)
        $hwidMatches = [regex]::Matches($panelsHtml, '([a-f0-9]{36})')
        foreach ($m in $hwidMatches) { $panelHwids += $m.Groups[1].Value }

    }

    # Get panel last connection dates via getDevices
    $panelLastDates = @()
    if (!$SkipPanelDates -and $panelHwids.Count -gt 0) {
        foreach ($hwid in ($panelHwids | Select-Object -Unique)) {
            if ($deviceCache.ContainsKey($hwid)) {
                $devInfo = $deviceCache[$hwid]
            } else {
                $devResult = Call-Ajax "getDevices" @{hwid=$hwid}
                $deviceCalls++
                $devInfo = $null
                if ($devResult.status -eq "success" -and !$devResult.data.err -and $devResult.data.content.Count -gt 0) {
                    $devInfo = $devResult.data.content[0][0]
                    $deviceCache[$hwid] = $devInfo
                } else {
                    $deviceCache[$hwid] = $null
                }
            }
            if ($devInfo -and $devInfo -match "LAST_UPDATE:\s*(.*?)(?:\s+\w+:|$)") {
                $panelLastDates += $matches[1].Trim()
            } else {
                $panelLastDates += "unknown"
            }
        }
    }

    $status = $objRow[2]
    $objUser = $objRow[1] -replace '<[^>]+>', ' ' -replace '\s+', ' '

    foreach ($lic in $objLicenses) {
        if (!$SummaryOnly) {
            Write-Output ("  License: $($lic.code)")
        }

        $licDetail = $null
        if ($licenseCache.ContainsKey($lic.code)) {
            $licDetail = $licenseCache[$lic.code]
        } else {
            $licDetail = Call-Ajax "getLicense" @{license=$lic.code}
            if ($licDetail.status -eq "success" -and !$licDetail.data.err) {
                $licenseCache[$lic.code] = $licDetail
            }
        }

        $umcStatus = "not supported"
        $licStatus = "UNKNOWN"
        $licHardware = "?"
        $licInfo = ""
        $ownerUser = ""
        $ownerEmail = ""
        $isHss = $false

        if ($licDetail -and $licDetail.status -eq "success" -and !$licDetail.data.err -and $licDetail.data.content.Count -gt 0) {
            $licRow = $licDetail.data.content[0]
            $licInfo = $licRow[2] -replace '<[^>]+>', ' ' -replace '\s+', ' '
            $licActive = $licRow[3]
            $licHardware = $licRow[4]
            $licActions = $licRow[7]

            $hasUMCEnable = $licActions -match 'ac_enable_umc'
            $hasUMCDisable = $licActions -match 'ac_disable_umc|ac_remove_umc'
            if ($hasUMCEnable) { $umcStatus = "DISABLED" }
            elseif ($hasUMCDisable) { $umcStatus = "ENABLED" }
            elseif ($licHardware -eq "UMC") { $umcStatus = "ENABLED" }

            $hasDeactivate = $licActions -match 'ac_deactivate_license'
            $hasActivate = $licActions -match 'ac_activate_license'
            $licStatus = if ($hasDeactivate) { "ACTIVE" } elseif ($hasActivate) { "INACTIVE" } else { $licActive }

            # HSS detection: "HSS:HSS_" in license title (col[1]) means HSS-type license
            $licTitle = $licRow[1] -replace '<[^>]+>', ' '
            if ($licTitle -match "HSS:HSS_") {
                $isHss = $true
            }
        }

        if ($umcStatus -ne "not supported") { $objWithUMC++ }

        $allLicenses += @{
            objId = $obj.id
            objName = $obj.name
            licId = $lic.id
            licCode = $lic.code
            licInfo = $licInfo
            licStatus = $licStatus
            licActive = if ($licDetail) { $licDetail.data.content[0][3] } else { "?" }
            hardware = $licHardware
            umc = $umcStatus
            isHss = $isHss
            servers = $serverCount
            panelCount = $panelCount
            panelNames = $panelDeviceNames -join ", "
            panelDates = $panelLastDates -join ", "
            status = $status
            user = $objUser
        }
    }
}

# SUMMARY
Write-Output "`n=============================================="
Write-Output "   LICENSE AUDIT REPORT"
Write-Output "=============================================="
Write-Output "Integrator: $Email"
Write-Output "Total objects managed: $($objects.Count)"
Write-Output "Objects with active servers: $objWithServers"
Write-Output "Total licenses found: $($allLicenses.Count)"
$uniqueCodes = @{}
foreach ($l in $allLicenses) { $uniqueCodes[$l.licCode] = $true }
Write-Output "Unique license codes: $($uniqueCodes.Count)"
$totalUmc = ($allLicenses | Where-Object { $_['umc'] -ne "not supported" }).Count
Write-Output "Licenses with UMC support: $totalUmc"
Write-Output "getDevices API calls: $deviceCalls"
Write-Output ""

# UMC Licenses Detail
$licWithUMC = $allLicenses | Where-Object { $_['umc'] -ne "not supported" }
$hssCount = ($licWithUMC | Where-Object { $_['isHss'] }).Count
$pureUmc = $licWithUMC | Where-Object { !$_['isHss'] }
if ($licWithUMC.Count -gt 0) {
    Write-Output "--- UMC Licenses Detail ---"
    Write-Output "  Total UMC-capable: $($licWithUMC.Count)"
    Write-Output "  HSS-typed (excluded): $hssCount"
    Write-Output "  Pure UMC: $($pureUmc.Count)"
    Write-Output ""
    foreach ($lic in $licWithUMC) {
        $hssTag = if ($lic.isHss) { " [HSS]" } else { "" }
        $umcOk = if ($lic.servers -gt 0) { "OK (has servers)" } else { "WARNING: no active servers" }
        Write-Output "  $($lic.licCode)$hssTag | $($lic.objName) | UMC: $($lic.umc) | Srv: $($lic.servers) | Panels: $($lic.panelCount) | $umcOk"
    }
}

# Pure UMC without servers
Write-Output ""
Write-Output "--- Pure UMC without active servers ---"
$umcNoSrv = $pureUmc | Where-Object { $_['servers'] -eq 0 }
if ($umcNoSrv.Count -gt 0) {
    foreach ($lic in $umcNoSrv) {
        $pDates = if ($lic.panelDates -and $lic.panelDates -ne "") { "Last panel: $($lic.panelDates)" } else { "No panels" }
        Write-Output "  $($lic.licCode) | $($lic.objName) | Panels: $($lic.panelCount) | $pDates"
    }
} else {
    Write-Output "  All pure UMC licenses have active servers."
}

# Show all UMC licenses if requested
if ($ShowAllUmc -and $pureUmc.Count -gt 0) {
    Write-Output ""
    Write-Output "--- All Pure UMC Licenses ($($pureUmc.Count)) ---"
    Write-Output "Code | Object | Status | Srv | Panels | Panel dates"
    foreach ($lic in $pureUmc) {
        $pDates = if ($lic.panelDates) { $lic.panelDates } else { "-" }
        Write-Output ("  " + $lic.licCode + " | " + $lic.objName + " | " + $lic.status + " | " + $lic.servers + " | " + $lic.panelCount + " | " + $pDates)
    }
}

# Free Licenses
Write-Output "`n--- Free Licenses ---"
$freeFound = $false
foreach ($lic in $allLicenses) {
    $isFree = $false
    $reason = ""

    if ($lic.licStatus -eq "INACTIVE") { $isFree = $true; $reason = "License is INACTIVE (not activated)" }
    elseif ($lic.servers -eq 0 -and $lic.panelCount -eq 0) { $isFree = $true; $reason = "No devices connected (0 servers, 0 panels)" }
    elseif ($lic.hardware -match '^[Nn]o$|^[Nn]$|^0$') { $isFree = $true; $reason = "Hardware=N" }

    if ($isFree) {
        $freeFound = $true
        Write-Output "  FREE: $($lic.licCode) (ID: $($lic.licId))"
        Write-Output "    Object: $($lic.objName) | Status: $($lic.licStatus)"
        Write-Output "    Reason: $reason"
        Write-Output "    Info: $($lic.licInfo)"
        Write-Output ""
    }
}

if (!$freeFound) {
    Write-Output "  No free licenses found."
    Write-Output "  All $($allLicenses.Count) licenses are in use."

    Write-Output "`n--- Least Used Licenses ---"
    $sorted = $allLicenses | Sort-Object { $_['servers'] }
    foreach ($lic in $sorted | Select-Object -First 5) {
        Write-Output ("  " + $lic.licCode + " | " + $lic.objName + " | Servers: " + $lic.servers + " | Panels: " + $lic.panelCount)
    }
}

Write-Output "`n=============================================="
