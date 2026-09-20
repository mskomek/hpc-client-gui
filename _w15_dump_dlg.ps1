# Dump visible text of the "Unhandled exception in script" dialog via UIAutomation.
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::NameProperty, "Unhandled exception in script")
$dlg = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if ($null -eq $dlg) { Write-Output "DIALOG NOT FOUND"; exit 1 }
Write-Output ("FOUND: " + $dlg.Current.Name + " class=" + $dlg.Current.ClassName)
$texts = $dlg.FindAll([System.Windows.Automation.TreeScope]::Descendants,
  (New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::IsTextPatternAvailableProperty, $true)))
foreach ($t in $texts) {
  try {
    $pat = $t.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
    Write-Output "----- TEXT -----"
    Write-Output $pat.DocumentRange.GetText(-1)
  } catch { Write-Output ("<pattern error: " + $_ + ">") }
}
$edits = $dlg.FindAll([System.Windows.Automation.TreeScope]::Descendants,
  (New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Document)))
foreach ($e in $edits) {
  try {
    $pat = $e.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
    Write-Output "----- DOC -----"
    Write-Output $pat.DocumentRange.GetText(-1)
  } catch { Write-Output ("<doc error: " + $_ + ">") }
}
