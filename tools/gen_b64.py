import base64, sys

# 순서 중요: 긴 문자열 먼저 (우주항구 > 우주항)
# cl="..." 속성 + XML 태그명 모두 교체
pairs = [
    # cl= 속성
    ('cl="하이퍼스페이스"', 'cl="Hyperspace"'),
    ('cl="우주항구"',       'cl="Spaceport"'),
    ('cl="우주항"',         'cl="Spaceport"'),
    ('cl="광업"',           'cl="Mining"'),
    ('cl="농업"',           'cl="Farming"'),
    ('cl="정련업"',         'cl="Refining"'),
    ('cl="정제"',           'cl="Refining"'),
    ('cl="저온성소"',       'cl="Cryosanctum"'),
    ('cl="중간기착지"',     'cl="Waystation"'),
    # XML 오픈 태그 (<태그명  또는 <태그명>)
    ('<하이퍼스페이스',     '<Hyperspace'),
    ('</하이퍼스페이스>',   '</Hyperspace>'),
    ('<우주항구',           '<Spaceport'),
    ('</우주항구>',         '</Spaceport>'),
    ('<우주항',             '<Spaceport'),
    ('</우주항>',           '</Spaceport>'),
    ('<광업',               '<Mining'),
    ('</광업>',             '</Mining>'),
    ('<농업',               '<Farming'),
    ('</농업>',             '</Farming>'),
    ('<정련업',             '<Refining'),
    ('</정련업>',           '</Refining>'),
    ('<정제',               '<Refining'),
    ('</정제>',             '</Refining>'),
    ('<저온성소',           '<Cryosanctum'),
    ('</저온성소>',         '</Cryosanctum>'),
    ('<중간기착지',         '<Waystation'),
    ('</중간기착지>',       '</Waystation>'),
]

map_lines = '\n'.join(
    f"    '{k}' = '{v}'"
    for k, v in pairs
)

script = (
    "$enc = [System.Text.UTF8Encoding]::new($false)\n"
    "$saves = $env:SAVES_DIR\n"
    "$map = [ordered]@{\n"
    + map_lines + "\n"
    "}\n"
    "$files = Get-ChildItem -Path $saves -Filter campaign.xml -Recurse -EA SilentlyContinue\n"
    "if (-not $files) { Write-Host \"campaign.xml not found in $saves\"; Read-Host; exit }\n"
    "Write-Host \"Found: $($files.Count) files\"\n"
    "$totalF = 0; $totalR = 0\n"
    "foreach ($f in $files) {\n"
    "    $txt = [IO.File]::ReadAllText($f.FullName, $enc)\n"
    "    $old = $txt\n"
    "    foreach ($kv in $map.GetEnumerator()) {\n"
    "        $n = ([regex]::Matches($txt, [regex]::Escape($kv.Key))).Count\n"
    "        if ($n -gt 0) { $txt = $txt.Replace($kv.Key, $kv.Value); $totalR += $n }\n"
    "    }\n"
    "    if ($txt -ne $old) {\n"
    "        $bak = $f.FullName + \".repair_bak\"\n"
    "        if (-not (Test-Path $bak)) { Copy-Item $f.FullName $bak }\n"
    "        [IO.File]::WriteAllText($f.FullName, $txt, $enc)\n"
    "        Write-Host \"[FIXED] $($f.FullName)\"\n"
    "        $totalF++\n"
    "    } else { Write-Host \"[OK]    $($f.DirectoryName)\" }\n"
    "}\n"
    "Write-Host \"\"\n"
    "Write-Host \"Fixed: $totalF files, $totalR replacements\"\n"
    "if ($totalF -eq 0) { Write-Host \"No contamination found.\" }\n"
)

# UTF-16LE with BOM (PowerShell이 확실히 UTF-16 파일로 인식)
content_bytes = b'\xff\xfe' + script.encode('utf-16-le')
encoded = base64.b64encode(content_bytes).decode('ascii')
sys.stdout.write(encoded)
