# List all top-level window titles (fallback dialog discovery).
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children,
  (New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Window)))
foreach ($w in $wins) {
  try { Write-Output ("PID=" + $w.Current.ProcessId + " TITLE=" + $w.Current.Name) }
  catch { }
}
