<?php
namespace App\Service;

class ServiceChecker
{
    public $host;
    public $headers;

    private $reservedHeaders = array('host', 'referrer', 'x-forwarded-for', 'transfer-encoding', 'upgrade');

    public function __construct($host, $headers)
    {
        $this->host    = $host;
        $this->headers = $this->filterHeaders($headers);
    }

    public function filterHeaders($data)
    {
        $parsedHeaders = array();
        foreach ($data as $hKey => $hVal)
        {
            if (! in_array(strtolower(trim($hKey)), $this->reservedHeaders) )
            {
                $parsedHeaders[strtolower(trim($hKey))] = trim($hVal);
            }
        }
        return $parsedHeaders;
    }

    public function statusLive()
    {
        if (! preg_match("/^https?/i", $this->host) ) {
            return false;
        }

        array_walk($this->headers, static function(&$v, $k) { $v = $k.': '.$v; });

        $context = stream_context_create([
            "http" => [
                "header"        => implode("\r\n", $this->headers),
                "ignore_errors" => true,
            ],
        ]);

        $response = @file_get_contents($this->host, false, $context);

        if (! $response )
        {
            return false;
        }

        return true;
    }

}
