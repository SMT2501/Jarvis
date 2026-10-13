param([switch]$Probe)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try {
    Add-Type -AssemblyName System.Speech
    $installed = @([System.Speech.Recognition.SpeechRecognitionEngine]::InstalledRecognizers())
    if ($Probe) { @{recognizers=@($installed | ForEach-Object { $_.Culture.Name }); supported=($installed.Count -gt 0)} | ConvertTo-Json -Compress; exit }
    if ($installed.Count -eq 0) { throw 'No Windows speech recognizer installed. Typed chat is available.' }
    $choice = $installed | Where-Object { $_.Culture.Name -like 'en-*' } | Select-Object -First 1
    if (-not $choice) { $choice = $installed[0] }
    $recognizer = [System.Speech.Recognition.SpeechRecognitionEngine]::new($choice)
    try {
        $recognizer.LoadGrammar([System.Speech.Recognition.DictationGrammar]::new())
        $recognizer.SetInputToDefaultAudioDevice()
        $recognizer.InitialSilenceTimeout = [TimeSpan]::FromSeconds(8)
        $recognizer.BabbleTimeout = [TimeSpan]::FromSeconds(8)
        $result = $recognizer.Recognize([TimeSpan]::FromSeconds(8))
        if ($result) { @{text=$result.Text; confidence=$result.Confidence} | ConvertTo-Json -Compress }
        else { @{error='No speech recognized. Check microphone and try again.'} | ConvertTo-Json -Compress }
    } finally { $recognizer.Dispose() }
} catch { @{error=$_.Exception.Message} | ConvertTo-Json -Compress; exit 1 }
