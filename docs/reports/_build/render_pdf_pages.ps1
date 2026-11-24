param([Parameter(Mandatory=$true)][string]$PdfPath,[Parameter(Mandatory=$true)][string]$OutputDir,[int]$Width=1000)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.DataReader,Windows.Storage.Streams,ContentType=WindowsRuntime]
$generic=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$actionMethod=([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethodDefinition -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
function Await-Result($operation,[Type]$type) {
    $task=$generic.MakeGenericMethod($type).Invoke($null,@($operation))
    $task.Wait()
    return $task.Result
}
$file=Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync([IO.Path]::GetFullPath($PdfPath))) ([Windows.Storage.StorageFile])
$document=Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
[IO.Directory]::CreateDirectory([IO.Path]::GetFullPath($OutputDir)) | Out-Null
for ($i=0;$i -lt $document.PageCount;$i++) {
    $page=$document.GetPage($i)
    $stream=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $options=New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth=[uint32]$Width
    $action=$page.RenderToStreamAsync($stream,$options)
    $actionMethod.Invoke($null,@($action)).Wait()
    $reader=New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    $loaded=Await-Result ($reader.LoadAsync([uint32]$stream.Size)) ([uint32])
    $bytes=New-Object byte[] ([int]$stream.Size)
    $reader.ReadBytes($bytes)
    $dest=Join-Path $OutputDir ('page_{0:D2}.png' -f ($i+1))
    [IO.File]::WriteAllBytes([IO.Path]::GetFullPath($dest),$bytes)
    $reader.Dispose();$stream.Dispose();$page.Dispose()
}
Write-Output ('Rendered pages: '+$document.PageCount)
