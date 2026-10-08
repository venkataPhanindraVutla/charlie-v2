export function speakLocal(_text: string) {
  // Sidecar speaks through macOS `say` / Windows SAPI. Chromium speechSynthesis
  // is the robotic compact MacinTalk path — do not use it here.
}
