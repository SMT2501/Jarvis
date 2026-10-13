$ErrorActionPreference = 'Stop'
try {
    Add-Type -AssemblyName System.Speech
    $text = [Console]::In.ReadToEnd()
    $speaker = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try { $speaker.Speak($text) } finally { $speaker.Dispose() }
} catch { exit 1 }
