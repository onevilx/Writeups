<?php
require_once __DIR__ . '/vendor/autoload.php';

$smarty = new Smarty();
$smarty->setTemplateDir(__DIR__ . '/templates');
$smarty->setCompileDir(__DIR__ . '/templates_c');
$smarty->setCacheDir(__DIR__ . '/cache');

// --- WAF Configuration ---
$BLOCKLIST = [
    'system',
    'exec',
    'passthru',
    'shell_exec',
    'popen',
    'proc_open',
    'pcntl_exec',
    'eval',
    'assert',
    '\{php\}',
    '\{\/php\}',
    'flag',
    '\/etc',
    'proc',
    '\$smarty',
    'base64',
    'hex2bin',
    'call_user_func',
    'preg_replace',
    'create_function',
    'include',
    'require',
];

$MAX_INPUT_LENGTH = 200;
$RATE_LIMIT_FILE  = '/tmp/rate_limit.json';
$MAX_PIPES        = 3;

function is_blocked(string $text, array $blocklist): ?string {
    foreach ($blocklist as $pattern) {
        if (preg_match('/' . $pattern . '/i', $text)) {
            return $pattern;
        }
    }
    return null;
}

function is_rate_limited(string $file): bool {
    $ip   = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1')[0];
    $now  = time();
    $data = [];

    if (file_exists($file)) {
        $data = json_decode(file_get_contents($file), true) ?: [];
    }

    if (isset($data[$ip])) {
        $data[$ip] = array_filter($data[$ip], fn($t) => $t >= $now - 1);
    }

    $count = count($data[$ip] ?? []);
    if ($count >= 5) {
        return true;
    }

    $data[$ip][] = $now;
    file_put_contents($file, json_encode($data));
    return false;
}

$action  = $_GET['action'] ?? '';
$preview = null;
$error   = false;

if ($action === 'preview') {
    if (is_rate_limited($RATE_LIMIT_FILE)) {
        $preview = 'Rate limit exceeded. Try again later.';
        $error   = true;
    } else {
        $text = $_GET['text'] ?? '';

        if (empty($text)) {
        } elseif (strlen($text) > $MAX_INPUT_LENGTH) {
            $preview = "Input too long. Max {$MAX_INPUT_LENGTH} characters.";
            $error   = true;
        } elseif (is_blocked($text, $BLOCKLIST)) {
            $preview = 'WAF: blocked pattern detected.';
            $error   = true;
        } elseif (substr_count($text, '|') > $MAX_PIPES) {
            $preview = 'WAF: too many filters.';
            $error   = true;
        } else {
            $tpl_string = "<h3>Comment Preview:</h3><p>{$text}</p>";
            try {
                $preview = $smarty->fetch('string:' . $tpl_string);
            } catch (\Exception $e) {
                $preview = 'Template Error.';
                $error   = true;
            }
        }
    }
}

$smarty->assign('preview', $preview);
$smarty->assign('error', $error);
$smarty->display('index.tpl');
