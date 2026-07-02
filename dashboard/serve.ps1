param(
  [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Prefix = "http://127.0.0.1:$Port/"
$Listener = [System.Net.HttpListener]::new()
$Listener.Prefixes.Add($Prefix)

function Get-MimeType {
  param([string]$Path)
  switch ([System.IO.Path]::GetExtension($Path).ToLowerInvariant()) {
    ".html" { "text/html; charset=utf-8"; break }
    ".css" { "text/css; charset=utf-8"; break }
    ".js" { "application/javascript; charset=utf-8"; break }
    ".json" { "application/json; charset=utf-8"; break }
    default { "application/octet-stream" }
  }
}

$Listener.Start()
Write-Host "Serving $Root at $Prefix"

try {
  while ($Listener.IsListening) {
    $Context = $Listener.GetContext()
    $RequestPath = [Uri]::UnescapeDataString($Context.Request.Url.AbsolutePath.TrimStart("/"))
    if ([string]::IsNullOrWhiteSpace($RequestPath)) {
      $RequestPath = "dashboard/index.html"
    }

    $LocalPath = (Join-Path $Root ($RequestPath -replace "/", [System.IO.Path]::DirectorySeparatorChar))
    $FullPath = [System.IO.Path]::GetFullPath($LocalPath)

    if (-not $FullPath.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase)) {
      $Context.Response.StatusCode = 403
      $Context.Response.Close()
      continue
    }

    if (-not [System.IO.File]::Exists($FullPath)) {
      $Context.Response.StatusCode = 404
      $Context.Response.Close()
      continue
    }

    $Bytes = [System.IO.File]::ReadAllBytes($FullPath)
    $Context.Response.ContentType = Get-MimeType $FullPath
    $Context.Response.ContentLength64 = $Bytes.Length
    $Context.Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
    $Context.Response.Close()
  }
}
finally {
  $Listener.Stop()
  $Listener.Close()
}
